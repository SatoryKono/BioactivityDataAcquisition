# semanticscholar_publication

> **Status**: Historical legacy guide. This page is retained only as a
> compatibility stub to avoid publishing stale contract details.

## Current Canonical Sources

- [Provider reference](../providers/semanticscholar/publication.md)
- `configs/entities/semanticscholar/publication.yaml`
- [Pipeline index](INDEX.md)

## Current Canonical Contract Summary

| Property | Value |
|----------|-------|
| Pipeline Name | `semanticscholar_publication` |
| Provider | `semanticscholar` |
| Entity Type | `publication` |
| Business Primary Keys | `["paper_id"]` |
| Loading Strategy | `full_scan_only` |
| Bronze Format | `jsonl` + `zstd` |
| Silver Format | `delta` |
| Gold Format | `delta` |

## Notes

- Current field names are snake_case, for example `paper_id`,
  `publication_doi`, `publication_pmid`, `publication_year`, `page_first`,
  `page_last`.
- Historical dashed field labels from older docs are intentionally not repeated
  here because they no longer represent the active contract.
- For new code, configs, and documentation updates, use the provider reference
  page and entity config listed above.
