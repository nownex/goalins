import json
import os
import re
import requests

from datetime import datetime, timezone, timedelta


# =========================================================
# GOALINS — HIGHLIGHTS ENGINE
# =========================================================

API_KEY = os.environ.get("YOUTUBE_API_KEY")

if not API_KEY:
    raise RuntimeError("YOUTUBE_API_KEY is missing")


MATCHES_FILE = "data/matches.json"
OUTPUT_FILE = "data/highlights.json"

LOOKBACK_DAYS = 7
MAX_HIGHLIGHTS = 50

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


# =========================================================
# ALLOWED LEAGUES
# =========================================================

ALLOWED_LEAGUES = {

    "premier league",
    "la liga",
    "ligue 1",
    "serie a",
    "bundesliga",
    "eredivisie",
    "primeira liga",
    "jupiler pro league",
    "pro league",

    "uefa champions league",
    "uefa europa league",
    "uefa europa conference league",

    "champions league",
    "europa league",
    "conference league",

}


# =========================================================
# BLOCK GAMING / FAKE FOOTBALL
# =========================================================

BLOCKED_WORDS = [

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
    "e-football",

    "pes",
    "pes 2021",
    "pes 2022",
    "pes 2023",
    "pes 2024",
    "pes 2025",
    "pes 2026",

    "playstation",
    "play station",
    "ps4",
    "ps5",

    "xbox",

    "gameplay",
    "game play",

    "gaming",
    "video game",
    "videogame",

    "career mode",
    "master league",

    "simulation",
    "simulated",

]


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

else:

    matches = data


print("=" * 55)
print("GOALINS HIGHLIGHTS ENGINE")
print("=" * 55)

print(
    f"Total matches in matches.json: {len(matches)}"
)


# =========================================================
# HELPERS
# =========================================================

def normalize(text):

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


def get_status(match):

    status = match.get(
        "status"
    )

    if isinstance(status, dict):

        return str(
            status.get(
                "short",
                ""
            )
        ).upper()

    return str(
        status or ""
    ).upper()


def get_date(match):

    value = match.get(
        "date",
        ""
    )

    if not value:

        fixture = match.get(
            "fixture",
            {}
        )

        value = fixture.get(
            "date",
            ""
        )


    return str(
        value
    )[:10]


def get_league(match):

    league = match.get(
        "league",
        {}
    )

    if not isinstance(
        league,
        dict
    ):

        return {
            "id": None,
            "name": str(
                league
            )
        }

    return league


def get_team(
    match,
    side
):

    teams = match.get(
        "teams",
        {}
    )


    if isinstance(
        teams,
        dict
    ):

        team = teams.get(
            side,
            {}
        )

        if isinstance(
            team,
            dict
        ):

            return team


    return match.get(
        side,
        {}
    ) or {}


def contains_blocked_word(
    text
):

    normalized = normalize(
        text
    )

    for word in BLOCKED_WORDS:

        if normalize(word) in normalized:

            return True

    return False


def team_matches_title(
    team,
    title
):

    team = normalize(
        team
    )

    title = normalize(
        title
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


    found = 0


    for word in words:

        if word in title:

            found += 1


    return found >= max(
        1,
        len(words) // 2
    )


# =========================================================
# DATE
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


# =========================================================
# FILTER FINISHED REAL MATCHES
# =========================================================

finished_matches = []


for match in matches:

    status = get_status(
        match
    )


    if status not in (
        "FT",
        "AET",
        "PEN"
    ):

        continue


    date_string = get_date(
        match
    )


    try:

        match_date = datetime.strptime(
            date_string,
            "%Y-%m-%d"
        ).date()

    except Exception:

        continue


    if match_date < minimum_date:

        continue


    league = get_league(
        match
    )


    league_name = str(
        league.get(
            "name",
            ""
        )
    )


    league_normalized = normalize(
        league_name
    )


    # ---------------------------------------------
    # IMPORTANT:
    # We use league NAME instead of relying only
    # on league ID.
    # ---------------------------------------------

    if league_normalized not in ALLOWED_LEAGUES:

        continue


    home = get_team(
        match,
        "home"
    )


    away = get_team(
        match,
        "away"
    )


    home_name = str(
        home.get(
            "name",
            ""
        )
    )


    away_name = str(
        away.get(
            "name",
            ""
        )
    )


    if not home_name or not away_name:

        continue


    fixture_id = (
        match.get(
            "fixture_id"
        )
        or match
        .get(
            "fixture",
            {}
        )
        .get(
            "id"
        )
    )


    finished_matches.append({

        "fixture_id":
            fixture_id,

        "date":
            date_string,

        "league_id":
            league.get(
                "id"
            ),

        "league":
            league_name,

        "league_key":
            league_normalized,

        "home":
            home_name,

        "away":
            away_name

    })


# =========================================================
# SORT
# =========================================================

finished_matches.sort(
    key=lambda x: (
        x.get(
            "date",
            ""
        ),
        x.get(
            "fixture_id"
        ) or 0
    ),
    reverse=True
)


print(
    f"Finished allowed matches "
    f"in last {LOOKBACK_DAYS} days: "
    f"{len(finished_matches)}"
)


print(
    "-" * 55
)


for match in finished_matches:

    print(
        f"{match['date']} | "
        f"{match['league']} | "
        f"{match['home']} vs "
        f"{match['away']}"
    )


# =========================================================
# YOUTUBE SEARCH
# =========================================================

def youtube_search(
    query,
    published_after
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

        "publishedAfter":
            published_after,

        "key":
            API_KEY

    }


    response = requests.get(
        SEARCH_URL,
        params=params,
        timeout=30
    )


    response.raise_for_status()


    data = response.json()


    return data.get(
        "items",
        []
    )


# =========================================================
# VIDEO DETAILS
# =========================================================

def youtube_details(
    video_ids
):

    if not video_ids:

        return {}


    params = {

        "part":
            "snippet,status",

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


    data = response.json()


    result = {}


    for item in data.get(
        "items",
        []
    ):

        result[
            item.get("id")
        ] = item


    return result


# =========================================================
# SEARCH
# =========================================================

highlights = []

used_videos = set()


youtube_searches = 0


for match in finished_matches:

    if len(highlights) >= MAX_HIGHLIGHTS:

        break


    home = match["home"]
    away = match["away"]


    print("=" * 55)

    print(
        f"Searching YouTube: "
        f"{home} vs {away}"
    )


    query = (
        f'"{home}" "{away}" '
        f"highlights"
    )


    published_after = (
        f"{match['date']}T00:00:00Z"
    )


    try:

        results = youtube_search(
            query,
            published_after
        )

        youtube_searches += 1


    except Exception as e:

        print(
            "YouTube ERROR:",
            e
        )

        continue


    ids = []


    for item in results:

        video_id = (
            item
            .get(
                "id",
                {}
            )
            .get(
                "videoId"
            )
        )


        if video_id:

            ids.append(
                video_id
            )


    try:

        details = youtube_details(
            ids
        )

    except Exception as e:

        print(
            "Video details ERROR:",
            e
        )

        continue


    selected = None


    for item in results:

        video_id = (
            item
            .get(
                "id",
                {}
            )
            .get(
                "videoId"
            )
        )


        if not video_id:

            continue


        if video_id in used_videos:

            continue


        video = details.get(
            video_id
        )


        if not video:

            continue


        snippet = video.get(
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


        channel = str(
            snippet.get(
                "channelTitle",
                ""
            )
        )


        combined = (
            title
            + " "
            + description
            + " "
            + channel
        )


        # ---------------------------------------------
        # BLOCK GAMING
        # ---------------------------------------------

        if contains_blocked_word(
            combined
        ):

            print(
                "REJECT GAMING:",
                title
            )

            continue


        # ---------------------------------------------
        # SPORTS CATEGORY
        # ---------------------------------------------

        category_id = str(
            snippet.get(
                "categoryId",
                ""
            )
        )


        if category_id != "17":

            print(
                "REJECT NON-SPORT:",
                title
            )

            continue


        # ---------------------------------------------
        # BOTH TEAMS MUST APPEAR
        # ---------------------------------------------

        if not team_matches_title(
            home,
            title
        ):

            print(
                "REJECT HOME TEAM:",
                title
            )

            continue


        if not team_matches_title(
            away,
            title
        ):

            print(
                "REJECT AWAY TEAM:",
                title
            )

            continue


        # ---------------------------------------------
        # REJECT BAD VIDEO TYPES
        # ---------------------------------------------

        normalized_title = normalize(
            title
        )


        rejected_terms = [

            "prediction",
            "predictions",
            "preview",
            "reaction",
            "watch along",
            "watchalong",
            "transfer",
            "news"

        ]


        if any(
            term in normalized_title
            for term in rejected_terms
        ):

            print(
                "REJECT NON-HIGHLIGHT:",
                title
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
            .get(
                "url"
            )
        )


        if not thumbnail:

            thumbnail = (
                thumbnails
                .get(
                    "medium",
                    {}
                )
                .get(
                    "url"
                )
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
                channel,

            "published_at":
                snippet.get(
                    "publishedAt",
                    ""
                ),

            "youtube_category":
                category_id,

            "date":
                match["date"],

            "league":
                match["league"],

            "league_key":
                match["league_key"],

            "league_id":
                match["league_id"],

            "home":
                home,

            "away":
                away,

            "embed":
                (
                    "https://www.youtube-nocookie.com/"
                    f"embed/{video_id}"
                    "?rel=0"
                    "&modestbranding=1"
                    "&playsinline=1"
                )

        }


        break


    if selected:

        print(
            "SELECTED:",
            selected["title"]
        )


        highlights.append(
            selected
        )


        used_videos.add(
            selected["video_id"]
        )


    else:

        print(
            "NO VALID REAL FOOTBALL VIDEO"
        )


# =========================================================
# SAVE
# =========================================================

highlights.sort(
    key=lambda x: (
        x.get(
            "date",
            ""
        ),
        x.get(
            "published_at",
            ""
        )
    ),
    reverse=True
)


highlights = highlights[
    :MAX_HIGHLIGHTS
]


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
# FINAL
# =========================================================

print("=" * 55)

print(
    f"GOALINS: "
    f"{len(highlights)} "
    f"real football highlights saved."
)

print(
    f"YouTube searches: "
    f"{youtube_searches}"
)

print(
    "Gaming videos rejected automatically."
)

print("=" * 55)
