"""
config/settings.py

AI Secretary Pro V1.0
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """
    Application Settings
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ===============================
    # OpenAI
    # ===============================

    OPENAI_API_KEY: str

    OPENAI_MODEL: str = "gpt-4.1-mini"

    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # ===============================
    # Directory
    # ===============================

    DATA_DIR: Path = BASE_DIR / "data"

    VECTOR_DB_DIR: Path = BASE_DIR / "vector_db"

    LOG_DIR: Path = BASE_DIR / "logs"

    # ===============================
    # Streamlit
    # ===============================

    APP_NAME: str = "AI Secretary Pro"

    APP_ENV: str = "development"

    DEBUG: bool = True

    # ===============================
    # Initialize
    # ===============================

    def create_directories(self):

        self.DATA_DIR.mkdir(exist_ok=True)

        self.VECTOR_DB_DIR.mkdir(exist_ok=True)

        self.LOG_DIR.mkdir(exist_ok=True)


settings = Settings()

settings.create_directories()