---
Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-04-03'
---

# ChEMBL Compound Record Pipeline Specification

> **Status**: Canonical compact spec summary. Current detailed contract lives in
> [../../providers/chembl/compound-record.md](../../providers/chembl/compound-record.md)
> and
> `configs/entities/chembl/compound_record.yaml`.

## Current Canonical Contract Summary

| Parameter | Value |
|-----------|-------|
| Pipeline ID | `chembl_compound_record` |
| Provider | `chembl` |
| Entity | `compound_record` |
| Business Primary Keys | `["record_id"]` |
| Silver Format | `delta` |
| Gold Format | `delta` |
| Gold Mode | `scd2` |

## Notes

- Current canonical field names are snake_case, for example `record_id`,
  `molecule_id`, `publication_id`, `src_id`, `compound_key`, `compound_name`,
  `src_compound_id`.
- This page no longer republishes older dashed labels such as `record-id`,
  `molecule-id`, `publication-id`, `compound-key`, or `src-compound-id` as the
  active contract.
- For input filters, merge keys, and record-linkage validation, use the
  provider reference and entity config above.

## Contract References

| Artifact | Link |
| --- | --- |
| Provider reference | [compound-record.md](../../providers/chembl/compound-record.md) |
| Gold contract export | [chembl_compound_record_v1.0.json](../../contracts/gold/chembl_compound_record_v1.0.json) |
| Gold schemas index | [gold-schemas.md](../../contracts/gold-schemas.md) |
| Versioning policy | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Control | Status | Evidence |
| --- | --- | --- |
| Metadata | Pass | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Canonical source traceability | Pass | Page delegates current contract to the linked canonical source and active config surface |
| Contract linkage | Pass | [chembl_compound_record_v1.0.json](../../contracts/gold/chembl_compound_record_v1.0.json) |
| Published-page role | Pass | Canonical compact summary is explicitly bounded by current canonical sources |
