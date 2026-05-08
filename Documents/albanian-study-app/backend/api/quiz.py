from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.db.models import QuizSession, QuizAnswer
from backend.services.ai_service import generate_quiz_questions
from backend.services.analytics_service import award_xp, XP_PER_QUIZ

router = APIRouter(prefix="/api/quiz", tags=["quiz"])

_LETTER_TO_IDX = {"A": 0, "B": 1, "C": 2, "D": 3}


def normalize_correct_answer(correct: str, options: list[str]) -> str:
    """Map a letter answer (A/B/C/D) to the matching option text.

    When the AI returns 'B' instead of the full option text, this converts it
    so the string comparison against the radio-button selection works correctly.
    """
    if not correct or not options:
        return correct
    idx = _LETTER_TO_IDX.get(correct.strip().upper())
    if idx is not None and idx < len(options):
        return options[idx]
    return correct


class QuizGenerateRequest(BaseModel):
    topic: str
    subject: str
    count: int = 5
    difficulty: str = "mesatar"


class AnswerItem(BaseModel):
    question_text: str
    user_answer: str
    correct_answer: str


class QuizSubmit(BaseModel):
    subject: str
    topic: str
    answers: list[AnswerItem]
    duration_seconds: int = 0


@router.post("/generate")
async def generate_quiz(body: QuizGenerateRequest):
    questions = await generate_quiz_questions(body.topic, body.subject, body.count, body.difficulty)
    for q in questions:
        q["correct"] = normalize_correct_answer(q.get("correct", ""), q.get("options", []))
    return {"questions": questions, "topic": body.topic, "subject": body.subject}


@router.post("/submit")
def submit_quiz(body: QuizSubmit, db: Session = Depends(get_db)):
    correct = sum(1 for a in body.answers if a.user_answer.strip().lower() == a.correct_answer.strip().lower())
    total = len(body.answers)
    score = round((correct / total) * 100, 1) if total else 0.0

    session = QuizSession(
        subject=body.subject,
        topic=body.topic,
        score=score,
        total_questions=total,
        correct_answers=correct,
        duration_seconds=body.duration_seconds,
    )
    db.add(session)
    db.flush()

    for a in body.answers:
        is_correct = a.user_answer.strip().lower() == a.correct_answer.strip().lower()
        db.add(QuizAnswer(
            session_id=session.id,
            question_text=a.question_text,
            user_answer=a.user_answer,
            correct_answer=a.correct_answer,
            is_correct=is_correct,
        ))

    db.commit()
    award_xp(db, XP_PER_QUIZ + int(score // 10), "quiz")

    return {
        "session_id": session.id,
        "score": score,
        "correct": correct,
        "total": total,
    }


@router.get("/sessions")
def quiz_history(db: Session = Depends(get_db)):
    sessions = db.query(QuizSession).order_by(QuizSession.created_at.desc()).limit(20).all()
    return [
        {
            "id": s.id,
            "subject": s.subject,
            "topic": s.topic,
            "score": s.score,
            "total_questions": s.total_questions,
            "created_at": s.created_at.isoformat(),
        }
        for s in sessions
    ]
