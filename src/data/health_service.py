from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd

from config.settings import get_settings


DEMO_PARTICIPANTS = [f"p{str(index).zfill(2)}" for index in range(1, 17)]


@dataclass(frozen=True)
class HealthContext:
    participant_id: str
    source_label: str
    date_start: str | None
    date_end: str | None
    recent_rows: list[dict[str, object]]
    available_metrics: list[str]
    notes: list[str]


@lru_cache(maxsize=1)
def load_processed_summaries(path_str: str) -> pd.DataFrame:
    path = Path(path_str)
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    if "measurement_date" in frame.columns:
        frame["measurement_date"] = pd.to_datetime(frame["measurement_date"], errors="coerce").dt.date
    return frame


def reset_health_cache() -> None:
    load_processed_summaries.cache_clear()


class HealthService:
    def __init__(self, processed_path: Path | None = None) -> None:
        settings = get_settings()
        self.processed_path = Path(processed_path or settings.processed_health_path)

    def available_participants(self) -> list[str]:
        frame = load_processed_summaries(str(self.processed_path))
        if frame.empty or "participant_id" not in frame.columns:
            return []
        return sorted(str(value) for value in frame["participant_id"].dropna().unique())

    def participant_frame(self, participant_id: str) -> pd.DataFrame:
        frame = load_processed_summaries(str(self.processed_path))
        if frame.empty:
            return frame
        filtered = frame[frame["participant_id"].astype(str) == str(participant_id)].copy()
        if "measurement_date" in filtered.columns:
            filtered = filtered.sort_values("measurement_date")
        return filtered

    def filter_dates(self, frame: pd.DataFrame, start=None, end=None) -> pd.DataFrame:
        if frame.empty or "measurement_date" not in frame.columns:
            return frame
        work = frame.copy()
        work["measurement_date"] = pd.to_datetime(work["measurement_date"])
        if start is not None:
            work = work[work["measurement_date"] >= pd.to_datetime(start)]
        if end is not None:
            work = work[work["measurement_date"] <= pd.to_datetime(end)]
        return work

    def metric_card(self, frame: pd.DataFrame, column: str) -> dict[str, object]:
        if column not in frame.columns or frame[column].dropna().empty:
            return {
                "metric": column,
                "latest": None,
                "average": None,
                "missing": True,
                "count": 0,
            }
        series = pd.to_numeric(frame[column], errors="coerce")
        return {
            "metric": column,
            "latest": float(series.dropna().iloc[-1]),
            "average": float(series.mean(skipna=True)),
            "missing": False,
            "count": int(series.notna().sum()),
        }

    def context_for_query(self, participant_id: str, query: str, limit: int = 7) -> HealthContext:
        frame = self.participant_frame(participant_id)
        notes = [
            "This is labelled PMData research-participant data, not personal Fitbit data for the signed-in user."
        ]
        if frame.empty:
            return HealthContext(
                participant_id=participant_id,
                source_label="PMData Fitbit research dataset",
                date_start=None,
                date_end=None,
                recent_rows=[],
                available_metrics=[],
                notes=notes + ["No processed measurements are available for this participant."],
            )
        preferred = []
        lowered = query.lower()
        if any(token in lowered for token in ("sleep", "bed", "rest", "insomnia")):
            preferred.extend(["sleep_hours", "sleep_score", "deep_sleep_minutes"])
        if any(token in lowered for token in ("step", "walk", "activ", "exercise")):
            preferred.extend(["steps", "active_minutes", "very_active_minutes"])
        if any(token in lowered for token in ("heart", "rhr", "pulse")):
            preferred.extend(["resting_heart_rate"])
        if not preferred:
            preferred = ["steps", "sleep_hours", "resting_heart_rate", "active_minutes", "sleep_score"]
        available = [
            column
            for column in preferred
            if column in frame.columns and frame[column].notna().any()
        ]
        display_columns = ["measurement_date", *available]
        recent = frame.tail(limit)[display_columns]
        records = []
        for row in recent.to_dict(orient="records"):
            cleaned = {}
            for key, value in row.items():
                if pd.isna(value):
                    cleaned[key] = None
                elif hasattr(value, "isoformat"):
                    cleaned[key] = value.isoformat()
                else:
                    cleaned[key] = value
            records.append(cleaned)
        return HealthContext(
            participant_id=participant_id,
            source_label="PMData Fitbit research dataset",
            date_start=str(frame["measurement_date"].min()),
            date_end=str(frame["measurement_date"].max()),
            recent_rows=records,
            available_metrics=available,
            notes=notes,
        )
