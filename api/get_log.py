from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from models.userlearninglogs import UserLearningLogs
from models.user_setting import UserSetting
from models.word import UserWordProgress
from models.user_reviewed_words import UserReviewedWords
from db.database import get_db
from api.login import get_current_user
from sqlalchemy import func

log_router = APIRouter(prefix="/api")

@log_router.get("/learning-logs")
async def get_learning_logs(request: Request, db: Session = Depends(get_db)):
    """获取用户今日学习日志"""
    try:
        # 获取当前登录用户
        user = get_current_user(request, db)
        
        # 获取用户设置
        user_setting = db.query(UserSetting).filter(UserSetting.id == user.id).first()
        if not user_setting:
            raise HTTPException(status_code=404, detail="用户设置不存在")
        
        # 获取今日学习记录
        today = date.today()
        learning_log = db.query(UserLearningLogs).filter(
            UserLearningLogs.id == user.id,
            UserLearningLogs.log_date == today
        ).first()
        
        # 如果没有今日记录，创建新记录
        if not learning_log:
            learning_log = UserLearningLogs(
                id=user.id,
                log_date=today,
                new_words_learned=0,
                words_reviewed=0
            )
            db.add(learning_log)
            db.commit()
            db.refresh(learning_log)
        
        # 获取今日需要复习的单词总数（应复习 ∪ 今日已复习）
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        # 1. 应复习单词
        should_review_ids = set(
            w.word_id for w in db.query(UserWordProgress.word_id).filter(
                UserWordProgress.user_id == user.id,
                UserWordProgress.next_review_at <= today_end,
                UserWordProgress.status.in_([2, 3])
            ).all()
        )
        # 2. 今日已复习单词
        reviewed_ids = set(
            r.word_id for r in db.query(UserReviewedWords.word_id).filter(
                UserReviewedWords.user_id == user.id,
                UserReviewedWords.review_date == today,
                UserReviewedWords.reviewed == 1
            ).all()
        )
        # 3. 总数为并集
        total_review_words = len(should_review_ids | reviewed_ids)
        
        return {
            "status": "success",
            "data": {
                "new_words_learned": learning_log.new_words_learned,
                "daily_goal": user_setting.daily_goal,
                "words_reviewed": learning_log.words_reviewed,
                "total_review_words": total_review_words
            }
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取学习日志失败: {str(e)}"
        )

@log_router.get("/learning-stats")
async def get_learning_stats(request: Request, db: Session = Depends(get_db)):
    """获取用户学习统计数据"""
    try:
        # 获取当前登录用户
        user = get_current_user(request, db)
        
        # 获取连续学习天数
        today = date.today()
        streak_days = 0
        current_date = today
        
        while True:
            # 检查当天是否有学习记录
            log = db.query(UserLearningLogs).filter(
                UserLearningLogs.id == user.id,
                UserLearningLogs.log_date == current_date
            ).first()
            
            if not log or (log.new_words_learned == 0 and log.words_reviewed == 0):
                break
                
            streak_days += 1
            current_date -= timedelta(days=1)
        
        # 获取累计学习天数
        total_days = db.query(func.count(UserLearningLogs.log_date)).filter(
            UserLearningLogs.id == user.id,
            UserLearningLogs.new_words_learned > 0
        ).scalar()
        
        # 获取已掌握单词数
        mastered_words = db.query(func.count(UserWordProgress.word_id)).filter(
            UserWordProgress.user_id == user.id,
            UserWordProgress.srs_level >= 3  # 已掌握状态
        ).scalar()
        
        # 获取用户设置
        user_setting = db.query(UserSetting).filter(UserSetting.id == user.id).first()
        if not user_setting:
            raise HTTPException(status_code=404, detail="用户设置不存在")
        
        # 获取今日学习效率
        today_log = db.query(UserLearningLogs).filter(
            UserLearningLogs.id == user.id,
            UserLearningLogs.log_date == today
        ).first()
        
        if today_log:
            total_words = today_log.new_words_learned + today_log.words_reviewed
            daily_goal = user_setting.daily_goal
            efficiency = min(100, int((total_words / daily_goal) * 100))
            efficiency_text = f"{efficiency}%"
        else:
            efficiency_text = "0%"
        
        return {
            "status": "success",
            "data": {
                "streak_days": streak_days,
                "total_days": total_days,
                "mastered_words": mastered_words,
                "efficiency": efficiency_text
            }
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取学习统计数据失败: {str(e)}"
        )

@log_router.get("/learning-stats/chart")
async def get_learning_chart_data(request: Request, db: Session = Depends(get_db)):
    """获取用户学习图表数据"""
    try:
        # 获取当前登录用户
        user = get_current_user(request, db)
        
        # 获取最近7天的日期
        today = date.today()
        dates = [(today - timedelta(days=i)).strftime('%m-%d') for i in range(6, -1, -1)]
        
        # 获取最近7天的学习记录
        seven_days_ago = today - timedelta(days=6)
        logs = db.query(UserLearningLogs).filter(
            UserLearningLogs.id == user.id,
            UserLearningLogs.log_date >= seven_days_ago,
            UserLearningLogs.log_date <= today
        ).order_by(UserLearningLogs.log_date).all()
        
        # 准备数据
        new_words = [0] * 7
        review_words = [0] * 7
        
        # 填充数据
        for log in logs:
            day_index = (today - log.log_date).days
            if 0 <= day_index < 7:
                new_words[day_index] = log.new_words_learned
                review_words[day_index] = log.words_reviewed
        
        return {
            "status": "success",
            "data": {
                "dates": dates,
                "new_words": new_words,
                "review_words": review_words
            }
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取图表数据失败: {str(e)}"
        )
