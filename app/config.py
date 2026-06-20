from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "FinanceFlow"
    APP_VERSION: str = "2.0.5"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Database - SQLite for MVP; swap to PostgreSQL URL for production
    DATABASE_URL: str = "sqlite:///./data/expenses.db"

    # Redis / Celery broker + result backend (background jobs)
    REDIS_URL: str = "redis://localhost:6379/0"

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

    # -- Conversational agent ("Chat with your finances") ----------- #
    # Provider-agnostic. Defaults point at a local LM Studio server
    # (OpenAI-compatible) so no cloud key is required; set CHAT_LLM_PROVIDER
    # to "anthropic"/"gemini" and clear LLM_BASE_URL to use the cloud.
    CHAT_LLM_PROVIDER: str = "openai"  # "openai" (incl. LM Studio) | "anthropic" | "gemini"
    CHAT_LLM_MODEL: str = "google/gemma-4-12b-qat"
    LLM_BASE_URL: Optional[str] = None  # e.g. http://localhost:1234/v1 (LM Studio); None = cloud default
    CHAT_LLM_TEMPERATURE: float = 0.0
    CHAT_MAX_TOKENS: int = 512
    CHAT_LLM_TIMEOUT: int = 60  # seconds per LLM call; raise for slow local models
    GEMINI_API_KEY: Optional[str] = None

    # Embeddings for retrieval (Chroma)
    EMBEDDING_PROVIDER: str = "openai"  # "openai" (incl. LM Studio) | "local"
    EMBEDDING_MODEL: str = "text-embedding-nomic-embed-text-v1.5"
    EMBEDDING_BASE_URL: Optional[str] = None  # defaults to LLM_BASE_URL when unset

    # Adaptive-RAG tuning
    CHAT_RETRIEVAL_K: int = 4
    CHAT_MAX_REWRITES: int = 1  # how many query-rewrite retries before answering anyway
    CHAT_RECENT_TX_LIMIT: int = 8

    # Production RAG: persistent Chroma index with fingerprint-based refresh.
    # When False, /chat uses an ephemeral per-request index instead.
    RAG_PERSISTENT: bool = True
    RAG_PERSIST_DIR: str = "./data/chroma"
    RAG_COLLECTION: str = "finance_facts"

    # Reranking: fetch more candidates, then rerank down to CHAT_RETRIEVAL_K.
    RAG_RERANK: bool = True
    RAG_FETCH_K: int = 12          # candidates pulled before reranking
    RAG_RERANK_LLM: bool = False   # True = LLM reranker; False = deterministic lexical

    # Guardrails (input/output validation).
    GUARDRAILS: bool = True

    # Long-term / semantic memory (per-user persistent recall across sessions).
    LONG_TERM_MEMORY: bool = True
    LTM_PERSIST_DIR: str = "./data/chroma_memory"
    LTM_COLLECTION: str = "user_memory"
    LTM_RECALL_K: int = 3

    # "extra: ignore" lets the shared .env hold unrelated keys
    # (LANGSMITH_*, TAVILY_API_KEY, PINECONE_API_KEY, ...) without breaking startup.
    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}


settings = Settings()
