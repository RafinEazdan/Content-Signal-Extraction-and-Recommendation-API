from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.database.base import Base


class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, nullable=False)
    comment_id = Column(String, unique=True, nullable=False)
    video_db_id = Column(
        Integer,
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False
    )
    published_at = Column(DateTime, nullable=False)
    author_name = Column(String, nullable=False )
    like_count = Column(Integer, nullable=True)
    text = Column(String, nullable=False)
    

