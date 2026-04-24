---
Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# Composite Publication Pipeline Specification

> **Status**: Canonical compact spec summary. Current detailed contract lives in
> [../../../03-guides/pipeline-configuration.md](../../../03-guides/pipeline-configuration.md)
> and
> `configs/composites/publication.yaml`.

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

## Contract References

| Artifact | Link |
| --- | --- |
| Canonical guide | [pipeline-configuration.md](../../../03-guides/pipeline-configuration.md) |
| Gold contract export | [composite_publication_v1.0.json](../../contracts/gold/composite_publication_v1.0.json) |
| Gold schemas index | [gold-schemas.md](../../contracts/gold-schemas.md) |
| Versioning policy | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Control | Status | Evidence |
| --- | --- | --- |
| Metadata | Pass | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Canonical source traceability | Pass | Page delegates current contract to the linked canonical source and active config surface |
| Contract linkage | Pass | [composite_publication_v1.0.json](../../contracts/gold/composite_publication_v1.0.json) |
| Published-page role | Pass | Canonical compact summary is explicitly bounded by current canonical sources |
