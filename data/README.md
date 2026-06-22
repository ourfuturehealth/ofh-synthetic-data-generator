# Data

Data is split by lifecycle stage:

- `raw/`: public source artefacts, copied as received
- `processed/`: validated registries and generation metadata

Public source artefacts in `raw/` are included for reproducibility. Source filenames, links
and source terms are documented in [raw/README.md](raw/README.md).

Generated artefacts in `processed/` are ignored by git by default and should be regenerated
from source.

Generated synthetic datasets and QA artefacts are written under `outputs/` by default. They
are Beta artefacts intended for local development, schema exploration and workflow testing
while manual validation continues.
