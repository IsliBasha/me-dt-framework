from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.db.models import UserProgress, QuizSession, ExamSession, StudySession, Flashcard

XP_PER_QUIZ = 20
XP_PER_EXAM = 50
XP_PER_FLASHCARD_REVIEW = 5
XP_PER_STUDY_MINUTE = 1

LEVEL_THRESHOLDS = [0, 100, 250, 500, 1000, 2000, 4000, 8000, 15000, 30000]

BADGES = {
    "para_hapa": {"name": "Hapat e Para", "xp_required": 100},
    "kuizmast": {"name": "Kuizmast", "quiz_count": 10},
    "perseverance": {"name": "Këmbëngulja", "streak_required": 7},
    "lexues": {"name": "Lexuesi i Zellshëm", "study_minutes": 300},
}


def _calculate_level(xp: int) -> int:
    for i, threshold in enumerate(reversed(LEVEL_THRESHOLDS)):
        if xp >= threshold:
            return len(LEVEL_THRESHOLDS) - i
    return 1


def award_xp(db: Session, amount: int, source: str = "") -> UserProgress:
    progress = db.query(UserProgress).first()
    if not progress:
        progress = UserProgress()
        db.add(progress)

    progress.xp += amount
    progress.level = _calculate_level(progress.xp)

    now = datetime.utcnow()
    if progress.last_active_date:
        delta = (now.date() - progress.last_active_date.date()).days
        if delta == 1:
            progress.streak_days += 1
        elif delta > 1:
            progress.streak_days = 1
    else:
        progress.streak_days = 1
    progress.last_active_date = now

    _check_badges(db, progress)
    db.commit()
    db.refresh(progress)
    return progress


def _check_badges(db: Session, progress: UserProgress):
    badges = set(progress.badges or [])
    quiz_count = db.query(func.count(QuizSession.id)).scalar()
    study_minutes = progress.total_study_minutes or 0

    if progress.xp >= BADGES["para_hapa"]["xp_required"]:
        badges.add("para_hapa")
    if quiz_count >= BADGES["kuizmast"]["quiz_count"]:
        badges.add("kuizmast")
    if progress.streak_days >= BADGES["perseverance"]["streak_required"]:
        badges.add("perseverance")
    if study_minutes >= BADGES["lexues"]["study_minutes"]:
        badges.add("lexues")

    progress.badges = list(badges)


def get_dashboard_stats(db: Session) -> dict:
    progress = db.query(UserProgress).first()
    recent_quizzes = (
        db.query(QuizSession)
        .order_by(QuizSession.created_at.desc())
        .limit(5)
        .all()
    )
    avg_score = db.query(func.avg(QuizSession.score)).scalar() or 0.0
    due_flashcards = (
        db.query(func.count(Flashcard.id))
        .filter(Flashcard.due_date <= datetime.utcnow())
        .scalar()
    )

    return {
        "xp": progress.xp if progress else 0,
        "level": progress.level if progress else 1,
        "streak_days": progress.streak_days if progress else 0,
        "badges": progress.badges if progress else [],
        "avg_quiz_score": round(avg_score, 1),
        "due_flashcards": due_flashcards,
        "recent_quizzes": [
            {
                "id": q.id,
                "subject": q.subject,
                "score": q.score,
                "created_at": q.created_at.isoformat(),
            }
            for q in recent_quizzes
        ],
    }


def get_topic_heatmap(db: Session) -> dict:
    quiz_topics = (
        db.query(QuizSession.topic, func.avg(QuizSession.score).label("avg_score"))
        .group_by(QuizSession.topic)
        .all()
    )
    return {
        "topics": [
            {"topic": t.topic or "Pa temë", "avg_score": round(t.avg_score or 0, 1)}
            for t in quiz_topics
        ]
    }


def log_study_session(db: Session, duration_minutes: int, session_type: str, subject: str) -> None:
    session = StudySession(
        duration_minutes=duration_minutes,
        session_type=session_type,
        subject=subject,
    )
    db.add(session)
    progress = db.query(UserProgress).first()
    if progress:
        progress.total_study_minutes = (progress.total_study_minutes or 0) + duration_minutes
    db.commit()
    award_xp(db, duration_minutes * XP_PER_STUDY_MINUTE, "study")
