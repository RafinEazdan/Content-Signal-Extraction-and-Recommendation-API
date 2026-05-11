from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.redis.dependencies import get_redis
from app.redis.redis_client import RedisClient
from app.schemas.reddit import VideoIdeasRequest, VideoIdeasResponse
from app.services.idea_service import IdeaService
from app.services.reddit_service import RedditService

router = APIRouter(prefix="/ideas", tags=["Video Ideas"])


@router.post("/reddit", response_model=VideoIdeasResponse)
async def get_reddit_video_ideas(
    request: VideoIdeasRequest,
    db: Session = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    try:
        posts = await RedditService(db, redis).get_trending(request.mode, request.subreddits)
        ideas = IdeaService().generate_video_ideas(posts)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return VideoIdeasResponse(
        mode=request.mode,
        subreddits=request.subreddits,
        top_posts=posts,
        video_ideas=ideas,
    )
