# Our Future Health Synthetic Data Generator Project Brief

## Purpose

Create a Python tool that generates Beta synthetic `participant.csv` and baseline health
questionnaire V2 `questionnaire.csv` tables from public Our Future Health P14 documentation.

The aim is to help researchers understand table shape, identifiers, codings, joins and common
branching patterns before working with non-synthetic data in the TRE. The project prioritises
structural fidelity, valid codings, reproducibility and clear synthetic markers. Statistical
fidelity is not required for Beta.

## Scope

In scope:

- P14 `participant` fields included by the configured registry build.
- P14 baseline health questionnaire V2 `questionnaire` fields.
- one questionnaire row per synthetic participant.
- source-driven schema, coding and release-schema questionnaire logic.
- deterministic generation from a fixed seed.
- visible synthetic markers, including `SYN`-prefixed identifiers, generated
  `CONSENT_VERSION` values beginning with `SYNTHETIC_`.
- temporal consistency for dates used to generate age only (i.e. core timeline).
- curated subset of linked datasets (HES Admitted Patient Care, HES Outpatient, HES Accident & Emergency, ONS Death Registration)
- unit tests and QA checks for schema, types, codings and linkage.

Out of scope:

- V1 questionnaire data.
- geography, genetic, and clinic measurement.
- de-identification suppressions.
- the full linked data offering on the Trusted Research Environment
- statistical fidelity to observed Our Future Health distributions.
- temporal consistency across other date, year and age fields outside the reduced core
  timeline.
- field-specific plausibility rules beyond documented broad numeric range heuristics, such as
  consistency between related answers or tighter quantity limits.
- exhaustive checks for every questionnaire minor-version changelog edge case.

## Source Artefacts

Source artefacts are included in `dictionaries/raw/` to support reproducible registry builds. They
should be copied exactly as received. Expected source files and source links are documented in
[dictionaries/raw/README.md](dictionaries/raw/README.md).

## Generated Artefacts

Processed registries are generated under `dictionaries/processed/`:

```text
field_registry.csv
coding_registry.csv
logic_registry.csv
entity_registry.csv
coverage_summary.md
source_manifest.json
```
Processed linked data dictionaries and coding files are generated under `dictionaries/processed/linked-data/`. Dictionaries and coding files for all linked datasets within the p15 release are processed, including those that are not within scope for synthetic data generation.

Synthetic and QA outputs are generated under `outputs/`:

```text
outputs/synthetic/participant.csv
outputs/synthetic/questionnaire.csv
outputs/synthetic/nhse_eng_inpat.csv
outputs/synthetic/nhse_eng_outpat.csv
outputs/synthetic/nhse_eng_ed.csv
outputs/synthetic/nhse_engwal_deaths.csv
outputs/synthetic/manifest.json
```

Decoded outputs are only available for questionnaire and participant outputs. Generated artefacts are ignored by git by default.

## Current Status

Current verified behaviour:

- synthetic linked data, `participant.csv` and `questionnaire.csv` are generated.
- output columns follow source data dictionary order.
- generated coded values come from the Our Future Health codings file.
- supported release-schema questionnaire logic is applied.
- skipped fields, superseded fields and uncoded non-V2 fields are blank.
- participant and questionnaire rows link correctly by `PID`.
- generated outputs are deterministic with a fixed seed.
- unit tests, QA tests, linting and dependency consistency checks pass.

Current registry build result from the P14 source files:

- 373 in-scope dictionary fields.
- 2,482 coding rows.
- 288 questionnaire logic rows.
- 2 in-scope entities: `participant` and `questionnaire`.
- 4 linked datasets
- 299 fields marked for generation.
- 74 fields marked blank.
- 73 fields with inferred numeric ranges.

## Key Assumptions

Detailed assumptions are documented in [docs/assumptions.md](docs/assumptions.md). In short:

- blank values mean not generated, not asked, skipped or out of V2 scope.
- negative codes mean asked but coded as a special response such as `Do not know` or
  `Prefer not to answer`.
- numeric ranges are broad Beta heuristics unless a more specific rule is documented.
- multi-select values are serialized as bracketed comma lists, for example `[1,6]`.
- `QUESTIONNAIRE_VERSION` is generated as `"v2"`.

## Useful Commands

```bash
poetry install
poetry run ofh-synthetic-data --config configs/default.yaml inspect-inputs
poetry run ofh-synthetic-data --config configs/default.yaml build-registry
poetry run ofh-synthetic-data --config configs/default.yaml generate
poetry run ofh-synthetic-data --config configs/default.yaml validate
poetry run pytest
poetry run ruff check .
```
