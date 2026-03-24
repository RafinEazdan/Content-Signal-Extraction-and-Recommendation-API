from sqlalchemy import TIMESTAMP, Column, Float, ForeignKey, Integer, String, text

from app.database.base import Base


class Topic(Base):
    __tablename__ = "topics"
    id = Column(Integer, primary_key=True, nullable=False)
    source_id = Column(
        Integer,
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False
    )
    topic = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    count = Column(Integer, nullable=False, default=0)
    likes = Column(Integer, nullable=False, default=0)
    intent_count = Column(Integer, nullable=False, default=0)
    source_type = Column(String, nullable=False)    # "youtube", "reddit"
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text('now()')
    )
