______________________________________________________________________

Version: 1.0.0
Status: published
Class: runbook
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-14'

______________________________________________________________________

# Migration Runbook: Canonical Semantic Field Unification

This runbook operationalizes the semantic-field-unification wave across dev,
staging and prod.

## Decision Anchors

- `ADR-039`: unified entity configs are the source of truth for canonical
  schema/filter/contract surfaces.
- `ADR-026`: composite `join_keys` and `field_mappings` must use canonical
  names.
- `ADR-018`: Gold validation must bind to canonical field names.
- `ADR-045`: DQ contracts must bind to canonical field names.

## Source Artifacts

- Registry: `configs/field_registry/canonical_registry.json`
- Published reference: `docs/04-reference/contracts/canonical-field-registry.md`
- CSV matrix: `docs/04-reference/contracts/canonical-field-registry.csv`

## Branch

- Registry/docs only: `feature/canonical-registry`
- Runtime surface changes: `feature/rename-<cluster>`
- Composite adjustments: `feature/update-composite-joins`

## CI/QA

Run at minimum:

1. `./.venv/bin/python -m pytest tests/unit/infrastructure/config/test_semantic_field_registry_loader.py`
2. `./.venv/bin/python -m pytest tests/integration/config/test_semantic_field_unification_contract.py`
3. Targeted provider/composite tests for any cluster being changed
4. `uv run ruff check src/bioetl tests`

Release gate expectations:

- legacy provider-native names may remain only at external ingestion boundaries
- canonical names must be used for internal filter fields, key nullability,
  composite join keys and Gold-facing contracts
- registry JSON and published CSV/markdown must stay in sync

## Pull Request

Checklist:

- registry updated first
- runtime/config changes limited to the clusters declared in the registry
- tests prove canonical internal naming did not regress
- rollback path documented in PR body when a runtime rename is introduced

## Merge

- merge after green CI only
- if a PR changes canonical mappings, include the affected cluster IDs in the
  merge summary
- treat new legacy aliases as exceptional and registry-reviewed only

## Deploy

1. Apply to `dev`
2. Validate canonical filter/join behavior on smoke datasets
3. Promote to `staging`
4. Compare composite outputs and Gold schema conformance
5. Promote to `prod`

## Rollback

Registry-only rollback:

- revert the registry/doc/test commit

Runtime rename rollback:

1. restore previous registry row for the cluster
2. restore previous internal field mapping in entity/composite config
3. rerun targeted provider/composite tests
4. deploy reverted config set through the same dev -> staging -> prod path

## Notes

- Existing BioETL runtime already uses canonical internal fields for the
  clusters listed in the registry. This runbook therefore governs drift
  prevention and future cluster waves, not a first-time bulk rename.
