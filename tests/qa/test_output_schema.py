from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from ofh_synthetic_data.config import PathsConfig, load_config
from ofh_synthetic_data.generate.registry_generator import (
    generate_tables_from_processed_registries,
    write_generated_tables,
)
from ofh_synthetic_data.ingest.registries import build_registries
from ofh_synthetic_data.validate.outputs import validate_synthetic_outputs

pytestmark = pytest.mark.qa

SUPPORTED_DICTIONARY_TYPES = {"date", "float", "integer", "string"}


def test_generated_outputs_match_dictionary_schema(tmp_path: Path) -> None:
    config = load_config("configs/default.yaml")
    config = replace(
        config,
        paths=PathsConfig(
            raw_data_dir=config.paths.raw_data_dir,
            interim_data_dir=tmp_path / "interim",
            processed_data_dir=tmp_path / "processed",
            synthetic_data_dir=tmp_path / "synthetic",
            reports_dir=tmp_path / "reports",
        ),
    )

    build_registries(config)
    tables = generate_tables_from_processed_registries(config)
    write_generated_tables(tables, config.paths.synthetic_data_dir, config.generation)

    result = validate_synthetic_outputs(config)
    assert result.passed, [f"{error.check}: {error.message}" for error in result.errors]

    field_registry = _read_csv(config.paths.processed_data_dir / "field_registry.csv")
    participants = _read_csv(config.paths.synthetic_data_dir / config.generation.participant_file)
    questionnaires = _read_csv(
        config.paths.synthetic_data_dir / config.generation.questionnaire_file,
    )

    _assert_table_matches_dictionary_schema(participants, field_registry, "participant")
    _assert_table_matches_dictionary_schema(questionnaires, field_registry, "questionnaire")


def _assert_table_matches_dictionary_schema(
    table: pd.DataFrame,
    field_registry: pd.DataFrame,
    entity: str,
) -> None:
    fields = _fields_for_entity(field_registry, entity)
    expected_columns = fields["name"].astype(str).tolist()

    assert table.columns.astype(str).tolist() == expected_columns

    unknown_types = sorted(
        {
            field_type
            for field_type in fields["type"].astype(str).str.lower().unique()
            if field_type not in SUPPORTED_DICTIONARY_TYPES
        },
    )
    assert unknown_types == []

    for field in fields.to_dict("records"):
        name = str(field["name"])
        field_type = str(field["type"]).lower()
        non_blank = table[name][table[name].map(lambda value: not _is_blank(value))]

        if non_blank.empty:
            continue

        if _as_bool(field.get("is_multi_select")):
            _assert_multi_select_values_are_integer_codes(name, non_blank)
        elif field_type == "integer":
            _assert_integer_values(name, non_blank)
        elif field_type == "float":
            _assert_numeric_values(name, non_blank)
        elif field_type == "date":
            _assert_date_values(name, non_blank)
        elif field_type == "string":
            _assert_string_values(name, non_blank)


def _assert_integer_values(name: str, values: pd.Series) -> None:
    numeric = pd.to_numeric(values, errors="coerce")
    assert not numeric.isna().any(), f"{name} contains non-numeric values"
    assert not (numeric % 1 != 0).any(), f"{name} contains non-integer values"


def _assert_numeric_values(name: str, values: pd.Series) -> None:
    numeric = pd.to_numeric(values, errors="coerce")
    assert not numeric.isna().any(), f"{name} contains non-numeric values"


def _assert_date_values(name: str, values: pd.Series) -> None:
    invalid_values = []
    for value in values:
        try:
            date.fromisoformat(str(value))
        except ValueError:
            invalid_values.append(value)

    assert invalid_values == [], f"{name} contains invalid ISO date values"


def _assert_string_values(name: str, values: pd.Series) -> None:
    non_string_count = values.map(lambda value: not isinstance(value, str)).sum()
    assert non_string_count == 0, f"{name} contains non-string values"


def _assert_multi_select_values_are_integer_codes(name: str, values: pd.Series) -> None:
    invalid_values = []
    for value in values:
        text = str(value).strip()
        if not (text.startswith("[") and text.endswith("]")):
            invalid_values.append(value)
            continue

        options = [option.strip() for option in text[1:-1].split(",") if option.strip()]
        if not options or any(not _is_integer_text(option) for option in options):
            invalid_values.append(value)

    assert invalid_values == [], f"{name} contains invalid multi-select integer codes"


def _fields_for_entity(field_registry: pd.DataFrame, entity: str) -> pd.DataFrame:
    fields = field_registry[field_registry["entity"] == entity].copy()
    fields["_dictionary_order"] = pd.to_numeric(fields["dictionary_order"], errors="coerce")
    return fields.sort_values("_dictionary_order", kind="stable").drop(
        columns=["_dictionary_order"],
    )


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=object).where(pd.notna, "")


def _is_blank(value: object) -> bool:
    return str(value).strip() == ""


def _is_integer_text(value: str) -> bool:
    return value.startswith("-") and value[1:].isdigit() or value.isdigit()


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}
