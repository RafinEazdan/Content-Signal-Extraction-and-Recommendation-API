from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from app.database.session import get_db
from app.schemas.channels import ChannelRequest, ChannelResponse
from app.services.oauth import get_current_user
from app.services.api_get_channel import get_channel
from app.redis.dependencies import get_redis
from app.services.fetch_create_channel import fetch_create_channel


router = APIRouter(
    prefix='/channels',
    tags=['Channels']
)

@router.post('/', response_model = ChannelResponse)
async def fetch_channels(channel_handle: ChannelRequest ,db: Connection= Depends(get_db), redis = Depends(get_redis), current_user: dict = Depends(get_current_user)):
    channel_data = await fetch_create_channel(
        channel_handle=channel_handle.channel_handle,
        db=db,
        redis=redis,
    )

    return ChannelResponse(
        channel_id=channel_data["channel_id"],
        channel_title=channel_data["channel_title"],
        channel_handle=channel_handle.channel_handle,
        subscriber_count=channel_data["subscriber_count"],
        upload_playlist=channel_data["upload_playlist"]
    )