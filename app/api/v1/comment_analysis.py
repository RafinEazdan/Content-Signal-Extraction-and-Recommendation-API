from fastapi import APIRouter, Depends, HTTPException

from app.services.comment_service import CommentService
from app.database.session import get_db
from app.schemas.comment_analysis import (
    RequestCommentAnalysis,
    RequestTopicExtraction,
    TopicExtractionResponse,
)

router = APIRouter()

@router.post("/comment_analysis")
async def comment_analysis(request: RequestCommentAnalysis, db = Depends(get_db)):
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


@router.post("/comment_topics", response_model=TopicExtractionResponse)
async def extract_comment_topics(request: RequestTopicExtraction, db=Depends(get_db)):
    service = CommentService(db)
    try:
        return await service.extract_comment_topics(
            video_db_id=request.video_db_id,
            provider=request.provider,
            model=request.model,
            top_k=request.top_k,
            chunk_size=request.chunk_size,
            per_chunk_topics=request.per_chunk_topics,
            max_parallel_requests=request.max_parallel_requests,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error occurred while extracting topics: {str(e)}")
