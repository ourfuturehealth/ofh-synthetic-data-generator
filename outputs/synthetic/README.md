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
  `SYNTHETIC_` and dates or years using `3000+`.
- Registration year/month, consent year/month and questionnaire submission year/month are the
  same per participant and use years `3095-3100`. `BIRTH_YEAR` uses `3000-3075`, so age
  calculated against registration, consent or questionnaire submission should be adult.
- If analysis code needs a synthetic current year, use `3100` as a suggested reference year.
  Some libraries, including pandas nanosecond datetimes, may not support years this far in the
  future; parse year and month components from the strings if native date parsing fails.
- Other age/year fields do not have temporal validity guarantees. For example,
  `FATHER_AGE_1_1` or `IMMIGRATE_UK_YR_1_1` may not be consistent with `BIRTH_YEAR` or the core
  timeline.
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
