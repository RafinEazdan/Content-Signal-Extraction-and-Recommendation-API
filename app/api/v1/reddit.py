from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from app.schemas.reddit import RequestRedditFetch, RequestRedditTopics, ResponseRedditFetch
from app.services.reddit_service import RedditService
from app.services.trend_service import TrendService
from app.database.session import get_db
from app.services.oauth import get_current_user

router = APIRouter(
    prefix="/reddit",
    tags=["Reddit"],
)


@router.post("/fetch", response_model=ResponseRedditFetch)
async def fetch_reddit_posts(
    request: RequestRedditFetch,
    current_user: dict = Depends(get_current_user),
):
    """Fetch and cache Reddit posts for a subreddit."""
    try:
        service = RedditService()
        posts = await service.fetch_reddit_posts(request.subreddit, request.limit)
        return {
            "subreddit": request.subreddit,
            "post_count": len(posts),
            "posts": posts,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching Reddit posts: {str(e)}",
        )


@router.post("/topics")
async def extract_reddit_topics(
    request: RequestRedditTopics,
    db: Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Extract topics from a subreddit using the same pipeline as YouTube."""
    try:
        service = TrendService(db)
        topics = await service.extract_reddit_topics(request.subreddit, request.limit)
        return {"subreddit": request.subreddit, "topic_count": len(topics), "topics": topics}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error extracting Reddit topics: {str(e)}",
        )
