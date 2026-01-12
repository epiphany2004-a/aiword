from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from models.base import Base

class UserEssayResult(Base):
    __tablename__ = "user_essay_result"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    essay_title = Column(Text, nullable=False)
    essay_content = Column(Text, nullable=False)
    score = Column(Integer)
    radar_data = Column(JSON)
    suggestions = Column(JSON)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    user = relationship("User")
