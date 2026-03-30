---
Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# ChEMBL Assay Pipeline Specification

> **Status**: Historical deep spec. Current canonical contract lives in
> [../../providers/chembl/assay.md](../../providers/chembl/assay.md)
> and
> `configs/entities/chembl/assay.yaml`.

## Current Canonical Contract Summary

| Parameter | Value |
|-----------|-------|
| Pipeline ID | `chembl_assay` |
| Provider | `chembl` |
| Entity | `assay` |
| Business Primary Keys | `["assay_id"]` |
| Loading Strategy | `incremental` |
| Silver Format | `delta` |
| Gold Format | `delta` |
| Gold Mode | `scd2` |

## Notes

- Current contract uses snake_case field names such as `assay_id`,
  `assay_type`, `assay_taxonomy_id`, `publication_id`, `cell_id`, `tissue_id`,
  `variant_accession`.
- Filter, DQ, and contract settings now live in the entity YAML config and are
  the authoritative source for merge keys, required fields, and enum/range
  validation.
- This page no longer republishes the older dashed API field tables or legacy
  Pandera snippets.
