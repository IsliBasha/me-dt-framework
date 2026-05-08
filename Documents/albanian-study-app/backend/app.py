from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.db.database import init_db
from backend.api.pdf import router as pdf_router
from backend.api.flashcards import router as flashcards_router
from backend.api.quiz import router as quiz_router
from backend.api.tutor import router as tutor_router
from backend.api.analytics import router as analytics_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Albanian Study App API",
        description="Backend për aplikacionin e studimit shqiptar",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(pdf_router)
    app.include_router(flashcards_router)
    app.include_router(quiz_router)
    app.include_router(tutor_router)
    app.include_router(analytics_router)

    @app.on_event("startup")
    def startup():
        init_db()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
