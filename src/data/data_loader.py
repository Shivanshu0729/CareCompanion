from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


SUPPORTED_DAILY_FILES = {
    "sedentary_minutes.json": "sedentary_minutes",
    "lightly_active_minutes.json": "lightly_active_minutes",
    "moderately_active_minutes.json": "moderately_active_minutes",
    "very_active_minutes.json": "very_active_minutes",
}


def discover_participants(raw_root: Path) -> list[str]:
    if not raw_root.exists():
        return []
    participants = []
    for path in sorted(raw_root.iterdir()):
        if path.is_dir() and path.name.lower().startswith("p"):
            participants.append(path.name)
    return participants


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _parse_datetime(value: Any) -> pd.Timestamp | pd.NaT:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return pd.NaT
    return pd.to_datetime(value, errors="coerce", utc=False)


def datetime_value_frame(records: list[dict[str, Any]], value_name: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        timestamp = record.get("dateTime") or record.get("date") or record.get("timestamp")
        value = record.get("value")
        if isinstance(value, dict):
            value = value.get("value")
        rows.append({"timestamp": timestamp, value_name: value})
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["timestamp"] = frame["timestamp"].map(_parse_datetime)
    frame = frame.dropna(subset=["timestamp"])
    frame[value_name] = pd.to_numeric(frame[value_name], errors="coerce")
    frame["measurement_date"] = frame["timestamp"].dt.date
    return frame


def load_daily_minutes(path: Path, column_name: str) -> pd.DataFrame:
    records = load_json(path)
    if not isinstance(records, list):
        return pd.DataFrame()
    frame = datetime_value_frame(records, column_name)
    if frame.empty:
        return frame
    return (
        frame.groupby("measurement_date", as_index=False)[column_name]
        .sum(min_count=1)
        .drop_duplicates(subset=["measurement_date"])
    )


def load_resting_heart_rate(path: Path) -> pd.DataFrame:
    records = load_json(path)
    if not isinstance(records, list):
        return pd.DataFrame()
    frame = datetime_value_frame(records, "resting_heart_rate")
    if frame.empty:
        return frame
    return (
        frame.groupby("measurement_date", as_index=False)["resting_heart_rate"]
        .mean()
        .drop_duplicates(subset=["measurement_date"])
    )


def load_steps(path: Path) -> pd.DataFrame:
    records = load_json(path)
    if not isinstance(records, list):
        return pd.DataFrame()
    frame = datetime_value_frame(records, "steps")
    if frame.empty:
        return frame
    return (
        frame.groupby("measurement_date", as_index=False)["steps"]
        .sum(min_count=1)
        .drop_duplicates(subset=["measurement_date"])
    )


def load_sleep(path: Path) -> pd.DataFrame:
    records = load_json(path)
    if not isinstance(records, list):
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        date_value = record.get("dateOfSleep") or record.get("date")
        minutes = record.get("minutesAsleep")
        duration_ms = record.get("duration")
        if minutes is None and duration_ms is not None:
            try:
                minutes = float(duration_ms) / 60000.0
            except (TypeError, ValueError):
                minutes = None
        rows.append(
            {
                "measurement_date": date_value,
                "sleep_minutes": minutes,
                "time_in_bed_minutes": record.get("timeInBed"),
                "sleep_efficiency": record.get("efficiency"),
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["measurement_date"] = pd.to_datetime(frame["measurement_date"], errors="coerce").dt.date
    frame = frame.dropna(subset=["measurement_date"])
    for column in ("sleep_minutes", "time_in_bed_minutes", "sleep_efficiency"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.groupby("measurement_date", as_index=False).agg(
        {
            "sleep_minutes": "sum",
            "time_in_bed_minutes": "sum",
            "sleep_efficiency": "mean",
        }
    )


def load_sleep_score(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if frame.empty:
        return frame
    frame.columns = [str(column).strip() for column in frame.columns]
    timestamp_col = "timestamp" if "timestamp" in frame.columns else frame.columns[0]
    frame["measurement_date"] = pd.to_datetime(frame[timestamp_col], errors="coerce").dt.date
    frame = frame.dropna(subset=["measurement_date"])
    keep = {
        "overall_score": "sleep_score",
        "deep_sleep_in_minutes": "deep_sleep_minutes",
        "resting_heart_rate": "sleep_score_resting_heart_rate",
        "restlessness": "sleep_restlessness",
    }
    available = {source: target for source, target in keep.items() if source in frame.columns}
    subset = frame[["measurement_date", *available.keys()]].copy()
    subset = subset.rename(columns=available)
    for column in subset.columns:
        if column != "measurement_date":
            subset[column] = pd.to_numeric(subset[column], errors="coerce")
    return subset.drop_duplicates(subset=["measurement_date"])


def inspect_fitbit_dir(fitbit_dir: Path) -> dict[str, bool]:
    names = [
        "steps.json",
        "sleep.json",
        "sleep_score.csv",
        "resting_heart_rate.json",
        *SUPPORTED_DAILY_FILES.keys(),
    ]
    return {name: (fitbit_dir / name).exists() for name in names}


def load_participant(raw_root: Path, participant_id: str) -> dict[str, pd.DataFrame]:
    fitbit_dir = raw_root / participant_id / "fitbit"
    if not fitbit_dir.exists():
        return {}
    loaded: dict[str, pd.DataFrame] = {}
    steps_path = fitbit_dir / "steps.json"
    if steps_path.exists():
        loaded["steps"] = load_steps(steps_path)
    sleep_path = fitbit_dir / "sleep.json"
    if sleep_path.exists():
        loaded["sleep"] = load_sleep(sleep_path)
    score_path = fitbit_dir / "sleep_score.csv"
    if score_path.exists():
        loaded["sleep_score"] = load_sleep_score(score_path)
    rhr_path = fitbit_dir / "resting_heart_rate.json"
    if rhr_path.exists():
        loaded["resting_heart_rate"] = load_resting_heart_rate(rhr_path)
    for filename, column_name in SUPPORTED_DAILY_FILES.items():
        path = fitbit_dir / filename
        if path.exists():
            loaded[column_name] = load_daily_minutes(path, column_name)
    return loaded
