from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data.data_cleaner import reject_impossible_values
from src.data.data_loader import inspect_fitbit_dir, load_participant
from src.data.feature_engineering import merge_participant_tables, process_raw_dataset
from src.data.health_service import HealthService, reset_health_cache
from tests.conftest import write_pmdata_fixture


def test_cleaning_and_summaries(tmp_path: Path) -> None:
    write_pmdata_fixture(tmp_path)
    tables = load_participant(tmp_path, "p01")
    assert set(tables) >= {"steps", "sleep", "resting_heart_rate", "sedentary_minutes"}
    daily = merge_participant_tables(tables, "p01")
    assert daily["steps"].notna().all()
    assert daily["sleep_hours"].between(1, 16).all()
    dirty = pd.DataFrame({"steps": [-4, 1000], "sleep_minutes": [5000, 400], "resting_heart_rate": [10, 55]})
    cleaned = reject_impossible_values(dirty)
    assert pd.isna(cleaned.loc[0, "steps"])
    assert pd.isna(cleaned.loc[0, "sleep_minutes"])
    assert pd.isna(cleaned.loc[0, "resting_heart_rate"])

    processed = tmp_path / "processed"
    output = process_raw_dataset(tmp_path, processed)
    assert not output.empty
    reset_health_cache()
    service = HealthService(processed_path=processed / "daily_summaries.csv")
    context = service.context_for_query("p01", "review my sleep")
    assert context.participant_id == "p01"
    assert "sleep_hours" in context.available_metrics or context.recent_rows
    files = inspect_fitbit_dir(tmp_path / "p01" / "fitbit")
    assert files["sleep.json"] is True
