from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection
from youtube.app.services import comment_service
from youtube.app.services.comment_service import CommentService
from youtube.app.database.session import get_db
from youtube.app.schemas.comments import ResponseComment, RequestComment
from youtube.app.services.oauth import get_current_user

router = APIRouter()

@router.post("/fetch-comments", response_model=ResponseComment)
async def fetch_comments(video_db_id: RequestComment, db: Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = CommentService(db)
    try:
        comments = await service.fetch_and_store_comment(video_db_id.video_db_id)
        return {
            "success": True,
            "message": f"Fetched and stored comments for video_db_id {video_db_id.video_db_id}",
            "comments": comments
        }
    except HTTPException:
        raise 
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error occurred while fetching comments: {str(e)}")