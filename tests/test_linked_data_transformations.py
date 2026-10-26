"""Unit tests for linked_data_transformations.

The attached module depends on Faker and ofh_synthetic_data.constants. When
those project dependencies are unavailable (for example, when running this
file by itself), small import stubs keep the tests isolated from them.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pandas as pd


def _install_optional_import_stubs() -> None:
    try:
        import faker  # noqa: F401
    except ImportError:
        faker_module = types.ModuleType("faker")

        class Faker:  # only used as an import-time annotation in the module
            pass

        faker_module.Faker = Faker
        sys.modules["faker"] = faker_module

    try:
        from ofh_synthetic_data.constants import DATE_BOOKENDS  # noqa: F401
    except ImportError:
        package = types.ModuleType("ofh_synthetic_data")
        package.__path__ = []
        constants = types.ModuleType("ofh_synthetic_data.constants")
        constants.DATE_BOOKENDS = {
            "nhse_eng_inpat": {
                "start": dt.date(2000, 1, 1),
                "end": dt.date(2020, 12, 31),
            }
        }
        sys.modules.setdefault("ofh_synthetic_data", package)
        sys.modules["ofh_synthetic_data.constants"] = constants


_install_optional_import_stubs()
_MODULE_PATH = _MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "ofh_synthetic_data"
    / "generate"
    / "linked_data_transformations.py"
)
_SPEC = importlib.util.spec_from_file_location("linked_data_transformations", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
ldt = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ldt)


class LinkedDataTransformationsTests(unittest.TestCase):
    def test_check_n_files_returns_the_only_filename(self):
        self.assertEqual(ldt.check_n_files(["data.csv"]), "data.csv")

    def test_check_n_files_rejects_empty_and_multiple_lists(self):
        with self.assertRaisesRegex(Exception, "No files found"):
            ldt.check_n_files([])
        with self.assertRaisesRegex(Exception, "Multiple files"):
            ldt.check_n_files(["a.csv", "b.csv"])

    def test_get_dictionaries_loads_dictionary_and_relevant_code_files(self):
        with self.subTest("ontology coding"):
            with __import__("tempfile").TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                (root / "linked_data_dictionaries").mkdir()
                (root / "linked_data_codings").mkdir()
                pd.DataFrame({"name": ["DIAG"], "coding_name": ["ICD10"]}).to_csv(
                    root / "linked_data_dictionaries" / "dataset_dictionary.csv", index=False
                )
                pd.DataFrame({"code": ["A01"]}).to_csv(
                    root / "linked_data_codings" / "ICD10.csv", index=False
                )
                result = ldt.get_dictionaries(str(root) + "/", "dataset")
                self.assertEqual(set(result), {"dictionary", "ICD10"})
                self.assertEqual(result["ICD10"]["code"].tolist(), ["A01"])

        with self.subTest("dataset code list"):
            with __import__("tempfile").TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                (root / "linked_data_dictionaries").mkdir()
                (root / "linked_data_codings").mkdir()
                pd.DataFrame({"name": ["STATUS"], "coding_name": ["status_codes"]}).to_csv(
                    root / "linked_data_dictionaries" / "dataset_dictionary.csv", index=False
                )
                pd.DataFrame({"coding_name": ["status_codes"], "code": ["Y"]}).to_csv(
                    root / "linked_data_codings" / "dataset_codes.csv", index=False
                )
                result = ldt.get_dictionaries(str(root) + "/", "dataset")
                self.assertEqual(set(result), {"dictionary", "codes"})
                self.assertEqual(result["codes"]["code"].tolist(), ["Y"])

    def test_get_dictionaries_returns_dictionary_when_no_codings_exist(self):
        with __import__("tempfile").TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "linked_data_dictionaries").mkdir()
            pd.DataFrame({"name": ["AGE"], "coding_name": [np.nan]}).to_csv(
                root / "linked_data_dictionaries" / "dataset_dictionary.csv", index=False
            )
            result = ldt.get_dictionaries(str(root) + "/", "dataset")
            self.assertEqual(set(result), {"dictionary"})

    def test_extract_date_fields_selects_date_typed_names(self):
        fields = pd.DataFrame(
            {"name": ["DOB", "AGE", "ADMIT"], "type": ["date", "integer", "date"]}
        )
        self.assertEqual(list(ldt.extract_date_fields(fields)), ["DOB", "ADMIT"])

    def test_generate_row_number_adds_sequential_ids(self):
        frame = pd.DataFrame({"value": ["a", "b", "c"]}, index=[9, 4, 20])
        result = ldt.generate_row_number(frame)
        self.assertIs(result, frame)
        self.assertEqual(result["ROW_ID"].tolist(), [0, 1, 2])

    def test_create_coded_pairs_excludes_uncoded_fields(self):
        dictionary = {
            "dictionary": pd.DataFrame(
                {"name": ["DIAG", "PROC", "AGE"], "coding_name": ["ICD10", "OPCS4", np.nan]}
            )
        }
        self.assertEqual(
            ldt.create_coded_pairs(dictionary), {"DIAG": "ICD10", "PROC": "OPCS4"}
        )

    def test_pick_random_code_uses_ontology_or_dataset_code_table(self):
        fake = Mock()
        fake.random_element.side_effect = lambda elements: list(elements)[0]
        tables = {
            "ICD10": pd.DataFrame({"code": ["A", "B"]}),
            "codes": pd.DataFrame(
                {"coding_name": ["status", "status", "other"], "code": ["Y", "N", "X"]}
            ),
        }
        self.assertEqual(ldt.pick_random_code(fake, "ICD10", tables), "A")
        self.assertEqual(ldt.pick_random_code(fake, "status", tables), "Y")
        self.assertEqual(fake.random_element.call_count, 2)

    def test_order_numbered_columns_sorts_numerically_by_base_name(self):
        result = ldt.order_numbered_columns(
            {"DIAG_10": "x", "PROC_2": "y", "DIAG_2": "z", "plain": "q", "PROC_1": "w"}
        )
        self.assertEqual(result, {"DIAG": ["DIAG_2", "DIAG_10"], "PROC": ["PROC_1", "PROC_2"]})

    def test_generate_numeric_id_requests_a_unique_n_digit_number(self):
        fake = Mock()
        fake.unique.random_int.return_value = 438
        self.assertEqual(ldt.generate_numeric_id(fake, 3), 438)
        fake.unique.random_int.assert_called_once_with(min=100, max=999)

    def test_get_max_years_includes_both_endpoint_years(self):
        dates = {"sample": {"start": dt.date(2019, 7, 1), "end": dt.date(2021, 2, 1)}}
        self.assertEqual(ldt.get_max_years("sample", dates), 3)

    def test_generate_apc_dates_when_anchor_is_before_conditional_fields(self):
        fake = Mock()
        fake.date_between.side_effect = lambda start_date, end_date: start_date
        fake.pybool.return_value = True
        date_fields = {"ADMIDATE", "EPIEND", "OTHER", "DISREADYDATE", "RTTPERSTART", "RTTPEREND"}

        bookends = {
            "nhse_eng_inpat": {
                "start": dt.date(2000, 1, 1),
                "end": dt.date(2020, 12, 31),
            },
        }

        with unittest.mock.patch.object(ldt, "DATE_BOOKENDS", bookends):
            record = ldt.generate_apc_dates(fake, "pid-1", date_fields, "ADMIDATE")

        self.assertEqual(record["PID"], "pid-1")
        self.assertEqual(record["ADMIDATE"], dt.date(2000, 1, 1))
        self.assertEqual(record["EPIEND"], dt.date(2000, 1, 1))
        for field in ("DISREADYDATE", "RTTPERSTART", "RTTPEREND"):
            self.assertTrue(pd.isna(record[field]))
        self.assertEqual(record["ELECDATE"], dt.date(1999, 12, 22))

    def test_generate_apc_dates_fills_conditional_fields_for_recent_anchor(self):
        fake = Mock()
        fake.date_between.side_effect = lambda start_date, end_date: start_date
        fake.pybool.return_value = False
        fields = {"ADMIDATE", "EPIEND", "DISREADYDATE", "RTTPERSTART", "RTTPEREND"}
        recent_bookends = {
            "nhse_eng_inpat": {
                "start": dt.date(2010, 1, 1),
                "end": dt.date(2020, 12, 31),
            }
        }
        with unittest.mock.patch.object(ldt, "DATE_BOOKENDS", recent_bookends):
            record = ldt.generate_apc_dates(fake, "pid-2", fields, "ADMIDATE")

        anchor = dt.date(2010, 1, 1)
        self.assertEqual(record["PID"], "pid-2")
        self.assertEqual(record["EPIEND"], anchor)
        self.assertEqual(record["DISREADYDATE"], anchor)
        self.assertEqual(record["RTTPERSTART"], anchor)
        self.assertEqual(record["RTTPEREND"], anchor)


if __name__ == "__main__":
    unittest.main()
