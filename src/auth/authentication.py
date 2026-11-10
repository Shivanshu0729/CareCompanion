from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config.settings import Settings, get_settings
from src.database.connection import DatabaseConfigurationError, create_public_client


class AuthenticationError(RuntimeError):
    """Raised when authentication fails."""


class EmailConfirmationRequired(AuthenticationError):
    """Raised when signup succeeds but Supabase requires email confirmation."""


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str


@dataclass
class AuthSession:
    user: AuthUser
    access_token: str
    refresh_token: str


def _extract_session(result: Any) -> AuthSession:
    session = getattr(result, "session", None)
    user = getattr(result, "user", None)
    if session is None or user is None:
        raise AuthenticationError("Authentication did not return a session. Confirm the email if required.")
    user_id = getattr(user, "id", None)
    email = getattr(user, "email", None) or ""
    access_token = getattr(session, "access_token", None)
    refresh_token = getattr(session, "refresh_token", None) or ""
    if not user_id or not access_token:
        raise AuthenticationError("Authentication session was incomplete.")
    return AuthSession(
        user=AuthUser(id=str(user_id), email=str(email)),
        access_token=str(access_token),
        refresh_token=str(refresh_token),
    )


class AuthService:
    def __init__(self, client: Any | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = client

    def _client_or_create(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            self._client = create_public_client(self.settings)
        except DatabaseConfigurationError as exc:
            raise AuthenticationError(str(exc)) from exc
        return self._client

    def ensure_profile(self, session: AuthSession) -> None:
        client = self._client_or_create()
        refreshed = client.auth.set_session(session.access_token, session.refresh_token)
        active_session = getattr(refreshed, "session", None)
        access_token = getattr(active_session, "access_token", None) or session.access_token
        client.postgrest.auth(access_token)
        try:
            client.table("users").upsert(
                {"id": session.user.id, "email": session.user.email},
                on_conflict="id",
            ).execute()
        except Exception as exc:
            raise AuthenticationError(
                "Signed in, but the user profile could not be stored. "
                f"Supabase returned: {exc}"
            ) from exc

    def sign_up(self, email: str, password: str, display_name: str = "") -> AuthSession:
        email = email.strip().lower()
        display_name = display_name.strip()[:80]
        if not email or not password:
            raise AuthenticationError("Email and password are required.")
        if len(password) < 8:
            raise AuthenticationError("Password must be at least 8 characters.")
        client = self._client_or_create()
        try:
            result = client.auth.sign_up({"email": email, "password": password})
        except Exception as exc:
            message = str(exc).lower()
            if "already" in message or "registered" in message or "duplicate" in message:
                detail = "This email is already registered. Try signing in instead."
            elif "email" in message and "invalid" in message:
                detail = "Enter a valid email address."
            elif "password" in message:
                detail = "This password does not meet the account requirements."
            else:
                detail = "Registration could not be completed. Check your details and try again."
            raise AuthenticationError(detail) from exc
        if getattr(result, "session", None) is None and getattr(result, "user", None) is not None:
            raise EmailConfirmationRequired(
                "Registration succeeded. Check your email and confirm your account before signing in."
            )
        session = _extract_session(result)
        self.ensure_profile(session)
        return session

    def sign_in(self, email: str, password: str) -> AuthSession:
        email = email.strip().lower()
        if not email or not password:
            raise AuthenticationError("Email and password are required.")
        client = self._client_or_create()
        try:
            result = client.auth.sign_in_with_password({"email": email, "password": password})
        except Exception as exc:
            raise AuthenticationError("Login failed. Check your email and password.") from exc
        session = _extract_session(result)
        self.ensure_profile(session)
        return session

    def refresh(self, refresh_token: str) -> AuthSession:
        if not refresh_token:
            raise AuthenticationError("Your session expired. Please sign in again.")
        client = self._client_or_create()
        try:
            result = client.auth.refresh_session(refresh_token)
        except Exception as exc:
            raise AuthenticationError("Your session expired. Please sign in again.") from exc
        session = _extract_session(result)
        self.ensure_profile(session)
        return session

    def request_password_reset(self, email: str) -> None:
        email = email.strip().lower()
        if not email:
            raise AuthenticationError("Enter the email associated with your account.")
        client = self._client_or_create()
        redirect_to = self.settings.app_url
        try:
            client.auth.reset_password_for_email(email, {"redirect_to": redirect_to})
        except Exception as exc:
            raise AuthenticationError("Could not send a password reset email.") from exc

    def update_password(self, access_token: str, new_password: str) -> None:
        if len(new_password) < 8:
            raise AuthenticationError("Password must be at least 8 characters.")
        client = self._client_or_create()
        client.postgrest.auth(access_token)
        try:
            client.auth.update_user({"password": new_password})
        except Exception as exc:
            raise AuthenticationError("Could not update the password. Request a new reset link.") from exc

    def sign_out(self) -> None:
        client = self._client_or_create()
        try:
            client.auth.sign_out()
        except Exception:
            return
