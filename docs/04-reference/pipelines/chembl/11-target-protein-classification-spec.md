______________________________________________________________________

Version: 1.0.0
Status: Active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-01'

______________________________________________________________________

# ChEMBL Target Protein Classification Pipeline Specification

This document describes the current active ChEMBL Target Protein Classification pipeline specification.

Canonical sources:

- [ChEMBL target provider reference](../../providers/chembl/target.md)
- [ChEMBL protein class provider reference](../../providers/chembl/protein-class.md)
- `configs/entities/chembl/target_protein_classification.yaml`

Current canonical summary:

- The pipeline publishes derived ChEMBL target-to-protein-classification relation rows.
- Business identity is governed by `target_id` and `hierarchy_index`.
- Strict classification status values are governed by the active entity config and Gold contract.
- Its deterministic target-level collapse policy is the canonical summary rule
  reused by `composite_target` and by standalone `chembl_target`.
- Standalone `chembl_target` does not rely on raw `/target` carrying nested
  classification hierarchies; composition-owned ChEMBL data-source enrichment
  prepares the same relation-like rows from `/target_component` and
  `/protein_classification`.
- Use the live entity config and contract export as the source of truth for current field, hash, and loading behavior.

## Contract References

| Artifact             | Link                                                                                                        |
| -------------------- | ----------------------------------------------------------------------------------------------------------- |
| Target reference     | [target.md](../../providers/chembl/target.md)                                                               |
| Protein class reference | [protein-class.md](../../providers/chembl/protein-class.md)                                              |
| Gold contract export | [chembl_target_protein_classification_v1.0.json](../../contracts/gold/chembl_target_protein_classification_v1.0.json) |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                                          |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md)                    |

## Compliance

| Control                       | Status | Evidence                                                                                                    |
| ----------------------------- | ------ | ----------------------------------------------------------------------------------------------------------- |
| Metadata                      | Pass   | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified`                    |
| Canonical source traceability | Pass   | Page delegates current contract to the linked canonical source and active config surface                    |
| Contract linkage              | Pass   | [chembl_target_protein_classification_v1.0.json](../../contracts/gold/chembl_target_protein_classification_v1.0.json) |
| Published-page role           | Pass   | Canonical compact summary is explicitly bounded by current canonical sources                                |
