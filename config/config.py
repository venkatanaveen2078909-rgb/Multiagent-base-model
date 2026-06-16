"""
config.py — Centralised settings loaded from .env
All modules import from here; never import os.environ directly.
"""
import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    groq_api_key: str = Field(default="")
    groq_model: str = Field(default="llama-3.3-70b-versatile")
    groq_temperature: float = Field(default=0.2)
    groq_max_tokens: int = Field(default=4096)

    # Search
    tavily_api_key: str = Field(default="")
    tavily_max_results: int = Field(default=5)
    tavily_search_depth: str = Field(default="advanced")

    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///./agentic_platform.db")

    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_debug: bool = Field(default=False)
    secret_key: str = Field(default="change-me")

    # Evaluation
    eval_confidence_threshold: float = Field(default=0.7)

    # Logging
    log_level: str = Field(default="INFO")

    # LangSmith
    langsmith_api_key: str = Field(default="")
    langsmith_tracing: bool = Field(default=False)
    langsmith_project: str = Field(default="default")

    @property
    def has_groq_key(self) -> bool:
        return bool(self.groq_api_key and self.groq_api_key != "your_groq_api_key_here")

    @property
    def has_tavily_key(self) -> bool:
        return bool(self.tavily_api_key and self.tavily_api_key != "your_tavily_api_key_here")

    @property
    def has_langsmith_key(self) -> bool:
        return bool(self.langsmith_api_key and self.langsmith_api_key != "your_langsmith_api_key_here")

    def configure_langsmith(self) -> None:
        """Push LangSmith settings into os.environ so LangChain picks them up."""
        if self.has_langsmith_key:
            os.environ["LANGCHAIN_API_KEY"] = self.langsmith_api_key
            os.environ["LANGCHAIN_TRACING_V2"] = "true" if self.langsmith_tracing else "false"
            os.environ["LANGCHAIN_PROJECT"] = self.langsmith_project
            # Also set the native LangSmith env vars
            os.environ["LANGSMITH_API_KEY"] = self.langsmith_api_key
            os.environ["LANGSMITH_TRACING"] = "true" if self.langsmith_tracing else "false"
            os.environ["LANGSMITH_PROJECT"] = self.langsmith_project


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
