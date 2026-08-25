import json
import os
import re
import requests

from datetime import (
    datetime,
    timezone,
    timedelta
)


# =========================================================
# GOALINS — YOUTUBE HIGHLIGHTS ENGINE
# =========================================================

API_KEY = os.environ.get("YOUTUBE_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "YOUTUBE_API_KEY is missing"
    )


MATCHES_FILE = "data/matches.json"
OUTPUT_FILE = "data/highlights.json"

SEARCH_URL = (
    "https://www.googleapis.com/youtube/v3/search"
)

VIDEOS_URL = (
    "https://www.googleapis.com/youtube/v3/videos"
)


LOOKBACK_DAYS = 7
MAX_HIGHLIGHTS = 50


# =========================================================
# ALLOWED LEAGUES
# =========================================================

ALLOWED_LEAGUES = {

    39: "premier-league",
    140: "la-liga",
    61: "ligue-1",
    135: "serie-a",
    88: "eredivisie",
    144: "jupiler-pro-league",
    94: "primeira-liga",
    78: "bundesliga",

    2: "champions-league",
    3: "europa-league",
    848: "conference-league",

    1: "world-cup",
    4: "euro",
    6: "afcon",
    9: "copa-america",

}


# =========================================================
# BLOCKED WORDS
# =========================================================
#
# These words strongly indicate FIFA/PES/eFootball/
# PlayStation/gameplay rather than a real football match.
# =========================================================

BLOCKED_WORDS = {

    "fifa",
    "fifa 23",
    "fifa 24",
    "fifa 25",
    "fifa 26",

    "ea fc",
    "fc 24",
    "fc 25",
    "fc 26",

    "efootball",
    "e football",

    "pes",
    "pes 2021",
    "pes 2022",
    "pes 2023",
    "pes 2024",
    "pes 2025",
    "pes 2026",

    "playstation",
    "ps4",
    "ps5",

    "xbox",

    "gameplay",
    "game play",

    "career mode",
    "master league",

    "virtual",
    "simulation",
    "simulated",

    "gaming",
    "video game",
    "videogame",

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


print("=" * 50)
print("GOALINS HIGHLIGHTS ENGINE")
print("=" * 50)
print(
    f"Total matches in matches.json: "
    f"{len(matches)}"
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

    text = str(
        text or ""
    ).lower()

    text = re.sub(
        r"[^a-z0-9\u0600-\u06ff]+",
        " ",
        text
    )

    return " ".join(
        text.split()
    )


def contains_blocked_word(text):

    normalized = normalize_text(
        text
    )

    for word in BLOCKED_WORDS:

        blocked = normalize_text(
            word
        )

        if not blocked:
            continue

        if blocked in normalized:

            return True

    return False


def team_in_title(
    team,
    title
):

    team_normalized = normalize_text(
        team
    )

    title_normalized = normalize_text(
        title
    )

    if not team_normalized:
        return False

    if team_normalized in title_normalized:
        return True

    words = [
        word
        for word in team_normalized.split()
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


# =========================================================
# MATCH FILTER
# =========================================================

today = datetime.now(
    timezone.utc
).date()

minimum_date = (
    today
    - timedelta(
        days=LOOKBACK_DAYS
    )
)


finished_matches = []


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


    if league_id not in ALLOWED_LEAGUES:

        continue


    status = get_status(
        match
    )

    if status not in (
        "FT",
        "AET",
        "PEN"
    ):

        continue


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


    home, away = get_teams(
        match
    )


    home_name = (
        home.get("name")
        or ""
    )

    away_name = (
        away.get("name")
        or ""
    )


    if not home_name or not away_name:

        continue


    fixture_id = (
        match.get("fixture_id")
        or match
        .get("fixture", {})
        .get("id")
    )


    finished_matches.append({

        "fixture_id":
            fixture_id,

        "date":
            match_date,

        "league_id":
            league_id,

        "league":
            (
                league.get("name")
                or ALLOWED_LEAGUES[
                    league_id
                ]
            ),

        "league_key":
            ALLOWED_LEAGUES[
                league_id
            ],

        "home":
            home_name,

        "away":
            away_name

    })


# =========================================================
# SORT MATCHES
# =========================================================

finished_matches.sort(
    key=lambda item: (
        item.get("date", ""),
        item.get("fixture_id") or 0
    ),
    reverse=True
)


print(
    f"Finished allowed matches in "
    f"last {LOOKBACK_DAYS} days: "
    f"{len(finished_matches)}"
)


for match in finished_matches:

    print(
        f"  {match['date']} | "
        f"{match['league']} | "
        f"{match['home']} vs "
        f"{match['away']}"
    )


# =========================================================
# YOUTUBE SEARCH
# =========================================================

def search_youtube(
    query,
    published_after=None
):

    params = {

        "part":
            "snippet",

        "q":
            query,

        "type":
            "video",

        "maxResults":
            10,

        "order":
            "relevance",

        "videoEmbeddable":
            "true",

        "videoSyndicated":
            "true",

        "videoDuration":
            "medium",

        "key":
            API_KEY

    }


    if published_after:

        params[
            "publishedAfter"
        ] = published_after


    response = requests.get(
        SEARCH_URL,
        params=params,
        timeout=30
    )


    response.raise_for_status()


    result = response.json()


    if result.get("error"):

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
# GET VIDEO DETAILS
# =========================================================

def get_video_details(
    video_ids
):

    if not video_ids:

        return {}


    params = {

        "part":
            "snippet,contentDetails,status",

        "id":
            ",".join(
                video_ids
            ),

        "key":
            API_KEY

    }


    response = requests.get(
        VIDEOS_URL,
        params=params,
        timeout=30
    )


    response.raise_for_status()


    result = response.json()


    if result.get("error"):

        raise RuntimeError(
            str(
                result["error"]
            )
        )


    details = {}


    for item in result.get(
        "items",
        []
    ):

        details[
            item.get("id")
        ] = item


    return details


# =========================================================
# SEARCH HIGHLIGHTS
# =========================================================

highlights = []

used_video_ids = set()
used_fixture_ids = set()


searches_done = 0


for match in finished_matches:

    if len(highlights) >= MAX_HIGHLIGHTS:

        break


    home_name = match["home"]
    away_name = match["away"]


    print("-" * 50)

    print(
        f"Searching YouTube: "
        f"{home_name} vs {away_name}"
    )


    query = (
        f'"{home_name}" '
        f'"{away_name}" '
        f"highlights football"
    )


    # Search from match date onward.
    published_after = (
        f"{match['date']}T00:00:00Z"
    )


    try:

        videos = search_youtube(
            query,
            published_after
        )

        searches_done += 1

    except Exception as e:

        print(
            "YouTube search error:",
            e
        )

        continue


    if not videos:

        print(
            "No YouTube results."
        )

        continue


    candidate_ids = []


    for video in videos:

        video_id = (
            video
            .get("id", {})
            .get("videoId")
        )

        if video_id:

            candidate_ids.append(
                video_id
            )


    try:

        video_details = get_video_details(
            candidate_ids
        )

    except Exception as e:

        print(
            "YouTube video details error:",
            e
        )

        continue


    selected = None


    for video in videos:

        video_id = (
            video
            .get("id", {})
            .get("videoId")
        )


        if not video_id:

            continue


        if video_id in used_video_ids:

            continue


        details = video_details.get(
            video_id
        )


        if not details:

            continue


        snippet = details.get(
            "snippet",
            {}
        )


        title = snippet.get(
            "title",
            ""
        )


        description = snippet.get(
            "description",
            ""
        )


        channel_title = snippet.get(
            "channelTitle",
            ""
        )


        # ---------------------------------------------
        # REJECT GAMING
        # ---------------------------------------------

        combined_text = (
            f"{title} "
            f"{description} "
            f"{channel_title}"
        )


        if contains_blocked_word(
            combined_text
        ):

            print(
                f"REJECTED GAMING: "
                f"{title}"
            )

            continue


        # ---------------------------------------------
        # YOUTUBE CATEGORY
        # ---------------------------------------------

        category_id = str(
            snippet.get(
                "categoryId",
                ""
            )
        )


        if category_id != "17":

            print(
                f"REJECTED NON-SPORTS "
                f"(category {category_id}): "
                f"{title}"
            )

            continue


        # ---------------------------------------------
        # TEAM CHECK
        # ---------------------------------------------

        home_ok = team_in_title(
            home_name,
            title
        )


        away_ok = team_in_title(
            away_name,
            title
        )


        if not home_ok or not away_ok:

            print(
                f"REJECTED TEAMS: "
                f"{title}"
            )

            continue


        # ---------------------------------------------
        # CHANNEL / TITLE QUALITY
        # ---------------------------------------------

        title_normalized = normalize_text(
            title
        )


        bad_generic_terms = [

            "prediction",
            "predictions",
            "preview",
            "reaction",
            "watch along",
            "watchalong",
            "live",
            "news",
            "transfer"

        ]


        if any(
            word in title_normalized
            for word in bad_generic_terms
        ):

            print(
                f"REJECTED NON-HIGHLIGHT: "
                f"{title}"
            )

            continue


        # ---------------------------------------------
        # THUMBNAIL
        # ---------------------------------------------

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


        # ---------------------------------------------
        # SELECT
        # ---------------------------------------------

        selected = {

            "fixture_id":
                match["fixture_id"],

            "video_id":
                video_id,

            "title":
                title,

            "thumbnail":
                thumbnail,

            "channel":
                channel_title,

            "published_at":
                snippet.get(
                    "publishedAt",
                    ""
                ),

            "youtube_category":
                category_id,

            "date":
                match["date"],

            "league_id":
                match["league_id"],

            "league":
                match["league"],

            "league_key":
                match["league_key"],

            "home":
                home_name,

            "away":
                away_name,

            "embed":
                (
                    "https://www.youtube-nocookie.com/"
                    f"embed/{video_id}"
                    "?rel=0"
                    "&modestbranding=1"
                    "&playsinline=1"
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
            f"SELECTED: "
            f"{selected['title']}"
        )


        highlights.append(
            selected
        )


        used_video_ids.add(
            selected["video_id"]
        )


        if selected["fixture_id"]:

            used_fixture_ids.add(
                selected["fixture_id"]
            )

    else:

        print(
            "No valid real-football video found."
        )


# =========================================================
# SORT
# =========================================================

highlights.sort(
    key=lambda item: (
        item.get("date", ""),
        item.get("published_at", "")
    ),
    reverse=True
)


highlights = highlights[
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
        len(highlights),

    "highlights":
        highlights

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


# =========================================================
# FINAL DIAGNOSTIC
# =========================================================

print("=" * 50)

print(
    f"GOALINS: "
    f"{len(highlights)} "
    f"real football highlights saved."
)

print(
    f"YouTube searches: "
    f"{searches_done}"
)

print(
    "Gaming videos rejected automatically."
)

print("=" * 50)
