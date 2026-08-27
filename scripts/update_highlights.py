import json
import os
import re
import requests

from datetime import datetime, timezone, timedelta


# =========================================================
# GOALINS — BEIN SPORTS HIGHLIGHTS ENGINE
# =========================================================
#
# IMPORTANT:
#
# This engine does NOT use matches.json.
#
# It scans the official beIN SPORTS YouTube channel directly.
#
# It does NOT use YouTube search.list.
#
# It DOES NOT require videos to be embeddable.
#
# Why?
#
# beIN SPORTS MENA may block YouTube iframe embedding.
# The video can still be opened normally on YouTube.
#
# GOALINS therefore saves the video and uses:
#
# https://www.youtube.com/watch?v=VIDEO_ID
#
# for opening the video.
#
# =========================================================


# =========================================================
# API
# =========================================================

API_KEY = os.environ.get(
    "YOUTUBE_API_KEY"
)

if not API_KEY:

    raise RuntimeError(
        "YOUTUBE_API_KEY is missing"
    )


# =========================================================
# FILES
# =========================================================

OUTPUT_FILE = (
    "data/highlights.json"
)


# =========================================================
# YOUTUBE API
# =========================================================

CHANNELS_URL = (
    "https://www.googleapis.com/youtube/v3/channels"
)

PLAYLIST_ITEMS_URL = (
    "https://www.googleapis.com/youtube/v3/playlistItems"
)

VIDEOS_URL = (
    "https://www.googleapis.com/youtube/v3/videos"
)


# =========================================================
# BEIN SPORTS
# =========================================================

BEIN_HANDLE = (
    "@beinsports"
)


# =========================================================
# SETTINGS
# =========================================================

MAX_CHANNEL_VIDEOS = 50

MAX_HIGHLIGHTS = 50

LOOKBACK_DAYS = 14


# =========================================================
# HIGHLIGHT KEYWORDS
# =========================================================

HIGHLIGHT_WORDS = [

    # Arabic
    "ملخص مباراة",
    "ملخص المباراه",
    "ملخص المبار",
    "ملخص لقاء",
    "ملخص وأهداف",
    "ملخص واهداف",
    "ملخص و أهداف",
    "ملخص و اهداف",
    "أهداف مباراة",
    "اهداف مباراة",
    "أهداف المباراه",
    "اهداف المباراه",

    # English
    "highlights",
    "match highlights",
    "extended highlights",
    "full highlights",
    "match recap",

]


# =========================================================
# FOOTBALL WORDS
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
    "أهداف",
    "اهداف",
    "كرة القدم",
    "القدم",
    "دوري الأبطال",
    "دوري ابطال",
    "دوري أبطال",
    "أبطال أوروبا",
    "ابطال اوروبا",
    "الدوري الإنجليزي",
    "الدوري الانجليزي",
    "الدوري الإسباني",
    "الدوري الاسباني",
    "الدوري الإيطالي",
    "الدوري الايطالي",
    "الدوري الألماني",
    "الدوري الالماني",
    "الدوري الفرنسي",
    "الدوري التركي",
    "الدوري السعودي",
    "الدوري المصري",
    "الدوري المغربي",
    "الدوري القطري",
    "الدوري الإماراتي",
    "الدوري الاماراتي",
    "الدوري الهولندي",
    "الدوري البرتغالي",
    "الدوري الأوروبي",
    "الدوري الاوروبي",
    "دوري المؤتمر",
    "كأس العالم",
    "كاس العالم",

    # English
    "football",
    "soccer",
    "match",
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

]


# =========================================================
# WORDS THAT ARE NOT MATCH HIGHLIGHTS
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
    "تصريحات",
    "تصريح",
    "مؤتمر صحفي",
    "مؤتمر",
    "كواليس",
    "انتقال",
    "انتقالات",
    "صفقة",
    "صفقات",
    "سوق الانتقالات",
    "تحليل",
    "تحليلات",
    "استوديو",
    "استديو",
    "برنامج",
    "حلقة",
    "تقرير",
    "تقارير",
    "توقعات",
    "preview",

    # English
    "news",
    "transfer",
    "transfers",
    "breaking",
    "analysis",
    "studio",
    "interview",
    "press conference",
    "podcast",
    "report",
    "preview",

]


# =========================================================
# GAMING
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


# =========================================================
# CONTAINS
# =========================================================

def contains(
    text,
    words
):

    value = normalize(
        text
    )


    for word in words:

        if normalize(word) in value:

            return True


    return False


# =========================================================
# GAMING
# =========================================================

def is_gaming(text):

    return contains(
        text,
        GAMING_WORDS
    )


# =========================================================
# STRONG MATCH TITLE
# =========================================================

def is_strong_highlight_title(
    title
):

    value = normalize(
        title
    )


    strong_words = [

        "ملخص مباراة",
        "ملخص المباراه",
        "ملخص لقاء",
        "ملخص وأهداف",
        "ملخص واهداف",
        "أهداف مباراة",
        "اهداف مباراة",
        "highlights",
        "match highlights",
        "extended highlights",
        "full highlights",
        "match recap",

    ]


    for word in strong_words:

        if normalize(word) in value:

            return True


    return False


# =========================================================
# REAL FOOTBALL HIGHLIGHT
# =========================================================

def is_real_highlight(
    title,
    description
):

    combined = " ".join([

        str(title or ""),

        str(description or ""),

    ])


    # -----------------------------------------------------
    # Gaming
    # -----------------------------------------------------

    if is_gaming(
        combined
    ):

        return False, (
            "gaming content"
        )


    # -----------------------------------------------------
    # Must look like highlight
    # -----------------------------------------------------

    if not contains(
        title,
        HIGHLIGHT_WORDS
    ):

        return False, (
            "no highlight keyword"
        )


    # -----------------------------------------------------
    # News / analysis
    # -----------------------------------------------------

    if contains(
        title,
        NEWS_WORDS
    ):

        if not is_strong_highlight_title(
            title
        ):

            return False, (
                "news/analysis content"
            )


    # -----------------------------------------------------
    # Football context
    # -----------------------------------------------------

    if not contains(
        combined,
        FOOTBALL_WORDS
    ):

        # Important:
        #
        # Arabic beIN titles may only contain:
        #
        # "ملخص مباراة فنربهتشة وقونيا سبور"
        #
        # In that case "مباراة" itself is enough.
        #

        value = normalize(
            title
        )


        if "مباراة" not in value:

            if "مباراه" not in value:

                return False, (
                    "no football context"
                )


    return True, (
        "real football highlight"
    )


# =========================================================
# FIND BEIN CHANNEL
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

        CHANNELS_URL,

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
            "beIN SPORTS channel not found"
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
            "beIN channel ID missing"
        )


    if not uploads_playlist:

        raise RuntimeError(
            "beIN uploads playlist missing"
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
# GET LATEST VIDEOS
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

        PLAYLIST_ITEMS_URL,

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
# GET VIDEO DETAILS
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

        VIDEOS_URL,

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


        if video_id:

            result[
                video_id
            ] = item


    return result


# =========================================================
# LOAD OLD HIGHLIGHTS
# =========================================================

def load_old():

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

            result = data.get(
                "highlights",
                []
            )


            if isinstance(
                result,
                list
            ):

                return result


        if isinstance(
            data,
            list
        ):

            return data


    except Exception as error:

        print(
            "Old data error:",
            error
        )


    return []


# =========================================================
# DATE
# =========================================================

def parse_date(
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
# BUILD ITEM
# =========================================================

def build_item(
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


    thumbnail = ""


    for size in [

        "maxres",
        "standard",
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


    published_date = ""


    parsed = parse_date(
        published_at
    )


    if parsed:

        published_date = (
            parsed
            .date()
            .isoformat()
        )


    watch_url = (
        "https://www.youtube.com/watch?v="
        + video_id
    )


    embed_url = (
        "https://www.youtube.com/embed/"
        + video_id
    )


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

        # Kept for compatibility
        "embed":
            embed_url,

        "embed_url":
            embed_url,

        # IMPORTANT:
        # Frontend should open THIS URL.
        "url":
            watch_url,

        "youtube_url":
            watch_url,

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
    "GOALINS — BEIN SPORTS HIGHLIGHTS ENGINE"
)

print("=" * 60)

print(
    "Source: Official beIN SPORTS"
)

print(
    "Mode: Direct channel scan"
)

print(
    "Match database: DISABLED"
)

print(
    "Arabic titles: ENABLED"
)

print(
    "Gaming filter: ENABLED"
)

print(
    "Embeddable requirement: DISABLED"
)

print(
    "YouTube search.list: DISABLED"
)

print("=" * 60)


# =========================================================
# CHANNEL
# =========================================================

channel_id, uploads_playlist = (
    get_bein_channel()
)


# =========================================================
# LATEST VIDEOS
# =========================================================

playlist_items = get_latest_videos(
    uploads_playlist
)


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


print(
    "Video IDs found:",
    len(video_ids)
)


# =========================================================
# DETAILS
# =========================================================

videos = get_video_details(
    video_ids
)


print(
    "Videos inspected:",
    len(videos)
)


# =========================================================
# OLD DATA
# =========================================================

old_highlights = load_old()


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


print(
    "Already saved:",
    len(old_ids)
)


# =========================================================
# CUTOFF
# =========================================================

now = datetime.now(
    timezone.utc
)


cutoff = (

    now

    - timedelta(
        days=LOOKBACK_DAYS
    )

)


# =========================================================
# SCAN
# =========================================================

new_highlights = []


for video_id in video_ids:

    video = videos.get(
        video_id
    )


    if not video:

        print(
            "SKIP:",
            video_id,
            "details unavailable"
        )

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
        "CHECKING VIDEO:"
    )

    print(
        "ID:",
        video_id
    )

    print(
        "TITLE:",
        title
    )

    print(
        "PUBLISHED:",
        published_at
    )


    # -----------------------------------------------------
    # CHANNEL
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
    # OLD
    # -----------------------------------------------------

    if video_id in old_ids:

        print(
            "SKIPPED: already saved"
        )

        continue


    # -----------------------------------------------------
    # DATE
    # -----------------------------------------------------

    parsed = parse_date(
        published_at
    )


    if parsed:

        if parsed < cutoff:

            print(
                "REJECTED: older than",
                LOOKBACK_DAYS,
                "days"
            )

            continue


    # -----------------------------------------------------
    # PRIVACY
    # -----------------------------------------------------

    privacy = status.get(
        "privacyStatus",
        ""
    )


    if privacy != "public":

        print(
            "REJECTED: privacy =",
            privacy
        )

        continue


    # -----------------------------------------------------
    # DO NOT CHECK EMBEDDABLE
    # -----------------------------------------------------
    #
    # This is intentional.
    #
    # beIN may block iframe embedding.
    # We still want the video on GOALINS.
    #
    # The frontend will open YouTube.
    #
    # -----------------------------------------------------

    print(
        "Embeddable check: SKIPPED"
    )


    # -----------------------------------------------------
    # GAMING
    # -----------------------------------------------------

    if is_gaming(
        title + " " + description
    ):

        print(
            "REJECTED: gaming"
        )

        continue


    # -----------------------------------------------------
    # HIGHLIGHT
    # -----------------------------------------------------

    accepted, reason = (
        is_real_highlight(
            title,
            description
        )
    )


    if not accepted:

        print(
            "REJECTED:",
            reason
        )

        continue


    # -----------------------------------------------------
    # ACCEPT
    # -----------------------------------------------------

    print(
        "=============================================="
    )

    print(
        "SELECTED REAL FOOTBALL HIGHLIGHT"
    )

    print(
        title
    )

    print(
        "YouTube URL:"
    )

    print(
        "https://www.youtube.com/watch?v="
        + video_id
    )

    print(
        "=============================================="
    )


    item = build_item(

        video,

        channel_id

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
    # Compatibility
    # -----------------------------------------------------

    item[
        "youtube_id"
    ] = video_id


    item[
        "url"
    ] = (
        "https://www.youtube.com/watch?v="
        + video_id
    )


    item[
        "youtube_url"
    ] = (
        "https://www.youtube.com/watch?v="
        + video_id
    )


    item[
        "embed"
    ] = (
        "https://www.youtube.com/embed/"
        + video_id
    )


    item[
        "embed_url"
    ] = (
        "https://www.youtube.com/embed/"
        + video_id
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


# =========================================================
# KEEP 50
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
# FINAL
# =========================================================

print("=" * 60)

print(
    "GOALINS HIGHLIGHTS RESULT"
)

print("=" * 60)

print(
    "YouTube search.list calls: 0"
)

print(
    "Channel videos inspected:",
    len(videos)
)

print(
    "New football highlights:",
    len(new_highlights)
)

print(
    "Total saved:",
    len(combined)
)

print(
    "Source: Official beIN SPORTS"
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
    "Embeddable requirement: DISABLED"
)

print(
    "Videos open on YouTube: ENABLED"
)

print("=" * 60)
