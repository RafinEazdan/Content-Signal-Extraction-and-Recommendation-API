from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from app.database.session import get_db
from app.schemas.channels import ChannelRequest, ChannelResponse
from app.services.oauth import get_current_user


router = APIRouter(
    prefix='/channels',
    tags=['Channels']
)

@router.post('/', response_model = ChannelResponse)
async def channels(channel_handle: ChannelRequest ,db: Connection= Depends(get_db), current_user: dict = Depends(get_current_user)):
    return