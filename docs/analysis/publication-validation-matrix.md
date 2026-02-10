# Publication Validation Matrix

*Version: 1.0.0 | Date: 2026-02-10*

Cross-pipeline analysis of validation rules for all publication entities in BioETL.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Validation Layers](#2-validation-layers)
3. [Main Validation Matrix: 5 Core Publication Pipelines](#3-main-validation-matrix)
4. [ChEMBL Auxiliary Pipelines](#4-chembl-auxiliary-pipelines)
5. [Composite Publication Pipeline](#5-composite-publication-pipeline)
6. [Divergence Analysis](#6-divergence-analysis)
7. [Unification Plans](#7-unification-plans)

---

## 1. Overview

BioETL has **5 core publication pipelines** that ingest scholarly publication metadata from different providers, plus **2 ChEMBL auxiliary pipelines** and **1 composite pipeline** that merges data across providers.

| # | Pipeline | Provider | Primary Key | Schema Class |
|---|----------|----------|-------------|--------------|
| 1 | `chembl/publication` | ChEMBL | `document_chembl_id` | `ChemblPublicationSchema` |
| 2 | `pubmed/publication` | PubMed/MEDLINE | `pmid` | `PubMedPublicationSchema` |
| 3 | `crossref/publication` | CrossRef | `doi` | `PublicationEnrichedSchema` |
| 4 | `openalex/publication` | OpenAlex | `openalex_id` | `OpenAlexPublicationSchema` |
| 5 | `semanticscholar/publication` | Semantic Scholar | `paper_id` | `SemanticScholarPublicationSchema` |
| 6 | `chembl/publication_term` | ChEMBL | composite key | `PublicationTermSchema` |
| 7 | `chembl/publication_similarity` | ChEMBL | `sim_id` | `PublicationSimilaritySchema` |
| 8 | `composite/publication` | Multi-source | from seed | `CompositePublicationGoldSchema` |

All 5 core publication schemas inherit from `PublicationBaseSchema` (which inherits from `ETLRecordSchema`). Validation is applied at 4 layers: Entity (Pydantic), Silver Schema (Pandera), DQ Rules (YAML config), Gold Schema (Pandera).

---

## 2. Validation Layers

| Layer | Technology | Location | When Applied |
|-------|-----------|----------|--------------|
| **Entity DTO** | Pydantic `BaseModel` | `domain/entities/{provider}.py` | API response parsing |
| **Entity Domain** | `@dataclass` + `__post_init__` | `domain/entities/{provider}.py` | Entity construction |
| **Silver Schema** | Pandera `DataFrameModel` | `domain/schemas/{provider}/publication.py` | Bronze -> Silver transform |
| **DQ Rules** | YAML config | `configs/dq/entities/{provider}/publication.yaml` | Post-Silver DQ engine |
| **Gold Schema** | Pandera `DataFrameModel` | `domain/contracts/gold/publications.py` | Silver -> Gold promotion |

### Base Schema Inheritance Chain

```
ETLRecordSchema (entity_id, content_hash, _run_id, _run_type, _source_batch_id, _ingestion_ts, _dq_warn, _dq_error, _index)
  └── PublicationBaseSchema (pmid, doi, pmc_id, title, abstract, authors, affiliation_list, author_orcids,
                              journal, publication_year, publication_date, publication_type, language,
                              page_first, page_last, citations_received, citations_made, is_oa,
                              _lookup_method, _original_id, _source)
        ├── ChemblPublicationSchema
        ├── PubMedPublicationSchema
        ├── PublicationEnrichedSchema (CrossRef)
        ├── OpenAlexPublicationSchema
        └── SemanticScholarPublicationSchema
```

---

## 3. Main Validation Matrix

### Legend

- **Type**: Pandera data type
- **Null**: `N` = nullable=False (required), `Y` = nullable=True (optional)
- **Pattern/Constraint**: regex, range, enum, or custom check
- **DQ**: additional DQ rule from YAML config (if different from schema)
- `--` = field not present in this pipeline
- `(base)` = inherited from `PublicationBaseSchema` without override

### 3.1 Primary Key Fields

| Field | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|-------|--------|--------|----------|----------|------------------|
| `document_chembl_id` | `str`, N, `^CHEMBL\d+$` | -- | -- | -- | -- |
| `pmid` | `str`, Y, `^[1-9]\d*$` (base) | `str`, **N**, `^[1-9]\d*$` | -- (base, Y) | `str`, Y (base) | `str`, Y (base) |
| `doi` | `str`, Y, DOI pattern (base) | `str`, Y, DOI pattern | `str`, **N**, DOI pattern | `str`, Y, DOI pattern (base) | `str`, Y, DOI pattern (base) |
| `openalex_id` | -- | -- | -- | `str`, N, `^W\d+$` | -- |
| `paper_id` | -- | -- | -- | -- | `str`, N, `^[a-f0-9]{40}$` |

> DOI pattern: `^10\.\d{4,}/\S+$`

### 3.2 Core Content Fields

| Field | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|-------|--------|--------|----------|----------|------------------|
| `title` | `str`, Y (base) | `str`, **N** | `str`, Y (base) | `str`, Y (base) | `str`, Y (base) |
| `abstract` | `str`, Y (base) | `str`, Y (base) | -- (base, Y) | `str`, Y (base) | `str`, Y (base) |
| `authors` | `str`, Y (base) | `str`, Y (base) | `str`, Y (base) | `str`, Y (base) | `str`, Y (base) |
| `affiliation_list` | `str`, Y (base) | `str`, Y (base) | -- (base, Y) | `str`, Y (base) | `str`, Y (base) |
| `author_orcids` | `str`, Y (base) | -- (base, Y) | `str`, Y (base) | `str`, Y (base) | `str`, Y (base) |

> `title` has custom check `title_not_empty` (len >= 1 when present) inherited from base.
> DQ rules add: max_length=2000, pattern `\S` (warn for whitespace-only) on all 5 pipelines.

### 3.3 Publication Metadata Fields

| Field | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|-------|--------|--------|----------|----------|------------------|
| `journal` | `str`, Y (base) | `str`, Y | `str`, Y (base) | `str`, Y (base) | `str`, Y (base) |
| `publication_year` | `Int64`, Y, [1500,2100] (base) | `Int64`, Y, [1500,2100] (base) | `Int64`, Y, [1500,2100] (base) | `Int64`, Y, [1500,2100] (base) | `Int64`, Y, [1500,2100] (base) |
| `publication_date` | -- (base, Y, `^\d{4}-\d{2}-\d{2}$`) | `str`, Y (base) | `str`, Y (base) | `str`, Y (base) | `str`, Y (base) |
| `publication_type` | `str`, Y, isin `PUBLICATION_TYPES` | `str`, Y (base, no isin) | `str`, Y (no isin, raw type) | `str`, Y (no isin, raw type) | `str`, Y (no isin, pipe-delimited) |
| `language` | -- (base, str_length 2..3) | `str`, Y (base, str_length 2..3) | `str`, Y (base) | `str`, Y (base) | -- (base, Y) |
| `publication_status` | -- | `str`, Y, check isin `ppublish/epublish/aheadofprint` | -- | -- | -- |
| `publication_types` | -- | `str`, Y (JSON array) | -- | -- | `str`, Y (JSON array) |
| `publication_type_list` | -- | `str`, Y (JSON array) | -- | -- | -- |

> `PUBLICATION_TYPES` (ChEMBL): `{PUBLICATION, PATENT, DATASET, BOOK}`

### 3.4 Journal-Specific Fields

| Field | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|-------|--------|--------|----------|----------|------------------|
| `journal_name_short` | -- | `str`, Y | `str`, Y | -- | -- |
| `journal_iso_abbrev` | -- | `str`, Y | -- | -- | -- |
| `issn` | -- | `str`, Y, `^\d{4}-\d{3}[\dX]$` | `str`, Y, ISSN pattern | `str`, Y, ISSN pattern | -- |
| `issn_list` | -- | -- | `str`, Y (JSON array) | -- | -- |
| `issn_print` | -- | -- | `str`, Y, ISSN pattern | -- | -- |
| `issn_electronic` | -- | -- | `str`, Y, ISSN pattern | -- | -- |
| `journal_issn_type` | -- | `str`, Y, check isin `Print/Electronic/Linking` | -- | -- | -- |
| `nlm_unique_id` | -- | `str`, Y | -- | -- | -- |
| `publisher` | -- | -- | `str`, Y | `str`, Y | -- |
| `volume` | `str`, Y | -- (in Gold only) | -- (in Gold only) | `str`, Y | `str`, Y |
| `issue` | `str`, Y | -- (in Gold only) | -- (in Gold only) | `str`, Y | -- |
| `country` | -- | `str`, Y | -- | -- | -- |

> ISSN pattern: `^\d{4}-\d{3}[\dX]$`

### 3.5 Pagination Fields

| Field | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|-------|--------|--------|----------|----------|------------------|
| `page_first` | `str`, Y | `str`, Y (base) | `str`, Y (base) | `str`, Y (base) | `str`, Y (base) |
| `page_last` | `str`, Y | `str`, Y (base) | `str`, Y (base) | `str`, Y (base) | `str`, Y (base) |
| `page_range` | -- | `str`, Y | -- | -- | `str`, Y |
| `medline_pgn` | -- | `str`, Y | -- | -- | -- |

### 3.6 Metrics Fields

| Field | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|-------|--------|--------|----------|----------|------------------|
| `citations_received` | `Int64`, Y, ge=0 (base) | `Int64`, Y, ge=0 (base) | `Int64`, Y, ge=0 (base) | `Int64`, Y, ge=0 (base) | `Int64`, Y, ge=0 (base) |
| `citations_made` | `Int64`, Y, ge=0 (base) | `Int64`, Y, ge=0 (base) | `Int64`, Y, ge=0 (base) | `Int64`, Y, ge=0 (base) | `Int64`, Y, ge=0 (base) |
| `fwci` | -- | -- | -- | `float`, Y, ge=0 | -- |
| `influential_citation_count` | -- | -- | -- | -- | `Int64`, Y, ge=0 |

> DQ rules on all 5 pipelines: `citations_received` has warn at max=10,000,000.

### 3.7 Open Access Fields

| Field | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|-------|--------|--------|----------|----------|------------------|
| `is_oa` | `bool`, Y (base) | `bool`, Y (base) | `bool`, Y (base) | `bool`, Y (base) | `bool`, Y (base) |
| `oa_status` | -- | -- | -- | `str`, Y, isin OA_STATUS | `str`, Y, isin OA_STATUS |
| `open_access_url` | -- | -- | -- | -- | `str`, Y |

> `OA_STATUS_VALUES`: `[gold, green, hybrid, bronze, closed]`

### 3.8 Classification & Subject Fields

| Field | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|-------|--------|--------|----------|----------|------------------|
| `subject_mesh` | -- | `str`, Y (JSON array) | -- | `str`, Y (JSON array) | -- |
| `subject_keywords` | -- | `str`, Y (JSON array) | `str`, Y (JSON array) | `str`, Y (JSON array) | -- |
| `subject_topics` | -- | -- | -- | `str`, Y (JSON array) | -- |
| `primary_topic` | -- | -- | -- | `str`, Y (JSON object) | -- |
| `subject_fields` | -- | -- | -- | -- | `str`, Y (JSON array) |
| `chemicals` | -- | `str`, Y (JSON array) | -- | -- | -- |
| `databanks` | -- | `str`, Y (JSON array) | -- | -- | -- |
| `gene_symbols` | -- | `str`, Y (JSON array) | -- | -- | -- |
| `citation_subset` | -- | `str`, Y | -- | -- | -- |

### 3.9 Author-Specific Fields

| Field | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|-------|--------|--------|----------|----------|------------------|
| `author_count` | -- | `Int64`, Y, ge=0 (check) | -- | -- | -- |
| `abstract_structured` | -- | `bool`, Y | -- | -- | -- |
| `authors_with_affiliations` | -- | `str`, Y (JSON) | -- | -- | -- |
| `affiliation_structured` | -- | `str`, Y (JSON) | -- | -- | -- |
| `author_details` | -- | -- | `str`, Y (JSON) | -- | -- |
| `author_openalex_ids` | -- | -- | -- | `str`, Y (JSON array) | -- |
| `author_s2_ids` | -- | -- | -- | -- | `str`, Y (JSON array) |
| `author_h_indices` | -- | -- | -- | -- | `str`, Y (JSON array) |

### 3.10 Date-Specific Fields

| Field | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|-------|--------|--------|----------|----------|------------------|
| `pub_month` | -- | `Int64`, Y, check [1,12] | -- | -- | -- |
| `pub_day` | -- | `Int64`, Y, check [1,31] | -- | -- | -- |
| `date_completed` | -- | `datetime`, Y | -- | -- | -- |
| `date_revised` | -- | `datetime`, Y | -- | -- | -- |
| `creation_date` | `str`, Y, `^\d{4}-\d{2}-\d{2}$` | -- | -- | -- | -- |
| `published_print` | -- | -- | `str`, Y | -- | -- |
| `published_online` | -- | -- | `str`, Y | -- | -- |
| `published` | -- | -- | `str`, Y | -- | -- |

### 3.11 Provider-Specific Identifier Fields

| Field | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|-------|--------|--------|----------|----------|------------------|
| `pmc_id` | `str`, Y, `^PMC\d+$` (base) | `str`, Y, check `^PMC\d+$` | `str`, Y (base) | `str`, Y (base) | `str`, Y (base) |
| `pii` | -- | `str`, Y | -- | -- | -- |
| `mid` | -- | `str`, Y | -- | -- | -- |
| `publisher_id` | -- | `str`, Y | -- | -- | -- |
| `src_id` | `Int64`, Y | -- | -- | -- | -- |
| `alternative_id` | -- | -- | `object`, Y | -- | -- |
| `mag_id` | -- | -- | -- | `str`, Y | -- |
| `dblp_id` | -- | -- | -- | -- | `str`, Y |
| `corpus_id` | -- | -- | -- | -- | `Int64`, Y, ge=0 |

### 3.12 Other Provider-Specific Fields

| Field | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|-------|--------|--------|----------|----------|------------------|
| `chembl_release` | `str`, Y | -- | -- | -- | -- |
| `license_url` | -- | -- | `str`, Y | -- | -- |
| `content_domain_domains` | -- | -- | `object`, Y | -- | -- |
| `content_domain_crossmark_restriction` | -- | -- | `bool`, Y | -- | -- |
| `references` | -- | -- | `str`, Y (JSON) | -- | -- |
| `grants` | -- | -- | -- | `str`, Y (JSON) | -- |
| `is_retracted` | -- | -- | -- | `bool`, **N** | -- |
| `institution_ids` | -- | -- | -- | `str`, Y (JSON) | -- |
| `institution_country_codes` | -- | -- | -- | `str`, Y (JSON) | -- |
| `ror_ids` | -- | -- | -- | `str`, Y (JSON) | -- |
| `tldr` | -- | -- | -- | -- | `str`, Y |
| `citation_contexts` | -- | -- | -- | -- | `str`, Y (JSON) |

### 3.13 System & Lookup Fields

| Field | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|-------|--------|--------|----------|----------|------------------|
| `_source` | `str`, N, eq=`chembl` | `str`, N, eq=`pubmed` | `str`, N, eq=`crossref` | `str`, N, eq=`openalex` | `str`, N, eq=`semanticscholar` |
| `_lookup_method` | `str`, N, isin LOOKUP_METHODS (base) | `str`, N, isin LOOKUP_METHODS (base) | `str`, N, isin LOOKUP_METHODS (base) | `str`, N, isin LOOKUP_METHODS (base) | `str`, N, isin LOOKUP_METHODS (base) |
| `_original_id` | `str`, Y (base) | `str`, Y (base) | `str`, Y (base) | `str`, Y (base) | `str`, Y (base) |
| `_dq_warn` | `BooleanDtype`, Y | `bool`, N (base) | `bool`, N (base) | `bool`, N (base) | `bool`, N (base) |
| `_dq_error` | `BooleanDtype`, Y | `bool`, N (base) | `bool`, N (base) | `bool`, N (base) | `bool`, N (base) |

> `LOOKUP_METHODS`: `[direct, doi, pmid, title_fallback, title_only, unknown]`

### 3.14 DQ Cross-Field Validations

| Rule | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|------|--------|--------|----------|----------|------------------|
| `publication_identifiable` | `document_chembl_id` + `title` all_present | `pmid` + `title` all_present | `doi` + `title` all_present | `openalex_id` + `title` all_present | `paper_id` + `title` all_present |
| `has_cross_reference` | `pmid` OR `doi` any_present (warn) | `pmid` OR `doi` OR `pmc_id` any_present | -- | -- | -- |
| `retracted_publication_warning` | -- | -- | -- | `is_retracted == true` (warn) | -- |

### 3.15 DQ Thresholds (from provider configs)

| Parameter | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|-----------|--------|--------|----------|----------|------------------|
| soft threshold | provider default | 0.05 | 0.10 | 0.08 | 0.15 |
| hard threshold | provider default | 0.15 | 0.30 | 0.25 | 0.40 |

---

## 4. ChEMBL Auxiliary Pipelines

### 4.1 Publication Term (`chembl/publication_term`)

Schema: `PublicationTermSchema` (inherits `ETLRecordSchema`, NOT `PublicationBaseSchema`)

| Field | Type | Nullable | Constraint |
|-------|------|----------|------------|
| `document_chembl_id` | `str` | N | `^CHEMBL\d+$` |
| `term` | `str` | N | str_length min=1 |
| `term_type` | `str` | N | isin `[MESH_HEADING, MESH_QUALIFIER, KEYWORD, CONCEPT]` |
| `mesh_id` | `str` | Y | -- |
| `qualifier` | `str` | Y | -- |

DQ cross-field: `term_completeness` = `document_chembl_id` + `term` + `term_type` all_present.

> Note: DQ config allows `term_type` values `[MESH_HEADING, KEYWORD, AUTHOR, INSTITUTION]` which differs from the Pandera schema `[MESH_HEADING, MESH_QUALIFIER, KEYWORD, CONCEPT]`. This is a known divergence.

### 4.2 Publication Similarity (`chembl/publication_similarity`)

Schema: `PublicationSimilaritySchema` (inherits `ETLRecordSchema`, NOT `PublicationBaseSchema`)

| Field | Type | Nullable | Constraint |
|-------|------|----------|------------|
| `sim_id` | `int` | N | -- |
| `doc_1` | `int` | N | -- |
| `doc_2` | `int` | N | -- |
| `pubmed_id1` | `str` | Y | `^\d+$` |
| `pubmed_id2` | `str` | Y | `^\d+$` |
| `tid_tani` | `float` | Y | [0, 1] |
| `mol_tani` | `float` | Y | [0, 1] |
| `avg_tani` | `float` | Y | [0, 1] |
| `max_tani` | `float` | Y | [0, 1] |

DQ rules: `sim_id` ge=1, `doc_1` ge=1, `doc_2` ge=1, Tanimoto coefficients [0,1].

---

## 5. Composite Publication Pipeline

Schema: `CompositePublicationGoldSchema` (`strict=False`)

The composite pipeline does not have its own field-level validation for business columns. It validates only system/lineage fields:

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `entity_id` | `str` | N | From seed |
| `content_hash` | `str` | N | From seed |
| `_dq_warn` | `bool` | N | From seed |
| `_dq_error` | `bool` | N | From seed |
| `_composite_run_id` | `str` | N | MergeService |
| `_source_providers` | `str` | N | JSON list |
| `_enrichment_status` | `str` | N | JSON dict |
| `_lineage_created_at` | `str` | N | ISO timestamp |

Business columns use qualified names `{provider}.{entity}.{field}` and are validated only by source pipeline schemas before merge.

---

## 6. Divergence Analysis

### 6.1 Fields with Same Name but Different Validation

The following fields exist in multiple pipelines under the same name but have **different validation rules**.

#### 6.1.1 `pmid`

| Aspect | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|--------|--------|--------|----------|----------|------------------|
| **Schema type** | `str` | `str` | `str` (base) | `str` (base) | `str` (base) |
| **Nullable (schema)** | Y | **N** | Y | Y | Y |
| **Pattern (schema)** | `^[1-9]\d*$` (base) | `^[1-9]\d*$` | `^[1-9]\d*$` (base) | `^[1-9]\d*$` (base) | `^[1-9]\d*$` (base) |
| **DQ type** | range | range | -- | range | range |
| **DQ min/max** | 1 / 10B | 1 / 10B | -- | 1 / 10B | 1 / 10B |
| **DQ nullable** | true | **false** | -- | true | true |

**Divergence**: PubMed requires `pmid` as non-nullable (it's the primary key). All others treat it as optional cross-reference. DQ rules validate it as a numeric range, while the Pandera schema validates it as a string pattern -- both enforce the same semantic (positive integer) but through different mechanisms.

#### 6.1.2 `doi`

| Aspect | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|--------|--------|--------|----------|----------|------------------|
| **Nullable (schema)** | Y | Y | **N** | Y | Y |
| **Pattern (schema)** | `^10\.\d{4,}/\S+$` (base) | `^10\.\d{4,}/\S+$` | `^10\.\d{4,}/\S+$` | `^10\.\d{4,}/\S+$` (base) | `^10\.\d{4,}/\S+$` (base) |
| **DQ nullable** | true | true | **false** | true | true |
| **DQ pattern** | `^10\.\d{4,}/\S+$` | `^10\.\d{4,}/\S+$` | `^10\.\d{4,}/\S+$` | `^10\.\d{4,}/\S+$` | `^10\.\d{4,}/\S+$` |

**Divergence**: CrossRef requires `doi` as non-nullable (it's the primary key). Pattern is consistent. Entity-level validation: `CrossRefPublicationEntity.__post_init__` raises `ValueError` if `doi` is empty.

#### 6.1.3 `title`

| Aspect | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|--------|--------|--------|----------|----------|------------------|
| **Nullable (schema)** | Y (base) | **N** | Y (base) | Y (base) | Y (base) |
| **Check** | `title_not_empty` (base) | `title_not_empty` (base) | `title_not_empty` (base) | `title_not_empty` (base) | `title_not_empty` (base) |
| **DQ max_length** | 2000 | 2000 | 2000 | 2000 | 2000 |
| **DQ non-whitespace** | warn | warn | warn | warn | warn |
| **Gold nullable** | -- (no ChEMBL gold) | N | Y | Y | Y |

**Divergence**: PubMed requires `title` as non-nullable in both Silver schema and Gold schema. Other pipelines allow null titles.

#### 6.1.4 `publication_type`

| Aspect | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|--------|--------|--------|----------|----------|------------------|
| **Schema constraint** | isin `{PUBLICATION, PATENT, DATASET, BOOK}` | none (base) | none | none | none |
| **Value semantics** | Unified BioETL types | Inherited from base | Raw CrossRef type (e.g., `journal-article`) | Raw OpenAlex type (e.g., `article`) | Pipe-delimited string |
| **DQ field name** | `doc_type` | `pub_type` | `type` | `type` | -- |
| **DQ allowed values** | `PUBLICATION, BOOK, DATASET, PATENT` | `Journal Article, Review, Letter, ...` | `journal-article, book-chapter, ...` | `article, book-chapter, book, ...` | -- |

**Divergence**: This is the most divergent field. ChEMBL uses unified BioETL types, while CrossRef and OpenAlex store raw provider types. PubMed DQ uses NLM publication types. SemanticScholar uses pipe-delimited strings. The transformers map raw types to unified types for the entity, but the Silver schema stores different representations.

#### 6.1.5 `_source`

| Aspect | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|--------|--------|--------|----------|----------|------------------|
| **Nullable** | N | N | N | N | N |
| **Fixed value** | `chembl` | `pubmed` | `crossref` | `openalex` | `semanticscholar` |
| **Base schema** | Y (nullable) | -- | -- | -- | -- |

**Divergence**: All pipelines override `_source` to non-nullable with a fixed value. The base schema defines it as nullable -- this is intentional (base doesn't know the provider). ChEMBL uses `BooleanDtype` for `_dq_warn`/`_dq_error` while others use `bool`, creating a type divergence.

#### 6.1.6 `_dq_warn` / `_dq_error`

| Aspect | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|--------|--------|--------|----------|----------|------------------|
| **Schema type** | `pd.BooleanDtype` | `bool` (base) | `bool` (base) | `bool` (base) | `bool` (base) |
| **Nullable** | Y | N (base) | N (base) | N (base) | N (base) |
| **Default** | False | False | False | False | False |

**Divergence**: ChEMBL uses `pd.BooleanDtype` (nullable boolean) while all others inherit `bool` (non-nullable) from `ETLRecordSchema`. ChEMBL also marks these as nullable=True.

#### 6.1.7 `publication_year`

| Aspect | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|--------|--------|--------|----------|----------|------------------|
| **Silver type** | `pd.Int64Dtype` (base) | `pd.Int64Dtype` (base) | `pd.Int64Dtype` (base) | `pd.Int64Dtype` (base) | `pd.Int64Dtype` (base) |
| **Silver range** | [1500, 2100] (base) | [1500, 2100] (base) | [1500, 2100] (base) | [1500, 2100] (base) | [1500, 2100] (base) |
| **Silver nullable** | Y | Y | Y | Y | Y |
| **DQ range** | [1500, 2100] | [1500, 2100] | [1500, 2100] | [1500, 2100] | [1500, 2100] |
| **Gold type** | -- | `float`, [1500,2100], coerce | `float`, [1500,2100], coerce | `float`, [1500,2100], coerce | `float`, [1500,2100], coerce |
| **Gold nullable** | -- | Y | Y | Y | Y |
| **Entity type** | `int \| None` (base) | `int \| None` (base) | `int \| None` (base) | `int \| None` (base) | `int \| None` (base) |
| **Domain validation** | `validate_publication_year()` | `validate_publication_year()` | `validate_publication_year()` | `validate_publication_year()` | `validate_publication_year()` |

**Divergence**: Minimal. The Silver schema, DQ rules, and domain validation are all consistent (range [1500, 2100]). The only difference is the Gold layer uses `float` with coerce=True (for Pandas nullable int handling). This is a documented design decision (RULES.md 2.6, EXC-007).

#### 6.1.8 `citations_received`

| Aspect | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|--------|--------|--------|----------|----------|------------------|
| **Silver type** | `Int64` (base) | `Int64` (base) | `Int64` (base) | `Int64` (base) | `Int64` (base) |
| **Silver constraint** | ge=0 | ge=0 | ge=0 | ge=0 | ge=0 |
| **DQ error** | ge=0 | ge=0 | ge=0 | ge=0 | ge=0 |
| **DQ warn** | [0, 10M] | [0, 10M] | [0, 10M] | [0, 10M] | [0, 10M] |
| **Gold type** | -- | `float`, ge=0, coerce | `float`, ge=0, coerce | `float`, ge=0, coerce | `float`, ge=0, coerce |

**Divergence**: Fully consistent across all pipelines. Both schema and DQ layers are aligned.

#### 6.1.9 `oa_status`

| Aspect | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|--------|--------|--------|----------|----------|------------------|
| **Present** | No | No | No | Yes | Yes |
| **Allowed values** | -- | -- | -- | `OA_STATUS_VALUES` | `OA_STATUS_VALUES` |
| **Nullable** | -- | -- | -- | Y | Y |

**Divergence**: Only present in OpenAlex and Semantic Scholar. Both use the same `OA_STATUS_VALUES` enum. CrossRef has `license_url` instead.

#### 6.1.10 `subject_keywords`

| Aspect | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|--------|--------|--------|----------|----------|------------------|
| **Present** | No | Yes | Yes | Yes | No |
| **Type** | -- | `str` (JSON array) | `str` (JSON array) | `str` (JSON array) | -- |
| **Description** | -- | Author keywords | Subject areas | Keywords | -- |
| **Nullable** | -- | Y | Y | Y | -- |

**Divergence**: Same field name, same type (JSON array of strings), same nullable. Semantically similar: all represent keyword/subject classification. No structural divergence.

#### 6.1.11 `subject_mesh`

| Aspect | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|--------|--------|--------|----------|----------|------------------|
| **Present** | No | Yes | No | Yes | No |
| **Type** | -- | `str` (JSON array) | -- | `str` (JSON array) | -- |
| **Nullable** | -- | Y | -- | Y | -- |

**Divergence**: Consistent between PubMed and OpenAlex. Both store MeSH terms as JSON array of descriptor names.

#### 6.1.12 `page_range`

| Aspect | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|--------|--------|--------|----------|----------|------------------|
| **Present** | No | Yes | No | No | Yes |
| **Type** | -- | `str` | -- | -- | `str` |
| **Nullable** | -- | Y | -- | -- | Y |
| **Description** | -- | Page range (unified) | -- | -- | Legacy format `123-456` |

**Divergence**: Minimal. Both are nullable strings. PubMed also has `medline_pgn` (MEDLINE-specific format).

---

## 7. Unification Plans

### 7.1 `publication_type` -- HIGH PRIORITY

**Problem**: Most divergent field. 4 different value sets across pipelines.

| Pipeline | Current Values | Mapping to Unified |
|----------|---------------|-------------------|
| ChEMBL | `PUBLICATION, PATENT, DATASET, BOOK` | Already unified |
| PubMed | NLM types: `Journal Article, Review, ...` | Needs mapping |
| CrossRef | Raw types: `journal-article, book-chapter, ...` | Has `CROSSREF_TYPE_MAP` in entity |
| OpenAlex | Raw types: `article, book, preprint, ...` | Has `OPENALEX_TYPE_MAP` in entity |
| S2 | Pipe-delimited: `JournalArticle\|Review` | Needs mapping |

**Unification Plan**:

1. **Define canonical enum** in `domain/types.py` or `domain/value_objects/`:
   ```
   PublicationType = Literal["PUBLICATION", "PREPRINT", "BOOK", "DATASET", "PATENT", "OTHER"]
   ```
2. **Apply mapping in transformer** (not schema): Each transformer already has type maps (`CROSSREF_TYPE_MAP`, `OPENALEX_TYPE_MAP`). Extend to PubMed and SemanticScholar.
3. **Add Silver schema validation**: Add `isin` constraint to base schema field `publication_type` with the canonical enum values.
4. **Store raw type separately**: Keep `publication_type_raw` (nullable, str) for the original provider value, and `publication_type` for the unified value.
5. **Update DQ rules**: Align all DQ configs to validate unified `publication_type` enum instead of provider-specific `doc_type` / `pub_type` / `type` fields.

**Impact**: All 5 transformers, DQ configs, Gold schemas. Estimated: ~20 files.

---

### 7.2 `title` Nullability -- MEDIUM PRIORITY

**Problem**: PubMed requires `title` as non-nullable; other pipelines allow null.

**Analysis**: PubMed receives title directly from MEDLINE records where it's required. Other providers may have records without titles (e.g., datasets, errata). Forcing non-nullable on all pipelines would cause data loss.

**Unification Plan**:

1. **Keep PubMed non-nullable**: PubMed's source data guarantees title presence.
2. **Add DQ severity escalation**: For pipelines where title is nullable, add a DQ rule that escalates `title IS NULL` to error severity (not just warn) for records with `publication_type = PUBLICATION`.
3. **No schema change needed**: The current approach (nullable in base, override in PubMed) is architecturally sound.

**Impact**: DQ config files only. Estimated: ~4 files.

---

### 7.3 `pmid` / `doi` Nullability -- LOW PRIORITY (by design)

**Problem**: Primary keys are non-nullable in their owning pipeline, nullable elsewhere.

**Analysis**: This is intentional and correct. `pmid` is the primary key for PubMed, `doi` for CrossRef. When used as cross-references in other pipelines, they are nullable because not all publications have them.

**Unification Plan**: **No change needed.** Document current behavior as an architectural invariant:
- Primary key field: non-nullable in owning pipeline
- Cross-reference field: nullable in all other pipelines

---

### 7.4 `_dq_warn` / `_dq_error` Type Divergence -- MEDIUM PRIORITY

**Problem**: ChEMBL uses `pd.BooleanDtype` (nullable) while all others use `bool` (non-nullable) from base.

**Unification Plan**:

1. **Align ChEMBL to base**: Change `ChemblPublicationSchema._dq_warn` and `_dq_error` to use `bool`, non-nullable, matching the `ETLRecordSchema` base.
2. **Remove override**: Delete the `_dq_warn` and `_dq_error` field definitions from `ChemblPublicationSchema`.
3. **Test**: Verify that ChEMBL pipeline produces non-nullable boolean DQ fields.

**Impact**: `domain/schemas/chembl/publication.py`, ChEMBL transformer. Estimated: ~2 files.

---

### 7.5 `publication_term` `term_type` Enum Divergence -- MEDIUM PRIORITY

**Problem**: Pandera schema allows `[MESH_HEADING, MESH_QUALIFIER, KEYWORD, CONCEPT]` but DQ config allows `[MESH_HEADING, KEYWORD, AUTHOR, INSTITUTION]`.

**Unification Plan**:

1. **Audit actual data**: Determine which `term_type` values appear in ChEMBL API responses.
2. **Align enum**: Create a single source of truth for allowed values in `domain/schemas/constants.py`.
3. **Update both**: Pandera schema `isin` and DQ config `allowed` must reference the same set.

**Impact**: `domain/schemas/chembl/publication_term.py`, `configs/dq/entities/chembl/publication_term.yaml`. Estimated: ~2 files.

---

### 7.6 DQ Cross-Field Validation Alignment -- LOW PRIORITY

**Problem**: `has_cross_reference` rule exists only in ChEMBL and PubMed; `retracted_publication_warning` only in OpenAlex.

**Unification Plan**:

1. **Add `has_cross_reference`** to CrossRef (doi + pmid), OpenAlex (doi + pmid), and SemanticScholar (doi + pmid) DQ configs as warn-level rules.
2. **Add `retracted_publication_warning`** to SemanticScholar if S2 API provides retraction data (currently not available).
3. **Consider adding `is_retracted`** to base schema (nullable=True, default=None) so all pipelines can optionally provide it.

**Impact**: DQ configs. Estimated: ~3-4 files.

---

### 7.7 DQ Threshold Normalization -- LOW PRIORITY

**Problem**: DQ soft/hard thresholds vary significantly across providers (PubMed: 5%/15% vs SemanticScholar: 15%/40%).

**Analysis**: These reflect genuine differences in data quality across providers. SemanticScholar has more missing/inconsistent data, warranting looser thresholds. This is **not a bug** but a conscious design choice.

**Unification Plan**: **No change needed.** Document rationale for each provider's thresholds in the DQ config files.

---

### Summary of Unification Priorities

| # | Item | Priority | Impact | Files |
|---|------|----------|--------|-------|
| 7.1 | `publication_type` unified enum | HIGH | All pipelines | ~20 |
| 7.2 | `title` nullability DQ escalation | MEDIUM | DQ configs | ~4 |
| 7.4 | `_dq_warn`/`_dq_error` ChEMBL alignment | MEDIUM | ChEMBL schema | ~2 |
| 7.5 | `term_type` enum alignment | MEDIUM | ChEMBL term | ~2 |
| 7.6 | Cross-field DQ rules expansion | LOW | DQ configs | ~4 |
| 7.3 | PK nullability (no change) | LOW | Documentation | 0 |
| 7.7 | DQ thresholds (no change) | LOW | Documentation | 0 |

---

*Sources: `domain/schemas/common/publication_base.py`, `domain/schemas/{provider}/publication.py`, `configs/dq/entities/{provider}/publication.yaml`, `domain/contracts/gold/publications.py`, `domain/entities/{provider}.py`, `domain/validation.py`*
