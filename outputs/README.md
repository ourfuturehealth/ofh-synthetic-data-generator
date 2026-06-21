# Outputs

This folder is for generated artefacts from local runs.

Default generated outputs are split into:

- `synthetic/`: canonical generated synthetic datasets and manifest.
- `qa/`: decoded manual QA copies of synthetic outputs.

Generated files in these folders are ignored by git by default. Keep only README and
placeholder files under version control.

## Reading The Outputs

- Canonical synthetic datasets live in `outputs/synthetic/` and keep coded values as codes.
- Decoded review copies live in `outputs/qa/` and replace coded values with Our Future Health
  coding meanings where possible.

The generated dataset is scoped to baseline health questionnaire V2. Fields that are out of
V2 scope, superseded by V2 fields or skipped by supported release-schema questionnaire logic
may be blank.

Synthetic markers include IDs with a visible `SYN` prefix, `CONSENT_VERSION` values beginning
with `SYNTHETIC_` and dates or years using `3000+`.

The core participant timeline has limited temporal consistency: registration year/month,
consent year/month and questionnaire submission year/month are the same per participant and
use years `3095-3100`. `BIRTH_YEAR` uses `3000-3075`, so age calculated against registration,
consent or questionnaire submission should be adult. If analysis code needs a synthetic
current year, use `3100` as a suggested reference year rather than the real current year.
Some libraries, including pandas nanosecond datetimes, may not support years this far in the
future; parse year and month components from the strings if native date parsing fails.

Other age/year fields do not have temporal validity guarantees. For example,
`FATHER_AGE_1_1` or `IMMIGRATE_UK_YR_1_1` may not be consistent with `BIRTH_YEAR` or the core
timeline.
