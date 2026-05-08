import re
from pathlib import Path
import fitz  # PyMuPDF
import pdfplumber
import pytesseract
from PIL import Image
import io


def extract_text_pymupdf(pdf_path: str) -> dict:
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text")
        pages.append({"page": i + 1, "text": text.strip()})
    doc.close()
    return {"pages": pages, "total_pages": len(pages)}


def extract_text_ocr(pdf_path: str) -> dict:
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=300)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        text = pytesseract.image_to_string(img, lang="sqi+eng")
        pages.append({"page": i + 1, "text": text.strip()})
    doc.close()
    return {"pages": pages, "total_pages": len(pages)}


def extract_with_pdfplumber(pdf_path: str) -> list[dict]:
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_tables = page.extract_tables()
            if page_tables:
                tables.append({"page": i + 1, "tables": page_tables})
    return tables


_QUESTION_PATTERNS = [
    re.compile(r"^\d+[\.\)]\s+(.+\?)", re.MULTILINE),
    re.compile(r"^[a-zA-Z][\.\)]\s+(.+\?)", re.MULTILINE),
    re.compile(r"Pyetje[:\s]+(.+)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"Llogarit[i]?\s+(.+)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"Gjej\s+(.+)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"Shkruaj\s+(.+)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"Analizo\s+(.+)", re.IGNORECASE | re.MULTILINE),
]

_FORMULA_PATTERN = re.compile(
    r"(?:[A-Za-z]\s*=\s*[\w\s\+\-\*/\^()]+|"
    r"\d+[\+\-\*/]\d+|"
    r"[A-Za-z]\^2|"
    r"√\w+)",
    re.MULTILINE,
)

_MATH_TOPICS = [
    "algjebër", "gjeometri", "trigonometri", "funksion", "ekuacion",
    "probabilitet", "statistikë", "numër", "fraksion", "integral",
]

_ALBANIAN_TOPICS = [
    "folje", "emër", "mbiemër", "sintagmë", "fjali", "letërsi",
    "poezi", "prozë", "ese", "gramatikë", "drejtshkrim", "morfologji",
]


def detect_subject(text: str) -> str:
    text_lower = text.lower()
    math_score = sum(1 for t in _MATH_TOPICS if t in text_lower)
    alb_score = sum(1 for t in _ALBANIAN_TOPICS if t in text_lower)
    if math_score > alb_score:
        return "matematike"
    if alb_score > math_score:
        return "shqipe"
    return "të përgjithshme"


def extract_questions(text: str) -> list[str]:
    questions = set()
    for pattern in _QUESTION_PATTERNS:
        for match in pattern.finditer(text):
            q = match.group(1).strip() if match.lastindex else match.group().strip()
            if len(q) > 10:
                questions.add(q)
    return list(questions)


def extract_formulas(text: str) -> list[str]:
    return list({m.group().strip() for m in _FORMULA_PATTERN.finditer(text) if len(m.group().strip()) > 2})


def extract_topics(text: str, subject: str) -> list[str]:
    text_lower = text.lower()
    topic_list = _MATH_TOPICS if subject == "matematike" else _ALBANIAN_TOPICS
    return [t for t in topic_list if t in text_lower]


def analyze_pdf(pdf_path: str) -> dict:
    path = Path(pdf_path)
    extraction = extract_text_pymupdf(pdf_path)
    full_text = " ".join(p["text"] for p in extraction["pages"])

    if len(full_text.strip()) < 100:
        extraction = extract_text_ocr(pdf_path)
        full_text = " ".join(p["text"] for p in extraction["pages"])

    subject = detect_subject(full_text)
    questions = extract_questions(full_text)
    formulas = extract_formulas(full_text) if subject == "matematike" else []
    topics = extract_topics(full_text, subject)

    return {
        "filename": path.name,
        "total_pages": extraction["total_pages"],
        "subject": subject,
        "full_text": full_text,
        "questions": questions,
        "formulas": formulas,
        "topics": topics,
        "pages": extraction["pages"],
    }
