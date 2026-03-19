# Semantic Scholar Publication Pipeline Specification

> **Status**: Historical deep spec. Current canonical contract lives in
> [../../providers/semanticscholar/publication.md](../../providers/semanticscholar/publication.md)
> and [../../../../configs/entities/semanticscholar/publication.yaml](../../../../configs/entities/semanticscholar/publication.yaml).

## Current Canonical Contract Summary

| Parameter | Value |
|-----------|-------|
| Pipeline ID | `semanticscholar_publication` |
| Provider | `semanticscholar` |
| Entity | `publication` |
| Business Primary Keys | `["paper_id"]` |
| Loading Strategy | `full_scan_only` |
| Bronze Format | `jsonl` + `zstd` |
| Silver Format | `delta` |
| Gold Format | `delta` |

## Notes

- Current field names are snake_case, for example `paper_id`,
  `publication_doi`, `publication_pmid`, `publication_year`, `page_first`,
  `page_last`.
- This page no longer republishes the older dashed contract tables.
- For implementation, tests, and config changes, use the provider reference and
  entity config above.
