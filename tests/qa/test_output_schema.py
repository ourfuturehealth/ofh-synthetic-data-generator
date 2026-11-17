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
    config = _config_for_tmp_path(tmp_path)

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
    _assert_core_timeline_supports_adult_age(participants, questionnaires)


def test_registry_preserves_literal_none_coding_meanings(tmp_path: Path) -> None:
    config = _config_for_tmp_path(tmp_path)
    source_none_keys = _literal_none_coding_keys(
        config.paths.raw_data_dir / config.source_files.codings,
    )

    result = build_registries(config)
    processed_codings = _read_csv(result.coding_registry)
    processed_lookup = {
        _coding_key(row["coding_name"], row["code"]): str(row["meaning"])
        for row in processed_codings.to_dict("records")
    }

    in_scope_none_keys = source_none_keys & set(processed_lookup)
    lost_meanings = {
        key: processed_lookup[key]
        for key in in_scope_none_keys
        if processed_lookup[key] != "None"
    }

    assert in_scope_none_keys
    assert lost_meanings == {}


def test_coded_questionnaire_fields_absent_from_logic_are_blank(tmp_path: Path) -> None:
    config = _config_for_tmp_path(tmp_path)
    result = build_registries(config)
    field_registry = _read_csv(result.field_registry)

    coded_dictionary_fields = field_registry[
        (field_registry["entity"] == "questionnaire")
        & field_registry["coding_found"].map(_as_bool)
        & ~field_registry["is_superseded_version"].map(_as_bool)
        & ~field_registry["in_questionnaire_logic"].map(_as_bool)
    ]
    generated_fields = coded_dictionary_fields[
        coded_dictionary_fields["generation_action"] != "blank"
    ]

    medicat = field_registry[field_registry["name"] == "MEDICAT_1_M"].iloc[0]

    assert not coded_dictionary_fields.empty
    assert "MEDICAT_1_M" not in set(coded_dictionary_fields["name"])
    assert generated_fields[["name", "v2_inclusion_status", "blank_reason"]].to_dict(
        "records",
    ) == []
    assert set(coded_dictionary_fields["v2_inclusion_status"]) == {"not_in_v2_logic"}
    assert set(coded_dictionary_fields["blank_reason"]) == {"not_in_v2_logic"}
    assert _as_bool(medicat["in_questionnaire_logic"])
    assert medicat["v2_inclusion_status"] == "v2_questionnaire_field"
    assert medicat["generation_action"] == "generate"


def test_numeric_range_with_special_code_fields_generate_allowed_values(
    tmp_path: Path,
) -> None:
    config = _config_for_tmp_path(tmp_path)

    result = build_registries(config)
    tables = generate_tables_from_processed_registries(config)
    write_generated_tables(tables, config.paths.synthetic_data_dir, config.generation)

    field_registry = _read_csv(result.field_registry)
    coding_registry = _read_csv(result.coding_registry)
    participants = _read_csv(config.paths.synthetic_data_dir / config.generation.participant_file)
    questionnaires = _read_csv(
        config.paths.synthetic_data_dir / config.generation.questionnaire_file,
    )

    fields = field_registry[
        field_registry["value_strategy"] == "numeric_range_with_special_codes"
    ]
    special_codes = _special_codes_by_coding_name(coding_registry)
    failures = []

    assert not fields.empty

    for field in fields.to_dict("records"):
        table = participants if field["entity"] == "participant" else questionnaires
        failures.extend(
            _numeric_range_with_special_code_failures(
                field=field,
                values=table[str(field["name"])],
                special_codes=special_codes.get(str(field["coding_name"]), set()),
            ),
        )

    assert failures == []


def test_default_outputs_do_not_generate_suppression_codes(tmp_path: Path) -> None:
    config = _config_for_tmp_path(tmp_path)

    build_registries(config)
    tables = generate_tables_from_processed_registries(config)
    write_generated_tables(tables, config.paths.synthetic_data_dir, config.generation)

    participants = _read_csv(config.paths.synthetic_data_dir / config.generation.participant_file)
    questionnaires = _read_csv(
        config.paths.synthetic_data_dir / config.generation.questionnaire_file,
    )
    failures = []

    for table_name, table in [
        ("participant", participants),
        ("questionnaire", questionnaires),
    ]:
        for column in table.columns:
            values = table[column].astype(str)
            suppression_values = sorted(
                value
                for value in values.unique()
                if _contains_suppression_code(value)
            )
            if suppression_values:
                failures.append(
                    {
                        "table": table_name,
                        "column": column,
                        "values": suppression_values,
                    },
                )

    assert failures == []


def _config_for_tmp_path(tmp_path: Path):
    config = load_config("configs/default.yaml")
    return replace(
        config,
        paths=PathsConfig(
            raw_data_dir=config.paths.raw_data_dir,
            processed_data_dir=tmp_path / "processed",
            synthetic_data_dir=tmp_path / "synthetic",
            qa_dir=tmp_path / "qa",
        ),
    )


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


def _assert_core_timeline_supports_adult_age(
    participants: pd.DataFrame,
    questionnaires: pd.DataFrame,
) -> None:
    joined = participants.merge(
        questionnaires[["PID", "SUBMISSION_DATE"]],
        on="PID",
        how="inner",
    )
    assert len(joined) == len(participants) == len(questionnaires)

    registration_years = pd.to_numeric(joined["REGISTRATION_YEAR"])
    registration_months = pd.to_numeric(joined["REGISTRATION_MONTH"])
    consent_years = pd.to_numeric(joined["CONSENT_YEAR"])
    consent_months = pd.to_numeric(joined["CONSENT_MONTH"])
    birth_years = pd.to_numeric(joined["BIRTH_YEAR"])
    birth_months = pd.to_numeric(joined["BIRTH_MONTH"])
    submission_years = joined["SUBMISSION_DATE"].str.slice(0, 4).astype(int)
    submission_months = joined["SUBMISSION_DATE"].str.slice(5, 7).astype(int)

    assert registration_years.between(3095, 3100).all()
    assert birth_years.between(3000, 3075).all()
    assert registration_years.tolist() == consent_years.tolist()
    assert registration_months.tolist() == consent_months.tolist()
    assert registration_years.tolist() == submission_years.tolist()
    assert registration_months.tolist() == submission_months.tolist()

    age_months = (submission_years - birth_years) * 12 + (submission_months - birth_months)
    assert age_months.ge(18 * 12).all()


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


def _numeric_range_with_special_code_failures(
    field: dict[str, object],
    values: pd.Series,
    special_codes: set[str],
) -> list[dict[str, object]]:
    name = str(field["name"])
    minimum = _numeric_value(field["generation_min"])
    maximum = _numeric_value(field["generation_max"])
    failures = []

    if minimum is None or maximum is None or not special_codes:
        return [
            {
                "field": name,
                "problem": "missing range or special-code metadata",
            },
        ]

    for value in values:
        if _is_blank(value):
            continue

        formatted_value = _format_code(value)
        numeric_value = _numeric_value(value)
        in_range = numeric_value is not None and minimum <= numeric_value <= maximum
        if formatted_value not in special_codes and not in_range:
            failures.append(
                {
                    "field": name,
                    "value": value,
                    "range": f"{minimum}-{maximum}",
                    "special_codes": sorted(special_codes),
                },
            )

    return failures


def _special_codes_by_coding_name(coding_registry: pd.DataFrame) -> dict[str, set[str]]:
    special_rows = coding_registry[coding_registry["is_special_code"].map(_as_bool)]
    lookup: dict[str, set[str]] = {}

    for row in special_rows.to_dict("records"):
        lookup.setdefault(str(row["coding_name"]), set()).add(_format_code(row["code"]))

    return lookup


def _fields_for_entity(field_registry: pd.DataFrame, entity: str) -> pd.DataFrame:
    fields = field_registry[field_registry["entity"] == entity].copy()
    fields["_dictionary_order"] = pd.to_numeric(fields["dictionary_order"], errors="coerce")
    return fields.sort_values("_dictionary_order", kind="stable").drop(
        columns=["_dictionary_order"],
    )


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=object, keep_default_na=False).where(pd.notna, "")


def _literal_none_coding_keys(path: Path) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    workbook = pd.ExcelFile(path)

    for sheet_name in workbook.sheet_names:
        if sheet_name.upper() == "README":
            continue

        frame = pd.read_excel(
            path,
            sheet_name=sheet_name,
            dtype=object,
            keep_default_na=False,
        )
        if not {"coding_name", "code", "meaning"}.issubset(frame.columns):
            continue

        literal_none_rows = frame[frame["meaning"].astype(str).eq("None")]
        keys.update(
            _coding_key(row["coding_name"], row["code"])
            for row in literal_none_rows.to_dict("records")
        )

    return keys


def _coding_key(coding_name: object, code: object) -> tuple[str, str]:
    return str(coding_name), _format_code(code)


def _format_code(value: object) -> str:
    text = str(value)
    numeric = _numeric_value(value)
    if pd.notna(numeric) and float(numeric).is_integer():
        return str(int(numeric))
    return text


def _numeric_value(value: object) -> float | None:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return None
    return float(numeric)


def _is_blank(value: object) -> bool:
    return str(value).strip() == ""


def _contains_suppression_code(value: object) -> bool:
    text = str(value).strip()
    if text == "-999":
        return True
    if text.startswith("[") and text.endswith("]"):
        return any(option.strip() == "-999" for option in text[1:-1].split(","))
    return False


def _is_integer_text(value: str) -> bool:
    return value.startswith("-") and value[1:].isdigit() or value.isdigit()


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}
