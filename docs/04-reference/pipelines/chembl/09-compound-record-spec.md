# ChEMBL Compound Record Pipeline Specification

> **Status**: Historical deep spec. Current canonical contract lives in
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
