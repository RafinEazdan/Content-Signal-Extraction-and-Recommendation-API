from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from app.database.session import get_db
from app.models import video
from app.services.oauth import get_current_user
from app.services.video_service import VideoService
from app.schemas.videos import VideoRequest, VideoResponse

router = APIRouter(
    prefix='/videos',
    tags=['Videos']
)

@router.post('/store', response_model=VideoResponse)
async def store_video(req: VideoRequest, db: Connection = Depends(get_db)):
    service = VideoService(db=db)
    result = await service.store_videos(req.channel_handle)

    return result
