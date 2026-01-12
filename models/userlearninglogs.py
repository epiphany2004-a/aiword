from sqlalchemy import Column, Integer, Date, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from models.base import Base

class UserLearningLogs(Base):
    """用户学习日志模型"""
    __tablename__ = "user_learning_logs"

    id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    log_date = Column(Date)
    new_words_learned = Column(Integer, default=0)
    words_reviewed = Column(Integer, default=0)

    # 设置复合主键
    __table_args__ = (
        PrimaryKeyConstraint('id', 'log_date'),
    )

    # 关联用户
    user = relationship("User", back_populates="learning_logs")
