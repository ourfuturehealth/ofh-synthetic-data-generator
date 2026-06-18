# Processed Data

Store generation-ready derived artefacts here, such as canonical field registries,
allowed-value lookups, skip-logic registries and generation metadata. These files should be
reproducible from `data/raw/` plus the project code and configuration.

The `build-registry` command writes:

- `field_registry.csv`: one row per in-scope dictionary field
- `coding_registry.csv`: valid coded values used by in-scope fields
- `logic_registry.csv`: one row per V2 questionnaire logic entry
- `entity_registry.csv`: field counts and key metadata by entity
- `coverage_summary.md`: generated coverage checks and source-specific notes
- `source_manifest.json`: local raw file fingerprints, including filenames, sizes and hashes

In `logic_registry.csv`, rows with a blank `show_if` are treated as top-of-tree/root logic
fields. Generated root fields that are in scope are expected to be populated; dependent fields
are evaluated from these answers.

`field_registry.csv` also includes generation metadata used by later phases:

- `v2_inclusion_status`
- `generation_action`
- `blank_reason`
- `value_strategy`
- `generation_min` / `generation_max`
- `numeric_range_rule`
- `special_code_policy`
- `multi_select_strategy`
- `is_required_metadata`

Numeric range assumptions are auditable in `field_registry.csv` via `generation_min`,
`generation_max` and `numeric_range_rule`. Current numeric generation uses simple uniform
sampling within those ranges unless a separate rule is explicitly documented.
