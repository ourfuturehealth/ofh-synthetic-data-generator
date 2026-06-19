# QA Outputs

This folder is for generated manual QA artefacts.

The `export-qa` command writes decoded copies of the canonical synthetic outputs here by
default:

- `participant_decoded.csv`
- `questionnaire_decoded.csv`
- `decoded_manifest.json`

These files are intended for human review. They replace coded values with Our Future Health
coding meanings where possible, while preserving uncoded values and unmatched values.

## Interpreting Decoded QA Outputs

- Decoded QA outputs contain the same synthetic records as `outputs/synthetic/`, but coded
  values are replaced with labels where possible.
- Use these files for manual inspection, checking questionnaire flow and reviewing whether
  values look understandable.
- Use the canonical files in `outputs/synthetic/` when testing code that expects Our Future
  Health coding values, numeric codes or bracketed multi-select code lists.
- Some decoded labels are not numeric even when the canonical field is integer-coded. For
  example, a special code such as `-10` may decode to a label like `Less than a year`.
- Literal coding meanings are preserved. For example, if the Our Future Health coding meaning
  is `None`, the decoded value is `None`; this does not necessarily mean the CSV value is
  missing.

Generated QA files are ignored by git by default.
