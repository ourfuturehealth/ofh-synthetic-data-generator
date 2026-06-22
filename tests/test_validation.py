from pathlib import Path

import pandas as pd

from ofh_synthetic_data.config import AppConfig, GenerationConfig, PathsConfig
from ofh_synthetic_data.generate.registry_generator import generate_tables, write_generated_tables
from ofh_synthetic_data.validate.outputs import validate_synthetic_outputs


def test_validate_synthetic_outputs_passes_for_generated_tables(tmp_path: Path) -> None:
    config = _write_valid_fixture(tmp_path)

    result = validate_synthetic_outputs(config)

    assert result.passed
    assert result.checks_run > 0


def test_validate_synthetic_outputs_reports_blank_root_logic_fields(tmp_path: Path) -> None:
    config = _write_valid_fixture(tmp_path)
    synthetic_dir = config.paths.synthetic_data_dir

    questionnaires = pd.read_csv(synthetic_dir / "questionnaire.csv", dtype=object)
    questionnaires.loc[0, "TRIGGER_1_1"] = ""
    questionnaires.to_csv(synthetic_dir / "questionnaire.csv", index=False)

    result = validate_synthetic_outputs(config)

    assert not result.passed
    assert any(error.check == "root_logic" for error in result.errors)


def test_validate_synthetic_outputs_reports_data_errors(tmp_path: Path) -> None:
    config = _write_valid_fixture(tmp_path)
    synthetic_dir = config.paths.synthetic_data_dir

    participants = pd.read_csv(synthetic_dir / "participant.csv", dtype=object)
    participants.loc[0, "DEMOG_SEX_2_1"] = "999"
    participants.to_csv(synthetic_dir / "participant.csv", index=False)

    questionnaires = pd.read_csv(synthetic_dir / "questionnaire.csv", dtype=object)
    questionnaires.loc[0, "HIDDEN_CHILD_1_1"] = "9"
    questionnaires.loc[1, "PID"] = "SYN-999999999999"
    questionnaires.to_csv(synthetic_dir / "questionnaire.csv", index=False)

    result = validate_synthetic_outputs(config)

    assert not result.passed
    checks = {error.check for error in result.errors}
    assert "coded_values" in checks
    assert "pid_links" in checks
    assert "source_logic" in checks


def test_validate_synthetic_outputs_reports_type_errors(tmp_path: Path) -> None:
    config = _write_valid_fixture(tmp_path)
    synthetic_dir = config.paths.synthetic_data_dir

    participants = pd.read_csv(synthetic_dir / "participant.csv", dtype=object)
    participants.loc[0, "BIRTH_YEAR"] = "not-a-year"
    participants.to_csv(synthetic_dir / "participant.csv", index=False)

    questionnaires = pd.read_csv(synthetic_dir / "questionnaire.csv", dtype=object)
    questionnaires.loc[0, "SUBMISSION_DATE"] = "not-a-date"
    questionnaires.loc[0, "TRIGGER_1_1"] = "1.5"
    questionnaires.to_csv(synthetic_dir / "questionnaire.csv", index=False)

    result = validate_synthetic_outputs(config)

    assert not result.passed
    type_messages = [error.message for error in result.errors if error.check == "types"]
    assert any("BIRTH_YEAR" in message and "non-numeric" in message for message in type_messages)
    assert any(
        "TRIGGER_1_1" in message and "non-integer" in message
        for message in type_messages
    )
    assert any(
        "SUBMISSION_DATE" in message and "invalid date" in message
        for message in type_messages
    )


def _write_valid_fixture(tmp_path: Path) -> AppConfig:
    processed_dir = tmp_path / "processed"
    synthetic_dir = tmp_path / "synthetic"
    processed_dir.mkdir()
    synthetic_dir.mkdir()

    field_registry = pd.DataFrame(
        [
            _field(
                "participant",
                "PID",
                "string",
                "synthetic_identifier",
                dictionary_order=0,
                primary_key_type="global",
            ),
            _field(
                "participant",
                "DEMOG_SEX_2_1",
                "integer",
                "coded_single",
                coding_name="DEMOG_SEX_2_1",
                dictionary_order=1,
            ),
            _field(
                "participant",
                "BIRTH_YEAR",
                "integer",
                "numeric_range",
                generation_min=3000,
                generation_max=3075,
                numeric_range_rule="birth_year",
                dictionary_order=2,
            ),
            _field(
                "questionnaire",
                "ID",
                "string",
                "synthetic_identifier",
                dictionary_order=3,
                primary_key_type="local",
            ),
            _field(
                "questionnaire",
                "PID",
                "string",
                "synthetic_identifier",
                dictionary_order=4,
            ),
            _field(
                "questionnaire",
                "QUESTIONNAIRE_VERSION",
                "string",
                "constant_questionnaire_version",
                dictionary_order=5,
            ),
            _field(
                "questionnaire",
                "SUBMISSION_DATE",
                "date",
                "synthetic_future_date",
                dictionary_order=6,
            ),
            _field(
                "questionnaire",
                "TRIGGER_1_1",
                "integer",
                "numeric_range",
                generation_min=1,
                generation_max=1,
                dictionary_order=7,
            ),
            _field(
                "questionnaire",
                "HIDDEN_CHILD_1_1",
                "integer",
                "numeric_range",
                generation_min=9,
                generation_max=9,
                dictionary_order=8,
            ),
            _field(
                "questionnaire",
                "OLD_FIELD_1_1",
                "integer",
                "blank",
                dictionary_order=9,
            ),
        ],
    )
    coding_registry = pd.DataFrame(
        [
            _code("DEMOG_SEX_2_1", 1, False),
            _code("DEMOG_SEX_2_1", 2, False),
            _code("DEMOG_SEX_2_1", -1, True),
        ],
    )
    logic_registry = pd.DataFrame(
        [
            _logic("TRIGGER_1_1", ""),
            _logic("HIDDEN_CHILD_1_1", "([TRIGGER_1_1] = 2)"),
        ],
    )

    field_registry.to_csv(processed_dir / "field_registry.csv", index=False)
    coding_registry.to_csv(processed_dir / "coding_registry.csv", index=False)
    logic_registry.to_csv(processed_dir / "logic_registry.csv", index=False)

    generation_config = GenerationConfig(rows=2, seed=3)
    config = AppConfig(
        paths=PathsConfig(processed_data_dir=processed_dir, synthetic_data_dir=synthetic_dir),
        generation=generation_config,
    )
    tables = generate_tables(
        field_registry=field_registry,
        coding_registry=coding_registry,
        logic_registry=logic_registry,
        generation_config=generation_config,
    )
    write_generated_tables(tables, synthetic_dir, generation_config)

    return config


def _field(
    entity: str,
    name: str,
    field_type: str,
    value_strategy: str,
    *,
    dictionary_order: int,
    primary_key_type: str = "",
    coding_name: str = "",
    generation_min: int | str = "",
    generation_max: int | str = "",
    numeric_range_rule: str = "",
) -> dict[str, object]:
    return {
        "dictionary_order": dictionary_order,
        "entity": entity,
        "name": name,
        "type": field_type,
        "primary_key_type": primary_key_type,
        "coding_name": coding_name,
        "is_multi_select": False,
        "title": f"{name} title",
        "description": f"{name} description",
        "generation_action": "blank" if value_strategy == "blank" else "generate",
        "value_strategy": value_strategy,
        "generation_min": generation_min,
        "generation_max": generation_max,
        "numeric_range_rule": numeric_range_rule,
    }


def _code(coding_name: str, code: int, is_special_code: bool) -> dict[str, object]:
    return {
        "coding_name": coding_name,
        "code": code,
        "is_special_code": is_special_code,
    }


def _logic(field_name: str, show_if: str) -> dict[str, object]:
    return {
        "field_name": field_name,
        "show_if": show_if,
        "question_text": f"{field_name} question text",
    }
