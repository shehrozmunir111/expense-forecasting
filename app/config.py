from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Expense Forecasting API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Database - SQLite for MVP; swap to PostgreSQL URL for production
    DATABASE_URL: str = "sqlite:///./data/expenses.db"

    # LLM Provider
    LLM_PROVIDER: str = "anthropic"  # "anthropic" | "openai"
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    LLM_MODEL: str = "claude-haiku-4-5-20251001"
    LLM_MAX_TOKENS: int = 2048
    LLM_BATCH_SIZE: int = 20  # transactions per LLM call

    # ML
    MODEL_PATH: str = "./data/models"
    MIN_MONTHS_FOR_FORECAST: int = 2

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
