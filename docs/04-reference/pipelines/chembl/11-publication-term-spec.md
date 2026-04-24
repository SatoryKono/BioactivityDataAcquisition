______________________________________________________________________

Version: 1.0.0
Status: Active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-23'

______________________________________________________________________

# ChEMBL Publication Term Pipeline Specification

> **Notice**: This document contains historical references. For the most current information, always refer to the active entity configuration at `configs/entities/chembl/publication_term.yaml` and the [ChEMBL provider reference](../../providers/chembl/publication-term.md).

This document describes the current active ChEMBL Publication Term pipeline specification.

Canonical sources:

- [ChEMBL publication provider reference](../../providers/chembl/publication.md)
- `configs/entities/chembl/publication_term.yaml`

Current canonical summary:

- The active config surface uses snake_case keys such as `loading_strategy`.
- Publication identifiers and alias mappings are defined in the entity config and current provider pipeline implementation.
- Use the entity config and provider reference for current behavior; do not copy field names or loading examples from this legacy page.

## Contract References

| Artifact             | Link                                                                                        |
| -------------------- | ------------------------------------------------------------------------------------------- |
| Provider reference   | [publication-term.md](../../providers/chembl/publication-term.md)                           |
| Gold contract export | [chembl_publication_term_v1.0.json](../../contracts/gold/chembl_publication_term_v1.0.json) |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                          |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md)    |

## Compliance

| Control                       | Status | Evidence                                                                                    |
| ----------------------------- | ------ | ------------------------------------------------------------------------------------------- |
| Metadata                      | Pass   | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified`    |
| Canonical source traceability | Pass   | Page delegates current contract to the linked canonical source and active config surface    |
| Contract linkage              | Pass   | [chembl_publication_term_v1.0.json](../../contracts/gold/chembl_publication_term_v1.0.json) |
| Published-page role           | Pass   | Historical deep spec or summary is explicitly bounded by current canonical sources          |
