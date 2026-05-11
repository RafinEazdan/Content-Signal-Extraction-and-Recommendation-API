from datetime import datetime
from pydantic import BaseModel

class RequestComment(BaseModel):
    video_db_id: int

class ResponseCommentBase(BaseModel):
    comment_id: str
    video_db_id: int
    author_name: str
    text: str
    published_at: str

class ResponseComment(BaseModel):
    success: bool
    message: str
    comments: list[ResponseCommentBase]