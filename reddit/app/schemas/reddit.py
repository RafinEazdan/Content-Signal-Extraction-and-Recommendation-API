from typing import Literal
from pydantic import BaseModel, model_validator


class VideoIdeasRequest(BaseModel):
    mode: Literal["general", "specific"]
    subreddits: list[str] | None = None

    @model_validator(mode="after")
    def validate_subreddits(self):
        if self.mode == "specific":
            if not self.subreddits:
                raise ValueError("subreddits is required when mode is 'specific'")
            if len(self.subreddits) > 3:
                raise ValueError("maximum 3 subreddits allowed")
        return self


class TrendingPost(BaseModel):
    post_id: str
    title: str
    subreddit: str
    upvotes: int
    num_comments: int
    trend_score: float
    url: str | None


class VideoIdeasResponse(BaseModel):
    mode: str
    subreddits: list[str] | None
    top_posts: list[TrendingPost]
    video_ideas: list[str]
