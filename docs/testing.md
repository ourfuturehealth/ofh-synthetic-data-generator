# Unit Test Summary

This project currently has 16 unit tests and 5 QA tests under `tests/`.

Run all tests with:

```bash
poetry run pytest
```

Run only the unit tests with:

```bash
poetry run pytest tests/test_*.py
```

Run only the QA tests with:

```bash
poetry run pytest tests/qa
```

The unit tests use small local fixtures and temporary directories. They are intended to check
core pipeline behaviour without depending on generated output files being committed to the
repo.

## Current Coverage

| Test module | Tests | Scope |
| --- | ---: | --- |
| `tests/test_config.py` | 3 | Default configuration values, YAML config overrides and legacy config compatibility for the QA output directory. |
| `tests/test_decoded_export.py` | 2 | Decoded manual QA export behaviour, including single coded values, multi-select values, special codes and output file writing. |
| `tests/test_registries.py` | 1 | Registry building from source-style workbook fixtures, including entity filtering, V2 field handling, coding metadata, source manifest output and coverage notes. |
| `tests/test_generator.py` | 6 | Synthetic table generation, linked `PID` values, synthetic identifiers, future dates, blank fields, coded values, multi-select values, suppression-code exclusion, numeric input fields with coded choices, column ordering and supported `show_if` logic. |
| `tests/test_validation.py` | 4 | Output validation checks for valid generated tables, blank root logic fields, invalid coded values, type errors, broken `PID` links and populated fields that should be blanked by supported skip logic. |
| `tests/qa/test_output_schema.py` | 5 | QA checks that generated full outputs match source-derived column names, data dictionary order and broad data dictionary types, that literal `None` coding meanings are preserved from the source workbook, that coded questionnaire fields absent from V2 logic are blanked, that numeric-range fields with special codes only produce values allowed by their configured ranges or codings, that suppression codes are not generated, that the core timeline supports adult age calculation, and that the medication reasons logic row maps to `MEDICAT_1_M`. |

## What The Tests Check

- configuration defaults and config-file overrides are loaded as expected.
- source-like dictionary, coding and questionnaire logic fixtures can be converted into
  processed registries.
- only configured in-scope entities are retained during registry building.
- generated participant and questionnaire tables are linked by the same synthetic `PID`.
- synthetic identifiers use visible `SYN` prefixes.
- generated questionnaire dates use future synthetic dates.
- output columns follow source dictionary order.
- blank fields remain blank.
- coded fields use values from the coding registry.
- manual QA exports can replace coded values with coding meanings where available.
- dictionary-derived numeric and date types are enforced during output validation.
- supported release-schema questionnaire logic blanks skipped fields.
- validation reports key structural and data-quality issues.

## QA Checks

The QA tests build registries from the included public source artefacts, generate synthetic
outputs in a temporary directory and checks the full `participant.csv` and `questionnaire.csv`
schema.

It checks that:

- output column names exactly match the source-derived field registry.
- output columns appear in data dictionary order.
- every generated column uses a supported dictionary type.
- populated integer, float, date and multi-select values conform to the broad dictionary
  type expected for that column.
- string columns contain string values when populated.
- literal `None` coding meanings in the source workbook remain `None` in processed codings.
- coded questionnaire fields absent from V2 logic are blanked unless explicitly retained by
  the registry policy.
- fields generated with the `numeric_range_with_special_codes` strategy only contain blank
  values, values inside the configured numeric range or field-specific special codes.
- default generated outputs do not contain suppression encodings such as `-999`.
- registration, consent and questionnaire submission year-month values align, and birth years
  support adult age calculation against that core timeline.

## Current Limits

The unit tests do not replace manual validation of the generated Beta outputs.
