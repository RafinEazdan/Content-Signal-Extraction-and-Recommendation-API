from pydantic import BaseModel


class RequestCommentAnalysis(BaseModel):
    video_db_id: int


class RequestTopicExtraction(BaseModel):
    video_db_id: int
    provider: str = "huggingface"
    model: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    top_k: int = 30
    chunk_size: int = 40
    per_chunk_topics: int = 20
    max_parallel_requests: int = 4


class TopicItem(BaseModel):
    topic: str
    count: int


class TopicExtractionResponse(BaseModel):
    provider: str
    model: str
    total_comments: int
    chunks_processed: int
    topics: list[TopicItem]
    next_video_ideas: list[str]

