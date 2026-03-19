# ChEMBL Cell Line Pipeline Specification

> **Status**: Historical deep spec. Current canonical contract lives in
> [../../providers/chembl/cell-line.md](../../providers/chembl/cell-line.md)
> and
> [../../../../configs/entities/chembl/cell_line.yaml](../../../../configs/entities/chembl/cell_line.yaml).

## Current Canonical Contract Summary

| Parameter | Value |
|-----------|-------|
| Pipeline ID | `chembl_cell_line` |
| Provider | `chembl` |
| Entity | `cell-line` |
| Business Primary Keys | `["cell_id"]` |
| Loading Strategy | `incremental` with input filter |
| Silver Format | `delta` |
| Gold Format | `delta` |
| Gold Mode | `scd2` |

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
