"""Writers for generated synthetic datasets."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def write_records_csv(
    records: list[dict[str, object]],
    path: Path,
    fieldnames: list[str],
) -> None:
    """Write records to CSV with a stable column order."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def write_metadata(metadata: dict[str, Any], path: Path) -> None:
    """Write JSON metadata with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
