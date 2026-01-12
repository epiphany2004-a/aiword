from fastapi import APIRouter, HTTPException, Depends, Response, Request
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

from models.user import User
from models.user_setting import UserSetting
from models.word import Book
from schemas.user_setting import UserSettingBase, UserSettingResponse
from db.database import get_db
from api.login import get_current_user


setting_router = APIRouter(prefix="/api")

@setting_router.get("/settings", response_model=UserSettingResponse)
async def get_settings(request: Request, db: Session = Depends(get_db)):
    """获取用户设置"""
    try:
        user = get_current_user(request, db)
        
        # 获取或创建设置
        settings = db.query(UserSetting).filter(UserSetting.id == user.id).first()
        if not settings:
            # 获取默认词书
            default_book = db.query(Book).filter(Book.book_id == 1).first()
            if not default_book:
                raise HTTPException(status_code=404, detail="未找到默认词书")
                
            settings = UserSetting(
                id=user.id,
                daily_goal=20,  # 默认每日学习目标
                book_id=1,  # 设置默认词书ID为1
                review_mode=1,  # 默认标准模式
                default_pronounce=1  # 默认美式发音
            )
            db.add(settings)
            db.commit()
            db.refresh(settings)
        
        # 获取词书信息
        book = db.query(Book).filter(Book.book_id == settings.book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="未找到选择的词书")
            
        # 构建返回数据
        response_data = {
            "id": settings.id,
            "daily_goal": settings.daily_goal,
            "book_id": settings.book_id,
            "book_name": book.book_name,  # 使用正确的字段名
            "review_mode": settings.review_mode,
            "default_pronounce": settings.default_pronounce
        }
        
        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取设置失败: {str(e)}"
        )

@setting_router.post("/settings", response_model=UserSettingResponse)
async def update_settings(
    settings: UserSettingBase,
    request: Request,
    db: Session = Depends(get_db)
):
    """更新用户设置"""
    try:
        user = get_current_user(request, db)
        
        # 验证词书是否存在
        if settings.book_id:
            book = db.query(Book).filter(Book.book_id == settings.book_id).first()
            if not book:
                raise HTTPException(status_code=404, detail="选择的词书不存在")
        else:
            # 如果没有指定词书，使用默认词书ID 1
            settings.book_id = 1
        
        # 获取或创建设置
        db_settings = db.query(UserSetting).filter(UserSetting.id == user.id).first()
        if not db_settings:
            db_settings = UserSetting(id=user.id)
            db.add(db_settings)
        
        # 更新设置
        db_settings.daily_goal = settings.daily_goal
        db_settings.book_id = settings.book_id
        db_settings.review_mode = settings.review_mode
        db_settings.default_pronounce = settings.default_pronounce
        
        db.commit()
        db.refresh(db_settings)
        
        # 获取词书信息
        book = db.query(Book).filter(Book.book_id == db_settings.book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="未找到选择的词书")
            
        # 构建返回数据
        response_data = {
            "id": db_settings.id,
            "daily_goal": db_settings.daily_goal,
            "book_id": db_settings.book_id,
            "book_name": book.book_name,  # 使用正确的字段名
            "review_mode": db_settings.review_mode,
            "default_pronounce": db_settings.default_pronounce
        }
        
        return response_data
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"保存设置失败: {str(e)}"
        )

@setting_router.get("/books")
async def get_books(db: Session = Depends(get_db)):
    """获取所有词书列表"""
    try:
        books = db.query(Book).all()
        result = [
            {
                "book_id": book.book_id,
                "book_name": book.book_name,
                "word_count": book.word_count
            }
            for book in books
        ]
        return {"status": "success", "books": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取词书列表失败: {str(e)}")




