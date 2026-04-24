______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-03'

______________________________________________________________________

# ChEMBL Tissue Pipeline Specification

> **Status**: Canonical compact spec summary. Current detailed contract lives in
> [../../providers/chembl/tissue.md](../../providers/chembl/tissue.md)
> and
> `configs/entities/chembl/tissue.yaml`.

## Current Canonical Contract Summary

| Parameter             | Value               |
| --------------------- | ------------------- |
| Pipeline ID           | `chembl_tissue`     |
| Provider              | `chembl`            |
| Entity                | `tissue`            |
| Business Primary Keys | `["tissue_id"]`     |
| Loading Strategy      | incremental default |
| Silver Format         | `delta`             |
| Gold Format           | `delta`             |
| Gold Mode             | `scd2`              |

## Notes

- Current canonical field names are snake_case, for example `tissue_id`,
  `pref_name`, `bto_id`, `caloha_id`, `efo_id`, `uberon_id`.
- This page no longer republishes the older dashed field tables such as
  `tissue-id`, `pref-name`, `bto-id`, `efo-id`, and `uberon-id`.
- For DQ rules, field groups, and related file paths, use the provider
  reference and entity config above.

## Contract References

| Artifact             | Link                                                                                     |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Provider reference   | [tissue.md](../../providers/chembl/tissue.md)                                            |
| Gold contract export | [chembl_tissue_v1.0.json](../../contracts/gold/chembl_tissue_v1.0.json)                  |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Control                       | Status | Evidence                                                                                 |
| ----------------------------- | ------ | ---------------------------------------------------------------------------------------- |
| Metadata                      | Pass   | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Canonical source traceability | Pass   | Page delegates current contract to the linked canonical source and active config surface |
| Contract linkage              | Pass   | [chembl_tissue_v1.0.json](../../contracts/gold/chembl_tissue_v1.0.json)                  |
| Published-page role           | Pass   | Canonical compact summary is explicitly bounded by current canonical sources             |
