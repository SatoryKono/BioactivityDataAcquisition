______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-03'

______________________________________________________________________

# ChEMBL Publication Pipeline Specification

> **Status**: Canonical compact spec summary. Current detailed contract lives in
> [../../providers/chembl/publication.md](../../providers/chembl/publication.md)
> and
> `configs/entities/chembl/publication.yaml`.

## Current Canonical Contract Summary

| Parameter             | Value                |
| --------------------- | -------------------- |
| Pipeline ID           | `chembl_publication` |
| Provider              | `chembl`             |
| Entity                | `publication`        |
| Business Primary Keys | `["publication_id"]` |
| Loading Strategy      | `full_scan_only`     |
| Silver Format         | `delta`              |
| Gold Format           | `delta`              |
| Gold Mode             | `scd2`               |

## Notes

- Current contract uses snake_case field names such as `publication_id`,
  `publication_doi`, `publication_pmid`, `publication_pmc_id`,
  `publication_year`, `page_first`, `page_last`, `publication_type`.
- Field aliases from older source names such as `year`, `first_page`,
  `last_page`, `doc_type`, `doi`, and `pmid` are maintained in the entity YAML
  config; that config is the authoritative source.
- This page no longer republishes the older dashed extraction tables,
  cross-provider mapping tables, or legacy schema snippets.

## Contract References

| Artifact             | Link                                                                                     |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Provider reference   | [publication.md](../../providers/chembl/publication.md)                                  |
| Gold contract export | [chembl_publication_v1.0.json](../../contracts/gold/chembl_publication_v1.0.json)        |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Control                       | Status | Evidence                                                                                 |
| ----------------------------- | ------ | ---------------------------------------------------------------------------------------- |
| Metadata                      | Pass   | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Canonical source traceability | Pass   | Page delegates current contract to the linked canonical source and active config surface |
| Contract linkage              | Pass   | [chembl_publication_v1.0.json](../../contracts/gold/chembl_publication_v1.0.json)        |
| Published-page role           | Pass   | Canonical compact summary is explicitly bounded by current canonical sources             |
