import json
import os
import re
import requests

from datetime import datetime, timezone, timedelta


# =========================================================
# GOALINS — HIGHLIGHTLY HIGHLIGHTS ENGINE
# =========================================================

API_KEY = os.environ.get("HIGHLIGHTLY_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "HIGHLIGHTLY_API_KEY is missing"
    )


MATCHES_FILE = "data/matches.json"
OUTPUT_FILE = "data/highlights.json"

API_URL = (
    "https://soccer.highlightly.net/highlights"
)

LOOKBACK_DAYS = 7
MAX_HIGHLIGHTS = 50


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
    "virtual",
]


# =========================================================
# NORMALIZE
# =========================================================

def normalize(text):

    text = str(text or "").lower()

    # Remove accents that can cause small differences
    replacements = {
        "á": "a",
        "à": "a",
        "â": "a",
        "ä": "a",
        "ã": "a",
        "å": "a",
        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",
        "í": "i",
        "ì": "i",
        "î": "i",
        "ï": "i",
        "ó": "o",
        "ò": "o",
        "ô": "o",
        "ö": "o",
        "õ": "o",
        "ú": "u",
        "ù": "u",
        "û": "u",
        "ü": "u",
        "ý": "y",
        "ñ": "n",
        "ø": "o",
        "ł": "l",
        "č": "c",
        "ć": "c",
        "š": "s",
        "ž": "z",
        "đ": "d",
        "ğ": "g",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(
        r"[^a-z0-9\u0600-\u06ff]+",
        " ",
        text
    )

    return " ".join(
        text.split()
    )


# =========================================================
# GAMING DETECTION
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


def get_home(match):

    home = match.get(
        "home",
        {}
    )

    if isinstance(
        home,
        dict
    ):

        return str(
            home.get(
                "name",
                ""
            )
        ).strip()

    return str(
        home or ""
    ).strip()


def get_away(match):

    away = match.get(
        "away",
        {}
    )

    if isinstance(
        away,
        dict
    ):

        return str(
            away.get(
                "name",
                ""
            )
        ).strip()

    return str(
        away or ""
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


# =========================================================
# FINISHED
# =========================================================

def is_finished(match):

    return get_status(match) in {

        "FT",
        "AET",
        "PEN"

    }


# =========================================================
# TEAM NAME MATCHING
# =========================================================

def team_name_match(
    expected,
    actual
):

    expected = normalize(
        expected
    )

    actual = normalize(
        actual
    )

    if not expected or not actual:

        return False


    # Exact

    if expected == actual:

        return True


    # Full containment

    if (
        expected in actual
        or actual in expected
    ):

        return True


    expected_tokens = {

        token

        for token in expected.split()

        if len(token) >= 3

    }


    actual_tokens = {

        token

        for token in actual.split()

        if len(token) >= 3

    }


    if not expected_tokens:

        return False


    common = (
        expected_tokens
        & actual_tokens
    )


    # Require at least one meaningful
    # common token.

    return len(common) >= 1


# =========================================================
# GET HIGHLIGHT TEAM NAMES
# =========================================================

def get_video_teams(video):

    video_match = video.get(
        "match",
        {}
    )

    if not isinstance(
        video_match,
        dict
    ):

        return "", ""


    home_team = video_match.get(
        "homeTeam",
        {}
    )

    away_team = video_match.get(
        "awayTeam",
        {}
    )


    if not isinstance(
        home_team,
        dict
    ):

        home_team = {}


    if not isinstance(
        away_team,
        dict
    ):

        away_team = {}


    video_home = (

        home_team.get(
            "name"
        )

        or home_team.get(
            "displayName"
        )

        or ""

    )


    video_away = (

        away_team.get(
            "name"
        )

        or away_team.get(
            "displayName"
        )

        or ""

    )


    return (
        str(video_home).strip(),
        str(video_away).strip()
    )


# =========================================================
# MATCH VIDEO TO FIXTURE
# =========================================================

def highlight_matches_fixture(
    video,
    fixture
):

    video_home, video_away = (
        get_video_teams(video)
    )


    fixture_home = fixture[
        "home"
    ]

    fixture_away = fixture[
        "away"
    ]


    # -----------------------------------------------------
    # FIRST: USE HIGHLIGHTLY MATCH DATA
    # -----------------------------------------------------

    if video_home and video_away:

        home_ok = team_name_match(
            fixture_home,
            video_home
        )

        away_ok = team_name_match(
            fixture_away,
            video_away
        )


        if home_ok and away_ok:

            print(
                "MATCH VERIFIED BY API MATCH DATA:"
            )

            print(
                f"  Highlightly: "
                f"{video_home} vs {video_away}"
            )

            print(
                f"  GOALINS: "
                f"{fixture_home} vs {fixture_away}"
            )

            return True


    # -----------------------------------------------------
    # SECOND: CHECK TITLE
    # -----------------------------------------------------

    title = str(
        video.get(
            "title",
            ""
        )
    )


    description = str(
        video.get(
            "description",
            ""
        )
    )


    combined_text = (
        title
        + " "
        + description
    )


    home_ok = team_name_match(
        fixture_home,
        combined_text
    )

    away_ok = team_name_match(
        fixture_away,
        combined_text
    )


    if home_ok and away_ok:

        print(
            "MATCH VERIFIED BY TITLE:"
        )

        print(
            f"  GOALINS: "
            f"{fixture_home} vs {fixture_away}"
        )

        print(
            f"  Title: {title}"
        )

        return True


    return False


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
    "GOALINS - HIGHLIGHTLY HIGHLIGHTS ENGINE"
)

print("=" * 60)

print(
    f"Total matches in matches.json: "
    f"{len(matches)}"
)


# =========================================================
# ALGERIA DATE
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
    f"Searching from: {start_date}"
)

print(
    f"Searching to: {today}"
)


# =========================================================
# TARGET MATCHES
# =========================================================

target_matches = []


for match in matches:

    league = get_league(
        match
    )

    match_date = get_date(
        match
    )

    home = get_home(
        match
    )

    away = get_away(
        match
    )


    if league not in ALLOWED_LEAGUES:

        continue


    if not is_finished(
        match
    ):

        continue


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


# =========================================================
# DIAGNOSTIC
# =========================================================

print("-" * 60)

print(
    f"Finished allowed matches: "
    f"{len(target_matches)}"
)

print("-" * 60)

print(
    "TARGET MATCHES:"
)


for match in target_matches:

    print(

        f"  {match['date']} | "
        f"{match['league']} | "
        f"{match['home']} vs "
        f"{match['away']}"

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
# HEADERS
# =========================================================

headers = {

    "x-rapidapi-key":
        API_KEY,

    "x-rapidapi-host":
        "football-highlights-api.p.rapidapi.com",

    "Accept":
        "application/json"

}


# =========================================================
# API REQUEST
# =========================================================

def fetch_highlights(
    fixture
):

    params = {

        "date":
            fixture["date"],

        "homeTeamName":
            fixture["home"],

        "awayTeamName":
            fixture["away"],

        "limit":
            40,

        "offset":
            0

    }


    print(
        "Request:",
        fixture["home"],
        "vs",
        fixture["away"]
    )


    response = requests.get(

        API_URL,

        headers=headers,

        params=params,

        timeout=30

    )


    print(
        "HTTP:",
        response.status_code
    )


    if response.status_code != 200:

        try:

            print(
                "API response:",
                response.text[:500]
            )

        except Exception:

            pass


        response.raise_for_status()


    data = response.json()


    if isinstance(
        data,
        dict
    ):

        return data.get(
            "data",
            []
        )


    if isinstance(
        data,
        list
    ):

        return data


    return []


# =========================================================
# SEARCH
# =========================================================

new_highlights = []


searched_fixtures = 0


for fixture in target_matches:

    if len(
        new_highlights
    ) >= MAX_HIGHLIGHTS:

        break


    searched_fixtures += 1


    print("=" * 60)

    print(
        f"Searching Highlightly:"
    )

    print(
        f"{fixture['date']} | "
        f"{fixture['league']} | "
        f"{fixture['home']} vs "
        f"{fixture['away']}"
    )

    print("=" * 60)


    try:

        videos = fetch_highlights(
            fixture
        )

    except Exception as error:

        print(
            "Highlightly ERROR:",
            error
        )

        continue


    print(
        f"Videos returned: "
        f"{len(videos)}"
    )


    # =====================================================
    # VIDEOS
    # =====================================================

    for video in videos:

        if not isinstance(
            video,
            dict
        ):

            continue


        video_id = video.get(
            "id"
        )


        if not video_id:

            continue


        video_id = str(
            video_id
        )


        if video_id in old_ids:

            print(
                "Already saved:",
                video_id
            )

            continue


        # -------------------------------------------------
        # BASIC DATA
        # -------------------------------------------------

        title = str(
            video.get(
                "title",
                ""
            )
        )


        description = str(
            video.get(
                "description",
                ""
            )
        )


        source = str(
            video.get(
                "source",
                ""
            )
        )


        channel = str(
            video.get(
                "channel",
                ""
            )
        )


        video_type = str(
            video.get(
                "type",
                ""
            )
        ).upper()


        embed_url = video.get(
            "embedUrl"
        )


        thumbnail = video.get(
            "imgUrl"
        )


        original_url = video.get(
            "url"
        )


        # -------------------------------------------------
        # VERIFIED ONLY
        # -------------------------------------------------

        if video_type != "VERIFIED":

            print(
                "REJECTED non-VERIFIED:",
                title
            )

            continue


        # -------------------------------------------------
        # EMBED REQUIRED
        # -------------------------------------------------

        if not embed_url:

            print(
                "REJECTED no embedUrl:",
                title
            )

            continue


        # -------------------------------------------------
        # GAMING FILTER
        # -------------------------------------------------

        searchable = " ".join([

            title,
            description,
            source,
            channel,

        ])


        if is_gaming(
            searchable
        ):

            print(
                "REJECTED GAMING:",
                title
            )

            continue


        # -------------------------------------------------
        # REAL FOOTBALL MATCH
        # -------------------------------------------------

        if not highlight_matches_fixture(
            video,
            fixture
        ):

            print(
                "REJECTED: fixture mismatch"
            )

            print(
                "Title:",
                title
            )

            video_home, video_away = (
                get_video_teams(video)
            )

            print(
                "Highlightly teams:",
                video_home,
                "vs",
                video_away
            )

            print(
                "GOALINS teams:",
                fixture["home"],
                "vs",
                fixture["away"]
            )

            continue


        # =================================================
        # SUCCESS
        # =================================================

        print(
            "=============================================="
        )

        print(
            "SELECTED REAL FOOTBALL HIGHLIGHT"
        )

        print(
            f"{fixture['home']} "
            f"vs "
            f"{fixture['away']}"
        )

        print(
            "Title:",
            title
        )

        print(
            "Source:",
            source
        )

        print(
            "Embed:",
            embed_url
        )

        print(
            "=============================================="
        )


        item = {

            "highlight_id":
                video_id,

            "fixture_id":
                fixture[
                    "fixture_id"
                ],

            "title":
                title,

            "description":
                description,

            "thumbnail":
                thumbnail,

            "embed":
                embed_url,

            "embed_url":
                embed_url,

            "url":
                original_url,

            "source":
                source,

            "channel":
                channel,

            "type":
                "VERIFIED",

            "date":
                fixture[
                    "date"
                ],

            "league":
                fixture[
                    "league"
                ],

            "home":
                fixture[
                    "home"
                ],

            "away":
                fixture[
                    "away"
                ],

        }


        new_highlights.append(
            item
        )


        old_ids.add(
            video_id
        )


        if len(
            new_highlights
        ) >= MAX_HIGHLIGHTS:

            break


# =========================================================
# MERGE
# =========================================================

combined = []

seen = set()


for item in (

    new_highlights
    + old_highlights

):

    item_id = str(
        item.get(
            "highlight_id",
            ""
        )
    )


    if not item_id:

        continue


    if item_id in seen:

        continue


    seen.add(
        item_id
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
            "title",
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
        "Highlightly",

    "type":
        "VERIFIED",

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
    f"GOALINS: "
    f"{len(combined)} real football highlights saved."
)

print(
    f"New videos: "
    f"{len(new_highlights)}"
)

print(
    f"Fixtures searched: "
    f"{searched_fixtures}"
)

print(
    f"Target matches: "
    f"{len(target_matches)}"
)

print(
    "Source: Highlightly"
)

print(
    "Type: VERIFIED only"
)

print(
    "Gaming videos rejected automatically."
)

print("=" * 60)
