from fastapi import APIRouter, Depends, HTTPException

from app.services.comment_service import CommentService
from app.database.session import get_db
from app.schemas.comment_analysis import RequestCommentAnalysis
from app.services.oauth import get_current_user

router = APIRouter()

@router.post("/comment_analysis")
async def comment_analysis(request: RequestCommentAnalysis, db = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = CommentService(db)
    try:
        comment_analysis_result = await service.process_comments(request.video_db_id)
        print(comment_analysis_result)
        return comment_analysis_result
    except HTTPException:
        print("HTTPException in comment_analysis endpoint, re-raising")
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error occurred while analyzing comments: {str(e)}")
