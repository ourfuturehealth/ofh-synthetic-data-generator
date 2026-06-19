# Future Work

This document records possible improvements for later iterations. These items are not Beta
requirements unless they are explicitly promoted into scope.

## Plausibility Rules

The main proposed improvement is an auditable plausibility layer for additional
synthetic-generation assumptions that sit alongside source-derived release-schema
questionnaire logic.

Candidate rule families:

- temporal consistency, such as `birth < registration <= consent <= questionnaire submission`.
- relationship-level consistency, such as first-child age being less than or equal to
  last-child age where both are populated.
- quantity bounds beyond the current broad numeric range heuristics, such as high smoking,
  alcohol or physical activity values.
- unit-specific numeric bounds, including distinguishing hours per day from hours per week for
  fields that may plausibly exceed 24.

Implementation should start with candidate discovery rather than direct rules. A useful first
artefact would be:

```text
data/processed/plausibility_candidates.csv
```

Suggested candidate metadata:

- field name and entity.
- candidate type.
- related participant or questionnaire context fields.
- source evidence from registry, dictionary, codings or `show_if`.
- proposed constraint.
- review status.
- notes.

## Temporal Consistency

Potential first temporal rules:

- use a synthetic future reference date for age calculations.
- ensure generated participants are at least 18 at the synthetic reference date.
- keep registration before or equal to consent.
- keep consent before or equal to questionnaire submission.
- keep immigration year after birth year and before registration where populated.
- keep first-child age less than or equal to last-child age where both are populated.

## Questionnaire Version Changelog Checks

The Our Future Health questionnaire version changelog identifies several V2, V2.1 and V2.2
logic fixes that should be checked explicitly against the synthetic generator.

Suggested follow-up checks:

- improve parsing of multi-line `show_if` expressions where `AND` or `OR` appear on separate
  lines.
- check smoking change follow-ups so `SMOKE_CHG_REDUCE_REASON_2_M` and
  `SMOKE_CHG_REDUCE_ABST_1_1` are only populated when `SMOKE_CHG_2_1 = 3`.
- check vaping follow-ups because the source logic references `SMOKE_REG_1`, while the
  generated table contains `SMOKE_REG_1_M`.
- review malformed numeric expressions such as `int(=>0 & <=7)` and decide whether to
  normalise these during registry build or handle them in the `show_if` parser.
- clarify whether `QUESTIONNAIRE_VERSION = "v2"` should represent the V2 family generally or
  a specific V2 minor-version logic position.
- add focused tests for the version-changelog cases once the intended behaviour is confirmed.

## Validation

Each implemented rule family should have:

- focused unit tests.
- QA checks against full generated outputs.
- manifest metadata showing which rule groups were enabled.
- clear documentation in [docs/assumptions.md](assumptions.md).

## Additional Entity Tables

Potential later extensions outside the current Beta scope:

- participant geographies.
- clinic measurements.
- linked NHSE-style example structures.

These should only be added after the participant and questionnaire outputs are sufficiently
reviewed for the intended use case.
