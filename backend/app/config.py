from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = f"sqlite:///{(Path(__file__).resolve().parents[1] / 'aigovern.db').as_posix()}"
    environment: str = "development"
    admin_api_key: str = ""
    reviewer_api_key: str = ""
    viewer_api_key: str = ""
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()