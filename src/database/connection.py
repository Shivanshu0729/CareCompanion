from __future__ import annotations

from supabase import Client, create_client

from config.settings import Settings, get_settings


class DatabaseConfigurationError(RuntimeError):
    """Raised when Supabase is not configured."""


def require_supabase(settings: Settings | None = None) -> Settings:
    settings = settings or get_settings()
    if not settings.supabase_configured():
        raise DatabaseConfigurationError(
            "SUPABASE_URL and SUPABASE_ANON_KEY must be configured."
        )
    return settings


def create_public_client(settings: Settings | None = None) -> Client:
    settings = require_supabase(settings)
    return create_client(settings.supabase_url, settings.supabase_anon_key)


def create_authenticated_client(access_token: str, settings: Settings | None = None) -> Client:
    if not access_token.strip():
        raise DatabaseConfigurationError("An access token is required for protected queries.")
    settings = require_supabase(settings)
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(access_token)
    return client
