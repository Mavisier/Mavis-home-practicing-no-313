from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg://workflow:workflow@localhost:5433/workflow"
    database_pool_size: int = Field(default=1, ge=1, le=20)
    demo_requester_token: SecretStr
    demo_approver_token: SecretStr | None = None
    llm_provider: Literal["fixture", "openai", "anthropic", "ollama"] = "fixture"
    llm_model: str = ""
    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    embedding_provider: Literal["fixture", "openai", "ollama"] = "fixture"
    embedding_model: str = "text-embedding-3-small"
    ollama_base_url: str = "http://127.0.0.1:11434"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
