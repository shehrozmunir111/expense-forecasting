import hashlib
import logging
import math
import re
from typing import List

from langchain_core.embeddings import Embeddings

from app.config import settings

logger = logging.getLogger(__name__)


def get_chat_model(streaming: bool = False):
    """Return an LCEL-compatible chat model selected by ``CHAT_LLM_PROVIDER`` (OpenAI/LM Studio by default)."""
    provider = (settings.CHAT_LLM_PROVIDER or "openai").lower()

    if provider in ("claude_cli", "claude-cli", "claudecli"):
        from app.services.claude_cli_model import ChatClaudeCLI

        return ChatClaudeCLI(
            model=settings.CLAUDE_CLI_MODEL,
            command=settings.CLAUDE_CLI_COMMAND,
            disable_thinking=settings.CLAUDE_CLI_DISABLE_THINKING,
            timeout=settings.CHAT_LLM_TIMEOUT,
        )

    if provider in ("openai", "lmstudio", "lm_studio"):
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.CHAT_LLM_MODEL,
            base_url=settings.LLM_BASE_URL or None,
            api_key=settings.OPENAI_API_KEY or "lm-studio",
            temperature=settings.CHAT_LLM_TEMPERATURE,
            max_tokens=settings.CHAT_MAX_TOKENS,
            timeout=settings.CHAT_LLM_TIMEOUT,
            max_retries=1,
            streaming=streaming,
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not set")
        return ChatAnthropic(
            model=settings.CHAT_LLM_MODEL,
            api_key=settings.ANTHROPIC_API_KEY,
            temperature=settings.CHAT_LLM_TEMPERATURE,
            max_tokens=settings.CHAT_MAX_TOKENS,
            timeout=settings.CHAT_LLM_TIMEOUT,
            streaming=streaming,
        )

    if provider in ("gemini", "google", "google-genai"):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "Gemini support requires: pip install langchain-google-genai"
            ) from exc
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set")
        return ChatGoogleGenerativeAI(
            model=settings.CHAT_LLM_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=settings.CHAT_LLM_TEMPERATURE,
            max_output_tokens=settings.CHAT_MAX_TOKENS,
        )

    raise ValueError(f"Unknown CHAT_LLM_PROVIDER: {provider!r}")


def get_embeddings() -> Embeddings:
    """Return an embeddings model: offline HashingEmbeddings when EMBEDDING_PROVIDER=local, else OpenAI-compatible."""
    provider = (settings.EMBEDDING_PROVIDER or "openai").lower()

    if provider == "local":
        return HashingEmbeddings()

    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        base_url=settings.EMBEDDING_BASE_URL or settings.LLM_BASE_URL or None,
        api_key=settings.OPENAI_API_KEY or "lm-studio",
        # nomic / non-OpenAI models aren't in tiktoken; send raw strings, not token ids.
        check_embedding_ctx_length=False,
    )


class HashingEmbeddings(Embeddings):
    """Deterministic, dependency-free bag-of-words hashing embedding for offline tests (not semantic)."""

    def __init__(self, dim: int = 256):
        self.dim = dim

    def _embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        for tok in re.findall(r"[a-z0-9]+", text.lower()):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            vec[h % self.dim] += 1.0 if (h >> 8) % 2 == 0 else -1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)
