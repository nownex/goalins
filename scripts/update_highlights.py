import json
import os
import re
import requests
from datetime import datetime, timezone, timedelta


# =========================================================
# GOALINS — YOUTUBE HIGHLIGHTS ENGINE
# =========================================================

API_KEY = os.environ.get("YOUTUBE_API_KEY")

if not API_KEY:
    raise RuntimeError("YOUTUBE_API_KEY is missing")


MATCHES_FILE = "data/matches.json"
OUTPUT_FILE = "data/highlights.json"

YOUTUBE_SEARCH_URL = (
    "https://www.googleapis.com/youtube/v3/search"
)


# =========================================================
# SETTINGS
# =========================================================

MAX_HIGHLIGHTS = 50

# نبحث فقط عن مباريات انتهت خلال آخر 7 أيام
# حتى لا نستهلك Quota على مباريات قديمة جدًا.
LOOKBACK_DAYS = 7

# =========================================================
# ALLOWED LEAGUES
# =========================================================
# هذه القائمة هي المصدر الوحيد المسموح به.
# لا توجد دوريات درجة ثانية أو كرة نسائية هنا.

ALLOWED_LEAGUES = {

    # England
    39: "premier-league",

    # Spain
    140: "la-liga",

    # France
    61: "ligue-1",

    # Italy
    135: "serie-a",

    # Netherlands
    88: "eredivisie",

    # Belgium
    144: "jupiler-pro-league",

    # Portugal
    94: "primeira-liga",

    # Germany
    78: "bundesliga",

    # UEFA
    2: "champions-league",
    3: "europa-league",
    848: "conference-league",

    # Major international competitions
    1: "world-cup",
    4: "euro",
    6: "afcon",
    9: "copa-america",

}


# =========================================================
# LOAD MATCHES
# =========================================================

with open(
    MATCHES_FILE,
    "r",
    encoding="utf-8"
) as f:

    data = json.load(f)


if isinstance(data, dict):

    matches = data.get(
        "matches",
        []
    )

elif isinstance(data, list):

    matches = data

else:

    matches = []


# =========================================================
# LOAD EXISTING HIGHLIGHTS
# =========================================================

existing_highlights = []

if os.path.exists(OUTPUT_FILE):

    try:

        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            old_data = json.load(f)


        if isinstance(old_data, dict):

            existing_highlights = old_data.get(
                "highlights",
                []
            )

        elif isinstance(old_data, list):

            existing_highlights = old_data

    except Exception as e:

        print(
            "Could not load existing highlights:",
            e
        )


# =========================================================
# HELPERS
# =========================================================

def get_league(match):

    return (
        match.get("league")
        or match.get("competition")
        or {}
    )


def get_teams(match):

    teams = match.get(
        "teams",
        {}
    )

    home = (
        match.get("home")
        or teams.get("home")
        or {}
    )

    away = (
        match.get("away")
        or teams.get("away")
        or {}
    )

    return home, away


def get_date(match):

    value = (
        match.get("date")
        or match.get(
            "fixture",
            {}
        ).get("date")
        or ""
    )

    return str(value)[:10]


def get_status(match):

    status = match.get("status")

    if isinstance(status, dict):

        return str(
            status.get(
                "short",
                ""
            )
        )

    return str(
        status
        or match.get(
            "fixture",
            {}
        ).get(
            "status",
            {}
        ).get(
            "short",
            ""
        )
    )


def normalize_text(text):

    text = str(text).lower()

    text = re.sub(
        r"[^a-z0-9\u0600-\u06ff]+",
        " ",
        text
    )

    return " ".join(
        text.split()
    )


def team_matches_title(
    team_name,
    title
):

    team = normalize_text(
        team_name
    )

    title_normalized = normalize_text(
        title
    )

    if not team:
        return False

    # المطابقة الكاملة أولاً
    if team in title_normalized:
        return True

    # محاولة مطابقة الكلمات المهمة
    words = [
        word
        for word in team.split()
        if len(word) >= 3
    ]

    if not words:
        return False

    found = sum(
        1
        for word in words
        if word in title_normalized
    )

    return found >= max(
        1,
        len(words) // 2
    )


def is_good_video_title(
    title,
    home_name,
    away_name
):

    title_normalized = normalize_text(
        title
    )

    # نرفض Shorts صراحةً
    if "#shorts" in title_normalized:
        return False

    if "shorts" in title_normalized:
        return False

    # يجب أن يظهر الفريقان في العنوان
    home_ok = team_matches_title(
        home_name,
        title
    )

    away_ok = team_matches_title(
        away_name,
        title
    )

    if not home_ok or not away_ok:
        return False

    # يجب أن يكون الفيديو مرتبطًا بالملخص
    highlight_words = [
        "highlight",
        "highlights",
        "goals",
        "goal",
        "resumen",
        "resumo",
        "recap",
        "match",
        "extended",
        "full",
        "ملخص",
        "اهداف",
        "أهداف"
    ]

    return any(
        word in title_normalized
        for word in highlight_words
    )


# =========================================================
# SEARCH YOUTUBE
# =========================================================

def search_youtube(
    query,
    published_after=None
):

    params = {

        "part": "snippet",

        "q": query,

        "type": "video",

        "maxResults": 10,

        "order": "relevance",

        "videoEmbeddable": "true",

        "videoSyndicated": "true",

        # غالبًا ملخصات المباريات تقع ضمن هذا النطاق
        # ويقلل ظهور Shorts
        "videoDuration": "medium",

        "key": API_KEY

    }


    if published_after:

        params["publishedAfter"] = (
            published_after
        )


    response = requests.get(
        YOUTUBE_SEARCH_URL,
        params=params,
        timeout=30
    )


    response.raise_for_status()


    result = response.json()


    if "error" in result:

        raise RuntimeError(
            str(
                result["error"]
            )
        )


    return result.get(
        "items",
        []
    )


# =========================================================
# EXISTING VIDEO IDS
# =========================================================

existing_ids = set()

for item in existing_highlights:

    video_id = item.get(
        "video_id"
    )

    if video_id:

        existing_ids.add(
            video_id
        )


print(
    f"Existing highlights: {len(existing_ids)}"
)


# =========================================================
# DATE LIMIT
# =========================================================

now = datetime.now(
    timezone.utc
)

minimum_date = (
    now - timedelta(
        days=LOOKBACK_DAYS
    )
).date()


# =========================================================
# BUILD HIGHLIGHTS
# =========================================================

new_highlights = []


for match in matches:

    league = get_league(
        match
    )


    # ---------------------------------------------
    # LEAGUE ID
    # ---------------------------------------------

    try:

        league_id = int(
            league.get("id")
        )

    except Exception:

        continue


    # ---------------------------------------------
    # ONLY ALLOWED LEAGUES
    # ---------------------------------------------

    if league_id not in ALLOWED_LEAGUES:

        continue


    # ---------------------------------------------
    # ONLY FINISHED MATCHES
    # ---------------------------------------------

    status = get_status(
        match
    )

    if status not in (
        "FT",
        "AET",
        "PEN"
    ):

        continue


    # ---------------------------------------------
    # DATE
    # ---------------------------------------------

    match_date = get_date(
        match
    )

    try:

        match_date_obj = datetime.strptime(
            match_date,
            "%Y-%m-%d"
        ).date()

    except Exception:

        continue


    # لا نبحث عن مباريات قديمة جدًا
    if match_date_obj < minimum_date:

        continue


    # ---------------------------------------------
    # TEAMS
    # ---------------------------------------------

    home, away = get_teams(
        match
    )


    home_name = (
        home.get("name")
        or "Home"
    )

    away_name = (
        away.get("name")
        or "Away"
    )


    # ---------------------------------------------
    # MATCH KEY
    # ---------------------------------------------

    fixture_id = (
        match.get("fixture_id")
        or match.get("fixture", {}).get("id")
    )


    # ---------------------------------------------
    # SKIP IF WE ALREADY HAVE A VIDEO
    # ---------------------------------------------

    already_exists = False


    for item in existing_highlights:

        if fixture_id and item.get(
            "fixture_id"
        ) == fixture_id:

            already_exists = True
            break


        if (
            item.get("home") == home_name
            and
            item.get("away") == away_name
            and
            item.get("date") == match_date
        ):

            already_exists = True
            break


    if already_exists:

        continue


    # ---------------------------------------------
    # LEAGUE NAME
    # ---------------------------------------------

    league_name = (
        league.get("name")
        or "Football"
    )


    # ---------------------------------------------
    # SEARCH
    # ---------------------------------------------

    query = (
        f'"{home_name}" '
        f'"{away_name}" '
        f'highlights'
    )


    # نبحث عن الفيديوهات المنشورة حول وقت المباراة
    published_after = (
        datetime.combine(
            match_date_obj,
            datetime.min.time()
        )
        .replace(
            tzinfo=timezone.utc
        )
        .isoformat()
        .replace(
            "+00:00",
            "Z"
        )
    )


    print(
        f"Searching: {home_name} vs {away_name}"
    )


    try:

        videos = search_youtube(
            query,
            published_after
        )

    except Exception as e:

        print(
            "YouTube error:",
            e
        )

        continue


    if not videos:

        print(
            "No videos found."
        )

        continue


    # ---------------------------------------------
    # SELECT BEST MATCH
    # ---------------------------------------------

    selected = None


    for video in videos:

        video_id = (
            video
            .get("id", {})
            .get("videoId")
        )


        snippet = video.get(
            "snippet",
            {}
        )


        if not video_id:

            continue


        if video_id in existing_ids:

            continue


        title = snippet.get(
            "title",
            ""
        )


        if not is_good_video_title(
            title,
            home_name,
            away_name
        ):

            continue


        thumbnails = (
            snippet.get(
                "thumbnails",
                {}
            )
        )


        thumbnail = (
            thumbnails
            .get(
                "high",
                {}
            )
            .get("url")
        )


        if not thumbnail:

            thumbnail = (
                thumbnails
                .get(
                    "medium",
                    {}
                )
                .get("url")
            )


        selected = {

            "fixture_id":
                fixture_id,

            "video_id":
                video_id,

            "title":
                title,

            "thumbnail":
                thumbnail,

            "channel":
                snippet.get(
                    "channelTitle",
                    ""
                ),

            "published_at":
                snippet.get(
                    "publishedAt",
                    ""
                ),

            "date":
                match_date,

            "league_id":
                league_id,

            "league":
                league_name,

            "league_key":
                ALLOWED_LEAGUES[
                    league_id
                ],

            "home":
                home_name,

            "away":
                away_name,

            "embed":
                (
                    "https://www.youtube.com/embed/"
                    f"{video_id}"
                ),

            "youtube_url":
                (
                    "https://www.youtube.com/watch?v="
                    f"{video_id}"
                )

        }


        break


    if selected:

        new_highlights.append(
            selected
        )

        existing_ids.add(
            selected["video_id"]
        )

        print(
            "Selected:",
            selected["title"]
        )

    else:

        print(
            "No reliable matching highlight found."
        )


# =========================================================
# MERGE OLD + NEW
# =========================================================

combined = []

seen_fixtures = set()
seen_videos = set()


# الجديد أولاً
for item in new_highlights:

    video_id = item.get(
        "video_id"
    )

    fixture_id = item.get(
        "fixture_id"
    )


    if video_id and video_id in seen_videos:

        continue


    if fixture_id and fixture_id in seen_fixtures:

        continue


    combined.append(
        item
    )


    if video_id:

        seen_videos.add(
            video_id
        )


    if fixture_id:

        seen_fixtures.add(
            fixture_id
        )


# القديم
for item in existing_highlights:

    video_id = item.get(
        "video_id"
    )

    fixture_id = item.get(
        "fixture_id"
    )


    if video_id and video_id in seen_videos:

        continue


    if fixture_id and fixture_id in seen_fixtures:

        continue


    combined.append(
        item
    )


    if video_id:

        seen_videos.add(
            video_id
        )


    if fixture_id:

        seen_fixtures.add(
            fixture_id
        )


# =========================================================
# SORT BY DATE
# =========================================================

combined.sort(
    key=lambda x: (
        x.get("date", ""),
        x.get("published_at", "")
    ),
    reverse=True
)


# =========================================================
# LIMIT
# =========================================================

combined = combined[
    :MAX_HIGHLIGHTS
]


# =========================================================
# OUTPUT
# =========================================================

output = {

    "updated_at":
        datetime.now(
            timezone.utc
        ).isoformat(),

    "count":
        len(combined),

    "highlights":
        combined

}


os.makedirs(
    os.path.dirname(
        OUTPUT_FILE
    ),
    exist_ok=True
)


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        output,
        f,
        ensure_ascii=False,
        indent=2
    )


print(
    "======================================"
)

print(
    f"GOALINS: {len(combined)} highlights saved."
)

print(
    f"New videos: {len(new_highlights)}"
)

print(
    "======================================"
        )
