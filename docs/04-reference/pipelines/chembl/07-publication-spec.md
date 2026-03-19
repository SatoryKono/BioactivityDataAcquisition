# ChEMBL Publication Pipeline Specification

> **Status**: Historical deep spec. Current canonical contract lives in
> [../../providers/chembl/publication.md](../../providers/chembl/publication.md)
> and
> [../../../../configs/entities/chembl/publication.yaml](../../../../configs/entities/chembl/publication.yaml).

## Current Canonical Contract Summary

| Parameter | Value |
|-----------|-------|
| Pipeline ID | `chembl_publication` |
| Provider | `chembl` |
| Entity | `publication` |
| Business Primary Keys | `["publication_id"]` |
| Loading Strategy | `full_scan_only` |
| Silver Format | `delta` |
| Gold Format | `delta` |
| Gold Mode | `scd2` |

## Notes

- Current contract uses snake_case field names such as `publication_id`,
  `publication_doi`, `publication_pmid`, `publication_pmc_id`,
  `publication_year`, `page_first`, `page_last`, `publication_type`.
- Field aliases from older source names such as `year`, `first_page`,
  `last_page`, `doc_type`, `doi`, and `pmid` are maintained in the entity YAML
  config; that config is the authoritative source.
- This page no longer republishes the older dashed extraction tables,
  cross-provider mapping tables, or legacy schema snippets.
