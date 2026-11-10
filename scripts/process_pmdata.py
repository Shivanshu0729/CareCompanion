from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.feature_engineering import process_raw_dataset


def main() -> None:
    raw_root = ROOT / "data" / "pmdata" / "raw"
    processed_root = ROOT / "data" / "pmdata" / "processed"
    daily = process_raw_dataset(raw_root, processed_root)
    print(f"Processed {len(daily)} daily rows into {processed_root}")


if __name__ == "__main__":
    main()
