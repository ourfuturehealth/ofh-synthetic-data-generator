# Project History

This document records the completed implementation phases for the Beta synthetic data
generator. The concise project brief is in `PROJECT.md`.

## Phase 1: Source Registries

Status: complete.

Built reproducible registries from the raw documentation:

- `field_registry.csv`: one row per in-scope dictionary field.
- `coding_registry.csv`: valid coded values used by in-scope fields.
- `logic_registry.csv`: V2 questionnaire logic rows.
- `entity_registry.csv`: entity-level field counts and key metadata.
- `coverage_summary.md`: generated coverage checks and source-specific notes.
- `source_manifest.json`: local raw file fingerprints for reproducible builds.

Current verified output:

- 373 dictionary fields.
- 2,482 coding rows.
- 288 questionnaire logic rows.
- 2 entities: `participant` and `questionnaire`.
- source files fingerprinted in `source_manifest.json`.

## Phase 2: Enrich Field Metadata

Status: complete.

Added generation metadata to the processed registry layer:

- V2 inclusion status.
- output entity: `participant` or `questionnaire`.
- blanking reason for out-of-scope or superseded fields.
- inferred numeric ranges for uncoded numeric fields.
- special-code policy.
- multi-select handling.
- required metadata fields.

Current verified output:

- 298 fields marked `generate`.
- 75 fields marked `blank`.
- 72 fields with inferred numeric ranges.
- 5 required metadata fields.
- `field_registry.csv` includes `v2_inclusion_status`, `generation_action`,
  `blank_reason`, `value_strategy`, `numeric_range_rule`, `special_code_policy` and
  `multi_select_strategy`.

## Phase 3: Synthetic Value Generation

Status: complete.

Implemented source-driven value generation:

- IDs use visible `SYN` prefixes.
- dates use deliberately synthetic/future years.
- coded fields sample from valid codings.
- negative codes are treated as special/missing codes.
- uncoded numeric fields use documented inferred ranges.
- free-text and identifier-only fields use obvious synthetic placeholders.
- multi-select values use bracketed lists such as `[1,6]`.

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

## Phase 4: Questionnaire Logic

Status: complete.

Implemented the supported `show_if` grammar from the logic workbook:

- equality checks, e.g. `FIELD = N`
- `NULL` and `NOT NULL`
- `ONE of [...]`
- `ANY of [...]`
- simple integer ranges
- `AND` / `OR`
- nested parentheses where feasible
- duplicate logic rows combined with OR

Current verified output:

- logic expressions are evaluated in questionnaire order.
- participant fields are available to release-schema questionnaire logic.
- duplicate logic rows for the same field are combined as OR.
- skipped fields are left blank.
- `manifest.json` records whether release-schema questionnaire logic was applied and how many
  values were skipped by that logic.

## Phase 5: Generate Beta Tables

Status: complete.

Generation order:

1. Build or load registries.
2. Generate participants.
3. Generate one questionnaire row per participant.
4. Seed participant values into the questionnaire context for cross-entity logic.
5. Apply V2 scoping and supported release-schema questionnaire logic.
6. Populate shown fields.
7. Leave skipped or non-V2 fields blank.
8. Write outputs in source data dictionary order.
9. Write metadata.

## Phase 6: Validation

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

## Phase 7: Documentation And Beta Release Cleanup

Status: complete.

Beta release cleanup included:

- `README.md` quickstart updated.
- `docs/methodology.md`, `docs/assumptions.md` and `docs/sharing_checklist.md` updated.
- `manifest.json` records row count, seed, config snapshot, source file fingerprints and
  output file paths.
- current scope notes and stretch goals documented.
- previous starter/baseline generator code removed.
- previous `synthetic_baseline.csv` configuration path removed.
- local-only development notes removed from the end-user workflow.

Current verified output:

- current default config writes linked participant/questionnaire rows.
- `participant.PID` and `questionnaire.PID` use the same deterministic `SYN-...` values.
- `questionnaire.ID` uses deterministic `SYN-ID-...` values.
- full registry build, generation, validation, lint and unit tests pass.
