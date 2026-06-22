# Outputs

This folder is for generated artefacts from local runs. Generated files are ignored by git by
default and can be regenerated with explicit config and seed values.

Default generated outputs are split into:

- `synthetic/`: canonical generated synthetic datasets and manifest.
- `qa/`: decoded manual QA copies of synthetic outputs.

Keep only this README and placeholder files under version control.

## Reading The Outputs

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

The generated data is structurally useful but not statistically representative.

## Canonical Synthetic Outputs

The `generate` command writes canonical outputs to `outputs/synthetic/`:

- `participant.csv`
- `questionnaire.csv`
- `manifest.json`

`participant.csv` and `questionnaire.csv` link by `PID`.

The canonical files keep Our Future Health coding values as codes. Single-select coded fields
contain one code. Multi-select coded fields are stored as bracketed code lists, for example
`[1,6]`.

Blank values mean not generated, not asked, skipped or out of V2 scope. Negative coded values
mean an asked question has a coded special response, such as `Do not know`, `Prefer not to
answer` or another field-specific value.

The manifest records Beta status, manual validation status, row count, seed, questionnaire
version, output paths, config snapshot, source file fingerprints, synthetic marker rules and
how many generated questionnaire values were skipped by supported release-schema
questionnaire logic. Output columns follow the source data dictionary order for each entity.

Run validation from the repository root:

```bash
poetry run ofh-synthetic-data --config configs/default.yaml validate
```

## Decoded QA Outputs

The `export-qa` command writes decoded review copies to `outputs/qa/`:

- `participant_decoded.csv`
- `questionnaire_decoded.csv`
- `decoded_manifest.json`

Decoded QA outputs contain the same synthetic records as `outputs/synthetic/`, but coded
values are replaced with Our Future Health coding meanings where possible. Uncoded values and
values without a matching coding are preserved.

Use decoded outputs for manual inspection, checking questionnaire flow and reviewing whether
values look understandable. Use the canonical files in `outputs/synthetic/` when testing code
that expects Our Future Health coding values, numeric codes or bracketed multi-select code
lists.

Some decoded labels are not numeric even when the canonical field is integer-coded. For
example, a special code such as `-10` may decode to a label like `Less than a year`.

Literal coding meanings are preserved. For example, if the Our Future Health coding meaning is
`None`, the decoded value is `None`; this does not necessarily mean the CSV value is missing.

Create decoded QA outputs from the repository root:

```bash
poetry run ofh-synthetic-data --config configs/default.yaml export-qa
```
