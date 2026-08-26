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

# Highlightly direct API
API_URL = "https://soccer.highlightly.net/highlights"

LOOKBACK_DAYS = 7

# Highlightly maximum for /highlights is 40
API_LIMIT = 40

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

]


# =========================================================
# NORMALIZE
# =========================================================

def normalize(text):

    text = str(text or "").lower()

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

        normalized_word = normalize(word)

        if normalized_word in value:

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


    # Exact match

    if expected == actual:

        return True


    # One contains the other

    if (
        expected in actual
        or actual in expected
    ):

        return True


    # Token matching

    expected_tokens = {

        token

        for token in expected.split()

        if len(token) >= 4

    }


    actual_tokens = {

        token

        for token in actual.split()

        if len(token) >= 4

    }


    if not expected_tokens:

        return False


    common = (
        expected_tokens
        & actual_tokens
    )


    return len(common) >= 1


# =========================================================
# HIGHLIGHT MATCHING
# =========================================================

def highlight_matches_fixture(
    video,
    fixture
):

    video_match = video.get(
        "match",
        {}
    )


    if not isinstance(
        video_match,
        dict
    ):

        return False


    # -----------------------------------------------------
    # Highlightly home team
    # -----------------------------------------------------

    home_team = video_match.get(
        "homeTeam",
        {}
    )


    if not isinstance(
        home_team,
        dict
    ):

        home_team = {}


    video_home = (

        home_team.get(
            "name"
        )

        or home_team.get(
            "displayName"
        )

        or ""

    )


    # -----------------------------------------------------
    # Highlightly away team
    # -----------------------------------------------------

    away_team = video_match.get(
        "awayTeam",
        {}
    )


    if not isinstance(
        away_team,
        dict
    ):

        away_team = {}


    video_away = (

        away_team.get(
            "name"
        )

        or away_team.get(
            "displayName"
        )

        or ""

    )


    fixture_home = fixture[
        "home"
    ]

    fixture_away = fixture[
        "away"
    ]


    print(
        "Highlightly match:"
    )

    print(
        f"  {video_home} vs {video_away}"
    )

    print(
        "GOALINS match:"
    )

    print(
        f"  {fixture_home} vs {fixture_away}"
    )


    return (

        team_name_match(
            fixture_home,
            video_home
        )

        and

        team_name_match(
            fixture_away,
            video_away
        )

    )


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

# Algeria is UTC+1
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


    # -----------------------------------------------------
    # LEAGUE
    # -----------------------------------------------------

    if league not in ALLOWED_LEAGUES:

        continue


    # -----------------------------------------------------
    # FINISHED
    # -----------------------------------------------------

    if not is_finished(
        match
    ):

        continue


    # -----------------------------------------------------
    # DATE
    # -----------------------------------------------------

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
# DATES
# =========================================================

dates = sorted({

    match["date"]

    for match in target_matches

})


print(
    f"Dates to search: "
    f"{len(dates)}"
)


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


    except Exception as error:

        print(
            "WARNING: Could not read old highlights:",
            error
        )

        old_highlights = []


old_ids = {

    str(
        item.get(
            "highlight_id"
        )
    )

    for item in old_highlights

    if isinstance(
        item,
        dict
    )

    and item.get(
        "highlight_id"
    )

}


# =========================================================
# HEADERS
# =========================================================
#
# IMPORTANT:
# We are using Highlightly DIRECT API:
#
# https://soccer.highlightly.net
#
# Therefore x-rapidapi-host is NOT required.
#
# x-rapidapi-host is only required when using RapidAPI.
#
# =========================================================

headers = {

    "x-rapidapi-key":
        API_KEY,

    "Accept":
        "application/json"

}


# =========================================================
# FETCH HIGHLIGHTS
# =========================================================

def fetch_highlights(
    date
):

    params = {

        "date":
            date,

        "timezone":
            "Europe/Algiers",

        "limit":
            API_LIMIT,

        "offset":
            0

    }


    response = requests.get(

        API_URL,

        headers=headers,

        params=params,

        timeout=30

    )


    print(
        "Request URL:",
        response.url
    )

    print(
        "HTTP:",
        response.status_code
    )


    # -----------------------------------------------------
    # ERROR DETAILS
    # -----------------------------------------------------

    if response.status_code != 200:

        try:

            print(
                "API response:",
                response.text[:1000]
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


for date in dates:

    print("=" * 60)

    print(
        f"Searching Highlightly: "
        f"{date}"
    )

    print("=" * 60)


    try:

        videos = fetch_highlights(
            date
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


    date_matches = [

        match

        for match in target_matches

        if match["date"] == date

    ]


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


        # =================================================
        # MATCH THE VIDEO TO REAL FIXTURE
        # =================================================

        selected_match = None


        for fixture in date_matches:

            if highlight_matches_fixture(
                video,
                fixture
            ):

                selected_match = fixture

                break


        # -------------------------------------------------
        # NO MATCH
        # -------------------------------------------------

        if not selected_match:

            print(
                "REJECTED: fixture mismatch"
            )

            print(
                "Title:",
                title
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
            f"{selected_match['home']} "
            f"vs "
            f"{selected_match['away']}"
        )

        print(
            "Title:",
            title
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
                selected_match[
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
                selected_match[
                    "date"
                ],

            "league":
                selected_match[
                    "league"
                ],

            "home":
                selected_match[
                    "home"
                ],

            "away":
                selected_match[
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

    if not isinstance(
        item,
        dict
    ):

        continue


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
    f"Dates searched: "
    f"{len(dates)}"
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
