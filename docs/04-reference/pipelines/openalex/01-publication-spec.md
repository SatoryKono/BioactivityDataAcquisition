______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-28'

______________________________________________________________________

# OpenAlex Publication Pipeline Specification

> **Status**: Canonical compact spec summary. Current detailed contract lives in
> [../../providers/openalex/publication.md](../../providers/openalex/publication.md)
> and `configs/entities/openalex/publication.yaml`.

## Current Canonical Contract Summary

| Parameter             | Value                  |
| --------------------- | ---------------------- |
| Pipeline ID           | `openalex_publication` |
| Provider              | `openalex`             |
| Entity                | `publication`          |
| Business Primary Keys | `["openalex_id"]`      |
| Loading Strategy      | `full_scan_only`       |
| Bronze Format         | `jsonl` + `zstd`       |
| Silver Format         | `delta`                |
| Gold Format           | `delta`                |

## Notes

- Current field names are snake_case, for example `openalex_id`,
  `publication_doi`, `publication_pmid`, `publication_year`, `page_first`,
  `page_last`.
- Provider config now declares `auth_type: api_key`,
  `api_key_env: BIOETL_OPENALEX_API_KEY`, cursor paging, and credit-model rate
  headers. `BIOETL_OPENALEX_EMAIL` is contact attribution only.
- The active output keeps the canonical `grants` field for compatibility, but
  current OpenAlex funding data is read from `awards`/`funders` with legacy
  `grants` accepted only as a fallback for old replay fixtures.
- This page no longer republishes the older dashed contract tables.
- For implementation, tests, and config changes, use the provider reference and
  entity config above.

## Contract References

| Artifact             | Link                                                                                     |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Provider reference   | [publication.md](../../providers/openalex/publication.md)                                |
| Gold contract export | [openalex_publication_v1.0.json](../../contracts/gold/openalex_publication_v1.0.json)    |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Control                       | Status | Evidence                                                                                 |
| ----------------------------- | ------ | ---------------------------------------------------------------------------------------- |
| Metadata                      | Pass   | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Canonical source traceability | Pass   | Page delegates current contract to the linked canonical source and active config surface |
| Contract linkage              | Pass   | [openalex_publication_v1.0.json](../../contracts/gold/openalex_publication_v1.0.json)    |
| Published-page role           | Pass   | Canonical compact summary is explicitly bounded by current canonical sources             |
