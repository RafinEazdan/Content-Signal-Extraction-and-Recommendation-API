from pydantic import BaseModel


class RequestRedditFetch(BaseModel):
    subreddit: str
    limit: int = 20


class RedditPost(BaseModel):
    text: str
    likes: int


class ResponseRedditFetch(BaseModel):
    subreddit: str
    post_count: int
    posts: list[RedditPost]


class RequestRedditTopics(BaseModel):
    subreddit: str
    limit: int = 20
