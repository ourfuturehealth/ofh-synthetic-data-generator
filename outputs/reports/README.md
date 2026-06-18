# Reports

This folder is for generated report-style outputs, such as workflow summaries, figures and
analysis compatibility reports.

Decoded QA copies from `export-qa` are written to `outputs/qa/` by default, not here.

Generated report files are ignored by git by default.

Reports should state which input they used:

- canonical coded outputs from `outputs/synthetic/`.
- decoded manual QA outputs from `outputs/qa/`.

If a report calculates age or time intervals from synthetic future-dated fields, document the
synthetic reference year used.
