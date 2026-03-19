from app.database.base import Base

from sqlalchemy import TIMESTAMP, Column, Integer, String, text

class PredictedTitle(Base):
    __tablename__ = "predicted_titles"
    id = Column(Integer, primary_key=True, nullable=False)
    video_db_id = Column(Integer, nullable=False)
    predicted_title = Column(String, nullable=False)
    score = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    