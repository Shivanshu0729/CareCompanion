from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.agent.memory_manager import MemoryManager
from src.data.health_service import HealthService
from src.database.store import CareStore


def render_dashboard(store: CareStore, health_service: HealthService, user_id: str) -> None:
    st.markdown('<div class="cc-kicker">Health dashboard</div>', unsafe_allow_html=True)
    st.title("Health Dashboard")
    st.caption("PMData demo data is labelled research data, not your personal measurements.")

    manager = MemoryManager(store)
    available = health_service.available_participants()
    if not available:
        st.warning("No processed PMData summaries were found. Run `python scripts/process_pmdata.py` after adding raw files.")
        return

    current = manager.demo_participant(user_id)
    if current not in available:
        current = available[0]
    participant = st.selectbox("Demo participant mapping", available, index=available.index(current))
    if participant != current:
        manager.set_demo_participant(user_id, participant)

    frame = health_service.participant_frame(participant)
    if frame.empty:
        st.info("No measurements are available for this participant.")
        return

    frame["measurement_date"] = pd.to_datetime(frame["measurement_date"])
    start = st.date_input("Start date", value=frame["measurement_date"].min().date())
    end = st.date_input("End date", value=frame["measurement_date"].max().date())
    filtered = health_service.filter_dates(frame, start, end)
    st.markdown(
        f'<span class="source-pill">Source: PMData</span> &nbsp; Participant {participant} &nbsp; {start} to {end}',
        unsafe_allow_html=True,
    )

    metric_map = {
        "Daily steps": "steps",
        "Sleep hours": "sleep_hours",
        "Active minutes": "active_minutes",
        "Resting heart rate": "resting_heart_rate",
    }
    available_metrics = [
        (label, key)
        for label, key in metric_map.items()
        if key in filtered.columns and filtered[key].notna().any()
    ]
    if not available_metrics:
        st.info("No measured values are available in the selected range.")
        return
    cards = st.columns(min(len(available_metrics), 3))
    for column, (label, key) in zip(cards, available_metrics):
        summary = health_service.metric_card(filtered, key)
        with column:
            st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div>', unsafe_allow_html=True)
            st.metric("Latest", f"{summary['latest']:.1f}", help=f"Average {summary['average']:.1f}")
            st.markdown("</div>", unsafe_allow_html=True)

    chart_label, chart_key = available_metrics[0]
    st.subheader(f"{chart_label} trend")
    chart_data = filtered[["measurement_date", chart_key]].dropna()
    figure = px.line(
        chart_data,
        x="measurement_date",
        y=chart_key,
        markers=True,
        template="simple_white",
        labels={"measurement_date": "Date", chart_key: chart_label},
    )
    figure.update_layout(margin=dict(l=10, r=10, t=20, b=10), showlegend=False)
    st.plotly_chart(figure, use_container_width=True)
