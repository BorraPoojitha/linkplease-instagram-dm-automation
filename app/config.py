import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PSEUDOGRAM_API_KEY: str = "test-api-key"
    DATABASE_URL: str = "sqlite+aiosqlite:///./linkplease.db"
    MAX_RETRIES: int = 5
    WORKER_POLL_INTERVAL: float = 0.5
    RATE_LIMIT_REQUESTS: int = 10
    RATE_LIMIT_WINDOW_SECONDS: float = 60.0
    PSEUDOGRAM_API_BASE_URL: str = "https://pseudogram-api.onrender.com"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
