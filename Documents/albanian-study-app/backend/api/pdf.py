import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.db.models import Document, Question, Topic
from backend.services.pdf_analyzer import analyze_pdf

router = APIRouter(prefix="/api/pdf", tags=["pdf"])

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _process_pdf(doc_id: int, file_path: str):
    from backend.db.database import SessionLocal
    db = SessionLocal()
    try:
        result = analyze_pdf(file_path)
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return
        doc.subject = result["subject"]
        doc.page_count = result["total_pages"]
        doc.analyzed = True

        for q_text in result["questions"]:
            db.add(Question(
                document_id=doc_id,
                text=q_text,
                question_type="math" if result["subject"] == "matematike" else "grammar",
                topic=result["topics"][0] if result["topics"] else None,
            ))

        for topic_name in result["topics"]:
            existing = db.query(Topic).filter(
                Topic.document_id == doc_id, Topic.name == topic_name
            ).first()
            if existing:
                existing.frequency += 1
            else:
                db.add(Topic(document_id=doc_id, name=topic_name, subject=result["subject"]))

        db.commit()
    finally:
        db.close()


@router.post("/upload")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Vetëm skedarë PDF pranohen")

    dest = UPLOAD_DIR / file.filename
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    doc = Document(filename=file.filename, file_path=str(dest))
    db.add(doc)
    db.commit()
    db.refresh(doc)

    background_tasks.add_task(_process_pdf, doc.id, str(dest))

    return {"id": doc.id, "filename": doc.filename, "status": "duke u analizuar..."}


@router.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "subject": d.subject,
            "page_count": d.page_count,
            "analyzed": d.analyzed,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]


@router.get("/analyze/{doc_id}")
def get_analysis(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokumenti nuk u gjet")

    questions = db.query(Question).filter(Question.document_id == doc_id).all()
    topics = db.query(Topic).filter(Topic.document_id == doc_id).all()

    return {
        "id": doc.id,
        "filename": doc.filename,
        "subject": doc.subject,
        "analyzed": doc.analyzed,
        "questions": [{"id": q.id, "text": q.text, "topic": q.topic} for q in questions],
        "topics": [{"name": t.name, "frequency": t.frequency} for t in topics],
    }
