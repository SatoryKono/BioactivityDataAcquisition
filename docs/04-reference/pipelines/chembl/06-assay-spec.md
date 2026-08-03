______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-03'

______________________________________________________________________

# ChEMBL Assay Pipeline Specification

> **Status**: Canonical compact spec summary. Current detailed contract lives in
> [../../providers/chembl/assay.md](../../providers/chembl/assay.md)
> and
> `configs/entities/chembl/assay.yaml`.

## Current Canonical Contract Summary

| Parameter             | Value          |
| --------------------- | -------------- |
| Pipeline ID           | `chembl_assay` |
| Provider              | `chembl`       |
| Entity                | `assay`        |
| Business Primary Keys | `["assay_id"]` |
| Loading Strategy      | `incremental`  |
| Silver Format         | `delta`        |
| Gold Format           | `delta`        |
| Gold Mode             | `scd2`         |

## Notes

- Current contract uses snake_case field names such as `assay_id`,
  `assay_type`, `assay_taxonomy_id`, `publication_id`, `cell_id`, `tissue_id`,
  `variant_accession`.
- Filter, DQ, and contract settings now live in the entity YAML config and are
  the authoritative source for merge keys, required fields, and enum/range
  validation.
- This page no longer republishes the older dashed API field tables or legacy
  Pandera snippets.

## Contract References

| Artifact             | Link                                                                                     |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Provider reference   | [assay.md](../../providers/chembl/assay.md)                                              |
| Gold contract export | [chembl_assay_v1.0.json](../../contracts/gold/chembl_assay_v1.0.json)                    |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Control                       | Status | Evidence                                                                                 |
| ----------------------------- | ------ | ---------------------------------------------------------------------------------------- |
| Metadata                      | Pass   | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Canonical source traceability | Pass   | Page delegates current contract to the linked canonical source and active config surface |
| Contract linkage              | Pass   | [chembl_assay_v1.0.json](../../contracts/gold/chembl_assay_v1.0.json)                    |
| Published-page role           | Pass   | Canonical compact summary is explicitly bounded by current canonical sources             |
