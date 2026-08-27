import json
import os
import re
import requests

from datetime import datetime, timezone, timedelta


# =========================================================
# GOALINS — AUTOMATIC FOOTBALL HIGHLIGHTS ENGINE
# =========================================================
#
# IMPORTANT:
# This version DOES NOT depend on matches.json.
#
# It scans the official beIN SPORTS YouTube channel directly
# and automatically collects real football match highlights.
#
# YouTube API usage:
# - channels.list
# - playlistItems.list
# - videos.list
#
# It does NOT use search.list for every match.
#
# =========================================================


API_KEY = os.environ.get("YOUTUBE_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "YOUTUBE_API_KEY is missing"
    )


OUTPUT_FILE = "data/highlights.json"

YOUTUBE_CHANNELS_URL = (
    "https://www.googleapis.com/youtube/v3/channels"
)

YOUTUBE_PLAYLIST_URL = (
    "https://www.googleapis.com/youtube/v3/playlistItems"
)

YOUTUBE_VIDEOS_URL = (
    "https://www.googleapis.com/youtube/v3/videos"
)


# =========================================================
# SETTINGS
# =========================================================

BEIN_HANDLE = "@beinsports"

MAX_CHANNEL_VIDEOS = 50

MAX_HIGHLIGHTS = 50

LOOKBACK_DAYS = 14


# =========================================================
# FOOTBALL / HIGHLIGHT KEYWORDS
# =========================================================

HIGHLIGHT_KEYWORDS = [

    # Arabic
    "ملخص مباراة",
    "ملخص المبار",
    "ملخص لقاء",
    "ملخص ",
    "أهداف مباراة",
    "اهداف مباراة",
    "أهداف",
    "اهداف",
    "هدف المباراة",
    "ملخص وأهداف",
    "ملخص واهداف",
    "ملخص و أهداف",
    "ملخص و اهداف",

    # English
    "highlights",
    "match highlights",
    "extended highlights",
    "full highlights",
    "match recap",
    "goals",

]


# =========================================================
# STRONG FOOTBALL WORDS
# =========================================================

FOOTBALL_WORDS = [

    # Arabic
    "مباراة",
    "مباراه",
    "لقاء",
    "الدوري",
    "دوري",
    "كأس",
    "كاس",
    "دوري الأبطال",
    "دوري ابطال",
    "دوري أبطال",
    "أبطال أوروبا",
    "ابطال اوروبا",
    "الدوري الإنجليزي",
    "الدوري الاسباني",
    "الدوري الإسباني",
    "الدوري الإيطالي",
    "الدوري الألماني",
    "الدوري الفرنسي",
    "الدوري التركي",
    "الدوري السعودي",
    "الدوري المصري",
    "الدوري المغربي",
    "الدوري القطري",
    "الدوري الإماراتي",
    "الدوري الهولندي",
    "الدوري البرتغالي",
    "دوري المؤتمر",
    "الدوري الأوروبي",
    "كأس العالم",
    "المنتخب",
    "منتخب",

    # English
    "match",
    "game",
    "league",
    "cup",
    "premier league",
    "champions league",
    "europa league",
    "conference league",
    "la liga",
    "serie a",
    "bundesliga",
    "ligue 1",
    "eredivisie",
    "football",
    "soccer",

]


# =========================================================
# NON-HIGHLIGHT / NEWS WORDS
# =========================================================

NEWS_WORDS = [

    # Arabic
    "أخبار",
    "اخبار",
    "الحصاد",
    "حصاد",
    "آخر الأخبار",
    "اخر الاخبار",
    "أهم الأخبار",
    "اهم الاخبار",
    "ترند",
    "تصريحات",
    "تصريح",
    "مؤتمر صحفي",
    "مؤتمر",
    "كواليس",
    "انتقال",
    "انتقالات",
    "ينضم",
    "يعلن",
    "إعلان",
    "اعلان",
    "صفقة",
    "صفقات",
    "سوق الانتقالات",
    "تحليل",
    "تحليلات",
    "تعليق",
    "استوديو",
    "استديو",
    "برنامج",
    "حلقة",
    "تقرير",
    "تقارير",
    "حديث",
    "حديث خاص",
    "رأي",
    "آراء",

    # English
    "news",
    "transfer",
    "transfers",
    "breaking",
    "analysis",
    "studio",
    "interview",
    "press conference",
    "preview",
    "podcast",
    "report",

]


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
# KEYWORD CHECK
# =========================================================

def contains_keyword(
    text,
    keywords
):

    value = normalize(text)

    for keyword in keywords:

        keyword_normalized = normalize(
            keyword
        )

        if keyword_normalized in value:

            return True

    return False


# =========================================================
# GAMING CHECK
# =========================================================

def is_gaming(text):

    return contains_keyword(
        text,
        GAMING_WORDS
    )


# =========================================================
# NEWS CHECK
# =========================================================

def is_news(text):

    return contains_keyword(
        text,
        NEWS_WORDS
    )


# =========================================================
# REAL FOOTBALL HIGHLIGHT CHECK
# =========================================================

def is_real_highlight(
    title,
    description=""
):

    searchable = " ".join([

        str(title or ""),

        str(description or ""),

    ])


    # -----------------------------------------------------
    # Gaming is never accepted
    # -----------------------------------------------------

    if is_gaming(searchable):

        return False


    # -----------------------------------------------------
    # Must contain a highlight keyword
    # -----------------------------------------------------

    if not contains_keyword(
        title,
        HIGHLIGHT_KEYWORDS
    ):

        return False


    # -----------------------------------------------------
    # Reject obvious news / analysis videos
    # -----------------------------------------------------

    if is_news(title):

        # Exception:
        # "ملخص مباراة" is much stronger than news words.

        strong_match = (

            "ملخص مباراة" in normalize(title)

            or

            "أهداف مباراة" in normalize(title)

            or

            "اهداف مباراة" in normalize(title)

            or

            "match highlights" in normalize(title)

            or

            "highlights" in normalize(title)

        )

        if not strong_match:

            return False


    # -----------------------------------------------------
    # Must contain football context
    # -----------------------------------------------------

    if not contains_keyword(
        searchable,
        FOOTBALL_WORDS
    ):

        return False


    return True


# =========================================================
# GET BEIN CHANNEL
# =========================================================

def get_bein_channel():

    print("=" * 60)

    print(
        "Finding official beIN SPORTS channel..."
    )


    params = {

        "part":
            "id,contentDetails,snippet",

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
            response.text[:2000]
        )

        response.raise_for_status()


    data = response.json()


    items = data.get(
        "items",
        []
    )


    if not items:

        raise RuntimeError(
            "Official beIN SPORTS channel not found."
        )


    channel = items[0]


    channel_id = channel.get(
        "id"
    )


    uploads_playlist = (

        channel

        .get(
            "contentDetails",
            {}
        )

        .get(
            "relatedPlaylists",
            {}
        )

        .get(
            "uploads"
        )

    )


    if not channel_id:

        raise RuntimeError(
            "beIN channel ID missing."
        )


    if not uploads_playlist:

        raise RuntimeError(
            "beIN uploads playlist missing."
        )


    print(
        "beIN Channel ID:",
        channel_id
    )

    print(
        "Uploads playlist:",
        uploads_playlist
    )


    return (

        channel_id,

        uploads_playlist

    )


# =========================================================
# GET LATEST CHANNEL VIDEOS
# =========================================================

def get_latest_videos(
    uploads_playlist
):

    print("=" * 60)

    print(
        "Loading latest beIN SPORTS videos..."
    )


    params = {

        "part":
            "snippet,contentDetails",

        "playlistId":
            uploads_playlist,

        "maxResults":
            MAX_CHANNEL_VIDEOS,

        "key":
            API_KEY,

    }


    response = requests.get(

        YOUTUBE_PLAYLIST_URL,

        params=params,

        timeout=30

    )


    print(
        "Playlist HTTP:",
        response.status_code
    )


    if response.status_code != 200:

        print(
            response.text[:2000]
        )

        response.raise_for_status()


    data = response.json()


    items = data.get(
        "items",
        []
    )


    print(
        "Channel videos returned:",
        len(items)
    )


    return items


# =========================================================
# CHECK VIDEO DETAILS
# =========================================================

def get_video_details(
    video_ids
):

    if not video_ids:

        return {}


    params = {

        "part":
            "snippet,contentDetails,status",

        "id":
            ",".join(video_ids),

        "key":
            API_KEY,

    }


    response = requests.get(

        YOUTUBE_VIDEOS_URL,

        params=params,

        timeout=30

    )


    print(
        "Videos HTTP:",
        response.status_code
    )


    if response.status_code != 200:

        print(
            response.text[:2000]
        )

        response.raise_for_status()


    data = response.json()


    result = {}


    for item in data.get(
        "items",
        []
    ):

        video_id = item.get(
            "id"
        )


        if not video_id:

            continue


        result[
            video_id
        ] = item


    return result


# =========================================================
# LOAD OLD DATA
# =========================================================

def load_old_highlights():

    if not os.path.exists(
        OUTPUT_FILE
    ):

        return []


    try:

        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )


        if isinstance(
            data,
            dict
        ):

            highlights = data.get(
                "highlights",
                []
            )


            if isinstance(
                highlights,
                list
            ):

                return highlights


        if isinstance(
            data,
            list
        ):

            return data


    except Exception as error:

        print(
            "Could not read old highlights:",
            error
        )


    return []


# =========================================================
# VIDEO DATE
# =========================================================

def parse_youtube_date(
    value
):

    if not value:

        return None


    try:

        return datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00"
            )
        )

    except Exception:

        return None


# =========================================================
# BUILD HIGHLIGHT
# =========================================================

def build_highlight(
    video,
    channel_id
):

    video_id = video.get(
        "id"
    )


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


    published_at = str(
        snippet.get(
            "publishedAt",
            ""
        )
    )


    thumbnails = snippet.get(
        "thumbnails",
        {}
    )


    thumbnail = None


    for size in [

        "maxres",
        "high",
        "medium",
        "default",

    ]:

        image = thumbnails.get(
            size,
            {}
        )


        if image.get(
            "url"
        ):

            thumbnail = image.get(
                "url"
            )

            break


    # -----------------------------------------------------
    # Date
    # -----------------------------------------------------

    published_date = ""


    parsed_date = parse_youtube_date(
        published_at
    )


    if parsed_date:

        published_date = (
            parsed_date
            .date()
            .isoformat()
        )


    # -----------------------------------------------------
    # Save
    # -----------------------------------------------------

    return {

        "highlight_id":
            video_id,

        "youtube_id":
            video_id,

        "title":
            title,

        "description":
            description,

        "thumbnail":
            thumbnail,

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

        "source":
            "YouTube",

        "channel":
            snippet.get(
                "channelTitle",
                "beIN SPORTS"
            ),

        "channel_id":
            channel_id,

        "type":
            "OFFICIAL",

        "date":
            published_date,

    }


# =========================================================
# MAIN
# =========================================================

print("=" * 60)

print(
    "GOALINS — AUTOMATIC FOOTBALL HIGHLIGHTS"
)

print("=" * 60)

print(
    "Source: Official beIN SPORTS"
)

print(
    "Mode: Channel scan"
)

print(
    "Match database requirement: DISABLED"
)

print(
    "Arabic titles: ENABLED"
)

print(
    "Gaming filter: ENABLED"
)

print(
    "Embeddable videos: REQUIRED"
)

print("=" * 60)


# =========================================================
# CHANNEL
# =========================================================

channel_id, uploads_playlist = (
    get_bein_channel()
)


# =========================================================
# GET LATEST VIDEOS
# =========================================================

playlist_items = get_latest_videos(
    uploads_playlist
)


# =========================================================
# VIDEO IDS
# =========================================================

video_ids = []


for item in playlist_items:

    content = item.get(
        "contentDetails",
        {}
    )


    video_id = content.get(
        "videoId"
    )


    if video_id:

        video_ids.append(
            video_id
        )


# =========================================================
# GET DETAILS
# =========================================================

video_details = get_video_details(
    video_ids
)


print("=" * 60)

print(
    "Inspecting videos..."
)

print(
    f"Videos inspected: "
    f"{len(video_details)}"
)

print("=" * 60)


# =========================================================
# LOAD OLD
# =========================================================

old_highlights = (
    load_old_highlights()
)


old_ids = set()


for item in old_highlights:

    if not isinstance(
        item,
        dict
    ):

        continue


    video_id = (

        item.get(
            "highlight_id"
        )

        or

        item.get(
            "youtube_id"
        )

    )


    if video_id:

        old_ids.add(
            str(video_id)
        )


# =========================================================
# FIND NEW HIGHLIGHTS
# =========================================================

new_highlights = []


now = datetime.now(
    timezone.utc
)


cutoff = (

    now

    - timedelta(
        days=LOOKBACK_DAYS
    )

)


for video_id in video_ids:

    video = video_details.get(
        video_id
    )


    if not video:

        continue


    snippet = video.get(
        "snippet",
        {}
    )


    status = video.get(
        "status",
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


    published_at = str(
        snippet.get(
            "publishedAt",
            ""
        )
    )


    print("-" * 60)

    print(
        "Checking:",
        title
    )


    # -----------------------------------------------------
    # Correct channel
    # -----------------------------------------------------

    result_channel = str(
        snippet.get(
            "channelId",
            ""
        )
    )


    if result_channel != channel_id:

        print(
            "REJECTED: wrong channel"
        )

        continue


    # -----------------------------------------------------
    # Already saved
    # -----------------------------------------------------

    if video_id in old_ids:

        print(
            "Already saved:",
            video_id
        )

        continue


    # -----------------------------------------------------
    # Date
    # -----------------------------------------------------

    parsed_date = parse_youtube_date(
        published_at
    )


    if parsed_date:

        if parsed_date < cutoff:

            print(
                "REJECTED: older than "
                f"{LOOKBACK_DAYS} days"
            )

            continue


    # -----------------------------------------------------
    # Embeddable
    # -----------------------------------------------------

    embeddable = status.get(
        "embeddable",
        False
    )


    if not embeddable:

        print(
            "REJECTED: not embeddable"
        )

        continue


    # -----------------------------------------------------
    # Privacy
    # -----------------------------------------------------

    privacy = status.get(
        "privacyStatus",
        ""
    )


    if privacy not in {

        "public",

    }:

        print(
            "REJECTED: not public"
        )

        continue


    # -----------------------------------------------------
    # Gaming
    # -----------------------------------------------------

    if is_gaming(
        " ".join([
            title,
            description
        ])
    ):

        print(
            "REJECTED: gaming"
        )

        continue


    # -----------------------------------------------------
    # Real football highlight
    # -----------------------------------------------------

    if not is_real_highlight(
        title,
        description
    ):

        print(
            "REJECTED: not a football "
            "match highlight"
        )

        continue


    # -----------------------------------------------------
    # ACCEPT
    # -----------------------------------------------------

    print(
        "SELECTED REAL FOOTBALL HIGHLIGHT:"
    )

    print(
        title
    )


    item = build_highlight(

        video,

        channel_id

    )


    new_highlights.append(
        item
    )


    old_ids.add(
        video_id
    )


    # -----------------------------------------------------
    # Limit
    # -----------------------------------------------------

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

    +

    old_highlights

):

    if not isinstance(
        item,
        dict
    ):

        continue


    video_id = (

        item.get(
            "highlight_id"
        )

        or

        item.get(
            "youtube_id"
        )

    )


    if not video_id:

        continue


    video_id = str(
        video_id
    )


    if video_id in seen:

        continue


    seen.add(
        video_id
    )


    # -----------------------------------------------------
    # Make sure old records also have embed fields
    # -----------------------------------------------------

    if not item.get(
        "youtube_id"
    ):

        item["youtube_id"] = video_id


    if not item.get(
        "embed_url"
    ):

        item["embed_url"] = (
            "https://www.youtube.com/embed/"
            + video_id
        )


    if not item.get(
        "embed"
    ):

        item["embed"] = (
            "https://www.youtube.com/embed/"
            + video_id
        )


    if not item.get(
        "url"
    ):

        item["url"] = (
            "https://www.youtube.com/watch?v="
            + video_id
        )


    combined.append(
        item
    )


# =========================================================
# SORT NEWEST FIRST
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


# =========================================================
# KEEP LAST 50
# =========================================================

combined = combined[
    :MAX_HIGHLIGHTS
]


# =========================================================
# SAVE
# =========================================================

os.makedirs(
    "data",
    exist_ok=True
)


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
# FINAL RESULT
# =========================================================

print("=" * 60)

print(
    "GOALINS HIGHLIGHTS RESULT"
)

print("=" * 60)

print(
    f"YouTube search.list calls: 0"
)

print(
    f"Channel videos inspected: "
    f"{len(video_details)}"
)

print(
    f"New football highlights: "
    f"{len(new_highlights)}"
)

print(
    f"Total saved: "
    f"{len(combined)}"
)

print(
    "Source: Official beIN SPORTS channel"
)

print(
    "Match database matching: DISABLED"
)

print(
    "Arabic titles: ENABLED"
)

print(
    "Gaming filter: ENABLED"
)

print(
    "Embeddable videos: REQUIRED"
)

print(
    "Real football highlights only."
)

print("=" * 60)
