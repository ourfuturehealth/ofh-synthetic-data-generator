# Synthetic Data

Store final generated synthetic datasets and their metadata here. These files are ignored by
git by default so they can be regenerated with explicit config and seed values.

Generated outputs are Beta artefacts while manual validation continues. They are intended for
schema exploration, local development and workflow testing rather than statistical analysis.

The current `generate` command writes:

- `participant.csv`
- `questionnaire.csv`
- `manifest.json`

The manifest records Beta status, manual validation status, row count, seed, questionnaire
version, output paths, config snapshot, source file fingerprints and how many generated
questionnaire values were skipped by supported `show_if` logic. Output columns follow the
source data dictionary order for each entity.

Run `poetry run ofh-synthetic-data --config configs/default.yaml validate` from the repository
root to validate the current synthetic outputs.

For manual QA, run:

```bash
poetry run ofh-synthetic-data --config configs/default.yaml export-qa
```

This writes decoded QA copies to `outputs/reports/` by default. Values with OFH codings are
replaced with coding meanings where possible. Uncoded values and values without a matching
coding are preserved.
