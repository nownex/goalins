import json
import os
import re
import requests

from datetime import datetime, timezone


# =========================================================
# GOALINS — beIN SPORTS DIRECT HIGHLIGHTS ENGINE
# =========================================================

API_KEY = os.environ.get("YOUTUBE_API_KEY")

if not API_KEY:
    raise RuntimeError("YOUTUBE_API_KEY is missing")


OUTPUT_FILE = "data/highlights.json"

CHANNELS_URL = (
    "https://www.googleapis.com/youtube/v3/channels"
)

PLAYLIST_ITEMS_URL = (
    "https://www.googleapis.com/youtube/v3/playlistItems"
)

VIDEOS_URL = (
    "https://www.googleapis.com/youtube/v3/videos"
)

BEIN_HANDLE = "@beinsports"

MAX_HIGHLIGHTS = 30

CHANNEL_VIDEO_LIMIT = 50


# =========================================================
# GAMING / NON-FOOTBALL FILTER
# =========================================================

REJECT_WORDS = [

    # Gaming
    "fifa",
    "ea fc",
    "fc 26",
    "fc26",
    "fc 25",
    "fc25",
    "efootball",
    "pes",
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
    "اي فوتبول",
    "إي فوتبول",

    # General non-match content
    "ترتيب",
    "جدول الترتيب",
    "قرعة",
    "موعد",
    "مواعيد",
    "توقعات",
    "تحليل",
    "تحليلات",
    "تصريحات",
    "تصريح",
    "مؤتمر صحفي",
    "مؤتمر صحافي",
    "خبر",
    "أخبار",
    "اخر الاخبار",
    "آخر الأخبار",
    "أخبار اليوم",
    "تقديم",
    "تغطية",
    "كواليس",
    "لقاء خاص",
    "حوار",
    "interview",
    "preview",
    "news",
    "analysis",
]


# =========================================================
# STRONG HIGHLIGHT WORDS
# =========================================================

HIGHLIGHT_WORDS = [

    "ملخص مباراة",
    "ملخص المباراه",
    "ملخص",

    "اهداف مباراة",
    "أهداف مباراة",
    "اهداف المباراه",
    "أهداف المباراة",

    "اهداف",
    "أهداف",

    "highlights",
    "match highlights",

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

    # Remove Arabic tashkeel
    text = re.sub(
        r"[\u064B-\u065F\u0670]",
        "",
        text
    )

    # Remove punctuation
    text = re.sub(
        r"[^a-z0-9\u0600-\u06ff]+",
        " ",
        text
    )

    return " ".join(
        text.split()
    )


# =========================================================
# GAMING
# =========================================================

def is_gaming(text):

    value = normalize(text)

    for word in REJECT_WORDS:

        if normalize(word) in value:

            if normalize(word) in {
                normalize(x)
                for x in [
                    "fifa",
                    "ea fc",
                    "fc 26",
                    "fc26",
                    "fc 25",
                    "fc25",
                    "efootball",
                    "pes",
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
                    "اي فوتبول",
                    "إي فوتبول",
                ]
            }:
                return True

    return False


# =========================================================
# REJECT GENERAL CONTENT
# =========================================================

def is_general_content(title):

    value = normalize(title)

    general_words = [

        "ترتيب",
        "جدول الترتيب",
        "قرعة",
        "موعد",
        "مواعيد",
        "توقعات",
        "تحليل",
        "تحليلات",
        "تصريحات",
        "تصريح",
        "مؤتمر صحفي",
        "مؤتمر صحافي",
        "خبر",
        "اخبار",
        "اخر الاخبار",
        "اخر اخبار",
        "تقديم",
        "تغطيه",
        "كواليس",
        "لقاء خاص",
        "حوار",
        "interview",
        "preview",
        "news",
        "analysis",
    ]

    for word in general_words:

        if normalize(word) in value:

            return True

    return False


# =========================================================
# IS FOOTBALL HIGHLIGHT
# =========================================================

def is_match_highlight(
    title,
    description=""
):

    text = normalize(
        f"{title} {description}"
    )

    # Never accept gaming
    if is_gaming(text):
        return False

    # Never accept obvious general/news videos
    if is_general_content(title):
        return False

    # Strong highlight signal
    for word in HIGHLIGHT_WORDS:

        if normalize(word) in text:

            return True

    return False


# =========================================================
# GET CHANNEL
# =========================================================

def get_channel():

    print("=" * 60)
    print("GETTING beIN SPORTS CHANNEL")
    print("=" * 60)

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
        "Channels HTTP:",
        response.status_code
    )

    response.raise_for_status()

    data = response.json()

    items = data.get(
        "items",
        []
    )

    if not items:

        raise RuntimeError(
            "beIN SPORTS channel was not found."
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
            "beIN channel ID is missing."
        )

    if not uploads_playlist:

        raise RuntimeError(
            "beIN uploads playlist is missing."
        )

    print(
        "Channel ID:",
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
# GET CHANNEL VIDEOS
#
# IMPORTANT:
# playlistItems.list
# NOT search.list
# =========================================================

def get_channel_videos(
    uploads_playlist
):

    print("=" * 60)
    print("GETTING LATEST beIN SPORTS VIDEOS")
    print("=" * 60)

    params = {

        "part":
            "snippet,contentDetails",

        "playlistId":
            uploads_playlist,

        "maxResults":
            CHANNEL_VIDEO_LIMIT,

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
# EXTRACT DATE FROM TITLE
# =========================================================

def extract_match_info(
    title
):

    """
    We intentionally do not require the match
    to exist in matches.json.

    The title itself is enough to display
    the video.
    """

    clean_title = str(
        title or ""
    ).strip()

    home = ""
    away = ""
    league = ""

    # -----------------------------------------------------
    # Common Arabic format:
    #
    # ملخص مباراة X و Y | الدوري ...
    # -----------------------------------------------------

    patterns = [

        r"ملخص مباراة\s+(.+?)\s+(?:و|ضد|امام|أمام)\s+(.+?)(?:\||$)",

        r"ملخص\s+(.+?)\s+(?:و|ضد|امام|أمام)\s+(.+?)(?:\||$)",

        r"اهداف مباراة\s+(.+?)\s+(?:و|ضد|امام|أمام)\s+(.+?)(?:\||$)",

        r"أهداف مباراة\s+(.+?)\s+(?:و|ضد|امام|أمام)\s+(.+?)(?:\||$)",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            clean_title,
            flags=re.IGNORECASE
        )

        if match:

            home = match.group(
                1
            ).strip()

            away = match.group(
                2
            ).strip()

            break


    # -----------------------------------------------------
    # Extract league after |
    # -----------------------------------------------------

    if "|" in clean_title:

        parts = clean_title.split(
            "|"
        )

        if len(parts) >= 2:

            league = parts[-1].strip()

    return (
        home,
        away,
        league
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
            "Could not read old highlights:",
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

    if item.get(
        "highlight_id"
    )

}


# =========================================================
# MAIN
# =========================================================

print("=" * 60)

print(
    "GOALINS — DIRECT beIN SPORTS "
    "HIGHLIGHTS ENGINE"
)

print("=" * 60)

print(
    "No search.list is used."
)

print(
    "No matches.json matching is required."
)


# =========================================================
# CHANNEL
# =========================================================

channel_id, uploads_playlist = (
    get_channel()
)


# =========================================================
# LATEST VIDEOS
# =========================================================

playlist_items = (
    get_channel_videos(
        uploads_playlist
    )
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


video_ids = list(
    dict.fromkeys(
        video_ids
    )
)


print(
    "Unique video IDs:",
    len(video_ids)
)


# =========================================================
# DETAILS
# =========================================================

details = get_video_details(
    video_ids
)


# =========================================================
# COLLECT REAL MATCH HIGHLIGHTS
# =========================================================

new_highlights = []

seen_ids = set()


for item in playlist_items:

    content = item.get(
        "contentDetails",
        {}
    )

    snippet = item.get(
        "snippet",
        {}
    )

    video_id = content.get(
        "videoId"
    )

    if not video_id:

        continue

    if video_id in seen_ids:

        continue

    seen_ids.add(
        video_id
    )

    title = str(
        snippet.get(
            "title",
            ""
        )
    ).strip()

    description = str(
        snippet.get(
            "description",
            ""
        )
    ).strip()

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
    # OLD VIDEO
    # -----------------------------------------------------

    if video_id in old_ids:

        print(
            "Already saved."
        )

        continue


    # -----------------------------------------------------
    # GAMING
    # -----------------------------------------------------

    if is_gaming(
        f"{title} {description}"
    ):

        print(
            "REJECTED: gaming."
        )

        continue


    # -----------------------------------------------------
    # EMBEDDING
    # -----------------------------------------------------

    detail = details.get(
        video_id,
        {}
    )

    status = detail.get(
        "status",
        {}
    )

    embeddable = status.get(
        "embeddable",
        True
    )

    if embeddable is False:

        print(
            "REJECTED: not embeddable."
        )

        continue


    # -----------------------------------------------------
    # HIGHLIGHT TEST
    # -----------------------------------------------------

    if not is_match_highlight(
        title,
        description
    ):

        print(
            "REJECTED: not a match highlight."
        )

        continue


    # -----------------------------------------------------
    # EXTRACT INFO
    # -----------------------------------------------------

    home, away, league = (
        extract_match_info(
            title
        )
    )


    thumbnail = (

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

    )


    if not thumbnail:

        thumbnail = (

            snippet

            .get(
                "thumbnails",
                {}
            )

            .get(
                "medium",
                {}
            )

            .get(
                "url"
            )

        )


    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    print(
        "SELECTED REAL FOOTBALL HIGHLIGHT:"
    )

    print(
        title
    )


    item_output = {

        "highlight_id":
            video_id,

        "fixture_id":
            None,

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

        "youtube_id":
            video_id,

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
            published_at[:10],

        "league":
            league,

        "home":
            home,

        "away":
            away,

        "published_at":
            published_at,

    }


    new_highlights.append(
        item_output
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

    video_id = str(
        item.get(
            "highlight_id",
            ""
        )
    )

    if not video_id:

        continue

    if video_id in seen:

        continue

    seen.add(
        video_id
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
        "YouTube / beIN SPORTS",

    "channel":
        BEIN_HANDLE,

    "channel_id":
        channel_id,

    "type":
        "OFFICIAL",

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
    "YouTube search.list calls: 0"
)

print(
    f"Channel videos inspected: "
    f"{len(playlist_items)}"
)

print(
    f"New match highlights: "
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

print("=" * 60)
