from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field

from api.deps import (
    CurrentUser,
    api_error,
    clear_session_cookie,
    get_current_user,
    public_message,
    set_session_cookie,
    settings_dep,
)
from config.settings import Settings
from src.auth.authentication import (
    AuthenticationError,
    AuthService,
    EmailConfirmationRequired,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)
    display_name: str = Field(default="", max_length=80)


class ForgotPassword(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class ResetPassword(BaseModel):
    access_token: str = Field(min_length=10)
    new_password: str = Field(min_length=1, max_length=256)


def _user_payload(user_id: str, email: str) -> dict[str, dict[str, str]]:
    return {"user": {"id": user_id, "email": email}}


@router.post("/login")
def login(body: Credentials, response: Response, settings: Settings = Depends(settings_dep)):
    try:
        session = AuthService(settings=settings).sign_in(body.email, body.password)
    except AuthenticationError as exc:
        raise api_error(401, "invalid_credentials", public_message(exc)) from exc
    set_session_cookie(response, session, settings)
    return _user_payload(session.user.id, session.user.email)


@router.post("/register")
def register(body: Credentials, response: Response, settings: Settings = Depends(settings_dep)):
    try:
        session = AuthService(settings=settings).sign_up(
            body.email,
            body.password,
            body.display_name,
        )
    except EmailConfirmationRequired as exc:
        response.status_code = 202
        return {
            "status": "email_confirmation_required",
            "message": public_message(exc),
        }
    except AuthenticationError as exc:
        raise api_error(400, "registration_failed", public_message(exc)) from exc
    set_session_cookie(response, session, settings)
    return _user_payload(session.user.id, session.user.email)


@router.post("/forgot-password")
def forgot_password(body: ForgotPassword, settings: Settings = Depends(settings_dep)):
    try:
        AuthService(settings=settings).request_password_reset(body.email)
    except AuthenticationError as exc:
        raise api_error(400, "reset_failed", public_message(exc)) from exc
    return {"message": "If that email has an account, a reset link is on its way."}


@router.post("/reset-password")
def reset_password(body: ResetPassword, settings: Settings = Depends(settings_dep)):
    try:
        AuthService(settings=settings).update_password(
            body.access_token,
            body.new_password,
        )
    except AuthenticationError as exc:
        raise api_error(400, "reset_failed", public_message(exc)) from exc
    return {"message": "Password updated. You can sign in now."}


@router.post("/logout")
def logout(response: Response):
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/me")
def me(user: CurrentUser = Depends(get_current_user)):
    return _user_payload(user.id, user.email)
