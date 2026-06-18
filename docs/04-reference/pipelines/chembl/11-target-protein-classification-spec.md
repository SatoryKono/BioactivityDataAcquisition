______________________________________________________________________

Version: 1.2.0
Status: Active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-17'

______________________________________________________________________

# ChEMBL Target Protein Classification Pipeline Specification

This document describes the current active ChEMBL Target Protein Classification pipeline specification.

Canonical sources:

- [ChEMBL target provider reference](../../providers/chembl/target.md)
- [ChEMBL protein class provider reference](../../providers/chembl/protein-class.md)
- `configs/entities/chembl/target_protein_classification.yaml`

Current canonical summary:

- The pipeline publishes derived ChEMBL target-to-protein-classification relation rows.
- Business identity is governed by `target_id`, `classification_status`, `component_id`, and `leaf_id`.
- Strict classification status values are governed by the active entity config and Gold contract.
- Path-first fields `path_ids`, `path_names`, `path_labels`, `depth`,
  `root_id`, and `is_leaf` are the canonical hierarchy representation.
- Legacy `l1_*` through `l5_*` fields remain backward-compatible projections
  derived from the path fields; they are not the source of truth.
- Relation rows publish normalized top-level evidence: `canonical_l1`,
  `l1_counts_for_target_type`, `l1_mapping_version`,
  `target_type_rule_version`, `l1_normalization_status`, and
  `l1_normalization_notes`.
- Composite `target_protein_class_type` is derived only from the unique
  informative `canonical_l1` values: zero informative classes gives `unknown`,
  one gives that canonical class, and two or more gives `multifunctional`.
- `unclassified_protein`, `unknown`, and missing L1 values are preserved for
  audit but are non-counting for `target_protein_class_type`.
- `major_family` is a separate L2+ derived signal and must not replace the
  top-level `target_protein_class_type` semantic boundary.
- Standalone `chembl_target` does not rely on raw `/target` carrying nested
  classification hierarchies and does not own classification summary fields in
  its hash contract.
- Composition-owned snapshot enrichment prepares relation rows from local
  `chembl.target`, `chembl.target_component`, and `chembl.protein_class` tables
  before Silver hashing. It must not perform runtime HTTP lookups against the
  external `/protein_classification` resource.
- Source manifest fields (`dataset_version`, `source_url`, `chembl_release`,
  `chembl_api_version`, `source_manifest_status`,
  `source_snapshot_fingerprint`, and snapshot row counts) make the dictionary
  build auditable. If the local snapshot lacks ChEMBL status metadata, the
  release/API fields are explicitly `unknown` and
  `source_manifest_status=release_metadata_unavailable`.
- Use the live entity config and contract export as the source of truth for current field, hash, and loading behavior.

## Contract References

| Artifact             | Link                                                                                                        |
| -------------------- | ----------------------------------------------------------------------------------------------------------- |
| Target reference     | [target.md](../../providers/chembl/target.md)                                                               |
| Protein class reference | [protein-class.md](../../providers/chembl/protein-class.md)                                              |
| Gold contract export | [chembl_target_protein_classification_v2.2.json](../../contracts/gold/chembl_target_protein_classification_v2.2.json) |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                                          |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md)                    |

## Compliance

| Control                       | Status | Evidence                                                                                                    |
| ----------------------------- | ------ | ----------------------------------------------------------------------------------------------------------- |
| Metadata                      | Pass   | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified`                    |
| Canonical source traceability | Pass   | Page delegates current contract to the linked canonical source and active config surface                    |
| Contract linkage              | Pass   | [chembl_target_protein_classification_v2.2.json](../../contracts/gold/chembl_target_protein_classification_v2.2.json) |
| Published-page role           | Pass   | Canonical compact summary is explicitly bounded by current canonical sources                                |
