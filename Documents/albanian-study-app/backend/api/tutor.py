from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.db.models import AIConversation
from backend.services.ai_service import chat_with_tutor, explain_solution, generate_study_plan

router = APIRouter(prefix="/api/tutor", tags=["tutor"])


class ChatMessage(BaseModel):
    content: str
    subject: str
    conversation_id: int | None = None


class ExplainRequest(BaseModel):
    question: str
    subject: str


class StudyPlanRequest(BaseModel):
    weak_topics: list[str]
    subject: str
    days: int = 7


@router.post("/chat")
async def chat(body: ChatMessage, db: Session = Depends(get_db)):
    if body.conversation_id:
        convo = db.query(AIConversation).filter(AIConversation.id == body.conversation_id).first()
        if not convo:
            raise HTTPException(status_code=404, detail="Biseda nuk u gjet")
        messages = list(convo.messages or [])
    else:
        convo = AIConversation(subject=body.subject, messages=[])
        db.add(convo)
        db.flush()
        messages = []

    messages.append({"role": "user", "content": body.content, "timestamp": datetime.utcnow().isoformat()})
    reply = await chat_with_tutor(messages, body.subject)
    messages.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})

    convo.messages = messages
    convo.updated_at = datetime.utcnow()
    db.commit()

    return {
        "conversation_id": convo.id,
        "reply": reply,
        "message_count": len(messages),
    }


@router.post("/explain")
async def explain(body: ExplainRequest):
    explanation = await explain_solution(body.question, body.subject)
    return {"explanation": explanation}


@router.post("/study-plan")
async def study_plan(body: StudyPlanRequest):
    plan = await generate_study_plan(body.weak_topics, body.subject, body.days)
    return {"plan": plan, "days": body.days}


@router.get("/conversations")
def list_conversations(db: Session = Depends(get_db)):
    convos = db.query(AIConversation).order_by(AIConversation.updated_at.desc()).limit(10).all()
    return [
        {
            "id": c.id,
            "subject": c.subject,
            "message_count": len(c.messages or []),
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in convos
    ]
