from __future__ import annotations

import streamlit as st

from src.agent.coach import WellnessCoach
from src.database.store import CareStore
from src.llm.exceptions import LLMError
from src.services.conversation_service import ConversationService

SUGGESTED = [
    "Help me improve my sleep routine.",
    "Review my activity patterns.",
    "Help me create a realistic wellness goal.",
    "Show me my progress.",
]


def render_chat(store: CareStore, coach: WellnessCoach, user_id: str) -> None:
    conversations = ConversationService(store)
    conversation_id = st.session_state.get("conversation_id")
    if not conversation_id:
        created = conversations.create(user_id)
        st.session_state.conversation_id = created.id
        conversation_id = created.id
    conversation = store.get_conversation(user_id, conversation_id)
    if conversation is None:
        created = conversations.create(user_id)
        st.session_state.conversation_id = created.id
        conversation = created
        conversation_id = created.id

    st.markdown('<div class="cc-kicker">CareCompanion</div>', unsafe_allow_html=True)
    st.title("Your wellness coach")
    st.markdown(
        '<p class="page-subtitle">A thoughtful space to reflect, build better routines, '
        'and make progress one conversation at a time.</p>',
        unsafe_allow_html=True,
    )
    st.caption(f"Conversation · {conversation.title}")

    messages = store.list_messages(user_id, conversation_id)
    memories = store.list_memories(user_id)
    goals = store.list_goals(user_id)
    relevant_memory = []
    for item in [*goals, *memories]:
        content = getattr(item, "goal_description", None) or getattr(item, "memory_content", None)
        if content and content not in relevant_memory:
            relevant_memory.append(content)
    if relevant_memory:
        with st.expander("What I remember", expanded=False):
            st.markdown(
                "\n".join(f"- {item}" for item in relevant_memory[:4])
            )

    if not messages:
        st.markdown(
            """
            <div class="cc-card">
              <div class="cc-kicker">Welcome</div>
              <h2>Start with what matters today.</h2>
              <p>Your coach can connect this conversation with saved goals, previous sessions, and available PMData demo context.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        cols = st.columns(2)
        for index, prompt in enumerate(SUGGESTED):
            if cols[index % 2].button(prompt, use_container_width=True):
                st.session_state.pending_prompt = prompt
                st.rerun()
    else:
        for message in messages:
            with st.chat_message(message.role):
                st.markdown(message.content)

    pending = st.session_state.pop("pending_prompt", None)
    typed = st.chat_input(
        "Ask about sleep, activity, goals, or your next small step",
        key=f"chat-input-{conversation_id}",
    )
    if isinstance(typed, str):
        user_text = typed.strip()
    else:
        user_text = None
    if pending is not None and user_text is None:
        user_text = pending
    if user_text:
        with st.chat_message("user"):
            st.markdown(user_text)
        with st.chat_message("assistant"):
            with st.spinner("CareCompanion is thinking…"):
                try:
                    turn = coach.respond(
                        user_id,
                        conversation_id,
                        user_text,
                    )
                    st.session_state.last_turn = turn
                    st.markdown(turn.assistant_message)
                    st.rerun()
                except (LLMError, ValueError, KeyError) as exc:
                    st.error(str(exc))
