# Publication Pipelines

Index page for all publication-related data pipelines in BioETL.

---

## Purpose

This section documents the publication data pipelines that ingest, transform, and enrich scholarly publication metadata from multiple providers. These pipelines form the foundation for:

- **DOI Resolution**: Resolving publication identifiers to full metadata
- **Citation Analysis**: Tracking citation counts and research impact
- **Publication Enrichment**: Combining data from multiple sources via composite pipeline
- **Literature Search**: Supporting drug discovery literature reviews

All pipelines follow the Medallion Architecture (Bronze → Silver → Gold) with full lineage tracking and data quality monitoring.

---

## Quick Navigation

| Pipeline | Provider | Layers | Primary Key(s) | Documentation |
|----------|----------|--------|----------------|---------------|
| `chembl_publication` | ChEMBL | Silver, Gold | `doc_id` | [chembl-publication.md](./chembl-publication.md) |
| `chembl_publication_similarity` | ChEMBL | Silver, Gold | `doc_id_1`, `doc_id_2` | [chembl-publication-similarity.md](./chembl-publication-similarity.md) |
| `chembl_publication_term` | ChEMBL | Silver, Gold | `doc_id`, `term_type`, `term_value` | [chembl-publication-term.md](./chembl-publication-term.md) |
| `crossref_publication` | CrossRef | Silver, Gold | `doi` | [crossref-publication.md](./crossref-publication.md) |
| `openalex_publication` | OpenAlex | Silver, Gold | `openalex_id` | [openalex-publication.md](./openalex-publication.md) |
| `pubmed_publication` | PubMed | Silver, Gold | `pmid` | [pubmed-publication.md](./pubmed-publication.md) |
| `semanticscholar_publication` | Semantic Scholar | Silver, Gold | `paper_id` | [semanticscholar-publication.md](./semanticscholar-publication.md) |
| `composite_publication` | Multi-provider | Composite | `doi` (seed) | [composite-publication.md](./composite-publication.md) |

---

## Pipeline Categories

### Provider-Specific Pipelines

These pipelines ingest data from a single source and produce normalized Silver/Gold tables:

| Pipeline | Use Case | Rate Limit |
|----------|----------|------------|
| **chembl_publication** | Drug discovery literature from ChEMBL | 10 req/sec |
| **crossref_publication** | DOI metadata resolution | Polite pool |
| **openalex_publication** | Open scholarly metadata with title fallback | ~10 req/sec |
| **pubmed_publication** | Biomedical literature via Entrez | 3 req/sec |
| **semanticscholar_publication** | Citation metrics, TLDR, author analytics | 1 req/sec |

### ChEMBL Auxiliary Pipelines

Supporting pipelines for ChEMBL publication analysis:

| Pipeline | Purpose |
|----------|---------|
| **chembl_publication_similarity** | Publication similarity scores (Tanimoto) |
| **chembl_publication_term** | MeSH terms, keywords, abstract terms |

### Composite Pipeline

| Pipeline | Purpose |
|----------|---------|
| **composite_publication** | Merges Silver data from all providers into unified Gold table |

---

## Naming Conventions

### Pipeline Names

Pipeline names follow the pattern: `{provider}_{entity}` or `{provider}_{entity}_{variant}`

| Pattern | Example | Notes |
|---------|---------|-------|
| `{provider}_{entity}` | `pubmed_publication` | Standard single-entity pipeline |
| `{provider}_{entity}_{variant}` | `chembl_publication_term` | Variant/auxiliary pipeline |
| `composite_{entity}` | `composite_publication` | Multi-provider merge pipeline |

### Primary Keys

Each provider uses its native identifier as primary key:

| Provider | Primary Key | Format |
|----------|-------------|--------|
| ChEMBL | `doc_id` | `CHEMBL{number}` (e.g., `CHEMBL1234567`) |
| CrossRef | `doi` | `10.xxxx/...` (normalized lowercase) |
| OpenAlex | `openalex_id` | `W{number}` (e.g., `W2148763428`) |
| PubMed | `pmid` | Numeric string (e.g., `"12345678"`) |
| Semantic Scholar | `paper_id` | 40-char hex (e.g., `abc123...`) |

### Cross-Reference Fields

All publication pipelines include cross-reference fields for joining:

- `doi` - Digital Object Identifier (normalized)
- `pmid` - PubMed ID
- `pmc_id` - PubMed Central ID (where available)

---

## Dependencies Overview

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     INPUT: DOIs / PMIDs / Titles                    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────┐           ┌───────────────┐           ┌───────────────┐
│    PubMed     │           │   CrossRef    │           │   OpenAlex    │
│  (Bronze→    │           │  (Bronze→    │           │  (Bronze→    │
│   Silver)     │           │   Silver)     │           │   Silver)     │
└───────┬───────┘           └───────┬───────┘           └───────┬───────┘
        │                           │                           │
        │   ┌───────────────┐       │       ┌───────────────┐   │
        │   │    ChEMBL     │       │       │ SemanticScholar│   │
        │   │  Publication  │       │       │  (Bronze→    │   │
        │   │  (Bronze→    │       │       │   Silver)     │   │
        │   │   Silver)     │       │       └───────┬───────┘   │
        │   └───────┬───────┘       │               │           │
        │           │               │               │           │
        │   ┌───────┴───────┐       │               │           │
        │   │ ChEMBL Term   │       │               │           │
        │   │ (Aggregations)│       │               │           │
        │   └───────┬───────┘       │               │           │
        │           │               │               │           │
        └───────────┴───────────────┴───────────────┴───────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │    composite_publication      │
                    │  (Silver merge → Gold)        │
                    │                               │
                    │  Seed: pubmed_publication     │
                    │  Enrichers:                   │
                    │   - crossref_publication      │
                    │   - openalex_publication      │
                    │   - semanticscholar_pub...    │
                    │   - chembl_publication        │
                    │   - chembl_publication_term   │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │         GOLD OUTPUT           │
                    │   Unified publication table   │
                    └───────────────────────────────┘
```

### Composite Pipeline Dependencies

The `composite_publication` pipeline consumes Silver tables from all providers:

| Role | Pipeline | Join Keys | Priority |
|------|----------|-----------|----------|
| **Seed** | `pubmed_publication` | - | 1 (highest) |
| Enricher | `crossref_publication` | `doi` | 2 |
| Enricher | `openalex_publication` | `doi`, `pmid` | 3 |
| Enricher | `semanticscholar_publication` | `doi`, `pmid` | 4 |
| Enricher | `chembl_publication` | `doi`, `pmid` | 5 |
| Enricher | `chembl_publication_term` | `doc_id` → `doi` | 6 (aggregated) |

### ChEMBL Term Aggregations

The `chembl_publication_term` pipeline provides aggregated term data that is merged into composite publications:

- **MeSH Terms**: Medical Subject Headings
- **Keywords**: Author-assigned keywords
- **Abstract Terms**: Extracted terms from abstracts

---

## Configuration Files

### Pipeline Configs

| Pipeline | Config Path |
|----------|-------------|
| `chembl_publication` | `configs/pipelines/chembl/publication.yaml` |
| `chembl_publication_similarity` | `configs/pipelines/chembl/publication_similarity.yaml` |
| `chembl_publication_term` | `configs/pipelines/chembl/publication_term.yaml` |
| `crossref_publication` | `configs/pipelines/crossref/publication.yaml` |
| `openalex_publication` | `configs/pipelines/openalex/publication.yaml` |
| `pubmed_publication` | `configs/pipelines/pubmed/publication.yaml` |
| `semanticscholar_publication` | `configs/pipelines/semanticscholar/publication.yaml` |
| `composite_publication` | `configs/pipelines/composite/publication.yaml` |

### Schema Definitions

| Type | Location |
|------|----------|
| Silver (PyArrow) | `src/bioetl/infrastructure/schemas/silver.py` |
| Gold (Pandera) | `src/bioetl/domain/contracts/gold/publications.py` |
| Composite Gold | **TODO** - needs definition |

---

## TODO

### Documentation

- [ ] Create `chembl-publication.md`
- [ ] Create `chembl-publication-similarity.md`
- [ ] Create `chembl-publication-term.md`
- [ ] Create `crossref-publication.md`
- [ ] Create `pubmed-publication.md`
- [ ] Create `composite-publication.md`

### Schema Contracts

- [ ] **Composite Gold Contract Missing**: Define Pandera schema for `composite_publication` Gold layer
- [ ] **JSON Contract Export**: Generate JSON schema contracts for all publication Gold schemas
- [ ] **Cross-Provider Field Mapping**: Document field coalescing rules in composite merger

### Pipeline Enhancements

- [ ] Add incremental loading support when APIs stabilize cursor pagination
- [ ] Implement citation network extraction for SemanticScholar
- [ ] Add ORCID-based author disambiguation across providers

---

## Maintainers / Ownership

| Area | Owner | Contact |
|------|-------|---------|
| Publication Pipelines | *TBD* | *TBD* |
| Composite Pipeline | *TBD* | *TBD* |
| Schema Contracts | *TBD* | *TBD* |

---

## Related Documentation

- [RULES.md](../RULES.md) - Architecture and coding standards
- [Medallion Architecture](../RULES.md#2-medallion-architecture) - Bronze/Silver/Gold layer design
- [ADR-024](../02-architecture/decisions/ADR-024-publication-entity-validation.md) - Publication entity validation
- [ADR-028](../02-architecture/decisions/ADR-028-filter-configuration.md) - Filter configuration pattern
- [ADR-030](../02-architecture/decisions/ADR-030-api-offset-stability.md) - API offset stability

---

*Last updated: 2026-01-27*
