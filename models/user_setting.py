from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base

class UserSetting(Base):
    """用户设置模型"""
    __tablename__ = "users_setting"

    id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    daily_goal = Column(Integer, default=30)
    review_mode = Column(Integer, default=1)
    default_pronounce = Column(Integer, default=1)
    book_id = Column(Integer, ForeignKey("books.book_id"), default=1)

    # 关联用户
    user = relationship("User", back_populates="setting")
    # 关联词书
    book = relationship("Book")
