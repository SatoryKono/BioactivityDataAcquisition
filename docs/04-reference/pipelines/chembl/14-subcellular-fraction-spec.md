---
Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# ChEMBL Subcellular Fraction Pipeline Specification

> **Status**: Historical deep spec. Current canonical contract lives in
> [../../providers/chembl/subcellular-fraction.md](../../providers/chembl/subcellular-fraction.md)
> and
> `configs/entities/chembl/subcellular_fraction.yaml`.

## Current Canonical Contract Summary

| Parameter | Value |
|-----------|-------|
| Pipeline ID | `chembl_subcellular_fraction` |
| Provider | `chembl` |
| Entity | `subcellular_fraction` |
| Business Primary Keys | `["entity_id"]` |
| Loading Strategy | `full_scan_only` |
| Silver Format | `delta` |
| Gold Format | `delta` |
| Gold Mode | `scd2` |

## Notes

- Current canonical field names are snake_case, for example `entity_id`,
  `assay_subcellular_fraction`, `assay_id`, `target_id`, `assay_type`,
  `assay_organism`.
- This page no longer republishes older dashed labels such as
  `subcellular-fraction`, `assay-count`, or `example-assay-id` as the active
  contract.
- For derived-entity behavior, validation rules, and filter settings, use the
  provider reference and entity config above.
