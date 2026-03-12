from fastapi import APIRouter, HTTPException, Depends
from psycopg import Connection

from app.database.session import get_db
from app.redis.dependencies import get_redis
from app.services.metrics_video import video_metrics
from app.schemas.metrics import RequestMetrics, ResponseMetrics
from app.services.oauth import get_current_user
router = APIRouter(
    prefix='/metrics',
    tags=['metrics']
)

@router.post('/',response_model=ResponseMetrics)
async def metrics(channel_id: RequestMetrics, db: Connection = Depends(get_db), redis = Depends(get_redis), current_user: dict = Depends(get_current_user) ):
    try:
        channel_db_id = channel_id.channel_db_id
        metrics_service = video_metrics(db, redis)
        metrics = await metrics_service.get_metrics(channel_db_id)
        return metrics

    except HTTPException:
        raise 

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error occured: {e}")
