from pydantic import BaseModel


class RequestTopicsFromComments(BaseModel):
    video_db_id: int


class ResponseTopicsFromComments(BaseModel):
    titles: list[str]