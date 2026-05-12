from psycopg import Connection
from datetime import date
import httpx
from fastapi import HTTPException, status
from app.core.config import settings

YT_API_KEY = settings.YT_API_KEY

class video_metrics:
    def __init__(self, db: Connection, redis):
        self.db = db
        self.redis = redis

    async def get_metrics(self, channel_db_id):
        """
        Fetch and store video metrics for a single channel
        """
        # Validate channel exists
        if not self._channel_exists(channel_db_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Channel with id {channel_db_id} not found"
            )
        
        cursor = self.db.cursor()
        
        # Get all videos for the channel
        cursor.execute('''
            SELECT id, video_id 
            FROM videos 
            WHERE channel_db_id = %s;
        ''', (channel_db_id,))
        
        videos = cursor.fetchall()
        # cursor.close()
        
        if not videos:
            return {
                "success": True,
                "message": "No videos found for this channel",
                "metrics_count": 0,
                "data": []
            }
        
        # Extract video IDs for batch API request
        video_ids = [video['video_id'] for video in videos]
        video_db_ids = {video['video_id']: video['id'] for video in videos}
        
        # Fetch metrics from YouTube API (batch request - up to 50 videos)
        metrics_data = []
        
        # Process in chunks of 50 (YouTube API limit)
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i:i + 50]
            chunk_metrics = await self._fetch_youtube_metrics(chunk)
            metrics_data.extend(chunk_metrics)
        
        # Store metrics in database
        self._store_metrics(metrics_data, video_db_ids)
        
        # Format and return response
        formatted_metrics = self._format_metrics_response(metrics_data)
        
        return {
            "success": True,
            "message": f"Successfully fetched metrics for {len(metrics_data)} videos",
            "metrics_count": len(metrics_data),
            "data": formatted_metrics
        }

    

    def _channel_exists(self, channel_db_id: int) -> bool:
        """
        Check if channel exists in database
        """
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT id FROM channels WHERE id = %s;",
            (channel_db_id,)
        )
        channel = cursor.fetchone()
        # cursor.close()
        return channel is not None

    def _store_metrics(self, metrics_data: list, video_db_ids: dict):
        """
        Store metrics in database
        """
        cursor = self.db.cursor()
        today = date.today()
        
        for metric in metrics_data:
            video_id = metric['video_id']
            video_db_id = video_db_ids.get(video_id)
            
            if not video_db_id:
                continue
            
            views = metric['views']
            likes = metric['likes']
            comments_count = metric['comments_count']
            
            # Calculate engagement rate: (likes + comments) / views * 100
            engagement_rate = (
                ((likes + comments_count) / views * 100) 
                if views > 0 else 0.0
            )
            # Upsert metrics (insert or update if exists for today)
            cursor.execute('''
                INSERT INTO video_metrics 
                (video_db_id, date, views, likes, comments_count, engagement_rate)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (video_db_id, date) 
                DO UPDATE SET
                    views = EXCLUDED.views,
                    likes = EXCLUDED.likes,
                    comments_count = EXCLUDED.comments_count,
                    engagement_rate = EXCLUDED.engagement_rate;
            ''', (video_db_id, today, views, likes, comments_count, engagement_rate))
        
        self.db.commit()
        # cursor.close()

    def _format_metrics_response(self, metrics_data: list) -> list:
        """
        Format metrics data for API response
        """
        formatted_metrics = []
        today = date.today()
        
        for metric in metrics_data:
            views = metric['views']
            likes = metric['likes']
            comments = metric['comments_count']
            engagement_rate = ((likes + comments) / views * 100) if views > 0 else 0.0
            
            formatted_metrics.append({
                "video_id": metric['video_id'],
                "date": today,
                "views": views,
                "likes": likes,
                "comments_count": comments,
                "engagement_rate": round(engagement_rate, 2)
            })
        
        return formatted_metrics

    async def _fetch_youtube_metrics(self, video_ids: list) -> list:
        """
        Fetch video statistics from YouTube Data API v3
        """
        if not video_ids:
            return []
        
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            'part': 'statistics',
            'id': ','.join(video_ids),
            'key': YT_API_KEY
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        metrics = []
        for item in data.get('items', []):
            stats = item.get('statistics', {})
            metrics.append({
                'video_id': item['id'],
                'views': int(stats.get('viewCount', 0)),
                'likes': int(stats.get('likeCount', 0)),
                'comments_count': int(stats.get('commentCount', 0))
            })
        
        return metrics