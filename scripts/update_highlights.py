import json
import os
import re
import requests

from datetime import datetime, timezone, timedelta


# =========================================================
# GOALINS — beIN SPORTS CHANNEL VIDEO ENGINE
# =========================================================

API_KEY = os.environ.get("YOUTUBE_API_KEY")

if not API_KEY:
    raise RuntimeError("YOUTUBE_API_KEY is missing")


MATCHES_FILE = "data/matches.json"
OUTPUT_FILE = "data/highlights.json"

CHANNELS_URL = (
    "https://www.googleapis.com/youtube/v3/channels"
)

PLAYLIST_ITEMS_URL = (
    "https://www.googleapis.com/youtube/v3/playlistItems"
)

VIDEOS_URL = (
    "https://www.googleapis.com/youtube/v3/videos"
)

BEIN_HANDLE = "@beinsports"

LOOKBACK_DAYS = 7
MAX_HIGHLIGHTS = 50

# How many latest channel videos to inspect
CHANNEL_VIDEO_LIMIT = 50


# =========================================================
# ALLOWED LEAGUES
# =========================================================

ALLOWED_LEAGUES = {
    "Premier League",
    "La Liga",
    "Ligue 1",
    "Serie A",
    "Eredivisie",
    "Jupiler Pro League",
    "Primeira Liga",
    "Bundesliga",
    "UEFA Champions League",
    "UEFA Europa League",
    "UEFA Europa Conference League",
    "UEFA Europa Conference League Qualification",
}


# =========================================================
# GAMING FILTER
# =========================================================

GAMING_WORDS = [
    "fifa",
    "ea fc",
    "fc 26",
    "fc26",
    "fc 25",
    "fc25",
    "efootball",
    "pes",
    "pes 2026",
    "playstation",
    "ps4",
    "ps5",
    "xbox",
    "gameplay",
    "gaming",
    "career mode",
    "ultimate team",
    "simulation",
    "simulated",
    "video game",
    "لعبة",
    "فيفا",
    "إي فوتبول",
    "اي فوتبول",
]


# =========================================================
# TEAM ALIASES
# =========================================================

TEAM_ALIASES = {

    "FK Tobol Kostanay": [
        "توبول",
        "توبول كوستاناي",
    ],

    "Kaisar": [
        "كايسار",
        "قايصار",
        "كايزار",
        "قيسار",
    ],

    "Abdish-Ata": [
        "أبدش آتا",
        "أبدش أتا",
        "أبدش عطا",
        "أبدش",
    ],

    "Talant": [
        "تالانت",
        "تالنت",
    ],

    "Al Kuwait": [
        "الكويت",
        "نادي الكويت",
        "الكويت الكويتي",
    ],

    "Al Arabi": [
        "العربي",
        "العربي الكويتي",
        "نادي العربي",
    ],

    "Sabah FA": [
        "ساباه",
        "صباح",
        "ساباه باكو",
        "سباه",
    ],

    "Hapoel Beer Sheva": [
        "هبوعيل بئر السبع",
        "هبوعيل بئر سبع",
        "هبوعيل بئرشبع",
        "بئر السبع",
    ],

    "Al Fahaheel": [
        "الفحيحيل",
        "فحيحيل",
    ],

    "Al Qadsia": [
        "القادسية",
        "القادسية الكويتي",
    ],

    "Al Shabab": [
        "الشباب",
        "الشباب الكويتي",
    ],

    "Valencia": [
        "فالنسيا",
    ],

    "Real Betis": [
        "ريال بيتيس",
        "بيتيس",
    ],

    "Celtic": [
        "سيلتيك",
        "سلتيك",
    ],

    "Bodo/Glimt": [
        "بودو غليمت",
        "بودو جليمت",
        "بودو",
    ],

    "Rapid Vienna": [
        "رابيد فيينا",
        "رابيد",
    ],

    "Heart of Midlothian": [
        "هارتس",
        "هارت أوف ميدلوثيان",
        "هارت اوف ميدلوثيان",
    ],

    "Botafogo": [
        "بوتافوغو",
        "بوتافوجو",
    ],

    "Atletico Paranaense": [
        "أتلتيكو باراناينسي",
        "اتلتيكو باراناينسي",
        "باراناينسي",
    ],

    "Zamalek SC": [
        "الزمالك",
        "نادي الزمالك",
    ],

    "Smouha SC": [
        "سموحة",
        "سموحه",
    ],

    "National Bank of Egypt": [
        "البنك الأهلي",
        "البنك الاهلي",
        "البنك الأهلي المصري",
    ],

    "Petrojet": [
        "بتروجيت",
        "بتروجت",
    ],

    "El Geish": [
        "طلائع الجيش",
    ],
}


# =========================================================
# NORMALIZE
# =========================================================

def normalize(text):

    text = str(text or "").lower()

    text = text.replace("أ", "ا")
    text = text.replace("إ", "ا")
    text = text.replace("آ", "ا")
    text = text.replace("ى", "ي")
    text = text.replace("ة", "ه")
    text = text.replace("ؤ", "و")
    text = text.replace("ئ", "ي")

    text = re.sub(
        r"[\u064B-\u065F\u0670]",
        "",
        text
    )

    text = re.sub(
        r"[^a-z0-9\u0600-\u06ff]+",
        " ",
        text
    )

    return " ".join(
        text.split()
    )


# =========================================================
# GAMING
# =========================================================

def is_gaming(text):

    value = normalize(text)

    for word in GAMING_WORDS:

        if normalize(word) in value:

            return True

    return False


# =========================================================
# MATCH HELPERS
# =========================================================

def get_date(match):

    return str(
        match.get(
            "date",
            ""
        )
    )[:10]


def get_league(match):

    league = match.get(
        "league",
        {}
    )

    if isinstance(
        league,
        dict
    ):

        return str(
            league.get(
                "name",
                ""
            )
        ).strip()

    return str(
        league or ""
    ).strip()


def get_team(match, side):

    team = match.get(
        side,
        {}
    )

    if isinstance(
        team,
        dict
    ):

        return str(
            team.get(
                "name",
                ""
            )
        ).strip()

    return str(
        team or ""
    ).strip()


def get_status(match):

    status = match.get(
        "status",
        ""
    )

    if isinstance(
        status,
        dict
    ):

        return str(
            status.get(
                "short",
                ""
            )
        ).upper()

    return str(
        status
    ).upper()


def is_finished(match):

    return get_status(match) in {
        "FT",
        "AET",
        "PEN",
    }


# =========================================================
# TEAM ALIASES
# =========================================================

def aliases_for_team(team):

    result = [
        normalize(team)
    ]

    for key, aliases in TEAM_ALIASES.items():

        if normalize(key) == normalize(team):

            result.extend(
                normalize(x)
                for x in aliases
            )

    clean = []

    seen = set()

    for item in result:

        if not item:
            continue

        if item in seen:
            continue

        seen.add(item)
        clean.append(item)

    return clean


# =========================================================
# TEAM FOUND
# =========================================================

def team_found(team, text):

    value = normalize(text)

    aliases = aliases_for_team(
        team
    )

    for alias in aliases:

        if alias in value:

            return True

    return False


# =========================================================
# SCORE VIDEO AGAINST MATCH
# =========================================================

def score_video(
    title,
    description,
    home,
    away
):

    text = normalize(
        f"{title} {description}"
    )

    score = 0

    home_found = team_found(
        home,
        text
    )

    away_found = team_found(
        away,
        text
    )

    if home_found:
        score += 100

    if away_found:
        score += 100

    if home_found and away_found:
        score += 200

    if "ملخص" in text:
        score += 60

    if "اهداف" in text:
        score += 50

    if "مباراة" in text:
        score += 25

    if "highlights" in text:
        score += 40

    if "goals" in text:
        score += 35

    if is_gaming(text):
        score -= 500

    return (
        score,
        home_found,
        away_found
    )


# =========================================================
# GET CHANNEL INFORMATION
#
# channels.list costs very little compared with search.list
# =========================================================

def get_channel():

    print("=" * 60)
    print("Finding beIN SPORTS channel")
    print("=" * 60)

    params = {
        "part": "id,contentDetails,snippet",
        "forHandle": BEIN_HANDLE,
        "key": API_KEY,
    }

    response = requests.get(
        CHANNELS_URL,
        params=params,
        timeout=30
    )

    print(
        "Channel HTTP:",
        response.status_code
    )

    response.raise_for_status()

    data = response.json()

    items = data.get(
        "items",
        []
    )

    if not items:

        raise RuntimeError(
            "beIN SPORTS channel not found"
        )

    channel = items[0]

    channel_id = channel.get(
        "id"
    )

    uploads_playlist = (
        channel
        .get(
            "contentDetails",
            {}
        )
        .get(
            "relatedPlaylists",
            {}
        )
        .get(
            "uploads"
        )
    )

    if not channel_id:

        raise RuntimeError(
            "beIN channel ID missing"
        )

    if not uploads_playlist:

        raise RuntimeError(
            "beIN uploads playlist missing"
        )

    print(
        "Channel ID:",
        channel_id
    )

    print(
        "Uploads playlist:",
        uploads_playlist
    )

    return (
        channel_id,
        uploads_playlist
    )


# =========================================================
# GET LATEST CHANNEL VIDEOS
#
# IMPORTANT:
# No search.list is used here.
# =========================================================

def get_latest_channel_videos(
    uploads_playlist
):

    print("=" * 60)
    print("Reading latest beIN SPORTS videos")
    print("=" * 60)

    params = {
        "part": "snippet,contentDetails",
        "playlistId": uploads_playlist,
        "maxResults": CHANNEL_VIDEO_LIMIT,
        "key": API_KEY,
    }

    response = requests.get(
        PLAYLIST_ITEMS_URL,
        params=params,
        timeout=30
    )

    print(
        "Playlist HTTP:",
        response.status_code
    )

    response.raise_for_status()

    data = response.json()

    items = data.get(
        "items",
        []
    )

    print(
        "Channel videos returned:",
        len(items)
    )

    return items


# =========================================================
# GET VIDEO DETAILS
#
# This confirms duration and embeddability.
# =========================================================

def get_video_details(video_ids):

    if not video_ids:
        return {}

    params = {
        "part": "snippet,contentDetails,status",
        "id": ",".join(video_ids),
        "key": API_KEY,
    }

    response = requests.get(
        VIDEOS_URL,
        params=params,
        timeout=30
    )

    print(
        "Videos HTTP:",
        response.status_code
    )

    response.raise_for_status()

    data = response.json()

    result = {}

    for item in data.get(
        "items",
        []
    ):

        video_id = item.get(
            "id"
        )

        if video_id:

            result[
                video_id
            ] = item

    return result


# =========================================================
# LOAD MATCHES
# =========================================================

with open(
    MATCHES_FILE,
    "r",
    encoding="utf-8"
) as file:

    matches_data = json.load(
        file
    )

matches = matches_data.get(
    "matches",
    []
)

print("=" * 60)

print(
    "GOALINS — beIN SPORTS DIRECT "
    "CHANNEL ENGINE"
)

print("=" * 60)

print(
    "No YouTube search.list is used."
)

print(
    f"Total matches: {len(matches)}"
)


# =========================================================
# DATE RANGE
# =========================================================

algeria_now = (
    datetime.now(
        timezone.utc
    )
    + timedelta(
        hours=1
    )
)

today = algeria_now.date()

start_date = (
    today
    - timedelta(
        days=LOOKBACK_DAYS
    )
)

print(
    f"Algeria date: {today}"
)

print(
    f"Looking back: {LOOKBACK_DAYS} days"
)


# =========================================================
# TARGET MATCHES
# =========================================================

target_matches = []

for match in matches:

    league = get_league(
        match
    )

    if league not in ALLOWED_LEAGUES:
        continue

    if not is_finished(match):
        continue

    match_date = get_date(
        match
    )

    try:

        date_obj = datetime.strptime(
            match_date,
            "%Y-%m-%d"
        ).date()

    except Exception:

        continue

    if date_obj < start_date:
        continue

    if date_obj > today:
        continue

    home = get_team(
        match,
        "home"
    )

    away = get_team(
        match,
        "away"
    )

    if not home or not away:
        continue

    target_matches.append({

        "fixture_id":
            match.get(
                "fixture_id"
            ),

        "date":
            match_date,

        "league":
            league,

        "home":
            home,

        "away":
            away,

    })


print("-" * 60)

print(
    "Target finished matches:",
    len(target_matches)
)

print("-" * 60)


# =========================================================
# LOAD OLD HIGHLIGHTS
# =========================================================

old_highlights = []

if os.path.exists(
    OUTPUT_FILE
):

    try:

        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            old_data = json.load(
                file
            )

        if isinstance(
            old_data,
            dict
        ):

            old_highlights = (
                old_data.get(
                    "highlights",
                    []
                )
            )

        elif isinstance(
            old_data,
            list
        ):

            old_highlights = old_data

    except Exception:

        old_highlights = []


old_ids = {

    str(
        item.get(
            "highlight_id"
        )
    )

    for item in old_highlights

    if item.get(
        "highlight_id"
    )

}


# =========================================================
# GET CHANNEL
# =========================================================

channel_id, uploads_playlist = (
    get_channel()
)


# =========================================================
# GET LATEST VIDEOS
# =========================================================

playlist_items = (
    get_latest_channel_videos(
        uploads_playlist
    )
)


# =========================================================
# COLLECT VIDEO IDS
# =========================================================

video_ids = []

for item in playlist_items:

    content = item.get(
        "contentDetails",
        {}
    )

    video_id = content.get(
        "videoId"
    )

    if video_id:
        video_ids.append(
            video_id
        )


video_ids = list(
    dict.fromkeys(
        video_ids
    )
)


print(
    "Unique video IDs:",
    len(video_ids)
)


# =========================================================
# VIDEO DETAILS
# =========================================================

video_details = (
    get_video_details(
        video_ids
    )
)


# =========================================================
# PREPARE CANDIDATES
# =========================================================

channel_videos = []

for item in playlist_items:

    snippet = item.get(
        "snippet",
        {}
    )

    content = item.get(
        "contentDetails",
        {}
    )

    video_id = content.get(
        "videoId"
    )

    if not video_id:
        continue

    title = str(
        snippet.get(
            "title",
            ""
        )
    )

    description = str(
        snippet.get(
            "description",
            ""
        )
    )

    published_at = str(
        snippet.get(
            "publishedAt",
            ""
        )
    )

    detail = video_details.get(
        video_id,
        {}
    )

    status = detail.get(
        "status",
        {}
    )

    # -----------------------------------------------------
    # Embedding
    # -----------------------------------------------------

    embeddable = status.get(
        "embeddable",
        True
    )

    if embeddable is False:

        print(
            "Rejected non-embeddable:",
            title
        )

        continue

    # -----------------------------------------------------
    # Gaming
    # -----------------------------------------------------

    if is_gaming(
        f"{title} {description}"
    ):

        print(
            "Rejected gaming:",
            title
        )

        continue

    thumbnail = (
        snippet
        .get(
            "thumbnails",
            {}
        )
        .get(
            "high",
            {}
        )
        .get(
            "url"
        )
    )

    if not thumbnail:

        thumbnail = (
            snippet
            .get(
                "thumbnails",
                {}
            )
            .get(
                "medium",
                {}
            )
            .get(
                "url"
            )
        )

    channel_videos.append({

        "video_id":
            video_id,

        "title":
            title,

        "description":
            description,

        "published_at":
            published_at,

        "thumbnail":
            thumbnail,

        "channel_id":
            channel_id,

        "channel_title":
            snippet.get(
                "channelTitle",
                "beIN SPORTS"
            ),

    })


print(
    "Usable beIN videos:",
    len(channel_videos)
)


# =========================================================
# MATCH VIDEOS TO FIXTURES
# =========================================================

new_highlights = []

used_video_ids = set()

used_fixture_ids = set()


for fixture in target_matches:

    if len(
        new_highlights
    ) >= MAX_HIGHLIGHTS:

        break

    fixture_id = fixture.get(
        "fixture_id"
    )

    best = None

    best_score = 0

    print("=" * 60)

    print(
        "MATCHING:"
    )

    print(
        f"{fixture['date']} | "
        f"{fixture['home']} vs "
        f"{fixture['away']}"
    )

    print("=" * 60)


    for video in channel_videos:

        video_id = video[
            "video_id"
        ]

        if video_id in used_video_ids:
            continue

        if video_id in old_ids:
            continue

        score, home_found, away_found = (
            score_video(
                video["title"],
                video["description"],
                fixture["home"],
                fixture["away"]
            )
        )

        if score <= 0:
            continue

        print(
            f"Candidate [{score}] "
            f"H={home_found} "
            f"A={away_found}: "
            f"{video['title']}"
        )

        # -------------------------------------------------
        # REQUIRE BOTH TEAMS
        # -------------------------------------------------

        if not (
            home_found
            and away_found
        ):

            continue

        # -------------------------------------------------
        # Prefer videos published close to match date
        # -------------------------------------------------

        date_bonus = 0

        published = video.get(
            "published_at",
            ""
        )

        try:

            published_date = (
                datetime.fromisoformat(
                    published.replace(
                        "Z",
                        "+00:00"
                    )
                ).date()
            )

            match_date = datetime.strptime(
                fixture["date"],
                "%Y-%m-%d"
            ).date()

            difference = abs(
                (
                    published_date
                    - match_date
                ).days
            )

            if difference == 0:
                date_bonus = 50

            elif difference == 1:
                date_bonus = 40

            elif difference == 2:
                date_bonus = 20

            elif difference <= 3:
                date_bonus = 10

        except Exception:

            pass

        final_score = (
            score
            + date_bonus
        )

        if (
            best is None
            or final_score > best_score
        ):

            best = video
            best_score = final_score


    # =====================================================
    # NO MATCH
    # =====================================================

    if best is None:

        print(
            "No reliable beIN video found."
        )

        continue


    # =====================================================
    # SAVE MATCH
    # =====================================================

    video_id = best[
        "video_id"
    ]

    print(
        "SELECTED:"
    )

    print(
        best["title"]
    )

    print(
        "Score:",
        best_score
    )


    item = {

        "highlight_id":
            video_id,

        "fixture_id":
            fixture_id,

        "title":
            best["title"],

        "description":
            best["description"],

        "thumbnail":
            best["thumbnail"],

        "embed":
            (
                "https://www.youtube.com/embed/"
                + video_id
            ),

        "embed_url":
            (
                "https://www.youtube.com/embed/"
                + video_id
            ),

        "url":
            (
                "https://www.youtube.com/watch?v="
                + video_id
            ),

        "youtube_id":
            video_id,

        "source":
            "YouTube",

        "channel":
            best["channel_title"],

        "channel_id":
            best["channel_id"],

        "type":
            "OFFICIAL",

        "date":
            fixture["date"],

        "league":
            fixture["league"],

        "home":
            fixture["home"],

        "away":
            fixture["away"],

    }


    new_highlights.append(
        item
    )

    used_video_ids.add(
        video_id
    )

    if fixture_id:
        used_fixture_ids.add(
            fixture_id
        )


# =========================================================
# MERGE
# =========================================================

combined = []

seen_ids = set()

for item in (
    new_highlights
    + old_highlights
):

    video_id = str(
        item.get(
            "highlight_id",
            ""
        )
    )

    if not video_id:
        continue

    if video_id in seen_ids:
        continue

    seen_ids.add(
        video_id
    )

    combined.append(
        item
    )


# =========================================================
# SORT
# =========================================================

combined.sort(
    key=lambda item: (
        item.get(
            "date",
            ""
        ),
        item.get(
            "published_at",
            ""
        )
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

    "source":
        "YouTube / beIN SPORTS",

    "channel":
        BEIN_HANDLE,

    "channel_id":
        channel_id,

    "type":
        "OFFICIAL",

    "count":
        len(combined),

    "highlights":
        combined,

}


os.makedirs(
    "data",
    exist_ok=True
)


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        output,
        file,
        ensure_ascii=False,
        indent=2
    )


# =========================================================
# FINAL DIAGNOSTIC
# =========================================================

print("=" * 60)

print(
    "GOALINS HIGHLIGHTS RESULT"
)

print("=" * 60)

print(
    "YouTube search.list calls: 0"
)

print(
    f"Channel videos inspected: "
    f"{len(channel_videos)}"
)

print(
    f"Target matches: "
    f"{len(target_matches)}"
)

print(
    f"New videos matched: "
    f"{len(new_highlights)}"
)

print(
    f"Total saved: "
    f"{len(combined)}"
)

print(
    "Source: Official beIN SPORTS channel"
)

print(
    "Arabic titles supported."

)

print(
    "Gaming videos rejected."
)

print(
    "Embeddable videos only."
)

print("=" * 60)
