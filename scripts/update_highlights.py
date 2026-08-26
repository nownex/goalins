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
    raise RuntimeError("HIGHLIGHTLY_API_KEY is missing")


MATCHES_FILE = "data/matches.json"
OUTPUT_FILE = "data/highlights.json"

API_URL = "https://soccer.highlightly.net/highlights"

LOOKBACK_DAYS = 7
MAX_HIGHLIGHTS = 50

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
    "pes2026",
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
# HELPERS
# =========================================================

def normalize(text):

    text = str(text or "").lower()

    text = re.sub(
        r"[^a-z0-9\u0600-\u06ff]+",
        " ",
        text
    )

    return " ".join(text.split())


def is_gaming(text):

    value = normalize(text)

    return any(
        normalize(word) in value
        for word in GAMING_WORDS
    )


def get_date(match):

    return str(
        match.get("date", "")
    )[:10]


def get_league(match):

    league = match.get(
        "league",
        {}
    )

    if isinstance(league, dict):

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

    if isinstance(home, dict):

        return str(
            home.get(
                "name",
                ""
            )
        ).strip()

    return str(home or "").strip()


def get_away(match):

    away = match.get(
        "away",
        {}
    )

    if isinstance(away, dict):

        return str(
            away.get(
                "name",
                ""
            )
        ).strip()

    return str(away or "").strip()


def get_status(match):

    status = match.get(
        "status",
        ""
    )

    if isinstance(status, dict):

        return str(
            status.get(
                "short",
                ""
            )
        ).upper()

    return str(status).upper()


def is_finished(match):

    return get_status(match) in {
        "FT",
        "AET",
        "PEN"
    }


def teams_match(
    home,
    away,
    text
):

    value = normalize(text)

    h = normalize(home)
    a = normalize(away)

    if not h or not a:
        return False

    home_ok = (
        h in value
        or any(
            word in value
            for word in h.split()
            if len(word) >= 4
        )
    )

    away_ok = (
        a in value
        or any(
            word in value
            for word in a.split()
            if len(word) >= 4
        )
    )

    return home_ok and away_ok


# =========================================================
# LOAD MATCHES
# =========================================================

with open(
    MATCHES_FILE,
    "r",
    encoding="utf-8"
) as file:

    matches_data = json.load(file)


matches = matches_data.get(
    "matches",
    []
)


print("=" * 55)
print("GOALINS — HIGHLIGHTLY HIGHLIGHTS ENGINE")
print("=" * 55)

print(
    f"Total matches in matches.json: {len(matches)}"
)


# =========================================================
# ALGERIA DATE
# =========================================================

algeria_now = (
    datetime.now(timezone.utc)
    + timedelta(hours=1)
)

today = algeria_now.date()

start_date = (
    today
    - timedelta(days=LOOKBACK_DAYS)
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
# FIND ALLOWED FINISHED MATCHES
# =========================================================

target_matches = []


for match in matches:

    league = get_league(match)

    match_date = get_date(match)

    home = get_home(match)

    away = get_away(match)

    status = get_status(match)


    # -----------------------------------------------------
    # LEAGUE
    # -----------------------------------------------------

    if league not in ALLOWED_LEAGUES:
        continue


    # -----------------------------------------------------
    # FINISHED
    # -----------------------------------------------------

    if status not in {
        "FT",
        "AET",
        "PEN"
    }:
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
            match.get("fixture_id"),

        "date":
            match_date,

        "league":
            league,

        "home":
            home,

        "away":
            away

    })


# =========================================================
# DIAGNOSTIC
# =========================================================

print("-" * 55)

print(
    f"Finished allowed matches: "
    f"{len(target_matches)}"
)

print("-" * 55)

print("TARGET MATCHES:")


for match in target_matches:

    print(
        f"  {match['date']} | "
        f"{match['league']} | "
        f"{match['home']} vs "
        f"{match['away']}"
    )


print("-" * 55)


# =========================================================
# IMPORTANT:
# IF NO TARGET MATCHES, DO NOT CALL API
# =========================================================

if not target_matches:

    print(
        "ERROR: No allowed finished matches found."
    )

    print(
        "Check league names in matches.json."
    )

    raise SystemExit(0)


# =========================================================
# DATES
# =========================================================

dates = sorted({

    match["date"]

    for match in target_matches

})


print(
    f"Dates to search: {len(dates)}"
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

            old_data = json.load(file)


        if isinstance(
            old_data,
            dict
        ):

            old_highlights = old_data.get(
                "highlights",
                []
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
# HIGHLIGHTLY REQUEST
# =========================================================

headers = {

    "x-rapidapi-key":
        API_KEY,

    "Accept":
        "application/json"

}


def fetch_highlights(date):

    response = requests.get(

        API_URL,

        headers=headers,

        params={
            "date": date
        },

        timeout=30

    )


    print(
        "HTTP:",
        response.status_code
    )


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

    print("=" * 55)

    print(
        f"Searching Highlightly: {date}"
    )

    print("=" * 55)


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
        f"Videos returned: {len(videos)}"
    )


    date_matches = [

        match

        for match in target_matches

        if match["date"] == date

    ]


    # -----------------------------------------------------
    # VIDEOS
    # -----------------------------------------------------

    for video in videos:

        if not isinstance(
            video,
            dict
        ):
            continue


        video_id = (

            video.get("id")

            or video.get(
                "highlightId"
            )

            or video.get(
                "videoId"
            )

        )


        if not video_id:
            continue


        video_id = str(
            video_id
        )


        if video_id in old_ids:
            continue


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


        embed = (

            video.get(
                "embedUrl"
            )

            or video.get(
                "embed_url"
            )

            or video.get(
                "embed"
            )

        )


        thumbnail = (

            video.get(
                "imgUrl"
            )

            or video.get(
                "thumbnail"
            )

            or video.get(
                "image"
            )

        )


        if not embed:
            continue


        # -------------------------------------------------
        # VERIFIED
        # -------------------------------------------------

        video_type = str(

            video.get(
                "type",
                ""
            )

        ).upper()


        if video_type and video_type != "VERIFIED":

            continue


        # -------------------------------------------------
        # GAMING
        # -------------------------------------------------

        searchable = " ".join([

            title,
            description,
            source,
            channel

        ])


        if is_gaming(searchable):

            print(
                "REJECTED GAMING:",
                title
            )

            continue


        # -------------------------------------------------
        # MATCH WITH REAL FIXTURE
        # -------------------------------------------------

        selected_match = None


        for match in date_matches:

            if teams_match(

                match["home"],
                match["away"],
                searchable

            ):

                selected_match = match

                break


        if not selected_match:

            continue


        # -------------------------------------------------
        # SAVE
        # -------------------------------------------------

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
                embed,

            "embed_url":
                embed,

            "source":
                source,

            "channel":
                channel,

            "url":
                video.get(
                    "url"
                ),

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
                ]

        }


        print(
            "SELECTED:",
            selected_match["home"],
            "vs",
            selected_match["away"]
        )

        print(
            "VIDEO:",
            title
        )


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
# FINAL
# =========================================================

print("=" * 55)

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

print("=" * 55)
