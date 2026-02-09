# Publication Validation Matrix

*Version: 1.0.0 | Date: 2026-02-09*

Cross-provider analysis of validation rules for `publication` entity across all 5 pipelines:
**ChEMBL**, **PubMed**, **CrossRef**, **OpenAlex**, **Semantic Scholar**.

Sources analysed:
- Pandera Silver schemas (`domain/schemas/{provider}/publication.py`)
- Pandera base schema (`domain/schemas/common/publication_base.py`)
- Gold contracts (`domain/contracts/gold/publications.py`)
- DQ rules (`configs/dq/entities/{provider}/publication.yaml`)
- Filter rules (`configs/filter/entities/{provider}/publication.yaml`)
- Value Objects (`domain/value_objects/publications.py`)
- Domain validation (`domain/validation.py`)

---

## Table of Contents

1. [Validation Layers Overview](#1-validation-layers-overview)
2. [Unified Fields Matrix (Base Schema)](#2-unified-fields-matrix-base-schema)
3. [Primary Key Validation](#3-primary-key-validation)
4. [Provider-Specific Fields](#4-provider-specific-fields)
5. [DQ Rules Matrix](#5-dq-rules-matrix)
6. [Filter Rules Matrix](#6-filter-rules-matrix)
7. [Gold Schema Matrix](#7-gold-schema-matrix)
8. [Cross-Field Validations](#8-cross-field-validations)
9. [Discrepancy Analysis: Fields with Different Validation](#9-discrepancy-analysis-fields-with-different-validation)
10. [Unification Plans](#10-unification-plans)

---

## 1. Validation Layers Overview

Each publication record passes through 4 validation layers:

| Layer | Location | Engine | Scope |
|-------|----------|--------|-------|
| **Value Object** | `domain/value_objects/` | Python classes | DOI, PubMedId normalization + format check |
| **Pandera Silver** | `domain/schemas/{provider}/` | Pandera DataFrameModel | Structural column validation on Silver write |
| **DQ Rules** | `configs/dq/entities/{provider}/` | YAML -> DQ Engine | Field-level + cross-field quality rules |
| **Filter (Gold)** | `configs/filter/entities/{provider}/` | YAML -> Filter Engine | Range narrowing + required-field enforcement for Gold |
| **Pandera Gold** | `domain/contracts/gold/` | Pandera DataFrameModel (strict) | Final Gold schema validation |

---

## 2. Unified Fields Matrix (Base Schema)

Fields inherited by all providers from `PublicationBaseSchema`.
"Override" column shows which providers redefine the field.

| Field | Type | Nullable | Validation (Base) | Overrides |
|-------|------|----------|-------------------|-----------|
| `pmid` | `str` | Yes | `^[1-9]\d*$` | PubMed: **nullable=False** (PK) |
| `doi` | `str` | Yes | `^10\.\d{4,}/\S+$` (DOI_REGEX_PATTERN) | CrossRef: **nullable=False** (PK); PubMed: re-declares with same pattern |
| `pmc_id` | `str` | Yes | `^PMC\d+$` | PubMed: custom `@pa.check` for same pattern |
| `title` | `str` | Yes | `@pa.check` title_not_empty (len >= 1 when present) | PubMed: **nullable=False** |
| `abstract` | `str` | Yes | -- | -- |
| `authors` | `str` | Yes | -- (JSON array) | -- |
| `affiliation_list` | `str` | Yes | -- (JSON array) | -- |
| `author_orcids` | `str` | Yes | `@pa.check` orcid_format: each element matches `^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$` | -- |
| `journal` | `str` | Yes | -- | PubMed, OpenAlex: re-declare (same rules) |
| `publication_year` | `Int64` | Yes | `ge=1500, le=2100` (MIN/MAX_PUBLICATION_YEAR) | -- |
| `publication_date` | `str` | Yes | `^\d{4}-\d{2}-\d{2}$` | -- |
| `publication_type` | `str` | Yes | -- (free text) | ChEMBL: `isin [PUBLICATION, PATENT, DATASET, BOOK]`; CrossRef: free text; OpenAlex: free text; S2: free text |
| `language` | `str` | Yes | `str_length min=2, max=3` | -- |
| `page_first` | `str` | Yes | -- | ChEMBL: re-declares (same) |
| `page_last` | `str` | Yes | -- | ChEMBL: re-declares (same) |
| `citations_received` | `Int64` | Yes | `ge=0` | -- |
| `citations_made` | `Int64` | Yes | `ge=0` | -- |
| `is_oa` | `bool` | Yes | -- | -- |
| `_lookup_method` | `str` | **No** | `isin [direct, doi, pmid, title_fallback, title_only, unknown]` | -- |
| `_original_id` | `str` | Yes | -- | -- |
| `_source` | `str` | Yes | -- | All providers override: **nullable=False**, `eq="{provider}"` |

---

## 3. Primary Key Validation

| Provider | PK Field | Type | Pattern | Nullable | DQ Rule | Value Object |
|----------|----------|------|---------|----------|---------|--------------|
| **ChEMBL** | `document_chembl_id` | `str` | `^CHEMBL\d+$` | No | `pattern ^CHEMBL\d+$` | -- |
| **PubMed** | `pmid` | `str` | `^[1-9]\d*$` | No | `range 1..10^10` | `PubMedId` VO: digits-only, positive, < 10^10 |
| **CrossRef** | `doi` | `str` | `^10\.\d{4,}/\S+$` | No | `pattern ^10\.\d{4,}/\S+$` | `DOI` VO: strips URL prefix, lowercase |
| **OpenAlex** | `openalex_id` | `str` | `^W\d+$` | No | `pattern ^W\d+$` | -- |
| **Semantic Scholar** | `paper_id` | `str` | `^[a-f0-9]{40}$` | No | `pattern ^[a-f0-9]{40}$` | -- |

---

## 4. Provider-Specific Fields

### 4.1 ChEMBL-Only Fields

| Field | Type | Nullable | Validation |
|-------|------|----------|------------|
| `src_id` | `Int64` | Yes | -- |
| `chembl_release` | `str` | Yes | -- |
| `creation_date` | `str` | Yes | `^\d{4}-\d{2}-\d{2}$` (ISO_DATE_PATTERN) |
| `volume` | `str` | Yes | -- |
| `issue` | `str` | Yes | -- |
| `_dq_warn` | `Boolean` | Yes | default=False |
| `_dq_error` | `Boolean` | Yes | default=False |

### 4.2 PubMed-Only Fields

| Field | Type | Nullable | Validation |
|-------|------|----------|------------|
| `abstract_structured` | `bool` | Yes | -- |
| `journal_name_short` | `str` | Yes | -- |
| `journal_iso_abbrev` | `str` | Yes | -- |
| `issn` | `str` | Yes | `^\d{4}-\d{3}[\dX]$` (ISSN_PATTERN) |
| `journal_issn_type` | `str` | Yes | `@pa.check` isin [Print, Electronic, Linking] |
| `nlm_unique_id` | `str` | Yes | -- |
| `country` | `str` | Yes | -- |
| `medline_pgn` | `str` | Yes | -- |
| `page_range` | `str` | Yes | -- |
| `pub_month` | `Int64` | Yes | `@pa.check` 1..12 |
| `pub_day` | `Int64` | Yes | `@pa.check` 1..31 |
| `publication_status` | `str` | Yes | `@pa.check` isin [ppublish, epublish, aheadofprint] |
| `publication_type_list` | `str` | Yes | -- (JSON array) |
| `date_completed` | `datetime` | Yes | -- |
| `date_revised` | `datetime` | Yes | -- |
| `citation_subset` | `str` | Yes | -- |
| `affiliation_structured` | `str` | Yes | -- (JSON array) |
| `author_count` | `Int64` | Yes | `@pa.check` >= 0 |
| `mesh_heading_count` | `Int64` | Yes | `@pa.check` >= 0 |
| `keyword_count` | `Int64` | Yes | `@pa.check` >= 0 |
| `grant_count` | `Int64` | Yes | `@pa.check` >= 0 |
| `chemical_count` | `Int64` | Yes | `@pa.check` >= 0 |
| `subject_mesh` | `str` | Yes | -- (JSON array) |
| `chemicals` | `str` | Yes | -- (JSON array) |
| `subject_keywords` | `str` | Yes | -- (JSON array) |
| `databanks` | `str` | Yes | -- (JSON array) |
| `gene_symbols` | `str` | Yes | -- (JSON array) |
| `publication_types` | `str` | Yes | -- (JSON array) |
| `pii` | `str` | Yes | -- |
| `mid` | `str` | Yes | -- |
| `publisher_id` | `str` | Yes | -- |
| `authors_with_affiliations` | `str` | Yes | -- (JSON array) |

### 4.3 CrossRef-Only Fields

| Field | Type | Nullable | Validation |
|-------|------|----------|------------|
| `issn` | `str` | Yes | `^\d{4}-\d{3}[\dX]$` (ISSN_PATTERN) |
| `issn_list` | `str` | Yes | -- (JSON array) |
| `publisher` | `str` | Yes | -- |
| `published_print` | `str` | Yes | -- |
| `published_online` | `str` | Yes | -- |
| `published` | `str` | Yes | -- (canonical date) |
| `license_url` | `str` | Yes | -- |
| `subject_keywords` | `str` | Yes | -- (JSON array) |
| `content_domain_domains` | `object` | Yes | -- |
| `content_domain_crossmark_restriction` | `bool` | Yes | coerce=True |
| `alternative_id` | `object` | Yes | -- |
| `journal_name_short` | `str` | Yes | -- |
| `issn_print` | `str` | Yes | `^\d{4}-\d{3}[\dX]$` (ISSN_PATTERN) |
| `issn_electronic` | `str` | Yes | `^\d{4}-\d{3}[\dX]$` (ISSN_PATTERN) |
| `author_details` | `str` | Yes | -- (JSON array) |
| `references` | `str` | Yes | -- (JSON array) |

### 4.4 OpenAlex-Only Fields

| Field | Type | Nullable | Validation |
|-------|------|----------|------------|
| `issn` | `str` | Yes | `^\d{4}-\d{3}[\dX]$` (ISSN_PATTERN) |
| `publisher` | `str` | Yes | -- |
| `oa_status` | `str` | Yes | `isin [gold, green, hybrid, bronze, closed]` |
| `volume` | `str` | Yes | -- |
| `issue` | `str` | Yes | -- |
| `fwci` | `float` | Yes | `ge=0` |
| `is_retracted` | `bool` | **No** | -- |
| `subject_topics` | `str` | Yes | -- (JSON array) |
| `primary_topic` | `str` | Yes | -- (JSON object) |
| `grants` | `str` | Yes | -- (JSON array) |
| `subject_mesh` | `str` | Yes | -- (JSON array) |
| `subject_keywords` | `str` | Yes | -- (JSON array) |
| `mag_id` | `str` | Yes | -- |
| `author_openalex_ids` | `str` | Yes | -- (JSON array) |
| `institution_ids` | `str` | Yes | -- |
| `institution_country_codes` | `str` | Yes | -- |
| `ror_ids` | `str` | Yes | -- (JSON array) |

### 4.5 Semantic Scholar-Only Fields

| Field | Type | Nullable | Validation |
|-------|------|----------|------------|
| `dblp_id` | `str` | Yes | -- |
| `corpus_id` | `Int64` | Yes | `ge=0` |
| `tldr` | `str` | Yes | -- |
| `volume` | `str` | Yes | -- |
| `page_range` | `str` | Yes | -- |
| `influential_citation_count` | `Int64` | Yes | `ge=0` |
| `open_access_url` | `str` | Yes | -- |
| `oa_status` | `str` | Yes | `isin [gold, green, hybrid, bronze, closed]` |
| `subject_fields` | `str` | Yes | -- (JSON array) |
| `publication_type` | `str` | Yes | -- (pipe-delimited) |
| `publication_types` | `str` | Yes | -- (JSON array) |
| `author_s2_ids` | `str` | Yes | -- (JSON array) |
| `author_h_indices` | `str` | Yes | -- (JSON array) |
| `citation_contexts` | `str` | Yes | -- (JSON array) |

---

## 5. DQ Rules Matrix

### 5.1 Field-Level DQ Rules

| Field | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|-------|--------|--------|----------|----------|-----------------|
| **Primary Key** | `document_chembl_id`: pattern `^CHEMBL\d+$`, nullable=false | `pmid`: range 1..10^10, nullable=false | `doi`: pattern `^10\.\d{4,}/\S+$`, nullable=false | `openalex_id`: pattern `^W\d+$`, nullable=false | `paper_id`: pattern `^[a-f0-9]{40}$`, nullable=false |
| **pmid** | range 1..10^10, nullable=true | **(PK, see above)** | -- | range 1..10^10, nullable=true | range 1..10^10, nullable=true |
| **doi** | pattern `^10\.\d{4,}/\S+$`, nullable=true | pattern `^10\.\d{4,}/\S+$`, nullable=true | **(PK, see above)** | pattern `^10\.\d{4,}/\S+$`, nullable=true | pattern `^10\.\d{4,}/\S+$`, nullable=true |
| **title** (max_length) | max_length=2000, nullable=true | max_length=2000, nullable=true | max_length=2000, nullable=true | max_length=2000, nullable=true | max_length=2000, nullable=true |
| **title** (pattern) | `\S`, severity=warn | `\S`, severity=warn | `\S`, severity=warn | `\S`, severity=warn | `\S`, severity=warn |
| **publication_year** | range 1500..2100, nullable=true | range 1500..2100, nullable=true | range 1500..2100, nullable=true | range 1500..2100, nullable=true | range 1500..2100, nullable=true |
| **doc_type / type** | `doc_type`: enum [PUBLICATION, BOOK, DATASET, PATENT] | `pub_type`: enum [Journal Article, Review, Letter, Editorial, Clinical Trial, Meta-Analysis, Case Reports, Comparative Study, Evaluation Study] | `type`: enum [journal-article, book-chapter, proceedings-article, posted-content, book, report, dataset, standard] | `type`: enum [article, book-chapter, book, dataset, dissertation, editorial, letter, review, preprint, other] | -- |
| **pmc_id** | -- | pattern `^PMC\d+$`, nullable=true | -- | -- | -- |
| **citations_received** | -- | -- | range >= 0; warn if > 10M | range >= 0; warn if > 10M | range >= 0; warn if > 10M |
| **citations_made** | -- | -- | range >= 0 | range >= 0 | range >= 0 |
| **fwci** | -- | -- | -- | range >= 0 | -- |
| **influential_citation_count** | -- | -- | -- | -- | range >= 0 |

### 5.2 Cross-Field DQ Rules

| Rule Name | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|-----------|--------|--------|----------|----------|-----------------|
| `publication_identifiable` | **any_present**(pmid, doi, title) | **all_present**(pmid, title) | **all_present**(doi, title) | **all_present**(openalex_id, title) | **all_present**(paper_id, title) |
| `has_identifier` | -- | **any_present**(pmid, doi, pmc_id) | -- | -- | -- |
| `retracted_publication_warning` | -- | -- | -- | warn if `is_retracted == true` | -- |

---

## 6. Filter Rules Matrix

| Parameter | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|-----------|--------|--------|----------|----------|-----------------|
| **publication_year range** | 1950..2050 | 1950..2050 | 1950..2050 | 1950..2050 | 1950..2050 |
| **doc_type filter** | `[PUBLICATION]` only | -- | -- | -- | -- |
| **required_fields** | document_chembl_id, doc_type, title | pmid, title | doi, title | openalex_id, title | paper_id, title |
| **input_filter source** | `data/input/publication.csv` | `data/input/pubmed.csv` | `data/input/dois.csv` | `data/input/dois.csv` | `data/input/dois.csv` |
| **input_filter column** | `document_chembl_id` | `pubmed_id` | `doi` | `doi` | `doi` |
| **fallback_column** | -- | `title` | `title` | `title` | `title` |
| **batch_size** | 16 | 100 | 50 | 50 | 100 |

---

## 7. Gold Schema Matrix

Key differences between providers in Gold layer contracts:

| Field | ChEMBL Gold | PubMed Gold | CrossRef Gold | OpenAlex Gold | S2 Gold |
|-------|-------------|-------------|---------------|---------------|---------|
| **publication_year** | -- (no ChEMBL Gold contract) | `float`, ge=1500, le=2100, coerce | `float`, ge=1500, le=2100, coerce | `float`, ge=1500, le=2100, coerce | `float`, ge=1500, le=2100, coerce |
| **citations_received** | -- | -- | `float`, ge=0, coerce | `float`, ge=0, coerce | `float`, ge=0, coerce |
| **citations_made** | -- | `float`, ge=0, coerce | `float`, ge=0, coerce | `float`, ge=0, coerce | `float`, ge=0, coerce |
| **title nullable** | -- | **No** | Yes | Yes | Yes |
| **doi validation** | -- | DOI_REGEX_PATTERN | DOI_REGEX_PATTERN | DOI_REGEX_PATTERN | DOI_REGEX_PATTERN |
| **strict mode** | -- | True | True | True | True |
| **Int->Float coercion** | -- | pub_month, pub_day, year, counts | year, citations | year, citations, fwci | year, corpus_id, citations |

---

## 8. Cross-Field Validations

### 8.1 Identifiability Rules Comparison

| Provider | Rule | Condition | Severity |
|----------|------|-----------|----------|
| ChEMBL | `publication_identifiable` | `any_present(pmid, doi, title)` -- at least one of three | error |
| PubMed | `publication_identifiable` | `all_present(pmid, title)` -- both required | error |
| PubMed | `has_identifier` | `any_present(pmid, doi, pmc_id)` -- at least one | error |
| CrossRef | `publication_identifiable` | `all_present(doi, title)` -- both required | error |
| OpenAlex | `publication_identifiable` | `all_present(openalex_id, title)` -- both required | error |
| Semantic Scholar | `publication_identifiable` | `all_present(paper_id, title)` -- both required | error |

---

## 9. Discrepancy Analysis: Fields with Different Validation

### 9.1 `publication_year`

| Validation Layer | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|------------------|--------|--------|----------|----------|-----------------|
| **Pandera Silver type** | `Int64` (from base) | `Int64` (from base) | `Int64` (from base) | `Int64` (from base) | `Int64` (from base) |
| **Pandera Silver range** | 1500..2100 | 1500..2100 | 1500..2100 | 1500..2100 | 1500..2100 |
| **DQ range** | 1500..2100 | 1500..2100 | 1500..2100 | 1500..2100 | 1500..2100 |
| **Filter (Gold) range** | **1950..2050** | **1950..2050** | **1950..2050** | **1950..2050** | **1950..2050** |
| **Gold contract type** | -- (no contract) | `float` coerce, 1500..2100 | `float` coerce, 1500..2100 | `float` coerce, 1500..2100 | `float` coerce, 1500..2100 |

**Discrepancy**: DQ validates 1500-2100 but Filter narrows to 1950-2050 for Gold. This is intentional: DQ flags for Silver quality, Filter selects for Gold relevance. However, ChEMBL has no Gold contract schema.

### 9.2 `publication_type` (field name / enum values)

| Aspect | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|--------|--------|--------|----------|----------|-----------------|
| **DQ field name** | `doc_type` | `pub_type` | `type` | `type` | -- |
| **Silver field name** | `publication_type` | `publication_type` (inherited) | `publication_type` | `publication_type` | `publication_type` |
| **Pandera isin** | `[PUBLICATION, PATENT, DATASET, BOOK]` | -- (free text from base) | -- (free text) | -- (free text) | -- (free text) |
| **DQ enum values** | PUBLICATION, BOOK, DATASET, PATENT | Journal Article, Review, Letter, Editorial, Clinical Trial, Meta-Analysis, Case Reports, Comparative Study, Evaluation Study | journal-article, book-chapter, proceedings-article, posted-content, book, report, dataset, standard | article, book-chapter, book, dataset, dissertation, editorial, letter, review, preprint, other | -- (no DQ enum) |
| **Case convention** | UPPER_CASE | Title Case | kebab-case | lowercase | -- |

**Discrepancy**: Four different naming conventions for the same semantic concept. DQ field names differ (`doc_type`, `pub_type`, `type`). Enum value sets use different casing and granularity. Semantic Scholar has no type validation at DQ level.

### 9.3 `title` (nullability)

| Aspect | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|--------|--------|--------|----------|----------|-----------------|
| **Pandera Silver nullable** | Yes (from base) | **No** (overridden) | Yes (from base) | Yes (from base) | Yes (from base) |
| **DQ nullable** | Yes | Yes | Yes | Yes | Yes |
| **Gold nullable** | -- | **No** | Yes | Yes | Yes |
| **Filter required** | Yes | Yes | Yes | Yes | Yes |

**Discrepancy**: PubMed enforces `title` as non-nullable at Pandera Silver level, while all others allow nullable. All providers require `title` in filter config, but PubMed additionally enforces at schema level.

### 9.4 `pmid` (type and validation)

| Aspect | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|--------|--------|--------|----------|----------|-----------------|
| **Pandera Silver type** | `str` (from base) | `str` (overridden, PK) | `str` (from base) | `str` (from base) | `str` (from base) |
| **Pandera nullable** | Yes | **No** (PK) | Yes | Yes | Yes |
| **Pandera pattern** | `^[1-9]\d*$` (from base) | `^[1-9]\d*$` (re-declared) | `^[1-9]\d*$` (from base) | `^[1-9]\d*$` (from base) | `^[1-9]\d*$` (from base) |
| **DQ type** | range 1..10^10 | range 1..10^10 | -- | range 1..10^10 | range 1..10^10 |
| **DQ nullable** | Yes | **No** | -- | Yes | Yes |
| **Value Object** | -- | `PubMedId` VO | -- | -- | -- |

**Discrepancy**: CrossRef DQ rules have no `pmid` validation (CrossRef API doesn't return PMID). PubMed uses Value Object for additional normalization. Base Pandera pattern requires leading non-zero digit (`^[1-9]\d*$`) while DQ uses numeric range.

### 9.5 `doi` (nullability)

| Aspect | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|--------|--------|--------|----------|----------|-----------------|
| **Pandera Silver nullable** | Yes (from base) | Yes (re-declared) | **No** (PK, overridden) | Yes (from base) | Yes (from base) |
| **DQ nullable** | Yes | Yes | **No** | Yes | Yes |
| **Pandera pattern** | `^10\.\d{4,}/\S+$` | `^10\.\d{4,}/\S+$` | `^10\.\d{4,}/\S+$` | `^10\.\d{4,}/\S+$` | `^10\.\d{4,}/\S+$` |
| **Value Object** | `DOI.from_raw` in transformer | -- | `DOI` VO (implicit) | -- | -- |

**Discrepancy**: CrossRef uses DOI as PK (non-nullable). ChEMBL transformer applies `DOI.from_raw` Value Object for normalization, but other providers rely only on Pandera regex.

### 9.6 `_source` (fixed value)

| Aspect | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|--------|--------|--------|----------|----------|-----------------|
| **Pandera eq** | `"chembl"` | `"pubmed"` | `"crossref"` | `"openalex"` | `"semanticscholar"` |
| **Pandera nullable** | No | No | No | No | No |

**No discrepancy** -- by design each provider has a different fixed value.

### 9.7 `citations_received` (DQ rules presence)

| Aspect | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|--------|--------|--------|----------|----------|-----------------|
| **Pandera Silver** | `Int64`, ge=0 (from base) | `Int64`, ge=0 (from base) | `Int64`, ge=0 (from base) | `Int64`, ge=0 (from base) | `Int64`, ge=0 (from base) |
| **DQ error rule** | -- | -- | range >= 0 | range >= 0 | range >= 0 |
| **DQ warn rule** | -- | -- | warn if > 10M | warn if > 10M | warn if > 10M |
| **Gold type** | -- | -- | `float`, ge=0, coerce | `float`, ge=0, coerce | `float`, ge=0, coerce |

**Discrepancy**: ChEMBL and PubMed have **no** DQ rules for `citations_received` (ChEMBL API doesn't return citation counts; PubMed doesn't provide them natively). CrossRef, OpenAlex, and S2 share identical DQ rules with the 10M warn threshold.

### 9.8 `citations_made` (DQ rules presence)

| Aspect | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|--------|--------|--------|----------|----------|-----------------|
| **DQ rule** | -- | -- | range >= 0 | range >= 0 | range >= 0 |

**Discrepancy**: Same as `citations_received` -- missing from ChEMBL and PubMed DQ.

### 9.9 `publication_identifiable` (cross-field logic)

| Provider | Condition | Fields | Strictness |
|----------|-----------|--------|------------|
| ChEMBL | `any_present` | pmid, doi, title | **Lenient** -- only 1 of 3 needed |
| PubMed | `all_present` | pmid, title | **Strict** -- both required |
| CrossRef | `all_present` | doi, title | **Strict** -- both required |
| OpenAlex | `all_present` | openalex_id, title | **Strict** -- both required |
| Semantic Scholar | `all_present` | paper_id, title | **Strict** -- both required |

**Discrepancy**: ChEMBL uses `any_present` (lenient: just one identifier suffices) while all others use `all_present` (PK + title both required). This means ChEMBL can pass DQ with only a DOI and no title.

### 9.10 `issn` (pattern validation presence)

| Aspect | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|--------|--------|--------|----------|----------|-----------------|
| **Has field** | No | Yes | Yes | Yes | No |
| **Pandera pattern** | -- | `^\d{4}-\d{3}[\dX]$` | `^\d{4}-\d{3}[\dX]$` | `^\d{4}-\d{3}[\dX]$` | -- |

**No real discrepancy** -- field is simply absent where the API doesn't provide ISSN.

### 9.11 `oa_status` (presence)

| Aspect | ChEMBL | PubMed | CrossRef | OpenAlex | Semantic Scholar |
|--------|--------|--------|----------|----------|-----------------|
| **Has field** | No | No | No | Yes | Yes |
| **Pandera isin** | -- | -- | -- | `[gold, green, hybrid, bronze, closed]` | `[gold, green, hybrid, bronze, closed]` |

**No discrepancy** between providers that have it -- both use the same enum from `OA_STATUS_VALUES`.

### 9.12 `subject_keywords` (type in Gold)

| Aspect | PubMed Gold | CrossRef Gold | OpenAlex Gold |
|--------|-------------|---------------|---------------|
| **Type** | `Series[object]` (list) | `Series[object]` (list) | `Series[object]` (list) |

**No discrepancy** -- consistent across all Gold schemas.

---

## 10. Unification Plans

### 10.1 `publication_type` -- Enum Value Normalization

**Problem**: Four different casing conventions and value vocabularies.

| Current Values | Proposed Unified Value | Mapping |
|----------------|----------------------|---------|
| PUBLICATION (ChEMBL), Journal Article (PubMed), journal-article (CrossRef), article (OpenAlex) | `journal-article` | Normalize in transformer |
| BOOK (ChEMBL), -- (PubMed), book (CrossRef/OpenAlex) | `book` | |
| DATASET (ChEMBL), -- (PubMed), dataset (CrossRef/OpenAlex) | `dataset` | |
| PATENT (ChEMBL) | `patent` | ChEMBL-only |
| Review (PubMed), review (OpenAlex) | `review` | |
| Letter (PubMed), letter (OpenAlex) | `letter` | |
| Editorial (PubMed), editorial (OpenAlex) | `editorial` | |
| Clinical Trial (PubMed) | `clinical-trial` | PubMed-only |
| Meta-Analysis (PubMed) | `meta-analysis` | PubMed-only |
| Case Reports (PubMed) | `case-reports` | PubMed-only |
| Comparative Study (PubMed) | `comparative-study` | PubMed-only |
| Evaluation Study (PubMed) | `evaluation-study` | PubMed-only |
| book-chapter (CrossRef/OpenAlex) | `book-chapter` | |
| proceedings-article (CrossRef) | `proceedings-article` | CrossRef-only |
| posted-content (CrossRef) | `posted-content` | CrossRef-only |
| report (CrossRef) | `report` | CrossRef-only |
| standard (CrossRef) | `standard` | CrossRef-only |
| dissertation (OpenAlex) | `dissertation` | OpenAlex-only |
| preprint (OpenAlex) | `preprint` | |
| other (OpenAlex) | `other` | |

**Plan**:

1. Define a canonical enum `PublicationType` in `domain/types.py` with **kebab-case lowercase** values (aligns with CrossRef/OpenAlex convention, most widely used).
2. Create a mapping table `PUBLICATION_TYPE_MAPPING: dict[str, str]` in `domain/mapping/publication_type_mapping.py` with provider-specific -> canonical mapping.
3. Apply normalization in `BasePublicationTransformer._normalize_publication_type()` (template method hook) so all Silver records use canonical values.
4. Unify DQ field name to `publication_type` (already done in Silver schemas; update DQ configs: rename `doc_type` -> `publication_type` in ChEMBL DQ, `pub_type` -> `publication_type` in PubMed DQ, `type` -> `publication_type` in CrossRef/OpenAlex DQ).
5. Unify DQ enum to use canonical values across all providers.
6. Keep provider-specific values in a `raw_publication_type` field for forensic retention if needed.

**Effort**: Medium. Requires DQ YAML updates + mapping table + transformer hook.

### 10.2 `publication_year` -- Layer Consistency

**Problem**: DQ allows 1500-2100 but Filter narrows to 1950-2050. This is architecturally correct (DQ = quality gate, Filter = business relevance gate), but the gap could cause confusion.

**Plan**:

1. **Keep current layered approach** -- it is correct by design:
   - DQ (1500-2100): catches clearly invalid years; preserves historical publications in Silver
   - Filter (1950-2050): selects relevant publications for Gold analysis
2. **Document explicitly** in DQ YAML comments that DQ range is intentionally broader than Filter range.
3. **Add DQ warn rule** for `publication_year < 1950` across all providers (currently only error for out-of-range). This provides a signal that the record will be filtered at Gold stage.
4. **Verify ChEMBL Gold contract** is created (currently missing) with the same 1500-2100 range.

**Effort**: Low. Documentation + optional warn rule.

### 10.3 `title` -- Nullability Harmonization

**Problem**: PubMed enforces non-nullable title at Pandera Silver, others don't. All Filter configs require title.

**Plan**:

1. **Option A (Recommended)**: Keep PubMed's stricter validation. PubMed API always returns titles; nullable=False is correct for PubMed. Other APIs may return records without titles (e.g., retracted/removed content), so nullable=True is appropriate.
2. **Add DQ warn rule** `title_missing` with `severity: warn` to all providers where title is nullable in Silver. This flags title-less records for investigation without hard-failing.
3. **Ensure Filter `required_fields`** catches title-less records before Gold (already done).

**Effort**: Low. Add warn rules to 4 DQ YAMLs.

### 10.4 `pmid` -- Cross-Provider Value Object Usage

**Problem**: PubMed uses `PubMedId` Value Object for normalization, other providers rely only on Pandera regex.

**Plan**:

1. **Apply `PubMedId.from_raw()`** in all transformers that extract `pmid` from API responses (ChEMBL, OpenAlex, Semantic Scholar). This ensures consistent stripping of leading zeros, int->str coercion, and upper-bound validation.
2. **Remove DQ `range` rule** for pmid where it duplicates Value Object validation (or keep for defense-in-depth and document the overlap).
3. **CrossRef**: No action needed -- CrossRef API doesn't return PMIDs.

**Effort**: Low. Add VO call in 3 transformers.

### 10.5 `doi` -- Value Object Normalization Consistency

**Problem**: ChEMBL transformer uses `DOI.from_raw()` for normalization (strips URL prefix, lowercase), others use only Pandera regex which doesn't strip prefixes.

**Plan**:

1. **Apply `DOI.from_raw()`** in all transformers that handle DOI values (PubMed, OpenAlex, Semantic Scholar). CrossRef already normalizes DOI as PK.
2. This ensures consistent lowercase normalization and URL prefix stripping across all providers.
3. **Add integration test** verifying that `doi` values across all providers are normalized identically (lowercase, no URL prefix).

**Effort**: Low. Add VO call in 3 transformers + test.

### 10.6 `citations_received` / `citations_made` -- DQ Rule Coverage

**Problem**: ChEMBL and PubMed have no DQ rules for citation fields (APIs don't provide them natively). Pandera base schema has `ge=0` but no DQ rules for these providers.

**Plan**:

1. **Add DQ rules** for `citations_received` and `citations_made` to ChEMBL and PubMed DQ configs with `nullable: true` and `range >= 0`. Even though the APIs don't currently return citation data, enrichment pipelines may add it later.
2. **Add the 10M warn threshold** for consistency with CrossRef/OpenAlex/S2.
3. **Alternative**: If the fields are guaranteed absent, add a comment in DQ YAML explaining why no rule exists.

**Effort**: Low. Add DQ rules or documenting comments.

### 10.7 `publication_identifiable` -- Cross-Field Logic Harmonization

**Problem**: ChEMBL uses `any_present(pmid, doi, title)` while all others use `all_present(pk, title)`.

**Plan**:

1. **Recommended**: Change ChEMBL to `all_present(document_chembl_id, title)` for consistency. The ChEMBL PK (`document_chembl_id`) is always present (nullable=false), so the real gate is `title`.
2. **Keep** ChEMBL's secondary rule for `any_present(pmid, doi, title)` but rename it to `has_cross_reference` to align with PubMed's `has_identifier` pattern.
3. **Result**: All providers use same pattern:
   - `publication_identifiable`: `all_present(pk, title)` -- ensures linkability
   - Optional `has_cross_reference`: `any_present(external IDs)` -- for enrichment potential

**Effort**: Low. Update ChEMBL DQ YAML.

### 10.8 `Semantic Scholar` -- Missing Publication Type DQ

**Problem**: Semantic Scholar has no DQ validation for publication type, while all other providers do.

**Plan**:

1. **Add DQ enum rule** for Semantic Scholar `publication_type` field.
2. **Map S2 values** (JournalArticle, Conference, Review, etc.) to canonical kebab-case values per plan 10.1.
3. **Alternatively**: If S2 uses a pipe-delimited string for `publication_type`, add a pattern rule instead of enum.

**Effort**: Low. Add DQ rule to S2 YAML.

---

## Summary of Prioritized Actions

| # | Action | Fields Affected | Effort | Priority |
|---|--------|----------------|--------|----------|
| 1 | Unify `publication_type` enum + DQ field names | publication_type, doc_type, pub_type, type | Medium | **High** -- blocks composite pipeline consistency |
| 2 | Apply `DOI.from_raw()` in all transformers | doi | Low | **High** -- data quality consistency |
| 3 | Apply `PubMedId.from_raw()` in all transformers | pmid | Low | **High** -- data quality consistency |
| 4 | Harmonize `publication_identifiable` cross-field rule | cross-field | Low | **Medium** -- DQ logic consistency |
| 5 | Add citation DQ rules to ChEMBL/PubMed | citations_received, citations_made | Low | **Medium** -- defense-in-depth |
| 6 | Add S2 publication_type DQ rule | publication_type | Low | **Medium** -- gap remediation |
| 7 | Add `title_missing` warn rule | title | Low | **Low** -- informational |
| 8 | Add `publication_year < 1950` DQ warn | publication_year | Low | **Low** -- informational |
| 9 | Create ChEMBL Gold contract schema | all ChEMBL fields | Medium | **Low** -- completeness |
