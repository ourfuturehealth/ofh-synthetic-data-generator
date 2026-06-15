# OFH Synthetic Data Generator

## Summary

Create a Python tool that generates a Beta synthetic dataset with linked `participant` and
baseline health questionnaire V2 `questionnaire` tables.

The wider Our Future Health (OFH) P14 release includes additional data areas, including
geography, genetic, clinic measurement and linked NHSE data. These are outside this Beta
generator.

The project prioritises structural fidelity, valid codings, reproducibility and clear
synthetic markers. Statistical fidelity is not required for Beta.

## Aim

Generate linked synthetic `participant.csv` and baseline health questionnaire V2
`questionnaire.csv` tables using publicly available OFH documentation:

- data dictionary
- data codings
- questionnaire logic
- questionnaire summary/PDF documentation

The outputs should help researchers understand table shape, identifiers, codings,
participant/questionnaire relationships and common branching patterns before working with
non-synthetic data in the TRE.

## Inputs

Public source artefacts are included in `data/raw/` to support reproducible registry builds.
Source artefacts should be copied exactly as received. The current pipeline writes generated registries to `data/processed/`. `data/interim/` is reserved for temporary parsed extracts if a future processing step needs them.

Source locations:

- Data dictionary and codings:
  `https://research.ourfuturehealth.org.uk/data-and-cohort/`
- Questionnaire PDF and logic:
  `https://ourfuturehealth.gitbook.io/our-future-health/data-types/questionnaire-data`
- Accessed: 11 June 2026
- Release target: P14
- Questionnaire target: V2

Generated and derived data should remain uncommitted by default:

```text
data/processed/   # generated registries and derived metadata
data/synthetic/   # generated synthetic datasets
outputs/reports/  # generated reports and summaries
```

## Requirements

- Use the OFH P14 data dictionary and codings.
- Produce Beta synthetic `participant.csv` and `questionnaire.csv` tables only.
- Scope questionnaire generation to baseline health questionnaire V2 only.
- Include obvious synthetic markers, such as `SYN`-prefixed IDs.
- Use deliberately synthetic/future dates where practical, for example years `3000+`.
- Include clear documentation that the dataset is synthetic, Beta and expected to improve.
- Include unit tests.
- Test that generated column names and broad data types match the data dictionary.
- Do not aim to preserve real statistical distributions.
- Do not derive values from observed participant-level records.

## Scope

In scope:

- `participant.csv`.
- baseline health questionnaire V2 `questionnaire.csv`.
- one questionnaire row per synthetic participant for Beta.
- P14 participant fields included by the configured registry build.
- source-driven schema and registry generation.
- V2 questionnaire field scoping.
- valid OFH coding values.
- simple synthetic value generation.
- supported questionnaire branching logic.
- assumptions and coverage documentation.

Out of scope:

- V1 questionnaire data.
- de-identification suppressions.
- statistical fidelity.
- clinic measurements.
- point-of-care lipid profile.
- geography data.
- linked NHSE data.
- genetic data.
- reconstructing the full raw questionnaire capture flow.

## Target Outputs

Final Beta outputs are generated under `data/synthetic/`:

```text
data/synthetic/
  participant.csv
  questionnaire.csv
  manifest.json
```

Processed source-derived artefacts are generated under `data/processed/`:

```text
data/processed/
  field_registry.csv
  coding_registry.csv
  logic_registry.csv
  entity_registry.csv
  coverage_summary.md
  source_manifest.json
```

## Current Status

This repository is a Beta release candidate. The pipeline includes unit tests for
configuration loading, registry parsing, synthetic generation, skip-logic handling and output
validation. Generated synthetic outputs are still undergoing manual validation and should be
treated as Beta artefacts.

Current implementation:

- builds source-derived registries from the included P14/V2 public artefacts.
- generates linked `participant.csv`, `questionnaire.csv` and `manifest.json`.
- applies supported questionnaire `show_if` branching logic.
- keeps output columns in source data dictionary order.
- validates codings, synthetic markers, PID links, root logic fields and supported skip logic.
- keeps generated processed and synthetic artefacts ignored by git by default.

Current registry build result from the P14 source files:

- 373 in-scope dictionary fields.
- 2,482 coding rows.
- 288 questionnaire logic rows.
- 2 in-scope entities: `participant` and `questionnaire`.
- 298 fields marked for generation.
- 75 fields marked blank.
- 72 fields with inferred numeric ranges.

Detailed implementation history is in `docs/project_history.md`.

## Acceptance Criteria

Beta is complete when:

- `participant.csv` and `questionnaire.csv` are generated.
- outputs are deterministic with a fixed seed.
- all IDs visibly indicate synthetic data with a `SYN` prefix.
- generated dates are visibly synthetic/future-dated where practical.
- in-scope columns match the OFH P14 data dictionary.
- generated coded values come from the OFH codings file.
- V2 questionnaire scope is applied.
- supported branching logic is applied.
- skipped or non-V2 fields are blank.
- `participant` and `questionnaire` rows link correctly by `PID`.
- assumptions and current scope notes are documented.
- unit tests pass.
- source files are included in `data/raw/`; generated datasets remain ignored by git by
  default.

## Stretch Goal: Plausibility Rules Beyond Questionnaire Logic

The questionnaire logic workbook does not encode every consistency constraint. As a stretch
goal, add an explicit plausibility layer for assumptions that are not present in the source
logic files.

Proposed first step:

- create `data/processed/plausibility_candidates.csv`.
- scan `field_registry.csv`, `logic_registry.csv` and source dictionary metadata for candidate
  sex-specific, age-specific, unit-specific and temporal constraints.
- review field names, titles, descriptions, codings and existing `show_if` conditions before
  converting any heuristic into a generation rule.

Possible first rule families:

- restrict candidate sex-specific fields, such as reviewed `GYN*` fields, to consistent
  synthetic participant contexts.
- make temporal responses coherent, such as birth year preceding registration, consent and
  questionnaire submission dates.
- keep related ages coherent, such as first-child age being less than or equal to last-child
  age where both are populated.
- constrain high-quantity smoking, alcohol or activity fields beyond the current Beta numeric
  heuristics.

This layer should be configurable, documented as additional synthetic-generation logic and
tested separately from source-derived questionnaire logic. It is a quality improvement, not a
Beta blocker.

## Known Assumptions

Documentation and source-specific notes:

- The questionnaire PDF includes fields that now live in the `participant` table, including
  `DEMOG_ETHNICITY`, `DEMOG_GENDER` and `DEMOG_SEX`.
- `section4` in the logic workbook has a non-standard section header.
- `section5` has an extra `notes` column.
- `DEMOG_HEIGHT_1_1` and `DEMOG_WEIGHT_1_1` appear more than once in the logic workbook.
- The logic field `eb` does not map to the data dictionary.
- The dictionary `entity` column is the preferred source for entity grouping.

Version and entity structure:

- Generate V2 questionnaire data only.
- Presence in the V2 logic file is the main signal for questionnaire inclusion.
- Field suffixes alone are not enough to determine whether a field is live in V2.
- `DEMOG_SEX_2_1`, `DEMOG_GENDER_2_1` and `DEMOG_ETHNICITY_1_1` are generated on
  `participant`, not duplicated into `questionnaire`.
- Some questionnaire questions branch on participant fields such as `DEMOG_SEX_2_1`.

Value generation:

- Use simple or uniform distributions unless an explicit rule is documented.
- Infer numeric ranges where the dictionary gives type or units but no bounds.
- Current numeric ranges are broad Beta heuristics, not field-specific validated
  distributions.
- Other uncoded numeric fields use default ranges: `0-10` for integers and `0-100` for
  floats.
- Treat negative integer codes as special/missing codes.
- Serialize multi-select answers as bracketed comma lists.
- Use a fixed seed by default for reproducibility.

## Useful Commands

```bash
poetry install
poetry run ofh-synthetic-data inspect-inputs
poetry run ofh-synthetic-data build-registry
poetry run ofh-synthetic-data --config configs/default.yaml generate
poetry run ofh-synthetic-data --config configs/default.yaml validate
poetry run pytest
poetry run ruff check .
```
