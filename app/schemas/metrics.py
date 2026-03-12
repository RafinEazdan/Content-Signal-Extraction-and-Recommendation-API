from datetime import date
from typing import List

from pydantic import BaseModel



class RequestMetrics(BaseModel):
    channel_db_id: int

class VideoMetricResponse(BaseModel):
    video_id: str
    date : date
    views: int
    likes: int
    comments_count: int
    engagement_rate: float


class ResponseMetrics(BaseModel):
    success: bool
    message: str
    metrics_count: int
    data: List[VideoMetricResponse]