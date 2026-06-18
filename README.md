# OFH Synthetic Data Generator

This repository contains a Python tool for generating reproducible synthetic Our Future
Health-style data from source documentation.

The wider OFH P14 data release includes several data areas, including participant,
questionnaire, geography, genetic, clinic measurement and linked NHSE data. This project is a
Beta generator for a narrower subset only.

The tool generates two linked tables:

- `participant.csv`
- `questionnaire.csv`

The questionnaire output is scoped to the baseline health questionnaire V2. The generated
data is synthetic, deterministic with a fixed seed and designed for local development,
onboarding and workflow prototyping rather than statistical analysis.

## Beta Status

This project is in Beta. The pipeline includes unit tests for core behaviour, but generated
synthetic outputs are still undergoing manual validation.

Outputs are suitable for exploring table structure, codings, joins and workflow prototyping.
They should not be used for statistical analysis or treated as a validated representation of
OFH data distributions.

See [docs/testing.md](docs/testing.md) for a summary of the current unit test coverage.

## Background

Researchers often need to understand data structure before they can write analysis code or
prepare workflows. This project provides a local synthetic dataset generator for the P14
`participant` table and baseline health questionnaire V2 `questionnaire` table, so users can
inspect table shape, identifiers, codings, branching patterns and joins before accessing
non-synthetic data.

The repository is intended to share the generator and its reproducible workflow rather than a
hand-authored dataset. The generator is source-driven: it reads the public OFH source
artefacts in `data/raw/`, builds processed registries from the data dictionary, codings and
questionnaire logic file, then uses those registries to generate linked synthetic
participant and questionnaire rows.

The questionnaire logic file is aligned to the release schema. It is used here to
generate and validate release-shaped synthetic outputs; it is not treated as a specification
for reconstructing the raw questionnaire capture flow or website engine behaviour. It
documents branching logic, not other validation rules or user-interface behaviour.

Generated datasets are ignored by git by default. Regenerate them locally from the included
source artefacts.

## What It Builds

Generation settings live in `configs/default.yaml`. A run writes linked participant and V2
questionnaire outputs to the configured synthetic output directory:

- `participant.csv`: one row per synthetic participant.
- `questionnaire.csv`: one questionnaire row per synthetic participant.
- `manifest.json`: row count, seed, config snapshot, source fingerprints and validation
  metadata.

The tables link by `PID`. Both `participant.PID` and `questionnaire.PID` use the same
deterministic `SYN-...` value. `questionnaire.ID` uses `SYN-ID-...`.

## Source Artefacts

The repository includes public source artefacts under `data/raw/` so registries and synthetic
outputs can be regenerated from a fresh checkout. The default configuration expects:

- `Our Future Health Baseline Health Questionnaire v2.pdf`
- `Our Future Health Baseline Questionnaire Logic v2.2.xlsx`
- `our_future_health_data_dictionary_v14.xlsx`
- `our_future_health_codings_v14.xlsx`

See [data/raw/README.md](data/raw/README.md) and [docs/data_sources.md](docs/data_sources.md)
for source details.

## Scope

In scope:

- P14 `participant` fields included by the configured registry build.
- P14 baseline health questionnaire V2 `questionnaire` fields.
- One questionnaire row per synthetic participant for Beta.

Out of scope:

- V1 questionnaire data.
- Geography, genetic, clinic measurement and linked NHSE data.
- Statistical fidelity to observed OFH distributions.

## Quickstart

Install dependencies:

```bash
poetry install
```

Check the expected source artefacts:

```bash
poetry run ofh-synthetic-data --config configs/default.yaml inspect-inputs
```

Build source-derived registries:

```bash
poetry run ofh-synthetic-data --config configs/default.yaml build-registry
```

Generate synthetic participant and questionnaire tables:

```bash
poetry run ofh-synthetic-data --config configs/default.yaml generate
```

Override the configured row count for a run:

```bash
poetry run ofh-synthetic-data --config configs/default.yaml generate --rows 50
```

Validate generated outputs:

```bash
poetry run ofh-synthetic-data --config configs/default.yaml validate
```

Create manual QA copies with coded values replaced by meanings where possible:

```bash
poetry run ofh-synthetic-data --config configs/default.yaml export-qa
```

Run tests and linting:

```bash
poetry run pytest
poetry run ruff check .
```

## Project Layout

```text
src/ofh_synthetic_data/
  ingest/       source file discovery and registry building
  generate/     synthetic data generation logic
  export/       CSV and metadata writers
  validate/     synthetic output validation checks
configs/        reproducible generation settings
data/raw/       public source artefacts used for registry builds
data/interim/   parsed extracts and temporary derived files
data/processed/ validated registries and generation metadata
outputs/synthetic/
                final synthetic datasets and manifest, ignored by git by default
outputs/qa/
                decoded manual QA copies, ignored by git by default
outputs/reports/
                generated reports and report-style summaries, ignored by git by default
docs/           methodology, assumptions, project history and sharing notes
tests/          focused unit tests
```

## Current Status

This repository is currently a Beta release candidate.

The pipeline includes unit tests for configuration loading, registry parsing, synthetic
generation, skip-logic handling and output validation. Generated synthetic outputs are still
undergoing manual validation and should be treated as Beta artefacts.

Current functionality:

- builds `participant.csv` and `questionnaire.csv` from processed registries.
- can export manual QA copies with coded values replaced by coding meanings where available.
- keeps output columns in data dictionary order.
- applies supported release-schema questionnaire logic.
- validates codings, synthetic markers, PID links, root logic fields and supported skip logic.
- keeps generated processed artefacts and outputs ignored by git by default.

## License

Code in this repository is intended to be licensed under the MIT License.

Generated synthetic outputs are not included in this repository. If synthetic datasets are
published separately, their download page should state the applicable data licence and
attribution requirements.

Source artefacts in `data/raw/` remain subject to their original source terms.

## Next Steps

The next planned stretch goal is an auditable plausibility layer for additional
synthetic-generation consistency checks that sit alongside source-derived release-schema
questionnaire logic.

Initial work will:

- generate a candidate registry for fields that may need sex-specific, age-specific,
  unit-specific or temporal constraints.
- review candidates before converting them into generation rules, starting with field
  families such as `GYN*`, date/year fields and high-quantity smoking or alcohol fields.
- keep these rules configurable and documented as additional synthetic-generation
  assumptions, separate from source-derived release-schema questionnaire logic.
- add tests and manifest metadata showing which plausibility rules were applied.
