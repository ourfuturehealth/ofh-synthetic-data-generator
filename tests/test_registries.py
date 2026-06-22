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

    config = AppConfig(
        paths=PathsConfig(raw_data_dir=raw_dir, processed_data_dir=processed_dir),
        source_files=SourceFilesConfig(
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
        "fields": 8,
        "codings": 12,
        "logic_rows": 5,
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
        "EDU_COMP_AGE_2_1",
        "MEDICAT_1_M",
        "DICT_ONLY_1_1",
    ]
    assert field_registry["dictionary_order"].tolist() == [0, 1, 2, 3, 4, 5, 6, 7]

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

    education_age_field = field_registry[
        field_registry["name"] == "EDU_COMP_AGE_2_1"
    ].iloc[0]
    assert education_age_field["logic_template_types"] == "radioAndInput"
    assert str(education_age_field["generation_min"]) == "0"
    assert str(education_age_field["generation_max"]) == "110"
    assert education_age_field["numeric_range_rule"] == "name_contains_age"
    assert education_age_field["value_strategy"] == "numeric_range_with_coded_choices"
    assert education_age_field["special_code_policy"] == "include"

    medicat_field = field_registry[field_registry["name"] == "MEDICAT_1_M"].iloc[0]
    assert bool(medicat_field["in_questionnaire_logic"])
    assert medicat_field["logic_sections"] == "4. Corrupted header section"
    assert medicat_field["coding_found"]
    assert medicat_field["generation_action"] == "generate"
    assert medicat_field["v2_inclusion_status"] == "v2_questionnaire_field"
    assert medicat_field["value_strategy"] == "coded_multi_select"

    dict_only_field = field_registry[field_registry["name"] == "DICT_ONLY_1_1"].iloc[0]
    assert not bool(dict_only_field["in_questionnaire_logic"])
    assert dict_only_field["coding_found"]
    assert dict_only_field["generation_action"] == "blank"
    assert dict_only_field["v2_inclusion_status"] == "not_in_v2_logic"
    assert dict_only_field["blank_reason"] == "not_in_v2_logic"
    assert dict_only_field["value_strategy"] == "blank"

    questionnaire_entity = entity_registry[entity_registry["entity"] == "questionnaire"].iloc[0]
    assert questionnaire_entity["generated_field_count"] == 4
    assert questionnaire_entity["blank_field_count"] == 2

    special_code = coding_registry[coding_registry["code"] == -1].iloc[0]
    assert bool(special_code["is_special_code"])
    none_meaning = coding_registry[coding_registry["code"] == 3].iloc[0]
    assert none_meaning["meaning"] == "None"

    normalised_logic = logic_registry[logic_registry["field_name"] == "MEDICAT_1_M"].iloc[0]
    assert bool(normalised_logic["dictionary_match"])
    assert "eb" not in set(logic_registry["field_name"])
    assert "`eb`" not in coverage_summary

    manifest_files = {entry["role"]: entry for entry in source_manifest["files"]}
    assert set(manifest_files) == {
        "questionnaire_logic",
        "data_dictionary",
        "codings",
    }
    assert manifest_files["questionnaire_logic"]["exists"]
    assert manifest_files["questionnaire_logic"]["sha256"]


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
            {
                "entity": "questionnaire",
                "name": "EDU_COMP_AGE_2_1",
                "type": "integer",
                "primary_key_type": "",
                "coding_name": "EDU_COMP_AGE_2_1",
                "is_sparse_coding": "",
                "is_multi_select": False,
                "referenced_entity_field": "",
                "relationship": "",
                "folder_path": "Questionnaire",
                "title": "Education completion age",
                "units": "",
                "description": "Age completed continuous full-time education",
            },
            {
                "entity": "questionnaire",
                "name": "MEDICAT_1_M",
                "type": "integer",
                "primary_key_type": "",
                "coding_name": "MEDICAT_1_M",
                "is_sparse_coding": "",
                "is_multi_select": True,
                "referenced_entity_field": "",
                "relationship": "",
                "folder_path": "Questionnaire",
                "title": "Medication reasons",
                "units": "",
                "description": "Medication reasons",
            },
            {
                "entity": "questionnaire",
                "name": "DICT_ONLY_1_1",
                "type": "integer",
                "primary_key_type": "",
                "coding_name": "DICT_ONLY_1_1",
                "is_sparse_coding": "",
                "is_multi_select": False,
                "referenced_entity_field": "",
                "relationship": "",
                "folder_path": "Questionnaire",
                "title": "Dictionary only",
                "units": "",
                "description": "Coding-backed field absent from questionnaire logic",
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
    questionnaire = pd.DataFrame(
        [
            {
                "coding_name": "MEDICAT_1_M",
                "code": 1,
                "meaning": "Autoimmune disorder",
                "display_order": 1,
                "parent_code": "",
            },
            {
                "coding_name": "MEDICAT_1_M",
                "code": -7,
                "meaning": "None of the above",
                "display_order": 2,
                "parent_code": "",
            },
            {
                "coding_name": "DICT_ONLY_1_1",
                "code": 1,
                "meaning": "Yes",
                "display_order": 1,
                "parent_code": "",
            },
            {
                "coding_name": "DICT_ONLY_1_1",
                "code": -1,
                "meaning": "Do not know",
                "display_order": 2,
                "parent_code": "",
            },
            {
                "coding_name": "EDU_COMP_AGE_2_1",
                "code": 0,
                "meaning": "Still in full time education",
                "display_order": 1,
                "parent_code": "",
            },
            {
                "coding_name": "EDU_COMP_AGE_2_1",
                "code": -2,
                "meaning": "Never went to school",
                "display_order": 2,
                "parent_code": "",
            },
            {
                "coding_name": "EDU_COMP_AGE_2_1",
                "code": -1,
                "meaning": "Do not know",
                "display_order": 3,
                "parent_code": "",
            },
            {
                "coding_name": "EDU_COMP_AGE_2_1",
                "code": -3,
                "meaning": "Prefer not to answer",
                "display_order": 4,
                "parent_code": "",
            },
        ],
    )

    with pd.ExcelWriter(path) as writer:
        participant.to_excel(writer, sheet_name="participant", index=False)
        questionnaire.to_excel(writer, sheet_name="questionnaire", index=False)


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
                "question_text": "Education completion age",
                "source": "",
                "template_type": "radioAndInput",
                "field_name": "EDU_COMP_AGE_2_1",
                "question_type": "core",
                "show_if": "",
            },
            {
                "index": 4,
                "sectio+B1:H59n": "4. Corrupted header section",
                "question_text": (
                    "Do you regularly take medications for any of the following reasons?"
                ),
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
