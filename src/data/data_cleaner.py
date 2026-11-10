from __future__ import annotations

import pandas as pd


def drop_duplicate_dates(frame: pd.DataFrame, date_column: str = "measurement_date") -> pd.DataFrame:
    if frame.empty or date_column not in frame.columns:
        return frame.copy()
    return frame.drop_duplicates(subset=[date_column], keep="last").copy()


def coerce_numeric(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    cleaned = frame.copy()
    for column in columns:
        if column in cleaned.columns:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
    return cleaned


def reject_impossible_values(frame: pd.DataFrame) -> pd.DataFrame:
    cleaned = frame.copy()
    if "steps" in cleaned.columns:
        cleaned.loc[cleaned["steps"] < 0, "steps"] = pd.NA
    if "sleep_minutes" in cleaned.columns:
        cleaned.loc[(cleaned["sleep_minutes"] < 0) | (cleaned["sleep_minutes"] > 24 * 60), "sleep_minutes"] = pd.NA
    if "resting_heart_rate" in cleaned.columns:
        cleaned.loc[
            (cleaned["resting_heart_rate"] < 30) | (cleaned["resting_heart_rate"] > 140),
            "resting_heart_rate",
        ] = pd.NA
    for column in (
        "sedentary_minutes",
        "lightly_active_minutes",
        "moderately_active_minutes",
        "very_active_minutes",
    ):
        if column in cleaned.columns:
            cleaned.loc[(cleaned[column] < 0) | (cleaned[column] > 24 * 60), column] = pd.NA
    return cleaned


def preserve_missing(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.replace({float("nan"): pd.NA})
