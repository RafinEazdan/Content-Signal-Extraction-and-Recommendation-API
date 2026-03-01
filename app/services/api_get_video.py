from fastapi import HTTPException
import requests

from app.core.config import settings


YT_API_KEY = settings.YT_API_KEY

def get_video_list(CHANNEL_ID, upload_playlist ):
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
        "description": v["snippet"]["description"],
        "published_at": v["snippet"]["publishedAt"],
        "channel_id": v["snippet"]["channelId"]
        }
        for v in videos
]
    return video_list