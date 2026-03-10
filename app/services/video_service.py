from fastapi import HTTPException
from psycopg import Connection
import requests
import httpx

from app.core.config import settings


YT_API_KEY = settings.YT_API_KEY


class VideoService:
    def __init__(self, db: Connection):
        self.db = db
    
    def _get_channel_db_id(self, channel_handle: str) -> int:

        cursor =  self.db.cursor()
        cursor.execute(
                "SELECT id, channel_id, upload_playlist FROM channels WHERE channel_handle = %s",
                (channel_handle,),
            )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Channel '{channel_handle}' not found in database."
            )
        return {
    "id": row["id"],
    "upload_playlist": row["upload_playlist"],
    "channel_handle": channel_handle
}
    


    async def get_video_list(self, channel_handle):
        videos = []
        next_page = None

        get_upload_playlist = self._get_channel_db_id(channel_handle)
        upload_playlist = get_upload_playlist["upload_playlist"]

        async with httpx.AsyncClient() as client:
            playlist_url = "https://www.googleapis.com/youtube/v3/playlistItems"

            playlist_params = {
                    "part": "snippet,contentDetails",
                    "playlistId": upload_playlist,
                    "maxResults": 20,
                    "pageToken": next_page,
                    "key": YT_API_KEY
                }

            response = await client.get(playlist_url, params=playlist_params)
            data = response.json()

            if "items" not in data:
                print("Playlist error:", data)
                return []
        

            videos.extend(data["items"])
            next_page = data.get("nextPageToken")

                # if not next_page:
                #     break

        video_list = [
            {
                "video_id": v["contentDetails"]["videoId"],
                "title": v["snippet"]["title"],
                "description": v["snippet"]["description"],
                "published_at": v["snippet"]["publishedAt"],
                "channel_id_url": v["snippet"]["channelId"],
            }
            for v in videos
        ]

        return video_list
    

    async def store_videos(self, channel_handle: str):
        get_channel_db_id = self._get_channel_db_id(channel_handle)
        channel_db_id = get_channel_db_id['id']
        # channel_id = get_channel_db_id['channel_id']
        video_list = await self.get_video_list(channel_handle)

        if not video_list:
            return 0

        inserted_count = 0

        cursor =  self.db.cursor()
        for video in video_list:
            cursor.execute(
                    """
                    INSERT INTO videos (
                        video_id,
                        video_title,
                        video_description,
                        published_at,
                        channel_id_url,
                        channel_db_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (video_id) DO NOTHING
                    """,
                    (
                        video["video_id"],
                        video["title"],
                        video["description"],
                        video["published_at"],
                        video["channel_id_url"],
                        channel_db_id,
                    ),
                )
            inserted_count += cursor.rowcount

        self.db.commit()
        return {
            "newly_added_video_count":inserted_count
        }

    def get_stored_videos(self, channel_db_id: int):
        cursor =  self.db.cursor()
        cursor.execute(
                """
                SELECT id, video_id, video_title, video_description, published_at, channel_id_url
                FROM videos
                WHERE channel_db_id = %s
                ORDER BY published_at DESC
                """,
                (channel_db_id,),
            )
        rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "video_id": row[1],
                "video_title": row[2],
                "video_description": row[3],
                "published_at": row[4],
                "channel_id_url": row[5],
            }
            for row in rows
        ]