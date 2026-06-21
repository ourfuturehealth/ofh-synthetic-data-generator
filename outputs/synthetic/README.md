# Synthetic Outputs

Store canonical generated synthetic datasets and their metadata here. These files are ignored
by git by default so they can be regenerated with explicit config and seed values.

Generated outputs are Beta artefacts while manual validation continues. They are intended for
schema exploration, local development and workflow testing rather than statistical analysis.

The current `generate` command writes:

- `participant.csv`
- `questionnaire.csv`
- `manifest.json`

The manifest records Beta status, manual validation status, row count, seed, questionnaire
version, output paths, config snapshot, source file fingerprints and how many generated
questionnaire values were skipped by supported release-schema questionnaire logic. Output
columns follow the source data dictionary order for each entity.

## Interpreting Canonical Outputs

- `participant.csv` and `questionnaire.csv` link by `PID`.
- IDs are visibly synthetic: `PID` values use `SYN-...`, and questionnaire `ID` values use
  `SYN-ID-...`.
- The questionnaire output is V2-only. V1-only fields, superseded fields and fields skipped by
  supported release-schema questionnaire logic may be blank.
- Blank values mean not generated, not asked, skipped or out of V2 scope. Negative coded
  values mean an asked question has a coded special response, such as `Do not know`,
  `Prefer not to answer` or another field-specific value.
- Single-select coded fields keep Our Future Health coding values as codes. Multi-select coded
  fields are stored as bracketed code lists, for example `[1,6]`.
- Synthetic markers include `SYN` identifiers, `CONSENT_VERSION` values beginning with
  `SYNTHETIC_` and dates or years using `3000+`. For age calculations, use a synthetic
  reference year rather than the real current year. A reference year such as `3050` can be
  useful for local QA with the current generated birth-year range.
- The generated data is structurally useful but not statistically representative.

Run `poetry run ofh-synthetic-data --config configs/default.yaml validate` from the repository
root to validate the current synthetic outputs.

For manual QA, run:

```bash
poetry run ofh-synthetic-data --config configs/default.yaml export-qa
```

This writes decoded QA copies to `outputs/qa/` by default. Values with Our Future Health
codings are replaced with coding meanings where possible. Uncoded values and values without a
matching coding are preserved.
