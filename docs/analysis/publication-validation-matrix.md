# Publication Validation Matrix

*Generated: 2026-02-09 | Codebase: BioETL*

Cross-provider analysis of data validation rules for `publication` entity pipelines.

**Pipelines analysed:** ChEMBL, PubMed, OpenAlex, SemanticScholar, CrossRef

**Validation layers:**
- **Schema** — Pandera schema checks (Silver layer)
- **DQ** — Data Quality YAML rules (Bronze->Silver boundary)
- **VO** — Domain Value Object validation (transformer layer)
- **Entity** — Domain entity dataclass constraints

---

## 1. Full Validation Matrix (fields x pipelines)

Legend:
- `N/N` = nullable / non-nullable
- `--` = field absent for this pipeline
- Inherits from `PublicationBaseSchema` unless noted as **override**

### 1.1 Primary Keys

| Field | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| `document_chembl_id` | **PK**, non-null, pattern `^CHEMBL\d+$` | -- | -- | -- | -- |
| `pmid` | nullable, str, regex `^[1-9]\d*$` (base); DQ range 1..100M | **PK**, non-null, str, check `^[1-9]\d*$`; DQ range 1..100M | nullable, str, regex `^[1-9]\d*$` (base) | nullable, str, regex `^[1-9]\d*$` (base) | -- |
| `openalex_id` | -- | -- | **PK**, non-null, pattern `^W\d+$` | -- | -- |
| `paper_id` | -- | -- | -- | **PK**, non-null, pattern `^[a-f0-9]{40}$` | -- |
| `doi` | nullable, regex `^10\.\d{4,}/.+$`; DQ pattern | nullable, regex `^10\.\d{4,}/.+$`; DQ pattern | nullable, regex `^10\.\d{4,}/.+$`; DQ pattern | nullable, regex `^10\.\d{4,}/.+$`; DQ pattern | **PK**, non-null, regex `^10\.\d{4,}/.+$`; DQ non-null pattern |

### 1.2 Core Content

| Field | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| `title` | nullable (base); DQ max_length 2000 | **non-null override**; DQ max_length 2000 | nullable (base); DQ max_length 2000 | nullable (base); DQ max_length 2000 | nullable (base); DQ max_length 2000 |
| `abstract` | nullable (base) | nullable (base) | nullable (base) | nullable (base) | nullable (base) |
| `authors` | nullable, str, JSON array (base) | nullable, str, JSON array (base) | nullable, str, JSON array (base) | nullable, str, JSON array (base) | nullable, str, JSON array (base) |
| `affiliation_list` | -- (excluded) | nullable (base) | nullable (base) | nullable (base) | nullable (base) |
| `author_orcids` | nullable, ORCID format check (base) | nullable, ORCID format check (base) | nullable, ORCID format check (base) | nullable, ORCID format check (base) | nullable, ORCID format check (base) |
| `abstract_structured` | -- | nullable, bool | -- | -- | -- |

### 1.3 Publication Metadata

| Field | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| `journal` | nullable (base) | nullable (override, same) | nullable (base) | nullable (base) | nullable (base) |
| `publication_year` | nullable, Int64, 1500..2100 (base); DQ range 1500..2100 | nullable, Int64, 1500..2100 (base); DQ range 1500..2100 | nullable, Int64, 1500..2100 (base); DQ range 1500..2100 | nullable, Int64, 1500..2100 (base); DQ range 1500..2100 | nullable, Int64, 1500..2100 (base); DQ range 1500..2100 |
| `publication_date` | -- (excluded; only year available) | nullable, str, regex `^\d{4}-\d{2}-\d{2}$` (base) | nullable, str, regex `^\d{4}-\d{2}-\d{2}$` (base) | nullable, str, regex `^\d{4}-\d{2}-\d{2}$` (base) | nullable, str, regex `^\d{4}-\d{2}-\d{2}$` (base) |
| `publication_type` | nullable, **enum** `{PUBLICATION, BOOK, DATASET, PATENT}` | nullable, str (base, no enum in schema); DQ enum `{Journal Article, Review, Letter, ...}` via `pub_type` | nullable, str (no enum in schema); DQ enum `{article, book-chapter, book, dataset, ...}` via `type` | nullable, str, pipe-delimited | nullable, str (no enum in schema); DQ enum `{journal-article, book-chapter, proceedings-article, ...}` via `type` |
| `language` | -- (excluded) | nullable, str (override, MARC code) | nullable, str, len 2..3 (base) | -- (excluded) | nullable, str, len 2..3 (base) |

### 1.4 Pagination

| Field | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| `page_first` | nullable, str | nullable (base) | nullable (base) | nullable (base) | nullable (base) |
| `page_last` | nullable, str | nullable (base) | nullable (base) | nullable (base) | nullable (base) |
| `page_range` | -- | nullable, str | -- | nullable, str | -- |
| `medline_pgn` | -- | nullable, str | -- | -- | -- |
| `volume` | nullable, str | -- | nullable, str | nullable, str | -- |
| `issue` | nullable, str | -- | nullable, str | -- | -- |

### 1.5 Metrics

| Field | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| `citations_received` | nullable, Int64, >= 0 (base) | -- (excluded) | nullable, Int64, >= 0 (base); DQ range >= 0 | nullable, Int64, >= 0 (base); DQ range >= 0 | nullable, Int64, >= 0 (base); DQ range >= 0 |
| `citations_made` | nullable, Int64, >= 0 (base) | nullable, Int64, >= 0 (base) | nullable, Int64, >= 0 (base); DQ `reference_count` >= 0 | nullable, Int64, >= 0 (base); DQ `reference_count` >= 0 | nullable, Int64, >= 0 (base) |
| `fwci` | -- | -- | nullable, float, >= 0; DQ range >= 0 | -- | -- |
| `influential_citation_count` | -- | -- | -- | nullable, Int64, >= 0; DQ range >= 0 | -- |

### 1.6 Open Access

| Field | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| `is_oa` | -- (excluded) | -- (excluded) | nullable, bool (base) | nullable, bool (base) | nullable, bool (base) |
| `oa_status` | -- (excluded) | -- (excluded) | nullable, enum `{gold, green, hybrid, bronze, closed}` | nullable, enum `{gold, green, hybrid, bronze, closed}` | -- |
| `open_access_url` | -- | -- | -- | nullable, str | -- |
| `license_url` | -- | -- | -- | -- | nullable, str |

### 1.7 Identifiers & Cross-references

| Field | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| `pmc_id` | -- (excluded) | nullable, regex `^PMC\d+$` (check) | nullable (base) | -- | -- |
| `pii` | -- | nullable, str | -- | -- | -- |
| `mid` | -- | nullable, str | -- | -- | -- |
| `publisher_id` | -- | nullable, str | -- | -- | -- |
| `dblp_id` | -- | -- | -- | nullable, str | -- |
| `corpus_id` | -- | -- | -- | nullable, Int64, >= 0 | -- |
| `mag_id` | -- | -- | nullable, str | -- | -- |
| `src_id` | nullable, Int64 | -- | -- | -- | -- |
| `alternative_id` | -- | -- | -- | -- | nullable, object |

### 1.8 Journal Details

| Field | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| `issn` | -- | nullable, regex `^\d{4}-\d{3}[\dX]$` | nullable, regex `^\d{4}-\d{3}[\dX]$` | -- | nullable, regex `^\d{4}-\d{3}[\dX]$` |
| `issn_list` | -- | -- | -- | -- | nullable, str (JSON) |
| `issn_print` | -- | -- | -- | -- | nullable, regex `^\d{4}-\d{3}[\dX]$` |
| `issn_electronic` | -- | -- | -- | -- | nullable, regex `^\d{4}-\d{3}[\dX]$` |
| `journal_name_short` | -- | nullable, str | -- | -- | nullable, str |
| `journal_iso_abbrev` | -- | nullable, str | -- | -- | -- |
| `journal_issn_type` | -- | nullable, enum `{Print, Electronic, Linking}` | -- | -- | -- |
| `nlm_unique_id` | -- | nullable, str | -- | -- | -- |
| `country` | -- | nullable, str | -- | -- | -- |
| `publisher` | -- | -- | nullable, str | -- | nullable, str |

### 1.9 Dates (provider-specific)

| Field | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| `creation_date` | nullable, regex `^\d{4}-\d{2}-\d{2}$` | -- | -- | -- | -- |
| `pub_month` | -- | nullable, Int64, check 1..12 | -- | -- | -- |
| `pub_day` | -- | nullable, Int64, check 1..31 | -- | -- | -- |
| `publication_status` | -- | nullable, enum `{ppublish, epublish, aheadofprint}` | -- | -- | -- |
| `date_completed` | -- | nullable, datetime | -- | -- | -- |
| `date_revised` | -- | nullable, datetime | -- | -- | -- |
| `published` | -- | -- | -- | -- | nullable, str (YYYY-MM-DD) |
| `published_print` | -- | -- | -- | -- | nullable, str (ISO) |
| `published_online` | -- | -- | -- | -- | nullable, str (ISO) |

### 1.10 Classification & Subjects

| Field | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| `subject_mesh` | -- | nullable, str (JSON array) | nullable, str (JSON array) | -- | -- |
| `subject_keywords` | -- | nullable, str (JSON array) | nullable, str (JSON array) | -- | nullable, str (JSON array) |
| `subject_topics` | -- | -- | nullable, str (JSON array) | -- | -- |
| `primary_topic` | -- | -- | nullable, str (JSON object) | -- | -- |
| `subject_fields` | -- | -- | -- | nullable, str (JSON array) | -- |
| `chemicals` | -- | nullable, str (JSON array) | -- | -- | -- |
| `gene_symbols` | -- | nullable, str (JSON array) | -- | -- | -- |
| `databanks` | -- | nullable, str (JSON array) | -- | -- | -- |
| `publication_types` | -- | nullable, str (JSON array) | -- | nullable, str (JSON array) | -- |
| `publication_type_list` | -- | nullable, str (JSON array) | -- | -- | -- |
| `citation_subset` | -- | nullable, str | -- | -- | -- |

### 1.11 Author Details (provider-specific)

| Field | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| `affiliation_structured` | -- | nullable, str (JSON) | -- | -- | -- |
| `authors_with_affiliations` | -- | nullable, str (JSON) | -- | -- | -- |
| `author_openalex_ids` | -- | -- | nullable, str (JSON) | -- | -- |
| `author_s2_ids` | -- | -- | -- | nullable, str (JSON) | -- |
| `author_h_indices` | -- | -- | -- | nullable, str (JSON) | -- |
| `author_details` | -- | -- | -- | -- | nullable, str (JSON) |
| `institution_ids` | -- | -- | nullable, str (JSON) | -- | -- |
| `institution_country_codes` | -- | -- | nullable, str (JSON) | -- | -- |
| `ror_ids` | -- | -- | nullable, str (JSON) | -- | -- |

### 1.12 Counts (PubMed-specific)

| Field | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| `author_count` | -- | nullable, Int64, check >= 0 | -- | -- | -- |
| `mesh_heading_count` | -- | nullable, Int64, check >= 0 | -- | -- | -- |
| `keyword_count` | -- | nullable, Int64, check >= 0 | -- | -- | -- |
| `grant_count` | -- | nullable, Int64, check >= 0 | -- | -- | -- |
| `chemical_count` | -- | nullable, Int64, check >= 0 | -- | -- | -- |

### 1.13 Provider-specific Extras

| Field | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| `chembl_release` | nullable, str | -- | -- | -- | -- |
| `is_retracted` | -- | -- | **non-null**, bool | -- | -- |
| `tldr` | -- | -- | -- | nullable, str | -- |
| `grants` | -- | -- | nullable, str (JSON) | -- | -- |
| `references` | -- | -- | -- | -- | nullable, str (JSON) |
| `citation_contexts` | -- | -- | -- | nullable, str (JSON) | -- |
| `content_domain_domains` | -- | -- | -- | -- | nullable, object |
| `content_domain_crossmark_restriction` | -- | -- | -- | -- | nullable, bool, coerce |

### 1.14 System & Lookup Fields

| Field | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| `_source` | **non-null**, eq `"chembl"` | **non-null**, eq `"pubmed"` | **non-null**, eq `"openalex"` | **non-null**, eq `"semanticscholar"` | **non-null**, eq `"crossref"` |
| `_lookup_method` | non-null, enum LOOKUP_METHODS | non-null (base), enum LOOKUP_METHODS | non-null, enum LOOKUP_METHODS | non-null, enum LOOKUP_METHODS | non-null (base), enum LOOKUP_METHODS |
| `_original_id` | nullable (base) | nullable (base) | nullable (base) | nullable (base) | nullable (base) |
| `_dq_warn` | nullable, BooleanDtype | nullable (base) | nullable (base) | nullable (base) | nullable (base) |
| `_dq_error` | nullable, BooleanDtype | nullable (base) | nullable (base) | nullable (base) | nullable (base) |

### 1.15 Cross-Field Validations (DQ layer)

| Rule Name | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| `publication_identifiable` | `any_present(pmid, doi, title)` | `all_present(pmid, title)` | `all_present(openalex_id, title)` | `all_present(paper_id, title)` | `all_present(doi, title)` |
| `has_identifier` | -- | `any_present(pmid, doi, pmc_id)` | -- | -- | -- |
| `retracted_publication_warning` | -- | -- | warn if `is_retracted == true` | -- | -- |

---

## 2. Divergence Analysis: Fields with Same Name but Different Validation

Below are fields that share the same name across two or more pipelines but have **different validation rules**.

### 2.1 `publication_type`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| **Schema field** | `publication_type` | `publication_type` (base) + `pub_type` (DQ) | `publication_type` | `publication_type` | `publication_type` |
| **Nullable** | true | true | true | true | true |
| **Schema enum** | `{PUBLICATION, BOOK, DATASET, PATENT}` | no enum in schema | no enum in schema | no enum | no enum |
| **DQ enum** | `{PUBLICATION, BOOK, DATASET, PATENT}` (via `doc_type`) | `{Journal Article, Review, Letter, Editorial, Clinical Trial, Meta-Analysis, Case Reports, Comparative Study, Evaluation Study}` (via `pub_type`) | `{article, book-chapter, book, dataset, dissertation, editorial, letter, review, preprint, other}` (via `type`) | -- | `{journal-article, book-chapter, proceedings-article, posted-content, book, report, dataset, standard}` (via `type`) |
| **Case convention** | UPPER_CASE | Title Case | lower-case with hyphens | pipe-delimited raw | lower-case with hyphens |
| **Source** | ChEMBL `doc_type` mapped | PubMed `PublicationType` MeSH | OpenAlex `type` raw | S2 `publicationTypes` joined | CrossRef `type` raw |

### 2.2 `publication_year`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| **Type** | `pd.Int64Dtype` | `pd.Int64Dtype` | `pd.Int64Dtype` | `pd.Int64Dtype` | `pd.Int64Dtype` |
| **Nullable** | true | true | true | true | true |
| **Schema range** | 1500..2100 | 1500..2100 | 1500..2100 | 1500..2100 | 1500..2100 |
| **DQ range** | 1500..2100 | 1500..2100 | 1500..2100 | 1500..2100 | 1500..2100 |
| **VO validation** | `PublicationYear` VO in transformer | `PublicationYear` VO in transformer | `PublicationYear` VO in transformer | `PublicationYear` VO in transformer | `PublicationYear` VO in transformer |
| **Source extraction** | `document.year` (int) | XML `<Year>` element (parsed) | JSON `publication_year` (int) | JSON `year` (int) | `published-print.date-parts[0][0]` or `published-online` (int) |
| **Date normalization** | year only, no full date | partial date -> end-of-period (YYYY-12-31, YYYY-MM-last_day) | direct from API | direct from API | date-parts array destructuring |
| **DQ field name** | `publication_year` | `publication_year` | `publication_year` | `publication_year` | `publication_year` |

> **Verdict:** Schema and DQ validation **are consistent** (range 1500..2100). Divergence is only in **source extraction logic** in transformers.

### 2.3 `title`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| **Nullable** | **true** | **false** (override) | **true** | **true** | **true** |
| **Schema check** | `title_not_empty` (base) | `title_not_empty` (base) + non-null | `title_not_empty` (base) | `title_not_empty` (base) | `title_not_empty` (base) |
| **DQ max_length** | 2000 | 2000 | 2000 | 2000 | 2000 |
| **Cross-field** | part of `any_present` | part of `all_present` | part of `all_present` | part of `all_present` | part of `all_present` |

### 2.4 `pmid`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| **Nullable** | true | **false** (PK) | true | true | -- (absent) |
| **Type** | str | str | str | str | -- |
| **Schema pattern** | `^[1-9]\d*$` (base) | `^[1-9]\d*$` (check method) | `^[1-9]\d*$` (base) | `^[1-9]\d*$` (base) | -- |
| **DQ validation** | range 1..100M | range 1..100M | -- | -- | -- |
| **VO** | `PubMedId.from_raw()` | `PubMedId.from_raw()` | -- | -- | -- |

### 2.5 `doi`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| **Nullable** | true | true | true | true | **false** (PK) |
| **Pattern** | `^10\.\d{4,}/.+$` | `^10\.\d{4,}/.+$` | `^10\.\d{4,}/.+$` | `^10\.\d{4,}/.+$` | `^10\.\d{4,}/.+$` |
| **DQ** | pattern check | pattern check | pattern check | pattern check | pattern check, non-null |
| **VO** | `DOI.from_raw()` | `DOI.from_raw()` | `DOI.from_raw()` | `DOI.from_raw()` | `DOI.from_raw()` |
| **Normalization** | lowercase, strip URL prefix | lowercase, strip URL prefix | lowercase, strip URL prefix | lowercase, strip URL prefix | lowercase, strip URL prefix |

### 2.6 `issn`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| **Present** | -- | yes | yes | -- | yes |
| **Pattern** | -- | `^\d{4}-\d{3}[\dX]$` | `^\d{4}-\d{3}[\dX]$` | -- | `^\d{4}-\d{3}[\dX]$` |
| **Additional ISSNs** | -- | `journal_issn_type` enum | -- | -- | `issn_print`, `issn_electronic`, `issn_list` |

### 2.7 `citations_received`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| **Present** | yes (base) | **excluded** | yes (base) | yes (base) | yes (base) |
| **Type** | Int64 | -- | Int64 | Int64 | Int64 |
| **Range** | >= 0 (base) | -- | >= 0 (base + DQ) | >= 0 (base + DQ) | >= 0 (base + DQ) |
| **DQ rule** | -- | -- | `citations_received >= 0` | `citations_received >= 0` | `citations_received >= 0` |

### 2.8 `is_oa`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| **Present** | excluded | excluded | yes (base) | yes (base) | yes (base) |
| **Type** | -- | -- | bool | bool | bool |
| **Nullable** | -- | -- | true | true | true |

### 2.9 `oa_status`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| **Present** | excluded | excluded | yes | yes | -- |
| **Enum values** | -- | -- | `{gold, green, hybrid, bronze, closed}` | `{gold, green, hybrid, bronze, closed}` | -- |

### 2.10 `subject_keywords`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| **Present** | -- | yes | yes | -- | yes |
| **Format** | -- | JSON array | JSON array | -- | JSON array |
| **Source** | -- | `<Keyword>` XML elements | OpenAlex `keywords` | -- | CrossRef `subject` array |

### 2.11 `subject_mesh`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| **Present** | -- | yes | yes | -- | -- |
| **Format** | -- | JSON array (descriptor/qualifier) | JSON array (descriptor names) | -- | -- |
| **Granularity** | -- | descriptor + qualifier pairs | descriptor names only | -- | -- |

### 2.12 `publication_types` (JSON array)

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| **Present** | -- | yes | -- | yes | -- |
| **Format** | -- | JSON array | -- | JSON array | -- |
| **Source** | -- | PubMed `<PublicationType>` UI codes | -- | S2 `publicationTypes` values | -- |
| **Values** | -- | MeSH-controlled vocabulary | -- | S2-specific taxonomy | -- |

### 2.13 `publication_identifiable` (cross-field DQ rule)

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|---|---|---|---|---|---|
| **Condition** | `any_present(pmid, doi, title)` | `all_present(pmid, title)` | `all_present(openalex_id, title)` | `all_present(paper_id, title)` | `all_present(doi, title)` |
| **Strictness** | LENIENT (any one) | STRICT (PK + title) | STRICT (PK + title) | STRICT (PK + title) | STRICT (PK + title) |

---

## 3. Unification Plans

For each divergent field, a proposed plan to unify validation across all pipelines.

### 3.1 `publication_type` — CRITICAL divergence

**Current state:**
- 4 different enum vocabularies (UPPER, Title Case, lower-hyphenated, pipe-delimited)
- ChEMBL: schema-level enum; PubMed/OpenAlex/CrossRef: DQ-level enum only
- SemanticScholar: no enum validation at all

**Proposed unification:**

1. **Define a canonical taxonomy** in `domain/types.py` or `domain/schemas/constants.py`:
   ```
   CANONICAL_PUBLICATION_TYPES = {
       "article", "review", "letter", "editorial", "book",
       "book-chapter", "dataset", "patent", "preprint",
       "clinical-trial", "meta-analysis", "case-report",
       "dissertation", "proceedings-article", "report",
       "standard", "other"
   }
   ```
   Convention: **lowercase with hyphens** (most common across APIs).

2. **Add mapping tables** per provider in transformer or a shared `publication_type_mapping.py`:
   - ChEMBL: `PUBLICATION -> article`, `BOOK -> book`, `DATASET -> dataset`, `PATENT -> patent`
   - PubMed: `Journal Article -> article`, `Review -> review`, `Clinical Trial -> clinical-trial`, etc.
   - OpenAlex: pass-through (already lowercase-hyphen)
   - CrossRef: pass-through (already lowercase-hyphen)
   - SemanticScholar: `JournalArticle -> article`, `Review -> review`, etc.

3. **Validate at schema level** (not just DQ) in all provider schemas using `isin=CANONICAL_PUBLICATION_TYPES`.

4. **Keep raw value** in a separate `source_type` column for provenance.

5. **Effort:** Medium. Requires transformer changes + schema updates + DQ config alignment.

---

### 3.2 `title` nullability — MEDIUM divergence

**Current state:**
- PubMed: non-nullable (strict)
- All others: nullable (lenient)

**Proposed unification:**

1. **Keep PubMed strict** — PMID records virtually always have titles (MEDLINE requirement).
2. **Tighten OpenAlex, SemanticScholar, CrossRef** to non-nullable in schema, since `publication_identifiable` DQ rule already requires `all_present(PK, title)`.
3. **Keep ChEMBL nullable** — ChEMBL documents may have titles missing (e.g., DATASET type).
4. **Alternative:** Unify all to non-nullable and add `title_not_empty` check. Records without title would fail DQ and be flagged.
5. **Effort:** Low. Schema field override + DQ alignment.

---

### 3.3 `pmid` DQ coverage — LOW divergence

**Current state:**
- ChEMBL, PubMed: DQ range 1..100,000,000
- OpenAlex, SemanticScholar: no DQ rule (schema regex only)

**Proposed unification:**

1. **Add DQ range rule** for `pmid` in OpenAlex and SemanticScholar DQ configs matching ChEMBL/PubMed (range 1..100M).
2. **Alternatively:** rely on shared `PubMedId` VO validation (already bounds-checks `< 10^10`) and schema regex `^[1-9]\d*$`.
3. **Effort:** Minimal. Add 4 lines to 2 DQ YAML files.

---

### 3.4 `citations_received` availability — MEDIUM divergence

**Current state:**
- PubMed: excluded entirely (API doesn't provide)
- ChEMBL: present in base but no DQ rule
- OpenAlex, SemanticScholar, CrossRef: present with DQ rules

**Proposed unification:**

1. **Accept PubMed exclusion** — this is an API limitation, not a validation gap.
2. **Add DQ rule for ChEMBL** `citations_received >= 0` for parity.
3. **Document in pipeline config** that PubMed citations must be enriched via CrossRef/OpenAlex composite pipeline.
4. **Effort:** Minimal. Add DQ rule to ChEMBL config.

---

### 3.5 `publication_identifiable` cross-field rule — HIGH divergence

**Current state:**
- ChEMBL: `any_present(pmid, doi, title)` — lenient
- All others: `all_present(PK, title)` — strict

**Proposed unification:**

1. **Standardize to two-tier validation**:
   - **Tier 1 (error):** PK must be present (non-negotiable per pipeline)
   - **Tier 2 (warning):** title should be present
2. **Update ChEMBL DQ** to `all_present(document_chembl_id, title)` with title as warn-severity (not error).
3. **Rationale:** ChEMBL PK (`document_chembl_id`) is already non-nullable at schema level, so the `any_present` rule is redundant for PK. Adding title requirement aligns with other pipelines.
4. **Effort:** Low. DQ YAML update for ChEMBL.

---

### 3.6 `issn` — LOW divergence

**Current state:**
- Pattern is consistent (`^\d{4}-\d{3}[\dX]$`) where present.
- CrossRef provides richer ISSN data (`issn_print`, `issn_electronic`, `issn_list`).

**Proposed unification:**

1. **No change needed for schema validation** — pattern is already unified.
2. **Consider adding** `issn_print` and `issn_electronic` to OpenAlex and PubMed schemas when the data becomes available from their APIs.
3. **Effort:** None currently required.

---

### 3.7 `subject_mesh` granularity — MEDIUM divergence

**Current state:**
- PubMed: descriptor + qualifier pairs (e.g., `{"descriptor": "Neoplasms", "qualifier": "drug therapy"}`)
- OpenAlex: descriptor names only (e.g., `"Neoplasms"`)

**Proposed unification:**

1. **Define canonical MeSH format** as JSON array of objects: `[{"descriptor": "...", "qualifier": "..."}]`.
2. **OpenAlex adapter:** map flat descriptors to `{"descriptor": name, "qualifier": null}`.
3. **Add shared schema check** validating JSON structure.
4. **Effort:** Medium. Transformer change for OpenAlex + shared check.

---

### 3.8 `oa_status` — LOW divergence

**Current state:**
- OpenAlex and SemanticScholar: identical enum `{gold, green, hybrid, bronze, closed}`.
- CrossRef: absent (has `license_url` instead).

**Proposed unification:**

1. **No schema change needed** — values are already consistent.
2. **Consider deriving** `oa_status` for CrossRef from `license_url` in composite pipeline.
3. **Effort:** Low (composite pipeline enrichment).

---

### 3.9 `language` — LOW divergence

**Current state:**
- Base schema: str, length 2..3 (ISO 639-1 or MARC)
- PubMed: overrides without length check (MARC codes, e.g., `eng`)
- ChEMBL, SemanticScholar: excluded

**Proposed unification:**

1. **PubMed override:** add explicit `str_length` check `2..3` matching base.
2. **ChEMBL, SemanticScholar:** keep excluded (data not available from API).
3. **Consider adding ISO 639 enum** validation for known language codes.
4. **Effort:** Minimal.

---

## 4. Summary: Prioritized Actions

| Priority | Field / Rule | Action | Effort | Impact |
|---|---|---|---|---|
| P0 | `publication_type` | Define canonical taxonomy + mapping tables | Medium | Enables cross-provider type analysis |
| P1 | `publication_identifiable` | Standardize to `all_present(PK, title)` + ChEMBL alignment | Low | Consistent DQ policy |
| P1 | `title` nullability | Tighten to non-null for OpenAlex/S2/CrossRef | Low | Matches DQ cross-field rules |
| P2 | `citations_received` DQ | Add ChEMBL DQ rule | Minimal | DQ parity |
| P2 | `pmid` DQ | Add OpenAlex/S2 DQ range rules | Minimal | DQ parity |
| P2 | `subject_mesh` granularity | Canonical JSON format | Medium | Cross-provider MeSH analysis |
| P3 | `language` | Add length check to PubMed | Minimal | Schema consistency |
| P3 | `oa_status` | Derive from CrossRef `license_url` | Low | OA analytics |
| P3 | `issn` | Future: extend to more providers | None | Future-proof |
