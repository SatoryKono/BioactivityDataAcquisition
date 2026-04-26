______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-03'

______________________________________________________________________

# ChEMBL Cell Line Pipeline Specification

> **Status**: Canonical compact spec summary. Current detailed contract lives in
> [../../providers/chembl/cell-line.md](../../providers/chembl/cell-line.md)
> and
> `configs/entities/chembl/cell_line.yaml`.

## Current Canonical Contract Summary

| Parameter             | Value                           |
| --------------------- | ------------------------------- |
| Pipeline ID           | `chembl_cell_line`              |
| Provider              | `chembl`                        |
| Entity                | `cell-line`                     |
| Business Primary Keys | `["cell_id"]`                   |
| Loading Strategy      | `incremental` with input filter |
| Silver Format         | `delta`                         |
| Gold Format           | `delta`                         |
| Gold Mode             | `scd2`                          |

## Notes

- Current canonical field names are snake_case, for example `cell_id`,
  `cell_name`, `cell_description`, `cell_source_taxonomy_id`,
  `cellosaurus_id`, `clo_id`, and `efo_id`.
- Legacy source/API names such as `cell_chembl_id` remain relevant only as
  ingestion aliases or filter-input column names; they are not the canonical
  Silver/Gold contract surface.
- This page no longer republishes the older dashed extraction tables or
  pre-canonical Pandera examples.
- For DQ rules, filter behavior, schema groups, and contract paths, use the
  provider reference and entity config above.

## Contract References

| Artifact             | Link                                                                                     |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Provider reference   | [cell-line.md](../../providers/chembl/cell-line.md)                                      |
| Gold contract export | [chembl_cell_line_v1.0.json](../../contracts/gold/chembl_cell_line_v1.0.json)            |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Control                       | Status | Evidence                                                                                 |
| ----------------------------- | ------ | ---------------------------------------------------------------------------------------- |
| Metadata                      | Pass   | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Canonical source traceability | Pass   | Page delegates current contract to the linked canonical source and active config surface |
| Contract linkage              | Pass   | [chembl_cell_line_v1.0.json](../../contracts/gold/chembl_cell_line_v1.0.json)            |
| Published-page role           | Pass   | Canonical compact summary is explicitly bounded by current canonical sources             |
