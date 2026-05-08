from pathlib import Path
from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    app_port: int = 8765
    db_path: str = str(DATA_DIR / "studimi.db")

    class Config:
        env_file = BASE_DIR / ".env"
        env_file_encoding = "utf-8"


settings = Settings()
API_BASE_URL = f"http://localhost:{settings.app_port}"
