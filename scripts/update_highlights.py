import json
import os
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests


# =========================================================
# GOALINS — YOUTUBE HIGHLIGHTS ENGINE
# =========================================================

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY")

if not YOUTUBE_API_KEY:
    raise RuntimeError("YOUTUBE_API_KEY is missing")

if not API_FOOTBALL_KEY:
    raise RuntimeError("API_FOOTBALL_KEY is missing")


MATCHES_FILE = "data/matches.json"
OUTPUT_FILE = "data/highlights.json"

API_FOOTBALL_URL = (
    "https://v3.football.api-sports.io/fixtures"
)

YOUTUBE_URL = (
    "https://www.googleapis.com/youtube/v3/search"
)

LOOKBACK_DAYS = 7
MAX_HIGHLIGHTS = 50

# مهم حتى لا نستهلك YouTube quota بسرعة
MAX_YOUTUBE_SEARCHES_PER_RUN = 4

LOCAL_TZ = ZoneInfo("Africa/Algiers")


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
# HELPERS
# =========================================================

def normalize_text(value):

    text = unicodedata.normalize(
        "NFKD",
        str(value)
    )

    text = "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )

    text = text.lower()

    text = re.sub(
        r"[^a-z0-9\u0600-\u06ff]+",
        " ",
        text
    )

    return " ".join(
        text.split()
    )


def team_in_title(team, title):

    team = normalize_text(team)
    title = normalize_text(title)

    if not team:
        return False

    if team in title:
        return True

    team_words = [
        word
        for word in team.split()
        if len(word) >= 3
    ]

    title_words = set(
        title.split()
    )

    if not team_words:
        return False

    if len(team_words) == 1:
        return team_words[0] in title_words

    found = sum(
        1
        for word in team_words
        if word in title_words
    )

    return found >= max(
        1,
        (len(team_words) + 1) // 2
    )


def get_league(match):

    league = match.get("league")

    if isinstance(league, dict):
        return league

    return {}


def get_teams(match):

    home = match.get("home")
    away = match.get("away")

    if not isinstance(home, dict):
        home = {}

    if not isinstance(away, dict):
        away = {}

    return home, away


def get_status(match):

    status = match.get("status")

    if isinstance(status, dict):

        return str(
            status.get("short") or ""
        ).upper()

    return str(
        status or ""
    ).upper()


def get_date(match):

    value = match.get("date") or ""

    return str(value)[:10]


def load_json(path, default):

    if not os.path.exists(path):
        return default

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception as error:

        print(
            f"Could not read {path}:",
            error
        )

        return default


def save_json(path, data):

    os.makedirs(
        os.path.dirname(path),
        exist_ok=True
    )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# API-FOOTBALL
# =========================================================

def convert_fixture(item):

    fixture = item.get(
        "fixture",
        {}
    )

    league = item.get(
        "league",
        {}
    )

    teams = item.get(
        "teams",
        {}
    )

    goals = item.get(
        "goals",
        {}
    )

    status = fixture.get(
        "status",
        {}
    )

    return {

        "fixture_id":
            fixture.get("id"),

        "date":
            fixture.get("date"),

        "timestamp":
            fixture.get("timestamp"),

        "status":
            status.get("short"),

        "status_long":
            status.get("long"),

        "league": {

            "id":
                league.get("id"),

            "name":
                league.get("name"),

            "country":
                league.get("country"),

            "logo":
                league.get("logo"),

            "flag":
                league.get("flag"),

            "round":
                league.get("round")
        },

        "home": {

            "id":
                teams.get(
                    "home",
                    {}
                ).get("id"),

            "name":
                teams.get(
                    "home",
                    {}
                ).get("name"),

            "logo":
                teams.get(
                    "home",
                    {}
                ).get("logo")
        },

        "away": {

            "id":
                teams.get(
                    "away",
                    {}
                ).get("id"),

            "name":
                teams.get(
                    "away",
                    {}
                ).get("name"),

            "logo":
                teams.get(
                    "away",
                    {}
                ).get("logo")
        },

        "goals": {

            "home":
                goals.get("home"),

            "away":
                goals.get("away")
        }
    }


def fetch_recent_fixtures():

    today = datetime.now(
        LOCAL_TZ
    ).date()

    start_date = (
        today
        - timedelta(
            days=LOOKBACK_DAYS
        )
    )

    params = {

        "from":
            start_date.isoformat(),

        "to":
            today.isoformat(),

        "timezone":
            "Africa/Algiers"
    }

    headers = {

        "x-apisports-key":
            API_FOOTBALL_KEY,

        "Accept":
            "application/json"
    }

    print(
        "======================================"
    )

    print(
        "API-FOOTBALL REFRESH"
    )

    print(
        f"From: {start_date}"
    )

    print(
        f"To:   {today}"
    )

    print(
        "======================================"
    )

    response = requests.get(
        API_FOOTBALL_URL,
        params=params,
        headers=headers,
        timeout=45
    )

    response.raise_for_status()

    data = response.json()

    if data.get("errors"):

        raise RuntimeError(
            str(
                data["errors"]
            )
        )

    fixtures = [

        convert_fixture(item)

        for item in data.get(
            "response",
            []
        )
    ]

    print(
        f"API-Football fixtures: {len(fixtures)}"
    )

    return fixtures


# =========================================================
# LOAD EXISTING HIGHLIGHTS
# =========================================================

def load_existing_highlights():

    data = load_json(
        OUTPUT_FILE,
        {}
    )

    if isinstance(data, dict):

        highlights = data.get(
            "highlights",
            []
        )

    elif isinstance(data, list):

        highlights = data

    else:

        highlights = []

    return (
        highlights
        if isinstance(highlights, list)
        else []
    )


# =========================================================
# BUILD RECENT ALLOWED MATCHES
# =========================================================

def get_recent_allowed_matches(fixtures):

    today = datetime.now(
        LOCAL_TZ
    ).date()

    minimum_date = (
        today
        - timedelta(
            days=LOOKBACK_DAYS
        )
    )

    unique = {}

    for match in fixtures:

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

        status_long = str(
            match.get(
                "status_long"
            ) or ""
        ).lower()

        finished = (

            status in (
                "FT",
                "AET",
                "PEN"
            )

            or

            "finished" in status_long
        )

        if not finished:
            continue

        match_date = get_date(
            match
        )

        try:

            date_object = datetime.strptime(
                match_date,
                "%Y-%m-%d"
            ).date()

        except Exception:

            continue

        if not (
            minimum_date
            <= date_object
            <= today
        ):

            continue

        fixture_id = match.get(
            "fixture_id"
        )

        if not fixture_id:
            continue

        unique[
            int(fixture_id)
        ] = match

    matches = list(
        unique.values()
    )

    matches.sort(
        key=lambda item: (
            get_date(item),
            str(
                item.get("date") or ""
            )
        ),
        reverse=True
    )

    return matches


# =========================================================
# YOUTUBE SEARCH
# =========================================================

def search_youtube(
    home,
    away,
    match_date
):

    query = (
        f'"{home}" "{away}" highlights'
    )

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

        "publishedAfter":
            f"{match_date}T00:00:00Z",

        "key":
            YOUTUBE_API_KEY
    }

    response = requests.get(
        YOUTUBE_URL,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if data.get("error"):

        raise RuntimeError(
            str(
                data["error"]
            )
        )

    return data.get(
        "items",
        []
    )


# =========================================================
# SELECT VIDEO
# =========================================================

def select_video(
    videos,
    home,
    away
):

    for video in videos:

        video_id = (
            video
            .get("id", {})
            .get("videoId")
        )

        if not video_id:
            continue

        snippet = video.get(
            "snippet",
            {}
        )

        title = snippet.get(
            "title",
            ""
        )

        normalized = normalize_text(
            title
        )

        # No Shorts
        if "shorts" in normalized:
            continue

        if not team_in_title(
            home,
            title
        ):
            continue

        if not team_in_title(
            away,
            title
        ):
            continue

        thumbnails = snippet.get(
            "thumbnails",
            {}
        )

        thumbnail = (

            thumbnails
            .get("high", {})
            .get("url")

            or

            thumbnails
            .get("medium", {})
            .get("url")

            or

            thumbnails
            .get("default", {})
            .get("url")
        )

        return {

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

            "embed":
                (
                    "https://www.youtube.com/embed/"
                    + video_id
                ),

            "youtube_url":
                (
                    "https://www.youtube.com/watch?v="
                    + video_id
                )
        }

    return None


# =========================================================
# MAIN
# =========================================================

def main():

    existing = (
        load_existing_highlights()
    )

    existing_fixtures = {

        item.get("fixture_id")

        for item in existing

        if item.get("fixture_id")
    }

    try:

        fixtures = (
            fetch_recent_fixtures()
        )

    except Exception as error:

        print(
            "API-Football ERROR:",
            error
        )

        # Fallback to local matches
        local = load_json(
            MATCHES_FILE,
            {}
        )

        if isinstance(local, dict):

            fixtures = local.get(
                "matches",
                []
            )

        else:

            fixtures = local

    matches = (
        get_recent_allowed_matches(
            fixtures
        )
    )

    print(
        "======================================"
    )

    print(
        "GOALINS HIGHLIGHTS DIAGNOSTIC"
    )

    print(
        f"Recent allowed finished matches: "
        f"{len(matches)}"
    )

    print(
        "======================================"
    )

    for match in matches:

        league = get_league(
            match
        )

        home, away = get_teams(
            match
        )

        print(
            f"{get_date(match)} | "
            f"{league.get('name', '')} | "
            f"{home.get('name', '')} vs "
            f"{away.get('name', '')}"
        )

    print(
        "======================================"
    )

    new_highlights = []

    searches = 0

    for match in matches:

        if searches >= (
            MAX_YOUTUBE_SEARCHES_PER_RUN
        ):
            break

        fixture_id = match.get(
            "fixture_id"
        )

        if fixture_id in existing_fixtures:
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

        print(
            "--------------------------------------"
        )

        print(
            f"Searching YouTube: "
            f"{home_name} vs {away_name}"
        )

        searches += 1

        try:

            videos = search_youtube(
                home_name,
                away_name,
                get_date(match)
            )

            selected = select_video(
                videos,
                home_name,
                away_name
            )

        except Exception as error:

            print(
                "YouTube ERROR:",
                error
            )

            continue

        if not selected:

            print(
                "No matching video found."
            )

            continue

        league = get_league(
            match
        )

        try:

            league_id = int(
                league.get("id")
            )

        except Exception:

            league_id = None

        item = {

            "fixture_id":
                fixture_id,

            "video_id":
                selected["video_id"],

            "title":
                selected["title"],

            "thumbnail":
                selected["thumbnail"],

            "channel":
                selected["channel"],

            "published_at":
                selected["published_at"],

            "date":
                get_date(match),

            "league_id":
                league_id,

            "league":
                league.get(
                    "name",
                    ""
                ),

            "league_key":
                ALLOWED_LEAGUES.get(
                    league_id
                ),

            "home":
                home_name,

            "away":
                away_name,

            "embed":
                selected["embed"],

            "youtube_url":
                selected["youtube_url"]
        }

        new_highlights.append(
            item
        )

        existing_fixtures.add(
            fixture_id
        )

        print(
            "SELECTED:",
            selected["title"]
        )

    # =====================================================
    # MERGE
    # =====================================================

    combined = (
        new_highlights
        + existing
    )

    final = []

    seen_fixtures = set()
    seen_videos = set()

    for item in combined:

        fixture_id = item.get(
            "fixture_id"
        )

        video_id = item.get(
            "video_id"
        )

        if (
            fixture_id
            and fixture_id in seen_fixtures
        ):
            continue

        if (
            video_id
            and video_id in seen_videos
        ):
            continue

        final.append(
            item
        )

        if fixture_id:
            seen_fixtures.add(
                fixture_id
            )

        if video_id:
            seen_videos.add(
                video_id
            )

    final.sort(
        key=lambda item: (
            str(
                item.get("date")
                or ""
            ),
            str(
                item.get("published_at")
                or ""
            )
        ),
        reverse=True
    )

    final = final[
        :MAX_HIGHLIGHTS
    ]

    # =====================================================
    # SAVE
    # =====================================================

    output = {

        "updated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "count":
            len(final),

        "highlights":
            final
    }

    save_json(
        OUTPUT_FILE,
        output
    )

    print(
        "======================================"
    )

    print(
        f"GOALINS: {len(final)} highlights saved."
    )

    print(
        f"New videos: {len(new_highlights)}"
    )

    print(
        f"YouTube searches this run: {searches}"
    )

    print(
        "======================================"
    )


if __name__ == "__main__":

    main()
