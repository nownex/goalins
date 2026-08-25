import json
import os
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
# ALLOWED LEAGUES
# =========================================================

ALLOWED_LEAGUES = {

    39: "premier-league",
    140: "la-liga",
    61: "ligue-1",
    135: "serie-a",
    88: "eredivisie",
    144: "jupiler",
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
        or match.get("fixture", {}).get("date")
        or ""
    )

    return str(value)[:10]


def get_status(match):

    return str(
        match.get("status")
        or match.get("fixture", {})
        .get("status", {})
        .get("short", "")
    )


# =========================================================
# SEARCH YOUTUBE
# =========================================================

def search_youtube(query):

    params = {

        "part": "snippet",

        "q": query,

        "type": "video",

        "maxResults": 5,

        "order": "relevance",

        "videoEmbeddable": "true",

        "videoSyndicated": "true",

        "key": API_KEY

    }


    response = requests.get(
        YOUTUBE_SEARCH_URL,
        params=params,
        timeout=30
    )


    response.raise_for_status()


    return response.json().get(
        "items",
        []
    )


# =========================================================
# BUILD HIGHLIGHTS
# =========================================================

highlights = []


for match in matches:


    league = get_league(match)


    try:

        league_id = int(
            league.get("id")
        )

    except:

        continue


    # ---------------------------------------------
    # ONLY OUR ALLOWED LEAGUES
    # ---------------------------------------------

    if league_id not in ALLOWED_LEAGUES:

        continue


    status = get_status(match)


    # ---------------------------------------------
    # ONLY FINISHED MATCHES
    # ---------------------------------------------

    if status not in (
        "FT",
        "AET",
        "PEN"
    ):

        continue


    home, away = get_teams(match)


    home_name = (
        home.get("name")
        or "Home"
    )

    away_name = (
        away.get("name")
        or "Away"
    )


    match_date = get_date(
        match
    )


    league_name = (
        league.get("name")
        or "Football"
    )


    # ---------------------------------------------
    # SEARCH PHRASE
    # ---------------------------------------------

    query = (
        f"{home_name} "
        f"{away_name} "
        f"highlights"
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


    if not videos:

        continue


    # ---------------------------------------------
    # TAKE FIRST EMBEDDABLE RESULT
    # ---------------------------------------------

    selected = None


    for video in videos:

        video_id = (
            video
            .get("id", {})
            .get("videoId")
        )

        snippet = (
            video.get(
                "snippet",
                {}
            )
        )


        if not video_id:

            continue


        selected = {

            "video_id":
                video_id,

            "title":
                snippet.get(
                    "title",
                    f"{home_name} vs {away_name}"
                ),

            "thumbnail":
                (
                    snippet
                    .get("thumbnails", {})
                    .get("high", {})
                    .get("url")
                    or
                    snippet
                    .get("thumbnails", {})
                    .get("medium", {})
                    .get("url")
                ),

            "channel":
                snippet.get(
                    "channelTitle",
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
                f"https://www.youtube.com/embed/{video_id}"

        }

        break


    if selected:

        highlights.append(
            selected
        )


# =========================================================
# REMOVE DUPLICATES
# =========================================================

unique = {}

for item in highlights:

    key = item["video_id"]

    unique[key] = item


highlights = list(
    unique.values()
)


# =========================================================
# LIMIT
# =========================================================

highlights = highlights[:50]


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
    f"GOALINS: {len(highlights)} highlights saved."
)
