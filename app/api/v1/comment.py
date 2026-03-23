from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection
from app.services import comment_service
from app.services.comment_service import CommentService
from app.database.session import get_db
from app.schemas.comments import ResponseComment, RequestComment
from app.services.oauth import get_current_user

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