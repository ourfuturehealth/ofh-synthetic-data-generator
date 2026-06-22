"""Validate generated participant and questionnaire tables against processed registries."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from ofh_synthetic_data.config import AppConfig
from ofh_synthetic_data.generate.show_if import evaluate_show_if

SYNTHETIC_YEAR_MINIMUM = 3000


@dataclass(frozen=True)
class ValidationIssue:
    check: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    errors: list[ValidationIssue]
    checks_run: int

    @property
    def passed(self) -> bool:
        return not self.errors


def validate_synthetic_outputs(
    config: AppConfig,
    input_dir: Path | None = None,
) -> ValidationResult:
    """Validate synthetic outputs using the processed source registries."""

    synthetic_dir = input_dir or config.paths.synthetic_data_dir
    participant_path = synthetic_dir / config.generation.participant_file
    questionnaire_path = synthetic_dir / config.generation.questionnaire_file
    manifest_path = synthetic_dir / config.generation.manifest_file
    field_registry_path = config.paths.processed_data_dir / "field_registry.csv"
    coding_registry_path = config.paths.processed_data_dir / "coding_registry.csv"
    logic_registry_path = config.paths.processed_data_dir / "logic_registry.csv"

    errors: list[ValidationIssue] = []
    checks_run = 0

    required_paths = {
        "participant output": participant_path,
        "questionnaire output": questionnaire_path,
        "manifest": manifest_path,
        "field registry": field_registry_path,
        "coding registry": coding_registry_path,
        "logic registry": logic_registry_path,
    }
    for label, path in required_paths.items():
        checks_run += 1
        if not path.exists():
            errors.append(ValidationIssue("expected_files", f"Missing {label}: {path}"))

    if any(not path.exists() for path in required_paths.values()):
        return ValidationResult(errors=errors, checks_run=checks_run)

    participants = _read_csv(participant_path)
    questionnaires = _read_csv(questionnaire_path)
    field_registry = _read_csv(field_registry_path)
    coding_registry = _read_csv(coding_registry_path)
    logic_registry = _read_csv(logic_registry_path)
    manifest = _read_manifest(manifest_path, errors)
    checks_run += 1

    participant_fields = _fields_for_entity(field_registry, "participant")
    questionnaire_fields = _fields_for_entity(field_registry, "questionnaire")
    coding_lookup = _build_coding_lookup(coding_registry)

    checks_run += _validate_columns(participants, participant_fields, "participant", errors)
    checks_run += _validate_columns(questionnaires, questionnaire_fields, "questionnaire", errors)
    checks_run += _validate_row_counts(participants, questionnaires, manifest, errors)
    checks_run += _validate_pid_links(participants, questionnaires, errors)
    checks_run += _validate_synthetic_ids(participants, participant_fields, "participant", errors)
    checks_run += _validate_synthetic_ids(
        questionnaires,
        questionnaire_fields,
        "questionnaire",
        errors,
    )
    checks_run += _validate_field_values(
        participants,
        participant_fields,
        coding_lookup,
        config.generation.questionnaire_version,
        errors,
    )
    checks_run += _validate_field_values(
        questionnaires,
        questionnaire_fields,
        coding_lookup,
        config.generation.questionnaire_version,
        errors,
    )
    checks_run += _validate_root_logic_fields(
        participants=participants,
        participant_fields=participant_fields,
        questionnaires=questionnaires,
        questionnaire_fields=questionnaire_fields,
        logic_registry=logic_registry,
        errors=errors,
    )
    checks_run += _validate_source_logic_blanks(
        participants=participants,
        questionnaires=questionnaires,
        questionnaire_fields=questionnaire_fields,
        logic_registry=logic_registry,
        manifest=manifest,
        errors=errors,
    )
    checks_run += _validate_no_source_text(
        participants=participants,
        questionnaires=questionnaires,
        field_registry=field_registry,
        logic_registry=logic_registry,
        errors=errors,
    )

    return ValidationResult(errors=errors, checks_run=checks_run)


def _validate_columns(
    table: pd.DataFrame,
    fields: pd.DataFrame,
    entity: str,
    errors: list[ValidationIssue],
) -> int:
    """Check output columns exactly match dictionary order."""
    expected = fields["name"].astype(str).tolist()
    actual = table.columns.astype(str).tolist()
    if actual == expected:
        return 1

    missing = [column for column in expected if column not in actual]
    extra = [column for column in actual if column not in expected]
    first_mismatch = _first_mismatch(actual, expected)
    message_parts = [f"{entity} columns do not match the data dictionary order"]
    if first_mismatch:
        position, actual_value, expected_value = first_mismatch
        message_parts.append(
            f"first mismatch at position {position}: "
            f"got {actual_value!r}, expected {expected_value!r}",
        )
    if missing:
        message_parts.append(f"missing={missing[:5]}")
    if extra:
        message_parts.append(f"extra={extra[:5]}")
    errors.append(ValidationIssue("column_order", "; ".join(message_parts)))
    return 1


def _validate_row_counts(
    participants: pd.DataFrame,
    questionnaires: pd.DataFrame,
    manifest: dict[str, Any],
    errors: list[ValidationIssue],
) -> int:
    """Check row counts agree across outputs and manifest metadata."""
    if len(participants) != len(questionnaires):
        errors.append(
            ValidationIssue(
                "row_counts",
                f"participant rows ({len(participants)}) != "
                f"questionnaire rows ({len(questionnaires)})",
            ),
        )

    manifest_rows = manifest.get("rows")
    if manifest_rows is not None and int(manifest_rows) != len(participants):
        errors.append(
            ValidationIssue(
                "manifest",
                f"manifest rows ({manifest_rows}) != participant rows ({len(participants)})",
            ),
        )
    return 1


def _validate_pid_links(
    participants: pd.DataFrame,
    questionnaires: pd.DataFrame,
    errors: list[ValidationIssue],
) -> int:
    """Check participant and questionnaire PID values link row by row."""
    if "PID" not in participants.columns or "PID" not in questionnaires.columns:
        errors.append(ValidationIssue("pid_links", "PID column missing from an output table"))
        return 1

    participant_pids = participants["PID"].astype(str).tolist()
    questionnaire_pids = questionnaires["PID"].astype(str).tolist()
    if participant_pids != questionnaire_pids:
        errors.append(
            ValidationIssue(
                "pid_links",
                "participant and questionnaire PID values do not match row-by-row",
            ),
        )
    return 1


def _validate_synthetic_ids(
    table: pd.DataFrame,
    fields: pd.DataFrame,
    entity: str,
    errors: list[ValidationIssue],
) -> int:
    """Check primary identifiers visibly use the synthetic prefix."""
    id_fields = fields[
        (fields["name"].isin({"ID", "PID"}))
        | (fields["primary_key_type"].astype(str).str.strip() != "")
    ]
    for field in id_fields.to_dict("records"):
        name = str(field["name"])
        if name not in table.columns:
            continue
        invalid_count = table[name].map(lambda value: not str(value).startswith("SYN")).sum()
        if invalid_count:
            errors.append(
                ValidationIssue(
                    "synthetic_ids",
                    f"{entity}.{name} has {invalid_count} value(s) without the SYN prefix",
                ),
            )
    return 1


def _validate_field_values(
    table: pd.DataFrame,
    fields: pd.DataFrame,
    coding_lookup: dict[str, dict[str, set[str]]],
    questionnaire_version: str,
    errors: list[ValidationIssue],
) -> int:
    """Validate values according to each field's registry strategy."""
    for field in fields.to_dict("records"):
        name = str(field["name"])
        if name not in table.columns:
            continue

        values = table[name]
        non_blank = values[values.map(lambda value: not _is_blank(value))]
        if str(field.get("generation_action", "")) == "blank":
            if not non_blank.empty:
                errors.append(
                    ValidationIssue(
                        "blank_fields",
                        f"{name} is marked blank but has {len(non_blank)} populated value(s)",
                    ),
                )
            continue

        value_strategy = str(field.get("value_strategy", ""))
        field_type = str(field.get("type", "")).lower()

        if value_strategy == "constant_questionnaire_version":
            invalid = non_blank[non_blank.astype(str) != questionnaire_version]
            if not invalid.empty:
                errors.append(
                    ValidationIssue(
                        "questionnaire_version",
                        f"{name} has {len(invalid)} value(s) other than "
                        f"version {questionnaire_version}",
                    ),
                )

        if value_strategy == "synthetic_string":
            invalid = non_blank[~non_blank.astype(str).str.startswith("SYNTHETIC")]
            if not invalid.empty:
                errors.append(
                    ValidationIssue(
                        "synthetic_strings",
                        f"{name} has {len(invalid)} value(s) without a SYNTHETIC prefix",
                    ),
                )

        if _as_bool(field.get("is_multi_select")):
            _validate_multi_select_values(field, non_blank, coding_lookup, errors)
            continue

        if value_strategy == "coded_single":
            _validate_coded_values(field, non_blank, coding_lookup, errors)

        if field_type in {"integer", "float"}:
            _validate_numeric_values(field, non_blank, coding_lookup, errors)

        if field_type == "date" or name.endswith("_DATE"):
            _validate_future_dates(name, non_blank, errors)

    return 1


def _validate_coded_values(
    field: dict[str, object],
    values: pd.Series,
    coding_lookup: dict[str, dict[str, set[str]]],
    errors: list[ValidationIssue],
) -> None:
    """Check single coded values appear in the codings registry."""
    name = str(field["name"])
    allowed = _allowed_codes(field, coding_lookup)
    if not allowed:
        return

    invalid = values[~values.map(lambda value: _format_code(value) in allowed)]
    if not invalid.empty:
        errors.append(
            ValidationIssue(
                "coded_values",
                f"{name} has {len(invalid)} value(s) not found in OFH codings",
            ),
        )


def _validate_multi_select_values(
    field: dict[str, object],
    values: pd.Series,
    coding_lookup: dict[str, dict[str, set[str]]],
    errors: list[ValidationIssue],
) -> None:
    """Check bracketed multi-select values contain valid coding options."""
    name = str(field["name"])
    allowed = _allowed_codes(field, coding_lookup)
    invalid_count = 0

    for value in values:
        options = _multi_select_options(value)
        if options is None or any(option not in allowed for option in options):
            invalid_count += 1

    if invalid_count:
        errors.append(
            ValidationIssue(
                "multi_select_values",
                f"{name} has {invalid_count} invalid bracketed multi-select value(s)",
            ),
        )


def _validate_numeric_values(
    field: dict[str, object],
    values: pd.Series,
    coding_lookup: dict[str, dict[str, set[str]]],
    errors: list[ValidationIssue],
) -> None:
    """Check numeric values parse, match integer type and stay in range."""
    name = str(field["name"])
    ignored_codes = _numeric_validation_ignored_codes(field, coding_lookup)
    numeric_values = values[~values.map(lambda value: _format_code(value) in ignored_codes)]
    parsed = pd.to_numeric(numeric_values, errors="coerce")

    if parsed.isna().any():
        errors.append(
            ValidationIssue(
                "types",
                f"{name} has {int(parsed.isna().sum())} non-numeric value(s)",
            ),
        )
        return

    if str(field.get("type", "")).lower() == "integer":
        non_integer_count = int((parsed % 1 != 0).sum())
        if non_integer_count:
            errors.append(
                ValidationIssue(
                    "types",
                    f"{name} has {non_integer_count} non-integer value(s)",
                ),
            )

    minimum = _float_value(field.get("generation_min"))
    maximum = _float_value(field.get("generation_max"))
    if minimum is not None and maximum is not None and not parsed.empty:
        outside = parsed[(parsed < minimum) | (parsed > maximum)]
        if not outside.empty:
            errors.append(
                ValidationIssue(
                    "numeric_ranges",
                    f"{name} has {len(outside)} value(s) outside [{minimum}, {maximum}]",
                ),
            )

    if str(field.get("numeric_range_rule", "")) == "synthetic_year":
        too_early = parsed[parsed < SYNTHETIC_YEAR_MINIMUM]
        if not too_early.empty:
            errors.append(
                ValidationIssue(
                    "synthetic_dates",
                    f"{name} has {len(too_early)} year value(s) before {SYNTHETIC_YEAR_MINIMUM}",
                ),
            )


def _validate_future_dates(
    name: str,
    values: pd.Series,
    errors: list[ValidationIssue],
) -> None:
    """Check generated date values are parseable and future-dated."""
    invalid_count = 0
    too_early_count = 0

    for value in values:
        try:
            parsed = date.fromisoformat(str(value).strip())
        except ValueError:
            invalid_count += 1
            continue

        if parsed.year < SYNTHETIC_YEAR_MINIMUM:
            too_early_count += 1

    if invalid_count:
        errors.append(
            ValidationIssue("types", f"{name} has {invalid_count} invalid date value(s)"),
        )
        return

    if too_early_count:
        errors.append(
            ValidationIssue(
                "synthetic_dates",
                f"{name} has {too_early_count} date value(s) before {SYNTHETIC_YEAR_MINIMUM}",
            ),
        )


def _validate_root_logic_fields(
    participants: pd.DataFrame,
    participant_fields: pd.DataFrame,
    questionnaires: pd.DataFrame,
    questionnaire_fields: pd.DataFrame,
    logic_registry: pd.DataFrame,
    errors: list[ValidationIssue],
) -> int:
    """Check root logic fields are populated when they should be generated."""
    root_field_names = _root_logic_field_names(logic_registry)
    if not root_field_names:
        return 1

    for entity, table, fields in [
        ("participant", participants, participant_fields),
        ("questionnaire", questionnaires, questionnaire_fields),
    ]:
        root_fields = fields[fields["name"].astype(str).isin(root_field_names)]
        for field in root_fields.to_dict("records"):
            name = str(field["name"])
            if name not in table.columns or not _should_generate(field):
                continue

            blank_count = int(table[name].map(_is_blank).sum())
            if blank_count:
                errors.append(
                    ValidationIssue(
                        "root_logic",
                        f"{entity}.{name} is a root logic field but has "
                        f"{blank_count} blank value(s)",
                    ),
                )

    return 1


def _validate_source_logic_blanks(
    participants: pd.DataFrame,
    questionnaires: pd.DataFrame,
    questionnaire_fields: pd.DataFrame,
    logic_registry: pd.DataFrame,
    manifest: dict[str, Any],
    errors: list[ValidationIssue],
) -> int:
    """Replay source show_if rules and check skipped fields are blank."""
    logic_rules, logic_order = _build_logic_rules(logic_registry)
    if not logic_rules:
        return 1

    field_by_name = {
        str(field["name"]): field
        for field in questionnaire_fields.to_dict("records")
    }
    skipped_count = 0

    for row_index in range(min(len(participants), len(questionnaires))):
        participant = participants.iloc[row_index].to_dict()
        questionnaire = questionnaires.iloc[row_index].to_dict()
        context = {**participant, **dict.fromkeys(questionnaires.columns.astype(str), "")}

        for name, value in questionnaire.items():
            if name not in logic_rules:
                context[str(name)] = value

        for name in logic_order:
            field = field_by_name.get(name)
            if field is None or name not in questionnaires.columns:
                continue

            value = questionnaire[name]
            if not _should_generate(field):
                context[name] = ""
                continue

            shown = any(evaluate_show_if(expression, context) for expression in logic_rules[name])
            if not shown:
                skipped_count += 1
                if not _is_blank(value):
                    errors.append(
                        ValidationIssue(
                            "source_logic",
                            f"row {row_index + 1} field {name} should be blank by show_if logic",
                        ),
                    )
                context[name] = ""
            else:
                context[name] = value

    manifest_logic = manifest.get("questionnaire_logic", {})
    manifest_skipped = manifest_logic.get("skipped_values")
    if manifest_skipped is not None and int(manifest_skipped) != skipped_count:
        errors.append(
            ValidationIssue(
                "manifest",
                f"manifest skipped_values ({manifest_skipped}) != "
                f"validated skipped fields ({skipped_count})",
            ),
        )

    return 1


def _validate_no_source_text(
    participants: pd.DataFrame,
    questionnaires: pd.DataFrame,
    field_registry: pd.DataFrame,
    logic_registry: pd.DataFrame,
    errors: list[ValidationIssue],
) -> int:
    """Check synthetic outputs do not copy source question text or labels."""
    source_text = _source_text_values(field_registry, logic_registry)
    if not source_text:
        return 1

    for entity, table in {"participant": participants, "questionnaire": questionnaires}.items():
        for column in table.columns:
            matches = table[column].map(lambda value: _normalise_text(value) in source_text).sum()
            if matches:
                errors.append(
                    ValidationIssue(
                        "source_text",
                        f"{entity}.{column} contains {matches} value(s) copied from source text",
                    ),
                )
    return 1


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=object, keep_default_na=False).where(pd.notna, "")


def _read_manifest(path: Path, errors: list[ValidationIssue]) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(ValidationIssue("manifest", f"Manifest is not valid JSON: {exc}"))
        return {}


def _fields_for_entity(field_registry: pd.DataFrame, entity: str) -> pd.DataFrame:
    fields = field_registry[field_registry["entity"] == entity].copy()
    if "dictionary_order" not in fields.columns:
        return fields.reset_index(drop=True)

    fields["_dictionary_order"] = pd.to_numeric(fields["dictionary_order"], errors="coerce")
    if fields["_dictionary_order"].notna().any():
        fields = fields.sort_values("_dictionary_order", kind="stable")
    return fields.drop(columns=["_dictionary_order"]).reset_index(drop=True)


def _root_logic_field_names(logic_registry: pd.DataFrame) -> set[str]:
    """Return logic fields with no show_if condition."""
    if logic_registry.empty or "field_name" not in logic_registry.columns:
        return set()

    if "show_if" in logic_registry.columns:
        show_if = logic_registry["show_if"]
    else:
        show_if = pd.Series([""] * len(logic_registry))

    root_rows = logic_registry[show_if.fillna("").astype(str).str.strip() == ""]
    return {
        str(field_name).strip()
        for field_name in root_rows["field_name"]
        if str(field_name).strip()
    }


def _build_logic_rules(logic_registry: pd.DataFrame) -> tuple[dict[str, list[str]], list[str]]:
    """Group validation show_if expressions by field."""
    rules: dict[str, list[str]] = {}
    order: list[str] = []

    for row in logic_registry.to_dict("records"):
        field_name = str(row.get("field_name", "")).strip()
        if not field_name:
            continue
        if field_name not in rules:
            rules[field_name] = []
            order.append(field_name)
        rules[field_name].append(str(row.get("show_if", "") or ""))

    return rules, order


def _build_coding_lookup(coding_registry: pd.DataFrame) -> dict[str, dict[str, set[str]]]:
    """Build sets of all and special codes by coding name."""
    if coding_registry.empty:
        return {}

    lookup: dict[str, dict[str, set[str]]] = {}
    for coding_name, rows in coding_registry.groupby("coding_name"):
        regular: set[str] = set()
        special: set[str] = set()
        for row in rows.to_dict("records"):
            code = _format_code(row.get("code", ""))
            if _as_bool(row.get("is_special_code")):
                special.add(code)
            else:
                regular.add(code)
        lookup[str(coding_name)] = {
            "all": regular | special,
            "special": special,
        }
    return lookup


def _allowed_codes(
    field: dict[str, object],
    coding_lookup: dict[str, dict[str, set[str]]],
) -> set[str]:
    return coding_lookup.get(str(field.get("coding_name", "")), {}).get("all", set())


def _special_codes(
    field: dict[str, object],
    coding_lookup: dict[str, dict[str, set[str]]],
) -> set[str]:
    return coding_lookup.get(str(field.get("coding_name", "")), {}).get("special", set())


def _numeric_validation_ignored_codes(
    field: dict[str, object],
    coding_lookup: dict[str, dict[str, set[str]]],
) -> set[str]:
    """Return coded values that should not be range-checked as numbers."""
    if str(field.get("value_strategy", "")) == "numeric_range_with_coded_choices":
        return _allowed_codes(field, coding_lookup)
    return _special_codes(field, coding_lookup)


def _multi_select_options(value: object) -> list[str] | None:
    text = str(value).strip()
    if not re.fullmatch(r"\[[^\[\]]+\]", text):
        return None
    return [_format_code(option.strip()) for option in text[1:-1].split(",") if option.strip()]


def _should_generate(field: dict[str, object]) -> bool:
    return str(field.get("generation_action", "")) == "generate" and str(
        field.get("value_strategy", ""),
    ) != "blank"


def _source_text_values(field_registry: pd.DataFrame, logic_registry: pd.DataFrame) -> set[str]:
    values: set[str] = set()
    for frame, columns in [
        (field_registry, ["title", "description"]),
        (logic_registry, ["question_text"]),
    ]:
        for column in columns:
            if column not in frame.columns:
                continue
            for value in frame[column]:
                text = _normalise_text(value)
                if len(text) >= 12:
                    values.add(text)
    return values


def _normalise_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value).strip())


def _first_mismatch(
    actual: list[str],
    expected: list[str],
) -> tuple[int, str | None, str | None] | None:
    for index in range(max(len(actual), len(expected))):
        actual_value = actual[index] if index < len(actual) else None
        expected_value = expected[index] if index < len(expected) else None
        if actual_value != expected_value:
            return index, actual_value, expected_value
    return None


def _is_blank(value: object) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    return text == "" or text.lower() == "nan"


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}


def _format_code(value: object) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.notna(numeric) and float(numeric).is_integer():
        return str(int(numeric))
    return str(value).strip()


def _float_value(value: object) -> float | None:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return None
    return float(numeric)
