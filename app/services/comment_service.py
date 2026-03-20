from fastapi import HTTPException
from passlib import exc
from app.core.config import settings

from app.ai.pipeline import analyze_comments
from app.ai.comment_topic_extractor import CommentTopicExtractor

YT_API_KEY = settings.YT_API_KEY

import httpx
from fastapi import HTTPException

class CommentService:
    def __init__(self, db):
        self.db = db

    async def fetch_and_store_comment(self, video_db_id):
        try:
            video_id = self._get_video_id(video_db_id)

            url = "https://www.googleapis.com/youtube/v3/commentThreads"

            comments = []
            next_page_token = None

            async with httpx.AsyncClient(timeout=30) as client:

                while True:

                    params = {
                        "part": "snippet",
                        "videoId": video_id,
                        "maxResults": 100,
                        "key": YT_API_KEY
                    }

                    if next_page_token:
                        params["pageToken"] = next_page_token

                    response = await client.get(url, params=params)

                    if response.status_code != 200:
                        raise HTTPException(
                            status_code=400,
                            detail=f"YouTube API error: {response.text}"
                        )

                    data = response.json()

                    for item in data.get("items", []):

                        snippet = item["snippet"]["topLevelComment"]["snippet"]

                        comments.append({
                            "comment_id": item["snippet"]["topLevelComment"]["id"],
                            "author_name": snippet["authorDisplayName"],
                            "published_at": snippet["publishedAt"],
                            "like_count": snippet["likeCount"],
                            "text": snippet["textDisplay"],
                            "video_db_id": video_db_id
                        })

                    next_page_token = data.get("nextPageToken")

                    if not next_page_token:
                        break

            self._store_comments(comments)

            return comments
        
        except HTTPException:
            raise  # ← don't wrap it again in a 500
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error occurred while fetching comments: {str(e)}")

    def _get_video_id(self, video_db_id:int):
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT video_id FROM videos WHERE id = %s", (video_db_id,))
            row = cursor.fetchone()
            # print(row)
            if not row:
                raise HTTPException(status_code=404, detail="No such video found")
            return row["video_id"]   # return the value directly, not a dict
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching video id: {e}")
            
    def _store_comments(self, comments):

        if not comments:
            return

        try:
            with self.db.cursor() as cursor:

                values = [
                    (
                        c["comment_id"],
                        c["author_name"],
                        c["published_at"],
                        c["like_count"],
                        c["text"],
                        c["video_db_id"]
                    )
                    for c in comments
                ]

                cursor.executemany(
                    """
                    INSERT INTO comments
                    (comment_id, author_name, published_at, like_count, text, video_db_id)
                    VALUES (%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (comment_id) DO NOTHING
                    """,
                    values
                )

            self.db.commit()

        except Exception as e:
            raise Exception(f"Database insert failed: {e}")
        

    def _get_comments(self, video_db_id):
            try:
                cursor = self.db.cursor()
                cursor.execute("SELECT comment_id, text from comments where video_db_id::integer = %s;",(video_db_id,))
                rows = cursor.fetchall()

                if not rows:
                    raise HTTPException(status_code=404, detail="Comments not found!")
                

                comments = []
                comments = [
                            {"comment_id": row["comment_id"], "text": row["text"]}
                            for row in rows
                            ]
                return comments

            except HTTPException:
                print("HTTPException in _get_comments, re-raising")
                raise

            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error occured while fetching from database: {e}")
            
            finally:
                cursor.close()
            
    def _get_comments_with_likes(self, video_db_id):
            try:
                cursor = self.db.cursor()
                cursor.execute("SELECT comment_id, text, like_count from comments where video_db_id::integer = %s;",(video_db_id,))
                rows = cursor.fetchall()

                if not rows:
                    raise HTTPException(status_code=404, detail="Comments not found!")
                

                comments = []
                comments = [
                            {"comment_id": row["comment_id"], "text": row["text"], "likes": row["like_count"]}
                            for row in rows
                            ]
                return comments

            except HTTPException:
                print("HTTPException in _get_comments, re-raising")
                raise

            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error occured while fetching from database: {e}")
            
            finally:
                cursor.close()


    async def process_comments(self, video_db_id):
        comments = self._get_comments(video_db_id)
        analysis = await analyze_comments(comments)
        if not analysis:
            raise HTTPException(status_code=500, detail=f"Error fetching from the AI models")
        return analysis
    

    def generate_titles(self, video_db_id, refresh=False):
        try:
            if not refresh:
                cursor = self.db.cursor()
                cursor.execute("SELECT predicted_title FROM predicted_titles WHERE video_db_id = %s ORDER BY score ASC;", (video_db_id,))
                rows = cursor.fetchall()
                if rows:
                    return [row["predicted_title"] for row in rows]
            
            extractor = CommentTopicExtractor()
            comments = self._get_comments(video_db_id)
            topics = extractor.extract_topics(comments)
            titles = extractor.generate_titles(topics)
            self._store_generated_titles(video_db_id, titles)

            return titles

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error occurred while generating titles: {str(e)}")

    
    def _store_generated_titles(self, video_db_id, titles):
        try:
            cursor = self.db.cursor()
            for idx, title in enumerate(titles):
                cursor.execute(
                    """
                    INSERT INTO predicted_titles (video_db_id, predicted_title, score)
                    VALUES (%s, %s, %s)
                    """,
                    (video_db_id, title, idx+1)
                )

            self.db.commit()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error occurred while storing generated titles: {str(e)}")
