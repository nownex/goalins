import json
import os
import re
import requests

from datetime import datetime, timezone, timedelta


# =========================================================
# GOALINS — YOUTUBE / beIN SPORTS ARABIC HIGHLIGHTS ENGINE
# =========================================================

API_KEY = os.environ.get("YOUTUBE_API_KEY")

if not API_KEY:
    raise RuntimeError("YOUTUBE_API_KEY is missing")


MATCHES_FILE = "data/matches.json"
OUTPUT_FILE = "data/highlights.json"

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"

LOOKBACK_DAYS = 7
MAX_HIGHLIGHTS = 50

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
# ARABIC LEAGUE NAMES
# =========================================================

LEAGUE_ARABIC = {
    "Premier League": [
        "الدوري الإنجليزي",
        "الدوري الانجليزي",
        "البريميرليغ",
        "بريميرليغ",
    ],

    "La Liga": [
        "الدوري الإسباني",
        "الدوري الاسباني",
        "الليغا",
        "لاليغا",
    ],

    "Ligue 1": [
        "الدوري الفرنسي",
        "ليغ 1",
        "الدوري الفرنسي 1",
    ],

    "Serie A": [
        "الدوري الإيطالي",
        "الدوري الايطالي",
        "السيري آ",
        "سيري آ",
    ],

    "Bundesliga": [
        "الدوري الألماني",
        "الدوري الالماني",
        "البوندسليغا",
        "بوندسليغا",
    ],

    "Eredivisie": [
        "الدوري الهولندي",
        "الإيرديفيزي",
        "الدوري الهولندي الممتاز",
    ],

    "Jupiler Pro League": [
        "الدوري البلجيكي",
        "الدوري البلجيكي الممتاز",
    ],

    "Primeira Liga": [
        "الدوري البرتغالي",
        "الدوري البرتغالي الممتاز",
    ],

    "UEFA Champions League": [
        "دوري أبطال أوروبا",
        "دوري الابطال",
        "أبطال أوروبا",
    ],

    "UEFA Europa League": [
        "الدوري الأوروبي",
        "يوروبا ليغ",
        "اليوروبا ليغ",
    ],

    "UEFA Europa Conference League": [
        "دوري المؤتمر الأوروبي",
        "دوري المؤتمر",
        "المؤتمر الأوروبي",
    ],

    "UEFA Europa Conference League Qualification": [
        "دوري المؤتمر الأوروبي",
        "تصفيات دوري المؤتمر",
    ],
}


# =========================================================
# ARABIC TEAM ALIASES
#
# This is intentionally flexible.
# More aliases can be added later without changing
# the search engine.
# =========================================================

TEAM_ALIASES = {

    # -----------------------------------------------------
    # ENGLISH / EUROPE
    # -----------------------------------------------------

    "Valencia": [
        "فالنسيا",
        "فالنسيا الإسباني",
        "فالنسيا الاسباني",
    ],

    "Real Betis": [
        "ريال بيتيس",
        "بيتيس",
        "ريال بيتس",
    ],

    "Celtic": [
        "سيلتيك",
        "سلتيك",
        "سلتك",
    ],

    "Lask Linz": [
        "لاس لينز",
        "لاسك لينز",
        "لاسك لينز",
    ],

    "Bodo/Glimt": [
        "بودو غليمت",
        "بودو جليمت",
        "بودو غليم",
        "بودو",
    ],

    "NEC Nijmegen": [
        "نييميخن",
        "نايميخن",
        "إن إي سي نيميخن",
        "إن إي سي",
    ],

    "Rapid Vienna": [
        "رابيد فيينا",
        "رابيد",
        "رابيد وين",
    ],

    "Heart of Midlothian": [
        "هارتس",
        "هارت أوف ميدلوثيان",
        "هارت أوف ميدلوتيان",
        "هارت اوف ميدلوثيان",
    ],

    # -----------------------------------------------------
    # BRAZIL
    # -----------------------------------------------------

    "Botafogo": [
        "بوتافوغو",
        "بوتافوجو",
        "بوتافغو",
    ],

    "Atletico Paranaense": [
        "أتلتيكو باراناينسي",
        "اتلتيكو باراناينسي",
        "أتلتيكو بارانينسي",
        "باراناينسي",
    ],

    # -----------------------------------------------------
    # KAZAKHSTAN
    # -----------------------------------------------------

    "FK Tobol Kostanay": [
        "توبول",
        "توبول كوستاناي",
        "توبول كوستاناي الكازاخي",
    ],

    "Kaisar": [
        "كايسار",
        "قايصار",
        "كايزار",
        "قيسار",
    ],

    # -----------------------------------------------------
    # UZBEKISTAN
    # -----------------------------------------------------

    "Abdish-Ata": [
        "أبدش آتا",
        "أبدش أتا",
        "أبدش عطا",
        "أبدش",
    ],

    "Talant": [
        "تالانت",
        "تالنت",
    ],

    # -----------------------------------------------------
    # KUWAIT
    # -----------------------------------------------------

    "Al Kuwait": [
        "الكويت",
        "نادي الكويت",
        "الكويت الكويتي",
    ],

    "Al Arabi": [
        "العربي",
        "العربي الكويتي",
        "نادي العربي",
    ],

    "Al Fahaheel": [
        "الفحيحيل",
        "فحيحيل",
        "نادي الفحيحيل",
    ],

    "Al Qadsia": [
        "القادسية",
        "القادسية الكويتي",
        "نادي القادسية",
    ],

    "Al Shabab": [
        "الشباب",
        "الشباب الكويتي",
        "نادي الشباب",
    ],

    "Al Jahra": [
        "الجهراء",
        "الجهراء الكويتي",
        "نادي الجهراء",
    ],

    # -----------------------------------------------------
    # AZERBAIJAN / ISRAEL
    # -----------------------------------------------------

    "Sabah FA": [
        "ساباه",
        "صباح",
        "ساباه باكو",
        "سباه",
    ],

    "Hapoel Beer Sheva": [
        "هبوعيل بئر السبع",
        "هبوعيل بئر سبع",
        "هبوعيل بئرشبع",
        "بئر السبع",
    ],

    # -----------------------------------------------------
    # EGYPT
    # -----------------------------------------------------

    "Smouha SC": [
        "سموحة",
        "سموحه",
        "نادي سموحة",
    ],

    "Asyut Petrol": [
        "بترول أسيوط",
        "بترول اسيوط",
        "أسيوط للبترول",
        "اسيوط للبترول",
    ],

    "National Bank of Egypt": [
        "البنك الأهلي",
        "البنك الأهلي المصري",
        "البنك الاهلي",
        "البنك الأهلي المصري",
    ],

    "Zamalek SC": [
        "الزمالك",
        "نادي الزمالك",
        "الزمالك المصري",
    ],

    "Petrojet": [
        "بتروجيت",
        "بتروجت",
        "نادي بتروجيت",
    ],

    "El Geish": [
        "طلائع الجيش",
        "الجيش",
        "نادي طلائع الجيش",
    ],
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
    "لعبة",
    "فيفا",
    "إي فوتبول",
    "e فوتبول",
]


# =========================================================
# NORMALIZE
# =========================================================

def normalize(text):

    text = str(text or "").lower()

    # Arabic normalization
    text = text.replace("أ", "ا")
    text = text.replace("إ", "ا")
    text = text.replace("آ", "ا")
    text = text.replace("ى", "ي")
    text = text.replace("ة", "ه")
    text = text.replace("ؤ", "و")
    text = text.replace("ئ", "ي")

    # Remove Arabic diacritics
    text = re.sub(
        r"[\u064B-\u065F\u0670]",
        "",
        text
    )

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
        "PEN",
    }


# =========================================================
# TEAM ALIAS LIST
# =========================================================

def get_team_aliases(team):

    aliases = []

    aliases.append(team)

    known = TEAM_ALIASES.get(
        team,
        []
    )

    aliases.extend(
        known
    )

    # Also support case-insensitive key lookup
    normalized_team = normalize(team)

    for key, values in TEAM_ALIASES.items():

        if normalize(key) == normalized_team:

            aliases.extend(values)

    # Remove duplicates
    result = []

    seen = set()

    for alias in aliases:

        value = normalize(alias)

        if not value:
            continue

        if value in seen:
            continue

        seen.add(value)
        result.append(value)

    return result


# =========================================================
# TEAM FOUND IN ARABIC TITLE
# =========================================================

def team_found_in_title(
    team,
    title,
    description=""
):

    searchable = normalize(
        f"{title} {description}"
    )

    aliases = get_team_aliases(
        team
    )

    for alias in aliases:

        if alias in searchable:

            return True

    return False


# =========================================================
# MATCH SCORE
# =========================================================

def video_match_score(
    title,
    description,
    home,
    away,
    league
):

    searchable = normalize(
        f"{title} {description}"
    )

    score = 0

    home_found = team_found_in_title(
        home,
        title,
        description
    )

    away_found = team_found_in_title(
        away,
        title,
        description
    )

    if home_found:
        score += 100

    if away_found:
        score += 100

    # Both teams is the strongest signal
    if home_found and away_found:
        score += 150

    # Arabic football keywords
    if "ملخص" in searchable:
        score += 50

    if "اهداف" in searchable:
        score += 40

    if "مباراة" in searchable:
        score += 20

    if "هدف" in searchable:
        score += 15

    if "highlights" in searchable:
        score += 40

    # League keyword
    for league_alias in LEAGUE_ARABIC.get(
        league,
        []
    ):

        if normalize(league_alias) in searchable:

            score += 20

            break

    # Gaming
    if is_gaming(searchable):

        score -= 500

    return score, home_found, away_found


# =========================================================
# GET beIN CHANNEL ID
# =========================================================

def get_bein_channel_id():

    global BEIN_CHANNEL_ID

    if BEIN_CHANNEL_ID:
        return BEIN_CHANNEL_ID

    print("=" * 60)
    print("Finding beIN SPORTS channel...")
    print("=" * 60)

    params = {
        "part": "id,snippet",
        "forHandle": BEIN_HANDLE,
        "key": API_KEY,
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
        items[0].get("id")
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
# SEARCH ONE QUERY
# =========================================================

def youtube_search_request(
    channel_id,
    query,
    published_after,
    published_before
):

    params = {

        "part": "snippet",

        "channelId":
            channel_id,

        "q":
            query,

        "type":
            "video",

        "order":
            "date",

        "maxResults":
            50,

        "publishedAfter":
            published_after,

        "publishedBefore":
            published_before,

        "relevanceLanguage":
            "ar",

        "regionCode":
            "DZ",

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

        return []

    data = response.json()

    items = data.get(
        "items",
        []
    )

    print(
        "Videos returned:",
        len(items)
    )

    return items


# =========================================================
# SEARCH YOUTUBE FOR A FIXTURE
# =========================================================

def search_youtube(
    home,
    away,
    match_date,
    league
):

    channel_id = (
        get_bein_channel_id()
    )

    date_obj = datetime.strptime(
        match_date,
        "%Y-%m-%d"
    )

    published_after = (
        date_obj
        .replace(
            hour=0,
            minute=0,
            second=0,
            tzinfo=timezone.utc
        )
        - timedelta(days=1)
    )

    published_before = (
        date_obj
        .replace(
            hour=23,
            minute=59,
            second=59,
            tzinfo=timezone.utc
        )
        + timedelta(days=3)
    )

    after_text = published_after.isoformat()
    before_text = published_before.isoformat()

    # -----------------------------------------------------
    # IMPORTANT
    #
    # We DO NOT depend on English team names.
    #
    # The official beIN channel publishes Arabic titles.
    # -----------------------------------------------------

    queries = [

        "ملخص مباراة",

        "ملخص",

        "اهداف",

        "أهداف",

        "ملخص الدوري",

    ]

    # Add Arabic league searches
    league_aliases = LEAGUE_ARABIC.get(
        league,
        []
    )

    for league_name in league_aliases[:2]:

        queries.append(
            f"ملخص {league_name}"
        )

    # Add known Arabic team searches
    home_aliases = get_team_aliases(home)
    away_aliases = get_team_aliases(away)

    if home_aliases and away_aliases:

        # Use the first Arabic aliases when available
        home_ar = next(
            (
                x
                for x in home_aliases
                if re.search(
                    r"[\u0600-\u06ff]",
                    x
                )
            ),
            ""
        )

        away_ar = next(
            (
                x
                for x in away_aliases
                if re.search(
                    r"[\u0600-\u06ff]",
                    x
                )
            ),
            ""
        )

        if home_ar and away_ar:

            queries.insert(
                0,
                f"ملخص {home_ar} {away_ar}"
            )

            queries.insert(
                1,
                f"{home_ar} {away_ar}"
            )

    # Remove duplicates
    unique_queries = []

    seen_queries = set()

    for query in queries:

        query_normalized = normalize(
            query
        )

        if query_normalized in seen_queries:
            continue

        seen_queries.add(
            query_normalized
        )

        unique_queries.append(
            query
        )

    candidates = {}

    for query in unique_queries:

        print("-" * 60)

        print(
            "YouTube Arabic search:",
            query
        )

        items = youtube_search_request(

            channel_id,

            query,

            after_text,

            before_text

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

            result_channel = str(
                snippet.get(
                    "channelId",
                    ""
                )
            )

            # Must be official beIN channel
            if result_channel != channel_id:
                continue

            searchable = (
                f"{title} {description}"
            )

            if is_gaming(
                searchable
            ):

                print(
                    "REJECTED GAMING:",
                    title
                )

                continue

            score, home_found, away_found = (
                video_match_score(
                    title,
                    description,
                    home,
                    away,
                    league
                )
            )

            print(
                f"Candidate [{score}] "
                f"H={home_found} "
                f"A={away_found}: "
                f"{title}"
            )

            candidate = {

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
                        .get(
                            "thumbnails",
                            {}
                        )
                        .get(
                            "high",
                            {}
                        )
                        .get(
                            "url"
                        )
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

                "home_found":
                    home_found,

                "away_found":
                    away_found,

            }

            old = candidates.get(
                video_id
            )

            if (
                old is None
                or score > old["score"]
            ):

                candidates[
                    video_id
                ] = candidate

    result = list(
        candidates.values()
    )

    result.sort(
        key=lambda item: (
            item["score"],
            item.get(
                "published_at",
                ""
            )
        ),
        reverse=True
    )

    return result


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
    "GOALINS — YOUTUBE / beIN SPORTS "
    "ARABIC HIGHLIGHTS ENGINE"
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
    + timedelta(hours=1)
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

    if not is_finished(match):
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
# TARGET DIAGNOSTIC
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

for fixture in target_matches:

    print(
        f"{fixture['date']} | "
        f"{fixture['league']} | "
        f"{fixture['home']} vs "
        f"{fixture['away']}"
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
        "Searching beIN SPORTS:"
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

            fixture["date"],

            fixture["league"]

        )

    except Exception as error:

        print(
            "YouTube ERROR:",
            error
        )

        continue

    if not candidates:

        print(
            "No videos returned from beIN SPORTS."
        )

        continue

    # -----------------------------------------------------
    # Find strongest candidate
    # -----------------------------------------------------

    selected = None

    for candidate in candidates:

        # Strongest case:
        # both teams found in Arabic title/description.

        if (
            candidate["home_found"]
            and candidate["away_found"]
        ):

            selected = candidate
            break

    # -----------------------------------------------------
    # If no exact Arabic team match,
    # do NOT randomly attach another match.
    # -----------------------------------------------------

    if selected is None:

        print(
            "beIN videos found, "
            "but no reliable team match."
        )

        for candidate in candidates[:5]:

            print(
                "Possible:",
                candidate["title"]
            )

        continue

    video_id = selected[
        "video_id"
    ]

    if video_id in old_ids:

        print(
            "Already saved:",
            video_id
        )

        continue

    print("=" * 60)

    print(
        "SELECTED OFFICIAL beIN SPORTS VIDEO"
    )

    print(
        "Title:",
        selected["title"]
    )

    print(
        "Score:",
        selected["score"]
    )

    print(
        "Video ID:",
        video_id
    )

    print("=" * 60)

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
        combined,

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
    "Language: Arabic first"
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
