# Methodology

This project should produce synthetic data that is useful for development, testing and
demonstration without representing observed participants.

The intended workflow is:

1. Store source artefacts in `data/raw/` without editing them.
2. Discover and validate the expected source artefacts.
3. Parse the data dictionary, questionnaire codings and logic spreadsheets into `data/interim/`.
4. Build canonical schema, allowed-value and dependency files in `data/processed/`.
5. Generate `participant.csv` and `questionnaire.csv` using explicit distributions and
   deterministic seeds.
6. Validate the generated records against the schema and questionnaire logic.
7. Export synthetic datasets to `data/synthetic/` with metadata describing the config, seed and
   source versions.

Current generation is source-driven by the processed registries and applies supported
questionnaire `show_if` branching logic. Generated outputs can be checked with
`poetry run ofh-synthetic-data validate`.

## Registry Build

The `build-registry` command creates the first source-driven layer in `data/processed/`:

- `field_registry.csv`
- `coding_registry.csv`
- `logic_registry.csv`
- `entity_registry.csv`
- `coverage_summary.md`
- `source_manifest.json`

These files are generated artefacts and should be reproducible from `data/raw/`, project code
and `configs/default.yaml`.

## Synthetic Outputs

The `generate` command writes:

- `data/synthetic/participant.csv`
- `data/synthetic/questionnaire.csv`
- `data/synthetic/manifest.json`

Generation populates fields using `value_strategy` from `field_registry.csv`, including
synthetic identifiers, future dates, valid coded values, inferred numeric ranges and bracketed
multi-select lists. Fields marked `blank` in the registry are left empty. Fields hidden by
supported `show_if` logic are also left empty.

Output columns follow the source data dictionary row order for each entity. Questionnaire
`show_if` order is used for dependency evaluation, not for rearranging exported columns.

The generated `manifest.json` records Beta status, manual validation status, row count, seed,
questionnaire version, output paths, config snapshot, source file fingerprints from
`source_manifest.json`, synthetic marker rules, column counts and supported skip-logic
summary.

## Validation

The `validate` command checks generated `participant.csv`, `questionnaire.csv` and
`manifest.json` against the processed registries. The current checks cover output file
presence, column order, broad field types, coded values, multi-select values, synthetic ID
markers, future date markers, participant/questionnaire `PID` links, generated root logic
fields with blank `show_if`, fields marked blank by V2 scoping and fields skipped by
supported `show_if` logic.
