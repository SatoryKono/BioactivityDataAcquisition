______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# CrossRef Publication Pipeline Specification

> **Status**: Canonical compact spec summary. Current detailed contract lives in
> [../../providers/crossref/publication.md](../../providers/crossref/publication.md)
> and
> `configs/entities/crossref/publication.yaml`.

## Current Canonical Contract Summary

| Parameter             | Value                  |
| --------------------- | ---------------------- |
| Pipeline ID           | `crossref_publication` |
| Provider              | `crossref`             |
| Entity                | `publication`          |
| Business Primary Keys | `["doi"]`              |
| Loading Strategy      | `full_scan_only`       |
| Silver Format         | `delta`                |
| Gold Format           | `delta`                |
| Gold Mode             | `scd2`                 |

## Notes

- Current canonical field names are snake_case, for example
  `publication_doi`, `publication_year`, `page_first`, `page_last`,
  `citations_received`, `citations_made`, `publication_type`.
- Structured semantic payloads now follow the shared raw/canonical sidecar
  contract used across non-ChEMBL publication providers:
  `author_details_raw_json` / `author_details_canonical_json` and
  `references_raw_json` / `references_canonical_json`.
- Derived publication taxonomy fields
  `publication_type_unified`, `publication_subclass`, and `publication_class`
  are validated against the shared Cross-provider taxonomy rather than ad-hoc
  per-provider enums.
- This page no longer republishes older API-shape and mixed-case labels such as
  `DOI`, `container-title`, `published-print`, `license-url`, or `doc-type`
  as the active contract.
- For DQ rules, field aliases, and implementation details, use the provider
  reference and entity config above.

## Contract References

| Artifact             | Link                                                                                     |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Provider reference   | [publication.md](../../providers/crossref/publication.md)                                |
| Gold contract export | [crossref_publication_v1.0.json](../../contracts/gold/crossref_publication_v1.0.json)    |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Control                       | Status | Evidence                                                                                 |
| ----------------------------- | ------ | ---------------------------------------------------------------------------------------- |
| Metadata                      | Pass   | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Canonical source traceability | Pass   | Page delegates current contract to the linked canonical source and active config surface |
| Contract linkage              | Pass   | [crossref_publication_v1.0.json](../../contracts/gold/crossref_publication_v1.0.json)    |
| Published-page role           | Pass   | Canonical compact summary is explicitly bounded by current canonical sources             |
