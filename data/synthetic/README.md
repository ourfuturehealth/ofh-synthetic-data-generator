# Synthetic Data

Store final generated synthetic datasets and their metadata here. These files are ignored by
git by default so they can be regenerated with explicit config and seed values.

The current `generate` command writes:

- `participant.csv`
- `questionnaire.csv`
- `manifest.json`

The manifest records the row count, seed, questionnaire version, output paths, config
snapshot, source file fingerprints and how many generated questionnaire values were skipped by
supported `show_if` logic. Output columns follow the source data dictionary order for each
entity.

Run `poetry run ofh-synthetic-data --config configs/default.yaml validate` from the repository
root to validate the current synthetic outputs.
