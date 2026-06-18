# Outputs

This folder is for generated artefacts from local runs.

Default generated outputs are split into:

- `synthetic/`: canonical generated synthetic datasets and manifest.
- `qa/`: decoded manual QA copies of synthetic outputs.

Generated files in these folders are ignored by git by default. Keep only README and
placeholder files under version control.

## Reading The Outputs

- Canonical synthetic datasets live in `outputs/synthetic/` and keep coded values as codes.
- Decoded review copies live in `outputs/qa/` and replace coded values with OFH coding
  meanings where possible.

The generated dataset is scoped to baseline health questionnaire V2. Fields that are out of
V2 scope, superseded by V2 fields or skipped by supported release-schema questionnaire logic
may be blank.

Synthetic IDs use a visible `SYN` prefix. Synthetic years and dates are deliberately
future-dated, generally using years `3000+`. If a workflow calculates age from `BIRTH_YEAR`,
use a synthetic reference year rather than the real current year. For example, a reference
year such as `3050` gives plausible adult ages for current generated birth years while still
keeping the data visibly synthetic.
