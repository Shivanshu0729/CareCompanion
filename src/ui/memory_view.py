from __future__ import annotations

import streamlit as st

from src.database.models import MemoryRecord
from src.database.store import CareStore
from src.services.text_utils import canonical_memory_key


def render_memory(store: CareStore, user_id: str) -> None:
    st.markdown('<div class="cc-kicker">Persistent Memory</div>', unsafe_allow_html=True)
    st.title("What CareCompanion remembers")
    st.caption("These records persist across conversations and threads. Correct or delete anything that is outdated.")

    last_turn = st.session_state.get("last_turn")
    if last_turn and last_turn.memories_used:
        with st.expander("Context used in the latest reply", expanded=False):
            for memory in last_turn.memories_used:
                st.markdown(f"**{memory.kind.title()}**: {memory.content}")

    # Add memory quick-form
    with st.expander("+ Add a new memory manually", expanded=False):
        with st.form("manual-memory-form"):
            category = st.selectbox(
                "Category",
                ["profile", "goal", "context", "progress", "preference", "health"],
                format_func=lambda x: {
                    "profile": "Profile (Education, Profession, Skills)",
                    "goal": "Goal (Career, Learning, Fitness)",
                    "context": "Context (Ongoing Projects, Architecture)",
                    "progress": "Progress (Milestones, Completed Tasks)",
                    "preference": "Preference (Style, Tone, Diet)",
                    "health": "Health (Conditions, Limitations)",
                }.get(x, x),
            )
            content = st.text_input("Memory statement", placeholder="e.g. Currently learning Python and building CareCompanion")
            submitted = st.form_submit_button("Save Memory")
            if submitted and content.strip():
                c_key = canonical_memory_key(category, content.strip())
                store.add_memory(
                    MemoryRecord(
                        user_id=user_id,
                        memory_type=category,
                        memory_content=content.strip(),
                        source="user_reported",
                        confidence=1.0,
                        importance=0.8,
                        confirmed=True,
                        is_current=True,
                        memory_key=c_key,
                    )
                )
                st.success("Memory saved successfully!")
                st.rerun()

    groups = {
        "Profile & Personal Context": store.list_memories(user_id, "profile"),
        "Goals": [
            *store.list_memories(user_id, "goal"),
            *[m for m in store.list_goals(user_id) if not any(g.memory_content == m.goal_description for g in store.list_memories(user_id, "goal"))],
        ],
        "Ongoing Projects & Context": store.list_memories(user_id, "context"),
        "Progress & Milestones": [
            *store.list_memories(user_id, "progress"),
            *store.list_outcomes(user_id),
        ],
        "Preferences": store.list_memories(user_id, "preference"),
        "Health & Limitations": store.list_memories(user_id, "health"),
        "Recommendations": store.list_recommendations(user_id),
        "Obstacles": store.list_obstacles(user_id),
        "Session summaries": store.list_session_summaries(user_id),
    }

    for title, items in groups.items():
        st.subheader(title)
        active_items = [it for it in items if getattr(it, "is_current", True)]
        if not active_items:
            st.caption("Nothing stored in this category.")
            continue

        for item in active_items:
            if hasattr(item, "memory_content"):
                label = f"{item.memory_type.title()} · {item.source}"
                content = item.memory_content
                key = f"mem-{item.id}"
                cols = st.columns((5, 1, 1))
                edited = cols[0].text_area(label, value=content, key=f"{key}-text", label_visibility="collapsed")
                if cols[1].button("Save", key=f"{key}-save"):
                    store.update_memory(user_id, item.id, edited)
                    st.rerun()
                if cols[2].button("Delete", key=f"{key}-del"):
                    store.delete_memory(user_id, item.id)
                    st.rerun()
            elif hasattr(item, "goal_description"):
                st.write(f"{item.goal_description} · {item.status}")
            elif hasattr(item, "recommendation"):
                st.write(item.recommendation)
            elif hasattr(item, "obstacle_description"):
                st.write(item.obstacle_description)
            elif hasattr(item, "reported_outcome"):
                st.write(item.reported_outcome)
            elif hasattr(item, "summary"):
                st.write(item.summary)
