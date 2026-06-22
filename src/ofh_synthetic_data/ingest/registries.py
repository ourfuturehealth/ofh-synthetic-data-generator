"""Build source-driven registries from OFH documentation workbooks."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ofh_synthetic_data.config import AppConfig
from ofh_synthetic_data.synthetic_ranges import (
    BIRTH_YEAR_MAX,
    BIRTH_YEAR_MIN,
    CORE_TIMELINE_YEAR_MAX,
    CORE_TIMELINE_YEAR_MIN,
    SYNTHETIC_YEAR_MAX,
    SYNTHETIC_YEAR_MIN,
)

FIELD_COLUMNS = [
    "source_sheet",
    "dictionary_order",
    "entity",
    "name",
    "type",
    "primary_key_type",
    "coding_name",
    "is_sparse_coding",
    "is_multi_select",
    "referenced_entity_field",
    "relationship",
    "folder_path",
    "title",
    "units",
    "description",
]

CODING_COLUMNS = [
    "source_sheet",
    "coding_name",
    "code",
    "meaning",
    "display_order",
    "parent_code",
]

LOGIC_COLUMNS = [
    "source_sheet",
    "index",
    "section",
    "question_text",
    "source",
    "template_type",
    "field_name",
    "question_type",
    "show_if",
    "notes",
]

REQUIRED_METADATA_FIELDS = {
    "participant": {"PID"},
    "questionnaire": {"ID", "PID", "QUESTIONNAIRE_VERSION", "SUBMISSION_DATE"},
}
DEFAULT_SPECIAL_CODE_PROBABILITY = 0.1


@dataclass(frozen=True)
class RegistryBuildResult:
    field_registry: Path
    coding_registry: Path
    logic_registry: Path
    entity_registry: Path
    coverage_summary: Path
    source_manifest: Path
    counts: dict[str, int]


def build_registries(config: AppConfig) -> RegistryBuildResult:
    """Build processed registry CSVs from the configured raw source artefacts."""

    processed_dir = config.paths.processed_data_dir
    processed_dir.mkdir(parents=True, exist_ok=True)

    data_dictionary_path = config.paths.raw_data_dir / config.source_files.data_dictionary
    codings_path = config.paths.raw_data_dir / config.source_files.codings
    logic_path = config.paths.raw_data_dir / config.source_files.questionnaire_logic

    field_registry = load_field_registry(data_dictionary_path, config.registry.target_entities)
    logic_registry = load_logic_registry(logic_path, field_registry)
    field_registry = add_logic_coverage(field_registry, logic_registry)

    used_coding_names = _non_empty_values(field_registry["coding_name"])
    coding_registry = load_coding_registry(codings_path, used_coding_names)
    field_registry = add_coding_coverage(field_registry, coding_registry)
    field_registry = add_generation_metadata(field_registry, coding_registry)

    entity_registry = build_entity_registry(field_registry)
    coverage_summary = build_coverage_summary(
        field_registry=field_registry,
        coding_registry=coding_registry,
        logic_registry=logic_registry,
        entity_registry=entity_registry,
        target_entities=config.registry.target_entities,
    )

    field_path = processed_dir / "field_registry.csv"
    coding_path = processed_dir / "coding_registry.csv"
    logic_path_out = processed_dir / "logic_registry.csv"
    entity_path = processed_dir / "entity_registry.csv"
    coverage_path = processed_dir / "coverage_summary.md"
    source_manifest_path = processed_dir / "source_manifest.json"

    _write_registry(field_registry, field_path)
    _write_registry(coding_registry, coding_path)
    _write_registry(logic_registry, logic_path_out)
    _write_registry(entity_registry, entity_path)
    coverage_path.write_text(coverage_summary, encoding="utf-8")
    write_source_manifest(config, source_manifest_path)

    return RegistryBuildResult(
        field_registry=field_path,
        coding_registry=coding_path,
        logic_registry=logic_path_out,
        entity_registry=entity_path,
        coverage_summary=coverage_path,
        source_manifest=source_manifest_path,
        counts={
            "fields": len(field_registry),
            "codings": len(coding_registry),
            "logic_rows": len(logic_registry),
            "entities": len(entity_registry),
        },
    )


def write_source_manifest(config: AppConfig, path: Path) -> None:
    """Write a manifest that fingerprints local raw files without committing them."""

    source_files = {
        "questionnaire_logic": config.source_files.questionnaire_logic,
        "data_dictionary": config.source_files.data_dictionary,
        "codings": config.source_files.codings,
    }
    manifest = {
        "raw_data_dir": str(config.paths.raw_data_dir),
        "processed_data_dir": str(config.paths.processed_data_dir),
        "target_entities": list(config.registry.target_entities),
        "files": [
            _source_file_entry(role, config.paths.raw_data_dir / filename)
            for role, filename in source_files.items()
        ],
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def load_field_registry(path: Path, target_entities: Iterable[str]) -> pd.DataFrame:
    """Load in-scope data dictionary fields and preserve dictionary order."""
    target_entity_set = set(target_entities)
    frames: list[pd.DataFrame] = []
    dictionary_order_start = 0

    workbook = pd.ExcelFile(path)
    for sheet_name in workbook.sheet_names:
        if sheet_name.upper() == "README":
            continue

        frame = _read_sheet(path, sheet_name)
        if "entity" not in frame.columns or "name" not in frame.columns:
            continue

        for column in FIELD_COLUMNS:
            if column not in frame.columns:
                frame[column] = ""

        frame["source_sheet"] = sheet_name
        frame["dictionary_order"] = range(
            dictionary_order_start,
            dictionary_order_start + len(frame),
        )
        dictionary_order_start += len(frame)
        frame = frame[FIELD_COLUMNS]
        frame = frame[frame["entity"].isin(target_entity_set)]
        frame = frame[frame["name"].astype(str).str.strip() != ""]
        frames.append(frame)

    if not frames:
        return _empty_field_registry()

    registry = pd.concat(frames, ignore_index=True)
    registry["is_sparse_coding"] = registry["is_sparse_coding"].map(_as_bool)
    registry["is_multi_select"] = registry["is_multi_select"].map(_as_bool)
    registry["in_beta_scope"] = True
    return registry.sort_values("dictionary_order", kind="stable").reset_index(drop=True)


def load_logic_registry(path: Path, field_registry: pd.DataFrame) -> pd.DataFrame:
    """Load questionnaire logic rows and flag matches to dictionary fields."""
    frames: list[pd.DataFrame] = []

    workbook = pd.ExcelFile(path)
    for sheet_name in workbook.sheet_names:
        if sheet_name == "information":
            continue

        frame = _read_sheet(path, sheet_name)
        if "field_name" not in frame.columns:
            continue

        frame = _normalise_logic_columns(frame)
        frame = _normalise_known_logic_field_names(frame)
        frame["source_sheet"] = sheet_name
        frame = frame[LOGIC_COLUMNS]
        frame = frame[frame["field_name"].astype(str).str.strip() != ""]
        frames.append(frame)

    if frames:
        registry = pd.concat(frames, ignore_index=True)
    else:
        registry = pd.DataFrame(columns=LOGIC_COLUMNS)

    field_entities = (
        field_registry.groupby("name")["entity"]
        .apply(lambda values: ";".join(sorted(set(map(str, values)))))
        .to_dict()
    )
    registry["dictionary_entities"] = registry["field_name"].map(field_entities).fillna("")
    registry["dictionary_match"] = registry["dictionary_entities"] != ""
    return registry.reset_index(drop=True)


def load_coding_registry(path: Path, used_coding_names: set[str]) -> pd.DataFrame:
    """Load codings used by in-scope fields."""
    frames: list[pd.DataFrame] = []

    workbook = pd.ExcelFile(path)
    for sheet_name in workbook.sheet_names:
        if sheet_name.upper() == "README":
            continue

        frame = _read_sheet(path, sheet_name)
        if "coding_name" not in frame.columns:
            continue

        for column in CODING_COLUMNS:
            if column not in frame.columns:
                frame[column] = ""

        frame["source_sheet"] = sheet_name
        frame = frame[CODING_COLUMNS]
        frame = frame[frame["coding_name"].isin(used_coding_names)]
        frames.append(frame)

    if frames:
        registry = pd.concat(frames, ignore_index=True)
    else:
        registry = pd.DataFrame(columns=CODING_COLUMNS)

    registry["is_special_code"] = registry["code"].map(_is_special_code)
    return registry.sort_values(["coding_name", "display_order", "code"]).reset_index(drop=True)


def add_logic_coverage(field_registry: pd.DataFrame, logic_registry: pd.DataFrame) -> pd.DataFrame:
    """Attach questionnaire logic coverage metadata to dictionary fields."""
    if logic_registry.empty:
        field_registry["in_questionnaire_logic"] = False
        field_registry["logic_row_count"] = 0
        field_registry["logic_sections"] = ""
        return field_registry

    logic_summary = (
        logic_registry.groupby("field_name")
        .agg(
            logic_row_count=("field_name", "size"),
            logic_sections=("section", _join_unique),
            logic_template_types=("template_type", _join_unique),
        )
        .reset_index()
        .rename(columns={"field_name": "name"})
    )

    registry = field_registry.merge(logic_summary, on="name", how="left")
    registry["logic_row_count"] = registry["logic_row_count"].fillna(0).astype(int)
    registry["logic_sections"] = registry["logic_sections"].fillna("")
    registry["logic_template_types"] = registry["logic_template_types"].fillna("")
    registry["in_questionnaire_logic"] = registry["logic_row_count"] > 0
    return registry


def add_coding_coverage(
    field_registry: pd.DataFrame,
    coding_registry: pd.DataFrame,
) -> pd.DataFrame:
    """Attach coding availability flags to field metadata."""
    available_codings = set(coding_registry["coding_name"])
    registry = field_registry.copy()
    registry["has_coding_name"] = registry["coding_name"].astype(str).str.strip() != ""
    registry["coding_found"] = registry["coding_name"].isin(available_codings)
    return registry


def add_generation_metadata(
    field_registry: pd.DataFrame,
    coding_registry: pd.DataFrame,
) -> pd.DataFrame:
    """Derive generation actions, value strategies and broad numeric ranges."""
    registry = field_registry.copy()
    version_info = registry["name"].map(_field_version_info).apply(pd.Series)
    registry["field_stem"] = version_info["field_stem"].fillna("")
    registry["field_version"] = version_info["field_version"].fillna("")
    registry["field_variant"] = version_info["field_variant"].fillna("")

    max_versions = _max_versions_by_stem(registry)
    registry["max_field_version_for_stem"] = registry["field_stem"].map(max_versions).fillna("")
    registry["is_superseded_version"] = registry.apply(_is_superseded_version, axis=1)
    registry["output_entity"] = registry["entity"]
    registry["is_required_metadata"] = registry.apply(_is_required_metadata, axis=1)
    registry["v2_inclusion_status"] = registry.apply(_v2_inclusion_status, axis=1)
    registry["generation_action"] = registry["v2_inclusion_status"].map(_generation_action)
    registry["blank_reason"] = registry["v2_inclusion_status"].map(_blank_reason)

    coding_summary = _coding_summary(coding_registry)
    registry = registry.merge(coding_summary, on="coding_name", how="left")
    registry["coding_value_count"] = registry["coding_value_count"].fillna(0).astype(int)
    registry["coding_special_value_count"] = (
        registry["coding_special_value_count"].fillna(0).astype(int)
    )
    registry["coding_non_special_value_count"] = (
        registry["coding_non_special_value_count"].fillna(0).astype(int)
    )
    registry["coding_has_special_values"] = registry["coding_special_value_count"] > 0
    registry["coding_has_non_special_values"] = registry["coding_non_special_value_count"] > 0

    range_info = registry.apply(_numeric_range_info, axis=1).apply(pd.Series)
    registry["generation_min"] = range_info["generation_min"].fillna("")
    registry["generation_max"] = range_info["generation_max"].fillna("")
    registry["numeric_range_rule"] = range_info["numeric_range_rule"].fillna("")
    registry["value_strategy"] = registry.apply(_value_strategy, axis=1)
    registry["special_code_policy"] = registry.apply(_special_code_policy, axis=1)
    registry["special_code_probability"] = registry.apply(_special_code_probability, axis=1)
    registry["multi_select_strategy"] = registry.apply(_multi_select_strategy, axis=1)

    return registry


def build_entity_registry(field_registry: pd.DataFrame) -> pd.DataFrame:
    """Summarise field coverage by output entity."""
    if field_registry.empty:
        return pd.DataFrame(
            columns=[
                "entity",
                "field_count",
                "generated_field_count",
                "blank_field_count",
                "coded_field_count",
                "multi_select_field_count",
                "logic_field_count",
                "required_metadata_field_count",
                "primary_key_fields",
            ],
        )

    return (
        field_registry.groupby("entity")
        .agg(
            field_count=("name", "size"),
            generated_field_count=(
                "generation_action",
                lambda values: (values == "generate").sum(),
            ),
            blank_field_count=("generation_action", lambda values: (values == "blank").sum()),
            coded_field_count=("has_coding_name", "sum"),
            multi_select_field_count=("is_multi_select", "sum"),
            logic_field_count=("in_questionnaire_logic", "sum"),
            required_metadata_field_count=("is_required_metadata", "sum"),
            primary_key_fields=("name", _join_primary_keys(field_registry)),
        )
        .reset_index()
    )


def build_coverage_summary(
    field_registry: pd.DataFrame,
    coding_registry: pd.DataFrame,
    logic_registry: pd.DataFrame,
    entity_registry: pd.DataFrame,
    target_entities: Iterable[str],
) -> str:
    """Build a markdown summary of registry coverage and source quirks."""
    unmatched_logic = logic_registry[~logic_registry["dictionary_match"]]
    duplicate_logic = logic_registry["field_name"].value_counts()
    duplicate_logic = duplicate_logic[duplicate_logic > 1]
    missing_codings = field_registry[
        field_registry["has_coding_name"] & ~field_registry["coding_found"]
    ]
    generated_fields = field_registry[field_registry["generation_action"] == "generate"]
    blank_fields = field_registry[field_registry["generation_action"] == "blank"]
    inferred_range_fields = field_registry[field_registry["numeric_range_rule"] != ""]

    lines = [
        "# Registry Coverage Summary",
        "",
        "Generated from the configured raw OFH documentation files.",
        "",
        "## Scope",
        "",
        f"- Target entities: {', '.join(target_entities)}",
        f"- Dictionary fields: {len(field_registry)}",
        f"- Coding rows: {len(coding_registry)}",
        f"- Questionnaire logic rows: {len(logic_registry)}",
        f"- Fields marked for generation: {len(generated_fields)}",
        f"- Fields marked blank: {len(blank_fields)}",
        f"- Fields with inferred numeric ranges: {len(inferred_range_fields)}",
        "",
        "## Entity Coverage",
        "",
        "| Entity | Fields | Generate | Blank | Coded | Multi-select | Fields in v2 logic |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for row in entity_registry.to_dict("records"):
        lines.append(
            "| {entity} | {field_count} | {generated_field_count} | {blank_field_count} | "
            "{coded_field_count} | {multi_select_field_count} | {logic_field_count} |".format(
                **row,
            ),
        )

    lines.extend(
        [
            "",
            "## Checks",
            "",
            f"- Logic rows not matched to dictionary fields: {len(unmatched_logic)}",
            f"- Fields with duplicate logic rows: {len(duplicate_logic)}",
            f"- Fields with coding names missing from coding workbook: {len(missing_codings)}",
            "",
        ],
    )

    if not unmatched_logic.empty:
        lines.append("### Unmatched Logic Fields")
        lines.append("")
        for field_name in sorted(unmatched_logic["field_name"].astype(str).unique()):
            lines.append(f"- `{field_name}`")
        lines.append("")

    if not duplicate_logic.empty:
        lines.append("### Duplicate Logic Fields")
        lines.append("")
        for field_name, count in duplicate_logic.sort_index().items():
            lines.append(f"- `{field_name}`: {count} rows")
        lines.append("")

    if not missing_codings.empty:
        lines.append("### Missing Coding Names")
        lines.append("")
        for coding_name in sorted(missing_codings["coding_name"].astype(str).unique()):
            lines.append(f"- `{coding_name}`")
        lines.append("")

    return "\n".join(lines)


def _read_sheet(path: Path, sheet_name: str) -> pd.DataFrame:
    """Read one workbook sheet with stable empty-string handling."""
    frame = pd.read_excel(
        path,
        sheet_name=sheet_name,
        dtype=object,
        keep_default_na=False,
    )
    frame = frame.dropna(how="all")
    frame.columns = [str(column).strip() for column in frame.columns]
    return frame.where(pd.notna(frame), "")


def _normalise_logic_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Ensure questionnaire logic sheets expose the expected column names."""
    if "section" not in frame.columns:
        section_column = _find_section_column(frame.columns)
        frame = frame.rename(columns={section_column: "section"})

    for column in LOGIC_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""

    return frame


def _normalise_known_logic_field_names(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply reviewed fixes for known source field-name quirks."""
    registry = frame.copy()
    field_name = registry["field_name"].astype(str).str.strip()
    question_text = registry["question_text"].astype(str).str.strip().str.casefold()

    medicat_question = (
        "do you regularly take medications for any of the following reasons?"
    )
    medicat_mask = (field_name == "eb") & (question_text == medicat_question)
    registry.loc[medicat_mask, "field_name"] = "MEDICAT_1_M"
    return registry


def _find_section_column(columns: Iterable[str]) -> str:
    for column in columns:
        if str(column).lower().startswith("sectio"):
            return str(column)
    return list(columns)[1]


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value == "":
        return False
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}


def _is_special_code(value: object) -> bool:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return bool(pd.notna(numeric) and numeric < 0)


def _field_version_info(field_name: object) -> dict[str, object]:
    """Split a versioned field name into stem, version and variant."""
    parts = str(field_name).rsplit("_", 2)
    if len(parts) != 3:
        return {"field_stem": "", "field_version": "", "field_variant": ""}

    stem, version, variant = parts
    if not version.isdigit() or not (variant.isdigit() or variant == "M"):
        return {"field_stem": "", "field_version": "", "field_variant": ""}

    return {
        "field_stem": stem,
        "field_version": int(version),
        "field_variant": variant,
    }


def _max_versions_by_stem(registry: pd.DataFrame) -> dict[str, int]:
    """Find the highest questionnaire version available for each field stem."""
    versioned = registry[
        (registry["field_stem"] != "")
        & (registry["field_version"] != "")
        & registry["field_version"].notna()
    ].copy()
    if versioned.empty:
        return {}

    versioned["field_version"] = versioned["field_version"].astype(int)
    return versioned.groupby("field_stem")["field_version"].max().to_dict()


def _is_superseded_version(row: pd.Series) -> bool:
    if row["field_version"] == "" or row["max_field_version_for_stem"] == "":
        return False
    return int(row["field_version"]) < int(row["max_field_version_for_stem"])


def _is_required_metadata(row: pd.Series) -> bool:
    entity = str(row["entity"])
    name = str(row["name"])
    if name in REQUIRED_METADATA_FIELDS.get(entity, set()):
        return True
    return bool(str(row["primary_key_type"]).strip())


def _v2_inclusion_status(row: pd.Series) -> str:
    """Classify whether a field should be generated for the V2 Beta scope."""
    if row["is_required_metadata"]:
        return "metadata"
    if row["is_superseded_version"]:
        return "superseded_by_v2_field"
    if row["entity"] == "participant":
        if row["in_questionnaire_logic"]:
            return "v2_question_participant_field"
        return "participant_context"
    if row["in_questionnaire_logic"]:
        return "v2_questionnaire_field"
    return "not_in_v2_logic"


def _generation_action(v2_inclusion_status: str) -> str:
    if v2_inclusion_status in {"superseded_by_v2_field", "not_in_v2_logic"}:
        return "blank"
    return "generate"


def _blank_reason(v2_inclusion_status: str) -> str:
    if v2_inclusion_status == "superseded_by_v2_field":
        return "superseded_by_v2_field"
    if v2_inclusion_status == "not_in_v2_logic":
        return "not_in_v2_logic"
    return ""


def _coding_summary(coding_registry: pd.DataFrame) -> pd.DataFrame:
    """Count regular and special coding values by coding name."""
    if coding_registry.empty:
        return pd.DataFrame(
            columns=[
                "coding_name",
                "coding_value_count",
                "coding_special_value_count",
                "coding_non_special_value_count",
            ],
        )

    summary = (
        coding_registry.groupby("coding_name")
        .agg(
            coding_value_count=("code", "size"),
            coding_special_value_count=("is_special_code", "sum"),
        )
        .reset_index()
    )
    summary["coding_non_special_value_count"] = (
        summary["coding_value_count"] - summary["coding_special_value_count"]
    )
    return summary


def _numeric_range_info(row: pd.Series) -> dict[str, object]:
    """Infer broad numeric generation bounds from field metadata."""
    if row["generation_action"] == "blank":
        return {"generation_min": "", "generation_max": "", "numeric_range_rule": ""}

    field_type = str(row["type"]).lower()
    if field_type not in {"integer", "float"}:
        return {"generation_min": "", "generation_max": "", "numeric_range_rule": ""}
    if (
        row["coding_found"]
        and row["coding_has_non_special_values"]
        and not _is_numeric_input_with_coded_choices(row)
    ):
        return {"generation_min": "", "generation_max": "", "numeric_range_rule": ""}

    name = str(row["name"]).upper()
    units = str(row["units"]).lower()

    if name == "BIRTH_YEAR":
        return _range(BIRTH_YEAR_MIN, BIRTH_YEAR_MAX, "birth_year")
    if name in {"REGISTRATION_YEAR", "CONSENT_YEAR"}:
        return _range(
            CORE_TIMELINE_YEAR_MIN,
            CORE_TIMELINE_YEAR_MAX,
            "core_timeline_year",
        )
    if "AGE" in name:
        return _range(0, 110, "name_contains_age")
    if "YEAR" in name or name.endswith("_YR") or "_YR_" in name:
        return _range(SYNTHETIC_YEAR_MIN, SYNTHETIC_YEAR_MAX, "synthetic_year")
    if "MONTH" in name:
        return _range(1, 12, "name_contains_month")
    if "DAYS" in name or name.endswith("_DAY"):
        return _range(0, 7, "name_contains_days")
    if "MINS" in name or "MINUTES" in name:
        return _range(0, 1440, "name_contains_minutes")
    if "HRS" in name or "HOURS" in name:
        return _range(0, 24, "name_contains_hours")
    if "HEIGHT" in name or "_CM" in name or units in {"cm", "centimetres", "centimeters"}:
        return _range(50, 220, "height_cm")
    if "WEIGHT" in name or "_KG" in name or units in {"kg", "kilograms", "kilogrammes"}:
        return _range(2, 300, "weight_kg")
    if field_type == "integer":
        return _range(0, 10, "type_default_integer")
    return _range(0, 100, "type_default_float")


def _range(minimum: int | float, maximum: int | float, rule: str) -> dict[str, object]:
    return {
        "generation_min": minimum,
        "generation_max": maximum,
        "numeric_range_rule": rule,
    }


def _value_strategy(row: pd.Series) -> str:
    """Choose the generator strategy for a field."""
    if row["generation_action"] == "blank":
        return "blank"

    name = str(row["name"])
    field_type = str(row["type"]).lower()

    if name in {"ID", "PID"}:
        return "synthetic_identifier"
    if name == "QUESTIONNAIRE_VERSION":
        return "constant_questionnaire_version"
    if field_type == "date" or name.endswith("_DATE"):
        return "synthetic_future_date"
    if row["is_multi_select"]:
        return "coded_multi_select"
    if _is_numeric_input_with_coded_choices(row):
        return "numeric_range_with_coded_choices"
    if row["coding_found"] and row["coding_has_non_special_values"]:
        return "coded_single"
    if row["coding_found"] and row["coding_has_special_values"] and field_type in {
        "integer",
        "float",
    }:
        return "numeric_range_with_special_codes"
    if field_type in {"integer", "float"}:
        return "numeric_range"
    if field_type == "string":
        return "synthetic_string"
    return "synthetic_value"


def _special_code_policy(row: pd.Series) -> str:
    """Choose whether special response codes may be sampled."""
    if row["generation_action"] == "blank":
        return "not_applicable"
    if _is_numeric_input_with_coded_choices(row) and row["coding_value_count"] > 0:
        return "include"
    if row["coding_has_special_values"]:
        return "include"
    return "exclude"


def _special_code_probability(row: pd.Series) -> float:
    if row["special_code_policy"] == "include":
        return DEFAULT_SPECIAL_CODE_PROBABILITY
    return 0.0


def _multi_select_strategy(row: pd.Series) -> str:
    """Describe the output format for multi-select fields."""
    if row["generation_action"] == "blank":
        return "not_applicable"
    if row["is_multi_select"]:
        return "bracketed_comma_list"
    return "not_applicable"


def _is_numeric_input_with_coded_choices(row: pd.Series) -> bool:
    """Identify radio-and-input fields that mix numeric values with coded choices."""
    field_type = str(row["type"]).lower()
    logic_template_types = str(row.get("logic_template_types", ""))
    return (
        field_type in {"integer", "float"}
        and bool(row["coding_found"])
        and "radioAndInput" in logic_template_types.split("; ")
    )


def _non_empty_values(series: pd.Series) -> set[str]:
    return {str(value) for value in series if str(value).strip()}


def _join_unique(values: pd.Series) -> str:
    return "; ".join(sorted({str(value) for value in values if str(value).strip()}))


def _join_primary_keys(field_registry: pd.DataFrame):
    primary_key_lookup = (
        field_registry[field_registry["primary_key_type"].astype(str).str.strip() != ""]
        .groupby("entity")["name"]
        .apply(_join_unique)
        .to_dict()
    )

    def join_primary_keys(names: pd.Series) -> str:
        entity = field_registry.loc[names.index[0], "entity"]
        return primary_key_lookup.get(entity, "")

    return join_primary_keys


def _write_registry(registry: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    registry.where(pd.notna(registry), "").to_csv(path, index=False)


def _source_file_entry(role: str, path: Path) -> dict[str, object]:
    """Describe and fingerprint one source file for the source manifest."""
    entry: dict[str, object] = {
        "role": role,
        "path": str(path),
        "filename": path.name,
        "exists": path.exists(),
    }

    if path.exists():
        entry["size_bytes"] = path.stat().st_size
        entry["sha256"] = _sha256(path)

    return entry


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _empty_field_registry() -> pd.DataFrame:
    registry = pd.DataFrame(columns=FIELD_COLUMNS)
    registry["in_beta_scope"] = pd.Series(dtype=bool)
    return registry
