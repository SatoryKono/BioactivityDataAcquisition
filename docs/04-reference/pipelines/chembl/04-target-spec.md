# ChEMBL Target Pipeline Deep Spec

Status: Historical deep spec.

This page is retained for historical context only. It predates the current snake_case unified config and field naming contract and should not be used as the canonical source for new work.

Canonical sources:
- [ChEMBL target provider reference](../../providers/chembl/target.md)
- [`configs/entities/chembl/target.yaml`](../../../../configs/entities/chembl/target.yaml)

Current canonical summary:
- Pipeline config and field names use snake_case.
- Canonical identifiers and business keys are defined in the entity config, not in this historical spec.
- Current target payloads use normalized fields such as `target_type`, `organism`, and provider-specific alias resolution configured via `field_aliases`.
- Composite and downstream enrichment behavior should be verified against the live entity config and current application code, not against this archived deep table.
