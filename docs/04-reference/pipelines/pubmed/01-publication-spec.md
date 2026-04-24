---
Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# PubMed Publication Pipeline Specification

> **Status**: Canonical compact spec summary. Current detailed contract lives in
> [../../providers/pubmed/publication.md](../../providers/pubmed/publication.md)
> and
> `configs/entities/pubmed/publication.yaml`.

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

## Contract References

| Artifact | Link |
| --- | --- |
| Provider reference | [publication.md](../../providers/pubmed/publication.md) |
| Gold contract export | [pubmed_publication_v1.0.json](../../contracts/gold/pubmed_publication_v1.0.json) |
| Gold schemas index | [gold-schemas.md](../../contracts/gold-schemas.md) |
| Versioning policy | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Control | Status | Evidence |
| --- | --- | --- |
| Metadata | Pass | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Canonical source traceability | Pass | Page delegates current contract to the linked canonical source and active config surface |
| Contract linkage | Pass | [pubmed_publication_v1.0.json](../../contracts/gold/pubmed_publication_v1.0.json) |
| Published-page role | Pass | Canonical compact summary is explicitly bounded by current canonical sources |
