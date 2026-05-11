from pydantic import BaseModel


class ChannelRequest(BaseModel):
    channel_handle: str

class ChannelResponse(BaseModel):
    channel_id: str
    channel_title: str
    channel_handle: str
    subscriber_count: int
    upload_playlist: str