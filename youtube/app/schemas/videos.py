from typing import Optional

from pydantic import BaseModel

class VideoRequest(BaseModel):
    channel_handle: str

class VideoBase(BaseModel):
    video_id: str
    title: str
    description: Optional[str] = None
    published_at: str
    channel_id: str

class VideoResponse(BaseModel):
    newly_added_video_count: int