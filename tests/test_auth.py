from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.auth.authentication import AuthenticationError, AuthService


def test_sign_in_returns_session() -> None:
    client = MagicMock()
    client.auth.sign_in_with_password.return_value = SimpleNamespace(
        user=SimpleNamespace(id="user-1", email="a@example.com"),
        session=SimpleNamespace(access_token="token", refresh_token="refresh"),
    )
    service = AuthService(client=client)
    session = service.sign_in("a@example.com", "password1")
    assert session.user.id == "user-1"
    assert session.access_token == "token"
    client.table.assert_called()


def test_sign_up_rejects_short_password() -> None:
    service = AuthService(client=MagicMock())
    with pytest.raises(AuthenticationError):
        service.sign_up("a@example.com", "short")


def test_sign_in_requires_credentials() -> None:
    service = AuthService(client=MagicMock())
    with pytest.raises(AuthenticationError):
        service.sign_in("", "")


def test_expired_refresh_is_authentication_error() -> None:
    client = MagicMock()
    client.auth.refresh_session.side_effect = RuntimeError("expired")
    service = AuthService(client=client)
    with pytest.raises(AuthenticationError):
        service.refresh("stale")
