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
