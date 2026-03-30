---
Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# ChEMBL Assay Parameters Pipeline Specification

> **Status**: Historical deep spec. Current canonical contract lives in
> [../../providers/chembl/assay-parameters.md](../../providers/chembl/assay-parameters.md)
> and
> `configs/entities/chembl/assay_parameters.yaml`.

## Current Canonical Contract Summary

| Parameter | Value |
|-----------|-------|
| Pipeline ID | `chembl_assay_parameters` |
| Provider | `chembl` |
| Entity | `assay_parameters` |
| Business Primary Keys | `["assay_param_id"]` |
| Silver Format | `delta` |
| Gold Format | `delta` |
| Gold Mode | `scd2` |

## Notes

- Current canonical field names are snake_case, for example `assay_param_id`,
  `assay_id`, `type`, `relation`, `value`, `units`, `text_value`, `comments`,
  `standard_type`, `standard_relation`, `standard_value`, `standard_units`,
  `standard_text_value`.
- This page no longer republishes older dashed labels such as `assay-param-id`,
  `assay-id`, `text-value`, `standard-type`, or `standard-text-value` as the
  active contract.
- For required Gold fields, input filtering, and validation rules, use the
  provider reference and entity config above.
