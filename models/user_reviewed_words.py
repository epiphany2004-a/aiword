from sqlalchemy import Column, Integer, Date, TIMESTAMP, UniqueConstraint
from models.base import Base
from datetime import datetime

class UserReviewedWords(Base):
    __tablename__ = "user_reviewed_words"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    word_id = Column(Integer, nullable=False, index=True)
    review_date = Column(Date, nullable=False, index=True)
    reviewed = Column(Integer, default=1)  # 1=已复习
    created_at = Column(TIMESTAMP, default=datetime.now)
    __table_args__ = (
        UniqueConstraint('user_id', 'word_id', 'review_date', name='uq_user_word_date'),
    )
