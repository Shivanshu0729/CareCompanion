from __future__ import annotations

import streamlit as st

from src.database.store import CareStore


def render_memory(store: CareStore, user_id: str) -> None:
    st.markdown('<div class="cc-kicker">My memory</div>', unsafe_allow_html=True)
    st.title("What CareCompanion remembers")
    st.caption("These records persist across conversations. Correct or delete anything that is wrong.")

    last_turn = st.session_state.get("last_turn")
    if last_turn and last_turn.memories_used:
        st.subheader("Used in the latest reply")
        for memory in last_turn.memories_used:
            st.write(f"{memory.kind}: {memory.content}")

    groups = {
        "Goals": store.list_goals(user_id),
        "Preferences": store.list_memories(user_id, "preference"),
        "Recommendations": store.list_recommendations(user_id),
        "Obstacles": store.list_obstacles(user_id),
        "Outcomes": store.list_outcomes(user_id),
        "Session summaries": store.list_session_summaries(user_id),
        "Other memories": [
            item for item in store.list_memories(user_id) if item.memory_type not in {"setting"}
        ],
    }
    for title, items in groups.items():
        st.subheader(title)
        if not items:
            st.info("Nothing stored yet.")
            continue
        for item in items:
            if hasattr(item, "memory_content"):
                label = f"{item.memory_type} · {item.source}"
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
