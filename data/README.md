# Data

Data is split by lifecycle stage:

- `raw/`: public source artefacts, copied as received
- `interim/`: parsed extracts and temporary derived files
- `processed/`: validated registries and generation metadata
- `synthetic/`: final generated synthetic datasets and metadata

Public source artefacts in `raw/` are included for reproducibility. Generated artefacts in
`interim/`, `processed/` and `synthetic/` are ignored by git by default and should be
regenerated from source.
