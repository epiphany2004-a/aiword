from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from models.word import Word, UserWordProgress
from models.user_setting import UserSetting
from models.word_review_sentence import WordReviewSentence
from models.user_reviewed_words import UserReviewedWords
from db.database import get_db
from api.login import get_current_user
from api.agent import deepseek_process_sentence_list
from datetime import datetime, date, timedelta
from typing import List, Dict, Any
import json

review_router = APIRouter(prefix="/api", tags=["Review"])

@review_router.get(
    "/review_words",
    summary="获取今日应复习单词及复习句子",
    response_model=Dict[str, Any]
)
async def get_review_words(request: Request, db: Session = Depends(get_db)):
    """
    获取当前用户今日应复习的单词列表（只返回今日未复习过的单词），并为每个单词获取复习句子（优先查表，无则AI生成）。
    """
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = user.id
    user_setting = db.query(UserSetting).filter(UserSetting.id == user_id).first()
    if not user_setting:
        raise HTTPException(status_code=404, detail="用户设置不存在")
    
    today = date.today()
    today_end = datetime.combine(today, datetime.max.time())
    # 查找今日已复习的单词id
    reviewed_word_ids = set(
        r.word_id for r in db.query(UserReviewedWords.word_id).filter(
            UserReviewedWords.user_id == user_id,
            UserReviewedWords.review_date == today,
            UserReviewedWords.reviewed == 1
        ).all()
    )
    # 只查今日未复习的单词
    review_words = db.query(UserWordProgress, Word).join(Word, UserWordProgress.word_id == Word.word_id)
    review_words = review_words.filter(
        UserWordProgress.user_id == user_id,
        UserWordProgress.next_review_at <= today_end,
        UserWordProgress.status.in_([2, 3]),
        ~UserWordProgress.word_id.in_(reviewed_word_ids)
    ).all()
    
    result = []
    need_generate = []
    word_to_progress = {}
    for progress, word in review_words:
        # 先查复习句子表
        review_sentence = db.query(WordReviewSentence).filter(WordReviewSentence.word == word.word).first()
        if review_sentence and review_sentence.content:
            result.append({
                "word": word.word,
                "word_id": word.word_id,
                "srs_level": progress.srs_level,
                "next_review_at": progress.next_review_at.isoformat() if progress.next_review_at else None,
                "review_content": review_sentence.content
            })
        else:
            need_generate.append(word.word)
            word_to_progress[word.word] = {
                "word": word.word,
                "word_id": word.word_id,
                "srs_level": progress.srs_level,
                "next_review_at": progress.next_review_at.isoformat() if progress.next_review_at else None
            }
    # 对于需要生成的单词，调用deepseek
    if need_generate:
        print(f"需要AI生成复习句子的单词: {need_generate}")
        ai_results = deepseek_process_sentence_list(need_generate, max_workers=5)
        for ai_content in ai_results:
            word = ai_content.get("correct_answer") or ai_content.get("word")
            # 保存到数据库
            if word:
                db_obj = WordReviewSentence(
                    word=word,
                    content=ai_content
                )
                db.add(db_obj)
                db.commit()
                db.refresh(db_obj)
                # 整理到结果
                base_info = word_to_progress.get(word, {"word": word})
                base_info["review_content"] = ai_content
                result.append(base_info)
    print("今日未复习单词及复习内容:")
    for item in result:
        print(json.dumps(item, ensure_ascii=False, indent=2))
    return {
        "status": "success",
        "count": len(result),
        "words": result
    }

@review_router.post("/review/progress", summary="保存复习进度")
async def save_review_progress(request: Request, db: Session = Depends(get_db)):
    """
    保存用户复习单词的进度，正确则SRS+1，错误则SRS-1，正确时复习数+1，并在user_reviewed_words表插入记录。
    同时根据SRS等级更新下一次复习时间。
    """
    data = await request.json()
    word_id = data.get("word_id")
    correct = data.get("correct")
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    progress = db.query(UserWordProgress).filter(
        UserWordProgress.user_id == user.id,
        UserWordProgress.word_id == word_id
    ).first()
    if not progress:
        raise HTTPException(status_code=404, detail="进度不存在")
    today = date.today()
    now = datetime.now()
    
    # 记录到user_reviewed_words表
    if not db.query(UserReviewedWords).filter(
        UserReviewedWords.user_id == user.id,
        UserReviewedWords.word_id == word_id,
        UserReviewedWords.review_date == today
    ).first():
        db.add(UserReviewedWords(
            user_id=user.id,
            word_id=word_id,
            review_date=today,
            reviewed=1
        ))
    
    if correct:
        progress.srs_level += 1
        # 复习数+1
        from models.userlearninglogs import UserLearningLogs
        log = db.query(UserLearningLogs).filter(
            UserLearningLogs.id == user.id,
            UserLearningLogs.log_date == today
        ).first()
        if log:
            log.words_reviewed += 1
        else:
            log = UserLearningLogs(
                id=user.id,
                log_date=today,
                new_words_learned=0,
                words_reviewed=1
            )
            db.add(log)
        
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
    else:
        progress.srs_level = max(0, progress.srs_level - 1)
        # 答错时设置较短的复习间隔
        if progress.srs_level == 0:
            progress.next_review_at = now + timedelta(days=1)
        elif progress.srs_level == 1:
            progress.next_review_at = now + timedelta(days=2)
        else:
            progress.next_review_at = now + timedelta(days=3)
    
    # 更新最后复习时间
    progress.last_reviewed_at = now
    
    db.commit()
    return {
        "status": "success", 
        "srs_level": progress.srs_level,
        "next_review_at": progress.next_review_at.isoformat() if progress.next_review_at else None
    }

    