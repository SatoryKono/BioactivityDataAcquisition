# BioETL Documentation Audit Checklist (v5.23+)

## Scope and inventory

- Confirm repo root and current target version (v5.23+).
- Identify doc entry points: README.md and mkdocs.yml.
- List all files under docs/ (use `rg --files docs`).

## RULES.md

- Verify stated rules exist in code/configs.
- Remove or update outdated rules.
- Ensure ADR-010 Local-Only and ADR-014 Determinism are reflected.
- Ensure observability requirements reflect ADR-017.

## REQUIREMENTS.md

- Ensure each requirement maps to a rule or implementation.
- Remove requirements that are no longer supported.
- Align terminology with RULES.md.

## Architecture docs (docs/02-architecture/)

- Confirm diagrams and descriptions reflect current modules and data flow.
- Ensure ADR-010, ADR-014, ADR-017 are referenced where appropriate.
- Flag missing or outdated components.

## Provider and pipeline docs (docs/04-reference/providers/, docs/04-reference/pipelines/)

- Verify each provider is implemented and active.
- Confirm pipeline steps, inputs/outputs, and configuration keys.
- Remove or mark providers that were retired.

## Contract and schema docs (docs/04-reference/contracts/, docs/04-reference/schemas/)

- Compare documented schemas against code schemas/models.
- Verify field names, types, and required/optional status.
- Ensure versioning notes match current behavior.

## Guides and operations docs (docs/03-guides/, docs/05-operations/)

- Ensure runbooks, deployment, and verification steps match current tooling.
- Verify commands and flags are current (`--run-type`, active script paths).
- Confirm onboarding/running guides align with current config layout.

## Archive and report hygiene (docs/99-archive/, docs/reports/, docs/plans/)

- Ensure archived docs are clearly marked and not referenced as active source of truth.
- Flag stale reports/plans that conflict with active docs.
- Keep active references pointed to `00-05` doc domains when possible.

## Dead or orphan documentation

- For each docs file, check if it is referenced by mkdocs.yml or other docs.
- Flag files with no inbound references for deletion, archival, or explicit index inclusion.

## Cross-doc consistency

- Check for duplicated definitions with conflicting wording.
- Ensure version and date references are consistent.

## Verification

- Verify internal links are valid and relative paths are correct.
- Confirm RULES.md and REQUIREMENTS.md are synchronized.
- Ensure ADRs are reflected in top-level docs.
- Verify strict docs build behavior (`mkdocs build --strict`) and note nav exclusions/warnings.
