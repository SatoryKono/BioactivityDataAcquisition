# Publication Validation Matrix

*Version: 1.0.0 | Date: 2026-02-09*

Cross-provider analysis of field validation rules across all publication pipelines in BioETL.

**Pipelines analyzed:**

| # | Pipeline | Primary Key | Schema Class |
|---|----------|-------------|--------------|
| 1 | ChEMBL publication | `document_chembl_id` | `ChemblPublicationSchema` |
| 2 | PubMed publication | `pmid` | `PubMedPublicationSchema` |
| 3 | OpenAlex publication | `openalex_id` | `OpenAlexPublicationSchema` |
| 4 | SemanticScholar publication | `paper_id` | `SemanticScholarPublicationSchema` |
| 5 | CrossRef publication | `doi` | `PublicationEnrichedSchema` |
| 6 | ChEMBL publication_term | `(document_chembl_id, term_type, term)` | `PublicationTermSchema` |
| 7 | ChEMBL publication_similarity | `(doc_1, doc_2, sim_id)` | `PublicationSimilaritySchema` |

**Validation layers:**

| Layer | Source | Description |
|-------|--------|-------------|
| Pandera Schema | `domain/schemas/` | Type checks, regex patterns, range constraints, custom checks |
| DQ Config | `configs/dq/entities/` | Field-level and cross-field rules evaluated at runtime |
| Gold Filter | `configs/filter/entities/` | Post-Silver filtering for Gold layer promotion |
| Value Object | `domain/value_objects/` | Rich domain validation with normalization (DOI, PubMedId) |
| Base Schema | `domain/schemas/common/publication_base.py` | Inherited constraints shared by all 5 main pipelines |

---

## 1. Full Validation Matrix (Main Publication Pipelines)

### 1.1 Identifier Fields

| Field | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|-------|--------|--------|----------|-----------------|----------|
| `document_chembl_id` | **PK**, not null, pattern `^CHEMBL\d+$` | -- | -- | -- | -- |
| `openalex_id` | -- | -- | **PK**, not null, pattern `^W\d+$` | -- | -- |
| `paper_id` | -- | -- | -- | **PK**, not null, pattern `^[a-f0-9]{40}$` | -- |
| `pmid` | nullable, DQ range 1..100M | **PK**, not null, pattern `^[1-9]\d*$` | nullable, DQ range 1..100M, base pattern `^[1-9]\d*$` | nullable, DQ range 1..100M, base pattern `^[1-9]\d*$` | -- (not available) |
| `doi` | nullable, pattern `^10\.\d{4,}/.+$` | nullable, pattern `^10\.\d{4,}/.+$` | nullable, pattern `^10\.\d{4,}/.+$` | nullable, pattern `^10\.\d{4,}/.+$` | **PK**, not null, pattern `^10\.\d{4,}/.+$` |
| `pmc_id` | -- (not available) | nullable, check `^PMC\d+$` | nullable (inherited), pattern `^PMC\d+$` | -- (excluded) | -- (not available) |

### 1.2 Core Content Fields

| Field | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|-------|--------|--------|----------|-----------------|----------|
| `title` | nullable, DQ max_length 2000 | **not null**, inherited check `len >= 1` | nullable, DQ max_length 2000 + DQ pattern `\S` (warn) | nullable, DQ max_length 2000 + DQ pattern `\S` (warn) | nullable, DQ max_length 2000 + DQ pattern `\S` (warn) |
| `abstract` | nullable (inherited) | nullable (inherited) | nullable (inherited) | nullable (inherited) | nullable (inherited) |
| `authors` | nullable (inherited), JSON array, PII hashed | nullable (inherited), JSON array, PII hashed | nullable (inherited), JSON array, PII hashed | nullable (inherited), JSON array, PII hashed | nullable (inherited), JSON array, PII hashed |
| `affiliation_list` | nullable (inherited), JSON array | nullable (inherited), JSON array | nullable (inherited), JSON array | nullable (inherited), JSON array | nullable (inherited), JSON array |
| `author_orcids` | nullable (inherited), ORCID format check | nullable (inherited), ORCID format check | nullable (inherited), ORCID format check | nullable (inherited), ORCID format check | nullable (inherited), ORCID format check |

### 1.3 Publication Metadata Fields

| Field | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|-------|--------|--------|----------|-----------------|----------|
| `publication_year` | nullable, Int64, range 1500..2100 (schema + DQ) | nullable, Int64, range 1500..2100 (schema + DQ) | nullable, Int64, range 1500..2100 (schema + DQ) | nullable, Int64, range 1500..2100 (schema + DQ) | nullable, Int64, range 1500..2100 (schema + DQ) |
| `publication_date` | -- (only year available) | nullable, pattern `^\d{4}-\d{2}-\d{2}$` | nullable, pattern `^\d{4}-\d{2}-\d{2}$` | nullable, pattern `^\d{4}-\d{2}-\d{2}$` | nullable, pattern `^\d{4}-\d{2}-\d{2}$` |
| `publication_type` | nullable, isin `{PUBLICATION, PATENT, DATASET, BOOK}` | nullable (inherited, no constraint) | nullable (inherited, no constraint) | nullable (inherited, no constraint) | nullable (inherited, no constraint) |
| `language` | -- (not available) | nullable (inherited), str_length 2..3 | nullable (inherited), str_length 2..3 | -- (not available) | nullable (inherited), str_length 2..3 |
| `journal` | nullable (inherited) | nullable | nullable | nullable (inherited) | nullable (inherited) |

### 1.4 Pagination Fields

| Field | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|-------|--------|--------|----------|-----------------|----------|
| `page_first` | nullable | nullable (inherited) | nullable (inherited) | nullable (inherited) | nullable (inherited) |
| `page_last` | nullable | nullable (inherited) | nullable (inherited) | nullable (inherited) | nullable (inherited) |
| `volume` | nullable | -- (inherited) | nullable | nullable | -- (inherited) |
| `issue` | nullable | -- (inherited) | nullable | -- | -- |
| `page_range` | -- | nullable | -- | nullable | -- |
| `medline_pgn` | -- | nullable | -- | -- | -- |

### 1.5 Metrics Fields

| Field | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|-------|--------|--------|----------|-----------------|----------|
| `citations_received` | -- (not available) | -- (not available) | nullable, Int64, ge=0 (schema + DQ) | nullable, Int64, ge=0 (schema + DQ) | nullable, Int64, ge=0 (DQ only) |
| `citations_made` | -- (not available) | -- (not available) | nullable, Int64, ge=0 (inherited) | nullable, Int64, ge=0 (inherited) | nullable, Int64, ge=0 (inherited) |
| `fwci` | -- | -- | nullable, float, ge=0 (schema + DQ) | -- | -- |
| `influential_citation_count` | -- | -- | -- | nullable, Int64, ge=0 (schema + DQ) | -- |

### 1.6 Open Access Fields

| Field | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|-------|--------|--------|----------|-----------------|----------|
| `is_oa` | -- (not available) | -- (not available) | nullable, bool (inherited) | nullable, bool (inherited) | nullable, bool (inherited) |
| `oa_status` | -- | -- | nullable, isin `{gold, green, hybrid, bronze, closed}` | nullable, isin `{gold, green, hybrid, bronze, closed}` | -- |
| `open_access_url` | -- | -- | -- | nullable | -- |

### 1.7 System & Tracking Fields

| Field | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|-------|--------|--------|----------|-----------------|----------|
| `_lookup_method` | not null, isin `{direct, doi, pmid, title_fallback, title_only, unknown}` | not null, isin (same set) | not null, isin (same set) | not null, isin (same set) | not null, isin (same set) |
| `_original_id` | nullable | nullable | nullable | nullable | nullable |
| `_source` | not null, eq=`"chembl"` | not null, eq=`"pubmed"` | not null, eq=`"openalex"` | not null, eq=`"semanticscholar"` | not null, eq=`"crossref"` |
| `_dq_warn` | nullable, BooleanDtype, default=False | -- (inherited) | -- (inherited) | -- (inherited) | -- (inherited) |
| `_dq_error` | nullable, BooleanDtype, default=False | -- (inherited) | -- (inherited) | -- (inherited) | -- (inherited) |

### 1.8 Provider-Specific Fields (unique to one or two providers)

| Field | Provider | Validation |
|-------|----------|------------|
| `src_id` | ChEMBL | nullable, Int64 |
| `chembl_release` | ChEMBL | nullable, str |
| `creation_date` | ChEMBL | nullable, pattern `^\d{4}-\d{2}-\d{2}$` |
| `pii` | PubMed | nullable |
| `mid` | PubMed | nullable |
| `publisher_id` | PubMed | nullable |
| `abstract_structured` | PubMed | nullable, bool |
| `journal_name_short` | PubMed, CrossRef | nullable |
| `journal_iso_abbrev` | PubMed | nullable |
| `issn` | PubMed, OpenAlex, CrossRef | nullable, pattern `^\d{4}-\d{3}[\dX]$` |
| `journal_issn_type` | PubMed | nullable, isin `{Print, Electronic, Linking}` |
| `nlm_unique_id` | PubMed | nullable |
| `country` | PubMed | nullable |
| `pub_month` | PubMed | nullable, Int64, range 1..12 |
| `pub_day` | PubMed | nullable, Int64, range 1..31 |
| `publication_status` | PubMed | nullable, isin `{ppublish, epublish, aheadofprint}` |
| `publication_type_list` | PubMed | nullable, JSON array |
| `publication_types` | PubMed, SemanticScholar | nullable, JSON array |
| `date_completed` | PubMed | nullable, datetime |
| `date_revised` | PubMed | nullable, datetime |
| `citation_subset` | PubMed | nullable |
| `affiliation_structured` | PubMed | nullable, JSON |
| `author_count` | PubMed | nullable, Int64, ge=0 |
| `mesh_heading_count` | PubMed | nullable, Int64, ge=0 |
| `keyword_count` | PubMed | nullable, Int64, ge=0 |
| `grant_count` | PubMed | nullable, Int64, ge=0 |
| `chemical_count` | PubMed | nullable, Int64, ge=0 |
| `subject_mesh` | PubMed, OpenAlex | nullable, JSON array |
| `chemicals` | PubMed | nullable, JSON array |
| `subject_keywords` | PubMed, OpenAlex, CrossRef | nullable, JSON array |
| `databanks` | PubMed | nullable, JSON array |
| `gene_symbols` | PubMed | nullable, JSON array |
| `authors_with_affiliations` | PubMed | nullable, JSON |
| `publisher` | OpenAlex, CrossRef | nullable |
| `is_retracted` | OpenAlex | not null, bool |
| `subject_topics` | OpenAlex | nullable, JSON array |
| `primary_topic` | OpenAlex | nullable, JSON object |
| `grants` | OpenAlex | nullable, JSON array |
| `mag_id` | OpenAlex | nullable |
| `author_openalex_ids` | OpenAlex | nullable, JSON array |
| `institution_ids` | OpenAlex | nullable, JSON array |
| `institution_country_codes` | OpenAlex | nullable, JSON array |
| `ror_ids` | OpenAlex | nullable, JSON array |
| `dblp_id` | SemanticScholar | nullable |
| `corpus_id` | SemanticScholar | nullable, Int64, ge=0 |
| `tldr` | SemanticScholar | nullable |
| `subject_fields` | SemanticScholar | nullable, JSON array |
| `author_s2_ids` | SemanticScholar | nullable, JSON array |
| `author_h_indices` | SemanticScholar | nullable, JSON array |
| `citation_contexts` | SemanticScholar | nullable, JSON array |
| `issn_list` | CrossRef | nullable, JSON array |
| `issn_print` | CrossRef | nullable, pattern `^\d{4}-\d{3}[\dX]$` |
| `issn_electronic` | CrossRef | nullable, pattern `^\d{4}-\d{3}[\dX]$` |
| `published_print` | CrossRef | nullable, ISO date |
| `published_online` | CrossRef | nullable, ISO date |
| `published` | CrossRef | nullable, ISO date |
| `license_url` | CrossRef | nullable |
| `content_domain_domains` | CrossRef | nullable, list |
| `content_domain_crossmark_restriction` | CrossRef | nullable, bool |
| `alternative_id` | CrossRef | nullable, list |
| `author_details` | CrossRef | nullable, JSON array |
| `references` | CrossRef | nullable, JSON array |

---

## 2. Cross-Field Validation Rules (DQ Config)

| Rule Name | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|-----------|--------|--------|----------|-----------------|----------|
| `publication_identifiable` | any_present(`pmid`, `doi`, `title`) | all_present(`pmid`, `title`) | all_present(`openalex_id`, `title`) | all_present(`paper_id`, `title`) | all_present(`doi`, `title`) |
| `has_identifier` | -- | any_present(`pmid`, `doi`, `pmc_id`) | -- | -- | -- |
| `retracted_publication_warning` | -- | -- | severity=warn when `is_retracted == true` | -- | -- |

---

## 3. Gold Filter Rules

| Parameter | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|-----------|--------|--------|----------|-----------------|----------|
| `publication_year` range | min: 1800 (exclusive) | min: 1800, max: 2100 | min: 1800, max: 2100 | min: 1800, max: 2100 | min: 1800, max: 2100 |
| `doc_type` / column filter | `[PUBLICATION]` only | -- | -- | -- | -- |
| Required fields | `document_chembl_id`, `doc_type`, `title` | `pmid`, `title` | `openalex_id`, `title` | `paper_id`, `title` | `doi`, `title` |

---

## 4. DQ Thresholds (Provider-Level)

| Provider | soft_fail | hard_fail | Source |
|----------|-----------|-----------|--------|
| ChEMBL | inherited default | inherited default | `providers/chembl.yaml` |
| PubMed | 0.05 (5%) | 0.15 (15%) | `providers/pubmed.yaml` |
| OpenAlex | 0.08 (8%) | 0.25 (25%) | `providers/openalex.yaml` |
| SemanticScholar | 0.15 (15%) | 0.40 (40%) | `providers/semanticscholar.yaml` |
| CrossRef | 0.10 (10%) | 0.30 (30%) | `providers/crossref.yaml` |

---

## 5. Derived Publication Entities (ChEMBL Only)

### 5.1 publication_term

| Field | Validation |
|-------|------------|
| `document_chembl_id` | not null, pattern `^CHEMBL\d+$` |
| `term` | not null, min length 1 |
| `term_type` | not null, isin `{MESH_HEADING, MESH_QUALIFIER, KEYWORD, CONCEPT}` |
| `mesh_id` | nullable |
| `qualifier` | nullable |

Config: `strict=True`, `ordered=False`, `coerce=True`

### 5.2 publication_similarity

| Field | Validation |
|-------|------------|
| `sim_id` | not null, int |
| `doc_1` | not null, int |
| `doc_2` | not null, int |
| `pubmed_id1` | nullable, pattern `^\d+$` |
| `pubmed_id2` | nullable, pattern `^\d+$` |
| `tid_tani` | nullable, float, range [0, 1] |
| `mol_tani` | nullable, float, range [0, 1] |
| `avg_tani` | nullable, float, range [0, 1] |
| `max_tani` | nullable, float, range [0, 1] |

Config: `strict=True`, `ordered=True`, `coerce=True`

---

## 6. Fields With Same Name But Different Validation

This section identifies fields that share the same column name across pipelines but have **divergent validation rules**. These are prime candidates for unification.

### 6.1 `pmid`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|--------|--------|--------|----------|-----------------|----------|
| **Nullable** | yes | **no (PK)** | yes | yes | N/A |
| **Schema type** | `str` (inherited) | `str` (overridden) | `str` (inherited) | `str` (inherited) | -- |
| **Schema pattern** | `^[1-9]\d*$` (inherited) | `^[1-9]\d*$` (overridden) | `^[1-9]\d*$` (inherited) | `^[1-9]\d*$` (inherited) | -- |
| **DQ validation** | range 1..100M | range 1..100M | range 1..100M | range 1..100M | -- |
| **Value Object** | `PubMedId` (max 10^10) | `PubMedId` (max 10^10) | `PubMedId` (max 10^10) | `PubMedId` (max 10^10) | -- |

**Discrepancy:** PubMed DQ max = 100,000,000 (10^8) while `PubMedId` Value Object allows up to 10^10. These two bounds are inconsistent.

### 6.2 `doi`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|--------|--------|--------|----------|-----------------|----------|
| **Nullable** | yes | yes | yes | yes | **no (PK)** |
| **Schema pattern** | `^10\.\d{4,}/.+$` (via `DOI_REGEX_PATTERN`) | `^10\.\d{4,}/.+$` (via `DOI_REGEX_PATTERN`) | `^10\.\d{4,}/.+$` (via `DOI_REGEX_PATTERN`) | `^10\.\d{4,}/.+$` (via `DOI_REGEX_PATTERN`) | `^10\.\d{4,}/.+$` (via `DOI_REGEX_PATTERN`) |
| **DQ validation** | pattern `^10\.\d{4,}/.+$` | pattern `^10\.\d{4,}/.+$` | pattern `^10\.\d{4,}/.+$` | pattern `^10\.\d{4,}/.+$` | pattern `^10\.\d{4,}/.+$` |
| **Value Object** | `DOI` (lowercase, strip URL prefix, pattern `^10\.\d{4,}/\S+$`) | same | same | same | same |

**Discrepancy:** Schema/DQ use pattern `/.+$` (allows trailing whitespace) while the DOI Value Object uses `/\S+$` (no whitespace). The schema is more permissive than the Value Object.

### 6.3 `title`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|--------|--------|--------|----------|-----------------|----------|
| **Nullable** | yes | **no** | yes | yes | yes |
| **Schema check** | `title_not_empty` (inherited, len >= 1 when present) | `title_not_empty` (inherited) | `title_not_empty` (inherited) | `title_not_empty` (inherited) | `title_not_empty` (inherited) |
| **DQ max_length** | 2000 | 2000 | 2000 | 2000 | 2000 |
| **DQ pattern** | -- | -- | `\S` (severity=warn) | `\S` (severity=warn) | `\S` (severity=warn) |

**Discrepancy:** (1) PubMed makes `title` not-nullable while all others allow null. (2) OpenAlex, SemanticScholar, CrossRef add an extra DQ warn-level whitespace check (`\S`), ChEMBL and PubMed do not.

### 6.4 `publication_year`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|--------|--------|--------|----------|-----------------|----------|
| **Schema type** | `pd.Int64Dtype` (inherited) | `pd.Int64Dtype` (inherited) | `pd.Int64Dtype` (inherited) | `pd.Int64Dtype` (inherited) | `pd.Int64Dtype` (inherited) |
| **Schema range** | ge=1500, le=2100 | ge=1500, le=2100 | ge=1500, le=2100 | ge=1500, le=2100 | ge=1500, le=2100 |
| **DQ range** | 1500..2100 | 1500..2100 | 1500..2100 | 1500..2100 | 1500..2100 |
| **Gold filter min** | **1800 (exclusive)** | 1800 | 1800 | 1800 | 1800 |
| **Gold filter max** | **(none specified)** | 2100 | 2100 | 2100 | 2100 |
| **Gold filter include_min** | **false** | (default: true) | (default: true) | (default: true) | (default: true) |

**Discrepancy:** (1) ChEMBL gold filter uses `include_min: false` (year > 1800), while all others use inclusive `min: 1800` (year >= 1800). The boundary behavior at year=1800 is inconsistent. (2) ChEMBL gold filter does not specify an explicit `max`, while PubMed, OpenAlex, SemanticScholar, and CrossRef explicitly set `max: 2100`.

### 6.5 `publication_type`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|--------|--------|--------|----------|-----------------|----------|
| **Schema constraint** | isin `{PUBLICATION, PATENT, DATASET, BOOK}` | none (inherited) | none (overridden, no isin) | none (overridden, no isin) | none (overridden, no isin) |
| **DQ enum (field name)** | `doc_type`: `[PUBLICATION, BOOK, DATASET, PATENT]` | `pub_type`: `[Journal Article, Review, Letter, ...]` | `type`: `[article, book-chapter, book, ...]` | -- | `type`: `[journal-article, book-chapter, ...]` |
| **Naming** | unified to `publication_type` | separate field `pub_type` + `publication_type_list` | raw type stored in `publication_type` | pipe-delimited `publication_type` + JSON `publication_types` | raw type stored in `publication_type` |
| **Value format** | UPPER_CASE canonical | Mixed case (PubMed vocabulary) | lowercase (OpenAlex vocabulary) | pipe-delimited string | lowercase-hyphenated (CrossRef vocabulary) |

**Discrepancy:** This is the most fragmented field. Each provider uses a different vocabulary, different casing, and different field names for the source type. ChEMBL schema enforces a canonical set, while others store raw provider values without normalization to the canonical set.

### 6.6 `citations_received`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|--------|--------|--------|----------|-----------------|----------|
| **Available** | no | no | yes | yes | yes |
| **Schema type** | -- | -- | `pd.Int64Dtype`, ge=0 | `pd.Int64Dtype`, ge=0 | `pd.Int64Dtype`, ge=0 (inherited) |
| **DQ field name** | -- | -- | `citations_received` | `citations_received` | `citations_received` |
| **DQ range** | -- | -- | min=0 | min=0 | min=0 |
| **DQ max** | -- | -- | **(none)** | **(none)** | **(none)** |

**Discrepancy:** Consistent where present. Minor issue: no upper-bound sanity check on any provider (e.g., citation_count > 10M might indicate data error).

### 6.7 `citations_made` (reference_count)

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|--------|--------|--------|----------|-----------------|----------|
| **Available** | no | no | yes | yes | yes (inherited) |
| **Schema** | -- | -- | `pd.Int64Dtype`, ge=0 (inherited) | `pd.Int64Dtype`, ge=0 (inherited) | `pd.Int64Dtype`, ge=0 (inherited) |
| **DQ field name** | -- | -- | `reference_count` | `reference_count` | -- |

**Discrepancy:** DQ config for OpenAlex and SemanticScholar validates under the original field name `reference_count` (pre-mapping name), but the schema uses the unified name `citations_made`. CrossRef has no DQ rule for this field.

### 6.8 `oa_status`

| Aspect | OpenAlex | SemanticScholar | Others |
|--------|----------|-----------------|--------|
| **Schema** | isin `{gold, green, hybrid, bronze, closed}` | isin `{gold, green, hybrid, bronze, closed}` | N/A |

**Discrepancy:** None -- consistent between the two providers that support it.

### 6.9 `issn`

| Aspect | PubMed | OpenAlex | CrossRef |
|--------|--------|----------|----------|
| **Schema pattern** | `^\d{4}-\d{3}[\dX]$` | `^\d{4}-\d{3}[\dX]$` | `^\d{4}-\d{3}[\dX]$` |
| **Nullable** | yes | yes | yes |

**Discrepancy:** None -- consistent pattern across all three providers.

### 6.10 `subject_keywords`

| Aspect | PubMed | OpenAlex | CrossRef |
|--------|--------|----------|----------|
| **Schema** | nullable, JSON array | nullable, JSON array | nullable, JSON array |
| **DQ** | -- | -- | -- |

**Discrepancy:** None -- consistent.

### 6.11 `subject_mesh`

| Aspect | PubMed | OpenAlex |
|--------|--------|----------|
| **Schema** | nullable, JSON array (descriptor/qualifier) | nullable, JSON array (descriptor names) |
| **Content format** | descriptor/qualifier pairs | descriptor names only |

**Discrepancy:** Different granularity in MeSH data. PubMed includes qualifiers; OpenAlex provides only descriptor names. No structural validation difference at schema level, but semantic content differs.

### 6.12 Cross-field rule `publication_identifiable`

| Aspect | ChEMBL | PubMed | OpenAlex | SemanticScholar | CrossRef |
|--------|--------|--------|----------|-----------------|----------|
| **Condition** | `any_present` | `all_present` | `all_present` | `all_present` | `all_present` |
| **Fields** | pmid, doi, title | pmid, title | openalex_id, title | paper_id, title | doi, title |

**Discrepancy:** ChEMBL uses `any_present` (at least one field needed), while all other providers use `all_present` (all listed fields required). This means ChEMBL accepts records that have only a DOI and no title, while others reject titleless records.

---

## 7. Unification Plans

### 7.1 `pmid` -- Align DQ Upper Bound with Value Object

**Current state:** DQ configs set `max: 100000000` (10^8), Value Object `PubMedId` allows up to `10_000_000_000` (10^10).

**Plan:**
1. **Preferred option:** Raise DQ `max` in all 4 configs (ChEMBL, PubMed, OpenAlex, SemanticScholar) from `100000000` to `10000000000` to match the `PubMedId` Value Object bound.
2. **Rationale:** PubMed currently assigns PMIDs above 39M and growing. The DQ limit of 10^8 is sufficient for the near future, but aligning with the Value Object avoids silent divergence.
3. **Action items:**
   - Update `configs/dq/entities/{chembl,pubmed,openalex,semanticscholar}/publication.yaml`: change `max: 100000000` to `max: 10000000000`.
   - Add a comment referencing `PubMedId._MAX_PMID`.
4. **Risk:** Low. Widening the range is non-breaking.

### 7.2 `doi` -- Align Schema Pattern with Value Object

**Current state:** Schema/DQ pattern `^10\.\d{4,}/.+$` allows trailing whitespace; Value Object pattern `^10\.\d{4,}/\S+$` rejects it.

**Plan:**
1. **Change `DOI_REGEX_PATTERN`** in `domain/validation.py` from `^10\.\d{4,}/.+$` to `^10\.\d{4,}/\S+$` to match the `DOI` Value Object.
2. **Update all DQ configs** that reference the DOI pattern to use the same `/\S+$` suffix.
3. **Rationale:** DOIs cannot contain spaces per the DOI Handbook. The Value Object is correct; the schema pattern should be tightened.
4. **Action items:**
   - `src/bioetl/domain/validation.py`: update `DOI_REGEX_PATTERN`.
   - Verify all 5 DQ configs reference the same pattern string.
   - Run existing tests to confirm no regressions.
5. **Risk:** Low. Any DOI with trailing whitespace would already fail the Value Object; tightening the schema catches the issue earlier.

### 7.3 `title` -- Standardize Nullability and Whitespace Check

**Current state:** PubMed `title` is not-nullable; others allow null. Only OpenAlex/SemanticScholar/CrossRef DQ configs have a whitespace warn check.

**Plan:**
1. **Keep PubMed not-null** (PMID is meaningless without a title in MEDLINE).
2. **Add `\S` pattern warn-level DQ check** to ChEMBL and PubMed configs for consistency.
3. **Rationale:** A whitespace-only title is never valid. All providers should warn about it. PubMed already rejects null titles at schema level, but adding the warn check catches edge cases (e.g., `"   "`).
4. **Action items:**
   - Add to `configs/dq/entities/chembl/publication.yaml`:
     ```yaml
     - field: title
       type: pattern
       pattern: '\S'
       nullable: true
       severity: warn
       error_message: "Title should not be empty or whitespace-only"
     ```
   - Add the same rule to `configs/dq/entities/pubmed/publication.yaml`.
5. **Risk:** Low. Warn-level only; no records rejected.

### 7.4 `publication_year` -- Standardize Gold Filter Behavior

**Current state:** ChEMBL uses `include_min: false` (year > 1800) with no explicit max. All others use `min: 1800` (year >= 1800) with `max: 2100`.

**Plan:**
1. **Standardize all gold filters** to `min: 1800, max: 2100` with inclusive boundaries (default behavior).
2. **Remove `include_min: false`** from ChEMBL config.
3. **Add explicit `max: 2100`** to ChEMBL config.
4. **Rationale:** The difference between > 1800 and >= 1800 is negligible (affects only publications from exactly year 1800). Consistency is more valuable than this edge case.
5. **Action items:**
   - Update `configs/filter/entities/chembl/publication.yaml`:
     ```yaml
     ranges:
       publication_year:
         min: 1800
         max: 2100
     ```
6. **Risk:** Minimal. Could include a handful of publications from year 1800 that were previously excluded from ChEMBL gold.

### 7.5 `publication_type` -- Implement Canonical Mapping

**Current state:** Each provider uses its own vocabulary and casing. ChEMBL stores `{PUBLICATION, PATENT, DATASET, BOOK}`. PubMed uses `Journal Article`, `Review`, etc. OpenAlex uses `article`, `book`, etc. CrossRef uses `journal-article`, `book-chapter`, etc.

**Plan:**
1. **Define a canonical type enum** in `domain/schemas/constants.py`:
   ```
   CANONICAL_PUBLICATION_TYPES = {
       PUBLICATION, PREPRINT, REVIEW, BOOK, BOOK_CHAPTER, DATASET,
       EDITORIAL, LETTER, PATENT, DISSERTATION, REPORT, OTHER
   }
   ```
2. **Create a mapping table** in `domain/mapping/publication_type_mapping.py`:
   ```python
   PUBLICATION_TYPE_MAP = {
       # OpenAlex
       "article": "PUBLICATION",
       "book-chapter": "BOOK_CHAPTER",
       "book": "BOOK",
       "preprint": "PREPRINT",
       "review": "REVIEW",
       "editorial": "EDITORIAL",
       "letter": "LETTER",
       "dataset": "DATASET",
       "dissertation": "DISSERTATION",
       "other": "OTHER",
       # CrossRef
       "journal-article": "PUBLICATION",
       "proceedings-article": "PUBLICATION",
       "posted-content": "PREPRINT",
       "report": "REPORT",
       "standard": "OTHER",
       # PubMed
       "Journal Article": "PUBLICATION",
       "Review": "REVIEW",
       "Letter": "LETTER",
       "Editorial": "EDITORIAL",
       "Clinical Trial": "PUBLICATION",
       "Meta-Analysis": "REVIEW",
       "Case Reports": "PUBLICATION",
       "Comparative Study": "PUBLICATION",
       "Evaluation Study": "PUBLICATION",
   }
   ```
3. **Apply mapping in transformers** before writing to Silver layer, storing the canonical type in `publication_type` and the raw provider type in a new `_raw_publication_type` field.
4. **Update all DQ configs** to validate against the canonical enum.
5. **Action items:**
   - Create `domain/mapping/publication_type_mapping.py`.
   - Extend `PublicationBaseSchema` with `_raw_publication_type: Series[str]` (nullable).
   - Update `base_publication_transformer.py` to apply mapping.
   - Update 5 DQ configs to use canonical enum for `publication_type`.
   - Remove provider-specific type fields from DQ (`doc_type`, `pub_type`, `type`).
6. **Risk:** Medium. Requires careful mapping for edge cases. Some PubMed types (e.g., "Clinical Trial") may not map cleanly. Recommend starting with the mapping table and iterating with domain experts.

### 7.6 `citations_received` -- Add Upper-Bound Sanity Check

**Current state:** All three providers (OpenAlex, SemanticScholar, CrossRef) validate `ge=0` with no upper bound.

**Plan:**
1. **Add a warn-level DQ upper bound** (e.g., `max: 10000000`) across all 3 configs.
2. **Rationale:** Citations > 10M likely indicate data corruption. A warn-level check flags these without rejecting records.
3. **Action items:**
   - Add to OpenAlex, SemanticScholar, CrossRef DQ configs:
     ```yaml
     - field: citations_received
       type: range
       min: 0
       max: 10000000
       nullable: true
       severity: warn
       error_message: "Unusually high citation count"
     ```
4. **Risk:** Low. Warn-level only.

### 7.7 `citations_made` / `reference_count` -- Align DQ Field Names

**Current state:** OpenAlex and SemanticScholar DQ configs validate `reference_count`, but the unified schema field is `citations_made`.

**Plan:**
1. **Update DQ configs** to use the unified field name `citations_made` instead of `reference_count`.
2. **Alternatively**, if the DQ engine resolves field mappings automatically, document this behavior and verify it works.
3. **Add CrossRef DQ rule** for `citations_made` (currently missing).
4. **Action items:**
   - Rename `reference_count` to `citations_made` in:
     - `configs/dq/entities/openalex/publication.yaml`
     - `configs/dq/entities/semanticscholar/publication.yaml`
   - Add to `configs/dq/entities/crossref/publication.yaml`:
     ```yaml
     - field: citations_made
       type: range
       min: 0
       nullable: true
       error_message: "Reference count must be non-negative"
     ```
5. **Risk:** Low if DQ engine supports field name mapping. Medium if DQ engine uses literal field names.

### 7.8 `publication_identifiable` -- Standardize Cross-Field Rule Semantics

**Current state:** ChEMBL uses `any_present` while all others use `all_present`.

**Plan:**
1. **Evaluate whether ChEMBL should switch to `all_present`** for `(document_chembl_id, title)`.
2. **Recommended:** Change ChEMBL to `all_present(document_chembl_id, title)` -- a ChEMBL document without a title is of limited analytical value. Keep the secondary rule `any_present(pmid, doi, title)` as a supplementary check.
3. **Updated ChEMBL config:**
   ```yaml
   entity_cross_field_validations:
     - name: publication_identifiable
       fields:
         - document_chembl_id
         - title
       condition: all_present
       error_message: "Publication must have ChEMBL ID and title"
     - name: has_external_identifier
       fields:
         - pmid
         - doi
       condition: any_present
       severity: warn
       error_message: "Publication should have at least one external identifier (PMID or DOI)"
   ```
4. **Action items:**
   - Update ChEMBL DQ config.
   - Verify gold filter already requires `title` (it does).
5. **Risk:** Medium. Some ChEMBL documents may lack titles (e.g., patent stubs). Analyze current data to confirm impact before applying.

### 7.9 `subject_mesh` -- Document Content Granularity Difference

**Current state:** PubMed provides descriptor + qualifier pairs; OpenAlex provides descriptor names only.

**Plan:**
1. **No schema-level change needed** -- both store JSON arrays.
2. **Document the semantic difference** in the field description and in the composite pipeline's merge logic.
3. **Action items:**
   - Add a note to `PublicationBaseSchema` or a separate mapping doc: "PubMed subject_mesh contains descriptor/qualifier pairs; OpenAlex subject_mesh contains descriptor names only. Composite merge should prefer PubMed as the richer source."
4. **Risk:** None. Documentation-only change.

---

## 8. Summary: Priority of Unification Tasks

| Priority | Task | Fields Affected | Risk | Effort |
|----------|------|-----------------|------|--------|
| **P1** | Align DOI pattern (schema vs Value Object) | `doi` | Low | Small |
| **P1** | Standardize gold filter `publication_year` | `publication_year` | Low | Small |
| **P2** | Align PMID DQ upper bound | `pmid` | Low | Small |
| **P2** | Add title whitespace DQ warn to all providers | `title` | Low | Small |
| **P2** | Align DQ field names with unified schema | `citations_made` | Low-Med | Small |
| **P3** | Canonical publication_type mapping | `publication_type` | Medium | Large |
| **P3** | Standardize cross-field rule semantics | `publication_identifiable` | Medium | Medium |
| **P4** | Add citation count upper-bound warn | `citations_received` | Low | Small |
| **P4** | Document subject_mesh granularity | `subject_mesh` | None | Small |
