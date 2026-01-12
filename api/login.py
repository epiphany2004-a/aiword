from fastapi import APIRouter, HTTPException, Depends, Response, Request
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timedelta
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

from models.user import User, Session as SessionModel
from schemas.user import UserCreate, UserResponse
from db.database import get_db

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBasic()

def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def create_session(db: Session, user_id: int) -> str:
    """创建会话"""
    # 生成会话令牌
    session_token = secrets.token_urlsafe(32)
    # 设置过期时间（24小时后）
    expires_at = datetime.now() + timedelta(hours=24)
    
    # 创建会话记录
    session = SessionModel(
        session_token=session_token,
        user_id=user_id,
        expires_at=expires_at
    )
    
    db.add(session)
    db.commit()
    return session_token

def get_current_user(request: Request, db: Session) -> User:
    """获取当前用户"""
    session_token = request.cookies.get("session")
    if not session_token:
        raise HTTPException(
            status_code=401,
            detail="未登录"
        )
    
    try:
        # 查找会话
        session = db.query(SessionModel).filter(
            SessionModel.session_token == session_token,
            SessionModel.expires_at > datetime.now()
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=401,
                detail="会话已过期"
            )
        
        # 查找用户
        user = db.query(User).filter(User.id == session.user_id).first()
        if not user:
            raise HTTPException(
                status_code=401,
                detail="用户不存在"
            )
        
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取用户信息失败: {str(e)}"
        )

class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str
    password: str

@router.post("/api/register")
async def register(user: UserCreate, response: Response, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查用户名是否已存在
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(
            status_code=400,
            detail="用户名已存在"
        )
    
    # 检查邮箱是否已存在
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(
            status_code=400,
            detail="邮箱已被注册"
        )
    
    # 创建新用户
    db_user = User(
        username=user.username,
        email=user.email,
        password_hash=get_password_hash(user.password),
        created_at=datetime.now()
    )
    
    try:
        # 保存到数据库
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        # 注册成功后重定向到登录页面
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"注册失败: {str(e)}"
        )

@router.post("/api/login")
async def login(login_data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """用户登录"""
    # 查找用户
    user = db.query(User).filter(User.username == login_data.username).first()
    if not user:
        raise HTTPException(
            status_code=400,
            detail="用户名或密码错误"
        )
    
    # 验证密码
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=400,
            detail="用户名或密码错误"
        )
    
    # 更新最后登录时间
    user.last_login_at = datetime.now()
    
    # 创建会话
    session_token = create_session(db, user.id)
    
    # 设置登录状态
    response = JSONResponse(content={"message": "登录成功", "username": user.username})
    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        max_age=3600*24,  # 24小时过期
        samesite="lax"
    )
    return response

@router.get("/api/check-login")
async def check_login(request: Request, db: Session = Depends(get_db)):
    """检查登录状态"""
    try:
        user = get_current_user(request, db)
        return {"status": "logged_in", "username": user.username}
    except HTTPException:
        raise HTTPException(status_code=401, detail="未登录")

@router.post("/api/logout")
async def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    """退出登录"""
    session_token = request.cookies.get("session")
    if session_token:
        # 删除会话记录
        db.query(SessionModel).filter(SessionModel.session_token == session_token).delete()
        db.commit()
    
    response = JSONResponse(content={"message": "已退出登录"})
    response.delete_cookie(key="session")
    return response