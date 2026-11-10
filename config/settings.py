from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Settings(BaseModel):
    groq_api_key: str = Field(default="")
    groq_model: str = Field(default="")
    supabase_url: str = Field(default="")
    supabase_anon_key: str = Field(default="")
    database_url: str = Field(default="")
    app_url: str = Field(default="http://localhost:8501")
    auth_cookie_secret: str = Field(default="")
    groq_timeout_seconds: float = Field(default=45.0)
    groq_max_retries: int = Field(default=1)
    max_history_messages: int = Field(default=12)
    max_memories_in_context: int = Field(default=12)
    project_root: Path = Field(default=PROJECT_ROOT)

    @property
    def processed_health_path(self) -> Path:
        return self.project_root / "data" / "pmdata" / "processed" / "daily_summaries.csv"

    @property
    def raw_pmdata_path(self) -> Path:
        return self.project_root / "data" / "pmdata" / "raw"

    def groq_configured(self) -> bool:
        return bool(self.groq_api_key.strip() and self.groq_model.strip())

    def supabase_configured(self) -> bool:
        return bool(self.supabase_url.strip() and self.supabase_anon_key.strip())


def _from_mapping(values: dict[str, object]) -> Settings:
    def pick(*names: str) -> str:
        for name in names:
            raw = values.get(name)
            if raw is None:
                continue
            text = str(raw).strip()
            if text:
                return text
        return ""

    return Settings(
        groq_api_key=pick("GROQ_API_KEY", "groq_api_key"),
        groq_model=pick("GROQ_MODEL", "groq_model"),
        supabase_url=pick("SUPABASE_URL", "supabase_url"),
        supabase_anon_key=pick("SUPABASE_ANON_KEY", "supabase_anon_key"),
        database_url=pick("DATABASE_URL", "database_url"),
        app_url=pick("APP_URL", "app_url") or "http://localhost:8501",
        auth_cookie_secret=pick("AUTH_COOKIE_SECRET", "auth_cookie_secret"),
    )


def load_settings() -> Settings:
    import os

    settings = _from_mapping(dict(os.environ))
    try:
        import streamlit as st

        if hasattr(st, "secrets"):
            secret_map = {str(k): v for k, v in dict(st.secrets).items()}
            secret_settings = _from_mapping(secret_map)
            settings = settings.model_copy(
                update={
                    key: getattr(secret_settings, key) or getattr(settings, key)
                    for key in (
                        "groq_api_key",
                        "groq_model",
                        "supabase_url",
                        "supabase_anon_key",
                        "database_url",
                        "app_url",
                        "auth_cookie_secret",
                    )
                }
            )
    except Exception:
        pass
    return settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
