from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from app.database.session import get_db
from app.schemas.channels import ChannelRequest, ChannelResponse
from app.services.oauth import get_current_user
from app.services.get_channel import get_channel

router = APIRouter(
    prefix='/channels',
    tags=['Channels']
)

@router.post('/', response_model = ChannelResponse)
async def channels(channel_handle: ChannelRequest ,db: Connection= Depends(get_db), current_user: dict = Depends(get_current_user)):
    CHANNEL_ID, channel_name, subscriber_count, uploads_playlist = await get_channel(channel_handle)

    # print(CHANNEL_ID, channel_name, subscriber_count, uploads_playlist)

    return {
    "channel_id": CHANNEL_ID,
    "channel_name": channel_name,
    "subscriber_count": subscriber_count
}