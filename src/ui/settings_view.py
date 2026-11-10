from __future__ import annotations

import streamlit as st

from src.agent.memory_manager import MemoryManager
from src.data.health_service import HealthService
from src.database.store import CareStore


def render_settings(store: CareStore, health_service: HealthService, user_id: str, email: str) -> None:
    st.markdown('<div class="cc-kicker">Settings</div>', unsafe_allow_html=True)
    st.title("Workspace settings")

    st.subheader("Demo participant mapping")
    st.write(
        "PMData contains research participants. Mapping a participant only attaches labelled demo measurements. "
        "It does not mean those readings belong to you."
    )
    manager = MemoryManager(store)
    available = health_service.available_participants() or ["p01"]
    current = manager.demo_participant(user_id)
    if current not in available:
        current = available[0]
    selected = st.selectbox("Research participant", available, index=available.index(current))
    if st.button("Save mapping"):
        manager.set_demo_participant(user_id, selected)
        st.success(f"Mapped this account to labelled participant {selected}.")

    st.subheader("Three-session demonstration")
    st.markdown(
        """
1. Start a conversation and say: *I have an inconsistent sleep schedule. I want to improve my sleep routine.*
2. Click **New Conversation** and say: *I tried sleeping at 11 PM, but I could not maintain it.*
3. Start another conversation and say: *I managed to maintain a more consistent bedtime for the last few days.*

Then open **My Memory** to inspect stored goals, obstacles, outcomes and the memories used in the latest reply.
        """
    )

    st.subheader("Account")
    st.write(f"Signed in as {email}")
    st.caption("Passwords are managed by Supabase Auth and are never stored in application tables.")


def render_profile(email: str, user_id: str) -> None:
    st.markdown('<div class="cc-kicker">Profile</div>', unsafe_allow_html=True)
    st.title("User profile")
    st.markdown(f"<div class='cc-card'><strong>Email</strong><br>{email}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='cc-card'><strong>User ID</strong><br>{user_id}</div>", unsafe_allow_html=True)
    st.caption("This identifier is the Supabase Auth user id used for row-level data isolation.")
