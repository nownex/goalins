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
    raise RuntimeError(
        "YOUTUBE_API_KEY is missing"
    )


MATCHES_FILE = "data/matches.json"
OUTPUT_FILE = "data/highlights.json"

YOUTUBE_SEARCH_URL = (
    "https://www.googleapis.com/youtube/v3/search"
)

YOUTUBE_CHANNELS_URL = (
    "https://www.googleapis.com/youtube/v3/channels"
)

LOOKBACK_DAYS = 7
MAX_HIGHLIGHTS = 50

# =========================================================
# OFFICIAL beIN SPORTS CHANNEL
# =========================================================

BEIN_HANDLE = "@beinsports"

BEIN_CHANNEL_ID = None


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

def team_tokens(name):

    value = normalize(name)

    ignored = {

        "fc",
        "sc",
        "cf",
        "afc",
        "club",
        "de",
        "the",
        "of",
        "and",

    }

    return {

        token

        for token in value.split()

        if len(token) >= 3
        and token not in ignored

    }


def team_name_match(
    expected,
    title
):

    expected_tokens = team_tokens(
        expected
    )

    title_tokens = set(
        normalize(title).split()
    )

    if not expected_tokens:

        return False


    common = (
        expected_tokens
        & title_tokens
    )


    # Strong match

    if len(common) >= 2:

        return True


    # Single distinctive token

    if len(expected_tokens) == 1:

        return len(common) >= 1


    return False


# =========================================================
# VIDEO MATCH SCORE
# =========================================================

def video_match_score(
    title,
    home,
    away
):

    title_normalized = normalize(
        title
    )

    home_tokens = team_tokens(
        home
    )

    away_tokens = team_tokens(
        away
    )

    title_tokens = set(
        title_normalized.split()
    )


    home_common = (
        home_tokens
        & title_tokens
    )

    away_common = (
        away_tokens
        & title_tokens
    )


    score = 0


    # Both teams found

    if home_common:

        score += 50

    if away_common:

        score += 50


    # More matching words = better

    score += (
        len(home_common) * 10
    )

    score += (
        len(away_common) * 10
    )


    # Highlights strongly preferred

    if "highlights" in title_normalized:

        score += 30

    if "extended highlights" in title_normalized:

        score += 20

    if "ملخص" in title_normalized:

        score += 30


    # Gaming penalty

    if is_gaming(title):

        score -= 200


    return score


# =========================================================
# GET beIN SPORTS CHANNEL ID
# =========================================================

def get_bein_channel_id():

    global BEIN_CHANNEL_ID


    if BEIN_CHANNEL_ID:

        return BEIN_CHANNEL_ID


    print("=" * 60)

    print(
        "Finding beIN SPORTS channel..."
    )


    params = {

        "part":
            "id,snippet",

        "forHandle":
            BEIN_HANDLE,

        "key":
            API_KEY,

    }


    response = requests.get(

        YOUTUBE_CHANNELS_URL,

        params=params,

        timeout=30

    )


    print(
        "Channel HTTP:",
        response.status_code
    )


    if response.status_code != 200:

        print(
            "YouTube API response:",
            response.text[:1000]
        )

        response.raise_for_status()


    data = response.json()


    items = data.get(
        "items",
        []
    )


    if not items:

        raise RuntimeError(
            "Could not find beIN SPORTS YouTube channel."
        )


    BEIN_CHANNEL_ID = (
        items[0]
        .get("id")
    )


    if not BEIN_CHANNEL_ID:

        raise RuntimeError(
            "beIN SPORTS channel ID is missing."
        )


    print(
        "beIN SPORTS Channel ID:",
        BEIN_CHANNEL_ID
    )


    return BEIN_CHANNEL_ID


# =========================================================
# SEARCH YOUTUBE
# =========================================================

def search_youtube(
    home,
    away,
    match_date
):

    channel_id = (
        get_bein_channel_id()
    )


    # Search only around the match date.
    published_after = (
        datetime.strptime(
            match_date,
            "%Y-%m-%d"
        )
        .replace(
            tzinfo=timezone.utc
        )
        - timedelta(
            days=1
        )
    )


    published_before = (
        datetime.strptime(
            match_date,
            "%Y-%m-%d"
        )
        .replace(
            tzinfo=timezone.utc
        )
        + timedelta(
            days=3
        )
    )


    # We try a few search forms.
    queries = [

        f"{home} {away} highlights",

        f"{home} vs {away}",

    ]


    candidates = []


    for query in queries:

        print(
            "YouTube search:",
            query
        )


        params = {

            "part":
                "snippet",

            "channelId":
                channel_id,

            "q":
                query,

            "type":
                "video",

            "order":
                "date",

            "maxResults":
                10,

            "publishedAfter":
                published_after.isoformat(),

            "publishedBefore":
                published_before.isoformat(),

            "videoEmbeddable":
                "true",

            "videoSyndicated":
                "true",

            "key":
                API_KEY,

        }


        response = requests.get(

            YOUTUBE_SEARCH_URL,

            params=params,

            timeout=30

        )


        print(
            "YouTube HTTP:",
            response.status_code
        )


        if response.status_code != 200:

            print(
                "YouTube API ERROR:",
                response.text[:1000]
            )

            continue


        data = response.json()


        items = data.get(
            "items",
            []
        )


        print(
            "Videos returned:",
            len(items)
        )


        for item in items:

            if not isinstance(
                item,
                dict
            ):

                continue


            item_id = item.get(
                "id",
                {}
            )


            if not isinstance(
                item_id,
                dict
            ):

                continue


            video_id = item_id.get(
                "videoId"
            )


            if not video_id:

                continue


            snippet = item.get(
                "snippet",
                {}
            )


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


            # Must belong to beIN channel

            result_channel = str(
                snippet.get(
                    "channelId",
                    ""
                )
            )


            if result_channel != channel_id:

                continue


            searchable = " ".join([

                title,
                description,

            ])


            # Reject gaming

            if is_gaming(
                searchable
            ):

                print(
                    "REJECTED GAMING:",
                    title
                )

                continue


            score = video_match_score(

                title,
                home,
                away

            )


            print(
                f"Candidate [{score}]: {title}"
            )


            # We require both teams
            # to appear meaningfully.

            home_found = team_name_match(
                home,
                title
            )

            away_found = team_name_match(
                away,
                title
            )


            if not (
                home_found
                and away_found
            ):

                print(
                    "REJECTED: teams not both found"
                )

                continue


            candidates.append({

                "video_id":
                    video_id,

                "title":
                    title,

                "description":
                    description,

                "published_at":
                    snippet.get(
                        "publishedAt",
                        ""
                    ),

                "thumbnail":
                    (
                        snippet
                        .get("thumbnails", {})
                        .get("high", {})
                        .get("url")
                    ),

                "channel_id":
                    result_channel,

                "channel_title":
                    snippet.get(
                        "channelTitle",
                        "beIN SPORTS"
                    ),

                "score":
                    score,

            })


    # =====================================================
    # REMOVE DUPLICATES
    # =====================================================

    unique = {}

    for item in candidates:

        video_id = item[
            "video_id"
        ]

        if video_id not in unique:

            unique[video_id] = item

        else:

            if (
                item["score"]
                >
                unique[video_id]["score"]
            ):

                unique[video_id] = item


    candidates = list(
        unique.values()
    )


    candidates.sort(

        key=lambda item: (

            item["score"],

            item.get(
                "published_at",
                ""
            )

        ),

        reverse=True

    )


    return candidates


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
    "GOALINS — YOUTUBE HIGHLIGHTS ENGINE"
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
# SEARCH
# =========================================================

new_highlights = []

fixtures_searched = 0


for fixture in target_matches:

    if len(
        new_highlights
    ) >= MAX_HIGHLIGHTS:

        break


    print("=" * 60)

    print(
        "Searching YouTube:"
    )

    print(
        f"{fixture['date']} | "
        f"{fixture['league']} | "
        f"{fixture['home']} vs "
        f"{fixture['away']}"
    )

    print("=" * 60)


    fixtures_searched += 1


    try:

        candidates = search_youtube(

            fixture["home"],

            fixture["away"],

            fixture["date"]

        )

    except Exception as error:

        print(
            "YouTube ERROR:",
            error
        )

        continue


    if not candidates:

        print(
            "No matching beIN SPORTS video found."
        )

        continue


    # Best candidate

    selected = candidates[0]


    video_id = selected[
        "video_id"
    ]


    if video_id in old_ids:

        print(
            "Already saved:",
            video_id
        )

        continue


    print(
        "SELECTED:"
    )

    print(
        selected["title"]
    )

    print(
        "Score:",
        selected["score"]
    )


    # =====================================================
    # SAVE
    # =====================================================

    item = {

        "highlight_id":
            video_id,

        "fixture_id":
            fixture[
                "fixture_id"
            ],

        "title":
            selected[
                "title"
            ],

        "description":
            selected[
                "description"
            ],

        "thumbnail":
            selected[
                "thumbnail"
            ],

        # IMPORTANT:
        # This is the URL that frontend
        # must use inside an iframe.

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
            selected[
                "channel_title"
            ],

        "channel_id":
            selected[
                "channel_id"
            ],

        "type":
            "OFFICIAL",

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
        "YouTube / beIN SPORTS",

    "type":
        "OFFICIAL",

    "channel":
        BEIN_HANDLE,

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
    f"Fixtures searched: "
    f"{fixtures_searched}"
)

print(
    f"Target matches: "
    f"{len(target_matches)}"
)

print(
    "Source: YouTube / beIN SPORTS"
)

print(
    "Official channel only."
)

print(
    "Embeddable videos only."
)

print(
    "Gaming videos rejected automatically."
)

print("=" * 60)
