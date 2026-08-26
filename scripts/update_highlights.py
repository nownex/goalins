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

TIMEZONE = "Africa/Algiers"


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
    9: "copa-america"
}


# =========================================================
# GAMING / FAKE VIDEO FILTER
# =========================================================

FORBIDDEN_WORDS = {

    "fifa",
    "ea fc",
    "fc 26",
    "fc26",
    "fc 25",
    "fc25",
    "efootball",
    "pes",
    "pes 2026",
    "pes2026",
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
    "game"
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


print(
    "=================================================="
)

print(
    "GOALINS — HIGHLIGHTLY HIGHLIGHTS ENGINE"
)

print(
    "=================================================="
)

print(
    f"Total matches in matches.json: {len(matches)}"
)


# =========================================================
# HELPERS
# =========================================================

def normalize_text(text):

    text = str(text or "").lower()

    text = re.sub(
        r"[^a-z0-9\u0600-\u06ff]+",
        " ",
        text
    )

    return " ".join(
        text.split()
    )


def team_matches(
    team_name,
    text
):

    team = normalize_text(
        team_name
    )

    title = normalize_text(
        text
    )

    if not team:
        return False

    if team in title:
        return True

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

        if word in title

    )

    return found >= max(
        1,
        (len(words) + 1) // 2
    )


def is_gaming_video(text):

    normalized = normalize_text(
        text
    )

    for word in FORBIDDEN_WORDS:

        forbidden = normalize_text(
            word
        )

        if forbidden in normalized:
            return True

    return False


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


def get_match_date(match):

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

    status = match.get(
        "status"
    )

    if isinstance(
        status,
        dict
    ):

        short = status.get(
            "short"
        )

        if short:
            return str(short)

        return str(
            status.get(
                "description",
                ""
            )
        )

    fixture_status = (

        match
        .get("fixture", {})
        .get("status", {})

    )

    if isinstance(
        fixture_status,
        dict
    ):

        short = fixture_status.get(
            "short"
        )

        if short:
            return str(short)

        return str(
            fixture_status.get(
                "description",
                ""
            )
        )

    return str(
        status or ""
    )


def is_finished(match):

    status = get_status(
        match
    ).strip().lower()

    return status in {

        "ft",
        "aet",
        "pen",

        "finished",

        "finished after penalties",

        "finished after extra time"

    }


# =========================================================
# ALGERIA DATE
# =========================================================

# UTC+1 is used for Algeria.
# This avoids the previous UTC date problem.

algeria_now = (

    datetime.now(
        timezone.utc
    )

    + timedelta(
        hours=1
    )

)

today = algeria_now.date()

minimum_date = (

    today

    - timedelta(
        days=LOOKBACK_DAYS
    )

)


print(
    f"Algeria date: {today.isoformat()}"
)

print(
    f"Searching from: "
    f"{minimum_date.isoformat()}"
)

print(
    f"Searching to: "
    f"{today.isoformat()}"
)


# =========================================================
# BUILD TARGET MATCHES
# =========================================================

target_matches = []


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


    # -----------------------------------------------------
    # ALLOWED LEAGUE
    # -----------------------------------------------------

    if league_id not in ALLOWED_LEAGUES:
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

    match_date = get_match_date(
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


    if match_date_obj > today:
        continue


    # -----------------------------------------------------
    # TEAMS
    # -----------------------------------------------------

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

        match.get(
            "fixture_id"
        )

        or match.get(
            "fixture",
            {}
        ).get("id")

    )


    target_matches.append({

        "fixture_id":
            fixture_id,

        "date":
            match_date,

        "league_id":
            league_id,

        "league":
            league.get("name")
            or ALLOWED_LEAGUES[
                league_id
            ],

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
# REMOVE DUPLICATE FIXTURES
# =========================================================

unique_targets = {}

for match in target_matches:

    key = (

        match.get(
            "fixture_id"
        )

        or (

            match["date"],
            match["home"],
            match["away"]

        )

    )

    unique_targets[key] = match


target_matches = list(
    unique_targets.values()
)


# =========================================================
# SORT TARGET MATCHES
# =========================================================

target_matches.sort(

    key=lambda item: (

        item["date"],
        item["league"],
        item["home"]

    ),

    reverse=True

)


# =========================================================
# IMPORTANT DIAGNOSTIC
# =========================================================

print(
    "--------------------------------------------------"
)

print(
    f"Finished allowed matches: "
    f"{len(target_matches)}"
)

print(
    "--------------------------------------------------"
)

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


print(
    "--------------------------------------------------"
)


# =========================================================
# LOAD OLD HIGHLIGHTS
# =========================================================

existing = []


if os.path.exists(
    OUTPUT_FILE
):

    try:

        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            old = json.load(
                f
            )


        if isinstance(
            old,
            dict
        ):

            existing = old.get(
                "highlights",
                []
            )

        elif isinstance(
            old,
            list
        ):

            existing = old


    except Exception as error:

        print(
            "Could not load old highlights:",
            error
        )

        existing = []


existing_ids = {

    str(
        item.get(
            "highlight_id"
        )
    )

    for item in existing

    if item.get(
        "highlight_id"
    )

}


# =========================================================
# HIGHLIGHTLY API
# =========================================================

HEADERS = {

    "x-rapidapi-key":
        API_KEY

}


def get_highlights(
    date_string
):

    params = {

        "date":
            date_string,

        "timezone":
            TIMEZONE,

        "limit":
            40,

        "offset":
            0

    }


    response = requests.get(

        API_URL,

        params=params,

        headers=HEADERS,

        timeout=30

    )


    response.raise_for_status()


    payload = response.json()


    if isinstance(
        payload,
        dict
    ):

        return payload.get(
            "data",
            []
        )


    if isinstance(
        payload,
        list
    ):

        return payload


    return []


# =========================================================
# SEARCH DATES
# =========================================================

dates_to_search = sorted({

    match["date"]

    for match in target_matches

})


print(
    f"Dates to search: "
    f"{len(dates_to_search)}"
)


# =========================================================
# SEARCH HIGHLIGHTS
# =========================================================

new_highlights = []

searched_dates = set()


for date_string in dates_to_search:

    searched_dates.add(
        date_string
    )


    print(
        "=================================================="
    )

    print(
        f"Searching Highlightly: "
        f"{date_string}"
    )

    print(
        "=================================================="
    )


    try:

        day_highlights = get_highlights(
            date_string
        )


    except Exception as error:

        print(
            "Highlightly error:",
            error
        )

        continue


    print(
        f"Highlights returned: "
        f"{len(day_highlights)}"
    )


    # -----------------------------------------------------
    # TARGETS FOR THIS DATE
    # -----------------------------------------------------

    date_targets = [

        match

        for match in target_matches

        if match["date"] == date_string

    ]


    # -----------------------------------------------------
    # PROCESS VIDEOS
    # -----------------------------------------------------

    for item in day_highlights:

        if not isinstance(
            item,
            dict
        ):
            continue


        highlight_id = item.get(
            "id"
        )


        if not highlight_id:
            continue


        highlight_id = str(
            highlight_id
        )


        if highlight_id in existing_ids:
            continue


        # -------------------------------------------------
        # VERIFIED ONLY
        # -------------------------------------------------

        video_type = str(

            item.get(
                "type",
                ""
            )

        ).upper()


        if video_type != "VERIFIED":

            continue


        # -------------------------------------------------
        # EMBED URL
        # -------------------------------------------------

        embed_url = item.get(
            "embedUrl"
        )


        if not embed_url:

            continue


        # -------------------------------------------------
        # VIDEO DATA
        # -------------------------------------------------

        title = str(

            item.get(
                "title",
                ""
            )

        )


        description = str(

            item.get(
                "description",
                ""
            )

        )


        source = str(

            item.get(
                "source",
                ""
            )

        )


        channel = str(

            item.get(
                "channel",
                ""
            )

        )


        searchable_text = " ".join([

            title,
            description,
            source,
            channel

        ])


        # -------------------------------------------------
        # GAMING FILTER
        # -------------------------------------------------

        if is_gaming_video(
            searchable_text
        ):

            print(
                "REJECTED GAMING:",
                title
            )

            continue


        # -------------------------------------------------
        # MATCH VIDEO TO REAL MATCH
        # -------------------------------------------------

        selected_match = None


        for target in date_targets:

            home_ok = team_matches(

                target["home"],

                searchable_text

            )


            away_ok = team_matches(

                target["away"],

                searchable_text

            )


            if home_ok and away_ok:

                selected_match = target

                break


        if not selected_match:

            continue


        # -------------------------------------------------
        # THUMBNAIL
        # -------------------------------------------------

        thumbnail = item.get(
            "imgUrl"
        )


        # -------------------------------------------------
        # SAVE
        # -------------------------------------------------

        selected = {

            "highlight_id":
                highlight_id,

            "fixture_id":
                selected_match[
                    "fixture_id"
                ],

            "video_id":
                highlight_id,

            "type":
                "VERIFIED",

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

            "source":
                source,

            "channel":
                channel,

            "url":
                item.get(
                    "url"
                ),

            "published_at":
                item.get(
                    "publishedAt"
                )

                or item.get(
                    "createdAt"
                )

                or "",

            "date":
                selected_match[
                    "date"
                ],

            "league_id":
                selected_match[
                    "league_id"
                ],

            "league":
                selected_match[
                    "league"
                ],

            "league_key":
                selected_match[
                    "league_key"
                ],

            "home":
                selected_match[
                    "home"
                ],

            "away":
                selected_match[
                    "away"
                ]

        }


        print(
            "SELECTED:",
            selected_match["home"],
            "vs",
            selected_match["away"],
            "|",
            title
        )


        new_highlights.append(
            selected
        )


        existing_ids.add(
            highlight_id
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

seen_ids = set()
seen_fixtures = set()


for item in (

    new_highlights
    + existing

):

    highlight_id = str(

        item.get(
            "highlight_id",
            ""
        )

    )


    fixture_id = item.get(
        "fixture_id"
    )


    if (

        highlight_id

        and highlight_id in seen_ids

    ):

        continue


    if (

        fixture_id

        and fixture_id in seen_fixtures

    ):

        continue


    combined.append(
        item
    )


    if highlight_id:

        seen_ids.add(
            highlight_id
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
        "Highlightly",

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


# =========================================================
# FINAL DIAGNOSTIC
# =========================================================

print(
    "=================================================="
)

print(
    f"GOALINS: "
    f"{len(combined)} "
    f"real football highlights saved."
)

print(
    f"New videos: "
    f"{len(new_highlights)}"
)

print(
    f"Dates searched: "
    f"{len(searched_dates)}"
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

print(
    "=================================================="
)
