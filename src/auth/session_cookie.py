from __future__ import annotations

import base64
import hashlib
import json
import time
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from config.settings import Settings
from src.auth.authentication import AuthSession, AuthUser

COOKIE_NAME = "carecompanion_session"
COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 30


def _cipher(settings: Settings) -> Fernet:
    secret = settings.auth_cookie_secret.strip()
    if not secret:
        secret = settings.supabase_anon_key.strip()
    if not secret:
        raise RuntimeError("AUTH_COOKIE_SECRET must be configured for persistent login.")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


def encode_session(session: AuthSession, settings: Settings) -> str:
    payload = {
        "user_id": session.user.id,
        "email": session.user.email,
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "expires_at": int(time.time()) + COOKIE_MAX_AGE_SECONDS,
    }
    return _cipher(settings).encrypt(json.dumps(payload).encode("utf-8")).decode("ascii")


def decode_session(value: str | None, settings: Settings) -> AuthSession | None:
    if not value:
        return None
    try:
        payload: dict[str, Any] = json.loads(_cipher(settings).decrypt(value.encode("ascii")))
        if int(payload["expires_at"]) <= int(time.time()):
            return None
        return AuthSession(
            user=AuthUser(id=str(payload["user_id"]), email=str(payload.get("email", ""))),
            access_token=str(payload["access_token"]),
            refresh_token=str(payload["refresh_token"]),
        )
    except (InvalidToken, KeyError, TypeError, ValueError):
        return None


def save_session(cookie_manager: Any, session: AuthSession, settings: Settings) -> None:
    cookie_manager.set(
        COOKIE_NAME,
        encode_session(session, settings),
        max_age=COOKIE_MAX_AGE_SECONDS,
        secure=settings.app_url.lower().startswith("https://"),
        same_site="lax",
    )


def clear_session(cookie_manager: Any) -> None:
    cookie_manager.delete(COOKIE_NAME)
