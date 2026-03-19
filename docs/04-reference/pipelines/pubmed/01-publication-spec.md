# PubMed Publication Pipeline Specification

> **Status**: Historical deep spec. Current canonical contract lives in
> [../../providers/pubmed/publication.md](../../providers/pubmed/publication.md)
> and
> [../../../../configs/entities/pubmed/publication.yaml](../../../../configs/entities/pubmed/publication.yaml).

## Current Canonical Contract Summary

| Parameter | Value |
|-----------|-------|
| Pipeline ID | `pubmed_publication` |
| Provider | `pubmed` |
| Entity | `publication` |
| Business Primary Keys | `["pmid"]` |
| Loading Strategy | `full_scan_only` |
| Silver Format | `delta` |
| Gold Format | `delta` |
| Gold Mode | `scd2` |

## Notes

- Current canonical field names are snake_case, for example `pmid`, `pmc_id`,
  `publication_year`, `publication_date`, `page_first`, `page_last`,
  `subject_mesh`, `subject_keywords`, `affiliation_structured`.
- This page no longer republishes older XML-path and dashed labels such as
  `ArticleIdList/PMC`, `mesh-headings`, `abstract-structured`, `pmc-id`, or
  `journal-iso-abbrev` as the active contract.
- For quality rules, aliases, and extraction details, use the provider
  reference and entity config above.
