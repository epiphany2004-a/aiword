from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File
from sqlalchemy.orm import Session
from db.database import get_db
from api.login import get_current_user
from schemas.score import EssayScoreRequest, EssayScoreResponse
from api.agent import deepseek_agent_get_essay_structure, extract_json_from_text, gemini_ocr
import base64
import json
from datetime import datetime
import os
import uuid
from typing import List
from models.score import UserEssayResult

score_router = APIRouter(prefix="/api", tags=["Score"])

@score_router.post("/essay-score", summary="作文评分")
async def score_essay(request: EssayScoreRequest, http_request: Request, db: Session = Depends(get_db)):
    """
    对作文进行AI评分，接收作文题目、图片、内容和图片
    """
    try:
        # 检查用户登录状态
        user = get_current_user(http_request, db)
        if not user:
            raise HTTPException(status_code=401, detail="请先登录")
        
        # 在控制台打印接收到的数据
        print("=" * 50)
        print("作文评分请求 -", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("用户ID:", user.id)
        print("=" * 50)
        
        print("作文题目:")
        print(request.essay_title)
        print()
        
        if request.essay_title_image:
            print("作文题目图片: 已上传 (base64数据长度:", len(request.essay_title_image), ")")
        else:
            print("作文题目图片: 无")
        print()
        
        print("作文内容:")
        print(request.essay_content)
        print()
        
        if request.essay_image:
            print("作文图片: 已上传 (base64数据长度:", len(request.essay_image), ")")
        else:
            print("作文图片: 无")
        print()
        
        print("=" * 50)
        print("开始AI评分...")
        
        # 调用DeepSeek AI进行作文评分
        try:
            ai_response = deepseek_agent_get_essay_structure(request.essay_title, request.essay_content)
            print("AI响应:", ai_response)
            
            # 提取JSON数据
            ai_result = extract_json_from_text(ai_response)
            print("解析后的AI结果:", ai_result)
            
            # 构建响应数据
            response_data = {
                "status": "success",
                "score": ai_result.get("score", 16),
                "radar_data": ai_result.get("radarData", [4, 3, 3, 4, 4]),
                "suggestions": ai_result.get("suggestions", []),
                "message": "AI评分完成"
            }
            
            # 保存到数据库
            essay_record = UserEssayResult(
                user_id=user.id,
                essay_title=request.essay_title,
                essay_content=request.essay_content,
                score=response_data["score"],
                radar_data=response_data["radar_data"],
                suggestions=response_data["suggestions"]
            )
            db.add(essay_record)
            db.commit()
            db.refresh(essay_record)
            
            print("返回数据:", response_data)
            return EssayScoreResponse(**response_data)
            
        except Exception as ai_error:
            print(f"AI评分出错: {str(ai_error)}")
            # 如果AI评分失败，返回模拟数据
            print("使用模拟数据作为备选方案")
            mock_response = {
                "status": "success",
                "score": 16,
                "radar_data": [4, 3, 3, 4, 4],  # 逻辑, 词汇, 句式, 语法, 相关性
                "suggestions": [
                    {
                        "id": 1,
                        "text": "shown in the picture",
                        "type": "upgradeable",
                        "suggestion": "vividly depicted in the cartoon"
                    },
                    {
                        "id": 2,
                        "text": "put together",
                        "type": "upgradeable", 
                        "suggestion": "harmoniously blended"
                    }
                ],
                "message": "AI评分失败，使用模拟数据"
            }
            return EssayScoreResponse(**mock_response)
        
    except Exception as e:
        print(f"作文评分出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"评分失败: {str(e)}")

@score_router.post("/score-essay-from-image", summary="从图片评分作文")
async def score_essay_from_image(
    http_request: Request,
    db: Session = Depends(get_db),
    essay_images: List[UploadFile] = File(...)
):
    """
    接收一张或多张作文图片，进行OCR识别后，再进行AI评分
    """
    temp_files_info = []
    try:
        user = get_current_user(http_request, db)
        if not user:
            raise HTTPException(status_code=401, detail="请先登录")

        # 1. 保存上传的所有图片到临时文件
        # 使用绝对路径确保在 Docker 中正常工作
        temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp_images")
        os.makedirs(temp_dir, exist_ok=True)
        
        for image in essay_images:
            file_extension = os.path.splitext(image.filename)[1]
            temp_filename = f"{uuid.uuid4()}{file_extension}"
            temp_filepath = os.path.join(temp_dir, temp_filename)
            
            with open(temp_filepath, "wb") as buffer:
                buffer.write(await image.read())
            
            temp_files_info.append((temp_filepath, image.content_type))
            print(f"图片已保存到: {temp_filepath}")

        # 2. 调用gemini_ocr进行文字识别
        try:
            ocr_text_raw = gemini_ocr(temp_files_info)
            ocr_result = extract_json_from_text(ocr_text_raw)
            print("OCR 识别结果:", ocr_result)
        except Exception as ocr_error:
            print(f"OCR识别出错: {str(ocr_error)}")
            raise HTTPException(status_code=400, detail=f"图片文字识别失败: {str(ocr_error)}")

        essay_title = ocr_result.get("title", "")
        essay_content = ocr_result.get("writing", "")

        if not essay_content:
            raise HTTPException(status_code=400, detail="图片识别成功，但未能提取到有效的作文内容。")

        # 3. 调用DeepSeek进行作文评分
        try:
            ai_response = deepseek_agent_get_essay_structure(essay_title, essay_content)
            ai_result = extract_json_from_text(ai_response)
            
            response_data = {
                "status": "success",
                "score": ai_result.get("score"),
                "radar_data": ai_result.get("radarData"),
                "suggestions": ai_result.get("suggestions"),
                "message": "AI评分完成",
                "ocr_result": ocr_result
            }
            # 保存到数据库
            essay_record = UserEssayResult(
                user_id=user.id,
                essay_title=essay_title,
                essay_content=essay_content,
                score=response_data["score"],
                radar_data=response_data["radar_data"],
                suggestions=response_data["suggestions"]
            )
            db.add(essay_record)
            db.commit()
            db.refresh(essay_record)
            return response_data
            
        except Exception as ai_error:
            print(f"AI评分出错: {str(ai_error)}")
            raise HTTPException(status_code=500, detail=f"AI评分失败: {str(ai_error)}")
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        print(f"作文评分过程出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")
    finally:
        # 4. 清理所有临时文件
        for path, _ in temp_files_info:
            if os.path.exists(path):
                os.remove(path)
        print("临时图片已全部清理")

@score_router.get("/essay-history", summary="获取用户作文历史记录")
async def get_essay_history(http_request: Request, db: Session = Depends(get_db)):
    user = get_current_user(http_request, db)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    records = db.query(UserEssayResult).filter_by(user_id=user.id).order_by(UserEssayResult.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "essay_title": r.essay_title,
            "score": r.score,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "essay_content": r.essay_content,
            "radar_data": r.radar_data,
            "suggestions": r.suggestions
        }
        for r in records
    ]
