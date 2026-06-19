# Our Future Health Synthetic Data Generator

Python tooling for generating reproducible synthetic Our Future Health-style data from public
source documentation.

This Beta generator creates linked, release-shaped `participant.csv` and baseline health
questionnaire V2 `questionnaire.csv` tables for local development, onboarding and workflow
prototyping.

It is intended to help users understand table structure, identifiers, codings, joins and
questionnaire branching before working with non-synthetic data. It is not intended to provide
statistical fidelity, preserve real-world distributions, replace TRE data access, or model the
full Our Future Health P14 release.

The wider Our Future Health P14 release includes other data areas, including geography,
genetic, clinic measurement and linked NHSE data. Those are outside the current Beta scope.

Generated outputs are deterministic with a fixed seed and visibly synthetic, including
`SYN`-prefixed identifiers and deliberately future-dated years where practical.

## Beta Status

This repository is a Beta release candidate. The pipeline has unit and QA tests, but generated
synthetic outputs are still undergoing manual validation.

This repository is shared without a commitment to ongoing development, maintenance, support
response times or future feature delivery.

## Prerequisites

- Python `>=3.11,<4.0`
- Poetry
- Git
- A terminal or shell environment
- The source artefacts listed in [data/raw/README.md](data/raw/README.md)

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

Create decoded manual QA copies:

```bash
poetry run ofh-synthetic-data --config configs/default.yaml export-qa
```

Run tests and linting:

```bash
poetry run pytest
poetry run ruff check .
```

## What Gets Generated

Default generated outputs are written under `outputs/`:

- `outputs/synthetic/participant.csv`
- `outputs/synthetic/questionnaire.csv`
- `outputs/synthetic/manifest.json`
- `outputs/qa/participant_decoded.csv`
- `outputs/qa/questionnaire_decoded.csv`
- `outputs/qa/decoded_manifest.json`

Generated files are ignored by git by default. The canonical synthetic outputs keep coded
values as codes. Decoded QA outputs replace coded values with Our Future Health coding
meanings where available.

Synthetic IDs use a visible `SYN` prefix. Synthetic dates and years are deliberately
future-dated where practical; generated dates use years `3000+` as a visible synthetic marker.

## Download Synthetic Example Data 

Pre-generated synthetic example outputs are available for users who want to inspect the table
shape without running the generator:

These files correspond to the current Beta synthetic participant and questionnaire outputs.

PLACEHOLDER - these links are currently placeholders.

- [Participant synthetic data](https://a.storyblok.com/f/228028/x/c1835e7466/participant_synthetic_our_future_health.csv)
- [Questionnaire synthetic data](https://a.storyblok.com/f/228028/x/8c2a97f296/questionnaire_synthetic_our_future_health.csv)

These files are synthetic example outputs, not real participant data.
See [License](#license) for the data licence and usage terms.

## Source Artefacts

The repository includes public source artefacts under `data/raw/` so the registries and
synthetic outputs can be regenerated from a fresh checkout.

Source details and expected filenames are documented in
[data/raw/README.md](data/raw/README.md).

## Documentation

- [PROJECT.md](PROJECT.md): concise project brief and current scope.
- [docs/methodology.md](docs/methodology.md): how the pipeline works.
- [docs/assumptions.md](docs/assumptions.md): generation assumptions and current limits.
- [docs/testing.md](docs/testing.md): unit and QA test coverage.
- [data/README.md](data/README.md): source and generated data folder conventions.
- [outputs/README.md](outputs/README.md): how to interpret generated output folders.
- [SECURITY.md](SECURITY.md): security, privacy and dependency reporting.

## Project Layout

```text
src/ofh_synthetic_data/  package source code
configs/                reproducible generation settings
data/raw/               public source artefacts
data/interim/           temporary parsed extracts, ignored by git
data/processed/         generated registries, ignored by git
outputs/synthetic/      generated synthetic datasets, ignored by git
outputs/qa/             decoded manual QA outputs, ignored by git
docs/                   methodology, assumptions, testing and future work
tests/                  unit and QA tests
```

## AI Assistance

AI-assisted tooling has been used during development of this repository, including support
with drafting code, tests and documentation.

## License

Code in this repository is licensed under the MIT License. See [LICENSE](LICENSE).

Synthetic example data linked from this README is licensed under the Creative Commons
Attribution 4.0 International License (CC BY 4.0), unless otherwise stated. You are free to
share and adapt the data, including for commercial purposes, provided appropriate credit is
given.

The data is provided as-is, without warranty or any commitment to maintain, update, correct or
support it.

Generated synthetic outputs are not committed to this repository by default.

Source artefacts in `data/raw/` remain subject to their original source terms.

## Support And Feedback

Use GitHub Issues to report bugs, documentation problems or suggested improvements.

Before opening an issue, please check existing issues to avoid duplicates. Include the command
you ran, the config used, the expected behaviour and the observed behaviour where relevant.

Do not include real participant data, credentials, TRE outputs or other sensitive information
in issues.

For security, privacy or suspected data disclosure concerns, do not open a public issue.
Follow the reporting route in [SECURITY.md](SECURITY.md).

## Related Projects And Resources

This project has been informed and inspired by related external work, particularly:

- [`ofhsyn`](https://github.com/hlnicholls/ofhsyn): an R package for generating broader
  Our Future Health-style synthetic cohort data, including participant, questionnaire, clinic
  measurement, geography and linked healthcare-style tables.
- [`phenofhy` ICD tutorial](https://studiovincentstraub.github.io/phenofhy/tutorials/icd.html):
  a tutorial resource for ICD-code based phenotyping workflows, relevant to possible future
  work involving linked healthcare-style data.

These resources are not runtime dependencies of this generator. This repository currently
focuses on source-driven generation of P14-shaped `participant` and baseline questionnaire V2
outputs.
