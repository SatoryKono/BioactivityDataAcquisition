# Publication Validation Matrix

*Version: 1.0.0 | Date: 2026-02-09*

Cross-pipeline analysis of validation rules for all publication entities in BioETL.
Covers 5 provider pipelines: **ChEMBL**, **PubMed**, **OpenAlex**, **SemanticScholar**, **CrossRef**.

Validation is applied at three layers:
1. **Schema (Pandera)** — structural type/nullability/pattern checks on Silver DataFrames
2. **DQ (configs/dq)** — configurable field-level and cross-field rules
3. **Filter (configs/filter)** — Gold-layer inclusion/exclusion criteria

---

## Table of Contents

1. [Common Fields Validation Matrix](#1-common-fields-validation-matrix)
2. [Provider-Specific Fields](#2-provider-specific-fields)
3. [Cross-Field Validations](#3-cross-field-validations)
4. [Gold Filter Rules](#4-gold-filter-rules)
5. [Divergence Analysis](#5-divergence-analysis)
6. [Unification Plans](#6-unification-plans)

---

## 1. Common Fields Validation Matrix

Fields inherited from `PublicationBaseSchema` with per-provider overrides.

### 1.1 Identifiers

| Field | Base | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|-------|------|--------|--------|----------|-----------------|----------|
| **pmid** | `str`, nullable, regex `^[1-9]\d*$` | inherited | **non-nullable** (PK), extra check `pmid_positive` via `@pa.check` | inherited | inherited | inherited |
| **doi** | `str`, nullable, regex `^10\.\d{4,}/.+$` | inherited | inherited | inherited | inherited | **non-nullable** (PK), same regex |
| **pmc_id** | `str`, nullable, regex `^PMC\d+$` | inherited | inherited + extra `@pa.check pmc_id_format` | inherited | inherited | inherited |

### 1.2 Core Content

| Field | Base | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|-------|------|--------|--------|----------|-----------------|----------|
| **title** | `str`, nullable | inherited | **non-nullable** + `@pa.check title_not_empty` (len >= 1) | inherited | inherited | inherited |
| **abstract** | `str`, nullable | inherited | inherited | inherited | inherited | inherited |
| **authors** | `str`, nullable, JSON array | inherited | inherited | inherited | inherited | inherited |
| **affiliation_list** | `str`, nullable, JSON array | inherited | inherited | inherited | inherited | inherited |
| **author_orcids** | `str`, nullable, JSON + ORCID regex via `@pa.check` | inherited | inherited | inherited | inherited | inherited |

### 1.3 Publication Metadata

| Field | Base | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|-------|------|--------|--------|----------|-----------------|----------|
| **publication_year** | `Int64`, nullable, ge=1500, le=2100 | inherited | inherited | inherited | inherited | inherited |
| **publication_date** | `str`, nullable, regex `^\d{4}-\d{2}-\d{2}$` | inherited | inherited | inherited | inherited | inherited |
| **publication_type** | `str`, nullable | `isin` PUBLICATION_TYPES (`PUBLICATION`, `PATENT`, `DATASET`, `BOOK`) | inherited (nullable) | nullable, free text (article, book, etc.) | nullable, pipe-delimited string | nullable, free text (journal-article, book, etc.) |
| **journal** | `str`, nullable | inherited | inherited | inherited | inherited | inherited |
| **language** | `str`, nullable, len 2..3 | inherited | nullable, no length constraint (MARC code) | inherited | inherited | inherited |

### 1.4 Pagination

| Field | Base | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|-------|------|--------|--------|----------|-----------------|----------|
| **page_first** | `str`, nullable | re-declared, nullable | inherited | inherited | inherited | inherited |
| **page_last** | `str`, nullable | re-declared, nullable | inherited | inherited | inherited | inherited |

### 1.5 Metrics

| Field | Base | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|-------|------|--------|--------|----------|-----------------|----------|
| **citations_received** | `Int64`, nullable, ge=0 | inherited | inherited | inherited | inherited | inherited |
| **citations_made** | `Int64`, nullable, ge=0 | inherited | inherited | inherited | inherited | inherited |
| **is_oa** | `bool`, nullable | inherited | inherited | inherited | inherited | inherited |

### 1.6 Lookup Tracking & System

| Field | Base | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|-------|------|--------|--------|----------|-----------------|----------|
| **_lookup_method** | `str`, **non-nullable**, `isin` LOOKUP_METHODS | re-declared, non-nullable, same `isin` | inherited | re-declared, non-nullable, same `isin` | re-declared, non-nullable, same `isin` | inherited |
| **_original_id** | `str`, nullable | inherited | inherited | inherited | inherited | inherited |
| **_source** | `str`, nullable | **non-nullable**, `eq="chembl"` | **non-nullable**, `eq="pubmed"` | **non-nullable**, `eq="openalex"` | **non-nullable**, `eq="semanticscholar"` | **non-nullable**, `eq="crossref"` |

---

## 2. Provider-Specific Fields

### 2.1 ChEMBL-Only Fields

| Field | Type | Nullable | Validation |
|-------|------|----------|------------|
| `document_chembl_id` | `str` | **false** (PK) | regex `^CHEMBL\d+$` |
| `src_id` | `Int64` | true | none |
| `chembl_release` | `str` | true | none |
| `creation_date` | `str` | true | regex `^\d{4}-\d{2}-\d{2}$` |
| `volume` | `str` | true | none |
| `issue` | `str` | true | none |
| `_dq_warn` | `Boolean` | true | default=False |
| `_dq_error` | `Boolean` | true | default=False |

### 2.2 PubMed-Only Fields

| Field | Type | Nullable | Validation |
|-------|------|----------|------------|
| `pii` | `str` | true | none |
| `mid` | `str` | true | none |
| `publisher_id` | `str` | true | none |
| `abstract_structured` | `bool` | true | none |
| `journal_name_short` | `str` | true | none |
| `journal_iso_abbrev` | `str` | true | none |
| `issn` | `str` | true | regex `^\d{4}-\d{3}[\dX]$` |
| `journal_issn_type` | `str` | true | `@pa.check` isin `[Print, Electronic, Linking]` |
| `nlm_unique_id` | `str` | true | none |
| `country` | `str` | true | none |
| `medline_pgn` | `str` | true | none |
| `page_range` | `str` | true | none |
| `pub_month` | `Int64` | true | `@pa.check` range 1..12 |
| `pub_day` | `Int64` | true | `@pa.check` range 1..31 |
| `publication_status` | `str` | true | `@pa.check` isin `[ppublish, epublish, aheadofprint]` |
| `publication_type_list` | `str` | true | JSON array |
| `date_completed` | `datetime` | true | none |
| `date_revised` | `datetime` | true | none |
| `citation_subset` | `str` | true | none |
| `affiliation_structured` | `str` | true | JSON array of objects |
| `author_count` | `Int64` | true | `@pa.check` ge=0 |
| `mesh_heading_count` | `Int64` | true | `@pa.check` ge=0 |
| `keyword_count` | `Int64` | true | `@pa.check` ge=0 |
| `grant_count` | `Int64` | true | `@pa.check` ge=0 |
| `chemical_count` | `Int64` | true | `@pa.check` ge=0 |
| `subject_mesh` | `str` | true | JSON array |
| `chemicals` | `str` | true | JSON array |
| `subject_keywords` | `str` | true | JSON array |
| `databanks` | `str` | true | JSON array |
| `gene_symbols` | `str` | true | JSON array |
| `publication_types` | `str` | true | JSON array |
| `authors_with_affiliations` | `str` | true | JSON array |

### 2.3 OpenAlex-Only Fields

| Field | Type | Nullable | Validation |
|-------|------|----------|------------|
| `openalex_id` | `str` | **false** (PK) | regex `^W\d+$` |
| `issn` | `str` | true | regex `^\d{4}-\d{3}[\dX]$` (ISSN-L) |
| `publisher` | `str` | true | none |
| `oa_status` | `str` | true | isin `[gold, green, hybrid, bronze, closed]` |
| `volume` | `str` | true | none |
| `issue` | `str` | true | none |
| `fwci` | `float` | true | ge=0 |
| `is_retracted` | `bool` | **false** | none |
| `subject_topics` | `str` | true | JSON array |
| `primary_topic` | `str` | true | JSON object |
| `grants` | `str` | true | JSON array |
| `subject_mesh` | `str` | true | JSON array |
| `subject_keywords` | `str` | true | JSON array |
| `mag_id` | `str` | true | none |
| `author_openalex_ids` | `str` | true | JSON array |
| `institution_ids` | `str` | true | JSON array |
| `institution_country_codes` | `str` | true | JSON array |
| `ror_ids` | `str` | true | JSON array |

### 2.4 SemanticScholar-Only Fields

| Field | Type | Nullable | Validation |
|-------|------|----------|------------|
| `paper_id` | `str` | **false** (PK) | regex `^[a-f0-9]{40}$` |
| `dblp_id` | `str` | true | none |
| `corpus_id` | `Int64` | true | ge=0 |
| `tldr` | `str` | true | none |
| `volume` | `str` | true | none |
| `page_range` | `str` | true | none |
| `influential_citation_count` | `Int64` | true | ge=0 |
| `open_access_url` | `str` | true | none |
| `oa_status` | `str` | true | isin `[gold, green, hybrid, bronze, closed]` |
| `subject_fields` | `str` | true | JSON array |
| `publication_type` | `str` | true | pipe-delimited string |
| `publication_types` | `str` | true | JSON array |
| `author_s2_ids` | `str` | true | JSON array |
| `author_h_indices` | `str` | true | JSON array |
| `citation_contexts` | `str` | true | JSON array |

### 2.5 CrossRef-Only Fields

| Field | Type | Nullable | Validation |
|-------|------|----------|------------|
| `issn` | `str` | true | regex `^\d{4}-\d{3}[\dX]$` |
| `issn_list` | `str` | true | JSON array |
| `issn_print` | `str` | true | regex `^\d{4}-\d{3}[\dX]$` |
| `issn_electronic` | `str` | true | regex `^\d{4}-\d{3}[\dX]$` |
| `publisher` | `str` | true | none |
| `published_print` | `str` | true | ISO date |
| `published_online` | `str` | true | ISO date |
| `license_url` | `str` | true | none |
| `subject_keywords` | `str` | true | JSON array |
| `content_domain_domains` | `object` | true | none |
| `content_domain_crossmark_restriction` | `bool` | true | coerce=True |
| `alternative_id` | `object` | true | none |
| `published` | `str` | true | canonical date YYYY-MM-DD |
| `journal_name_short` | `str` | true | none |
| `author_details` | `str` | true | JSON array |
| `references` | `str` | true | JSON array |

---

## 3. Cross-Field Validations

| Rule | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|------|--------|--------|----------|-----------------|----------|
| **publication_identifiable** | `any_present(pmid, doi, title)` | `all_present(pmid, title)` | `all_present(openalex_id, title)` | `all_present(paper_id, title)` | `all_present(doi, title)` |
| **has_identifier** | -- | `any_present(pmid, doi, pmc_id)` | -- | -- | -- |
| **retracted_warning** | -- | -- | `is_retracted == true` (severity: warn) | -- | -- |

---

## 4. Gold Filter Rules

| Criterion | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|-----------|--------|--------|----------|-----------------|----------|
| **Required fields** | `document_chembl_id`, `doc_type`, `title` | `pmid`, `title` | `openalex_id`, `title` | `paper_id`, `title` | `doi`, `title` |
| **Column value filter** | `doc_type=[PUBLICATION]` | -- | -- | -- | -- |
| **Year range** | `year > 1950` | -- | `1500..2100` | `1500..2100` | `1500..2100` |

---

## 5. Divergence Analysis

Fields with the **same semantic name** but **different validation** across pipelines.

### 5.1 `publication_year`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|--------|--------|--------|----------|-----------------|----------|
| **Schema type** | `Int64` | `Int64` | `Int64` | `Int64` | `Int64` |
| **Schema nullable** | true | true | true | true | true |
| **Schema range** | 1500..2100 | 1500..2100 | 1500..2100 | 1500..2100 | 1500..2100 |
| **DQ field name** | `year` | `pub_year` | `year` | `year` | `year` |
| **DQ range** | 1500..2100 | 1500..2100 | 1500..2100 | 1500..2100 | 1500..2100 |
| **Gold filter** | `year > 1950` | -- | `1500..2100` | `1500..2100` | `1500..2100` |

**Divergence:** DQ config uses **different field names** (`year` vs `pub_year`). Gold filter applies a **narrower range** for ChEMBL (`> 1950`) compared to other pipelines (`1500..2100`). Three pipelines (OpenAlex, S2, CrossRef) specify Gold year range explicitly; PubMed has no Gold year filter.

### 5.2 `publication_type`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|--------|--------|--------|----------|-----------------|----------|
| **Schema validation** | `isin` [PUBLICATION, PATENT, DATASET, BOOK] | nullable, no enum | nullable, free text | nullable, pipe-delimited | nullable, free text |
| **DQ field name** | `doc_type` | `pub_type` | `type` | -- | `type` |
| **DQ enum values** | PUBLICATION, BOOK, DATASET, PATENT | Journal Article, Review, Letter, Editorial, Clinical Trial, Meta-Analysis, Case Reports, Comparative Study, Evaluation Study | article, book-chapter, book, dataset, dissertation, editorial, letter, review, preprint, other | -- | journal-article, book-chapter, proceedings-article, posted-content, book, report, dataset, standard |

**Divergence:** Field name in DQ varies (`doc_type`, `pub_type`, `type`). Enum vocabularies are completely different per provider. ChEMBL uses uppercase normalized types; PubMed uses NLM vocabulary; OpenAlex uses its own lowercase taxonomy; CrossRef uses hyphenated CrossRef types. SemanticScholar has no DQ enum validation.

### 5.3 `title`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|--------|--------|--------|----------|-----------------|----------|
| **Schema nullable** | true | **false** | true | true | true |
| **Schema extra check** | -- | `title_not_empty` (len >= 1) | -- | -- | -- |
| **DQ validation** | max_length 2000 | pattern `.{1,2000}` | pattern `.{1,2000}` | pattern `.{1,2000}` | pattern `.{1,2000}` |
| **DQ nullable** | true | true | true | true | true |
| **Gold required** | yes | yes | yes | yes | yes |

**Divergence:** Only PubMed makes `title` non-nullable at schema level with an explicit `title_not_empty` check. ChEMBL uses `max_length` type in DQ while others use `pattern` type with equivalent effect. All pipelines require `title` at Gold level, but only PubMed enforces it at Schema level.

### 5.4 `pmid`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|--------|--------|--------|----------|-----------------|----------|
| **Schema type** | `str` | `str` | `str` | `str` | `str` |
| **Schema nullable** | true | **false** (PK) | true | true | true |
| **Schema regex** | `^[1-9]\d*$` (from base) | none (explicit `@pa.check` instead) | `^[1-9]\d*$` (from base) | `^[1-9]\d*$` (from base) | `^[1-9]\d*$` (from base) |
| **Schema extra check** | -- | `pmid_positive` `@pa.check` (`^[1-9]\d*$`) | -- | -- | -- |
| **DQ validation** | range 1..100000000 | range 1..100000000 | -- | -- | -- |

**Divergence:** PubMed makes `pmid` non-nullable (it's the PK) and adds redundant `@pa.check` for positive validation. ChEMBL and PubMed apply DQ range validation (1..100M); other pipelines have no DQ rule for `pmid`. Base schema applies regex for all.

### 5.5 `doi`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|--------|--------|--------|----------|-----------------|----------|
| **Schema nullable** | true | true | true | true | **false** (PK) |
| **Schema regex** | `^10\.\d{4,}/.+$` (from base) | `^10\.\d{4,}/.+$` (re-declared) | `^10\.\d{4,}/.+$` (from base) | `^10\.\d{4,}/.+$` (from base) | `^10\.\d{4,}/.+$` (re-declared) |
| **DQ validation** | pattern `^10\.\d{4,}/.+$` | pattern `^10\.\d{4,}/.+$` | pattern `^10\.\d{4,}/.+$` | pattern `^10\.\d{4,}/.+$` | pattern `^10\.\d{4,}/.+$`, **non-nullable** |

**Divergence:** Only CrossRef makes `doi` non-nullable (it's the PK). Regex pattern is identical across all. PubMed and CrossRef re-declare the field explicitly. DQ validation is consistent.

### 5.6 `_source`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|--------|--------|--------|----------|-----------------|----------|
| **Schema nullable** | **false** | **false** | **false** | **false** | **false** |
| **Schema eq value** | `"chembl"` | `"pubmed"` | `"openalex"` | `"semanticscholar"` | `"crossref"` |

**Divergence:** None -- each provider correctly pins its own source identifier. This is by design.

### 5.7 `_lookup_method`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|--------|--------|--------|----------|-----------------|----------|
| **Schema nullable** | false | false (from base) | false | false | false (from base) |
| **Schema isin** | LOOKUP_METHODS | LOOKUP_METHODS | LOOKUP_METHODS | LOOKUP_METHODS | LOOKUP_METHODS |
| **Re-declared** | yes | no | yes | yes | no |

**Divergence:** Minor -- ChEMBL, OpenAlex, S2 redundantly re-declare with identical values. PubMed and CrossRef rely on base. No functional difference.

### 5.8 `publication_identifiable` (cross-field)

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|--------|--------|--------|----------|-----------------|----------|
| **Condition** | `any_present(pmid, doi, title)` | `all_present(pmid, title)` | `all_present(openalex_id, title)` | `all_present(paper_id, title)` | `all_present(doi, title)` |
| **Strictness** | Lenient (any 1 of 3) | Strict (both required) | Strict (both required) | Strict (both required) | Strict (both required) |

**Divergence:** ChEMBL uses `any_present` (lenient -- a publication with only a DOI passes), while all other providers use `all_present` (strict -- both PK and title required). This is a significant semantic difference.

### 5.9 `issn`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|--------|--------|--------|----------|-----------------|----------|
| **Present** | no | yes | yes | no | yes |
| **Schema regex** | -- | `^\d{4}-\d{3}[\dX]$` | `^\d{4}-\d{3}[\dX]$` | -- | `^\d{4}-\d{3}[\dX]$` |

**Divergence:** None where present -- identical regex. ChEMBL and S2 don't have this field.

### 5.10 `oa_status`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|--------|--------|--------|----------|-----------------|----------|
| **Present** | no | no | yes | yes | no |
| **Schema isin** | -- | -- | `[gold, green, hybrid, bronze, closed]` | `[gold, green, hybrid, bronze, closed]` | -- |

**Divergence:** None where present -- identical OA_STATUS_VALUES enum.

### 5.11 `language`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|--------|--------|--------|----------|-----------------|----------|
| **Schema type** | `str` (from base) | `str` (re-declared, no length) | `str` (from base) | `str` (from base) | `str` (from base) |
| **Schema length** | 2..3 (from base) | **no length constraint** | 2..3 (from base) | 2..3 (from base) | 2..3 (from base) |

**Divergence:** PubMed re-declares `language` without the base `str_length(2..3)` constraint. PubMed uses MARC codes (typically 3-letter like `eng`) which fit within the base constraint anyway, but the explicit length validation is lost.

### 5.12 `subject_keywords`

| Aspect | PubMed | OpenAlex | CrossRef |
|--------|--------|----------|----------|
| **Present** | yes | yes | yes |
| **Type** | `str`, nullable | `str`, nullable | `str`, nullable |
| **Description** | Author keywords (JSON array) | Keywords (JSON array) | JSON array of subject areas |
| **Semantic meaning** | Author-assigned keywords | Extracted keywords | CrossRef subject categories |

**Divergence:** Same field name, same type, but **semantically different sources** (author keywords vs extracted vs publisher-assigned subjects). No structural validation difference.

### 5.13 `subject_mesh`

| Aspect | PubMed | OpenAlex |
|--------|--------|----------|
| **Present** | yes | yes |
| **Type** | `str`, nullable | `str`, nullable |
| **Description** | MeSH descriptor/qualifier strings | MeSH descriptor names |

**Divergence:** PubMed includes qualifiers in the JSON entries; OpenAlex only has descriptor names. No structural validation difference.

### 5.14 `volume`

| Aspect | ChEMBL | OpenAlex | SemanticScholar |
|--------|--------|----------|-----------------|
| **Present** | yes | yes | yes |
| **Type** | `str`, nullable | `str`, nullable | `str`, nullable |
| **Validation** | none | none | none |

**Divergence:** None -- consistent across all providers that include this field.

### 5.15 `page_range`

| Aspect | PubMed | SemanticScholar |
|--------|--------|-----------------|
| **Present** | yes | yes |
| **Type** | `str`, nullable | `str`, nullable |
| **Description** | Page numbers (unified) | Page range (legacy format, e.g. '123-456') |

**Divergence:** None structurally; PubMed and S2 both store page range as free-text string.

### 5.16 `journal_name_short`

| Aspect | PubMed | CrossRef |
|--------|--------|----------|
| **Present** | yes | yes |
| **Type** | `str`, nullable | `str`, nullable |
| **Validation** | none | none |

**Divergence:** None -- consistent.

### 5.17 `publisher`

| Aspect | OpenAlex | CrossRef |
|--------|----------|----------|
| **Present** | yes | yes |
| **Type** | `str`, nullable | `str`, nullable |
| **Validation** | none | none |

**Divergence:** None -- consistent.

### 5.18 `publication_types` (JSON array)

| Aspect | PubMed | SemanticScholar |
|--------|--------|-----------------|
| **Present** | yes | yes |
| **Type** | `str`, nullable | `str`, nullable |
| **Content** | NLM publication types (Journal Article, Review...) | S2 publication types |

**Divergence:** Same field name but different vocabularies. No structural validation.

---

## 6. Unification Plans

For each divergent field, a recommended plan to harmonize validation across pipelines.

### 6.1 `publication_year` -- Field Name & Gold Range Unification

**Problem:**
- DQ configs use inconsistent field names: `year` (ChEMBL, OpenAlex, S2, CrossRef) vs `pub_year` (PubMed)
- Gold filter range differs: ChEMBL `> 1950`, others `1500..2100` or none

**Plan:**

| Step | Action | Files |
|------|--------|-------|
| 1 | Rename DQ field to unified `publication_year` across all configs | `configs/dq/entities/*/publication.yaml` |
| 2 | Align Gold filter range to a common policy: `1500..2100` for schema, `> 1800` for Gold (scientific journals era) | `configs/filter/entities/*/publication.yaml` |
| 3 | Add Gold year filter to PubMed (currently missing) | `configs/filter/entities/pubmed/publication.yaml` |
| 4 | Document the decision: schema allows 1500..2100 (historical), Gold narrows to 1800+ (practical cutoff) | ADR |

**Rationale:** PubMed has publications from the 1800s; ChEMBL's `> 1950` is too restrictive for other providers. A unified `> 1800` Gold filter with `1500..2100` schema range covers all realistic use cases.

---

### 6.2 `publication_type` -- Vocabulary Normalization

**Problem:**
- DQ configs use different field names: `doc_type`, `pub_type`, `type`
- Enum vocabularies are provider-specific and incompatible
- SemanticScholar has no DQ enum validation at all

**Plan:**

| Step | Action | Files |
|------|--------|-------|
| 1 | Rename DQ field to unified `publication_type` across all configs | `configs/dq/entities/*/publication.yaml` |
| 2 | Define a **canonical type mapping** in domain layer: provider-raw -> normalized | `src/bioetl/domain/mapping/publication_type_mapping.py` (new) |
| 3 | Transformer normalizes to canonical set: `JOURNAL_ARTICLE`, `REVIEW`, `BOOK`, `BOOK_CHAPTER`, `PREPRINT`, `DATASET`, `PATENT`, `PROCEEDINGS`, `EDITORIAL`, `LETTER`, `OTHER` | Each provider transformer |
| 4 | Add DQ enum validation for SemanticScholar using canonical types | `configs/dq/entities/semanticscholar/publication.yaml` |
| 5 | Keep raw provider type in a separate field `_raw_publication_type` for provenance | Schema updates |

**Rationale:** Cross-provider analysis requires a common taxonomy. The canonical mapping preserves original values while enabling unified queries. Each transformer applies the mapping during the Bronze->Silver transformation.

---

### 6.3 `title` -- Nullable Consistency

**Problem:**
- Only PubMed enforces `title` as non-nullable at schema level
- All other providers allow nullable title, relying on Gold filter for enforcement
- ChEMBL uses `max_length` DQ type while others use `pattern` type with equivalent semantics

**Plan:**

| Step | Action | Files |
|------|--------|-------|
| 1 | Keep `title` nullable in base schema (some records legitimately lack titles in raw data) | No change to base |
| 2 | Standardize DQ validation to `max_length: 2000` across all providers (clearer intent than regex) | `configs/dq/entities/*/publication.yaml` |
| 3 | Enforce title presence uniformly via Gold filter `required_fields` (already done) | Verify all configs |
| 4 | Consider adding `title_not_empty` `@pa.check` to base schema (lift PubMed's check up) | `publication_base.py` -- optional |

**Rationale:** Title should be nullable at Silver level (raw data may lack it) but required at Gold level (already enforced everywhere). Making the DQ rule type consistent (`max_length` vs `pattern`) improves maintainability.

---

### 6.4 `pmid` -- DQ Coverage Gap

**Problem:**
- Only ChEMBL and PubMed have DQ range validation for `pmid` (1..100M)
- OpenAlex, S2, CrossRef have no DQ rule for `pmid` even though they may have it
- Base schema provides regex validation (`^[1-9]\d*$`) which partially covers this

**Plan:**

| Step | Action | Files |
|------|--------|-------|
| 1 | Add `pmid` DQ range rule (1..100000000) to OpenAlex, S2, CrossRef configs | `configs/dq/entities/{openalex,semanticscholar,crossref}/publication.yaml` |
| 2 | Remove redundant PubMed `@pa.check pmid_positive` (already covered by base regex) | `src/bioetl/domain/schemas/pubmed/publication.py` |
| 3 | Consider moving DQ pmid range to `_defaults.yaml` as a shared rule | `configs/dq/_defaults.yaml` |

**Rationale:** The base schema regex and DQ range validation should be consistent. If a provider returns a PMID, it should pass the same validation regardless of source.

---

### 6.5 `publication_identifiable` -- Cross-Field Rule Alignment

**Problem:**
- ChEMBL uses `any_present(pmid, doi, title)` -- lenient, a record with only a DOI is valid
- All other providers use `all_present(PK, title)` -- strict, both fields required
- Semantics are fundamentally different: ChEMBL checks identifiability, others check completeness

**Plan:**

| Step | Action | Files |
|------|--------|-------|
| 1 | Separate the two concerns: **identifiability** vs **completeness** | All DQ configs |
| 2 | Add `publication_identifiable` (`any_present(pmid, doi, title)`) to ALL providers as a soft check (warn) | `configs/dq/entities/*/publication.yaml` |
| 3 | Keep `record_complete` (`all_present(PK, title)`) as a hard check (error) per provider | `configs/dq/entities/*/publication.yaml` |
| 4 | Rename ChEMBL's existing rule to clarify it's the identifiability check | `configs/dq/entities/chembl/publication.yaml` |

**Rationale:** These are two different invariants. Every pipeline should check both: (a) is the publication identifiable by at least one external ID? and (b) does it have the minimum required fields for this provider? Splitting them improves debuggability and DQ reporting.

---

### 6.6 `language` -- Length Constraint Restoration

**Problem:**
- Base schema applies `str_length(2..3)` for ISO 639-1 (2-letter) or MARC (3-letter) codes
- PubMed re-declares `language` without this constraint, losing the validation

**Plan:**

| Step | Action | Files |
|------|--------|-------|
| 1 | Remove the PubMed-specific re-declaration of `language` and rely on base | `src/bioetl/domain/schemas/pubmed/publication.py` |
| 2 | Verify PubMed MARC codes all fit within 2..3 characters | Data audit |
| 3 | If any PubMed codes exceed 3 chars, extend base to `str_length(2..5)` | `publication_base.py` |

**Rationale:** PubMed MARC codes (e.g., `eng`, `fre`, `ger`) are 3-letter codes that fit the base constraint. The re-declaration is unnecessary and loses validation.

---

### 6.7 `_lookup_method` -- Redundant Re-declaration Cleanup

**Problem:**
- ChEMBL, OpenAlex, SemanticScholar redundantly re-declare `_lookup_method` with identical values
- PubMed and CrossRef correctly rely on base

**Plan:**

| Step | Action | Files |
|------|--------|-------|
| 1 | Remove redundant re-declarations from ChEMBL, OpenAlex, S2 schemas | Provider schema files |
| 2 | Keep only if the description text adds meaningful provider-specific context | Review descriptions |

**Rationale:** DRY principle. The base already defines `_lookup_method` as non-nullable with the full `LOOKUP_METHODS` isin check. Re-declaring without changes adds maintenance burden.

---

### Summary: Priority Matrix

| Field | Severity | Effort | Priority |
|-------|----------|--------|----------|
| `publication_type` vocabulary | HIGH -- blocks cross-provider analysis | HIGH -- requires mapping + transformer changes | **P1** |
| `publication_identifiable` semantics | HIGH -- inconsistent DQ behavior | MEDIUM -- DQ config changes only | **P1** |
| `publication_year` field naming | MEDIUM -- DQ field mismatch | LOW -- config rename | **P2** |
| `publication_year` Gold range | MEDIUM -- inconsistent filtering | LOW -- config change | **P2** |
| `title` DQ type consistency | LOW -- functionally equivalent | LOW -- config update | **P3** |
| `pmid` DQ coverage gap | LOW -- base schema covers regex | LOW -- add DQ rules | **P3** |
| `language` constraint loss | LOW -- PubMed values fit anyway | LOW -- remove re-declaration | **P3** |
| `_lookup_method` redundancy | INFO -- no functional impact | LOW -- remove re-declarations | **P4** |

---

*Generated from source code analysis of `src/bioetl/domain/schemas/`, `configs/dq/entities/`, and `configs/filter/entities/`.*
