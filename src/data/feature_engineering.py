from __future__ import annotations

from functools import reduce

import pandas as pd

from src.data.data_cleaner import coerce_numeric, drop_duplicate_dates, reject_impossible_values
from src.data.data_loader import inspect_fitbit_dir, load_participant


def merge_participant_tables(tables: dict[str, pd.DataFrame], participant_id: str) -> pd.DataFrame:
    frames = []
    for table in tables.values():
        if table is None or table.empty or "measurement_date" not in table.columns:
            continue
        frames.append(drop_duplicate_dates(table))
    if not frames:
        return pd.DataFrame()
    merged = reduce(
        lambda left, right: pd.merge(left, right, on="measurement_date", how="outer"),
        frames,
    )
    merged["participant_id"] = participant_id
    if "resting_heart_rate" not in merged.columns and "sleep_score_resting_heart_rate" in merged.columns:
        merged["resting_heart_rate"] = merged["sleep_score_resting_heart_rate"]
    elif "resting_heart_rate" in merged.columns and "sleep_score_resting_heart_rate" in merged.columns:
        merged["resting_heart_rate"] = merged["resting_heart_rate"].combine_first(
            merged["sleep_score_resting_heart_rate"]
        )
    numeric_columns = [
        column
        for column in merged.columns
        if column not in {"measurement_date", "participant_id"}
    ]
    merged = coerce_numeric(merged, numeric_columns)
    merged = reject_impossible_values(merged)
    if "sleep_minutes" in merged.columns:
        merged["sleep_hours"] = merged["sleep_minutes"] / 60.0
    activity_columns = [
        column
        for column in (
            "lightly_active_minutes",
            "moderately_active_minutes",
            "very_active_minutes",
        )
        if column in merged.columns
    ]
    if activity_columns:
        merged["active_minutes"] = merged[activity_columns].sum(axis=1, min_count=1)
    merged = merged.sort_values("measurement_date").reset_index(drop=True)
    for column in ("steps", "sleep_hours", "resting_heart_rate", "active_minutes"):
        if column in merged.columns:
            merged[f"{column}_7d_avg"] = merged[column].rolling(7, min_periods=3).mean()
            merged[f"{column}_change_7d"] = merged[column] - merged[column].shift(7)
    return merged


def add_weekly_summaries(daily: pd.DataFrame) -> pd.DataFrame:
    if daily.empty:
        return pd.DataFrame()
    work = daily.copy()
    work["measurement_date"] = pd.to_datetime(work["measurement_date"])
    work["week_start"] = work["measurement_date"] - pd.to_timedelta(work["measurement_date"].dt.dayofweek, unit="D")
    aggregations: dict[str, str] = {}
    for column in ("steps", "sleep_hours", "resting_heart_rate", "active_minutes", "sleep_score"):
        if column in work.columns:
            aggregations[column] = "mean"
    if not aggregations:
        return pd.DataFrame()
    weekly = work.groupby(["participant_id", "week_start"], as_index=False).agg(aggregations)
    weekly = weekly.rename(columns={column: f"weekly_avg_{column}" for column in aggregations})
    return weekly


def process_raw_dataset(raw_root, processed_root) -> pd.DataFrame:
    from pathlib import Path

    raw_root = Path(raw_root)
    processed_root = Path(processed_root)
    processed_root.mkdir(parents=True, exist_ok=True)
    participants = []
    daily_frames = []
    for participant_dir in sorted(path for path in raw_root.iterdir() if path.is_dir()):
        participant_id = participant_dir.name
        tables = load_participant(raw_root, participant_id)
        if not tables:
            continue
        daily = merge_participant_tables(tables, participant_id)
        if daily.empty:
            continue
        daily_frames.append(daily)
        participants.append(
            {
                "participant_id": participant_id,
                "files": inspect_fitbit_dir(participant_dir / "fitbit"),
                "start": str(daily["measurement_date"].min()),
                "end": str(daily["measurement_date"].max()),
                "days": int(daily.shape[0]),
            }
        )
    if not daily_frames:
        daily = pd.DataFrame()
    else:
        daily = pd.concat(daily_frames, ignore_index=True)
    daily_path = processed_root / "daily_summaries.csv"
    weekly_path = processed_root / "weekly_summaries.csv"
    manifest_path = processed_root / "dataset_manifest.json"
    daily.to_csv(daily_path, index=False)
    weekly = add_weekly_summaries(daily) if not daily.empty else pd.DataFrame()
    weekly.to_csv(weekly_path, index=False)
    import json

    manifest_path.write_text(json.dumps({"participants": participants}, indent=2), encoding="utf-8")
    return daily
