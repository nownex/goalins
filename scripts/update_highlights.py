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

LOOKBACK_DAYS = 7
MAX_HIGHLIGHTS = 50


# =========================================================
# ALLOWED LEAGUES
# =========================================================

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

    # Major tournaments
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


print("======================================")
print("GOALINS HIGHLIGHTS DIAGNOSTIC")
print("======================================")
print(f"Total matches in matches.json: {len(matches)}")


# =========================================================
# LOAD OLD HIGHLIGHTS
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
            "Could not read old highlights:",
            e
        )


existing_ids = {
    item.get("video_id")
    for item in existing_highlights
    if item.get("video_id")
}


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

    fixture_status = (
        match
        .get("fixture", {})
        .get("status", {})
    )

    if isinstance(fixture_status, dict):

        return str(
            fixture_status.get(
                "short",
                ""
            )
        )

    return str(
        status or ""
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


def team_in_title(
    team,
    title
):

    team = normalize_text(team)
    title = normalize_text(title)

    if not team:
        return False

    if team in title:
        return True

    words = [
        w for w in team.split()
        if len(w) >= 3
    ]

    if not words:
        return False

    found = sum(
        1
        for word in words
        if word in title
    )

    return found >= max(
        1,
        len(words) // 2
    )


# =========================================================
# DIAGNOSTIC COUNTERS
# =========================================================

allowed_count = 0
finished_count = 0
recent_count = 0

allowed_league_counts = {}

finished_matches = []


today = datetime.now(
    timezone.utc
).date()

minimum_date = (
    today - timedelta(
        days=LOOKBACK_DAYS
    )
)


# =========================================================
# ANALYZE MATCHES
# =========================================================

for match in matches:

    league = get_league(
        match
    )

    try:

        league_id = int(
            league.get("id")
        )

    except Exception:

        continue


    # ---------------------------------------------
    # ALLOWED LEAGUE
    # ---------------------------------------------

    if league_id not in ALLOWED_LEAGUES:

        continue


    allowed_count += 1


    league_name = (
        league.get("name")
        or ALLOWED_LEAGUES[league_id]
    )


    allowed_league_counts[
        league_name
    ] = (
        allowed_league_counts.get(
            league_name,
            0
        ) + 1
    )


    # ---------------------------------------------
    # STATUS
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


    finished_count += 1


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


    if match_date_obj < minimum_date:

        continue


    recent_count += 1


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


    fixture_id = (
        match.get("fixture_id")
        or match.get(
            "fixture",
            {}
        ).get("id")
    )


    finished_matches.append({

        "fixture_id":
            fixture_id,

        "date":
            match_date,

        "league_id":
            league_id,

        "league":
            league_name,

        "home":
            home_name,

        "away":
            away_name

    })


# =========================================================
# PRINT DIAGNOSTICS
# =========================================================

print("--------------------------------------")
print(f"Allowed league matches: {allowed_count}")
print(f"Finished allowed matches: {finished_count}")
print(
    f"Finished matches in last {LOOKBACK_DAYS} days: "
    f"{recent_count}"
)

print("--------------------------------------")
print("Allowed league distribution:")

for name, count in sorted(
    allowed_league_counts.items()
):

    print(
        f"  {name}: {count}"
    )

print("--------------------------------------")
print("Recent finished matches:")

for match in finished_matches:

    print(
        f"  {match['date']} | "
        f"{match['league']} | "
        f"{match['home']} vs {match['away']}"
    )

print("======================================")


# =========================================================
# SEARCH YOUTUBE
# =========================================================

def search_youtube(query):

    params = {

        "part": "snippet",

        "q": query,

        "type": "video",

        "maxResults": 10,

        "order": "relevance",

        "videoEmbeddable": "true",

        "videoSyndicated": "true",

        "videoDuration": "medium",

        "key": API_KEY

    }


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
# SEARCH HIGHLIGHTS
# =========================================================

new_highlights = []


for match in finished_matches:

    home_name = match["home"]
    away_name = match["away"]

    fixture_id = match["fixture_id"]

    query = (
        f"{home_name} {away_name} "
        f"highlights"
    )


    print("--------------------------------------")
    print(
        f"Searching YouTube: "
        f"{home_name} vs {away_name}"
    )


    try:

        videos = search_youtube(
            query
        )

    except Exception as e:

        print(
            "YouTube error:",
            e
        )

        continue


    print(
        f"YouTube results: {len(videos)}"
    )


    selected = None


    for video in videos:

        video_id = (
            video
            .get("id", {})
            .get("videoId")
        )

        if not video_id:
            continue


        if video_id in existing_ids:
            continue


        snippet = video.get(
            "snippet",
            {}
        )


        title = snippet.get(
            "title",
            ""
        )


        print(
            f"  Result: {title}"
        )


        # -----------------------------------------
        # REJECT SHORTS
        # -----------------------------------------

        title_normalized = normalize_text(
            title
        )

        if (
            "shorts" in title_normalized
            or "#shorts" in title_normalized
        ):

            continue


        # -----------------------------------------
        # CHECK TEAMS
        # -----------------------------------------

        home_ok = team_in_title(
            home_name,
            title
        )

        away_ok = team_in_title(
            away_name,
            title
        )


        if not home_ok or not away_ok:

            continue


        thumbnails = snippet.get(
            "thumbnails",
            {}
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
                match["date"],

            "league_id":
                match["league_id"],

            "league":
                match["league"],

            "league_key":
                ALLOWED_LEAGUES[
                    match["league_id"]
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

        print(
            f"SELECTED VIDEO: "
            f"{selected['title']}"
        )

        new_highlights.append(
            selected
        )

        existing_ids.add(
            selected["video_id"]
        )

    else:

        print(
            "No matching video found."
        )


# =========================================================
# MERGE
# =========================================================

combined = []

seen_videos = set()
seen_fixtures = set()


for item in new_highlights + existing_highlights:

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
# SORT
# =========================================================

combined.sort(
    key=lambda item: (
        item.get("date", ""),
        item.get("published_at", "")
    ),
    reverse=True
)


combined = combined[
    :MAX_HIGHLIGHTS
]


# =========================================================
# SAVE
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
    "data",
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


print("======================================")
print(
    f"GOALINS: {len(combined)} highlights saved."
)
print(
    f"New videos: {len(new_highlights)}"
)
print("======================================")
