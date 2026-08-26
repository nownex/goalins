import json
import os
import re
import requests

from datetime import datetime, timezone, timedelta


# =========================================================
# GOALINS — HIGHLIGHTLY VIDEO ENGINE
# =========================================================

API_KEY = os.environ.get("HIGHLIGHTLY_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "HIGHLIGHTLY_API_KEY is missing"
    )


API_URL = (
    "https://soccer.highlightly.net/highlights"
)

OUTPUT_FILE = "data/highlights.json"

LOOKBACK_DAYS = 3

MAX_HIGHLIGHTS = 50


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
    "virtual match",

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

        if normalize(word) in value:

            return True

    return False


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
# LOAD OLD DATA
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


print("=" * 60)

print(
    "GOALINS — HIGHLIGHTLY VIDEO ENGINE"
)

print("=" * 60)

print(
    f"Algeria date: {today}"
)

print(
    f"Searching from: {start_date}"
)

print(
    f"Searching to: {today}"
)

print("=" * 60)


# =========================================================
# FETCH ALL HIGHLIGHTS FOR DATE
# =========================================================

def fetch_highlights(date):

    params = {

        "date":
            date,

        "limit":
            100,

        "offset":
            0

    }


    print(
        f"Request date: {date}"
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

        print(
            "API response:",
            response.text[:500]
        )

        return []


    try:

        data = response.json()

    except Exception:

        return []


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
# COLLECT
# =========================================================

new_highlights = []

seen_ids = set(
    old_ids
)


dates = []


current = start_date


while current <= today:

    dates.append(
        current.strftime(
            "%Y-%m-%d"
        )
    )

    current += timedelta(
        days=1
    )


print(
    f"Dates to search: {len(dates)}"
)


# =========================================================
# SEARCH ALL VIDEOS
# =========================================================

for date in dates:

    print("=" * 60)

    print(
        f"Searching Highlightly: {date}"
    )

    print("=" * 60)


    videos = fetch_highlights(
        date
    )


    print(
        f"Videos returned: {len(videos)}"
    )


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


        if video_id in seen_ids:

            continue


        # -------------------------------------------------
        # DATA
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


        category = str(
            video.get(
                "category",
                ""
            )
        ).lower()


        thumbnail = video.get(
            "imgUrl"
        )


        embed_url = video.get(
            "embedUrl"
        )


        original_url = video.get(
            "url"
        )


        # -------------------------------------------------
        # MUST HAVE EMBED
        # -------------------------------------------------

        if not embed_url:

            print(
                "REJECTED — no embedUrl:",
                title
            )

            continue


        # -------------------------------------------------
        # GAMING
        # -------------------------------------------------

        searchable = " ".join([

            title,
            description,
            source,
            channel,
            category,

        ])


        if is_gaming(
            searchable
        ):

            print(
                "REJECTED — GAMING:",
                title
            )

            continue


        # -------------------------------------------------
        # ACCEPT
        #
        # We no longer require:
        # - exact fixture match
        # - allowed league
        # - VERIFIED only
        #
        # We only require:
        # - football highlight API result
        # - embedUrl
        # - not gaming
        # -------------------------------------------------

        print(
            "ACCEPTED VIDEO:"
        )

        print(
            "Title:",
            title
        )

        print(
            "Type:",
            video_type
        )

        print(
            "Category:",
            category
        )

        print(
            "Source:",
            source
        )

        print(
            "Embed:",
            embed_url
        )

        print("-" * 60)


        # -------------------------------------------------
        # MATCH INFORMATION IF AVAILABLE
        # -------------------------------------------------

        match = video.get(
            "match",
            {}
        )


        if not isinstance(
            match,
            dict
        ):

            match = {}


        home_team = match.get(
            "homeTeam",
            {}
        )


        away_team = match.get(
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


        home = (

            home_team.get(
                "name"
            )

            or ""

        )


        away = (

            away_team.get(
                "name"
            )

            or ""

        )


        league = match.get(
            "league",
            {}
        )


        if isinstance(
            league,
            dict
        ):

            league_name = (
                league.get(
                    "name"
                )
                or ""
            )

        else:

            league_name = str(
                league or ""
            )


        # -------------------------------------------------
        # SAVE
        # -------------------------------------------------

        item = {

            "highlight_id":
                video_id,

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
                video_type,

            "category":
                category,

            "date":
                date,

            "league":
                league_name,

            "home":
                home,

            "away":
                away,

        }


        new_highlights.append(
            item
        )


        seen_ids.add(
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
            "highlight_id",
            ""
        )

    ),

    reverse=True

)


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

print("=" * 60)

print(
    "GOALINS HIGHLIGHTS RESULT"
)

print("=" * 60)

print(
    f"Videos found: "
    f"{len(new_highlights)}"
)

print(
    f"Total saved: "
    f"{len(combined)}"
)

print(
    f"Dates searched: "
    f"{len(dates)}"
)

print(
    "Gaming videos rejected."
)

print(
    "Videos require embedUrl."
)

print("=" * 60)
