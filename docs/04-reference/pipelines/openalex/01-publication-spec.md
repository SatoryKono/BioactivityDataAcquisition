# OpenAlex Publication Pipeline Specification

> **Status**: Historical deep spec. Current canonical contract lives in
> [../../providers/openalex/publication.md](../../providers/openalex/publication.md)
> and [../../../../configs/entities/openalex/publication.yaml](../../../../configs/entities/openalex/publication.yaml).

## Current Canonical Contract Summary

| Parameter | Value |
|-----------|-------|
| Pipeline ID | `openalex_publication` |
| Provider | `openalex` |
| Entity | `publication` |
| Business Primary Keys | `["openalex_id"]` |
| Loading Strategy | `full_scan_only` |
| Bronze Format | `jsonl` + `zstd` |
| Silver Format | `delta` |
| Gold Format | `delta` |

## Notes

- Current field names are snake_case, for example `openalex_id`,
  `publication_doi`, `publication_pmid`, `publication_year`, `page_first`,
  `page_last`.
- This page no longer republishes the older dashed contract tables.
- For implementation, tests, and config changes, use the provider reference and
  entity config above.
