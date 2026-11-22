from __future__ import annotations

import streamlit as st
import extra_streamlit_components as stx

from config.settings import get_settings
from src.agent.coach import WellnessCoach
from src.auth.authentication import AuthenticationError, AuthService
from src.auth.session_cookie import (
    COOKIE_NAME,
    clear_session,
    decode_session,
    save_session,
)
from src.data.health_service import HealthService
from src.database.connection import DatabaseConfigurationError, create_authenticated_client
from src.database.repository import SupabaseCareStore
from src.llm.groq_client import GroqClient
from src.services.conversation_service import ConversationService
from src.ui.auth_view import render_auth
from src.ui.chat_view import render_chat
from src.ui.dashboard_view import render_dashboard
from src.ui.styles import inject_styles

st.set_page_config(page_title="CareCompanion", page_icon="C", layout="wide")
inject_styles(st)

settings = get_settings()
auth = AuthService(settings=settings)
cookie_manager = stx.CookieManager()


def persist_session(session) -> None:
    save_session(cookie_manager, session, settings)


if "page" not in st.session_state:
    st.session_state.page = "chat"
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"

query = st.query_params
if query.get("type") == "recovery":
    st.session_state.auth_mode = "reset"

if "auth_session" not in st.session_state:
    stored_session = decode_session(cookie_manager.get(COOKIE_NAME), settings)
    if stored_session is not None:
        try:
            st.session_state.auth_session = auth.refresh(stored_session.refresh_token)
            persist_session(st.session_state.auth_session)
        except AuthenticationError:
            clear_session(cookie_manager)
    if "auth_session" not in st.session_state:
        render_auth(auth, persist_session)
        st.stop()

session = st.session_state.auth_session
try:
    client = create_authenticated_client(session.access_token, settings)
except (DatabaseConfigurationError, Exception) as exc:
    if session.refresh_token:
        try:
            session = auth.refresh(session.refresh_token)
            st.session_state.auth_session = session
            client = create_authenticated_client(session.access_token, settings)
        except AuthenticationError:
            st.session_state.pop("auth_session", None)
            st.error("Your session expired. Please sign in again.")
            st.stop()
    else:
        st.error(str(exc))
        st.stop()

store = SupabaseCareStore(client)
health_service = HealthService()
llm = GroqClient(settings)
coach = WellnessCoach(
    store,
    llm,
    health_service=health_service,
    max_history=settings.max_history_messages,
    max_memories=settings.max_memories_in_context,
)
conversations = ConversationService(store)
user_id = session.user.id


@st.dialog("Rename conversation")
def rename_conversation(conversation_id: str, current_title: str) -> None:
    title = st.text_input("Thread name", value=current_title)
    if st.button("Save", type="primary", use_container_width=True):
        conversations.rename(user_id, conversation_id, title)
        st.session_state.pop("rename_thread", None)
        st.rerun()


@st.dialog("Delete conversation")
def delete_conversation(conversation_id: str, title: str) -> None:
    st.warning(f"Delete “{title}” and its conversation-linked memories?")
    st.caption("This cannot be undone.")
    confirm_col, cancel_col = st.columns(2)
    with confirm_col:
        if st.button("Delete", type="primary", use_container_width=True):
            conversations.delete(user_id, conversation_id)
            if st.session_state.get("conversation_id") == conversation_id:
                st.session_state.pop("conversation_id", None)
                st.session_state.last_turn = None
            st.rerun()
    with cancel_col:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


with st.sidebar:
    st.markdown(
        '<div class="cc-logo"><span class="cc-mark">C</span>CareCompanion</div>',
        unsafe_allow_html=True,
    )
    st.caption("A calm space for better routines")
    if st.button("+  New chat", use_container_width=True, type="primary"):
        created = conversations.create(user_id)
        st.session_state.conversation_id = created.id
        st.session_state.page = "chat"
        st.session_state.last_turn = None
        st.rerun()

    st.markdown('<div class="sidebar-label">Recent conversations</div>', unsafe_allow_html=True)
    conversation_list = conversations.list(user_id)[:20]
    for conversation in conversation_list:
        row = st.columns((6, 1))
        with row[0]:
            if st.button(conversation.title[:32], key=f"c-{conversation.id}", use_container_width=True):
                st.session_state.conversation_id = conversation.id
                st.session_state.page = "chat"
                st.rerun()
        with row[1]:
            with st.popover("⋯", key=f"menu-{conversation.id}"):
                if st.button("✎  Rename", key=f"rename-{conversation.id}"):
                    st.session_state.rename_thread = conversation.id
                    st.rerun()
                st.markdown('<div class="thread-menu-separator"></div>', unsafe_allow_html=True)
                pin_label = "Unpin" if conversation.is_pinned else "Pin"
                if st.button(f"⚑  {pin_label}", key=f"pin-{conversation.id}"):
                    conversations.set_pinned(user_id, conversation.id, not conversation.is_pinned)
                    st.rerun()
                st.markdown('<div class="thread-menu-separator"></div>', unsafe_allow_html=True)
                if st.button("🗑  Delete", key=f"delete-{conversation.id}"):
                    delete_conversation(conversation.id, conversation.title)

    rename_id = st.session_state.get("rename_thread")
    if rename_id:
        rename_target = next(
            (item for item in conversation_list if item.id == rename_id),
            None,
        )
        if rename_target:
            rename_conversation(rename_target.id, rename_target.title)
        else:
            st.session_state.pop("rename_thread", None)

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
    if st.button("Health Dashboard", use_container_width=True):
        st.session_state.page = "dashboard"
        st.rerun()
    st.markdown(
        f'<div class="sidebar-account"><span class="account-dot"></span>'
        f'<span>{session.user.email}</span></div>',
        unsafe_allow_html=True,
    )
    if st.button("Logout", use_container_width=True):
        auth.sign_out()
        clear_session(cookie_manager)
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

if not settings.groq_configured():
    st.warning("The AI service is not configured yet. Add the required settings before the coach can reply.")

page = st.session_state.page
if page == "dashboard":
    render_dashboard(store, health_service, user_id)
else:
    render_chat(store, coach, user_id)
