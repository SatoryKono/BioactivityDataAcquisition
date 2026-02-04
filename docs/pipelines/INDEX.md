# Publication Pipelines

Index page for publication-related data pipelines in BioETL.

---

## Purpose

These pipelines ingest, transform, and enrich publication metadata from multiple providers. They support:

- DOI resolution and metadata normalization
- Citation and reference tracking
- Cross-provider enrichment via composite merge
- Literature search and downstream analytics

All pipelines follow the Medallion Architecture (Bronze -> Silver -> Gold).

---

## Quick Navigation

| Pipeline | Provider | Layers | Primary Key(s) | Documentation |
|----------|----------|--------|----------------|---------------|
| `chembl_publication` | ChEMBL | Silver, Gold | `document_chembl_id` | [Spec](chembl/07-publication-spec.md) |
| `chembl_publication_similarity` | ChEMBL | Silver, Gold | `doc_id_1`, `doc_id_2` | [Spec](chembl/12-publication-similarity-spec.md) |
| `chembl_publication_term` | ChEMBL | Silver, Gold | `doc_id`, `term_type`, `term_value` | [Spec](chembl/11-publication-term-spec.md) |
| `crossref_publication` | CrossRef | Silver, Gold | `doi` | [Spec](crossref/01-publication-spec.md) |
| `openalex_publication` | OpenAlex | Silver, Gold | `openalex_id` | [Spec](openalex/01-publication-spec.md) |
| `pubmed_publication` | PubMed | Silver, Gold | `pmid` | [Spec](pubmed/01-publication-spec.md) |
| `semanticscholar_publication` | Semantic Scholar | Silver, Gold | `paper_id` | [Spec](semanticscholar/01-publication-spec.md) |
| `composite_publication` | Composite | Silver, Gold | `document_chembl_id` (seed) | [Spec](composite/01-publication-spec.md) |

---

## Composite Pipeline Summary

The `composite_publication` pipeline merges provider Silver tables into a unified Gold table.

- **Seed**: `chembl_publication`
- **Enrichers**: `crossref_publication`, `openalex_publication`, `pubmed_publication`, `semanticscholar_publication`
- **Config**: `configs/pipelines/composite/publication.yaml`
- **Field map**: `configs/data_schema/composite/publication.yaml`

---

## Naming Conventions

Pipeline names follow these patterns:

| Pattern | Example | Notes |
|---------|---------|-------|
| `{provider}_{entity}` | `pubmed_publication` | Standard single-entity pipeline |
| `{provider}_{entity}_{variant}` | `chembl_publication_term` | Variant/auxiliary pipeline |
| `composite_{entity}` | `composite_publication` | Multi-provider merge pipeline |

---

## Related ADRs

- [ADR-025](../02-architecture/decisions/ADR-025-pipeline-config-unification.md): Pipeline config unification
- [ADR-026](../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md): Composite pipeline pattern
- [ADR-027](../02-architecture/decisions/ADR-027-dq-rules-externalization.md): DQ rules externalization
- [ADR-028](../02-architecture/decisions/ADR-028-filter-rules-externalization.md): Filter rules externalization
- [ADR-029](../02-architecture/decisions/ADR-029-output-metadata-unification.md): Output metadata unification
- [ADR-030](../02-architecture/decisions/ADR-030-publication-pagination-strategy.md): Publication pagination strategy
- [ADR-031](../02-architecture/decisions/ADR-031-loading-strategy-formalization.md): Loading strategy formalization
- [ADR-032](../02-architecture/decisions/ADR-032-unified-http-client.md): Unified HTTP client pattern

---

*Last updated: 2026-02-03*
