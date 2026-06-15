# Unit Test Summary

This project currently has 11 unit tests under `tests/`.

Run the suite with:

```bash
poetry run pytest
```

The tests use small local fixtures and temporary directories. They are intended to check core
pipeline behaviour without depending on generated output files being committed to the repo.

## Current Coverage

| Test module | Tests | Scope |
| --- | ---: | --- |
| `tests/test_config.py` | 2 | Default configuration values and YAML config overrides. |
| `tests/test_registries.py` | 1 | Registry building from source-style workbook fixtures, including entity filtering, V2 field handling, coding metadata, source manifest output and coverage notes. |
| `tests/test_generator.py` | 4 | Synthetic table generation, linked `PID` values, synthetic identifiers, future dates, blank fields, coded values, multi-select values, column ordering and supported `show_if` logic. |
| `tests/test_validation.py` | 4 | Output validation checks for valid generated tables, blank root logic fields, invalid coded values, type errors, broken `PID` links and unsupported populated skip-logic fields. |

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
- dictionary-derived numeric and date types are enforced during output validation.
- supported questionnaire branching logic blanks skipped fields.
- validation reports key structural and data-quality issues.

## Current Limits

The unit tests do not replace manual validation of the generated Beta outputs. They do not
verify statistical fidelity, complete field-by-field plausibility, or every source-file edge
case in the full P14/V2 artefacts. Those checks remain part of ongoing manual review and
future plausibility-rule work.
