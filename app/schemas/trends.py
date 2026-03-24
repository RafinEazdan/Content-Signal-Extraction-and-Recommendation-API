from pydantic import BaseModel


class RequestMergedTopics(BaseModel):
    video_db_id: int | None = None
    subreddit: str | None = None
    reddit_limit: int = 20


class MergedTopic(BaseModel):
    topic: str
    score: float
    count: int
    likes: int
    intent_count: int
    sources: list[str]


class ResponseMergedTopics(BaseModel):
    topic_count: int
    topics: list[MergedTopic]
