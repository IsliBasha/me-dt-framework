from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.services.analytics_service import get_dashboard_stats, get_topic_heatmap, log_study_session

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


class StudySessionLog(BaseModel):
    duration_minutes: int
    session_type: str = "free"
    subject: str = ""


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    return get_dashboard_stats(db)


@router.get("/heatmap")
def heatmap(db: Session = Depends(get_db)):
    return get_topic_heatmap(db)


@router.post("/study-session")
def log_session(body: StudySessionLog, db: Session = Depends(get_db)):
    log_study_session(db, body.duration_minutes, body.session_type, body.subject)
    return {"ok": True, "minutes_logged": body.duration_minutes}
