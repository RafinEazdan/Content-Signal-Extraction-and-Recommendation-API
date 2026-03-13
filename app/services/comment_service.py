from fastapi import HTTPException
import googleapiclient.discovery
from app.core.config import settings


YT_API_KEY = settings.YT_API_KEY

class CommentService:
    def __init__(self, db):
        self.db = db

    async def fetch_and_store_comment(self, video_db_id):
        video_id = self._get_video_id(video_db_id)
        api_service_name = "youtube"
        api_version = "v3"
        youtube = googleapiclient.discovery.build(
        api_service_name, api_version, developerKey=YT_API_KEY)

        request = youtube.commentThreads().list(
            part="snippet",
            videoId="tXt1m0Pmc0s",
            maxResults=100
        )
        response = request.execute()

        comments = []

        for item in response['items']:
            comment = item['snippet']['topLevelComment']['snippet']
            comments.append([
                comment['authorDisplayName'],
                comment['publishedAt'],
                comment['likeCount'],
                comment['textDisplay']
            ])


    def _get_video_id(self, video_db_id):
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT video_id FROM videos WHERE id = %s", (video_db_id,))
            video_id = cursor.fetchone()

            if not video_id:
                raise HTTPException(status_code=404, detail= "No such video found" )
            
            return video_id


        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error: {e}.")