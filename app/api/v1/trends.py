from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from app.schemas.trends import RequestMergedTopics, ResponseMergedTopics
from app.services.trend_service import TrendService
from app.database.session import get_db
from app.services.oauth import get_current_user

router = APIRouter(
    prefix="/trends",
    tags=["Trends"],
)


@router.post("/merged", response_model=ResponseMergedTopics)
async def get_merged_topics(
    request: RequestMergedTopics,
    db: Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Merge topics from YouTube comments and Reddit posts.

    Provide video_db_id for YouTube, subreddit for Reddit, or both.
    Topics appearing in multiple sources get a source_bonus.
    """
    if request.video_db_id is None and request.subreddit is None:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of: video_db_id (YouTube) or subreddit (Reddit)",
        )

    try:
        service = TrendService(db)
        topics = await service.get_merged_topics(
            video_db_id=request.video_db_id,
            subreddit=request.subreddit,
            reddit_limit=request.reddit_limit,
        )

        # store topics in DB
        if request.subreddit:
            service.store_topics(
                [t for t in topics if "reddit" in t["sources"]],
                "reddit",
                request.subreddit,
            )
        if request.video_db_id is not None:
            service.store_topics(
                [t for t in topics if "youtube" in t["sources"]],
                "youtube",
                str(request.video_db_id),
            )

        return {"topic_count": len(topics), "topics": topics}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error merging topics: {str(e)}",
        )
