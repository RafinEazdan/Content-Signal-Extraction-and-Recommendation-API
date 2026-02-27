from pydantic import BaseModel


class ChannelRequest(BaseModel):
    channel_handle: str

class ChannelResponse(BaseModel):
    channel_id: str
    channel_name: str
    subscriber: int
    total_videos: int