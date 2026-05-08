from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.db.models import Flashcard


def sm2_review(flashcard: Flashcard, quality: int) -> Flashcard:
    """Apply SM-2 algorithm. quality: 0–5 (0=complete blackout, 5=perfect)."""
    if quality < 3:
        flashcard.repetitions = 0
        flashcard.interval = 1
    else:
        if flashcard.repetitions == 0:
            flashcard.interval = 1
        elif flashcard.repetitions == 1:
            flashcard.interval = 6
        else:
            flashcard.interval = round(flashcard.interval * flashcard.ease_factor)
        flashcard.repetitions += 1

    flashcard.ease_factor = max(
        1.3,
        flashcard.ease_factor + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02),
    )
    flashcard.due_date = datetime.utcnow() + timedelta(days=flashcard.interval)
    return flashcard


def get_due_flashcards(db: Session, limit: int = 20) -> list[Flashcard]:
    return (
        db.query(Flashcard)
        .filter(Flashcard.due_date <= datetime.utcnow())
        .order_by(Flashcard.due_date)
        .limit(limit)
        .all()
    )


def create_flashcard(db: Session, front: str, back: str, subject: str, topic: str, question_id: int | None = None) -> Flashcard:
    card = Flashcard(
        front=front,
        back=back,
        subject=subject,
        topic=topic,
        question_id=question_id,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


def submit_review(db: Session, flashcard_id: int, quality: int) -> Flashcard:
    card = db.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
    if not card:
        raise ValueError(f"Flashcard {flashcard_id} nuk u gjet")
    card = sm2_review(card, quality)
    db.commit()
    db.refresh(card)
    return card
