"""Configuration loading for synthetic data generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class PathsConfig:
    raw_data_dir: Path = Path("data/raw")
    processed_data_dir: Path = Path("data/processed")
    synthetic_data_dir: Path = Path("outputs/synthetic")
    qa_dir: Path = Path("outputs/qa")


@dataclass(frozen=True)
class SourceFilesConfig:
    questionnaire_logic: str = "Our Future Health Baseline Questionnaire Logic v2.2.xlsx"
    data_dictionary: str = "our_future_health_data_dictionary_v14.xlsx"
    codings: str = "our_future_health_codings_v14.xlsx"


@dataclass(frozen=True)
class GenerationConfig:
    rows: int = 200
    seed: int = 42
    participant_file: str = "participant.csv"
    questionnaire_file: str = "questionnaire.csv"
    manifest_file: str = "manifest.json"
    questionnaire_version: str = "v2"


@dataclass(frozen=True)
class RegistryConfig:
    target_entities: tuple[str, ...] = ("participant", "questionnaire")


@dataclass(frozen=True)
class AppConfig:
    paths: PathsConfig = field(default_factory=PathsConfig)
    source_files: SourceFilesConfig = field(default_factory=SourceFilesConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    registry: RegistryConfig = field(default_factory=RegistryConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppConfig:
        """Create config objects from a nested YAML-compatible dictionary."""
        paths = data.get("paths", {})
        source_files = data.get("source_files", {})
        generation = dict(data.get("generation", {}))
        generation.pop("reference_year", None)
        registry = data.get("registry", {})

        return cls(
            paths=PathsConfig(
                raw_data_dir=_path_value(paths, "raw_data_dir", PathsConfig.raw_data_dir),
                processed_data_dir=_path_value(
                    paths,
                    "processed_data_dir",
                    PathsConfig.processed_data_dir,
                ),
                synthetic_data_dir=_path_value(
                    paths,
                    "synthetic_data_dir",
                    PathsConfig.synthetic_data_dir,
                ),
                qa_dir=_path_value(
                    paths,
                    "qa_dir",
                    _path_value(paths, "reports_dir", PathsConfig.qa_dir),
                ),
            ),
            source_files=SourceFilesConfig(**source_files),
            generation=GenerationConfig(**generation),
            registry=RegistryConfig(
                target_entities=tuple(
                    registry.get("target_entities", RegistryConfig.target_entities),
                ),
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable snapshot for output manifests."""
        data = asdict(self)
        data["paths"] = {key: str(value) for key, value in data["paths"].items()}
        data["registry"]["target_entities"] = list(data["registry"]["target_entities"])
        return data


def load_config(path: str | Path) -> AppConfig:
    """Load an application config from YAML."""
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    return AppConfig.from_dict(data)


def _path_value(paths: dict[str, Any], key: str, default: Path) -> Path:
    return Path(paths.get(key, default))
