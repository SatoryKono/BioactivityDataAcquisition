______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Publication Fields Reference

> **Status**: Historical source artifact. This page was derived from an older
> spreadsheet-driven publication field inventory and is no longer the canonical
> publication contract.
>
> Current canonical publication contracts live in:
>
> - [providers/chembl/publication.md](providers/chembl/publication.md)
> - [providers/pubmed/publication.md](providers/pubmed/publication.md)
> - [providers/crossref/publication.md](providers/crossref/publication.md)
> - [providers/openalex/publication.md](providers/openalex/publication.md)
> - [providers/semanticscholar/publication.md](providers/semanticscholar/publication.md)
> - `configs/entities/{provider}/publication.yaml`

## Current Canonical Guidance

- Canonical field names are snake_case, for example `publication_id`,
  `publication_doi`, `publication_pmid`, `publication_pmc_id`,
  `publication_year`, `publication_date`, `page_first`, `page_last`,
  `affiliation_list`, `publication_type`.
- Provider-specific legacy names such as `document_chembl_id`, `first_page`,
  `last_page`, `doi`, `pmid`, and `affiliations` are handled via
  config-level `field_aliases` where supported; they are not the canonical
  published contract.
- DQ fields use underscore-prefixed names such as `_dq_warn` and `_dq_error`.
- Occurrence-scoped lineage anchors such as `_run_id`, `_run_type`,
  `_source_batch_id`, and `_ingestion_ts` are published via sidecar/control-plane
  artifacts rather than persisted Silver/Gold rows.
- Config- and normalization-matrix artifacts may still mention those anchors in
  hash-policy or normalization contexts; such inventories are not themselves
  the persisted-row contract.

## Why This Page Was Demoted

- The original table set still contains older dashed and legacy names such as
  `document-chembl-id`, `page-first`, `page-last`, and `affiliation-list`.
- Those names no longer match the active normalized contract used by current
  entity configs and provider references.

## What To Use Instead

For implementation, validation, and schema work:

1. Start with the provider reference page for the relevant publication source.
1. Treat `configs/entities/{provider}/publication.yaml` as the canonical field
   and alias registry.
1. Use active guides such as
   [../03-guides/publication-validation-guide.md](../03-guides/publication-validation-guide.md)
   for workflow guidance, not this historical artifact.
