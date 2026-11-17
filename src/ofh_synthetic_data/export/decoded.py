"""Decoded QA exports for generated synthetic datasets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ofh_synthetic_data.config import AppConfig
from ofh_synthetic_data.export.writers import write_metadata, write_records_csv


@dataclass(frozen=True)
class DecodedOutputPaths:
    participant: Path
    questionnaire: Path
    manifest: Path


def write_decoded_outputs(
    config: AppConfig,
    input_dir: Path | None = None,
    output_dir: Path | None = None,
) -> DecodedOutputPaths:
    """Write manual-QA copies of synthetic outputs with coded values decoded."""

    synthetic_dir = input_dir or config.paths.synthetic_data_dir
    qa_dir = output_dir or config.paths.qa_dir
    participant_input = synthetic_dir / config.generation.participant_file
    questionnaire_input = synthetic_dir / config.generation.questionnaire_file
    field_registry_path = config.paths.processed_data_dir / "field_registry.csv"
    coding_registry_path = config.paths.processed_data_dir / "coding_registry.csv"

    participants = _read_csv(participant_input)
    questionnaires = _read_csv(questionnaire_input)
    field_registry = _read_csv(field_registry_path)
    coding_registry = _read_csv(coding_registry_path)
    coding_lookup = _build_coding_lookup(coding_registry)

    decoded_participants, participant_summary = decode_table(
        participants,
        _fields_for_entity(field_registry, "participant"),
        coding_lookup,
    )
    decoded_questionnaires, questionnaire_summary = decode_table(
        questionnaires,
        _fields_for_entity(field_registry, "questionnaire"),
        coding_lookup,
    )

    participant_output = qa_dir / "participant_decoded.csv"
    questionnaire_output = qa_dir / "questionnaire_decoded.csv"
    manifest_output = qa_dir / "decoded_manifest.json"

    write_records_csv(
        decoded_participants.to_dict("records"),
        participant_output,
        decoded_participants.columns.astype(str).tolist(),
    )
    write_records_csv(
        decoded_questionnaires.to_dict("records"),
        questionnaire_output,
        decoded_questionnaires.columns.astype(str).tolist(),
    )
    write_metadata(
        {
            "status": "manual_qa",
            "description": (
                "QA copies of generated synthetic outputs with OFH coded values replaced "
                "by coding meanings where possible."
            ),
            "input_files": {
                "participant": str(participant_input),
                "questionnaire": str(questionnaire_input),
                "field_registry": str(field_registry_path),
                "coding_registry": str(coding_registry_path),
            },
            "output_files": {
                "participant": str(participant_output),
                "questionnaire": str(questionnaire_output),
            },
            "decode_policy": {
                "coded_values": "replace code with meaning when a coding is available",
                "multi_select_values": (
                    "replace bracketed code lists with semicolon-separated meanings"
                ),
                "blank_coding_meanings": (
                    "replace coded values with an explicit missing-meaning label"
                ),
                "uncoded_or_unmatched_values": "preserve original value",
                "blank_values": "preserve blank value",
            },
            "decoded_columns": {
                "participant": participant_summary.decoded_columns,
                "questionnaire": questionnaire_summary.decoded_columns,
            },
            "decoded_values": {
                "participant": participant_summary.decoded_values,
                "questionnaire": questionnaire_summary.decoded_values,
            },
        },
        manifest_output,
    )

    return DecodedOutputPaths(
        participant=participant_output,
        questionnaire=questionnaire_output,
        manifest=manifest_output,
    )


@dataclass(frozen=True)
class DecodeSummary:
    decoded_columns: int
    decoded_values: int


def decode_table(
    table: pd.DataFrame,
    fields: pd.DataFrame,
    coding_lookup: dict[str, dict[str, str]],
) -> tuple[pd.DataFrame, DecodeSummary]:
    """Return a copy of a table with coded values replaced by coding meanings."""

    decoded = table.copy()
    decoded_columns = 0
    decoded_values = 0

    for field in fields.to_dict("records"):
        name = str(field.get("name", ""))
        coding_name = str(field.get("coding_name", "")).strip()
        if name not in decoded.columns or coding_name not in coding_lookup:
            continue

        value_lookup = coding_lookup[coding_name]
        original = decoded[name].copy()
        if _as_bool(field.get("is_multi_select")):
            decoded[name] = decoded[name].map(
                lambda value, lookup=value_lookup: _decode_multi_select_value(value, lookup),
            )
        else:
            decoded[name] = decoded[name].map(
                lambda value, lookup=value_lookup: _decode_single_value(value, lookup),
            )

        changed = decoded[name] != original
        changed_count = int(changed.sum())
        if changed_count:
            decoded_columns += 1
            decoded_values += changed_count

    return decoded, DecodeSummary(decoded_columns=decoded_columns, decoded_values=decoded_values)


def _decode_single_value(value: object, value_lookup: dict[str, str]) -> object:
    """Replace one coded value with its meaning when available."""
    if _is_blank(value):
        return ""
    return value_lookup.get(_format_code(value), value)


def _decode_multi_select_value(value: object, value_lookup: dict[str, str]) -> object:
    """Decode a bracketed list of coded values into readable meanings."""
    if _is_blank(value):
        return ""

    text = str(value).strip()
    if not (text.startswith("[") and text.endswith("]")):
        return _decode_single_value(value, value_lookup)

    codes = [code.strip() for code in text[1:-1].split(",") if code.strip()]
    if not codes:
        return value

    return "; ".join(value_lookup.get(_format_code(code), code) for code in codes)


def _build_coding_lookup(coding_registry: pd.DataFrame) -> dict[str, dict[str, str]]:
    """Build code-to-meaning maps for each coding name."""
    lookup: dict[str, dict[str, str]] = {}
    if coding_registry.empty:
        return lookup

    for row in coding_registry.to_dict("records"):
        coding_name = str(row.get("coding_name", "")).strip()
        if not coding_name:
            continue
        code = _format_code(row.get("code", ""))
        meaning = str(row.get("meaning", "")).strip()
        lookup.setdefault(coding_name, {})[code] = meaning or _missing_meaning_label(code)

    return lookup


def _fields_for_entity(field_registry: pd.DataFrame, entity: str) -> pd.DataFrame:
    fields = field_registry[field_registry["entity"] == entity].copy()
    if "dictionary_order" not in fields.columns:
        return fields.reset_index(drop=True)

    fields["_dictionary_order"] = pd.to_numeric(fields["dictionary_order"], errors="coerce")
    if fields["_dictionary_order"].notna().any():
        fields = fields.sort_values("_dictionary_order", kind="stable")
    return fields.drop(columns=["_dictionary_order"]).reset_index(drop=True)


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=object, keep_default_na=False).where(pd.notna, "")


def _format_code(value: object) -> str:
    text = str(value)
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.notna(numeric) and float(numeric).is_integer():
        return str(int(numeric))
    return text


def _missing_meaning_label(code: str) -> str:
    return f"Code {code} (meaning unavailable)"


def _is_blank(value: object) -> bool:
    return str(value).strip() == ""


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}
