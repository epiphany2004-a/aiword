from pydantic import BaseModel
from typing import Optional

class EssayScoreRequest(BaseModel):
    """作文评分请求模型"""
    essay_title: str
    essay_title_image: Optional[str] = None  # base64编码的图片数据
    essay_content: str
    essay_image: Optional[str] = None  # base64编码的图片数据

class EssayScoreResponse(BaseModel):
    """作文评分响应模型"""
    status: str
    score: int
    radar_data: list
    suggestions: list
    message: str
