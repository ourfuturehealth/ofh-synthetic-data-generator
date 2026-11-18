import json
from contextlib import ExitStack
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
from unittest.mock import Mock, call, patch

import pandas as pd

from ofh_synthetic_data.config import GenerationConfig
from ofh_synthetic_data.generate import registry_generator as generator
from ofh_synthetic_data.generate.registry_generator import generate_tables, write_generated_tables
from ofh_synthetic_data.generate.show_if import evaluate_show_if
from ofh_synthetic_data.synthetic_ranges import *


LINKED_DATASETS = {
    "deaths": ("nhse_engwal_deaths", "REG_DATE_OF_DEATH"),
    "op": ("nhse_eng_outpat", "APPTDATE"),
    "ae": ("nhse_eng_ed", "ARRIVALDATE"),
    "apc": ("nhse_eng_inpat", "ADMIDATE"),
}


def test_generate_tables_from_enriched_registry(tmp_path: Path) -> None:
    field_registry = pd.DataFrame(
        [
            _field("participant", "PID", "string", "synthetic_identifier"),
            _field(
                "participant",
                "REGISTRATION_YEAR",
                "integer",
                "numeric_range",
                generation_min=SYNTHETIC_YEAR_MIN,
                generation_max=SYNTHETIC_YEAR_MAX,
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
                generation_min=SYNTHETIC_YEAR_MIN,
                generation_max=SYNTHETIC_YEAR_MAX,
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
                generation_min=BIRTH_YEAR_MIN,
                generation_max=BIRTH_YEAR_MAX,
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
    with ExitStack() as patches:
        fake = _linked_data_dependencies(patches)
        tables = generate_tables(field_registry, coding_registry, config, linked_data_dir=fake.linked_data_dir)
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

    assert registration_years.between(SYNTHETIC_YEAR_MIN, SYNTHETIC_YEAR_MAX).all()
    assert birth_years.between(BIRTH_YEAR_MIN, BIRTH_YEAR_MAX).all()
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
                generation_min=SYNTHETIC_YEAR_MIN,
                generation_max=SYNTHETIC_YEAR_MAX,
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

    with ExitStack() as patches:
        fake = _linked_data_dependencies(patches)
        tables = generate_tables(
            field_registry=field_registry,
            coding_registry=coding_registry,
            generation_config=GenerationConfig(rows=1, seed=1),
            linked_data_dir=fake.linked_data_dir,
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

    with ExitStack() as patches:
        fake = _linked_data_dependencies(patches)
        tables = generate_tables(
            field_registry=field_registry,
            coding_registry=coding_registry,
            generation_config=GenerationConfig(rows=1, seed=1),
            linked_data_dir=fake.linked_data_dir,
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

    with ExitStack() as patches:
        fake = _linked_data_dependencies(patches)
        tables = generate_tables(
            field_registry=field_registry,
            coding_registry=coding_registry,
            generation_config=GenerationConfig(rows=1, seed=1),
            linked_data_dir=fake.linked_data_dir,
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

    with ExitStack() as patches:
        fake = _linked_data_dependencies(patches)
        tables = generate_tables(
            field_registry=field_registry,
            coding_registry=coding_registry,
            logic_registry=logic_registry,
            generation_config=GenerationConfig(rows=1, seed=1),
            linked_data_dir=fake.linked_data_dir,
        )

    questionnaire = tables.questionnaires[0]
    assert questionnaire["TRIGGER_1_1"] == 1
    assert questionnaire["HIDDEN_CHILD_1_1"] == ""
    assert questionnaire["DUPLICATE_OR_CHILD_1_1"] == 7
    assert tables.skipped_by_logic_count == 1
    assert tables.manifest["questionnaire_logic"]["applied"]
    assert tables.manifest["questionnaire_logic"]["skipped_values"] == 1


def test_generate_tables_from_processed_registries_reads_inputs(tmp_path: Path) -> None:
    field_registry, coding_registry = _minimal_registries()
    logic_registry = pd.DataFrame([_logic("PID", "")])
    registries = {
        "field_registry": field_registry,
        "coding_registry": coding_registry,
        "logic_registry": logic_registry,
    }
    for name, registry in registries.items():
        registry.to_csv(tmp_path / f"{name}.csv", index=False)
    source_manifest = {"source": "test-fixture"}
    (tmp_path / "source_manifest.json").write_text(
        json.dumps(source_manifest), encoding="utf-8",
    )
    generation = GenerationConfig(rows=2, seed=11)
    snapshot = {"generation": {"rows": 2, "seed": 11}}
    config = SimpleNamespace(
        paths=SimpleNamespace(
            processed_data_dir=tmp_path,
            linked_data_dir=tmp_path / "linked-data",
        ),
        generation=generation,
        to_dict=Mock(return_value=snapshot),
    )

    with patch.object(generator, "generate_tables") as generate:
        tables = generator.generate_tables_from_processed_registries(config)

    assert tables is generate.return_value
    generate.assert_called_once()
    arguments = generate.call_args.kwargs
    for name in registries:
        expected = pd.read_csv(
            tmp_path / f"{name}.csv", dtype=object, keep_default_na=False,
        )
        pd.testing.assert_frame_equal(arguments[name], expected)
    assert arguments["generation_config"] is generation
    assert arguments["config_snapshot"] == snapshot
    assert arguments["source_manifest"] == source_manifest
    assert arguments["linked_data_dir"] == config.paths.linked_data_dir


def test_generate_tables_uses_configured_linked_data_directory(tmp_path: Path) -> None:
    linked_data_dir = tmp_path / "custom-linked-data"
    with ExitStack() as patches:
        _linked_data_dependencies(patches, linked_data_dir)
        field_registry, coding_registry = _minimal_registries()
        tables = generate_tables(
            field_registry=field_registry,
            coding_registry=coding_registry,
            generation_config=GenerationConfig(rows=0, seed=11),
            linked_data_dir=linked_data_dir,
        )

        datasets = sorted(dataset for dataset, _ in LINKED_DATASETS.values())
        assert generator.get_dictionaries.call_args_list == [
            call(path=str(linked_data_dir) + "/", df_name=dataset)
            for dataset in datasets
        ]
        assert sorted(tables.linked_data_columns) == datasets
        assert tables.participants == []
        assert tables.questionnaires == []
        for attribute in LINKED_DATASETS:
            assert getattr(tables, attribute) == []


def test_generate_tables_without_linked_events() -> None:
    with ExitStack() as patches:
        fake = _linked_data_dependencies(patches)
        fields, codes = _minimal_registries()
        tables = generate_tables(fields, codes, GenerationConfig(rows=2, seed=11), linked_data_dir=fake.linked_data_dir)

        for attribute, (dataset, date_column) in LINKED_DATASETS.items():
            assert getattr(tables, attribute) == []
            assert tables.linked_data_columns[dataset] == ["PID", date_column, "ROW_ID"]
            assert tables.manifest["column_order"][f"{attribute}_columns"] == 3
        assert len(tables.participants) == len(tables.questionnaires) == 2


def test_generate_tables_links_and_sorts_events() -> None:
    with ExitStack() as patches:
        fake = _linked_data_dependencies(patches)
        fake.pybool.return_value = True
        record_generators = {}
        for attribute, (_, date_column) in LINKED_DATASETS.items():
            def make_record(fake, *, pid, row_number, _date_column=date_column, **kwargs):
                return {
                    "PID": pid,
                    "ROW_ID": row_number,
                    _date_column: f"2020-01-{20 - row_number:02d}",
                }

            function = {
                "deaths": "_generate_death_record",
                "op": "_generate_outpatient_record",
                "ae": "_generate_ae_record",
                "apc": "_generate_apc_record",
            }[attribute]
            record_generators[attribute] = Mock(side_effect=make_record)
            patches.enter_context(patch.object(generator, function, record_generators[attribute]))

        fields, codes = _minimal_registries()
        config = GenerationConfig(rows=2, seed=11)
        tables = generate_tables(fields, codes, config, linked_data_dir=fake.linked_data_dir)
        participant_ids = {row["PID"] for row in tables.participants}

        for attribute, (dataset, date_column) in LINKED_DATASETS.items():
            records = getattr(tables, attribute)
            expected_count = 2 if attribute == "deaths" else 4
            assert len(records) == expected_count
            assert {row["PID"] for row in records} == participant_ids
            assert sorted(row["ROW_ID"] for row in records) == list(range(expected_count))
            if attribute != "deaths":
                assert [row[date_column] for row in records] == sorted(
                    row[date_column] for row in records
                )
            for call in record_generators[attribute].call_args_list:
                assert call.kwargs["date_fields"] == [date_column]
                assert call.kwargs["coded_pairs"] == {}
                assert call.kwargs["df_dict"]["dictionary"]["name"].tolist() == [
                    "PID", date_column, "ROW_ID"
                ]
                if attribute != "deaths":
                    assert call.kwargs["provider_codes"] == [123456, 654321]
            assert tables.manifest["outputs"][attribute] == getattr(config, f"{attribute}_file")
        assert [call.args[0] for call in fake.pybool.call_args_list] == [5, 75, 60, 70] * 2
        assert [call.kwargs["max"] for call in fake.random_int.call_args_list] == [7, 2, 3] * 2


def test_write_generated_tables_writes_all_outputs(tmp_path: Path) -> None:
    for rows in [0, 2]:
        with ExitStack() as patches:
            fake = _linked_data_dependencies(patches)
            fields, codes = _minimal_registries()
            config = GenerationConfig(rows=rows, seed=11)
            tables = generate_tables(fields, codes, config, linked_data_dir=fake.linked_data_dir)
            for attribute, (_, date_column) in LINKED_DATASETS.items():
                getattr(tables, attribute).extend(
                    {"PID": row["PID"], date_column: "2020-01-01", "ROW_ID": index}
                    for index, row in enumerate(tables.participants)
                )
            paths = write_generated_tables(tables, tmp_path, config)

            for attribute, (dataset, _) in LINKED_DATASETS.items():
                path = getattr(paths, attribute)
                assert path == tmp_path / getattr(config, f"{attribute}_file")
                records = pd.read_csv(path, dtype=object)
                assert records.columns.tolist() == tables.linked_data_columns[dataset]
                assert len(records) == rows
                assert records["PID"].tolist() == [row["PID"] for row in tables.participants]
                assert records["ROW_ID"].tolist() == [str(index) for index in range(rows)]
            manifest = json.loads(paths.manifest.read_text(encoding="utf-8"))
            assert paths.manifest == tmp_path / config.manifest_file
            assert manifest["output_files"] == {
                name: str(getattr(paths, name))
                for name in ("participant", "questionnaire", "deaths", "op", "ae", "apc")
            }
            assert manifest["outputs"] == tables.manifest["outputs"]


def test_generate_death_record_chains_causes_and_formats_dates() -> None:
    for populate in [False, True]:
        with ExitStack() as patches:
            fake = _record_dependencies(patches)
            fake.pybool.return_value = populate
            pairs = {name: "icd" for name in ("CAUSE_1", "CAUSE_2", "CAUSE_3", "UNDERLYING")}
            patches.enter_context(patch.object(
                generator,
                "order_numbered_columns",
                Mock(return_value={"CAUSE": ["CAUSE_1", "CAUSE_2", "CAUSE_3"]}),
            ))
            dates = ["REG_DATE_OF_DEATH", "REG_DATE"]
            record = generator._generate_death_record(
                fake, "SYN-1", {"icd": pd.DataFrame({"code": ["A01"]})}, 7, pairs, dates
            )

            assert record["PID"] == "SYN-1"
            assert record["ROW_ID"] == 7
            assert record["CAUSE_1"] == record["UNDERLYING"] == "A01"
            assert record["CAUSE_2"] == record["CAUSE_3"] == ("A01" if populate else "")
            death_date = date.fromisoformat(record["REG_DATE_OF_DEATH"])
            assert death_date <= date.fromisoformat(record["REG_DATE"]) <= death_date + timedelta(days=10)
            assert fake.date_between.call_args.kwargs == {
                "start_date": death_date, "end_date": death_date + timedelta(days=10)
            }


def test_generate_outpatient_record_date_dependent_fields() -> None:
    cases = [
        (date(2008, 3, 31), 12, 10, False),
        (date(2012, 3, 31), 12, 10, False),
        (date(2012, 4, 1), 12, 10, True),
        (date(2016, 4, 1), 12, 19, True),
        (date(2021, 3, 31), 12, 19, True),
        (date(2021, 4, 1), 19, 19, True),
    ]
    for appointment, attend_length, spell_length, has_rtt in cases:
        with ExitStack() as patches:
            fake = _record_dependencies(patches)
            patches.enter_context(patch.dict(
                generator.DATE_BOOKENDS,
                {"nhse_eng_outpat": {"start": appointment, "end": date(2025, 3, 31)}},
            ))
            pairs = {name: "codes" for name in (
                "DIAG_4_01", "DIAG_4_02", "OPERTN_01", "OPERTN_02", "RTTPERSTAT", "SUSSPELLID"
            )}
            dates = ["APPTDATE", "RTTPERSTART", "RTTPEREND"]
            record = generator._generate_outpatient_record(fake, "SYN-1", {}, 4, pairs, dates, [123456])

            assert record["PID"] == "SYN-1"
            assert record["ROW_ID"] == 4
            assert record["APPTDATE"] == appointment.isoformat()
            assert record["PROCODE3_OFH"] == 123456
            assert len(record["ATTENDKEY"]) == attend_length
            assert len(record["SUSSPELLID"]) == spell_length
            assert record["DIAG_4_01"] == record["OPERTN_01"] == "VALID"
            assert record["DIAG_4_02"] == record["OPERTN_02"] == ""
            if has_rtt:
                assert date.fromisoformat(record["RTTPERSTART"]) <= date.fromisoformat(record["RTTPEREND"])
                assert record["RTTPERSTAT"] == "VALID"
            else:
                assert all(record[name] == "" for name in ("RTTPERSTART", "RTTPEREND", "RTTPERSTAT"))


def test_generate_ae_record_dates_times_and_identifiers() -> None:
    cases = [
        (date(2013, 3, 31), 12, 10, False),
        (date(2013, 4, 1), 12, 10, True),
        (date(2016, 4, 1), 12, 19, True),
        (date(2021, 3, 31), 12, 19, True),
        (date(2021, 4, 1), 19, 19, True),
    ]
    for arrival, key_length, spell_length, has_episode in cases:
        with ExitStack() as patches:
            fake = _record_dependencies(patches)
            fake.pybool.side_effect = lambda probability: probability == 10
            patches.enter_context(patch.dict(
                generator.DATE_BOOKENDS,
                {"nhse_eng_ed": {"start": arrival, "end": date(2025, 3, 31)}},
            ))
            patches.enter_context(patch.object(
                generator,
                "order_numbered_columns",
                Mock(return_value={
                    "DIAG": ["DIAG_01", "DIAG_02"],
                    "INVEST": ["INVEST_01", "INVEST_02"],
                }),
            ))
            dictionary = {"dictionary": pd.DataFrame({"name": [
                "DIAG_01", "DIAG_02", "INVEST_01", "INVEST_02", "TREAT_01", "TREAT_02", "ARRIVALTIME"
            ]})}
            record = generator._generate_ae_record(
                fake, "SYN-1", dictionary, 8, {"SUSSPELLID": "codes"}, ["ARRIVALDATE"], [123456]
            )

            assert record["PID"] == "SYN-1"
            assert record["ROW_ID"] == 8
            assert record["ARRIVALDATE"] == arrival.isoformat()
            assert record["ARRIVALTIME"] == "0905"
            assert record["PROCODE3_OFH"] == 123456
            assert len(record["AEKEY"]) == key_length
            assert len(record["SUSSPELLID"]) == spell_length
            assert record["EPIKEY"] == ("1" * key_length if has_episode else "")
            assert record["DIAG_01"] == record["DIAG_02"] == "VALID"
            assert record["INVEST_01"] == record["INVEST_02"] == "VALID"
            assert record["TREAT_01"] == "12a"
            assert record["TREAT_02"] == ""


def test_generate_apc_record_dates_durations_and_procedures() -> None:
    for episode_start, has_rtt in [(date(2007, 3, 31), False), (date(2007, 4, 1), True)]:
        with ExitStack() as patches:
            fake = _record_dependencies(patches)
            episode_end = episode_start + timedelta(days=5)
            dates = ["EPISTART", "EPIEND", "ADMIDATE", "ELECDATE", "OPDATE_01", "OPDATE_02"]
            patches.enter_context(patch.object(
                generator,
                "generate_apc_dates",
                Mock(return_value={
                    "PID": "SYN-1",
                    "EPISTART": episode_start,
                    "EPIEND": episode_end,
                    "ADMIDATE": episode_start,
                    "ELECDATE": episode_start - timedelta(days=3),
                }),
            ))
            pairs = {name: "codes" for name in (
                "DIAG_4_01", "DIAG_4_02", "OPERTN_01", "OPERTN_02",
                "RTTPERSTAT", "ACSCFLAG", "OPERSTAT", "FIRSTREG"
            )}
            record = generator._generate_apc_record(fake, "SYN-1", {}, 6, pairs, dates, [123456])

            assert record["PID"] == "SYN-1"
            assert record["ROW_ID"] == 6
            assert record["PROCODE3_OFH"] == 123456
            assert record["EPIORDER"] == 1
            assert record["ELECDUR"] == 3
            assert record["EPIDUR"] == 5
            assert record["PREOPDUR"] == 0
            assert record["POSOPDUR"] == 5
            assert 1 <= record["BEDYEAR"] <= 366
            assert record["DIAG_4_01"] == record["OPERTN_01"] == "VALID"
            assert record["DIAG_4_02"] == record["OPERTN_02"] == record["OPDATE_02"] == ""
            assert record["RTTPERSTAT"] == record["ACSCFLAG"] == ("VALID" if has_rtt else "")
            assert record["OPERSTAT"] == record["FIRSTREG"] == "VALID"
            assert record["EPISTART"] == episode_start.isoformat()
            assert record["EPIEND"] == episode_end.isoformat()
            assert record["OPDATE_01"] == episode_start.isoformat()
            generator.generate_apc_dates.assert_called_once_with(
                fake=fake, pid="SYN-1", date_set={"EPIEND", "ADMIDATE", "ELECDATE"}, anchor_date_col="EPISTART"
            )


def _linked_data_dependencies(
    patches: ExitStack,
    linked_data_dir: Path | None = None,
) -> Mock:
    """Supply all four dictionaries and disable linked events by default."""
    if linked_data_dir is None:
        linked_data_dir = Path(patches.enter_context(TemporaryDirectory()))
    dictionary_dir = linked_data_dir / "linked_data_dictionaries"
    dictionary_dir.mkdir(parents=True)
    dictionaries = {
        name: {
            "dictionary": pd.DataFrame(
                {
                    "name": ["PID", date_column, "ROW_ID"],
                    "type": ["string", "date", "integer"],
                    "coding_name": [None, None, None],
                },
            ),
        }
        for name, date_column in LINKED_DATASETS.values()
    }
    for name, dictionary in dictionaries.items():
        dictionary["dictionary"].to_csv(
            dictionary_dir / f"{name}_dictionary.csv", index=False,
        )
    (dictionary_dir / ".gitkeep").touch()
    (dictionary_dir / "README.txt").write_text("Not a dictionary", encoding="utf-8")

    patches.enter_context(patch.object(
        generator,
        "get_dictionaries",
        Mock(side_effect=lambda *, path, df_name: dictionaries[df_name]),
    ))
    patches.enter_context(patch.object(generator, "create_coded_pairs", Mock(return_value={})))
    patches.enter_context(patch.object(generator, "get_max_years", Mock(return_value=1)))
    fake = Mock()
    fake.linked_data_dir = linked_data_dir
    fake.pybool.return_value = False
    fake.random_elements.return_value = [123456, 654321]
    fake.random_int.return_value = 2
    patches.enter_context(patch.object(generator, "Faker", Mock(return_value=fake)))
    return fake

def _minimal_registries() -> tuple[pd.DataFrame, pd.DataFrame]:
    return (
        pd.DataFrame([
            _field("participant", "PID", "string", "synthetic_identifier"),
            _field("questionnaire", "PID", "string", "synthetic_identifier"),
        ]),
        pd.DataFrame(columns=["coding_name", "code", "is_special_code"]),
    )


def _record_dependencies(patches: ExitStack) -> Mock:
    """Control random choices while exercising the actual record generators."""
    fake = Mock()
    fake.pybool.return_value = False
    fake.date_between.side_effect = lambda *, start_date, end_date: start_date
    fake.random_element.side_effect = lambda *, elements: list(elements)[0]
    fake.random_int.return_value = 12
    fake.random_letter.return_value = "a"
    fake.time.return_value = "09:05"
    patches.enter_context(patch.object(generator, "pick_random_code", Mock(return_value="VALID")))
    patches.enter_context(patch.object(generator, "generate_numeric_id", Mock(side_effect=lambda fake, n: "1" * n)))
    patches.enter_context(patch.object(generator, "IMD_VALID_ENTRIES", ["1"]))
    return fake


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
