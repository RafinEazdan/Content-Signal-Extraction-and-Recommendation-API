from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from app.database.base import Base


class RedditTrendingPost(Base):
    __tablename__ = "reddit_trending_posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(String(20), nullable=False)
    title = Column(Text, nullable=False)
    subreddit = Column(String(100), nullable=False)
    upvotes = Column(Integer, nullable=False)
    num_comments = Column(Integer, nullable=False)
    trend_score = Column(Float, nullable=False)
    url = Column(String(500))
    # discriminates which query this snapshot belongs to (general vs specific)
    cache_key = Column(String(300), nullable=False, index=True)
    mode = Column(String(20), nullable=False)
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
