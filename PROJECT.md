# OFH Synthetic Data Generator

## Summary

Create a Python tool that generates a Beta synthetic dataset with linked `participant` and
`questionnaire` tables mirroring the structure and relationships of core Our Future Health
(OFH) questionnaire data. The dataset should let internal and external researchers explore the
data model, develop analysis code locally, and prototype workflows before working with
non-synthetic data in the TRE.

This project prioritises structural fidelity, valid codings, reproducibility and clear
synthetic markers. Statistical fidelity is not required for Beta.

## Aim

Generate linked synthetic `participant.csv` and `questionnaire.csv` tables for the V2
questionnaire using publicly available OFH documentation:

- data dictionary
- data codings
- questionnaire logic
- questionnaire summary/PDF documentation

The output should support local development and onboarding by helping researchers understand
tables, columns, identifiers, codings, participant/questionnaire relationships and common
branching patterns.

## Inputs And Storage Policy

Public source artefacts are included in `data/raw/` to support reproducible registry builds.

Raw files live in:

```text
data/raw/
```

The source artefacts should be copied exactly as received. If a source file needs parsing,
normalization or other transformation, write the result to `data/interim/` or
`data/processed/`.

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

- Produce Beta synthetic participant and questionnaire tables only.
- Produce V2 questionnaire-scope data only.
- Include obvious synthetic markers, such as `SYN`-prefixed IDs.
- Use deliberately synthetic/future dates where practical, for example years `3000+`.
- Include clear documentation that the dataset is synthetic, Beta and expected to improve.
- Include unit tests.
- Test that generated column names and broad data types match the data dictionary.
- Do not aim to preserve real statistical distributions.
- Do not derive values from observed participant-level records.

## In Scope

- `participant.csv`
- `questionnaire.csv`
- one questionnaire row per synthetic participant for Beta
- source-driven schema/registry generation
- V2 field scoping
- valid coding values
- simple synthetic value generation
- supported questionnaire branching logic
- assumptions and coverage documentation

## Out Of Scope

- V1 questionnaire data
- de-identification suppressions
- statistical fidelity
- clinic measurements
- point-of-care lipid profile
- participant geographies
- linked NHS records
- genetic data
- reconstructing the full raw questionnaire capture flow

## Target Outputs

Final Beta outputs should be generated under `data/synthetic/`:

```text
data/synthetic/
  participant.csv
  questionnaire.csv
  manifest.json
  assumptions.md
  coverage_summary.md
```

Processed source-derived artefacts should be generated under `data/processed/`:

```text
data/processed/
  field_registry.csv
  coding_registry.csv
  logic_registry.csv
  entity_registry.csv
  coverage_summary.md
  source_manifest.json
```

## Current Repo Status

Completed:

- Poetry project setup.
- Data lifecycle folders: `data/raw`, `data/interim`, `data/processed`,
  `data/synthetic`, `outputs/reports`.
- Public source artefacts included in `data/raw/`; generated data ignored by git by default.
- CLI command to inspect expected raw inputs.
- CLI command to build source registries.
- Source registries enriched with V2 inclusion, generation action, blanking reason, value
  strategy, numeric range, special-code and multi-select metadata.
- Source-driven generator writes `participant.csv`, `questionnaire.csv` and `manifest.json`.
- Supported questionnaire `show_if` logic is applied during generation.
- Tests cover config loading, registry parsing, source-driven generation, skip logic and
  output validation.
- Local development guidance exists for agent-assisted work, but must not be required by or
  shipped as part of the end-user workflow.

Current registry build result from the P14/V2 source files:

- 373 in-scope dictionary fields.
- 2,482 coding rows.
- 288 questionnaire logic rows.
- 2 in-scope entities: `participant` and `questionnaire`.
- 298 fields marked for generation.
- 75 fields marked blank.
- 72 fields with inferred numeric ranges.

Next implementation step:

- Build an auditable plausibility-candidate registry for optional consistency rules beyond the
  source questionnaire logic.

## Plan Of Action

### Phase 1: Source Registries

Status: complete.

Build reproducible registries from the raw documentation:

- `field_registry.csv`: one row per in-scope dictionary field.
- `coding_registry.csv`: valid coded values used by in-scope fields.
- `logic_registry.csv`: V2 questionnaire logic rows.
- `entity_registry.csv`: entity-level field counts and key metadata.
- `coverage_summary.md`: generated coverage checks and source-specific notes.
- `source_manifest.json`: local raw file fingerprints so the source version can be checked
  during reproducible builds.

Current verified output:

- 373 dictionary fields.
- 2,482 coding rows.
- 288 questionnaire logic rows.
- 2 entities: `participant` and `questionnaire`.
- source files fingerprinted in `source_manifest.json`.

Verification:

```bash
poetry run ofh-synthetic-data inspect-inputs
poetry run ofh-synthetic-data build-registry
poetry run pytest
poetry run ruff check .
```

### Phase 2: Enrich Field Metadata

Status: complete.

Add generation metadata to the processed registry layer:

- V2 inclusion status.
- output entity: `participant` or `questionnaire`.
- blanking reason for out-of-scope/superseded fields.
- inferred numeric ranges for uncoded numeric fields.
- special-code policy.
- multi-select handling.
- required metadata fields.

Key rule:

- If both `_1_1` and `_2_1` versions exist, populate the V2 field.
- If only `_1_1` exists and it is part of V2, populate it.
- V1-only or superseded fields should be blank.

Current verified output:

- 298 fields marked `generate`.
- 75 fields marked `blank`.
- 72 fields with inferred numeric ranges.
- 5 required metadata fields.
- `field_registry.csv` includes `v2_inclusion_status`, `generation_action`,
  `blank_reason`, `value_strategy`, `numeric_range_rule`, `special_code_policy` and
  `multi_select_strategy`.

### Phase 3: Synthetic Value Generation

Status: complete.

Implement source-driven value generation:

- IDs use visible `SYN` prefixes.
- dates use deliberately synthetic/future years.
- coded fields sample from valid codings.
- negative codes are treated as special/missing codes.
- uncoded numeric fields use documented inferred ranges.
- free-text and identifier-only fields use obvious synthetic placeholders.
- multi-select values use bracketed lists such as `[1,6]`.

Statistical fidelity is not required. Default distributions can be uniform or simple.

Current verified output:

- `participant.csv`
- `questionnaire.csv`
- `manifest.json`
- deterministic `SYN-...` participant `PID` values.
- deterministic `SYN-ID-...` questionnaire `ID` values.
- linked participant/questionnaire `PID` values.
- future synthetic dates.
- valid coded single-select values.
- bracketed multi-select values.
- output columns in source data dictionary order.
- blank values for fields marked `blank` in `field_registry.csv`.

### Phase 4: Questionnaire Logic

Status: complete.

Implement the supported `show_if` grammar from the logic workbook:

- equality checks, e.g. `FIELD = N`
- `NULL` and `NOT NULL`
- `ONE of [...]`
- `ANY of [...]`
- simple integer ranges
- `AND` / `OR`
- nested parentheses where feasible
- duplicate logic rows combined with OR

Current scope note:

- The questionnaire logic files contain branching logic only. They do not contain all
  validation rules and cannot fully reconstruct the raw data capture questionnaire flow.

Unsupported or non-standard logic should be logged and handled conservatively rather than
stopping generation.

Current verified output:

- logic expressions are evaluated in questionnaire order.
- participant fields are available to questionnaire logic.
- duplicate logic rows for the same field are combined as OR.
- skipped fields are left blank.
- `manifest.json` records whether questionnaire logic was applied and how many values were
  skipped by logic.

### Phase 5: Generate Beta Tables

Generate:

- `participant.csv`
- `questionnaire.csv`
- `manifest.json`
- generated assumptions and coverage summaries

Generation order:

1. Build or load registries.
2. Generate participants.
3. Generate one questionnaire row per participant.
4. Seed participant values into the questionnaire context for cross-entity logic.
5. Apply V2 scoping and supported branching logic.
6. Populate shown fields.
7. Leave skipped or non-V2 fields blank.
8. Write outputs in source data dictionary order.
9. Write metadata.

### Phase 6: Validation

Status: complete.

The `validate` command checks:

- expected output files exist.
- output columns match in-scope dictionary fields in source data dictionary order.
- broad output types match dictionary types.
- coded values are valid.
- multi-select values contain valid options.
- participant and questionnaire rows link by `PID`.
- `ID` and `PID` values contain `SYN`.
- date fields use synthetic/future ranges.
- generated top-of-tree/root logic fields with blank `show_if` are populated.
- skipped fields are blank where supported logic says they should be skipped.
- generated outputs do not contain raw source content.

Current verified output:

- `poetry run ofh-synthetic-data --config configs/default.yaml validate` passes.
- validation reports human-readable errors and returns a non-zero exit code on failure.
- validation has unit tests for passing generated outputs and deliberately tampered outputs.
- validation has a unit test for blank root/top-of-tree logic fields.

### Phase 7: Documentation And Beta Release

Status: complete.

Beta release cleanup includes:

- `README.md` quickstart updated.
- `docs/methodology.md`, `docs/assumptions.md` and `docs/sharing_checklist.md` updated.
- `manifest.json` records row count, seed, config snapshot, source file fingerprints and
  output file paths.
- current scope notes and stretch goals are documented.
- previous starter/baseline generator code removed.
- previous `synthetic_baseline.csv` configuration path removed.
- Codex-specific/local agent guidance is ignored by git and not required for end users.

Current verified output:

- default generation writes 200 linked participant/questionnaire rows.
- `participant.PID` and `questionnaire.PID` use the same deterministic `SYN-...` values.
- `questionnaire.ID` uses deterministic `SYN-ID-...` values.
- full registry build, generation, validation, lint and unit tests pass.

### Stretch Goal: Plausibility Rules Beyond Questionnaire Logic

The questionnaire logic workbook does not encode every real-world consistency constraint.
As a stretch goal, add an explicit plausibility layer for assumptions that are not present in
the source logic files.

Examples:

- apply additional consistency rules for sex-specific responses, such as prostate exam
  responses.
- avoid internally inconsistent answers across related fields.
- constrain out-of-range or high-quantity smoking or alcohol values.
- make sex-specific, age-specific or unit-specific responses coherent where the source logic
  does not fully enforce this.
- make temporal responses coherent, such as date of birth preceding registration or
  questionnaire submission, and first-child age preceding or matching last-child age.

Proposed analysis before implementation:

- scan `field_registry.csv`, `logic_registry.csv` and source dictionary metadata for candidate
  field families that imply sex-specific, age-specific, unit-specific or temporal constraints.
- start with prefix-based candidates such as `GYN*` fields, which are likely to represent
  female-specific/gynaecological questionnaire content.
- scan date, year, month and age fields for temporal dependencies, including `BIRTH_*`,
  `REGISTRATION_*`, `CONSENT_*`, `SUBMISSION_DATE`, immigration year fields and first/last
  child age fields.
- review field names, titles, descriptions, codings and existing `show_if` conditions before
  turning any prefix heuristic into a generation rule.
- compare candidate sex-specific fields against participant sex fields, especially
  `DEMOG_SEX_2_1`, and document how unknown, missing or special-code sex values should be
  handled.
- compare candidate temporal fields against participant age/date context and document how
  special, missing or skipped values should be handled.
- produce an auditable candidate registry before coding rules, for example
  `data/processed/plausibility_candidates.csv`, with field name, reason, proposed constraint,
  source evidence and review status.

Possible first rule family:

- `GYN*` questionnaire fields should only be populated for participant records where the
  synthetic sex context is consistent with the field. Otherwise they should be blank or set to
  an appropriate synthetic missing/skipped value, depending on the field and coding.
- participant birth year/month should precede registration, consent and questionnaire
  submission dates.
- first-child age fields should be less than or equal to corresponding last-child age fields;
  both should be consistent with the participant's synthetic birth date or age context.
- immigration year should be after birth year and before registration or questionnaire
  submission year where those values are available.

This layer should be:

- clearly documented as additional synthetic-generation logic.
- configurable or easy to audit.
- tested separately from source-derived questionnaire logic.
- treated as a quality improvement, not a Beta blocker.

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

## Questionnaire Background

The baseline health questionnaire V2 has 288 questions:

- 68 core questions shown to all participants.
- 220 dynamic questions shown selectively based on previous responses.

The questionnaire has five sections:

- About you and your household: 25 questions.
- Work and education: 13 questions.
- Your lifestyle: 77 questions.
- Family health history: 68 questions.
- Your health history: 105 questions.

## Known Challenges And Assumptions

### Documentation And Source-Specific Notes

- The questionnaire PDF includes fields that now live in the `participant` table, including
  `DEMOG_ETHNICITY`, `DEMOG_GENDER` and `DEMOG_SEX`.
- `section4` in the logic workbook has a non-standard section header.
- `section5` has an extra `notes` column.
- `DEMOG_HEIGHT_1_1` and `DEMOG_WEIGHT_1_1` appear more than once in the logic workbook.
- The logic field `eb` does not map to the data dictionary.
- The dictionary `entity` column is the preferred source for entity grouping.

### Version Scoping

- Generate V2 only.
- Presence in the V2 logic file is the main signal for questionnaire inclusion.
- Field suffixes alone are not enough to determine whether a field is live in V2.
- A blank means not asked, skipped or not in V2.
- A negative code means the question was asked but the response is special/missing.

### Entity Structure

- `DEMOG_SEX_2_1`, `DEMOG_GENDER_2_1` and `DEMOG_ETHNICITY_1_1` should be generated on
  `participant`, not duplicated into `questionnaire`.
- Questionnaire metadata fields such as `ID`, `PID`, `QUESTIONNAIRE_VERSION` and
  `SUBMISSION_DATE` should always be populated.
- Some questionnaire questions branch on participant fields such as `DEMOG_SEX_2_1`.

### Value Generation

- Use simple or uniform distributions unless an explicit rule is documented.
- Infer numeric ranges where the dictionary gives type/units but no bounds.
- Treat negative integer codes as special/missing codes.
- Serialize multi-select answers as bracketed comma lists.
- Use a fixed seed by default for reproducibility.
- Plausibility rules not present in the source logic files should be documented separately and
  treated as stretch-goal synthetic-generation constraints.

## Useful Commands

```bash
poetry install
poetry run ofh-synthetic-data inspect-inputs
poetry run ofh-synthetic-data build-registry
poetry run ofh-synthetic-data --config configs/default.yaml generate
poetry run pytest
poetry run ruff check .
```
