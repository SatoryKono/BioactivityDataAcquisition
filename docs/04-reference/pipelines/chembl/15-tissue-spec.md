---
Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# ChEMBL Tissue Pipeline Specification

> **Status**: Historical deep spec. Current canonical contract lives in
> [../../providers/chembl/tissue.md](../../providers/chembl/tissue.md)
> and
> `configs/entities/chembl/tissue.yaml`.

## Current Canonical Contract Summary

| Parameter | Value |
|-----------|-------|
| Pipeline ID | `chembl_tissue` |
| Provider | `chembl` |
| Entity | `tissue` |
| Business Primary Keys | `["tissue_id"]` |
| Loading Strategy | incremental default |
| Silver Format | `delta` |
| Gold Format | `delta` |
| Gold Mode | `scd2` |

## Notes

- Current canonical field names are snake_case, for example `tissue_id`,
  `pref_name`, `bto_id`, `caloha_id`, `efo_id`, `uberon_id`.
- This page no longer republishes the older dashed field tables such as
  `tissue-id`, `pref-name`, `bto-id`, `efo-id`, and `uberon-id`.
- For DQ rules, field groups, and related file paths, use the provider
  reference and entity config above.
