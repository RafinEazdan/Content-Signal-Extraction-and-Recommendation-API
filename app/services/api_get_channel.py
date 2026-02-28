from fastapi import HTTPException
import requests

from app.core.config import settings


YT_API_KEY = settings.YT_API_KEY

async def get_channel(channel_handle):
    search_url = "https://www.googleapis.com/youtube/v3/search"
    search_params = {
    "part": "snippet",
    "q": channel_handle,
    "type": "channel",
    "maxResults": 1,
    "key": YT_API_KEY
}

    search_res = requests.get(search_url, params=search_params).json()

    if not search_res.get("items"):
        raise HTTPException

    CHANNEL_ID = search_res["items"][0]["id"]["channelId"]

# Step 2: Get channel details
    channel_url = "https://www.googleapis.com/youtube/v3/channels"
    channel_params = {
    "part": "snippet,statistics,contentDetails",
    "id": CHANNEL_ID,
    "key": YT_API_KEY
}

    res = requests.get(channel_url, params=channel_params).json()

    if not res.get("items"):
        raise HTTPException
    

    item = res["items"][0]

    channel_title = item["snippet"]["title"]
    subscriber_count = item["statistics"].get("subscriberCount", "Hidden")
    subscriber_count = int(subscriber_count) if subscriber_count else None

    upload_playlist = item["contentDetails"]["relatedPlaylists"]["uploads"]

    return {
    "channel_id": CHANNEL_ID,
    "channel_title": channel_title,
    "subscriber_count": subscriber_count,
    "upload_playlist": upload_playlist,
}

def get_video_list(CHANNEL_ID, upload_playlist ):
# Step 3: Get all videos
    videos = []
    next_page = None

    while True:
        playlist_url = "https://www.googleapis.com/youtube/v3/playlistItems"
        playlist_params = {
        "part": "snippet,contentDetails",
        "playlistId": upload_playlist,
        "maxResults": 50,
        "pageToken": next_page,
        "key": YT_API_KEY
    }

        data = requests.get(playlist_url, params=playlist_params).json()

        if "items" not in data:
            print("Playlist error:", data)
            break

        videos.extend(data["items"])
        next_page = data.get("nextPageToken")

        if not next_page:
            break

    video_list = [
        {
        "video_id": v["contentDetails"]["videoId"],
        "title": v["snippet"]["title"],
        "published_at": v["snippet"]["publishedAt"]
        }
        for v in videos
]
    return video_list