from __future__ import annotations

import base64
import json
import threading
import time
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException, Request, Response

from config.settings import Settings, get_settings
from src.auth.authentication import AuthenticationError, AuthService, AuthSession
from src.auth.session_cookie import (
    COOKIE_MAX_AGE_SECONDS,
    decode_session,
    encode_session,
)
from src.database.connection import create_authenticated_client

WEB_COOKIE_NAME = "carecompanion_web_session"
REFRESH_MARGIN_SECONDS = 60


def settings_dep() -> Settings:
    return get_settings()


def api_error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"error": {"code": code, "message": message}},
    )


def public_message(exc: Exception) -> str:
    return str(exc).split("Supabase returned:")[0].strip()


def set_session_cookie(response: Response, session: AuthSession, settings: Settings) -> None:
    response.set_cookie(
        WEB_COOKIE_NAME,
        encode_session(session, settings),
        max_age=COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.app_url.lower().startswith("https://"),
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(WEB_COOKIE_NAME, path="/")


def _jwt_expiry(token: str) -> int:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        return int(json.loads(decoded)["exp"])
    except (IndexError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return 0


_refresh_lock = threading.Lock()
_recent_refreshes: dict[str, tuple[float, AuthSession]] = {}


def _refresh_once(refresh_token: str, settings: Settings) -> AuthSession:
    with _refresh_lock:
        now = time.time()
        expired = [
            key for key, (timestamp, _) in _recent_refreshes.items()
            if now - timestamp > REFRESH_MARGIN_SECONDS
        ]
        for key in expired:
            del _recent_refreshes[key]
        cached = _recent_refreshes.get(refresh_token)
        if cached is not None:
            return cached[1]
        session = AuthService(settings=settings).refresh(refresh_token)
        _recent_refreshes[refresh_token] = (now, session)
        return session


@dataclass
class CurrentUser:
    id: str
    email: str
    client: Any


def get_current_user(
    request: Request,
    response: Response,
    settings: Settings = Depends(settings_dep),
) -> CurrentUser:
    session = decode_session(request.cookies.get(WEB_COOKIE_NAME), settings)
    if session is None:
        raise api_error(401, "not_authenticated", "Please sign in.")

    if _jwt_expiry(session.access_token) - time.time() < REFRESH_MARGIN_SECONDS:
        try:
            session = _refresh_once(session.refresh_token, settings)
        except AuthenticationError as exc:
            raise api_error(
                401,
                "session_expired",
                "Your session expired. Please sign in again.",
            ) from exc
        set_session_cookie(response, session, settings)

    client = create_authenticated_client(session.access_token, settings)
    return CurrentUser(id=session.user.id, email=session.user.email, client=client)
