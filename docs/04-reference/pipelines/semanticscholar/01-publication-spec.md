______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Semantic Scholar Publication Pipeline Specification

> **Status**: Canonical compact spec summary. Current detailed contract lives in
> [../../providers/semanticscholar/publication.md](../../providers/semanticscholar/publication.md)
> and `configs/entities/semanticscholar/publication.yaml`.

## Current Canonical Contract Summary

| Parameter             | Value                         |
| --------------------- | ----------------------------- |
| Pipeline ID           | `semanticscholar_publication` |
| Provider              | `semanticscholar`             |
| Entity                | `publication`                 |
| Business Primary Keys | `["paper_id"]`                |
| Loading Strategy      | `full_scan_only`              |
| Bronze Format         | `jsonl` + `zstd`              |
| Silver Format         | `delta`                       |
| Gold Format           | `delta`                       |

## Notes

- Current field names are snake_case, for example `paper_id`,
  `publication_doi`, `publication_pmid`, `publication_year`, `page_first`,
  `page_last`.
- This page no longer republishes the older dashed contract tables.
- For implementation, tests, and config changes, use the provider reference and
  entity config above.

## Contract References

| Artifact             | Link                                                                                                |
| -------------------- | --------------------------------------------------------------------------------------------------- |
| Provider reference   | [publication.md](../../providers/semanticscholar/publication.md)                                    |
| Gold contract export | [semanticscholar_publication_v1.0.json](../../contracts/gold/semanticscholar_publication_v1.0.json) |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                                  |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md)            |

## Compliance

| Control                       | Status | Evidence                                                                                            |
| ----------------------------- | ------ | --------------------------------------------------------------------------------------------------- |
| Metadata                      | Pass   | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified`            |
| Canonical source traceability | Pass   | Page delegates current contract to the linked canonical source and active config surface            |
| Contract linkage              | Pass   | [semanticscholar_publication_v1.0.json](../../contracts/gold/semanticscholar_publication_v1.0.json) |
| Published-page role           | Pass   | Canonical compact summary is explicitly bounded by current canonical sources                        |
