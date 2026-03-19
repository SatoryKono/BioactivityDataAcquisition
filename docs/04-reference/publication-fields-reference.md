# Publication Fields Reference

> **Status**: Historical source artifact. This page was derived from an older
> spreadsheet-driven publication field inventory and is no longer the canonical
> publication contract.
>
> Current canonical publication contracts live in:
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
- DQ/meta fields use underscore-prefixed names such as `_dq_warn`,
  `_dq_error`, `_run_id`, and `_source_batch_id`.

## Why This Page Was Demoted

- The original table set still contains older dashed and legacy names such as
  `document-chembl-id`, `page-first`, `page-last`, and `affiliation-list`.
- Those names no longer match the active normalized contract used by current
  entity configs and provider references.

## What To Use Instead

For implementation, validation, and schema work:

1. Start with the provider reference page for the relevant publication source.
2. Treat `configs/entities/{provider}/publication.yaml` as the canonical field
   and alias registry.
3. Use active guides such as
   [../03-guides/publication-validation-guide.md](../03-guides/publication-validation-guide.md)
   for workflow guidance, not this historical artifact.
