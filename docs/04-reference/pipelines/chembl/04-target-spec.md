---
Version: 1.0.0
Status: Historical deep spec.
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# ChEMBL Target Pipeline Deep Spec

This page is retained for historical context only. It predates the current snake_case unified config and field naming contract and should not be used as the canonical source for new work.

Canonical sources:
- [ChEMBL target provider reference](../../providers/chembl/target.md)
- `configs/entities/chembl/target.yaml`

Current canonical summary:
- Pipeline config and field names use snake_case.
- Canonical identifiers and business keys are defined in the entity config, not in this historical spec.
- Current target payloads use normalized fields such as `target_type`, `organism`, and provider-specific alias resolution configured via `field_aliases`.
- Composite and downstream enrichment behavior should be verified against the live entity config and current application code, not against this archived deep table.

## Contract References

| Artifact | Link |
| --- | --- |
| Provider reference | [target.md](../../providers/chembl/target.md) |
| Gold contract export | [chembl_target_v1.0.json](../../contracts/gold/chembl_target_v1.0.json) |
| Gold schemas index | [gold-schemas.md](../../contracts/gold-schemas.md) |
| Versioning policy | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Control | Status | Evidence |
| --- | --- | --- |
| Metadata | Pass | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Canonical source traceability | Pass | Page delegates current contract to the linked canonical source and active config surface |
| Contract linkage | Pass | [chembl_target_v1.0.json](../../contracts/gold/chembl_target_v1.0.json) |
| Published-page role | Pass | Historical deep spec or summary is explicitly bounded by current canonical sources |
