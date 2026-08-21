"""Registry-driven synthetic table generation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
import random
from random import Random
from typing import Any
from faker import Faker

import pandas as pd

from ofh_synthetic_data.config import AppConfig, GenerationConfig
from ofh_synthetic_data.export.writers import write_metadata, write_records_csv
from ofh_synthetic_data.generate.show_if import evaluate_show_if
from ofh_synthetic_data.synthetic_ranges import (
    BIRTH_YEAR_MAX,
    BIRTH_YEAR_MIN,
    CORE_TIMELINE_YEAR_MAX,
    CORE_TIMELINE_YEAR_MIN,
    SYNTHETIC_DATE_DAY_MAX,
    SYNTHETIC_DATE_DAY_MIN,
    SYNTHETIC_YEAR_MIN,
)
from ofh_synthetic_data.constants import *
from ofh_synthetic_data.generate.linked_data_transformations import *

SUPPRESSION_CODES = {"-999"}


@dataclass(frozen=True)
class GeneratedTables:
    participants: list[dict[str, object]]
    questionnaires: list[dict[str, object]]
    deaths: list[dict[str, object]]
    op: list[dict[str, object]]
    participant_columns: list[str]
    questionnaire_columns: list[str]
    deaths_columns: list[str]
    op_columns: list[str]
    manifest: dict[str, Any]
    skipped_by_logic_count: int


@dataclass(frozen=True)
class GeneratedTablePaths:
    participant: Path
    questionnaire: Path
    deaths: Path
    op: Path
    manifest: Path


@dataclass(frozen=True)
class CoreTimeline:
    year: int
    month: int


def generate_tables_from_processed_registries(config: AppConfig) -> GeneratedTables:
    """Read processed registries and generate in-memory synthetic tables."""
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
    """Generate linked participant and questionnaire records from registry metadata."""
    rng = Random(generation_config.seed)
    coding_lookup = _build_coding_lookup(coding_registry)
    logic_rules, logic_order = _build_logic_rules(logic_registry)

    participant_fields = _fields_for_entity(field_registry, "participant")
    questionnaire_fields = _fields_for_entity(field_registry, "questionnaire")
    deaths_columns = load_linked_dictionary(path="dictionaries/processed/linked-data/linked_data_dictionaries/", df_name="deaths")["name"].astype(str).tolist()
    op_columns = load_linked_dictionary(path="dictionaries/processed/linked-data/linked_data_dictionaries/", df_name="op")["name"].astype(str).tolist()
    participant_columns = participant_fields["name"].astype(str).tolist()
    questionnaire_columns = questionnaire_fields["name"].astype(str).tolist()
    synthetic_string_fields = sorted(
        field_registry.loc[
            field_registry["value_strategy"].astype(str).eq("synthetic_string"),
            "name",
        ]
        .astype(str)
        .tolist()
    )

    participants: list[dict[str, object]] = []
    questionnaires: list[dict[str, object]] = []
    deaths: list[dict[str, object]] = []
    op: list[dict[str, object]] = []
    skipped_by_logic_count = 0

    # setting faker instance and providing seed
    fake = Faker()
    Faker.seed(generation_config.seed)

    for row_index in range(generation_config.rows):
        pid = _participant_id(row_index)
        timeline = _core_timeline(rng)
        participant = _generate_record(
            fields=participant_fields,
            coding_lookup=coding_lookup,
            rng=rng,
            row_index=row_index,
            pid=pid,
            generation_config=generation_config,
            timeline=timeline,
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
            timeline=timeline,
        )

        skipped_by_logic_count += skipped_for_row
        participants.append(participant)
        questionnaires.append(questionnaire)

        # 5% chance a given PID will have died and therefore have a death record
        if random.random() < 0.05:
            death_record = _generate_death_record(fake, pid=pid, path="dictionaries/processed/linked-data/", row_number=len(deaths))
            deaths.append(death_record)

        # 90% chance a given PID will have an Outpatient record
        if random.random() < 0.9:
            op_record = _generate_outpatient_record(fake, pid=pid, path="dictionaries/processed/linked-data/", row_number=len(op))
            op.append(op_record)

    return GeneratedTables(
        participants=participants,
        questionnaires=questionnaires,
        deaths=deaths,
        op=op,
        participant_columns=participant_columns,
        questionnaire_columns=questionnaire_columns,
        deaths_columns=deaths_columns,
        op_columns=op_columns,
        manifest={
            "status": "beta",
            "manual_validation_status": "ongoing",
            "rows": generation_config.rows,
            "seed": generation_config.seed,
            "questionnaire_version": generation_config.questionnaire_version,
            "outputs": {
                "participant": generation_config.participant_file,
                "questionnaire": generation_config.questionnaire_file,
                "deaths" : generation_config.deaths_file,
                "op" : generation_config.op_file,
            },
            "config": config_snapshot or {"generation": asdict(generation_config)},
            "source_manifest": source_manifest or {},
            "synthetic_markers": {
                "id_prefix": "SYN",
                "synthetic_string_prefix": "SYNTHETIC",
                "synthetic_string_fields": synthetic_string_fields,
                "future_year_minimum": SYNTHETIC_YEAR_MIN,
                "core_timeline_year_range": [
                    CORE_TIMELINE_YEAR_MIN,
                    CORE_TIMELINE_YEAR_MAX,
                ],
                "birth_year_range": [BIRTH_YEAR_MIN, BIRTH_YEAR_MAX],
            },
            "questionnaire_logic": {
                "applied": bool(logic_rules),
                "skipped_values": skipped_by_logic_count,
            },
            "column_order": {
                "source": "data_dictionary",
                "participant_columns": len(participant_columns),
                "questionnaire_columns": len(questionnaire_columns),
                "deaths_columns" : len(deaths_columns),
                "op_columns" : len(op_columns)
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
    """Write generated tables and manifest to disk."""
    participant_path = output_dir / config.participant_file
    questionnaire_path = output_dir / config.questionnaire_file
    deaths_path = output_dir / config.deaths_file
    op_path = output_dir / config.op_file
    manifest_path = output_dir / config.manifest_file

    write_records_csv(tables.participants, participant_path, tables.participant_columns)
    write_records_csv(tables.questionnaires, questionnaire_path, tables.questionnaire_columns)
    write_records_csv(tables.deaths, deaths_path, tables.deaths_columns)
    write_records_csv(tables.op, op_path, tables.op_columns)
    write_metadata(
        {
            **tables.manifest,
            "output_files": {
                "participant": str(participant_path),
                "questionnaire": str(questionnaire_path),
                "deaths" : str(deaths_path),
                "op" : str(op_path)
            },
        },
        manifest_path,
    )

    return GeneratedTablePaths(
        participant=participant_path,
        questionnaire=questionnaire_path,
        deaths=deaths_path,
        op=op_path,
        manifest=manifest_path,
    )


def _generate_record(
    fields: pd.DataFrame,
    coding_lookup: dict[str, dict[str, list[str]]],
    rng: Random,
    row_index: int,
    pid: str,
    generation_config: GenerationConfig,
    timeline: CoreTimeline,
) -> dict[str, object]:
    """Generate a non-questionnaire record without branching logic."""
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
            timeline=timeline,
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
    timeline: CoreTimeline,
) -> tuple[dict[str, object], int]:
    """Generate a questionnaire row while applying release-schema show_if logic."""
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
                timeline=timeline,
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
                timeline=timeline,
            )
        else:
            record[name] = ""
            skipped_by_logic_count += 1

        context[name] = record[name]

    return record, skipped_by_logic_count

def _generate_death_record(fake: Faker, pid: str, path: Path, row_number:int) -> dict[str, object]:
    # load dictionaries and coding files
    df_dicts = get_dictionaries(path=path, df_name="deaths")

    # creating dictionary of coded columns and code value
    coded_pairs_dict = create_coded_pairs(data_dictionary=df_dicts)
    # ordering the coded columns
    ordered_columns_dict = order_numbered_columns(coded_pairs_dict=coded_pairs_dict)

    # defining fields which will always be populated with coded values
    always_populated = [x for x in coded_pairs_dict.keys() if not re.search("|".join(ordered_columns_dict.keys()), x) or re.search("_1$", x)]

    deaths_record = {}

    deaths_record["PID"] = pid

    # adding ICD codes to first cause of death column and underlying cause of death column
    for colname in always_populated:
            deaths_record[colname] = fake.random_element(
                    elements=df_dicts[coded_pairs_dict[colname]]["code"].unique()
                )

    # conditionally populating ICD cause of death columns to mimic missingness in real data
    for base_colname, ordered_col_list in ordered_columns_dict.items():
        for i in range(0, len(ordered_col_list)-1):
            if fake.random_int(min=0, max=10) < 8 and deaths_record[ordered_col_list[i]] != "":
                deaths_record[ordered_col_list[i+1]] = fake.random_element(
                    elements=df_dicts[coded_pairs_dict[ordered_col_list[i]]]["code"].unique()
                )
            else:
                deaths_record[ordered_col_list[i+1]] = ""

    deaths_record["REG_DATE_OF_DEATH"] = fake.date_between(start_date=DATE_BOOKENDS["deaths"]["start"], end_date=DATE_BOOKENDS["deaths"]["end"])
    deaths_record["REG_DATE"] = fake.date_between(
        start_date=deaths_record["REG_DATE_OF_DEATH"], 
        end_date=deaths_record["REG_DATE_OF_DEATH"] + datetime.timedelta(days=10)
    )

    deaths_record["ROW_ID"] = row_number

    return deaths_record

def _generate_outpatient_record(fake: Faker, pid: str, path: Path, row_number:int) -> dict[str, object]:
    # load dictionaries and coding files
    df_dicts = get_dictionaries(path=path, df_name="op")
    
    # creating dictionary of coded columns and code value
    coded_pairs_dict = create_coded_pairs(data_dictionary=df_dicts)
    # ordering the coded columns
    ordered_columns_dict = order_numbered_columns(coded_pairs_dict=coded_pairs_dict)

    # defining columns that require specific conditions for coded values to be populated
    conditional_columns = ["RTTPERSTAT", "SUSSPELLID"]

    # defining fields which will always be populated with coded values
    always_populated = [
        x for x in coded_pairs_dict.keys() 
        if not re.search("|".join(ordered_columns_dict.keys()), x) 
        or re.search("_01$", x) 
        and x not in conditional_columns
    ]

    record = {}
    
    record["PID"] = pid

    for colname in always_populated:
            record[colname] = pick_random_code(fake, df_name=coded_pairs_dict[colname], data_dictionary=df_dicts)
    
    for base_colname in ordered_columns_dict.keys():
        ordered_list = ordered_columns_dict[base_colname]
        for i in range(0, len(ordered_list)-1):
            # 80% chance that diagnosis or procedure code is populated
            if random.random() <= 0.8 and record[ordered_list[i]] not in ["", "-", "R69X", "R69X6", "R69X8", "R69X3"]:
                record[ordered_list[i+1]] = pick_random_code(fake, df_name=coded_pairs_dict[colname], data_dictionary=df_dicts)
            # 20% chance that unknown or missing code value present
            elif random.random() > 0.8 and record[ordered_list[i]] not in ["", "-"] and re.search("DIAG", base_colname):
                record[ordered_list[i+1]] = fake.random_element(elements=["R69X", "R69X6", "R69X8", "R69X3"])
            else:
                if re.search("OPERTN", base_colname):
                    record[ordered_list[i+1]] = "-"
                else:
                    record[ordered_list[i+1]] = ""
    
    record["APPTDATE"] = fake.date_between(start_date=DATE_BOOKENDS["op"]["start"], end_date=DATE_BOOKENDS["op"]["end"])
    # these fields only available from 2012/2013 financial year
    if record["APPTDATE"] >= datetime.date(2012,4,1):
        record["RTTPERSTART"] = fake.date_between(start_date=datetime.date(2012,4,1), end_date=DATE_BOOKENDS["op"]["end"])
        record["RTTPEREND"] = fake.date_between(start_date=record["RTTPERSTART"], end_date=DATE_BOOKENDS["op"]["end"])
        record["RTTPERSTAT"] = pick_random_code(fake, coded_pairs_dict["RTTPERSTAT"], data_dictionary=df_dicts)
    # enter as null for records prior to that FYEAR
    else:
        for c in ["RTTPERSTART", "RTTPEREND", "RTTPERSTAT"]:
            record[c] = np.nan
    
    # generating pseudonymised provider code
    record["PROCODE3_OFH"] = generate_numeric_id(n=6)
    
    # generating SUSSPELLID code
    if record["APPTDATE"] < datetime.date(2016,4,1):
        record["SUSSPELLID"] = generate_numeric_id(n=10)
    else:
        record["SUSSPELLID"] = generate_numeric_id(n=19)
    # 0.01% chance it is missing
    if random.random() < 0.01:
        record["SUSSPELLID"] = pick_random_code(fake, df_name=coded_pairs_dict["SUSSPELLID"], data_dictionary=df_dicts)
    
    # generating random IMD decile
    record["IMD04_DECILE"] = fake.random_element(elements=IMD_VALID_ENTRIES)
    # about 30% entries are uppercase
    if random.random() < 0.3:
        record["IMD04_DECILE"] = record["IMD04_DECILE"].upper()
    
        # adding `ROW_ID` to dataset
    
    record["ROW_ID"] = row_number
    return record

def _generate_value(
    field: dict[str, object],
    coding_lookup: dict[str, dict[str, list[str]]],
    rng: Random,
    row_index: int,
    pid: str,
    generation_config: GenerationConfig,
    timeline: CoreTimeline,
) -> object:
    """Generate one field value according to its registry value strategy."""
    strategy = str(field.get("value_strategy", ""))
    name = str(field["name"])

    if strategy == "blank":
        return ""
    if strategy == "synthetic_identifier":
        return _synthetic_identifier(name, row_index, pid)
    if strategy == "constant_questionnaire_version":
        return generation_config.questionnaire_version
    if strategy == "synthetic_future_date":
        return _future_date(rng, timeline)
    if name in {"REGISTRATION_YEAR", "CONSENT_YEAR"}:
        return timeline.year
    if name in {"REGISTRATION_MONTH", "CONSENT_MONTH"}:
        return timeline.month
    if name == "BIRTH_YEAR":
        return rng.randint(BIRTH_YEAR_MIN, BIRTH_YEAR_MAX)
    if strategy == "coded_multi_select":
        return _coded_multi_select(field, coding_lookup, rng)
    if strategy == "coded_single":
        return _coded_single(field, coding_lookup, rng)
    if strategy == "numeric_range_with_special_codes":
        if _use_special_code(field, rng):
            special_code = _special_code(field, coding_lookup, rng)
            if special_code:
                return special_code
        return _numeric_range_value(field, rng)
    if strategy == "numeric_range_with_coded_choices":
        if _use_special_code(field, rng):
            coded_choice = _coded_choice(field, coding_lookup, rng)
            if coded_choice:
                return coded_choice
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
    """Group show_if expressions by field while preserving logic row order."""
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
    """Build coding lists used for random value selection."""
    lookup: dict[str, dict[str, list[str]]] = {}

    for coding_name, rows in coding_registry.groupby("coding_name"):
        codes = [_format_code(value) for value in rows["code"].tolist()]
        special_flags = rows["is_special_code"].map(_as_bool).tolist()
        lookup[str(coding_name)] = {
            "regular": [
                code
                for code, special in zip(codes, special_flags, strict=True)
                if not special and not _is_suppression_code(code)
            ],
            "special": [
                code
                for code, special in zip(codes, special_flags, strict=True)
                if special and not _is_suppression_code(code)
            ],
            "all": [code for code in codes if not _is_suppression_code(code)],
        }

    return lookup


def _coded_single(
    field: dict[str, object],
    coding_lookup: dict[str, dict[str, list[str]]],
    rng: Random,
) -> str:
    """Choose one coded value, optionally using a special code."""
    if _use_special_code(field, rng):
        special_code = _special_code(field, coding_lookup, rng)
        if special_code:
            return special_code

    codes = _codes(field, coding_lookup, "regular")
    if not codes:
        codes = _codes(field, coding_lookup, "special")
    return rng.choice(codes) if codes else ""


def _coded_multi_select(
    field: dict[str, object],
    coding_lookup: dict[str, dict[str, list[str]]],
    rng: Random,
) -> str:
    """Choose a bracketed comma-list of coded values for multi-select fields."""
    if _use_special_code(field, rng):
        special_code = _special_code(field, coding_lookup, rng)
        if special_code:
            return f"[{special_code}]"

    regular_codes = _codes(field, coding_lookup, "regular")
    selected = [code for code in regular_codes if rng.random() < 0.5]
    if not selected and regular_codes:
        selected = [rng.choice(regular_codes)]
    if not selected:
        special_codes = _codes(field, coding_lookup, "special")
        if special_codes:
            selected = [rng.choice(special_codes)]
    if not selected:
        return ""
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


def _coded_choice(
    field: dict[str, object],
    coding_lookup: dict[str, dict[str, list[str]]],
    rng: Random,
) -> str:
    """Choose any coded option for numeric input fields with coded alternatives."""
    codes = _codes(field, coding_lookup, "all")
    return rng.choice(codes) if codes else ""


def _codes(
    field: dict[str, object],
    coding_lookup: dict[str, dict[str, list[str]]],
    code_type: str,
) -> list[str]:
    coding_name = str(field.get("coding_name", ""))
    return coding_lookup.get(coding_name, {}).get(code_type, [])


def _numeric_range_value(field: dict[str, object], rng: Random) -> int | float | str:
    """Generate an integer or float within registry min/max bounds."""
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


def _core_timeline(rng: Random) -> CoreTimeline:
    return CoreTimeline(
        year=rng.randint(CORE_TIMELINE_YEAR_MIN, CORE_TIMELINE_YEAR_MAX),
        month=rng.randint(1, 12),
    )


def _future_date(rng: Random, timeline: CoreTimeline) -> str:
    return date(
        year=timeline.year,
        month=timeline.month,
        day=rng.randint(SYNTHETIC_DATE_DAY_MIN, SYNTHETIC_DATE_DAY_MAX),
    ).isoformat()


def _read_registry(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=object, keep_default_na=False).where(pd.notna, "")


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


def _is_suppression_code(code: str) -> bool:
    return code in SUPPRESSION_CODES


def _float_value(value: object, default: float | None = None) -> float | None:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return default
    return float(numeric)


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}
