from pathlib import Path

import pandas as pd

from ofh_synthetic_data.config import GenerationConfig
from ofh_synthetic_data.generate.registry_generator import generate_tables, write_generated_tables
from ofh_synthetic_data.generate.show_if import evaluate_show_if


def test_generate_tables_from_enriched_registry(tmp_path: Path) -> None:
    field_registry = pd.DataFrame(
        [
            _field("participant", "PID", "string", "synthetic_identifier"),
            _field(
                "participant",
                "REGISTRATION_YEAR",
                "integer",
                "numeric_range",
                generation_min=3095,
                generation_max=3100,
            ),
            _field(
                "participant",
                "REGISTRATION_MONTH",
                "integer",
                "numeric_range",
                generation_min=1,
                generation_max=12,
            ),
            _field("participant", "CONSENT_VERSION", "string", "synthetic_string"),
            _field(
                "participant",
                "CONSENT_YEAR",
                "integer",
                "numeric_range",
                generation_min=3095,
                generation_max=3100,
            ),
            _field(
                "participant",
                "CONSENT_MONTH",
                "integer",
                "numeric_range",
                generation_min=1,
                generation_max=12,
            ),
            _field(
                "participant",
                "BIRTH_YEAR",
                "integer",
                "numeric_range",
                generation_min=3000,
                generation_max=3075,
            ),
            _field(
                "participant",
                "BIRTH_MONTH",
                "integer",
                "numeric_range",
                generation_min=1,
                generation_max=12,
            ),
            _field("participant", "DEMOG_SEX_1_1", "integer", "blank"),
            _field(
                "participant",
                "DEMOG_SEX_2_1",
                "integer",
                "coded_single",
                coding_name="DEMOG_SEX_2_1",
            ),
            _field("questionnaire", "ID", "string", "synthetic_identifier"),
            _field("questionnaire", "PID", "string", "synthetic_identifier"),
            _field(
                "questionnaire",
                "QUESTIONNAIRE_VERSION",
                "string",
                "constant_questionnaire_version",
            ),
            _field("questionnaire", "SUBMISSION_DATE", "date", "synthetic_future_date"),
            _field("questionnaire", "ACTIVITY_WALK_DAYS_1_1", "integer", "blank"),
            _field(
                "questionnaire",
                "ACTIVITY_WALK_DAYS_2_1",
                "integer",
                "numeric_range",
                generation_min=0,
                generation_max=7,
            ),
            _field(
                "questionnaire",
                "ACTIVITY_TRANSPORT_1_M",
                "integer",
                "coded_multi_select",
                coding_name="ACTIVITY_TRANSPORT_1_M",
                multi_select_strategy="bracketed_comma_list",
            ),
        ],
    )
    coding_registry = pd.DataFrame(
        [
            _code("DEMOG_SEX_2_1", 1, False),
            _code("DEMOG_SEX_2_1", 2, False),
            _code("DEMOG_SEX_2_1", -1, True),
            _code("ACTIVITY_TRANSPORT_1_M", 1, False),
            _code("ACTIVITY_TRANSPORT_1_M", 2, False),
            _code("ACTIVITY_TRANSPORT_1_M", -3, True),
        ],
    )

    config = GenerationConfig(rows=3, seed=11)
    tables = generate_tables(field_registry, coding_registry, config)
    output_paths = write_generated_tables(tables, tmp_path, config)

    participants = pd.read_csv(output_paths.participant, dtype=object)
    questionnaires = pd.read_csv(output_paths.questionnaire, dtype=object)

    assert participants["PID"].tolist() == [
        "SYN-000000000001",
        "SYN-000000000002",
        "SYN-000000000003",
    ]
    assert participants["CONSENT_VERSION"].str.startswith("SYNTHETIC_CONSENT_VERSION_").all()
    assert questionnaires["PID"].tolist() == participants["PID"].tolist()
    assert questionnaires["ID"].str.startswith("SYN-ID-").all()
    assert questionnaires["QUESTIONNAIRE_VERSION"].eq("v2").all()
    submission_years = questionnaires["SUBMISSION_DATE"].str.slice(0, 4).astype(int)
    submission_months = questionnaires["SUBMISSION_DATE"].str.slice(5, 7).astype(int)
    registration_years = participants["REGISTRATION_YEAR"].astype(int)
    registration_months = participants["REGISTRATION_MONTH"].astype(int)
    consent_years = participants["CONSENT_YEAR"].astype(int)
    consent_months = participants["CONSENT_MONTH"].astype(int)
    birth_years = participants["BIRTH_YEAR"].astype(int)
    birth_months = participants["BIRTH_MONTH"].astype(int)

    assert registration_years.between(3095, 3100).all()
    assert birth_years.between(3000, 3075).all()
    assert registration_years.tolist() == consent_years.tolist()
    assert registration_months.tolist() == consent_months.tolist()
    assert registration_years.tolist() == submission_years.tolist()
    assert registration_months.tolist() == submission_months.tolist()
    age_months = (submission_years - birth_years) * 12 + (submission_months - birth_months)
    assert age_months.ge(18 * 12).all()
    assert participants["DEMOG_SEX_1_1"].isna().all()
    assert questionnaires["ACTIVITY_WALK_DAYS_1_1"].isna().all()
    assert questionnaires["ACTIVITY_WALK_DAYS_2_1"].astype(int).between(0, 7).all()
    assert questionnaires["ACTIVITY_TRANSPORT_1_M"].str.match(r"^\[[0-9,]+\]$").all()
    assert tables.manifest["status"] == "beta"
    assert tables.manifest["manual_validation_status"] == "ongoing"
    assert tables.manifest["config"]["generation"]["rows"] == 3
    assert tables.manifest["synthetic_markers"]["synthetic_string_prefix"] == "SYNTHETIC"
    assert tables.manifest["synthetic_markers"]["synthetic_string_fields"] == [
        "CONSENT_VERSION"
    ]
    assert tables.manifest["phase"] == "7-beta-release-candidate"


def test_generate_tables_orders_columns_by_dictionary_order() -> None:
    field_registry = pd.DataFrame(
        [
            _field(
                "participant",
                "REGISTRATION_YEAR",
                "integer",
                "numeric_range",
                generation_min=3000,
                generation_max=3000,
                dictionary_order=2,
            ),
            _field(
                "questionnaire",
                "SUBMISSION_DATE",
                "date",
                "synthetic_future_date",
                dictionary_order=5,
            ),
            _field(
                "questionnaire",
                "QUESTIONNAIRE_VERSION",
                "string",
                "constant_questionnaire_version",
                dictionary_order=4,
            ),
            _field("participant", "PID", "string", "synthetic_identifier", dictionary_order=1),
            _field("questionnaire", "PID", "string", "synthetic_identifier", dictionary_order=3),
            _field("questionnaire", "ID", "string", "synthetic_identifier", dictionary_order=0),
        ],
    )
    coding_registry = pd.DataFrame(columns=["coding_name", "code", "is_special_code"])

    tables = generate_tables(
        field_registry=field_registry,
        coding_registry=coding_registry,
        generation_config=GenerationConfig(rows=1, seed=1),
    )

    assert tables.participant_columns == ["PID", "REGISTRATION_YEAR"]
    assert tables.questionnaire_columns == [
        "ID",
        "PID",
        "QUESTIONNAIRE_VERSION",
        "SUBMISSION_DATE",
    ]
    assert tables.manifest["column_order"]["source"] == "data_dictionary"


def test_generate_tables_excludes_suppression_codes() -> None:
    field_registry = pd.DataFrame(
        [
            _field("participant", "PID", "string", "synthetic_identifier"),
            _field("questionnaire", "ID", "string", "synthetic_identifier"),
            _field("questionnaire", "PID", "string", "synthetic_identifier"),
            _field(
                "questionnaire",
                "SINGLE_1_1",
                "integer",
                "coded_single",
                coding_name="SINGLE_1_1",
                special_code_policy="include",
                special_code_probability=1.0,
            ),
            _field(
                "questionnaire",
                "SPECIAL_SINGLE_1_1",
                "integer",
                "coded_single",
                coding_name="SPECIAL_SINGLE_1_1",
                special_code_policy="include",
                special_code_probability=1.0,
            ),
            _field(
                "questionnaire",
                "MULTI_1_M",
                "integer",
                "coded_multi_select",
                coding_name="MULTI_1_M",
                special_code_policy="include",
                special_code_probability=1.0,
            ),
            _field(
                "questionnaire",
                "NUMBER_1_1",
                "integer",
                "numeric_range_with_special_codes",
                coding_name="NUMBER_1_1",
                generation_min=10,
                generation_max=10,
                special_code_policy="include",
                special_code_probability=1.0,
            ),
        ],
    )
    coding_registry = pd.DataFrame(
        [
            _code("SINGLE_1_1", 1, False),
            _code("SINGLE_1_1", -999, True),
            _code("SPECIAL_SINGLE_1_1", 1, False),
            _code("SPECIAL_SINGLE_1_1", -1, True),
            _code("SPECIAL_SINGLE_1_1", -999, True),
            _code("MULTI_1_M", 1, False),
            _code("MULTI_1_M", 2, False),
            _code("MULTI_1_M", -999, True),
            _code("NUMBER_1_1", -999, True),
        ],
    )

    tables = generate_tables(
        field_registry=field_registry,
        coding_registry=coding_registry,
        generation_config=GenerationConfig(rows=1, seed=1),
    )

    questionnaire = tables.questionnaires[0]
    assert questionnaire["SINGLE_1_1"] == "1"
    assert questionnaire["SPECIAL_SINGLE_1_1"] == "-1"
    assert questionnaire["MULTI_1_M"] in {"[1]", "[2]", "[1,2]", "[2,1]"}
    assert questionnaire["NUMBER_1_1"] == 10
    assert "-999" not in {str(value) for value in questionnaire.values()}


def test_generate_tables_supports_numeric_ranges_with_coded_choices() -> None:
    field_registry = pd.DataFrame(
        [
            _field("participant", "PID", "string", "synthetic_identifier"),
            _field("questionnaire", "ID", "string", "synthetic_identifier"),
            _field("questionnaire", "PID", "string", "synthetic_identifier"),
            _field(
                "questionnaire",
                "AGE_VALUE_1_1",
                "integer",
                "numeric_range_with_coded_choices",
                coding_name="AGE_VALUE_1_1",
                generation_min=42,
                generation_max=42,
                special_code_policy="include",
                special_code_probability=0.0,
            ),
            _field(
                "questionnaire",
                "AGE_CODE_1_1",
                "integer",
                "numeric_range_with_coded_choices",
                coding_name="AGE_CODE_1_1",
                generation_min=42,
                generation_max=42,
                special_code_policy="include",
                special_code_probability=1.0,
            ),
        ],
    )
    coding_registry = pd.DataFrame(
        [
            _code("AGE_VALUE_1_1", 0, False),
            _code("AGE_VALUE_1_1", -1, True),
            _code("AGE_CODE_1_1", 0, False),
            _code("AGE_CODE_1_1", -1, True),
            _code("AGE_CODE_1_1", -999, True),
        ],
    )

    tables = generate_tables(
        field_registry=field_registry,
        coding_registry=coding_registry,
        generation_config=GenerationConfig(rows=1, seed=1),
    )

    questionnaire = tables.questionnaires[0]
    assert questionnaire["AGE_VALUE_1_1"] == 42
    assert str(questionnaire["AGE_CODE_1_1"]) in {"0", "-1"}
    assert questionnaire["AGE_CODE_1_1"] != "-999"


def test_show_if_evaluator_supports_expected_forms() -> None:
    context = {
        "SEX": "1",
        "DAYS": "5",
        "MULTI": "[1,6]",
        "KNOWN": "value",
        "BLANK": "",
    }

    assert evaluate_show_if("([SEX] = 1)", context)
    assert evaluate_show_if("([SEX] ONE of [2, 1])", context)
    assert evaluate_show_if("([DAYS] ONE of [int(>=0 & <=7), -1, -3])", context)
    assert evaluate_show_if("([MULTI] ANY of [6, 9])", context)
    assert evaluate_show_if("([KNOWN] is NOT NULL)", context)
    assert evaluate_show_if("([BLANK] = NULL)", context)
    assert evaluate_show_if("([SEX] = 1) AND ([MULTI] ANY of [6])", context)
    assert evaluate_show_if("([SEX] = 2) OR ([MULTI] ANY of [6])", context)
    assert evaluate_show_if("([SEX] = 1))", context)
    assert not evaluate_show_if("([SEX] = 2)", context)
    assert not evaluate_show_if("([MULTI] ANY of [3, 4])", context)


def test_generate_tables_applies_questionnaire_logic() -> None:
    field_registry = pd.DataFrame(
        [
            _field("participant", "PID", "string", "synthetic_identifier"),
            _field("questionnaire", "ID", "string", "synthetic_identifier"),
            _field("questionnaire", "PID", "string", "synthetic_identifier"),
            _field(
                "questionnaire",
                "TRIGGER_1_1",
                "integer",
                "numeric_range",
                generation_min=1,
                generation_max=1,
            ),
            _field(
                "questionnaire",
                "HIDDEN_CHILD_1_1",
                "integer",
                "numeric_range",
                generation_min=9,
                generation_max=9,
            ),
            _field(
                "questionnaire",
                "DUPLICATE_OR_CHILD_1_1",
                "integer",
                "numeric_range",
                generation_min=7,
                generation_max=7,
            ),
        ],
    )
    coding_registry = pd.DataFrame(columns=["coding_name", "code", "is_special_code"])
    logic_registry = pd.DataFrame(
        [
            _logic("TRIGGER_1_1", ""),
            _logic("HIDDEN_CHILD_1_1", "([TRIGGER_1_1] = 2)"),
            _logic("DUPLICATE_OR_CHILD_1_1", "([TRIGGER_1_1] = 2)"),
            _logic("DUPLICATE_OR_CHILD_1_1", "([TRIGGER_1_1] = 1)"),
        ],
    )

    tables = generate_tables(
        field_registry=field_registry,
        coding_registry=coding_registry,
        logic_registry=logic_registry,
        generation_config=GenerationConfig(rows=1, seed=1),
    )

    questionnaire = tables.questionnaires[0]
    assert questionnaire["TRIGGER_1_1"] == 1
    assert questionnaire["HIDDEN_CHILD_1_1"] == ""
    assert questionnaire["DUPLICATE_OR_CHILD_1_1"] == 7
    assert tables.skipped_by_logic_count == 1
    assert tables.manifest["questionnaire_logic"]["applied"]
    assert tables.manifest["questionnaire_logic"]["skipped_values"] == 1


def _field(
    entity: str,
    name: str,
    field_type: str,
    value_strategy: str,
    *,
    coding_name: str = "",
    generation_min: int | str = "",
    generation_max: int | str = "",
    special_code_policy: str = "exclude",
    special_code_probability: float = 0.0,
    multi_select_strategy: str = "not_applicable",
    dictionary_order: int | str = "",
) -> dict[str, object]:
    return {
        "dictionary_order": dictionary_order,
        "entity": entity,
        "name": name,
        "type": field_type,
        "generation_action": "blank" if value_strategy == "blank" else "generate",
        "value_strategy": value_strategy,
        "coding_name": coding_name,
        "generation_min": generation_min,
        "generation_max": generation_max,
        "special_code_policy": special_code_policy,
        "special_code_probability": special_code_probability,
        "multi_select_strategy": multi_select_strategy,
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
    }
