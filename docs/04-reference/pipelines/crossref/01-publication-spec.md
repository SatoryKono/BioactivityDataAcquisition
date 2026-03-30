---
Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# CrossRef Publication Pipeline Specification

> **Status**: Historical deep spec. Current canonical contract lives in
> [../../providers/crossref/publication.md](../../providers/crossref/publication.md)
> and
> `configs/entities/crossref/publication.yaml`.

## Current Canonical Contract Summary

| Parameter | Value |
|-----------|-------|
| Pipeline ID | `crossref_publication` |
| Provider | `crossref` |
| Entity | `publication` |
| Business Primary Keys | `["doi"]` |
| Loading Strategy | `full_scan_only` |
| Silver Format | `delta` |
| Gold Format | `delta` |
| Gold Mode | `scd2` |

## Notes

- Current canonical field names are snake_case, for example
  `publication_doi`, `publication_year`, `page_first`, `page_last`,
  `citations_received`, `citations_made`, `publication_type`.
- This page no longer republishes older API-shape and mixed-case labels such as
  `DOI`, `container-title`, `published-print`, `license-url`, or `doc-type`
  as the active contract.
- For DQ rules, field aliases, and implementation details, use the provider
  reference and entity config above.
