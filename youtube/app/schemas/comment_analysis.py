from pydantic import BaseModel


class RequestCommentAnalysis(BaseModel):
    video_db_id: int

