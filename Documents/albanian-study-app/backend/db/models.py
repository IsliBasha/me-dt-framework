from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    subject = Column(String)  # "matematike" | "shqipe"
    page_count = Column(Integer, default=0)
    analyzed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    questions = relationship("Question", back_populates="document", cascade="all, delete-orphan")
    topics = relationship("Topic", back_populates="document", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    text = Column(Text, nullable=False)
    question_type = Column(String)  # "math" | "grammar" | "essay" | "literature"
    difficulty = Column(Float, default=0.5)  # 0.0–1.0
    topic = Column(String)
    answer = Column(Text)
    page_number = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="questions")
    flashcards = relationship("Flashcard", back_populates="question")


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    name = Column(String, nullable=False)
    subject = Column(String)
    frequency = Column(Integer, default=1)

    document = relationship("Document", back_populates="topics")


class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=True)
    front = Column(Text, nullable=False)
    back = Column(Text, nullable=False)
    subject = Column(String)
    topic = Column(String)
    # SM-2 spaced repetition fields
    ease_factor = Column(Float, default=2.5)
    interval = Column(Integer, default=1)      # days until next review
    repetitions = Column(Integer, default=0)
    due_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    question = relationship("Question", back_populates="flashcards")


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id = Column(Integer, primary_key=True)
    subject = Column(String)
    topic = Column(String)
    score = Column(Float)
    total_questions = Column(Integer)
    correct_answers = Column(Integer)
    duration_seconds = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    answers = relationship("QuizAnswer", back_populates="session", cascade="all, delete-orphan")


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("quiz_sessions.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=True)
    question_text = Column(Text)
    user_answer = Column(Text)
    correct_answer = Column(Text)
    is_correct = Column(Boolean, default=False)

    session = relationship("QuizSession", back_populates="answers")


class ExamSession(Base):
    __tablename__ = "exam_sessions"

    id = Column(Integer, primary_key=True)
    subject = Column(String)
    difficulty = Column(String)  # "lehtë" | "mesatar" | "vështirë"
    score = Column(Float)
    total_questions = Column(Integer)
    correct_answers = Column(Integer)
    time_limit_minutes = Column(Integer)
    duration_seconds = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    answers = relationship("ExamAnswer", back_populates="session", cascade="all, delete-orphan")


class ExamAnswer(Base):
    __tablename__ = "exam_answers"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("exam_sessions.id"), nullable=False)
    question_text = Column(Text)
    user_answer = Column(Text)
    correct_answer = Column(Text)
    is_correct = Column(Boolean, default=False)
    points = Column(Float, default=0.0)

    session = relationship("ExamSession", back_populates="answers")


class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True)
    xp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    streak_days = Column(Integer, default=0)
    last_active_date = Column(DateTime)
    badges = Column(JSON, default=list)
    total_study_minutes = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StudySession(Base):
    __tablename__ = "study_sessions"

    id = Column(Integer, primary_key=True)
    duration_minutes = Column(Integer)
    session_type = Column(String)  # "pomodoro" | "free" | "quiz" | "flashcard"
    subject = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id = Column(Integer, primary_key=True)
    subject = Column(String)
    topic = Column(String)
    messages = Column(JSON, default=list)  # [{role, content, timestamp}]
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
