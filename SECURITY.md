# Security And Privacy Reporting

Do not open a public GitHub issue for security, privacy or suspected data disclosure
concerns.

This repository is intended to generate synthetic data only. Even so, please report concerns
privately if you believe the repository, source artefacts, generated outputs or dependencies
could expose sensitive information or create a security risk.

Use GitHub private vulnerability reporting through the repository Security tab if it is
enabled. If private reporting is not available, contact the repository maintainers through
your existing Our Future Health contact route and include only the minimum information needed
to describe the concern.

Do not include real participant data, credentials, TRE outputs or other sensitive
information in public issues, pull requests or discussion threads.

## Dependency Review

Python dependencies are intentionally kept small. Runtime dependencies should be limited to
packages needed for reading source artefacts, generating synthetic outputs and validating
those outputs.

Before adding a new dependency, consider whether it is required at runtime, whether the same
task can be done with the standard library or an existing dependency, and whether it adds a
file parser, network client, deserialiser or other higher-risk behaviour.

This repository includes a Dependabot configuration for Python dependencies.

Useful local checks:

```bash
poetry check --lock
poetry run pip check
```
