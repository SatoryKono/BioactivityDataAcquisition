# [dq] Replace threshold-only composite DQ stubs with contract-derived validation bundles

Suggested labels: `architecture`, `dq`, `governance`, `P1`

Priority: `P1`

## Problem

Four active composite entities still use threshold-only DQ stubs instead of
field-level contract validation:

- `configs/quality/entities/composite/activity.yaml`
- `configs/quality/entities/composite/assay.yaml`
- `configs/quality/entities/composite/molecule.yaml`
- `configs/quality/entities/composite/target.yaml`

On current `main`, each of these files keeps only:

- `soft_fail_threshold`
- `hard_fail_threshold`
- `required_fields: []`

with no effective `entity_field_validations` or cross-field contract bundle.

By contrast, `configs/quality/entities/composite/publication.yaml` already
contains explicit `required_fields` and field validations, so this is not a
project-wide design choice. It is an unresolved gap limited to four composite
pipelines.

## Impact

- Composite Gold can pass with only threshold checks even when core join-bound
  or contract-visible fields silently degrade.
- Activity/assay/molecule/target composites do not express the same DQ posture
  that publication composite already exposes.
- Gold contracts, join-key semantics, and DQ policy are not yet tied together
  for these composite outputs, which weakens machine-verifiable governance.

## Evidence

- `configs/quality/entities/composite/activity.yaml`
- `configs/quality/entities/composite/assay.yaml`
- `configs/quality/entities/composite/molecule.yaml`
- `configs/quality/entities/composite/target.yaml`
- `configs/quality/entities/composite/publication.yaml`
- `tests/architecture/test_composite_dq_externalization.py`
- `configs/composites/activity.yaml`
- `configs/composites/assay.yaml`
- `configs/composites/molecule.yaml`
- `configs/composites/target.yaml`

## Proposed Change

Replace the threshold-only stubs for `activity`, `assay`, `molecule`, and
`target` with contract-derived DQ bundles that explicitly encode:

- required persisted fields
- join-key and lineage-anchor invariants that must remain present
- key field validations derived from Gold contracts and normalization posture
- cross-field checks where composite semantics depend on paired fields

The composite DQ files should stop being empty placeholders and become the
canonical machine-readable validation surface for these outputs.

## Acceptance Criteria

- `configs/quality/entities/composite/activity.yaml`,
  `assay.yaml`, `molecule.yaml`, and `target.yaml` no longer have
  `required_fields: []` as their only substantive content.
- Each of the four composite DQ files defines explicit required fields tied to
  the persisted contract surface.
- Each file has at least a minimal but real field-validation bundle for the
  highest-risk contract and join-bound fields.
- Architecture or contract tests fail if an active composite entity regresses
  back to a threshold-only DQ stub.
- Generated or regression evidence makes the asymmetry between
  `composite_publication` and the other four composites disappear.

## Out Of Scope

- Reworking composite merge strategy or dependency orchestration
- Changing publication composite DQ unless needed for consistency checks
- Inventing generic validations that do not map to persisted composite
  contracts or join semantics

## References

- `reports/semantic_pipeline_audit/semantic_pipeline_audit_exhaustive_2026-05-19.md`
- `docs/02-architecture/decisions/ADR-018-gold-strict-validation.md`
- `docs/02-architecture/decisions/ADR-026-composite-pipeline-pattern.md`
- `docs/02-architecture/decisions/ADR-045-dq-contract-system.md`
