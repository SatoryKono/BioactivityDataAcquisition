# Composite Publication Pipeline Specification

> **Status**: Historical deep spec. Current canonical contract lives in
> [../../../03-guides/pipeline-configuration.md](../../../03-guides/pipeline-configuration.md)
> and
> [../../../../configs/composites/publication.yaml](../../../../configs/composites/publication.yaml).

## Current Canonical Contract Summary

| Parameter | Value |
|-----------|-------|
| Pipeline ID | `composite_publication` |
| Provider | `composite` |
| Entity | `publication` |
| Seed Pipeline | `chembl_publication` |
| Enrichers | `crossref_publication`, `openalex_publication`, `pubmed_publication`, `semanticscholar_publication` |
| Conflict Resolution | `seed_priority` |
| Preserve All Sources | `true` |
| Silver Output | `data/output/silver/composite/publication` |
| Gold Output | `data/output/gold/composite/publication` |

## Notes

- Current contract uses snake_case field names such as `publication_id`,
  `publication_doi`, `publication_pmid`, `page_first`, `page_last`,
  `publication_year`.
- When `preserve_all_sources: true`, provider-qualified fields such as
  `crossref.publication.title` remain part of the merged output unless the
  config explicitly excludes them.
- This page no longer republishes the older dashed field tables and merge notes.
- For implementation, filters, DQ rules, and field priority changes, use the
  composite YAML config above.
