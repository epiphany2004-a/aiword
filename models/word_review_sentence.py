from sqlalchemy import Column, Integer, String, JSON, TIMESTAMP
from models.base import Base
from datetime import datetime

class WordReviewSentence(Base):
    __tablename__ = "word_review_sentence"

    word_id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String(50), unique=True, nullable=False, index=True)
    content = Column(JSON, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.now)
