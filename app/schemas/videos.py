from pydantic import BaseModel

class VideoRequest(BaseModel):
    video_id: str