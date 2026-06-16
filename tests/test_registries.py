import json
from pathlib import Path

import pandas as pd

from ofh_synthetic_data.config import (
    AppConfig,
    PathsConfig,
    RegistryConfig,
    SourceFilesConfig,
)
from ofh_synthetic_data.ingest.registries import build_registries


def test_build_registries_from_source_workbooks(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()

    _write_dictionary(raw_dir / "dictionary.xlsx")
    _write_codings(raw_dir / "codings.xlsx")
    _write_logic(raw_dir / "logic.xlsx")
    (raw_dir / "questionnaire.pdf").write_bytes(b"synthetic fixture pdf")

    config = AppConfig(
        paths=PathsConfig(raw_data_dir=raw_dir, processed_data_dir=processed_dir),
        source_files=SourceFilesConfig(
            questionnaire_pdf="questionnaire.pdf",
            questionnaire_logic="logic.xlsx",
            data_dictionary="dictionary.xlsx",
            codings="codings.xlsx",
        ),
        registry=RegistryConfig(target_entities=("participant", "questionnaire")),
    )

    result = build_registries(config)

    field_registry = pd.read_csv(result.field_registry, keep_default_na=False)
    coding_registry = pd.read_csv(result.coding_registry, keep_default_na=False)
    entity_registry = pd.read_csv(result.entity_registry, keep_default_na=False)
    logic_registry = pd.read_csv(result.logic_registry, keep_default_na=False)
    coverage_summary = result.coverage_summary.read_text(encoding="utf-8")
    source_manifest = json.loads(result.source_manifest.read_text(encoding="utf-8"))

    assert result.counts == {
        "fields": 5,
        "codings": 4,
        "logic_rows": 4,
        "entities": 2,
    }
    assert set(field_registry["entity"]) == {"participant", "questionnaire"}
    assert "clinic_measurements" not in set(field_registry["entity"])
    assert field_registry["name"].tolist() == [
        "PID",
        "DEMOG_SEX_2_1",
        "ID",
        "ACTIVITY_WALK_DAYS_1_1",
        "ACTIVITY_WALK_DAYS_2_1",
    ]
    assert field_registry["dictionary_order"].tolist() == [0, 1, 2, 3, 4]

    sex_field = field_registry[field_registry["name"] == "DEMOG_SEX_2_1"].iloc[0]
    assert bool(sex_field["in_questionnaire_logic"])
    assert sex_field["logic_sections"] == "4. Corrupted header section"
    assert sex_field["generation_action"] == "generate"
    assert sex_field["v2_inclusion_status"] == "v2_question_participant_field"
    assert sex_field["value_strategy"] == "coded_single"
    assert sex_field["special_code_policy"] == "include"

    id_field = field_registry[field_registry["name"] == "ID"].iloc[0]
    assert bool(id_field["is_required_metadata"])
    assert id_field["v2_inclusion_status"] == "metadata"
    assert id_field["value_strategy"] == "synthetic_identifier"

    old_activity_field = field_registry[
        field_registry["name"] == "ACTIVITY_WALK_DAYS_1_1"
    ].iloc[0]
    assert old_activity_field["generation_action"] == "blank"
    assert old_activity_field["blank_reason"] == "superseded_by_v2_field"

    v2_activity_field = field_registry[
        field_registry["name"] == "ACTIVITY_WALK_DAYS_2_1"
    ].iloc[0]
    assert v2_activity_field["generation_action"] == "generate"
    assert str(v2_activity_field["generation_min"]) == "0"
    assert str(v2_activity_field["generation_max"]) == "7"
    assert v2_activity_field["numeric_range_rule"] == "name_contains_days"
    assert v2_activity_field["value_strategy"] == "numeric_range"

    questionnaire_entity = entity_registry[entity_registry["entity"] == "questionnaire"].iloc[0]
    assert questionnaire_entity["generated_field_count"] == 2
    assert questionnaire_entity["blank_field_count"] == 1

    special_code = coding_registry[coding_registry["code"] == -1].iloc[0]
    assert bool(special_code["is_special_code"])
    none_meaning = coding_registry[coding_registry["code"] == 3].iloc[0]
    assert none_meaning["meaning"] == "None"

    unmatched_logic = logic_registry[logic_registry["field_name"] == "eb"].iloc[0]
    assert not bool(unmatched_logic["dictionary_match"])
    assert "`eb`" in coverage_summary

    manifest_files = {entry["role"]: entry for entry in source_manifest["files"]}
    assert set(manifest_files) == {
        "questionnaire_pdf",
        "questionnaire_logic",
        "data_dictionary",
        "codings",
    }
    assert manifest_files["questionnaire_pdf"]["exists"]
    assert manifest_files["questionnaire_pdf"]["sha256"]


def _write_dictionary(path: Path) -> None:
    participant = pd.DataFrame(
        [
            {
                "entity": "participant",
                "name": "PID",
                "type": "string",
                "primary_key_type": "global",
                "coding_name": "",
                "is_sparse_coding": "",
                "is_multi_select": "",
                "referenced_entity_field": "",
                "relationship": "",
                "folder_path": "Participant",
                "title": "PID",
                "units": "",
                "description": "Participant ID",
            },
            {
                "entity": "participant",
                "name": "DEMOG_SEX_2_1",
                "type": "integer",
                "primary_key_type": "",
                "coding_name": "DEMOG_SEX_2_1",
                "is_sparse_coding": False,
                "is_multi_select": False,
                "referenced_entity_field": "",
                "relationship": "",
                "folder_path": "Participant",
                "title": "Sex",
                "units": "",
                "description": "Sex at birth",
            },
        ],
    )
    questionnaire = pd.DataFrame(
        [
            {
                "entity": "questionnaire",
                "name": "ID",
                "type": "string",
                "primary_key_type": "local",
                "coding_name": "",
                "is_sparse_coding": "",
                "is_multi_select": "",
                "referenced_entity_field": "",
                "relationship": "",
                "folder_path": "Questionnaire",
                "title": "ID",
                "units": "",
                "description": "Questionnaire ID",
            },
            {
                "entity": "questionnaire",
                "name": "ACTIVITY_WALK_DAYS_1_1",
                "type": "integer",
                "primary_key_type": "",
                "coding_name": "",
                "is_sparse_coding": "",
                "is_multi_select": "",
                "referenced_entity_field": "",
                "relationship": "",
                "folder_path": "Questionnaire",
                "title": "Walk days old",
                "units": "",
                "description": "Old V1 walking days field",
            },
            {
                "entity": "questionnaire",
                "name": "ACTIVITY_WALK_DAYS_2_1",
                "type": "integer",
                "primary_key_type": "",
                "coding_name": "",
                "is_sparse_coding": "",
                "is_multi_select": "",
                "referenced_entity_field": "",
                "relationship": "",
                "folder_path": "Questionnaire",
                "title": "Walk days",
                "units": "",
                "description": "V2 walking days field",
            },
        ],
    )
    clinic = pd.DataFrame(
        [
            {
                "entity": "clinic_measurements",
                "name": "HEIGHT",
                "type": "float",
            },
        ],
    )

    with pd.ExcelWriter(path) as writer:
        participant.to_excel(writer, sheet_name="participant", index=False)
        questionnaire.to_excel(writer, sheet_name="questionnaire", index=False)
        clinic.to_excel(writer, sheet_name="clinic_measurements", index=False)


def _write_codings(path: Path) -> None:
    participant = pd.DataFrame(
        [
            {
                "coding_name": "DEMOG_SEX_2_1",
                "code": 1,
                "meaning": "Female",
                "display_order": 1,
                "parent_code": "",
            },
            {
                "coding_name": "DEMOG_SEX_2_1",
                "code": 2,
                "meaning": "Male",
                "display_order": 2,
                "parent_code": "",
            },
            {
                "coding_name": "DEMOG_SEX_2_1",
                "code": -1,
                "meaning": "Prefer not to say",
                "display_order": 3,
                "parent_code": "",
            },
            {
                "coding_name": "DEMOG_SEX_2_1",
                "code": 3,
                "meaning": "None",
                "display_order": 4,
                "parent_code": "",
            },
        ],
    )

    with pd.ExcelWriter(path) as writer:
        participant.to_excel(writer, sheet_name="participant", index=False)


def _write_logic(path: Path) -> None:
    section4 = pd.DataFrame(
        [
            {
                "index": 1,
                "sectio+B1:H59n": "4. Corrupted header section",
                "question_text": "What sex were you registered with at birth?",
                "source": "ONS",
                "template_type": "radio",
                "field_name": "DEMOG_SEX_2_1",
                "question_type": "core",
                "show_if": "",
            },
            {
                "index": 2,
                "sectio+B1:H59n": "4. Corrupted header section",
                "question_text": "Walking days",
                "source": "",
                "template_type": "input",
                "field_name": "ACTIVITY_WALK_DAYS_2_1",
                "question_type": "core",
                "show_if": "",
            },
            {
                "index": 3,
                "sectio+B1:H59n": "4. Corrupted header section",
                "question_text": "Unmatched row",
                "source": "",
                "template_type": "text",
                "field_name": "eb",
                "question_type": "core",
                "show_if": "",
            },
        ],
    )
    section5 = pd.DataFrame(
        [
            {
                "index": 1,
                "section": "5. Notes column",
                "question_text": "Questionnaire ID",
                "source": "",
                "template_type": "text",
                "field_name": "ID",
                "question_type": "metadata",
                "show_if": "",
                "notes": "extra column should be preserved",
            },
        ],
    )

    with pd.ExcelWriter(path) as writer:
        pd.DataFrame([{"Questionnaire Version": "v2.1"}]).to_excel(
            writer,
            sheet_name="information",
            index=False,
        )
        section4.to_excel(writer, sheet_name="section4", index=False)
        section5.to_excel(writer, sheet_name="section5", index=False)
