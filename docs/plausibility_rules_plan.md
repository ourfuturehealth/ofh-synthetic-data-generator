# Plausibility Rules Beyond Source Logic

## Purpose

The source questionnaire logic defines when many questions should be shown, but it does not
encode every cross-field consistency rule that may be useful for synthetic data generation.

This plan describes a separate plausibility layer for additional synthetic-generation
assumptions. These rules should improve coherence of the Beta outputs without implying
statistical fidelity to observed OFH data.

## Principles

- Keep source-derived questionnaire logic and additional plausibility rules separate.
- Treat plausibility rules as documented synthetic-generation assumptions.
- Review candidate fields before turning naming patterns into generation rules.
- Prefer conservative rules that reduce clearly inconsistent outputs.
- Make rules configurable or easy to audit.
- Record applied rule groups in generated metadata.
- Add tests for each implemented rule family.

## Phase 1: Candidate Discovery

Create an auditable candidate registry before implementing rules.

Proposed output:

```text
data/processed/plausibility_candidates.csv
```

Suggested columns:

- `field_name`
- `entity`
- `field_family`
- `candidate_type`
- `related_context_fields`
- `source_evidence`
- `existing_show_if`
- `proposed_constraint`
- `review_status`
- `notes`

Initial candidate scans:

- sex-specific fields, starting with reviewed prefixes such as `GYN*`.
- age-specific fields, including child, pregnancy, screening and employment-related fields.
- temporal fields, including birth, registration, consent, submission, immigration and family
  history dates or years.
- unit-specific numeric fields, including days, months, years, hours, height and weight.
- high-quantity fields, including smoking, alcohol and physical activity quantities.

Candidate discovery should use `field_registry.csv`, `logic_registry.csv`,
`coding_registry.csv` and source dictionary metadata. Prefixes should be treated as review
signals, not automatic rules.

## Phase 2: Review And Rule Design

Review candidate fields before implementation.

For each candidate rule, document:

- which field or field family it applies to.
- which participant or questionnaire context fields it depends on.
- whether existing `show_if` logic already covers the constraint.
- how missing, blank, special-code or unknown context values should be handled.
- whether the output should be blanked, regenerated or constrained to a smaller range.
- whether the rule is suitable for Beta or should remain deferred.

Recommended review statuses:

- `review_needed`
- `approved`
- `deferred`
- `rejected`
- `implemented`

## Phase 3: First Rule Families

Start with narrow rule families that are easy to explain and test.

### Sex-Specific Consistency

Candidate examples:

- reviewed `GYN*` questionnaire fields.
- prostate-related fields.
- pregnancy-related fields.

Expected behaviour:

- populate fields only where the synthetic participant context is consistent with the reviewed
  rule.
- otherwise leave the field blank or use an appropriate skipped/special value, depending on
  field semantics and coding.

### Temporal Consistency

Candidate examples:

- birth year/month before registration, consent and questionnaire submission.
- registration year/month before or equal to consent year/month.
- consent year/month before or equal to questionnaire submission date.
- immigration year after birth year and before registration.
- first-child age less than or equal to last-child age where both are populated.

Expected behaviour:

- generate related dates and years from a shared synthetic participant timeline.
- use a synthetic future run/reference date for age calculation, not the real date when the
  generator is run.
- ensure every generated participant is at least 18 at the synthetic run/reference date.
- use the planned order:
  `birth < registration <= consent <= questionnaire submission`.
- keep deliberately synthetic future dates where practical.

Proposed first temporal config:

```yaml
plausibility:
  enabled: true
  temporal:
    synthetic_run_date: "3100-01-01"
    min_participant_age: 18
    max_participant_age: 90
```

The `synthetic_run_date` should be used as the anchor for participant age and age-at-event
constraints. Registration, consent and questionnaire submission dates should be generated on
or before this synthetic run/reference date.

### Quantity Bounds

Candidate examples:

- smoking quantities.
- alcohol quantities.
- activity durations and frequencies.
- coded numeric fields where negative codes may include meaningful boundary categories,
  such as `-10 = Less than a year`, as well as true missing or suppressed values.

Expected behaviour:

- replace broad fallback numeric ranges with documented field-family ranges where the current
  defaults are too broad or unclear.
- keep these ranges labelled as Beta assumptions, not validated distributions.
- review negative coded values before treating all of them as missing/special values.
- separate true special values, such as suppressed, do-not-know and prefer-not-to-answer,
  from meaningful response categories that happen to use negative numeric codes.

## Phase 4: Implementation Shape

Keep the implementation separate from source-derived registry parsing.

Suggested structure:

```text
src/ofh_synthetic_data/plausibility/
  candidates.py
  rules.py
  __init__.py
```

Suggested generated artefacts:

```text
data/processed/plausibility_candidates.csv
data/processed/plausibility_rules.csv
```

Suggested config section:

```yaml
plausibility:
  enabled: true
  rule_groups:
    - sex_specific
    - temporal
    - quantity_bounds
```

The generator should apply approved plausibility rules after source-derived value generation
and supported questionnaire logic, unless a specific rule needs to generate a shared context
first.

## Phase 5: Validation And Tests

Add focused unit tests for each rule family.

Examples:

- sex-specific rules blank reviewed fields when participant context is inconsistent.
- temporal rules keep birth year before registration and submission dates.
- related child-age fields remain ordered where both are populated.
- quantity rules keep generated values inside documented family ranges.

Add QA checks for full generated outputs:

- no populated fields violate approved plausibility rules.
- generated metadata records which plausibility rule groups were enabled.
- candidate and rule registries are reproducible from source files and config.

## Acceptance Criteria

The plausibility layer is ready when:

- candidate discovery produces an auditable registry.
- implemented rules are documented as additional synthetic assumptions.
- rules are configurable or easy to disable.
- generated metadata records applied rule groups.
- unit tests cover each implemented rule family.
- QA checks run against full generated outputs.
- source-derived questionnaire logic remains traceable separately from plausibility rules.
