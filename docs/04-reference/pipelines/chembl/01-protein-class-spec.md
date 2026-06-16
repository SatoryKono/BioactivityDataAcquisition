______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-03'

______________________________________________________________________

# ChEMBL Protein Classification Pipeline Specification

> **Status**: Canonical compact spec summary. Current detailed contract lives in
> [../../providers/chembl/protein-class.md](../../providers/chembl/protein-class.md)
> and
> `configs/entities/chembl/protein_class.yaml`.

## Current Canonical Contract Summary

| Parameter             | Value                  |
| --------------------- | ---------------------- |
| Pipeline ID           | `chembl_protein_class` |
| Provider              | `chembl`               |
| Entity                | `protein_class`        |
| Business Primary Keys | `["protein_class_id"]` |
| Silver Format         | `delta`                |
| Gold Format           | `delta`                |
| Gold Mode             | `scd2`                 |

## Notes

- Current canonical field names are snake_case, for example
  `protein_class_id`, `parent_id`, `replaced_by`, `pref_name`, `short_name`,
  `protein_class_desc`, `definition`, `class_level`, `sort_order`,
  `downgraded`.
- BioETL canonical ownership stays on the `protein_class` entity and
  `chembl_protein_class` pipeline. ChEMBL exposes the same dictionary through
  the external API resource `/protein_classification`; that provider resource
  name is not a separate BioETL entity or duplicate DTO surface.
- This page no longer republishes older dashed labels such as
  `protein-class-id`, `parent-id`, `class-level`, or `sort-order` as the
  active contract.
- For hierarchy validation, filter settings, and partitioning details, use the
  provider reference and entity config above.

## Contract References

| Artifact             | Link                                                                                     |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Provider reference   | [protein-class.md](../../providers/chembl/protein-class.md)                              |
| Gold contract export | [chembl_protein_class_v1.0.json](../../contracts/gold/chembl_protein_class_v1.0.json)    |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Control                       | Status | Evidence                                                                                 |
| ----------------------------- | ------ | ---------------------------------------------------------------------------------------- |
| Metadata                      | Pass   | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Canonical source traceability | Pass   | Page delegates current contract to the linked canonical source and active config surface |
| Contract linkage              | Pass   | [chembl_protein_class_v1.0.json](../../contracts/gold/chembl_protein_class_v1.0.json)    |
| Published-page role           | Pass   | Canonical compact summary is explicitly bounded by current canonical sources             |
