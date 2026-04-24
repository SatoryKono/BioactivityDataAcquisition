---
Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# openalex_publication (Historical)

> **Status**: This is a historical document. The current active specification is available at [openalex_publication pipeline](../../04-reference/pipelines/openalex/publication.md).

> **Redirect Notice**: This page has been moved to the archive section. For current information, please refer to the active pipeline documentation.

## Current Canonical Sources

- [Provider reference](../providers/openalex/publication.md)
- `configs/entities/openalex/publication.yaml`
- [Pipeline index](INDEX.md)

## Current Canonical Contract Summary

| Property | Value |
|----------|-------|
| Pipeline Name | `openalex_publication` |
| Provider | `openalex` |
| Entity Type | `publication` |
| Business Primary Keys | `["openalex_id"]` |
| Loading Strategy | `full_scan_only` |
| Bronze Format | `jsonl` + `zstd` |
| Silver Format | `delta` |
| Gold Format | `delta` |

## Notes

- Current field names are snake_case, for example `openalex_id`,
  `publication_doi`, `publication_pmid`, `publication_year`, `page_first`,
  `page_last`.
- Historical dashed field labels from older docs are intentionally not repeated
  here because they no longer represent the active contract.
- For new code, configs, and documentation updates, use the provider reference
  page and entity config listed above.
