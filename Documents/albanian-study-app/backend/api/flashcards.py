from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.db.models import Flashcard
from backend.services.flashcard_service import get_due_flashcards, create_flashcard, submit_review
from backend.services.ai_service import generate_flashcards as ai_generate
from backend.services.analytics_service import award_xp, XP_PER_FLASHCARD_REVIEW

router = APIRouter(prefix="/api/flashcards", tags=["flashcards"])


class FlashcardCreate(BaseModel):
    front: str
    back: str
    subject: str
    topic: str = ""
    question_id: int | None = None


class ReviewSubmit(BaseModel):
    quality: int  # 0–5


class AIGenerateRequest(BaseModel):
    text: str
    subject: str
    count: int = 10


@router.get("")
def list_flashcards(subject: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Flashcard)
    if subject:
        query = query.filter(Flashcard.subject == subject)
    cards = query.order_by(Flashcard.created_at.desc()).all()
    return [_card_dict(c) for c in cards]


@router.get("/due")
def due_flashcards(limit: int = 20, db: Session = Depends(get_db)):
    cards = get_due_flashcards(db, limit=limit)
    return [_card_dict(c) for c in cards]


@router.post("")
def add_flashcard(body: FlashcardCreate, db: Session = Depends(get_db)):
    card = create_flashcard(
        db, body.front, body.back, body.subject, body.topic, body.question_id
    )
    return _card_dict(card)


@router.put("/{card_id}/review")
def review_flashcard(card_id: int, body: ReviewSubmit, db: Session = Depends(get_db)):
    if not (0 <= body.quality <= 5):
        raise HTTPException(status_code=400, detail="Cilësia duhet të jetë 0–5")
    try:
        card = submit_review(db, card_id, body.quality)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    award_xp(db, XP_PER_FLASHCARD_REVIEW, "flashcard")
    return _card_dict(card)


@router.post("/generate")
async def generate_ai_flashcards(body: AIGenerateRequest, db: Session = Depends(get_db)):
    cards_data = await ai_generate(body.text, body.subject, body.count)
    created = []
    for c in cards_data:
        card = create_flashcard(db, c["front"], c["back"], body.subject, c.get("topic", ""))
        created.append(_card_dict(card))
    return created


@router.delete("/{card_id}")
def delete_flashcard(card_id: int, db: Session = Depends(get_db)):
    card = db.query(Flashcard).filter(Flashcard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Kartela nuk u gjet")
    db.delete(card)
    db.commit()
    return {"ok": True}


def _card_dict(c: Flashcard) -> dict:
    return {
        "id": c.id,
        "front": c.front,
        "back": c.back,
        "subject": c.subject,
        "topic": c.topic,
        "ease_factor": c.ease_factor,
        "interval": c.interval,
        "repetitions": c.repetitions,
        "due_date": c.due_date.isoformat() if c.due_date else None,
    }
