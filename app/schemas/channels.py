from pydantic import BaseModel


class ChannelID(BaseModel):
    channel_id: str

class ChannelResponse(BaseModel):
    channel_id: str
    channel_name: str
    subscriber: int
    total_videos: int