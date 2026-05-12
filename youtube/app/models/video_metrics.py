from sqlalchemy import Column, Integer, Float, Date, ForeignKey, String, UniqueConstraint
from app.database.base import Base

class VideoMetric(Base):
    __tablename__ = "video_metrics"

    id = Column(Integer, primary_key=True, nullable=False)

    video_db_id = Column(
        Integer,
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False
    )
    date = Column(Date, nullable=False)

    views = Column(Integer, nullable=False, default=0)
    likes = Column(Integer, nullable=False, default=0)
    comments_count = Column(Integer, nullable=False, default=0)
    engagement_rate = Column(Float, nullable=False, default=0.0)

    __table_args__ = (
        UniqueConstraint('video_db_id', 'date', name='uq_video_db_id_date'),
    )