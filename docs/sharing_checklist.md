# Sharing Checklist

Before publishing or sharing this repository:

- Confirm the public source artefacts in `data/raw/` remain suitable for inclusion.
- Confirm the repository license.
- Confirm that generated synthetic outputs contain no observed participant-level data.
- Run `poetry run ofh-synthetic-data --config configs/default.yaml inspect-inputs`.
- Run `poetry run ofh-synthetic-data --config configs/default.yaml build-registry`.
- Run `poetry run ofh-synthetic-data --config configs/default.yaml generate`.
- Run `poetry run ofh-synthetic-data --config configs/default.yaml validate`.
- Run `poetry run pytest`.
- Run `poetry run ruff check .`.
- Confirm processed registries, synthetic outputs and `AGENTS.md` remain ignored by git unless
  there is a deliberate sharing decision.
