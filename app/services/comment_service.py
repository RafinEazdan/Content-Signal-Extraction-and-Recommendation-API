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
            videoId=video_id,
            maxResults=100
        )
        response = request.execute()

        comments = {}

        for item in response['items']:
            comment = item['snippet']['topLevelComment']['snippet']
            comments.append({
                "comment_id": item['snippet']['topLevelComment']['id'],
                "author_name": comment['authorDisplayName'],
                "published_at": comment['publishedAt'],
                "like_count": comment['likeCount'],
                "text": comment['textDisplay'],
                "video_db_id": video_db_id
            })

        cursor = self.db.cursor()
        for comment in comments:
            cursor.execute(
            """
            INSERT INTO comments (comment_id, author_name, published_at, like_count, text, video_db_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (comment_id) DO NOTHING
            """,
            (
                comment["comment_id"],
                comment["author_name"],
                comment["published_at"],
                comment["like_count"],
                comment["text"],
                comment["video_db_id"]
            )
            )
        self.db.commit()

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