from sqlalchemy import Column, ForeignKey, Integer, String

from ..database.base import Base

class Video(Base):
    __tablename__ = "videos"
    id = Column(Integer, primary_key=True, nullable=False)
    video_id = Column(String, nullable=False)
    video_title = Column(String, nullable=False)
    video_description = Column(String, nullable=True)
    published_at = Column(String, nullable=False)
    channel_id_url = Column(String, nullable=False)
    channel_db_id = Column(
        Integer,
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False
    )


