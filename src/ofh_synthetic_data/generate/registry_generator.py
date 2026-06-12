"""Registry-driven synthetic table generation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from random import Random
from typing import Any

import pandas as pd

from ofh_synthetic_data.config import AppConfig, GenerationConfig
from ofh_synthetic_data.export.writers import write_metadata, write_records_csv
from ofh_synthetic_data.generate.show_if import evaluate_show_if


@dataclass(frozen=True)
class GeneratedTables:
    participants: list[dict[str, object]]
    questionnaires: list[dict[str, object]]
    participant_columns: list[str]
    questionnaire_columns: list[str]
    manifest: dict[str, Any]
    skipped_by_logic_count: int


@dataclass(frozen=True)
class GeneratedTablePaths:
    participant: Path
    questionnaire: Path
    manifest: Path


def generate_tables_from_processed_registries(config: AppConfig) -> GeneratedTables:
    field_registry = _read_registry(config.paths.processed_data_dir / "field_registry.csv")
    coding_registry = _read_registry(config.paths.processed_data_dir / "coding_registry.csv")
    logic_registry = _read_registry(config.paths.processed_data_dir / "logic_registry.csv")
    source_manifest = _read_json(config.paths.processed_data_dir / "source_manifest.json")
    return generate_tables(
        field_registry=field_registry,
        coding_registry=coding_registry,
        logic_registry=logic_registry,
        generation_config=config.generation,
        config_snapshot=config.to_dict(),
        source_manifest=source_manifest,
    )


def generate_tables(
    field_registry: pd.DataFrame,
    coding_registry: pd.DataFrame,
    generation_config: GenerationConfig,
    logic_registry: pd.DataFrame | None = None,
    config_snapshot: dict[str, Any] | None = None,
    source_manifest: dict[str, Any] | None = None,
) -> GeneratedTables:
    rng = Random(generation_config.seed)
    coding_lookup = _build_coding_lookup(coding_registry)
    logic_rules, logic_order = _build_logic_rules(logic_registry)

    participant_fields = _fields_for_entity(field_registry, "participant")
    questionnaire_fields = _fields_for_entity(field_registry, "questionnaire")
    participant_columns = participant_fields["name"].astype(str).tolist()
    questionnaire_columns = questionnaire_fields["name"].astype(str).tolist()

    participants: list[dict[str, object]] = []
    questionnaires: list[dict[str, object]] = []
    skipped_by_logic_count = 0

    for row_index in range(generation_config.rows):
        pid = _participant_id(row_index)
        participant = _generate_record(
            fields=participant_fields,
            coding_lookup=coding_lookup,
            rng=rng,
            row_index=row_index,
            pid=pid,
            generation_config=generation_config,
        )
        questionnaire, skipped_for_row = _generate_questionnaire_record(
            fields=questionnaire_fields,
            logic_rules=logic_rules,
            logic_order=logic_order,
            coding_lookup=coding_lookup,
            rng=rng,
            row_index=row_index,
            pid=pid,
            generation_config=generation_config,
            participant=participant,
        )
        skipped_by_logic_count += skipped_for_row
        participants.append(participant)
        questionnaires.append(questionnaire)

    return GeneratedTables(
        participants=participants,
        questionnaires=questionnaires,
        participant_columns=participant_columns,
        questionnaire_columns=questionnaire_columns,
        manifest={
            "status": "beta",
            "manual_validation_status": "ongoing",
            "rows": generation_config.rows,
            "seed": generation_config.seed,
            "questionnaire_version": generation_config.questionnaire_version,
            "outputs": {
                "participant": generation_config.participant_file,
                "questionnaire": generation_config.questionnaire_file,
            },
            "config": config_snapshot or {"generation": asdict(generation_config)},
            "source_manifest": source_manifest or {},
            "synthetic_markers": {
                "id_prefix": "SYN",
                "future_year_minimum": 3000,
            },
            "questionnaire_logic": {
                "applied": bool(logic_rules),
                "skipped_values": skipped_by_logic_count,
            },
            "column_order": {
                "source": "data_dictionary",
                "participant_columns": len(participant_columns),
                "questionnaire_columns": len(questionnaire_columns),
            },
            "phase": "7-beta-release-candidate",
        },
        skipped_by_logic_count=skipped_by_logic_count,
    )


def write_generated_tables(
    tables: GeneratedTables,
    output_dir: Path,
    config: GenerationConfig,
) -> GeneratedTablePaths:
    participant_path = output_dir / config.participant_file
    questionnaire_path = output_dir / config.questionnaire_file
    manifest_path = output_dir / config.manifest_file

    write_records_csv(tables.participants, participant_path, tables.participant_columns)
    write_records_csv(tables.questionnaires, questionnaire_path, tables.questionnaire_columns)
    write_metadata(
        {
            **tables.manifest,
            "output_files": {
                "participant": str(participant_path),
                "questionnaire": str(questionnaire_path),
            },
        },
        manifest_path,
    )

    return GeneratedTablePaths(
        participant=participant_path,
        questionnaire=questionnaire_path,
        manifest=manifest_path,
    )


def _generate_record(
    fields: pd.DataFrame,
    coding_lookup: dict[str, dict[str, list[str]]],
    rng: Random,
    row_index: int,
    pid: str,
    generation_config: GenerationConfig,
) -> dict[str, object]:
    record: dict[str, object] = {}

    for field in fields.to_dict("records"):
        name = str(field["name"])
        record[name] = _generate_value(
            field=field,
            coding_lookup=coding_lookup,
            rng=rng,
            row_index=row_index,
            pid=pid,
            generation_config=generation_config,
        )

    return record


def _generate_questionnaire_record(
    fields: pd.DataFrame,
    logic_rules: dict[str, list[str]],
    logic_order: list[str],
    coding_lookup: dict[str, dict[str, list[str]]],
    rng: Random,
    row_index: int,
    pid: str,
    generation_config: GenerationConfig,
    participant: dict[str, object],
) -> tuple[dict[str, object], int]:
    field_records = fields.to_dict("records")
    fields_by_name = {str(field["name"]): field for field in field_records}
    record = {str(field["name"]): "" for field in field_records}
    context = {**participant, **record}
    skipped_by_logic_count = 0

    for field in field_records:
        name = str(field["name"])
        if name in logic_rules:
            continue
        if _should_generate(field):
            record[name] = _generate_value(
                field=field,
                coding_lookup=coding_lookup,
                rng=rng,
                row_index=row_index,
                pid=pid,
                generation_config=generation_config,
            )
            context[name] = record[name]

    for name in logic_order:
        field = fields_by_name.get(name)
        if field is None:
            continue

        if not _should_generate(field):
            record[name] = ""
            context[name] = ""
            continue

        if _is_shown(logic_rules.get(name, [""]), context):
            record[name] = _generate_value(
                field=field,
                coding_lookup=coding_lookup,
                rng=rng,
                row_index=row_index,
                pid=pid,
                generation_config=generation_config,
            )
        else:
            record[name] = ""
            skipped_by_logic_count += 1

        context[name] = record[name]

    return record, skipped_by_logic_count


def _generate_value(
    field: dict[str, object],
    coding_lookup: dict[str, dict[str, list[str]]],
    rng: Random,
    row_index: int,
    pid: str,
    generation_config: GenerationConfig,
) -> object:
    strategy = str(field.get("value_strategy", ""))
    name = str(field["name"])

    if strategy == "blank":
        return ""
    if strategy == "synthetic_identifier":
        return _synthetic_identifier(name, row_index, pid)
    if strategy == "constant_questionnaire_version":
        return generation_config.questionnaire_version
    if strategy == "synthetic_future_date":
        return _future_date(rng)
    if strategy == "coded_multi_select":
        return _coded_multi_select(field, coding_lookup, rng)
    if strategy == "coded_single":
        return _coded_single(field, coding_lookup, rng)
    if strategy == "numeric_range_with_special_codes":
        if _use_special_code(field, rng):
            return _special_code(field, coding_lookup, rng)
        return _numeric_range_value(field, rng)
    if strategy == "numeric_range":
        return _numeric_range_value(field, rng)
    if strategy == "synthetic_string":
        return f"SYNTHETIC_{name}_{row_index + 1:08d}"

    return f"SYNTHETIC_{row_index + 1:08d}"


def _should_generate(field: dict[str, object]) -> bool:
    return str(field.get("generation_action", "")) == "generate" and str(
        field.get("value_strategy", ""),
    ) != "blank"


def _is_shown(expressions: list[str], context: dict[str, object]) -> bool:
    return any(evaluate_show_if(expression, context) for expression in expressions)


def _fields_for_entity(field_registry: pd.DataFrame, entity: str) -> pd.DataFrame:
    fields = field_registry[field_registry["entity"] == entity].copy()
    if "dictionary_order" not in fields.columns:
        return fields.reset_index(drop=True)

    fields["_dictionary_order"] = pd.to_numeric(
        fields["dictionary_order"],
        errors="coerce",
    )
    if fields["_dictionary_order"].notna().any():
        fields = fields.sort_values("_dictionary_order", kind="stable")
    return fields.drop(columns=["_dictionary_order"]).reset_index(drop=True)


def _build_logic_rules(
    logic_registry: pd.DataFrame | None,
) -> tuple[dict[str, list[str]], list[str]]:
    if logic_registry is None or logic_registry.empty:
        return {}, []

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


def _build_coding_lookup(coding_registry: pd.DataFrame) -> dict[str, dict[str, list[str]]]:
    lookup: dict[str, dict[str, list[str]]] = {}

    for coding_name, rows in coding_registry.groupby("coding_name"):
        codes = [_format_code(value) for value in rows["code"].tolist()]
        special_flags = rows["is_special_code"].map(_as_bool).tolist()
        lookup[str(coding_name)] = {
            "regular": [
                code
                for code, special in zip(codes, special_flags, strict=True)
                if not special
            ],
            "special": [
                code
                for code, special in zip(codes, special_flags, strict=True)
                if special
            ],
        }

    return lookup


def _coded_single(
    field: dict[str, object],
    coding_lookup: dict[str, dict[str, list[str]]],
    rng: Random,
) -> str:
    if _use_special_code(field, rng):
        return _special_code(field, coding_lookup, rng)

    codes = _codes(field, coding_lookup, "regular")
    if not codes:
        codes = _codes(field, coding_lookup, "special")
    return rng.choice(codes) if codes else ""


def _coded_multi_select(
    field: dict[str, object],
    coding_lookup: dict[str, dict[str, list[str]]],
    rng: Random,
) -> str:
    if _use_special_code(field, rng):
        return f"[{_special_code(field, coding_lookup, rng)}]"

    regular_codes = _codes(field, coding_lookup, "regular")
    selected = [code for code in regular_codes if rng.random() < 0.5]
    if not selected and regular_codes:
        selected = [rng.choice(regular_codes)]
    return f"[{','.join(selected)}]"


def _use_special_code(field: dict[str, object], rng: Random) -> bool:
    if str(field.get("special_code_policy", "")) != "include":
        return False
    probability = _float_value(field.get("special_code_probability"), default=0.0)
    return rng.random() < probability


def _special_code(
    field: dict[str, object],
    coding_lookup: dict[str, dict[str, list[str]]],
    rng: Random,
) -> str:
    codes = _codes(field, coding_lookup, "special")
    return rng.choice(codes) if codes else ""


def _codes(
    field: dict[str, object],
    coding_lookup: dict[str, dict[str, list[str]]],
    code_type: str,
) -> list[str]:
    coding_name = str(field.get("coding_name", ""))
    return coding_lookup.get(coding_name, {}).get(code_type, [])


def _numeric_range_value(field: dict[str, object], rng: Random) -> int | float | str:
    minimum = _float_value(field.get("generation_min"))
    maximum = _float_value(field.get("generation_max"))
    if minimum is None or maximum is None:
        return ""

    if str(field.get("type", "")).lower() == "integer":
        return rng.randint(int(minimum), int(maximum))
    return round(rng.uniform(minimum, maximum), 2)


def _synthetic_identifier(name: str, row_index: int, pid: str) -> str:
    if name == "PID":
        return pid
    if name == "ID":
        return f"SYN-ID-{row_index + 1:012d}"
    return f"SYN-{name}-{row_index + 1:012d}"


def _participant_id(row_index: int) -> str:
    return f"SYN-{row_index + 1:012d}"


def _future_date(rng: Random) -> str:
    return date(
        year=rng.randint(3000, 3026),
        month=rng.randint(1, 12),
        day=rng.randint(1, 28),
    ).isoformat()


def _read_registry(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=object).where(pd.notna, "")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _format_code(value: object) -> str:
    text = str(value)
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.notna(numeric) and float(numeric).is_integer():
        return str(int(numeric))
    return text


def _float_value(value: object, default: float | None = None) -> float | None:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return default
    return float(numeric)


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}
