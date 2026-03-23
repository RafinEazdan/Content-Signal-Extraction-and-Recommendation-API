from aiohttp.web_routedef import route
from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from app.schemas.video_recommendation import RequestTopicsFromComments, ResponseTopicsFromComments
from app.services.comment_service import CommentService
from app.database.session import get_db
from app.services.oauth import get_current_user

router = APIRouter(
    prefix='/video_recommendation',
    tags=['Video Recommendation']
)

@router.post('/comments', response_model=ResponseTopicsFromComments)
def get_topics_from_comments(request: RequestTopicsFromComments, db: Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        comment_service = CommentService(db)
        titles = comment_service.generate_titles(request.video_db_id, request.refresh)
        # print(f"length of titles: {len(titles)}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error occurred while generating topics from comments: {str(e)}")
    return {"titles": titles}