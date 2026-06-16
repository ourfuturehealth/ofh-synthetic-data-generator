# Assumptions

This document records project-level assumptions for the Beta synthetic data generator and its
linked `participant` and `questionnaire` outputs. Generated outputs should also include
machine-readable metadata describing the exact config, seed and source files used for a run.

## Scope

- Generate linked Beta synthetic `participant` and `questionnaire` tables from OFH
  documentation plus explicit assumptions.
- Target release is P14.
- Target questionnaire version is v2.
- Target entities are `participant` and `questionnaire`.
- Generate one questionnaire row per synthetic participant for Beta.
- Clinic measurements, lipid profile, geographies, linked NHS records and genetic data are out
  of scope for Beta.

## Synthetic Markers

- Identifiers must visibly indicate synthetic data, using a `SYN` prefix.
- Dates should be deliberately synthetic, using future years where practical.
- Generated data must not be derived from observed participant-level records.
- `PID` values use a deterministic `SYN-...` format shared by `participant` and
  `questionnaire` rows.
- Questionnaire `ID` values use a deterministic `SYN-ID-...` format.

## Statistical Fidelity

- Statistical fidelity is not a Beta requirement.
- Default generation can use simple or uniform distributions where the documentation does not
  define distributions.
- Relationships, table shape, coding validity and skip-logic behaviour are more important than
  real-world prevalence.

## Field Generation Metadata

- The processed field registry records whether each field should be generated or blanked.
- Fields superseded by a newer V2 field are marked blank with `superseded_by_v2_field`.
- Questionnaire fields absent from V2 logic are marked blank with `not_in_v2_logic`, except
  required metadata fields.
- Numeric ranges are inferred only for uncoded numeric fields, or numeric fields whose coding
  list contains special/missing codes but not ordinary values.
- Inferred ranges are labelled with a `numeric_range_rule` so assumptions can be audited.
- Multi-select values are serialized as bracketed comma lists, for example `[1,6]`.
- `QUESTIONNAIRE_VERSION` is generated as the configured constant value, currently `"v2"`.

## Missingness And Skip Logic

- Blank values mean a question was not asked, for example because of skip logic or v2 scoping.
- Negative codes are treated as special or missing values when a question was asked but the
  response is unknown, refused or otherwise coded as special.
- Unsupported or non-standard logic should be logged and handled conservatively rather than
  stopping generation.
- Supported `show_if` forms include equality, `NULL`, `is NOT NULL`, `ONE of`, `ANY of`,
  integer range tokens, `AND`, `OR` and duplicate logic rows combined as OR.
- Unsupported `show_if` expressions currently default to shown so parser coverage does not
  unintentionally suppress fields.

## Plausibility Rules Beyond Source Logic

- The questionnaire logic workbook does not encode every real-world consistency constraint.
- Additional consistency rules, such as sex-specific responses or out-of-range smoking
  quantities, should be documented as synthetic-generation assumptions rather than
  source-derived rules.
- Candidate field-family analysis should be performed before adding these rules. Prefixes such
  as `GYN*` can help identify likely female-specific/gynaecological fields, but field names,
  titles, descriptions, codings and existing `show_if` conditions should be reviewed before any
  prefix heuristic becomes generation logic.
- Date, year, month and age fields should also be reviewed for temporal plausibility rules.
  Candidate rules include birth date preceding registration, consent and questionnaire
  submission dates; immigration year following birth year and preceding registration; and first
  child age being less than or equal to last child age where both are populated.
- These constraints are a stretch goal for improving synthetic data quality, not a Beta
  requirement unless explicitly promoted into scope.

## Source-Specific Notes

- The questionnaire logic workbook has a non-standard `section` header in `section4`.
- The questionnaire logic workbook has an extra `notes` column in `section5`.
- Some fields appear more than once in the logic workbook and need combined logic.
- The logic field `eb` does not map to the data dictionary.
- The dictionary `entity` column is the preferred source for entity grouping.
