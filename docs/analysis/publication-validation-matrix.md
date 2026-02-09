# Publication Validation Matrix

*Version: 1.0.0 | Date: 2026-02-09*

Cross-pipeline analysis of validation rules for all publication entities in BioETL.
Covers 5 single-provider publication pipelines and 2 derived ChEMBL entities.

---

## Table of Contents

1. [Pipelines Overview](#1-pipelines-overview)
2. [Validation Layers](#2-validation-layers)
3. [Common (Base) Fields Validation Matrix](#3-common-base-fields-validation-matrix)
4. [Provider-Specific Fields](#4-provider-specific-fields)
5. [ChEMBL Derived Entities](#5-chembl-derived-entities)
6. [Fields with Divergent Validation](#6-fields-with-divergent-validation)
7. [Unification Plans](#7-unification-plans)

---

## 1. Pipelines Overview

| # | Pipeline | Provider | Primary Key | Schema Class | DQ Config |
|---|----------|----------|-------------|--------------|-----------|
| 1 | ChEMBL Publication | ChEMBL 34 API | `document_chembl_id` | `ChemblPublicationSchema` | `chembl/publication.yaml` |
| 2 | PubMed Publication | NCBI E-Utilities | `pmid` | `PubMedPublicationSchema` | `pubmed/publication.yaml` |
| 3 | SemanticScholar Publication | S2 Academic Graph API | `paper_id` | `SemanticScholarPublicationSchema` | `semanticscholar/publication.yaml` |
| 4 | CrossRef Publication | CrossRef REST API | `doi` | `PublicationEnrichedSchema` | `crossref/publication.yaml` |
| 5 | OpenAlex Publication | OpenAlex Works API | `openalex_id` | `OpenAlexPublicationSchema` | `openalex/publication.yaml` |
| 6 | ChEMBL Publication Term | Derived from ChEMBL | `document_chembl_id + term_type + term` | `PublicationTermSchema` | `chembl/publication_term.yaml` |
| 7 | ChEMBL Publication Similarity | ChEMBL API | `sim_id` | `PublicationSimilaritySchema` | `chembl/publication_similarity.yaml` |

All 5 main publication schemas inherit from `PublicationBaseSchema` (defined in
`domain/schemas/common/publication_base.py`), which itself inherits from `ETLRecordSchema`.

---

## 2. Validation Layers

Each pipeline has up to 4 layers of validation:

| Layer | Where | Mechanism | Purpose |
|-------|-------|-----------|---------|
| **Transformer** | `application/pipelines/{provider}/transformer.py` | Value Objects (`DOI`, `PublicationYear`, `PubMedId`), extractors, normalizers | Input normalization, type coercion, format cleaning |
| **Silver Schema** | `domain/schemas/{provider}/publication.py` | Pandera `DataFrameModel` with `pa.Field()` constraints | Structural validation: types, nullability, regex, range, enum |
| **DQ Rules** | `configs/dq/entities/{provider}/publication.yaml` | YAML-driven field/cross-field/conditional rules | Business-level DQ: thresholds, cross-field consistency, identity checks |
| **Gold Schema** | `domain/contracts/gold/publications.py` | Pandera `DataFrameModel` (strict mode) | Final contract: exact column set, types, ranges before Delta Lake write |

---

## 3. Common (Base) Fields Validation Matrix

Fields inherited from `PublicationBaseSchema`. Cells describe the **effective** validation
(base + provider override + DQ + transformer logic combined).

### 3.1 Cross-Reference Identifiers

| Field | ChEMBL | PubMed | SemanticScholar | CrossRef | OpenAlex |
|-------|--------|--------|-----------------|----------|----------|
| **pmid** | `str`, nullable, regex `^[1-9]\d*$` (base). Transformer: `PMID` converter from `pubmed_id`. DQ: range 1..100M | `str`, **non-nullable** (PK). Custom check `pmid_positive` regex `^[1-9]\d*$`. DQ: range 1..100M, required | `str`, nullable, regex `^[1-9]\d*$` (base). Transformer: `PubMedId.from_raw()` VO | Excluded from output (popped in `entity_to_silver_record`) | `str`, nullable, regex `^[1-9]\d*$` (base). Extracted from `ids.pmid` |
| **doi** | `str`, nullable, regex `DOI_REGEX_PATTERN` (`^10\.\d{4,}/.+$`). Transformer: `DOI.from_raw()` VO. DQ: pattern `^10\.\d{4,}/.+$` | `str`, nullable, regex `DOI_REGEX_PATTERN`. Transformer: `DOI.from_raw()` VO. DQ: pattern `^10\.\d{4,}/.+$` | `str`, nullable, regex `DOI_REGEX_PATTERN` (base). Transformer: `DOI.from_raw()` VO. DQ: pattern `^10\.\d{4,}/.+$` | `str`, **non-nullable**, regex `DOI_REGEX_PATTERN` (PK). Pre-validation: ValueError if missing/invalid. Transformer: `DOI` VO. DQ: pattern required | `str`, nullable, regex `DOI_REGEX_PATTERN`. Transformer: `DOI` VO. DQ: pattern `^10\.\d{4,}/.+$` |
| **pmc_id** | Excluded from output | `str`, nullable, regex `^PMC\d+$` (custom check). `normalize_pmc_id()` in transformer. DQ: pattern `^PMC\d+$` | Excluded from output | Excluded from output | Excluded from output (popped) |

### 3.2 Core Content

| Field | ChEMBL | PubMed | SemanticScholar | CrossRef | OpenAlex |
|-------|--------|--------|-----------------|----------|----------|
| **title** | `str`, nullable. DQ: max_length 2000 | `str`, **non-nullable**. Custom check `title_not_empty` (len >= 1). DQ: pattern `.{1,2000}` | `str`, nullable (base). DQ: pattern `.{1,2000}` | `str`, nullable (base). Transformer: `extract_first_string()`. DQ: pattern `.{1,2000}` | `str`, nullable (base). DQ: pattern `.{1,2000}` |
| **abstract** | `str`, nullable. Transformer: `strip_html_tags()` | `str`, nullable. Transformer: `strip_html_tags()`, `AbstractExtractor`. Field `abstract_structured` bool | `str`, nullable. Transformer: `normalize_string()`. Fallback to `tldr` | Excluded from output (popped) | `str`, nullable. Transformer: `reconstruct_abstract()` from inverted index + `strip_html_tags()` |
| **authors** | `str`, nullable (JSON array). Transformer: `parse_authors_to_list()` + PII hash | `str`, nullable (JSON array). Transformer: `AuthorExtractor` + PII hash | Excluded from output (popped). Author IDs in separate fields | `str`, nullable (JSON array). Transformer: `extract_authors()` + PII hash | `str`, nullable (JSON array). Transformer: `extract_authors()` + PII hash |
| **affiliation_list** | Excluded from output | `str`, nullable (JSON array). Extracted from raw author affiliations, deduplicated | `str`, nullable (JSON array). `extract_affiliations()` | Excluded from output (popped) | `str`, nullable (JSON array). `extract_affiliations()` from authorships |

### 3.3 Publication Metadata

| Field | ChEMBL | PubMed | SemanticScholar | CrossRef | OpenAlex |
|-------|--------|--------|-----------------|----------|----------|
| **journal** | `str`, nullable | `str`, nullable. Full journal title | `str`, nullable. From `journal.name` or `venue` | `str`, nullable. From `container-title` | `str`, nullable. From `primary_location.source.display_name` |
| **publication_year** | `Int64`, nullable, ge=1500, le=2100. Transformer: `PublicationYear.from_raw()` VO | `Int64`, nullable, ge=1500, le=2100 (base). Transformer: `PublicationYear.from_raw()` VO | `Int64`, nullable, ge=1500, le=2100 (base). Transformer: `validate_year()` | `Int64`, nullable, ge=1500, le=2100 (base). Transformer: `extract_year()` | `Int64`, nullable, ge=1500, le=2100 (base). Transformer: `PublicationYear` VO |
| **publication_date** | Excluded from output | `str`, nullable, regex `^\d{4}-\d{2}-\d{2}$`. Transformer: `_compute_publication_date()` priority: epub > pub_date > year | `str`, nullable, regex `^\d{4}-\d{2}-\d{2}$` (base). Transformer: `_normalize_partial_date()` | `str`, nullable, regex `^\d{4}-\d{2}-\d{2}$` (base). Transformer: `_compute_publication_date()` priority: print > online | `str`, nullable, regex `^\d{4}-\d{2}-\d{2}$` (base). Transformer: `_normalize_partial_date()` |
| **publication_type** | `str`, nullable, isin `PUBLICATION_TYPES` (PUBLICATION, PATENT, DATASET, BOOK). Mapped from `doc_type` | `str`, nullable (base). Hardcoded `"PUBLICATION"` in transformer | `str`, nullable. Pipe-delimited from `publicationTypes` list. Default `"PUBLICATION"` | `str`, nullable. Raw CrossRef type string (journal-article, book, etc.) | `str`, nullable. Raw OpenAlex type string (article, book, dataset, etc.) |
| **language** | Excluded from output | `str`, nullable, length 2..3 (base). From XML `<Language>` | Not available from S2 API | `str`, nullable, length 2..3 (base). From raw `language` field | `str`, nullable, length 2..3 (base). From raw `language` field |

### 3.4 Pagination

| Field | ChEMBL | PubMed | SemanticScholar | CrossRef | OpenAlex |
|-------|--------|--------|-----------------|----------|----------|
| **page_first** | `str`, nullable | `str`, nullable. `parse_page_range()` | `str`, nullable. From extractor | `str`, nullable. `extract_page_info()` | `str`, nullable. From `biblio.first_page` |
| **page_last** | `str`, nullable | `str`, nullable. `parse_page_range()` | `str`, nullable. From extractor | `str`, nullable. `extract_page_info()` | `str`, nullable. From `biblio.last_page` |

### 3.5 Metrics

| Field | ChEMBL | PubMed | SemanticScholar | CrossRef | OpenAlex |
|-------|--------|--------|-----------------|----------|----------|
| **citations_received** | `Int64`, nullable, ge=0. From `citation_count` if present | Excluded from output (always None) | `Int64`, nullable, ge=0. From `citationCount`. DQ: range min=0 | `Int64`, nullable, ge=0. From `is-referenced-by-count`. DQ: range min=0 | `Int64`, nullable, ge=0. From `cited_by_count`. DQ: range min=0 |
| **citations_made** | Always None | `Int64`, nullable, ge=0. From reference list count | `Int64`, nullable, ge=0. From `referenceCount`. DQ: range min=0 | `Int64`, nullable, ge=0. From `references-count` | `Int64`, nullable, ge=0. From `referenced_works_count`. DQ: range min=0 |
| **is_oa** | Excluded (always None) | Excluded (always None) | `bool`, nullable. From `isOpenAccess` | Always None (not available) | `bool`, nullable. From `open_access.is_oa` |

### 3.6 Lookup & System Fields

| Field | ChEMBL | PubMed | SemanticScholar | CrossRef | OpenAlex |
|-------|--------|--------|-----------------|----------|----------|
| **_lookup_method** | `str`, non-nullable, isin `LOOKUP_METHODS`. Hardcoded `"direct"` | `str`, non-nullable, isin `LOOKUP_METHODS`. Default `"pmid"` | `str`, non-nullable, isin `LOOKUP_METHODS`. Default `"unknown"` | `str`, non-nullable, isin `LOOKUP_METHODS`. Default `"doi"` | `str`, non-nullable, isin `LOOKUP_METHODS`. Default `"unknown"` |
| **_original_id** | `str`, nullable. Set to `document_chembl_id` | `str`, nullable. From record metadata | `str`, nullable. From record metadata | `str`, nullable. From record metadata | `str`, nullable. From record metadata |
| **_source** | `str`, **non-nullable**, eq `"chembl"` | `str`, **non-nullable**, eq `"pubmed"` | `str`, **non-nullable**, eq `"semanticscholar"` | `str`, **non-nullable**, eq `"crossref"` | `str`, **non-nullable**, eq `"openalex"` |

---

## 4. Provider-Specific Fields

### 4.1 ChEMBL-Only Fields

| Field | Type | Validation |
|-------|------|------------|
| `document_chembl_id` | `str` | Non-nullable, regex `^CHEMBL\d+$`. DQ: pattern enforced |
| `src_id` | `Int64` | Nullable |
| `chembl_release` | `str` | Nullable. From nested API object |
| `creation_date` | `str` | Nullable, regex `^\d{4}-\d{2}-\d{2}$` |
| `volume` | `str` | Nullable |
| `issue` | `str` | Nullable |

### 4.2 PubMed-Only Fields

| Field | Type | Validation |
|-------|------|------------|
| `pii` | `str` | Nullable. Publisher Item Identifier |
| `mid` | `str` | Nullable. Manuscript ID |
| `publisher_id` | `str` | Nullable |
| `abstract_structured` | `bool` | Nullable. Whether abstract has NLM sections |
| `journal_name_short` | `str` | Nullable. Journal abbreviation |
| `journal_iso_abbrev` | `str` | Nullable |
| `issn` | `str` | Nullable, regex `^\d{4}-\d{3}[\dX]$` |
| `journal_issn_type` | `str` | Nullable, custom check isin `["Print", "Electronic", "Linking"]` |
| `nlm_unique_id` | `str` | Nullable |
| `country` | `str` | Nullable |
| `medline_pgn` | `str` | Nullable |
| `page_range` | `str` | Nullable |
| `pub_month` | `Int64` | Nullable, custom check range 1..12 |
| `pub_day` | `Int64` | Nullable, custom check range 1..31 |
| `publication_status` | `str` | Nullable, custom check isin `["ppublish", "epublish", "aheadofprint"]` |
| `publication_type_list` | `str` | Nullable (JSON array) |
| `date_completed` | `datetime` | Nullable |
| `date_revised` | `datetime` | Nullable |
| `citation_subset` | `str` | Nullable |
| `affiliation_structured` | `str` | Nullable (JSON array with ROR/GRID) |
| `author_count` | `Int64` | Nullable, custom check ge=0 |
| `mesh_heading_count` | `Int64` | Nullable, custom check ge=0 |
| `keyword_count` | `Int64` | Nullable, custom check ge=0 |
| `grant_count` | `Int64` | Nullable, custom check ge=0 |
| `chemical_count` | `Int64` | Nullable, custom check ge=0 |
| `subject_mesh` | `str` | Nullable (JSON array) |
| `chemicals` | `str` | Nullable (JSON array) |
| `subject_keywords` | `str` | Nullable (JSON array) |
| `databanks` | `str` | Nullable (JSON array) |
| `gene_symbols` | `str` | Nullable (JSON array) |
| `publication_types` | `str` | Nullable (JSON array) |
| `authors_with_affiliations` | `str` | Nullable (JSON array) |

### 4.3 SemanticScholar-Only Fields

| Field | Type | Validation |
|-------|------|------------|
| `paper_id` | `str` | Non-nullable, regex `^[a-f0-9]{40}$`. DQ: pattern enforced |
| `corpus_id` | `Int64` | Nullable, ge=0 |
| `dblp_id` | `str` | Nullable |
| `tldr` | `str` | Nullable. AI-generated summary |
| `volume` | `str` | Nullable |
| `page_range` | `str` | Nullable |
| `influential_citation_count` | `Int64` | Nullable, ge=0. DQ: range min=0 |
| `open_access_url` | `str` | Nullable |
| `oa_status` | `str` | Nullable, isin `OA_STATUS_VALUES` |
| `subject_fields` | `str` | Nullable (JSON array) |
| `publication_types` | `str` | Nullable (JSON array) |
| `author_s2_ids` | `str` | Nullable (JSON array) |
| `author_orcids` | `str` | Nullable (JSON array). Custom check: ORCID format validation |
| `author_h_indices` | `str` | Nullable (JSON array) |
| `citation_contexts` | `str` | Nullable (JSON array) |

### 4.4 CrossRef-Only Fields

| Field | Type | Validation |
|-------|------|------------|
| `issn` | `str` | Nullable, regex `^\d{4}-\d{3}[\dX]$` |
| `issn_list` | `str` | Nullable (JSON array) |
| `publisher` | `str` | Nullable |
| `published_print` | `str` | Nullable (ISO date) |
| `published_online` | `str` | Nullable (ISO date) |
| `license_url` | `str` | Nullable |
| `subject_keywords` | `str` | Nullable (JSON array) |
| `content_domain_domains` | `object` | Nullable |
| `content_domain_crossmark_restriction` | `bool` | Nullable, coerce=True |
| `alternative_id` | `object` | Nullable |
| `published` | `str` | Nullable (canonical date) |
| `journal_name_short` | `str` | Nullable |
| `issn_print` | `str` | Nullable, regex `^\d{4}-\d{3}[\dX]$` |
| `issn_electronic` | `str` | Nullable, regex `^\d{4}-\d{3}[\dX]$` |
| `author_orcid_list` | `str` | Nullable (JSON array). Custom check: ORCID format validation |
| `author_details` | `str` | Nullable (JSON array) |
| `references` | `str` | Nullable (JSON array) |

### 4.5 OpenAlex-Only Fields

| Field | Type | Validation |
|-------|------|------------|
| `openalex_id` | `str` | Non-nullable, regex `^W\d+$`. DQ: pattern enforced |
| `issn` | `str` | Nullable, regex `^\d{4}-\d{3}[\dX]$` |
| `publisher` | `str` | Nullable |
| `oa_status` | `str` | Nullable, isin `OA_STATUS_VALUES` |
| `volume` | `str` | Nullable |
| `issue` | `str` | Nullable |
| `fwci` | `float` | Nullable, ge=0. DQ: range min=0 |
| `is_retracted` | `bool` | Non-nullable |
| `subject_topics` | `str` | Nullable (JSON array) |
| `primary_topic` | `str` | Nullable (JSON object) |
| `grants` | `str` | Nullable (JSON array) |
| `subject_mesh` | `str` | Nullable (JSON array) |
| `subject_keywords` | `str` | Nullable (JSON array) |
| `mag_id` | `str` | Nullable |
| `author_orcids` | `str` | Nullable (JSON array). Custom check: ORCID format validation |
| `author_openalex_ids` | `str` | Nullable (JSON array) |
| `institution_ids` | `str` | Nullable (JSON array) |
| `institution_country_codes` | `str` | Nullable (JSON array) |
| `ror_ids` | `str` | Nullable (JSON array) |

---

## 5. ChEMBL Derived Entities

### 5.1 Publication Term (`PublicationTermSchema`)

| Field | Type | Validation |
|-------|------|------------|
| `document_chembl_id` | `str` | Non-nullable, regex `^CHEMBL\d+$` |
| `term` | `str` | Non-nullable, min length 1 |
| `term_type` | `str` | Non-nullable, isin `["MESH_HEADING", "MESH_QUALIFIER", "KEYWORD", "CONCEPT"]` |
| `mesh_id` | `str` | Nullable |
| `qualifier` | `str` | Nullable |

Config: `strict=True`, `coerce=True`. Does not inherit from `PublicationBaseSchema`.

### 5.2 Publication Similarity (`PublicationSimilaritySchema`)

| Field | Type | Validation |
|-------|------|------------|
| `sim_id` | `int` | Non-nullable |
| `doc_1` | `int` | Non-nullable |
| `doc_2` | `int` | Non-nullable |
| `pubmed_id1` | `str` | Nullable, regex `^\d+$` |
| `pubmed_id2` | `str` | Nullable, regex `^\d+$` |
| `tid_tani` | `float` | Nullable, range [0, 1] |
| `mol_tani` | `float` | Nullable, range [0, 1] |
| `avg_tani` | `float` | Nullable, range [0, 1] |
| `max_tani` | `float` | Nullable, range [0, 1] |

Config: `strict=True`, `ordered=True`, `coerce=True`. Does not inherit from `PublicationBaseSchema`.

---

## 6. Fields with Divergent Validation

This section highlights fields that share the **same name** across pipelines but have
**different validation rules**, nullability, or semantics.

### 6.1 `publication_year`

| Aspect | ChEMBL | PubMed | SemanticScholar | CrossRef | OpenAlex |
|--------|--------|--------|-----------------|----------|----------|
| **Schema Type** | `pd.Int64Dtype` | `pd.Int64Dtype` (base) | `pd.Int64Dtype` (base) | `pd.Int64Dtype` (base) | `pd.Int64Dtype` (base) |
| **Nullable** | Yes | Yes | Yes | Yes | Yes |
| **Range (Schema)** | ge=1500, le=2100 | ge=1500, le=2100 | ge=1500, le=2100 | ge=1500, le=2100 | ge=1500, le=2100 |
| **DQ field name** | `year` | `pub_year` | `year` | `year` | `year` |
| **DQ Range** | 1500..2100 | 1500..2100 | 1500..2100 | 1500..2100 | 1500..2100 |
| **Transformer VO** | `PublicationYear.from_raw()` | `PublicationYear.from_raw()` | `validate_year()` (custom) | `extract_year()` (custom) | `PublicationYear` VO |
| **Source field** | `year` | PubDate XML element | `year` | date-parts array | `publication_year` |

**Divergence:** Schema/range rules are aligned. Main divergence is in **DQ field naming**
(`year` vs `pub_year`) and **transformer validation** (some use `PublicationYear` VO, others
use custom functions).

### 6.2 `publication_type`

| Aspect | ChEMBL | PubMed | SemanticScholar | CrossRef | OpenAlex |
|--------|--------|--------|-----------------|----------|----------|
| **Schema Type** | `str` | `str` | `str` | `str` | `str` |
| **Nullable** | Yes | Yes | Yes | Yes | Yes |
| **Schema constraint** | isin `PUBLICATION_TYPES` (PUBLICATION, PATENT, DATASET, BOOK) | None (base) | None (description only) | None (description only) | None (description only) |
| **DQ field name** | `doc_type` | `pub_type` | -- | `type` | `type` |
| **DQ type** | enum: PUBLICATION, BOOK, DATASET, PATENT | enum: Journal Article, Review, Letter, etc. | -- | enum: journal-article, book-chapter, etc. | enum: article, book-chapter, book, etc. |
| **Transformer logic** | `doc_type` -> `publication_type` rename | Hardcoded `"PUBLICATION"` | Pipe-delimited join from list, default `"PUBLICATION"` | Raw CrossRef `type` passthrough | Raw OpenAlex `type` passthrough |
| **Vocabulary** | BioETL internal (UPPER) | NLM MeSH vocabulary | S2 types (pipe-delimited) | CrossRef native (kebab-case) | OpenAlex native (lowercase) |

**Divergence:** Significant. Each pipeline uses a **different vocabulary** for the same
field. ChEMBL uses an internal enum. PubMed hardcodes the value. S2 joins with pipes.
CrossRef and OpenAlex pass through raw API values in different formats.

### 6.3 `doi`

| Aspect | ChEMBL | PubMed | SemanticScholar | CrossRef | OpenAlex |
|--------|--------|--------|-----------------|----------|----------|
| **Nullable** | Yes | Yes | Yes | **No** (PK) | Yes |
| **Schema regex** | `DOI_REGEX_PATTERN` | `DOI_REGEX_PATTERN` | `DOI_REGEX_PATTERN` (base) | `DOI_REGEX_PATTERN` | `DOI_REGEX_PATTERN` |
| **Transformer VO** | `DOI.from_raw()` | `DOI.from_raw()` | `DOI.from_raw()` | `DOI` VO + pre-validation | `DOI` VO |
| **DQ pattern** | `^10\.\d{4,}/.+$` | `^10\.\d{4,}/.+$` | `^10\.\d{4,}/.+$` | `^10\.\d{4,}/.+$`, **required** | `^10\.\d{4,}/.+$` |
| **Pre-validation** | No | No | No | ValueError if missing/invalid | No |

**Divergence:** Nullability differs -- CrossRef requires DOI as primary key (non-nullable + pre-validation).
Regex and VO usage are aligned.

### 6.4 `pmid`

| Aspect | ChEMBL | PubMed | SemanticScholar | CrossRef | OpenAlex |
|--------|--------|--------|-----------------|----------|----------|
| **Nullable** | Yes | **No** (PK) | Yes | Excluded | Yes |
| **Schema type** | `str` | `str` | `str` | -- | `str` |
| **Schema regex** | `^[1-9]\d*$` (base) | custom check `^[1-9]\d*$` | `^[1-9]\d*$` (base) | -- | `^[1-9]\d*$` (base) |
| **Transformer VO** | `PMID` converter | `PubMedId.from_raw()` | `PubMedId.from_raw()` | -- | Extracted from `ids.pmid` (no VO) |
| **DQ** | range 1..100M | range 1..100M, **required** | -- | -- | -- |

**Divergence:** Nullability (PubMed requires it as PK). OpenAlex lacks VO validation on extraction.
DQ coverage is inconsistent (only ChEMBL and PubMed have PMID DQ rules).

### 6.5 `title`

| Aspect | ChEMBL | PubMed | SemanticScholar | CrossRef | OpenAlex |
|--------|--------|--------|-----------------|----------|----------|
| **Nullable** | Yes | **No** | Yes | Yes | Yes |
| **Schema constraint** | None | Custom check `title_not_empty` (len >= 1) | None | None | None |
| **DQ** | max_length 2000 | pattern `.{1,2000}` | pattern `.{1,2000}` | pattern `.{1,2000}` | pattern `.{1,2000}` |
| **Transformer** | Direct passthrough | Direct from XML | Direct passthrough | `extract_first_string()` from list | Direct passthrough |

**Divergence:** PubMed requires non-nullable title with non-empty check. ChEMBL uses max_length
DQ rule instead of pattern. All others treat title as nullable.

### 6.6 `_source`

| Aspect | ChEMBL | PubMed | SemanticScholar | CrossRef | OpenAlex |
|--------|--------|--------|-----------------|----------|----------|
| **Nullable** | No | No | No | No | No |
| **Constraint** | eq `"chembl"` | eq `"pubmed"` | eq `"semanticscholar"` | eq `"crossref"` | eq `"openalex"` |

**Divergence:** None -- correctly parametrized per provider. Aligned by design.

### 6.7 `citations_received`

| Aspect | ChEMBL | PubMed | SemanticScholar | CrossRef | OpenAlex |
|--------|--------|--------|-----------------|----------|----------|
| **Available** | Conditional (if `citation_count` present) | **No** (excluded) | Yes | Yes | Yes |
| **Schema** | `Int64`, nullable, ge=0 | `Int64`, nullable, ge=0 (base) | `Int64`, nullable, ge=0 | `Int64`, nullable, ge=0 | `Int64`, nullable, ge=0 |
| **DQ** | -- | -- | range min=0 | range min=0 | range min=0 |
| **Source field** | `citation_count` | -- | `citationCount` | `is-referenced-by-count` | `cited_by_count` |

**Divergence:** PubMed cannot provide this field. ChEMBL has it conditionally. DQ coverage
varies (ChEMBL/PubMed have no DQ rule, others do).

### 6.8 `subject_keywords`

| Aspect | PubMed | CrossRef | OpenAlex |
|--------|--------|----------|----------|
| **Schema Type** | `str` (JSON array) | `str` (JSON array) | `str` (JSON array) |
| **Transformer** | `ClassificationExtractor.parse_keywords()` | Raw `subject` list passthrough | `extract_keywords()` |
| **DQ** | -- | -- | -- |

**Divergence:** Extraction logic differs. PubMed parses from MeSH keywords. CrossRef and
OpenAlex extract from different API fields. No unified vocabulary.

### 6.9 `subject_mesh`

| Aspect | PubMed | OpenAlex |
|--------|--------|----------|
| **Schema Type** | `str` (JSON array) | `str` (JSON array) |
| **Transformer** | `ClassificationExtractor.parse_mesh_terms()` from MEDLINE | `extract_mesh_terms()` from OpenAlex `mesh` array |
| **Granularity** | Descriptor + qualifier pairs | Descriptor names only |

**Divergence:** PubMed provides more granular MeSH data (descriptor/qualifier pairs).
OpenAlex provides descriptor names only.

### 6.10 `oa_status`

| Aspect | SemanticScholar | OpenAlex |
|--------|-----------------|----------|
| **Schema Type** | `str` | `str` |
| **Constraint** | isin `OA_STATUS_VALUES` (gold, green, hybrid, bronze, closed) | isin `OA_STATUS_VALUES` |
| **Transformer** | From `openAccessPdf.status`, normalized to lowercase | From `open_access.oa_status` |

**Divergence:** Aligned on vocabulary. Source API fields differ.

### 6.11 `author_orcids`

| Aspect | SemanticScholar | OpenAlex |
|--------|-----------------|----------|
| **Field name** | `author_orcids` | `author_orcids` |
| **Schema Type** | `str` (JSON array) | `str` (JSON array) |
| **Custom check** | ORCID format regex `^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$` | ORCID format regex (same pattern) |

CrossRef uses `author_orcid_list` (different field name) with the same ORCID check.

**Divergence:** CrossRef uses a different field name for the same concept.

### 6.12 `issn`

| Aspect | PubMed | CrossRef | OpenAlex |
|--------|--------|----------|----------|
| **Schema regex** | `^\d{4}-\d{3}[\dX]$` | `^\d{4}-\d{3}[\dX]$` | `^\d{4}-\d{3}[\dX]$` |
| **Semantics** | Primary ISSN from journal | First from ISSN array | ISSN-L |

**Divergence:** Same format validation but different semantics for which ISSN is stored.

### 6.13 `_lookup_method`

| Aspect | ChEMBL | PubMed | SemanticScholar | CrossRef | OpenAlex |
|--------|--------|--------|-----------------|----------|----------|
| **Default** | `"direct"` | `"pmid"` | `"unknown"` | `"doi"` | `"unknown"` |
| **Enum** | `LOOKUP_METHODS` | `LOOKUP_METHODS` | `LOOKUP_METHODS` | `LOOKUP_METHODS` | `LOOKUP_METHODS` |

**Divergence:** Default values differ (appropriate per provider). Enum set is shared.

---

## 7. Unification Plans

### 7.1 `publication_year` -- Unify Transformer Validation

**Current state:** Schema rules aligned (ge=1500, le=2100), but transformer validation
uses different mechanisms: `PublicationYear.from_raw()` VO (ChEMBL, PubMed, OpenAlex)
vs `validate_year()` custom function (SemanticScholar) vs `extract_year()` (CrossRef).
DQ configs use inconsistent field names (`year`, `pub_year`).

**Plan:**

| Step | Action | Files |
|------|--------|-------|
| 1 | Ensure all 5 transformers use `PublicationYear.from_raw()` Value Object | `semanticscholar/transformer.py`, `crossref/transformer.py` |
| 2 | Rename DQ field `pub_year` -> `publication_year` in PubMed DQ config | `configs/dq/entities/pubmed/publication.yaml` |
| 3 | Rename DQ field `year` -> `publication_year` in ChEMBL, S2, CrossRef, OpenAlex DQ configs | `configs/dq/entities/{provider}/publication.yaml` |
| 4 | Verify `validate_year()` in S2 extractors delegates to `PublicationYear` VO | `semanticscholar/extractors.py` |

**Risk:** Low. `PublicationYear` VO already uses the same range (1500..2100).

---

### 7.2 `publication_type` -- Normalize Vocabulary

**Current state:** Five different vocabularies for the same concept. This is the most
significant divergence and blocks cross-provider aggregation in the composite pipeline.

**Plan:**

| Step | Action | Files |
|------|--------|-------|
| 1 | Define canonical `PublicationType` enum in domain: `JOURNAL_ARTICLE`, `REVIEW`, `BOOK`, `BOOK_CHAPTER`, `PREPRINT`, `DATASET`, `PATENT`, `EDITORIAL`, `LETTER`, `CLINICAL_TRIAL`, `OTHER` | `domain/value_objects/publication_type.py` (new) |
| 2 | Create per-provider mapping tables (raw value -> canonical) | `domain/mapping/publication_type_mapping.py` (new) |
| 3 | Add `PublicationTypeMapper` class with `map(raw_value, provider) -> PublicationType` | Same file |
| 4 | Apply mapper in each transformer before setting `publication_type` | All 5 `transformer.py` files |
| 5 | Keep raw value in provider-specific field `publication_type_raw` for forensic retention | All 5 schemas |
| 6 | Update DQ configs to validate against canonical enum | `configs/dq/entities/*/publication.yaml` |
| 7 | Update `PublicationBaseSchema.publication_type` to isin canonical values | `domain/schemas/common/publication_base.py` |

**Risk:** Medium. Requires mapping table curation. Some raw values may not map cleanly. Pipe-delimited S2 values need special handling (multi-type records).

**Provider mapping examples:**

| Raw Value (Provider) | Canonical |
|----------------------|-----------|
| `PUBLICATION` (ChEMBL) | `JOURNAL_ARTICLE` |
| `PATENT` (ChEMBL) | `PATENT` |
| `journal-article` (CrossRef) | `JOURNAL_ARTICLE` |
| `posted-content` (CrossRef) | `PREPRINT` |
| `article` (OpenAlex) | `JOURNAL_ARTICLE` |
| `preprint` (OpenAlex) | `PREPRINT` |
| `Review` (S2 type) | `REVIEW` |
| `Journal Article` (PubMed) | `JOURNAL_ARTICLE` |

---

### 7.3 `doi` -- Align Nullability Documentation

**Current state:** CrossRef requires non-nullable DOI (primary key). All others allow nullable.
This is **correct by design** since CrossRef's primary identifier IS the DOI.

**Plan:**

| Step | Action | Files |
|------|--------|-------|
| 1 | No schema change needed -- divergence is intentional | -- |
| 2 | Add DQ rule for DOI coverage to S2 and OpenAlex (currently missing) | `configs/dq/entities/semanticscholar/publication.yaml`, `configs/dq/entities/openalex/publication.yaml` |
| 3 | Document per-provider DOI availability expectations | This document (done) |

**Risk:** None.

---

### 7.4 `pmid` -- Add VO Validation to OpenAlex

**Current state:** ChEMBL uses `PMID` converter, PubMed and S2 use `PubMedId.from_raw()` VO.
OpenAlex extracts PMID from `ids.pmid` without Value Object validation.

**Plan:**

| Step | Action | Files |
|------|--------|-------|
| 1 | Add `PubMedId.from_raw()` validation in OpenAlex `extract_external_ids()` | `openalex/extractors.py` |
| 2 | Add DQ PMID rules for S2 and OpenAlex pipelines | `configs/dq/entities/semanticscholar/publication.yaml`, `configs/dq/entities/openalex/publication.yaml` |

**Risk:** Low.

---

### 7.5 `title` -- Align Nullability and DQ

**Current state:** PubMed requires non-nullable title. Others allow nullable. ChEMBL uses
`max_length` DQ rule; others use pattern `.{1,2000}`.

**Plan:**

| Step | Action | Files |
|------|--------|-------|
| 1 | Standardize DQ rule: use `max_length: 2000` across all providers (cleaner than regex pattern for length check) | `configs/dq/entities/*/publication.yaml` |
| 2 | Keep PubMed title as non-nullable (MEDLINE articles always have titles -- correct by design) | No change |
| 3 | Consider adding `str_length(min_value=1)` to base schema for non-null titles | `domain/schemas/common/publication_base.py` |

**Risk:** Low.

---

### 7.6 `citations_received` -- Add DQ Coverage

**Current state:** S2, CrossRef, OpenAlex have DQ range rules. ChEMBL and PubMed do not
(ChEMBL has it conditionally, PubMed doesn't provide it at all).

**Plan:**

| Step | Action | Files |
|------|--------|-------|
| 1 | Add DQ range rule (min=0) for `citations_received` in ChEMBL DQ config | `configs/dq/entities/chembl/publication.yaml` |
| 2 | No change for PubMed (field not available) | -- |

**Risk:** None.

---

### 7.7 `subject_keywords` -- Normalize Extraction

**Current state:** PubMed extracts from MeSH keywords, CrossRef from `subject`, OpenAlex
from `keywords`. Different extraction logic, no shared vocabulary.

**Plan:**

| Step | Action | Files |
|------|--------|-------|
| 1 | Ensure all extractors produce lowercase, trimmed keyword lists | Per-provider extractors |
| 2 | Add unified field documentation to `PublicationBaseSchema` | `domain/schemas/common/publication_base.py` |
| 3 | Consider adding a `KeywordNormalizer` domain service for deduplication and case normalization | `domain/services/keyword_normalizer.py` (new, optional) |

**Risk:** Low. Vocabularies are inherently different across providers; full unification is not feasible.

---

### 7.8 `author_orcids` / `author_orcid_list` -- Unify Field Name

**Current state:** S2 and OpenAlex use `author_orcids`. CrossRef uses `author_orcid_list`.
All have the same ORCID format validation.

**Plan:**

| Step | Action | Files |
|------|--------|-------|
| 1 | Rename CrossRef `author_orcid_list` -> `author_orcids` for consistency | `crossref/publication.py` (schema), `crossref/transformer.py`, `gold/publications.py` |
| 2 | Add `author_orcids` to `PublicationBaseSchema` as optional common field | `domain/schemas/common/publication_base.py` |
| 3 | Move ORCID format check to base schema | Same file |

**Risk:** Low. Breaking change for CrossRef Silver/Gold data -- requires migration or `REBUILD` run.

---

### 7.9 `issn` -- Document Semantic Differences

**Current state:** Same format validation, different semantics: PubMed = primary ISSN,
CrossRef = first from array, OpenAlex = ISSN-L.

**Plan:**

| Step | Action | Files |
|------|--------|-------|
| 1 | Add `issn_type` field to base schema or per-provider schemas | Consider for future version |
| 2 | Document the semantic difference (linking ISSN vs print/electronic) | This document (done) |
| 3 | In composite pipeline, prefer ISSN-L (OpenAlex) for deduplication | `application/composite/merger.py` |

**Risk:** Low. Not a validation divergence per se, but important for composite pipeline correctness.

---

### 7.10 `subject_mesh` -- Align Granularity

**Current state:** PubMed provides descriptor + qualifier pairs. OpenAlex provides descriptor
names only. Both store as JSON array of strings.

**Plan:**

| Step | Action | Files |
|------|--------|-------|
| 1 | No immediate change needed -- granularity difference is inherent to the data sources | -- |
| 2 | In composite pipeline, merge MeSH terms by descriptor name (ignore qualifiers for dedup) | `application/composite/merger.py` |
| 3 | Consider adding `subject_mesh_detailed` field for PubMed's richer data | Future version |

**Risk:** None.

---

## Summary of Priority Actions

| Priority | Action | Impact | Effort |
|----------|--------|--------|--------|
| **P0** | Unify `publication_type` vocabulary (7.2) | Blocks composite aggregation | High |
| **P1** | Unify `publication_year` transformer validation (7.1) | Consistency | Low |
| **P1** | Unify `author_orcids` field name (7.8) | Consistency | Medium (migration) |
| **P2** | Add `PubMedId` VO to OpenAlex (7.4) | Data quality | Low |
| **P2** | Align DQ field names for `publication_year` (7.1) | DQ consistency | Low |
| **P2** | Add missing DQ rules for `citations_received` (7.6) | DQ coverage | Low |
| **P3** | Standardize `title` DQ rule (7.5) | DQ consistency | Low |
| **P3** | Normalize `subject_keywords` extraction (7.7) | Minor quality improvement | Low |
| **P3** | Document ISSN semantics (7.9) | Documentation | Low |

---

## References

- **PublicationBaseSchema**: `src/bioetl/domain/schemas/common/publication_base.py`
- **Provider Schemas**: `src/bioetl/domain/schemas/{provider}/publication.py`
- **Gold Contracts**: `src/bioetl/domain/contracts/gold/publications.py`
- **DQ Configs**: `configs/dq/entities/{provider}/publication.yaml`
- **Transformers**: `src/bioetl/application/pipelines/{provider}/transformer.py`
- **Validation Module**: `src/bioetl/domain/validation.py`
- **Schema Constants**: `src/bioetl/domain/schemas/constants.py`
