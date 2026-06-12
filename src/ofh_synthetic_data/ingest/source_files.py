"""Helpers for discovering expected source artefacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ofh_synthetic_data.config import SourceFilesConfig


@dataclass(frozen=True)
class SourceFileStatus:
    role: str
    path: Path
    exists: bool


def expected_source_files(config: SourceFilesConfig) -> dict[str, str]:
    return {
        "questionnaire_pdf": config.questionnaire_pdf,
        "questionnaire_logic": config.questionnaire_logic,
        "data_dictionary": config.data_dictionary,
        "codings": config.codings,
    }


def discover_inputs(raw_data_dir: Path, config: SourceFilesConfig) -> list[SourceFileStatus]:
    return [
        SourceFileStatus(
            role=role,
            path=raw_data_dir / filename,
            exists=(raw_data_dir / filename).exists(),
        )
        for role, filename in expected_source_files(config).items()
    ]


def missing_inputs(statuses: list[SourceFileStatus]) -> list[SourceFileStatus]:
    return [status for status in statuses if not status.exists]
