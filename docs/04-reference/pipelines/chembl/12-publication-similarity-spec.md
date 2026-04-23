---
Version: 1.0.0
Status: Active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-04-23'
---

# ChEMBL Publication Similarity Pipeline Specification

This document describes the current active ChEMBL Publication Similarity pipeline specification.

Canonical sources:
- [ChEMBL publication provider reference](../../providers/chembl/publication.md)
- `configs/entities/chembl/publication_similarity.yaml`

Current canonical summary:
- Current config keys use snake_case, including `loading_strategy`.
- Canonical publication identifiers and downstream field mappings are owned by the live entity config and application pipeline code.
- Treat this file as historical evidence, not as the current publication similarity contract.

## Contract References

| Artifact | Link |
| --- | --- |
| Provider reference | [publication-similarity.md](../../providers/chembl/publication-similarity.md) |
| Gold contract export | [chembl_publication_similarity_v1.0.json](../../contracts/gold/chembl_publication_similarity_v1.0.json) |
| Gold schemas index | [gold-schemas.md](../../contracts/gold-schemas.md) |
| Versioning policy | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Control | Status | Evidence |
| --- | --- | --- |
| Metadata | Pass | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Canonical source traceability | Pass | Page delegates current contract to the linked canonical source and active config surface |
| Contract linkage | Pass | [chembl_publication_similarity_v1.0.json](../../contracts/gold/chembl_publication_similarity_v1.0.json) |
| Published-page role | Pass | Historical deep spec or summary is explicitly bounded by current canonical sources |
