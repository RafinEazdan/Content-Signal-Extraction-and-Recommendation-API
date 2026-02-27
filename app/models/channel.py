from sqlalchemy import Column, ForeignKey, Integer, String

from ..database.base import Base

class Channel(Base):
    __tablename__ = "channels"
    id = Column(Integer, primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    channel_id = Column(Integer, nullable=False)
    platform = Column(String, nullable=True)
    channel_title = Column(String, nullable=False)
    subscriber_count = Column(Integer, nullable=True)
    total_no_of_videos = Column(Integer, nullable=True)
