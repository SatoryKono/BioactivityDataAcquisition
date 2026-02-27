# BioETL Documentation Audit Checklist (v5.22+)

## Scope and inventory
- Confirm repo root and current target version (v5.22+).
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

## Architecture docs (docs/architecture/)
- Confirm diagrams and descriptions reflect current modules and data flow.
- Ensure ADR-010, ADR-014, ADR-017 are referenced where appropriate.
- Flag missing or outdated components.

## Provider docs (docs/providers/)
- Verify each provider is implemented and active.
- Confirm pipeline steps, inputs/outputs, and configuration keys.
- Remove or mark providers that were retired.

## Contract docs (docs/contracts/)
- Compare documented schemas against code schemas/models.
- Verify field names, types, and required/optional status.
- Ensure versioning notes match current behavior.

## Dead or orphan documentation
- For each docs file, check if it is referenced by mkdocs.yml or other docs.
- Flag files with no inbound references for deletion or archival.

## Cross-doc consistency
- Check for duplicated definitions with conflicting wording.
- Ensure version and date references are consistent.

## Verification
- Verify internal links are valid and relative paths are correct.
- Confirm RULES.md and REQUIREMENTS.md are synchronized.
- Ensure ADRs are reflected in top-level docs.
