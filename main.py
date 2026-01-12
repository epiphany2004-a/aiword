from fastapi import FastAPI
from fastapi.responses import FileResponse
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from pathlib import Path
from api.login import router as login_router
from api.setting import setting_router
from api.learning import router as learning_router
from api.get_log import log_router
from api.score import score_router
# 导入所有模型以确保它们被注册
from models.user import User, Session
from models.user_setting import UserSetting
from api.review import review_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)   

# 注册路由
app.include_router(login_router)
app.include_router(setting_router)
app.include_router(learning_router)
app.include_router(log_router)
app.include_router(review_router)
app.include_router(score_router)

# 获取项目根目录（在 Docker 中为 /app）
BASE_DIR = Path(__file__).parent

@app.get("/")
async def read_root():
    file_path = BASE_DIR / "static" / "html" / "login.html"
    return FileResponse(str(file_path))

@app.get("/index")
async def read_index():
    file_path = BASE_DIR / "static" / "html" / "index.html"
    return FileResponse(str(file_path))

@app.get("/register")
async def read_register():
    file_path = BASE_DIR / "static" / "html" / "register.html"
    return FileResponse(str(file_path))

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    for route in app.routes:
        print(route.path)
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
