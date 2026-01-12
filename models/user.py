from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base

class User(Base):
    """用户数据库模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_login_at = Column(DateTime, nullable=True)

    # 关联会话
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    # 关联设置
    setting = relationship("UserSetting", back_populates="user", uselist=False, cascade="all, delete-orphan")
    # 关联学习日志
    learning_logs = relationship("UserLearningLogs", back_populates="user")

    def __repr__(self):
        return f"<User {self.username}>"

class Session(Base):
    """会话数据库模型"""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=False)

    # 关联用户
    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<Session {self.session_token}>"
