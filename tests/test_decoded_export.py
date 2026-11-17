from pathlib import Path

import pandas as pd

from ofh_synthetic_data.config import AppConfig, PathsConfig
from ofh_synthetic_data.export.decoded import decode_table, write_decoded_outputs


def test_decode_table_replaces_coded_values_with_meanings() -> None:
    table = pd.DataFrame(
        [
            {
                "PID": "SYN-000000000001",
                "DEMOG_SEX_2_1": "1",
                "ACTIVITY_TRANSPORT_1_M": "[1,6,-3]",
                "UNCODED_FIELD": "7",
                "UNKNOWN_CODE": "999",
                "BLANK_MEANING_CODE": "0",
                "NONE_MEANING_CODE": "1",
            },
        ],
    )
    fields = pd.DataFrame(
        [
            _field("PID", ""),
            _field("DEMOG_SEX_2_1", "DEMOG_SEX_2_1"),
            _field("ACTIVITY_TRANSPORT_1_M", "ACTIVITY_TRANSPORT_1_M", is_multi_select=True),
            _field("UNCODED_FIELD", ""),
            _field("UNKNOWN_CODE", "DEMOG_SEX_2_1"),
            _field("BLANK_MEANING_CODE", "ACTIVITY_STAIRS_1_1"),
            _field("NONE_MEANING_CODE", "HOUSING_VEHICLES_1_1"),
        ],
    )
    coding_lookup = {
        "DEMOG_SEX_2_1": {
            "1": "Female",
            "2": "Male",
            "-1": "Prefer not to say",
        },
        "ACTIVITY_TRANSPORT_1_M": {
            "1": "Walk",
            "6": "Cycle",
            "-3": "None of the above",
        },
        "ACTIVITY_STAIRS_1_1": {
            "0": "Code 0 (meaning unavailable)",
            "1": "One flight",
        },
        "HOUSING_VEHICLES_1_1": {
            "1": "None",
            "2": "One",
        },
    }

    decoded, summary = decode_table(table, fields, coding_lookup)

    assert decoded.loc[0, "PID"] == "SYN-000000000001"
    assert decoded.loc[0, "DEMOG_SEX_2_1"] == "Female"
    assert decoded.loc[0, "ACTIVITY_TRANSPORT_1_M"] == "Walk; Cycle; None of the above"
    assert decoded.loc[0, "UNCODED_FIELD"] == "7"
    assert decoded.loc[0, "UNKNOWN_CODE"] == "999"
    assert decoded.loc[0, "BLANK_MEANING_CODE"] == "Code 0 (meaning unavailable)"
    assert decoded.loc[0, "NONE_MEANING_CODE"] == "None"
    assert summary.decoded_columns == 4
    assert summary.decoded_values == 4


def test_write_decoded_outputs_writes_manual_qa_files(tmp_path: Path) -> None:
    processed_dir = tmp_path / "processed"
    synthetic_dir = tmp_path / "synthetic"
    qa_dir = tmp_path / "qa"
    processed_dir.mkdir()
    synthetic_dir.mkdir()

    pd.DataFrame(
        [
            _registry_field("participant", "PID", ""),
            _registry_field("participant", "DEMOG_SEX_2_1", "DEMOG_SEX_2_1"),
            _registry_field("questionnaire", "ID", ""),
            _registry_field("questionnaire", "PID", ""),
            _registry_field(
                "questionnaire",
                "ACTIVITY_TRANSPORT_1_M",
                "ACTIVITY_TRANSPORT_1_M",
                is_multi_select=True,
            ),
            _registry_field("questionnaire", "ACTIVITY_STAIRS_1_1", "ACTIVITY_STAIRS_1_1"),
            _registry_field(
                "questionnaire",
                "HOUSING_VEHICLES_1_1",
                "HOUSING_VEHICLES_1_1",
            ),
        ],
    ).to_csv(processed_dir / "field_registry.csv", index=False)
    pd.DataFrame(
        [
            _code("DEMOG_SEX_2_1", 1, "Female"),
            _code("ACTIVITY_TRANSPORT_1_M", 1, "Walk"),
            _code("ACTIVITY_TRANSPORT_1_M", 6, "Cycle"),
            _code("ACTIVITY_STAIRS_1_1", 0, ""),
            _code("HOUSING_VEHICLES_1_1", 1, "None"),
        ],
    ).to_csv(processed_dir / "coding_registry.csv", index=False)
    pd.DataFrame(
        [{"PID": "SYN-000000000001", "DEMOG_SEX_2_1": "1"}],
    ).to_csv(synthetic_dir / "participant.csv", index=False)
    pd.DataFrame(
        [
            {
                "ID": "SYN-ID-000000000001",
                "PID": "SYN-000000000001",
                "ACTIVITY_TRANSPORT_1_M": "[1,6]",
                "ACTIVITY_STAIRS_1_1": "0",
                "HOUSING_VEHICLES_1_1": "1",
            },
        ],
    ).to_csv(synthetic_dir / "questionnaire.csv", index=False)

    config = AppConfig(
        paths=PathsConfig(
            processed_data_dir=processed_dir,
            synthetic_data_dir=synthetic_dir,
            qa_dir=qa_dir,
        ),
    )

    paths = write_decoded_outputs(config)

    decoded_participants = pd.read_csv(paths.participant, dtype=object, keep_default_na=False)
    decoded_questionnaires = pd.read_csv(
        paths.questionnaire,
        dtype=object,
        keep_default_na=False,
    )

    assert decoded_participants.loc[0, "DEMOG_SEX_2_1"] == "Female"
    assert decoded_questionnaires.loc[0, "ACTIVITY_TRANSPORT_1_M"] == "Walk; Cycle"
    assert decoded_questionnaires.loc[0, "ACTIVITY_STAIRS_1_1"] == (
        "Code 0 (meaning unavailable)"
    )
    assert decoded_questionnaires.loc[0, "HOUSING_VEHICLES_1_1"] == "None"
    assert paths.manifest.exists()


def _field(
    name: str,
    coding_name: str,
    *,
    is_multi_select: bool = False,
) -> dict[str, object]:
    return {
        "name": name,
        "coding_name": coding_name,
        "is_multi_select": is_multi_select,
    }


def _registry_field(
    entity: str,
    name: str,
    coding_name: str,
    *,
    is_multi_select: bool = False,
) -> dict[str, object]:
    return {
        "dictionary_order": 0,
        "entity": entity,
        "name": name,
        "coding_name": coding_name,
        "is_multi_select": is_multi_select,
    }


def _code(coding_name: str, code: int, meaning: str) -> dict[str, object]:
    return {
        "coding_name": coding_name,
        "code": code,
        "meaning": meaning,
    }
