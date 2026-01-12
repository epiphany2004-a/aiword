from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, not_, func
from datetime import datetime, timedelta, date
import json

from models.user import User
from models.word import Word, UserWordProgress, WordDictionary, Book, BookWordLink
from models.user_setting import UserSetting
from models.userlearninglogs import UserLearningLogs
from db.database import get_db
from api.login import get_current_user
from api.agent import gemini_process_word_list,deepseek_process_sentence_list, deepseek_process_word_list

router = APIRouter(prefix="/api")

@router.get("/start-task")
async def start_task(request: Request, db: Session = Depends(get_db)):
    """开始学习任务"""
    try:
        # 获取当前登录用户
        user = get_current_user(request, db)
        
        # 获取用户设置
        user_setting = db.query(UserSetting).filter(UserSetting.id == user.id).first()
        if not user_setting:
            raise HTTPException(status_code=404, detail="用户设置不存在")
        
        # 获取今天的学习日志
        today = date.today()
        today_log = db.query(UserLearningLogs).filter(
            UserLearningLogs.id == user.id,
            UserLearningLogs.log_date == today
        ).first()
        
        # 计算今天已经学习的新单词数量
        today_learned_count = today_log.new_words_learned if today_log else 0
        
        # 计算还需要学习的新单词数量
        remaining_words = user_setting.daily_goal - today_learned_count
        
        # 如果已经完成今日目标，返回空列表
        if remaining_words <= 0:
            return {
                "status": "success",
                "user_id": user.id,
                "username": user.username,
                "daily_goal": user_setting.daily_goal,
                "current_book": user_setting.book_id,
                "words": [],
                "message": "恭喜你，已完成今日目标",
                "today_learned": today_learned_count,
                "remaining": 0
            }
        
        # 获取当前词书下所有单词ID
        book_word_ids = db.query(BookWordLink.word_id).filter(BookWordLink.book_id == user_setting.book_id).subquery()
        # 获取用户未学习的单词，限制为剩余需要学习的数量
        new_words = db.query(Word).filter(
            Word.word_id.in_(book_word_ids)
        ).outerjoin(
            UserWordProgress,
            and_(
                UserWordProgress.word_id == Word.word_id,
                UserWordProgress.user_id == user.id
            )
        ).filter(
            UserWordProgress.word_id == None
        ).limit(remaining_words).all()
        
        # 准备返回数据
        words_data = []
        words_without_content = []
        
        for word in new_words:
            # 从中央字典表获取单词解释
            word_dict = db.query(WordDictionary).filter(
                WordDictionary.word_id == word.word_id
            ).first()
            
            if word_dict and word_dict.content:
                # 如果已有解释，直接使用
                word_data = {
                    "word_id": word.word_id,
                    "word": word.word,
                    "content": word_dict.content
                }
                words_data.append(word_data)
            else:
                # 如果没有解释，添加到待处理列表
                words_without_content.append(word.word)
        
        # 如果有需要获取解释的单词，使用agent处理
        if words_without_content:
            try:
                # 使用agent获取单词解释
                word_explanations = deepseek_process_word_list(words_without_content)
                
                # 处理获取到的解释
                for word in words_without_content:
                    try:
                        # 查找对应的Word对象
                        word_obj = next((w for w in new_words if w.word == word), None)
                        if word_obj:
                            # 查找对应的解释
                            explanation = next((exp for exp in word_explanations if exp.get("word") == word), None)
                            
                            if explanation:
                                # 将解释转换为JSON字符串
                                content = json.dumps(explanation, ensure_ascii=False)
                            else:
                                # 如果没有找到解释，使用空字符串
                                content = ""
                            
                            # 检查是否已存在记录
                            existing_dict = db.query(WordDictionary).filter(
                                WordDictionary.word_id == word_obj.word_id
                            ).first()
                            
                            if existing_dict:
                                # 如果记录已存在，更新内容
                                existing_dict.content = content
                                existing_dict.created_at = datetime.now()
                            else:
                                # 如果记录不存在，创建新记录
                                word_dict = WordDictionary(
                                    word_id=word_obj.word_id,
                                    word=word,
                                    content=content,
                                    created_at=datetime.now()
                                )
                                db.add(word_dict)
                            
                            # 添加到返回数据
                            word_data = {
                                "word_id": word_obj.word_id,
                                "word": word,
                                "content": content
                            }
                            words_data.append(word_data)
                    except Exception as e:
                        print(f"处理单词 '{word}' 时发生错误: {str(e)}")
                        db.rollback()  # 回滚当前单词的事务
                        continue
                
                # 提交数据库更改
                try:
                    db.commit()
                except Exception as e:
                    print(f"提交数据库更改时发生错误: {str(e)}")
                    db.rollback()
                    raise
            except Exception as e:
                print(f"获取单词解释时发生错误: {str(e)}")
                db.rollback()  # 回滚整个事务
                # 即使获取解释失败，也继续返回已有的单词数据
                for word in words_without_content:
                    try:
                        word_obj = next((w for w in new_words if w.word == word), None)
                        if word_obj:
                            # 检查是否已存在记录
                            existing_dict = db.query(WordDictionary).filter(
                                WordDictionary.word_id == word_obj.word_id
                            ).first()
                            
                            if not existing_dict:
                                # 创建空解释的记录
                                word_dict = WordDictionary(
                                    word_id=word_obj.word_id,
                                    word=word,
                                    content="",
                                    created_at=datetime.now()
                                )
                                db.add(word_dict)
                            
                            # 添加到返回数据
                            word_data = {
                                "word_id": word_obj.word_id,
                                "word": word,
                                "content": ""
                            }
                            words_data.append(word_data)
                    except Exception as e:
                        print(f"处理单词 '{word}' 时发生错误: {str(e)}")
                        continue
                try:
                    db.commit()
                except Exception as e:
                    print(f"保存空解释记录时发生错误: {str(e)}")
                    db.rollback()
        
        return {
            "status": "success",
            "user_id": user.id,
            "username": user.username,
            "daily_goal": user_setting.daily_goal,
            "current_book": user_setting.book_id,
            "words": words_data,
            "message": "任务开始",
            "today_learned": today_learned_count,
            "remaining": remaining_words
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"启动任务失败: {str(e)}"
        )
    
@router.post("/save-progress")
async def save_progress(request: Request, db: Session = Depends(get_db)):
    """保存学习进度"""
    try:
        # 获取当前登录用户
        user = get_current_user(request, db)
        
        # 获取请求数据
        data = await request.json()
        word_id = data.get("word_id")
        status = data.get("status")  # dont_know, unsure, know
        
        if not word_id or not status:
            raise HTTPException(status_code=400, detail="缺少必要参数")
            
        # 验证单词是否存在
        word = db.query(Word).filter(Word.word_id == word_id).first()
        if not word:
            raise HTTPException(status_code=404, detail="单词不存在")
            
        # 获取当前进度记录
        progress = db.query(UserWordProgress).filter(
            UserWordProgress.user_id == user.id,
            UserWordProgress.word_id == word_id
        ).first()
        
        now = datetime.now()
        today = date.today()
        
        # 检查是否是今天第一次学习这个单词
        is_new_word_today = False
        if not progress:
            # 这是第一次学习这个单词
            progress = UserWordProgress(
                user_id=user.id,
                word_id=word_id,
                status=1,  # 学习中
                srs_level=0,
                correct_streak=0,
                created_at=now
            )
            db.add(progress)
            is_new_word_today = True
        
        # 更新学习状态
        if status == "dont_know":
            progress.status = 1  # 重新学习中
            progress.srs_level = max(0, progress.srs_level - 1)  # 降级，但不低于0
            progress.correct_streak = 0
            # 设置较短的复习间隔（1天后）
            progress.next_review_at = now + timedelta(days=1)
        elif status == "unsure":
            progress.status = 2  # 复习中
            progress.srs_level = progress.srs_level  # 保持当前等级
            progress.correct_streak = 0
            # 设置中等复习间隔（2天后）
            progress.next_review_at = now + timedelta(days=2)
        elif status == "know":
            progress.status = 2  # 复习中
            progress.srs_level += 1  # 升级
            progress.correct_streak += 1  # 增加连续答对次数
            
            # 根据SRS等级设置下次复习时间
            if progress.srs_level == 1:
                progress.next_review_at = now + timedelta(days=2)
            elif progress.srs_level == 2:
                progress.next_review_at = now + timedelta(days=3)
            elif progress.srs_level == 3:
                progress.next_review_at = now + timedelta(days=5)
            elif progress.srs_level == 4:
                progress.next_review_at = now + timedelta(days=7)
            elif progress.srs_level == 5:
                progress.next_review_at = now + timedelta(days=14)
            else:  # srs_level >= 6
                progress.status = 3  # 已掌握
                progress.next_review_at = now + timedelta(days=30)
        
        progress.last_reviewed_at = now
        
       
        try:
            db.commit()
            return {
                "status": "success",
                "message": "进度已保存",
                "data": {
                    "word_id": word_id,
                    "srs_level": progress.srs_level,
                    "next_review_at": progress.next_review_at.isoformat(),
                    "is_new_word": is_new_word_today
                }
            }
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"保存进度失败: {str(e)}"
            )
            
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"保存进度失败: {str(e)}"
        )
