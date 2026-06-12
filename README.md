# OFH Synthetic Data Generator

This repository contains a Python tool for generating reproducible synthetic Our Future
Health-style data from source documentation.

The tool generates two linked tables:

- `participant.csv`
- `questionnaire.csv`

It is intended to help researchers understand the table structure, identifiers, codings and
branching patterns before working with non-synthetic data in the TRE. The generated data is
synthetic, deterministic with a fixed seed and designed for local development, onboarding and
workflow prototyping rather than statistical analysis.

## Background

Researchers often need to understand data structure before they can write analysis code or
prepare workflows. This project provides a local synthetic dataset generator for the core OFH
participant and questionnaire entities so users can inspect table shape, develop code and test
joins before accessing non-synthetic data.

The repository is intended to share the generator and its reproducible workflow rather than a
hand-authored dataset. The generator is source-driven: it reads the public OFH source
artefacts in `data/raw/`, builds processed registries from the data dictionary, codings and
questionnaire logic, then uses those registries to generate linked synthetic participant and
questionnaire rows.

Generated datasets are ignored by git by default. Regenerate them locally from the included
source artefacts.

## What It Builds

The default config generates 200 linked participant/questionnaire rows under
`data/synthetic/`:

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

Validate generated outputs:

```bash
poetry run ofh-synthetic-data --config configs/default.yaml validate
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
data/synthetic/ final synthetic datasets, ignored by git by default
docs/           methodology, assumptions and sharing notes
tests/          focused unit tests
```

## Current Status

This repository is currently a Beta release candidate.

The pipeline includes unit tests for configuration loading, registry parsing, synthetic generation, skip-logic handling and output validation. The generated synthetic outputs are still undergoing manual review and should be treated as Beta artefacts.

Current functionality:

- builds `participant.csv` and `questionnaire.csv` from processed registries.
- keeps output columns in data dictionary order.
- applies supported questionnaire `show_if` branching logic.
- validates codings, synthetic markers, PID links, root logic fields and supported skip logic.
- keeps generated processed and synthetic artefacts ignored by git by default.
