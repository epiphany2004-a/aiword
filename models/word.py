from sqlalchemy import Column, Integer, String, ForeignKey, JSON, TIMESTAMP, UniqueConstraint
from sqlalchemy.orm import relationship
from models.base import Base

class Word(Base):
    """词书单词模型"""
    __tablename__ = "words"
    word_id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String(50), unique=True, nullable=False)
    # 关系
    books = relationship("BookWordLink", back_populates="word", cascade="all, delete-orphan")

class UserWordProgress(Base):
    """用户单词学习进度模型"""
    __tablename__ = "user_word_progress"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    word_id = Column(Integer, ForeignKey("word_dictionary.word_id", ondelete="CASCADE"), primary_key=True)
    status = Column(Integer, default=1)  # 0=未学习, 1=学习中, 2=复习中, 3=已掌握
    srs_level = Column(Integer, default=0)
    next_review_at = Column(TIMESTAMP)
    last_reviewed_at = Column(TIMESTAMP)
    correct_streak = Column(Integer, default=0)
    created_at = Column(TIMESTAMP)

class WordDictionary(Base):
    """单词词典模型"""
    __tablename__ = "word_dictionary"

    word_id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String(50), unique=True)
    content = Column(JSON)
    created_at = Column(TIMESTAMP)

class Book(Base):
    """词书模型"""
    __tablename__ = "books"

    book_id = Column(Integer, primary_key=True, autoincrement=True)
    book_name = Column(String(100), unique=True, nullable=False)
    word_count = Column(Integer, default=0, nullable=False)
    # 关系
    words = relationship("BookWordLink", back_populates="book", cascade="all, delete-orphan")

class BookWordLink(Base):
    __tablename__ = "book_words"
    book_id = Column(Integer, ForeignKey("books.book_id", ondelete="CASCADE"), primary_key=True)
    word_id = Column(Integer, ForeignKey("words.word_id", ondelete="CASCADE"), primary_key=True)
    # 关系
    book = relationship("Book", back_populates="words")
    word = relationship("Word", back_populates="books")
    __table_args__ = (UniqueConstraint('book_id', 'word_id', name='uq_book_word'),)
