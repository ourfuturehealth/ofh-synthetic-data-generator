# Assumptions

This document records project-level assumptions for the Beta synthetic data generator and its
linked `participant` and `questionnaire` outputs. Generated outputs should also include
machine-readable metadata describing the exact config, seed and source files used for a run.

## Scope

- Generate linked Beta synthetic `participant` and `questionnaire` tables from Our Future Health
  documentation plus explicit assumptions.
- Target release is P14.
- Target questionnaire version is v2.
- Target entities are `participant` and `questionnaire`.
- Generate one questionnaire row per synthetic participant for Beta.
- Clinic measurements, lipid profile, geographies, linked NHS records and genetic data are out
  of scope for Beta.

## Questionnaire Logic Source

- The questionnaire logic file is aligned to the release schema, not the raw
  questionnaire capture schema.
- It is used to generate and validate release-shaped synthetic outputs.
- It is not treated as a specification for reconstructing the raw questionnaire capture flow
  or website engine behaviour.
- It documents branching logic only, not other validation rules or user-interface behaviour.

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

## Value Generation

- Coded single-choice fields are sampled from valid non-special Our Future Health coding
  values. Where special codes are available, they are included with a default 10% probability.
- Multi-select fields are stored as bracketed comma lists. Each non-special option has a 50%
  chance of selection, with at least one option selected unless a special code is used.
- Uncoded numeric fields use uniform draws within inferred ranges. Current broad limits are:
  ages `0-110`, years `3000-3026`, months `1-12`, days `0-7`, minutes `0-1440`, hours
  `0-24`, height `50-220` cm, weight `2-300` kg, default integers `0-10` and default floats
  `0-100`.
- Integer values are generated as whole numbers. Float values are rounded to two decimal
  places.

## Field Generation Metadata

- The processed field registry records whether each field should be generated or blanked.
- Fields superseded by a newer V2 field are marked blank with `superseded_by_v2_field`.
- Questionnaire fields present in V2 logic are generated unless superseded.
- Questionnaire fields selected through dictionary/coding metadata are still generated when
  they are coding-backed, non-superseded dictionary fields. These are marked
  `dictionary_coded_questionnaire_field` so they can be audited separately from logic-derived
  fields.
- Uncoded questionnaire fields outside the generated V2 scope are marked blank with
  `not_in_v2_logic`, except required metadata fields.
- Numeric ranges are inferred only for uncoded numeric fields, or numeric fields whose coding
  list contains special/missing codes but not ordinary values.
- Inferred ranges are labelled with a `numeric_range_rule` so assumptions can be audited.
- Current numeric ranges are broad Beta heuristics inferred from field names and units. For
  example, fields containing `HRS` or `HOURS` currently use a `0-24` range, even where the
  question wording may refer to hours per week. These fields are structurally valid but may
  need more specific ranges in a future plausibility pass.
- Multi-select values are serialized as bracketed comma lists, for example `[1,6]`.
- `QUESTIONNAIRE_VERSION` is generated as the configured constant value, currently `"v2"`.

## Missingness And Skip Logic

- Blank values mean a question was not asked, for example because of skip logic or v2 scoping.
- Negative codes are treated as special or missing values when a question was asked but the
  response is unknown, refused or otherwise coded as special.
- Non-standard logic patterns should be logged and handled conservatively rather than stopping
  generation.
- Supported `show_if` forms include equality, `NULL`, `is NOT NULL`, `ONE of`, `ANY of`,
  integer range tokens, `AND`, `OR` and duplicate logic rows combined as OR.
- `show_if` expressions outside the supported parser patterns currently default to shown so
  parser coverage does not unintentionally suppress fields.

## Additional Plausibility Rules

- Additional consistency rules, such as temporal coherence or out-of-range smoking
  quantities, should be documented as synthetic-generation assumptions that sit alongside
  source-derived release-schema questionnaire logic.
- Candidate field-family analysis should be performed before adding these rules. Field names,
  titles, descriptions, codings and existing `show_if` conditions should be reviewed before any
  heuristic becomes generation logic.
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
- The source logic row labelled `eb` for the medication reasons question is normalised to
  `MEDICAT_1_M` during registry build.
- The dictionary `entity` column is the preferred source for entity grouping.
