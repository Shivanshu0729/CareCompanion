from __future__ import annotations

import streamlit as st

from src.database.store import CareStore
from src.services.dashboard_service import DashboardService


def render_goals(store: CareStore, user_id: str) -> None:
    st.markdown('<div class="cc-kicker">My goals</div>', unsafe_allow_html=True)
    st.title("Goals, recommendations and progress")
    st.caption("Goals are only marked complete when you say so. The coach never auto-completes them.")

    dashboard = DashboardService(store)
    grouped = dashboard.goals_by_status(user_id)

    columns = st.columns(3)
    for column, status, title in zip(
        columns,
        ("active", "needs_attention", "completed"),
        ("Active", "Needs attention", "Completed"),
    ):
        with column:
            st.subheader(title)
            items = grouped.get(status, [])
            if not items:
                st.info("None yet.")
            for goal in items:
                st.markdown(f"<div class='cc-card'>{goal.goal_description}</div>", unsafe_allow_html=True)
                if status != "completed" and st.button("Mark completed", key=f"done-{goal.id}"):
                    store.update_goal_status(user_id, goal.id, "completed")
                    st.rerun()

    st.subheader("Previous recommendations")
    recommendations = store.list_recommendations(user_id)
    if not recommendations:
        st.info("No recommendations stored yet.")
    for item in recommendations:
        st.write(item.recommendation)

    st.subheader("User-reported progress")
    outcomes = store.list_outcomes(user_id)
    if not outcomes:
        st.info("No reported outcomes yet.")
    for item in outcomes:
        st.write(item.reported_outcome)
