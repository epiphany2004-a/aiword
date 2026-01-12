from pydantic import BaseModel, Field
from typing import Optional

class UserSettingBase(BaseModel):
    """用户设置基础模型"""
    daily_goal: int = Field(default=50, ge=1, le=200, description="每日学习目标")
    review_mode: int = Field(default=1, ge=1, le=3, description="复习模式")
    default_pronounce: int = Field(default=1, ge=1, le=2, description="默认发音")
    book_id: int = Field(default=1, description="当前词书ID")

class UserSettingResponse(UserSettingBase):
    """用户设置响应模型"""
    id: int
    book_name: Optional[str] = None

    class Config:
        from_attributes = True
