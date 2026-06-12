# Data

Data is split by lifecycle stage:

- `raw/`: public source artefacts, copied as received
- `interim/`: parsed extracts and temporary derived files
- `processed/`: validated registries and generation metadata
- `synthetic/`: final generated synthetic datasets and metadata

Public source artefacts in `raw/` are included for reproducibility. Generated artefacts in
`interim/`, `processed/` and `synthetic/` are ignored by git by default and should be
regenerated from source.

Generated synthetic datasets are Beta artefacts. They are intended for local development,
schema exploration and workflow testing while manual validation continues.

Sources:
* Data and codings file: https://research.ourfuturehealth.org.uk/data-and-cohort/
* questionnaire (pdf) and logic file: https://ourfuturehealth.gitbook.io/our-future-health/data-types/questionnaire-data

Downloaded: 11th June 2026
