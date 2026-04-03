---
Version: 1.0.0
Status: Historical deep spec.
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-04-03'
---

# ChEMBL Publication Term Pipeline Deep Spec

This page is preserved for historical analysis only. It describes an older contract shape and legacy loading-strategy wording.

Canonical sources:
- [ChEMBL publication provider reference](../../providers/chembl/publication.md)
- `configs/entities/chembl/publication_term.yaml`

Current canonical summary:
- The active config surface uses snake_case keys such as `loading_strategy`.
- Publication identifiers and alias mappings are defined in the entity config and current provider pipeline implementation.
- Use the entity config and provider reference for current behavior; do not copy field names or loading examples from this legacy page.

## Contract References

| Artifact | Link |
| --- | --- |
| Provider reference | [publication-term.md](../../providers/chembl/publication-term.md) |
| Gold contract export | [chembl_publication_term_v1.0.json](../../contracts/gold/chembl_publication_term_v1.0.json) |
| Gold schemas index | [gold-schemas.md](../../contracts/gold-schemas.md) |
| Versioning policy | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Control | Status | Evidence |
| --- | --- | --- |
| Metadata | Pass | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Canonical source traceability | Pass | Page delegates current contract to the linked canonical source and active config surface |
| Contract linkage | Pass | [chembl_publication_term_v1.0.json](../../contracts/gold/chembl_publication_term_v1.0.json) |
| Published-page role | Pass | Historical deep spec or summary is explicitly bounded by current canonical sources |
