from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    """用户基础信息"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")

class UserCreate(UserBase):
    """创建用户时的数据模式"""
    password: str = Field(..., min_length=6, max_length=50, description="密码")

class UserInDB(UserBase):
    """数据库中的用户信息"""
    id: int
    password_hash: str
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserResponse(UserBase):
    """返回给客户端的用户信息"""
    id: int
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True
