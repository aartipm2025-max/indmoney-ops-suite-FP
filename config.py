from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).parent
LOGS_DIR = ROOT_DIR / "logs"
DATA_DIR = ROOT_DIR / "data"
SECRETS_DIR = ROOT_DIR / ".secrets"

LOGS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
SECRETS_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "INDmoney Investor Ops Suite"
    app_env: str = "dev"
    log_level: str = "INFO"

    groq_api_key: str = ""
    groq_model_primary: str = "llama-3.3-70b-versatile"
    groq_model_fast: str = "llama-3.1-8b-instant"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-lite"

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    chroma_persist_dir: str = "./data/chroma_db"
    state_db_path: str = "./data/state.db"

    rag_top_k: int = 10
    rag_rerank_k: int = 3

    llm_max_retries: int = 3
    llm_circuit_breaker_threshold: int = 5
    llm_circuit_breaker_window_s: int = 60


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    from core.exceptions import ConfigError

    s = Settings()
    placeholder = "paste_your_key_here"
    if not s.groq_api_key or s.groq_api_key == placeholder:
        raise ConfigError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and fill in your key."
        )
    return s


settings = get_settings()
