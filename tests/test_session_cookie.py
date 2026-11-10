from __future__ import annotations

from config.settings import Settings
from src.auth.authentication import AuthSession, AuthUser
from src.auth.session_cookie import decode_session, encode_session


def test_session_cookie_round_trip() -> None:
    settings = Settings(auth_cookie_secret="test-cookie-secret")
    session = AuthSession(
        user=AuthUser(id="user-1", email="user@example.com"),
        access_token="access-token",
        refresh_token="refresh-token",
    )
    encoded = encode_session(session, settings)
    restored = decode_session(encoded, settings)
    assert restored == session


def test_session_cookie_cannot_be_decoded_with_another_secret() -> None:
    session = AuthSession(
        user=AuthUser(id="user-1", email="user@example.com"),
        access_token="access-token",
        refresh_token="refresh-token",
    )
    encoded = encode_session(session, Settings(auth_cookie_secret="first"))
    assert decode_session(encoded, Settings(auth_cookie_secret="second")) is None
