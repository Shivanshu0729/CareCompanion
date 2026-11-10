from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from src.auth.authentication import (
    AuthenticationError,
    AuthService,
    EmailConfirmationRequired,
)


def render_auth(
    auth: AuthService,
    persist_session: Callable[[object], None] | None = None,
) -> None:
    st.markdown('<div class="cc-kicker">CareCompanion</div>', unsafe_allow_html=True)
    st.title("A coach that remembers your wellness journey")
    st.caption("Sign in to continue conversations, goals and health insights.")

    mode = st.session_state.get("auth_mode", "login")
    left, right = st.columns((1.15, 0.85), gap="large")
    with right:
        st.markdown(
            """
            <div class="cc-card">
              <div class="cc-kicker">What you get</div>
              <p>Persistent memory across conversations, labelled PMData insights, and coaching that adapts when a plan does not work.</p>
              <p class="source-pill">Wellness coaching, not medical diagnosis</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with left:
        if mode == "register":
            _register(auth, persist_session)
        elif mode == "forgot":
            _forgot(auth)
        elif mode == "reset":
            _reset(auth)
        else:
            _login(auth, persist_session)


def _persist(persist_session: Callable[[object], None] | None, session: object) -> None:
    if persist_session is not None:
        persist_session(session)


def _login(
    auth: AuthService,
    persist_session: Callable[[object], None] | None,
) -> None:
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")
    if submitted:
        try:
            session = auth.sign_in(email, password)
            st.session_state.auth_session = session
            _persist(persist_session, session)
            st.rerun()
        except AuthenticationError as exc:
            st.error(str(exc))
    cols = st.columns(2)
    if cols[0].button("Create an account"):
        st.session_state.auth_mode = "register"
        st.rerun()
    if cols[1].button("Forgot password"):
        st.session_state.auth_mode = "forgot"
        st.rerun()


def _register(
    auth: AuthService,
    persist_session: Callable[[object], None] | None,
) -> None:
    with st.form("register_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Create account")
    if submitted:
        if password != confirm:
            st.error("Passwords do not match.")
        else:
            try:
                session = auth.sign_up(email, password)
                st.session_state.auth_session = session
                _persist(persist_session, session)
                st.success("Account created.")
                st.rerun()
            except EmailConfirmationRequired as exc:
                st.info(str(exc))
                st.session_state.auth_mode = "login"
            except AuthenticationError as exc:
                st.error(str(exc))
    if st.button("Back to sign in"):
        st.session_state.auth_mode = "login"
        st.rerun()


def _forgot(auth: AuthService) -> None:
    with st.form("forgot_form"):
        email = st.text_input("Account email")
        submitted = st.form_submit_button("Send reset email")
    if submitted:
        try:
            auth.request_password_reset(email)
            st.success("If the account exists, a reset email has been sent.")
        except AuthenticationError as exc:
            st.error(str(exc))
    if st.button("Back to sign in", key="forgot_back"):
        st.session_state.auth_mode = "login"
        st.rerun()


def _reset(auth: AuthService) -> None:
    st.info("Use the recovery session from your email link, then choose a new password.")
    with st.form("reset_form"):
        password = st.text_input("New password", type="password")
        submitted = st.form_submit_button("Update password")
    session = st.session_state.get("auth_session")
    if submitted:
        if session is None:
            st.error("No recovery session is available. Open the reset link again.")
        else:
            try:
                auth.update_password(session.access_token, password)
                st.success("Password updated. You can continue.")
                st.session_state.auth_mode = "login"
            except AuthenticationError as exc:
                st.error(str(exc))
