from sqlalchemy import TIMESTAMP, Column, Integer, String, text

from app.database.base import Base


class Source(Base):
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True, nullable=False)
    type = Column(String, nullable=False)           # "youtube", "reddit", "rss"
    external_id = Column(String, nullable=False)    # video_id / subreddit_name
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text('now()')
    )
