# Publication Validation Matrix

*Version: 1.0.0 | Date: 2026-02-10*

Cross-pipeline comparison of validation rules for `publication` entity across all five providers.

**Validation layers analysed:**

| Layer | Source |
|-------|--------|
| **Pandera schema** | `src/bioetl/domain/schemas/{provider}/publication.py` + base `common/publication_base.py` |
| **DQ rules** | `configs/dq/entities/{provider}/publication.yaml` |
| **Filter rules** | `configs/filter/entities/{provider}/publication.yaml` |

**Pipeline legend:**

| Abbr | Provider | Schema class | Primary Key |
|------|----------|-------------|-------------|
| **CH** | ChEMBL | `ChemblPublicationSchema` | `document_chembl_id` |
| **PM** | PubMed | `PubMedPublicationSchema` | `pmid` |
| **CR** | CrossRef | `PublicationEnrichedSchema` | `doi` |
| **OA** | OpenAlex | `OpenAlexPublicationSchema` | `openalex_id` |
| **S2** | SemanticScholar | `SemanticScholarPublicationSchema` | `paper_id` |

---

## 1. Master Validation Matrix

> **Convention:** `nullable=F` means non-nullable (required); `nullable=T` means nullable (optional).
> Inherited from `PublicationBaseSchema` is marked **(base)**.
> Provider-specific overrides are marked **(override)**.

### 1.1 Primary Keys

| Field | CH | PM | CR | OA | S2 |
|-------|----|----|----|----|-----|
| `document_chembl_id` | `str`, nullable=F, pattern `^CHEMBL\d+$` | -- | -- | -- | -- |
| `pmid` | **(base)** `str`, nullable=T, pattern `^[1-9]\d*$` | **(override)** `str`, nullable=F, pattern `^[1-9]\d*$` | **(base)** `str`, nullable=T | **(base)** `str`, nullable=T | **(base)** `str`, nullable=T |
| `doi` | **(base)** `str`, nullable=T, pattern `^10\.\d{4,}/\S+$` | **(override)** `str`, nullable=T, pattern `^10\.\d{4,}/\S+$` | **(override)** `str`, nullable=F, pattern `^10\.\d{4,}/\S+$` | **(base)** `str`, nullable=T | **(base)** `str`, nullable=T |
| `pmc_id` | **(base)** `str`, nullable=T, pattern `^PMC\d+$` | **(base)** + custom check `^PMC\d+$` | **(base)** `str`, nullable=T | **(base)** `str`, nullable=T | **(base)** `str`, nullable=T |
| `openalex_id` | -- | -- | -- | `str`, nullable=F, pattern `^W\d+$` | -- |
| `paper_id` | -- | -- | -- | -- | `str`, nullable=F, pattern `^[a-f0-9]{40}$` |

### 1.2 Core Content

| Field | CH | PM | CR | OA | S2 |
|-------|----|----|----|----|-----|
| `title` | **(base)** `str`, nullable=T, check: not_empty | **(override)** `str`, nullable=F, check: not_empty | **(base)** `str`, nullable=T, check: not_empty | **(base)** `str`, nullable=T, check: not_empty | **(base)** `str`, nullable=T, check: not_empty |
| `abstract` | **(base)** `str`, nullable=T | **(base)** `str`, nullable=T | **(base)** `str`, nullable=T | **(base)** `str`, nullable=T | **(base)** `str`, nullable=T |
| `authors` | **(base)** `str`, nullable=T (JSON array) | **(base)** `str`, nullable=T (JSON array) | **(base)** `str`, nullable=T (JSON array) | **(base)** `str`, nullable=T (JSON array) | **(base)** `str`, nullable=T (JSON array) |
| `affiliation_list` | **(base)** `str`, nullable=T (JSON array) | **(base)** `str`, nullable=T (JSON array) | **(base)** `str`, nullable=T (JSON array) | **(base)** `str`, nullable=T (JSON array) | **(base)** `str`, nullable=T (JSON array) |
| `author_orcids` | **(base)** `str`, nullable=T, check: ORCID format in JSON | **(base)** `str`, nullable=T, check: ORCID format in JSON | **(base)** `str`, nullable=T, check: ORCID format in JSON | **(base)** `str`, nullable=T, check: ORCID format in JSON | **(base)** `str`, nullable=T, check: ORCID format in JSON |

### 1.3 Publication Metadata

| Field | CH | PM | CR | OA | S2 |
|-------|----|----|----|----|-----|
| `journal` | **(base)** `str`, nullable=T | **(override)** `str`, nullable=T | **(base)** `str`, nullable=T | **(base)** `str`, nullable=T | **(base)** `str`, nullable=T |
| `publication_year` | **(base)** `Int64`, nullable=T, ge=1500, le=2100 | **(base)** `Int64`, nullable=T, ge=1500, le=2100 | **(base)** `Int64`, nullable=T, ge=1500, le=2100 | **(base)** `Int64`, nullable=T, ge=1500, le=2100 | **(base)** `Int64`, nullable=T, ge=1500, le=2100 |
| `publication_date` | **(base)** `str`, nullable=T, pattern `^\d{4}-\d{2}-\d{2}$` | **(base)** `str`, nullable=T, pattern `^\d{4}-\d{2}-\d{2}$` | **(base)** `str`, nullable=T, pattern `^\d{4}-\d{2}-\d{2}$` | **(base)** `str`, nullable=T, pattern `^\d{4}-\d{2}-\d{2}$` | **(base)** `str`, nullable=T, pattern `^\d{4}-\d{2}-\d{2}$` |
| `publication_type` | **(override)** `str`, nullable=T, isin={PUBLICATION, PATENT, DATASET, BOOK} | **(base)** `str`, nullable=T | **(override)** `str`, nullable=T (raw CrossRef type) | **(override)** `str`, nullable=T (raw OpenAlex type) | **(override)** `str`, nullable=T (pipe-delimited) |
| `publication_type_unified` | **(base)** `str`, nullable=T | **(base)** `str`, nullable=T | **(base)** `str`, nullable=T | **(base)** `str`, nullable=T | **(base)** `str`, nullable=T |
| `publication_subclass` | **(base)** `str`, nullable=T | **(base)** `str`, nullable=T | **(base)** `str`, nullable=T | **(base)** `str`, nullable=T | **(base)** `str`, nullable=T |
| `publication_class` | **(base)** `str`, nullable=T, isin={EXP, REV, PEER} | **(base)** `str`, nullable=T, isin={EXP, REV, PEER} | **(base)** `str`, nullable=T, isin={EXP, REV, PEER} | **(base)** `str`, nullable=T, isin={EXP, REV, PEER} | **(base)** `str`, nullable=T, isin={EXP, REV, PEER} |
| `language` | **(base)** `str`, nullable=T, len 2..3 | **(base)** `str`, nullable=T, len 2..3 | **(base)** `str`, nullable=T, len 2..3 | **(base)** `str`, nullable=T, len 2..3 | **(base)** `str`, nullable=T, len 2..3 |

### 1.4 Pagination

| Field | CH | PM | CR | OA | S2 |
|-------|----|----|----|----|-----|
| `page_first` | **(override)** `str`, nullable=T | **(base)** `str`, nullable=T | **(base)** `str`, nullable=T | **(base)** `str`, nullable=T | **(base)** `str`, nullable=T |
| `page_last` | **(override)** `str`, nullable=T | **(base)** `str`, nullable=T | **(base)** `str`, nullable=T | **(base)** `str`, nullable=T | **(base)** `str`, nullable=T |
| `page_range` | -- | `str`, nullable=T | -- | -- | `str`, nullable=T |
| `volume` | `str`, nullable=T | -- | -- | `str`, nullable=T | `str`, nullable=T |
| `issue` | `str`, nullable=T | -- | -- | `str`, nullable=T | -- |
| `medline_pgn` | -- | `str`, nullable=T | -- | -- | -- |

### 1.5 Metrics

| Field | CH | PM | CR | OA | S2 |
|-------|----|----|----|----|-----|
| `citations_received` | **(base)** `Int64`, nullable=T, ge=0 | **(base)** `Int64`, nullable=T, ge=0 | **(base)** `Int64`, nullable=T, ge=0 | **(base)** `Int64`, nullable=T, ge=0 | **(base)** `Int64`, nullable=T, ge=0 |
| `citations_made` | **(base)** `Int64`, nullable=T, ge=0 | **(base)** `Int64`, nullable=T, ge=0 | **(base)** `Int64`, nullable=T, ge=0 | **(base)** `Int64`, nullable=T, ge=0 | **(base)** `Int64`, nullable=T, ge=0 |
| `fwci` | -- | -- | -- | `float`, nullable=T, ge=0 | -- |
| `influential_citation_count` | -- | -- | -- | -- | `Int64`, nullable=T, ge=0 |

### 1.6 Open Access

| Field | CH | PM | CR | OA | S2 |
|-------|----|----|----|----|-----|
| `is_oa` | **(base)** `bool`, nullable=T | **(base)** `bool`, nullable=T | **(base)** `bool`, nullable=T | **(base)** `bool`, nullable=T | **(base)** `bool`, nullable=T |
| `oa_status` | -- | -- | -- | `str`, nullable=T, isin={gold, green, hybrid, bronze, closed} | `str`, nullable=T, isin={gold, green, hybrid, bronze, closed} |
| `open_access_url` | -- | -- | -- | -- | `str`, nullable=T |

### 1.7 Journal Details

| Field | CH | PM | CR | OA | S2 |
|-------|----|----|----|----|-----|
| `journal_name_short` | -- | `str`, nullable=T | `str`, nullable=T | -- | -- |
| `journal_iso_abbrev` | -- | `str`, nullable=T | -- | -- | -- |
| `issn` | -- | `str`, nullable=T, pattern `^\d{4}-\d{3}[\dX]$` | `str`, nullable=T, pattern `^\d{4}-\d{3}[\dX]$` | `str`, nullable=T, pattern `^\d{4}-\d{3}[\dX]$` | -- |
| `issn_print` | -- | -- | `str`, nullable=T, pattern `^\d{4}-\d{3}[\dX]$` | -- | -- |
| `issn_electronic` | -- | -- | `str`, nullable=T, pattern `^\d{4}-\d{3}[\dX]$` | -- | -- |
| `issn_list` | -- | -- | `str`, nullable=T (JSON array) | -- | -- |
| `journal_issn_type` | -- | `str`, nullable=T, isin={Print, Electronic, Linking} | -- | -- | -- |
| `publisher` | -- | -- | `str`, nullable=T | `str`, nullable=T | -- |
| `nlm_unique_id` | -- | `str`, nullable=T | -- | -- | -- |
| `country` | -- | `str`, nullable=T | -- | -- | -- |

### 1.8 System & Lookup

| Field | CH | PM | CR | OA | S2 |
|-------|----|----|----|----|-----|
| `_lookup_method` | **(base)** `str`, nullable=F, isin={direct, doi, pmid, title_fallback, title_only, unknown} | **(base)** same | **(base)** same | **(base)** same | **(base)** same |
| `_original_id` | **(base)** `str`, nullable=T | **(base)** same | **(base)** same | **(base)** same | **(base)** same |
| `_source` | **(override)** `str`, nullable=F, eq=`chembl` | **(override)** `str`, nullable=F, eq=`pubmed` | **(override)** `str`, nullable=F, eq=`crossref` | **(override)** `str`, nullable=F, eq=`openalex` | **(override)** `str`, nullable=F, eq=`semanticscholar` |

### 1.9 Classification

| Field | CH | PM | CR | OA | S2 |
|-------|----|----|----|----|-----|
| `subject_mesh` | -- | `str`, nullable=T (JSON array) | -- | `str`, nullable=T (JSON array) | -- |
| `subject_keywords` | -- | `str`, nullable=T (JSON array) | `str`, nullable=T (JSON array) | `str`, nullable=T (JSON array) | -- |
| `subject_fields` | -- | -- | -- | -- | `str`, nullable=T (JSON array) |
| `subject_topics` | -- | -- | -- | `str`, nullable=T (JSON array) | -- |
| `primary_topic` | -- | -- | -- | `str`, nullable=T (JSON object) | -- |
| `chemicals` | -- | `str`, nullable=T (JSON array) | -- | -- | -- |
| `databanks` | -- | `str`, nullable=T (JSON array) | -- | -- | -- |
| `gene_symbols` | -- | `str`, nullable=T (JSON array) | -- | -- | -- |
| `publication_types` | -- | `str`, nullable=T (JSON array) | -- | -- | `str`, nullable=T (JSON array) |
| `publication_type_list` | -- | `str`, nullable=T (JSON array) | -- | -- | -- |

### 1.10 Provider-Specific Identifiers

| Field | CH | PM | CR | OA | S2 |
|-------|----|----|----|----|-----|
| `src_id` | `Int64`, nullable=T | -- | -- | -- | -- |
| `chembl_release` | `str`, nullable=T | -- | -- | -- | -- |
| `creation_date` | `str`, nullable=T, pattern `^\d{4}-\d{2}-\d{2}$` | -- | -- | -- | -- |
| `pii` | -- | `str`, nullable=T | -- | -- | -- |
| `mid` | -- | `str`, nullable=T | -- | -- | -- |
| `publisher_id` | -- | `str`, nullable=T | -- | -- | -- |
| `mag_id` | -- | -- | -- | `str`, nullable=T | -- |
| `dblp_id` | -- | -- | -- | -- | `str`, nullable=T |
| `corpus_id` | -- | -- | -- | -- | `Int64`, nullable=T, ge=0 |

### 1.11 Provider-Specific Content

| Field | CH | PM | CR | OA | S2 |
|-------|----|----|----|----|-----|
| `abstract_structured` | -- | `bool`, nullable=T | -- | -- | -- |
| `tldr` | -- | -- | -- | -- | `str`, nullable=T |
| `citation_contexts` | -- | -- | -- | -- | `str`, nullable=T (JSON array) |
| `references` | -- | -- | `str`, nullable=T (JSON array) | -- | -- |
| `author_details` | -- | -- | `str`, nullable=T (JSON array) | -- | -- |
| `authors_with_affiliations` | -- | `str`, nullable=T (JSON array) | -- | -- | -- |
| `affiliation_structured` | -- | `str`, nullable=T (JSON array) | -- | -- | -- |

### 1.12 Provider-Specific Dates

| Field | CH | PM | CR | OA | S2 |
|-------|----|----|----|----|-----|
| `pub_month` | -- | `Int64`, nullable=T, check 1..12 | -- | -- | -- |
| `pub_day` | -- | `Int64`, nullable=T, check 1..31 | -- | -- | -- |
| `publication_status` | -- | `str`, nullable=T, isin={ppublish, epublish, aheadofprint} | -- | -- | -- |
| `date_completed` | -- | `datetime`, nullable=T | -- | -- | -- |
| `date_revised` | -- | `datetime`, nullable=T | -- | -- | -- |
| `published_print` | -- | -- | `str`, nullable=T (ISO) | -- | -- |
| `published_online` | -- | -- | `str`, nullable=T (ISO) | -- | -- |
| `published` | -- | -- | `str`, nullable=T (YYYY-MM-DD) | -- | -- |
| `citation_subset` | -- | `str`, nullable=T | -- | -- | -- |

### 1.13 Provider-Specific Counts (PubMed)

| Field | CH | PM | CR | OA | S2 |
|-------|----|----|----|----|-----|
| `author_count` | -- | `Int64`, nullable=T, check ge=0 | -- | -- | -- |
| `mesh_heading_count` | -- | `Int64`, nullable=T, check ge=0 | -- | -- | -- |
| `keyword_count` | -- | `Int64`, nullable=T, check ge=0 | -- | -- | -- |
| `grant_count` | -- | `Int64`, nullable=T, check ge=0 | -- | -- | -- |
| `chemical_count` | -- | `Int64`, nullable=T, check ge=0 | -- | -- | -- |

### 1.14 Provider-Specific Author IDs

| Field | CH | PM | CR | OA | S2 |
|-------|----|----|----|----|-----|
| `author_openalex_ids` | -- | -- | -- | `str`, nullable=T (JSON array) | -- |
| `author_s2_ids` | -- | -- | -- | -- | `str`, nullable=T (JSON array) |
| `author_h_indices` | -- | -- | -- | -- | `str`, nullable=T (JSON array) |

### 1.15 Provider-Specific Institutional

| Field | CH | PM | CR | OA | S2 |
|-------|----|----|----|----|-----|
| `institution_ids` | -- | -- | -- | `str`, nullable=T (JSON array) | -- |
| `institution_country_codes` | -- | -- | -- | `str`, nullable=T (JSON array) | -- |
| `ror_ids` | -- | -- | -- | `str`, nullable=T (JSON array) | -- |

### 1.16 Provider-Specific Quality

| Field | CH | PM | CR | OA | S2 |
|-------|----|----|----|----|-----|
| `is_retracted` | -- | -- | -- | `bool`, nullable=F | -- |
| `grants` | -- | -- | -- | `str`, nullable=T (JSON array) | -- |
| `license_url` | -- | -- | `str`, nullable=T | -- | -- |
| `content_domain_domains` | -- | -- | `object`, nullable=T | -- | -- |
| `content_domain_crossmark_restriction` | -- | -- | `bool`, nullable=T | -- | -- |
| `alternative_id` | -- | -- | `object`, nullable=T | -- | -- |

---

## 2. DQ Rules Comparison

### 2.1 DQ Thresholds

| Parameter | CH | PM | CR | OA | S2 |
|-----------|----|----|----|----|-----|
| Soft fail threshold | provider default | 0.05 (5%) | 0.10 (10%) | 0.08 (8%) | 0.15 (15%) |
| Hard fail threshold | provider default | 0.15 (15%) | 0.30 (30%) | 0.25 (25%) | 0.40 (40%) |

### 2.2 DQ Field Validations

| Field | CH | PM | CR | OA | S2 |
|-------|----|----|----|----|-----|
| **PK** | `document_chembl_id`: pattern `^CHEMBL\d+$`, nullable=F | `pmid`: range 1..10B, nullable=F | `doi`: pattern `^10\.\d{4,}/\S+$`, nullable=F | `openalex_id`: pattern `^W\d+$`, nullable=F | `paper_id`: pattern `^[a-f0-9]{40}$`, nullable=F |
| `pmid` | range 1..10B, nullable=T | *(PK, see above)* | -- | range 1..10B, nullable=T | range 1..10B, nullable=T |
| `doi` | pattern `^10\.\d{4,}/\S+$`, nullable=T | pattern `^10\.\d{4,}/\S+$`, nullable=T | *(PK, see above)* | pattern `^10\.\d{4,}/\S+$`, nullable=T | pattern `^10\.\d{4,}/\S+$`, nullable=T |
| `pmc_id` | -- | pattern `^PMC\d+$`, nullable=T | -- | -- | -- |
| `doc_type` / `type` | enum {PUBLICATION, BOOK, DATASET, PATENT}, nullable=T | enum {Journal Article, Review, ...}, nullable=T | enum {journal-article, book-chapter, ...}, nullable=T | enum {article, book-chapter, ...}, nullable=T | -- |
| `publication_year` | range 1500..2100, nullable=T | range 1500..2100, nullable=T | range 1500..2100, nullable=T | range 1500..2100, nullable=T | range 1500..2100, nullable=T |
| `title` (max_length) | max 2000, nullable=T | max 2000, nullable=T | max 2000, nullable=T | max 2000, nullable=T | max 2000, nullable=T |
| `title` (not_null) | severity=warn | severity=warn | severity=warn | severity=warn | severity=warn |
| `title` (not_empty) | pattern `\S`, severity=warn | pattern `\S`, severity=warn | pattern `\S`, severity=warn | pattern `\S`, severity=warn | pattern `\S`, severity=warn |
| `citations_received` | ge=0; warn if >10M | ge=0; warn if >10M | ge=0; warn if >10M | ge=0; warn if >10M | ge=0; warn if >10M |
| `citations_made` | ge=0 | ge=0 | ge=0 | ge=0 | ge=0 |
| `fwci` | -- | -- | -- | ge=0 | -- |
| `influential_citation_count` | -- | -- | -- | -- | ge=0 |

### 2.3 Cross-Field Validations

| Rule | CH | PM | CR | OA | S2 |
|------|----|----|----|----|-----|
| `publication_identifiable` | all_present: {document_chembl_id, title} | all_present: {pmid, title} | all_present: {doi, title} | all_present: {openalex_id, title} | all_present: {paper_id, title} |
| `has_cross_reference` | any_present: {pmid, doi}, severity=warn | any_present: {pmid, doi, pmc_id} | -- | -- | -- |

### 2.4 Conditional Validations

| Rule | CH | PM | CR | OA | S2 |
|------|----|----|----|----|-----|
| Title required by type | `doc_type`=PUBLICATION -> title not_null | -- | `type` in {journal-article, proceedings-article} -> title not_null | `type` in {article, review} -> title not_null | `publication_type`=JournalArticle -> title not_null |

---

## 3. Filter Rules Comparison

### 3.1 Gold Filters

| Parameter | CH | PM | CR | OA | S2 |
|-----------|----|----|----|----|-----|
| **publication_year range** | 1950..2050 | 1950..2050 | 1950..2050 | 1950..2050 | 1950..2050 |
| **Column filters** | doc_type=[PUBLICATION] | -- | -- | -- | -- |
| **Required fields** | document_chembl_id, doc_type, title | pmid, title | doi, title | openalex_id, title | paper_id, title |

### 3.2 Input Filters

| Parameter | CH | PM | CR | OA | S2 |
|-----------|----|----|----|----|-----|
| Source file | `data/input/publication.csv` | `data/input/pubmed.csv` | `data/input/dois.csv` | `data/input/dois.csv` | `data/input/dois.csv` |
| Filter column | `document_chembl_id` | `pubmed_id` | `doi` | `doi` | `doi` |
| Batch size | 16 | 100 | 50 | 50 | 100 |
| Fallback column | -- | `title` | `title` | `title` | `title` |

---

## 4. Fields With Same Name But Different Validation

This section identifies fields that share the same name across pipelines but have divergent validation rules. These are candidates for unification.

### 4.1 `title`

| Aspect | CH | PM | CR | OA | S2 |
|--------|----|----|----|----|-----|
| **Pandera nullable** | T | **F** | T | T | T |
| **DQ max_length** | 2000 | 2000 | 2000 | 2000 | 2000 |
| **DQ not_null severity** | warn | warn | warn | warn | warn |
| **DQ not_empty severity** | warn | warn | warn | warn | warn |
| **Conditional requirement** | Required when doc_type=PUBLICATION | -- (always required at schema level) | Required when type in {journal-article, proceedings-article} | Required when type in {article, review} | Required when publication_type=JournalArticle |
| **Gold filter required** | Yes | Yes | Yes | Yes | Yes |

**Divergence:** PubMed is the only provider where `title` is non-nullable at schema level. All others allow null but warn through DQ rules. Conditional requirement triggers differ by provider type vocabulary.

### 4.2 `publication_year`

| Aspect | CH | PM | CR | OA | S2 |
|--------|----|----|----|----|-----|
| **Pandera type** | `Int64` | `Int64` | `Int64` | `Int64` | `Int64` |
| **Pandera nullable** | T | T | T | T | T |
| **Pandera range** | 1500..2100 | 1500..2100 | 1500..2100 | 1500..2100 | 1500..2100 |
| **DQ range** | 1500..2100 | 1500..2100 | 1500..2100 | 1500..2100 | 1500..2100 |
| **Gold filter range** | 1950..2050 | 1950..2050 | 1950..2050 | 1950..2050 | 1950..2050 |

**Divergence:** Schema and DQ ranges are uniform (1500..2100). Gold filter ranges are also uniform (1950..2050). **Currently aligned.** However, the two-tier validation (schema allows 1500..2100, filter narrows to 1950..2050) applies consistently, so this field is effectively unified. No action needed.

### 4.3 `publication_type`

| Aspect | CH | PM | CR | OA | S2 |
|--------|----|----|----|----|-----|
| **Pandera type** | `str` | `str` | `str` | `str` | `str` |
| **Pandera constraint** | isin {PUBLICATION, PATENT, DATASET, BOOK} | no constraint (raw) | no constraint (raw CrossRef type) | no constraint (raw OpenAlex type) | no constraint (pipe-delimited) |
| **DQ field name** | `doc_type` | `pub_type` | `type` | `type` | `publication_type` |
| **DQ enum values** | {PUBLICATION, BOOK, DATASET, PATENT} | {Journal Article, Review, Letter, Editorial, Clinical Trial, Meta-Analysis, Case Reports, Comparative Study, Evaluation Study} | {journal-article, book-chapter, proceedings-article, posted-content, book, report, dataset, standard} | {article, book-chapter, book, dataset, dissertation, editorial, letter, review, preprint, other} | -- (no enum DQ) |
| **Conditional trigger field** | `doc_type` | -- | `type` | `type` | `publication_type` |
| **Conditional trigger values** | PUBLICATION | -- | journal-article, proceedings-article | article, review | JournalArticle |

**Divergence:** Significant. Each provider uses its own type vocabulary. The DQ config even references different field names (`doc_type`, `pub_type`, `type`). Enum values are provider-native and incompatible. The `publication_type_unified` and `publication_class` fields exist to bridge this gap, but the raw `publication_type` validation remains fragmented.

### 4.4 `pmid`

| Aspect | CH | PM | CR | OA | S2 |
|--------|----|----|----|----|-----|
| **Pandera type** | `str` | `str` | `str` | `str` | `str` |
| **Pandera nullable** | T | **F** | T | T | T |
| **Pandera pattern** | `^[1-9]\d*$` | `^[1-9]\d*$` | `^[1-9]\d*$` (base) | `^[1-9]\d*$` (base) | `^[1-9]\d*$` (base) |
| **DQ type** | range 1..10B | range 1..10B | -- | range 1..10B | range 1..10B |

**Divergence:** PubMed treats `pmid` as PK (non-nullable). ChEMBL has both schema pattern validation and DQ range check. CrossRef has no DQ rule for pmid at all (pmid is not part of CrossRef data). OpenAlex and S2 have DQ range validation.

### 4.5 `doi`

| Aspect | CH | PM | CR | OA | S2 |
|--------|----|----|----|----|-----|
| **Pandera nullable** | T | T | **F** | T | T |
| **Pandera pattern** | `^10\.\d{4,}/\S+$` | `^10\.\d{4,}/\S+$` | `^10\.\d{4,}/\S+$` | `^10\.\d{4,}/\S+$` (base) | `^10\.\d{4,}/\S+$` (base) |
| **DQ pattern** | `^10\.\d{4,}/\S+$` | `^10\.\d{4,}/\S+$` | `^10\.\d{4,}/\S+$` | `^10\.\d{4,}/\S+$` | `^10\.\d{4,}/\S+$` |
| **DQ nullable** | T | T | **F** | T | T |

**Divergence:** CrossRef treats `doi` as PK (non-nullable). Pattern validation is uniform across all providers. The nullability difference is structurally correct — each provider's PK should be non-nullable.

### 4.6 `_source`

| Aspect | CH | PM | CR | OA | S2 |
|--------|----|----|----|----|-----|
| **Pandera nullable** | F | F | F | F | F |
| **Pandera eq** | `chembl` | `pubmed` | `crossref` | `openalex` | `semanticscholar` |
| **Base default** | nullable=T, no eq constraint | -- | -- | -- | -- |

**Divergence:** Base schema defines `_source` as nullable=T without a fixed value. Each provider overrides to nullable=F with a provider-specific `eq` constraint. This is correct by design — no unification needed.

### 4.7 `citations_received`

| Aspect | CH | PM | CR | OA | S2 |
|--------|----|----|----|----|-----|
| **Pandera type** | `Int64` | `Int64` | `Int64` | `Int64` | `Int64` |
| **Pandera ge** | 0 | 0 | 0 | 0 | 0 |
| **DQ ge** | 0 | 0 | 0 | 0 | 0 |
| **DQ warn max** | 10M | 10M | 10M | 10M | 10M |

**Divergence:** None. Fully aligned across all providers.

### 4.8 `citations_made`

| Aspect | CH | PM | CR | OA | S2 |
|--------|----|----|----|----|-----|
| **Pandera type** | `Int64` | `Int64` | `Int64` | `Int64` | `Int64` |
| **Pandera ge** | 0 | 0 | 0 | 0 | 0 |
| **DQ ge** | 0 | 0 | 0 | 0 | 0 |

**Divergence:** None. Fully aligned across all providers.

### 4.9 `issn`

| Aspect | CH | PM | CR | OA | S2 |
|--------|----|----|----|----|-----|
| **Present** | No | Yes | Yes | Yes | No |
| **Pandera pattern** | -- | `^\d{4}-\d{3}[\dX]$` | `^\d{4}-\d{3}[\dX]$` | `^\d{4}-\d{3}[\dX]$` | -- |

**Divergence:** Same pattern where present. ChEMBL and S2 do not include ISSN.

### 4.10 `oa_status`

| Aspect | CH | PM | CR | OA | S2 |
|--------|----|----|----|----|-----|
| **Present** | No | No | No | Yes | Yes |
| **Pandera isin** | -- | -- | -- | {gold, green, hybrid, bronze, closed} | {gold, green, hybrid, bronze, closed} |

**Divergence:** Only OA and S2 provide this field. Values are aligned. No conflict.

### 4.11 `subject_keywords`

| Aspect | CH | PM | CR | OA | S2 |
|--------|----|----|----|----|-----|
| **Present** | No | Yes | Yes | Yes | No |
| **Pandera type** | -- | `str`, nullable=T (JSON array) | `str`, nullable=T (JSON array) | `str`, nullable=T (JSON array) | -- |

**Divergence:** Same schema definition where present. Semantic content may differ (author keywords vs subject areas vs topics), but validation is uniform.

### 4.12 `subject_mesh`

| Aspect | CH | PM | CR | OA | S2 |
|--------|----|----|----|----|-----|
| **Present** | No | Yes | No | Yes | No |
| **Pandera type** | -- | `str`, nullable=T (JSON array) | -- | `str`, nullable=T (JSON array) | -- |

**Divergence:** Same schema definition where present. PubMed provides descriptor/qualifier strings; OpenAlex provides descriptor names. JSON structure may differ, but Pandera validation is identical.

### 4.13 `volume`

| Aspect | CH | PM | CR | OA | S2 |
|--------|----|----|----|----|-----|
| **Present** | Yes | No | No | Yes | Yes |
| **Pandera type** | `str`, nullable=T | -- | -- | `str`, nullable=T | `str`, nullable=T |

**Divergence:** None where present.

### 4.14 `publication_types`

| Aspect | CH | PM | CR | OA | S2 |
|--------|----|----|----|----|-----|
| **Present** | No | Yes | No | No | Yes |
| **PM description** | -- | JSON array (e.g., Journal Article, Review) | -- | -- | JSON array |

**Divergence:** Same schema definition where present. Content vocabulary differs (PubMed MeSH types vs S2 types).

---

## 5. Unification Plan

### 5.1 `title` — Nullable Consistency

**Problem:** PubMed schema enforces `nullable=False` while all others use `nullable=True` + DQ warn.

**Proposed plan:**

1. **Change PubMed schema** to `nullable=True` (matching base and other providers).
2. **Rely on DQ warn** for missing title (already configured identically across all providers).
3. **Keep conditional validation** per provider (type-specific title requirement) — this is provider-native and correct.
4. **Gold filter** already enforces `title` as required field uniformly.

**Impact:** PubMed records without title will no longer fail schema validation but will be flagged by DQ warning and excluded by Gold filter. Aligns with other providers' behavior.

**Files to modify:**
- `src/bioetl/domain/schemas/pubmed/publication.py` — change `title` to `nullable=True`

### 5.2 `publication_type` — Vocabulary Normalization

**Problem:** Five different vocabularies for publication type, different DQ field names, incompatible enum values.

**Proposed plan:**

1. **Accept raw `publication_type` as free-form per provider** — do not enforce `isin` at schema level for raw type. This reflects API reality: each provider returns its own vocabulary.
2. **Remove `isin` constraint from ChEMBL schema override** — already done implicitly for CR/OA/S2; ChEMBL is the only one with `isin` on `publication_type` at schema level.
3. **Unify DQ config field name** — all DQ configs should reference `publication_type` (not `doc_type`, `pub_type`, or `type`). This requires updating:
   - `configs/dq/entities/chembl/publication.yaml`: rename `doc_type` → `publication_type`
   - `configs/dq/entities/pubmed/publication.yaml`: rename `pub_type` → `publication_type`
   - `configs/dq/entities/crossref/publication.yaml`: rename `type` → `publication_type`
   - `configs/dq/entities/openalex/publication.yaml`: rename `type` → `publication_type`
4. **Rely on `publication_type_unified` and `publication_class`** for cross-provider comparison. These fields (already in base schema) provide the canonical normalized vocabulary.
5. **Create a shared DQ rule template** for `publication_type` that validates against a unified enum at `publication_type_unified` level instead of raw type level.

**Impact:** DQ reports will use consistent field names. Raw type validation remains provider-specific (reflecting API reality). Cross-provider analysis uses unified fields.

**Files to modify:**
- `configs/dq/entities/chembl/publication.yaml`
- `configs/dq/entities/pubmed/publication.yaml`
- `configs/dq/entities/crossref/publication.yaml`
- `configs/dq/entities/openalex/publication.yaml`
- `src/bioetl/domain/schemas/chembl/publication.py` (relax `isin` on `publication_type`)

### 5.3 `pmid` — Nullability Alignment

**Problem:** PubMed treats `pmid` as PK (non-nullable); other providers treat it as optional cross-reference.

**Proposed plan:**

1. **Keep PubMed `pmid` as non-nullable** — this is correct: it is the PK for PubMed.
2. **No change needed** — the divergence is structurally sound. Each provider's PK is non-nullable; cross-references to other providers' PKs are nullable.
3. **Ensure DQ rules are consistent** for `pmid` as cross-reference: ChEMBL, OpenAlex, S2 all have range 1..10B. CrossRef has no pmid DQ rule (correct, since CrossRef doesn't provide PMID).

**Status: No action required.** Divergence is by design.

### 5.4 `doi` — Nullability Alignment

**Problem:** CrossRef treats `doi` as PK (non-nullable); other providers treat it as optional.

**Proposed plan:**

1. **Keep CrossRef `doi` as non-nullable** — this is correct: it is the PK for CrossRef.
2. **No change needed** — structurally sound.

**Status: No action required.** Divergence is by design.

### 5.5 `publication_type` DQ Conditional Validations — Trigger Unification

**Problem:** Each provider uses different field name and value for "journal article requires title" conditional validation.

| Provider | condition_field | condition_value |
|----------|----------------|-----------------|
| CH | `doc_type` | `PUBLICATION` |
| PM | -- | -- (schema-level non-nullable) |
| CR | `type` | `journal-article`, `proceedings-article` |
| OA | `type` | `article`, `review` |
| S2 | `publication_type` | `JournalArticle` |

**Proposed plan:**

1. **Unify condition_field** to `publication_type` across all DQ configs (consistent with schema field name after vocabulary unification in 5.2).
2. **Keep provider-specific condition_values** — these must match the raw provider vocabulary.
3. **Add PubMed conditional validation** — since PubMed title will become nullable (per 5.1), add a conditional rule:
   ```yaml
   - name: journal_article_requires_title
     condition_field: publication_type
     condition_value: Journal Article
     condition_operator: eq
     then_validations:
       - field: title
         type: not_null
         nullable: false
   ```
4. **Long-term:** Consider adding a conditional validation based on `publication_type_unified` (the normalized field) so that the same logical rule applies across all providers.

**Files to modify:**
- `configs/dq/entities/chembl/publication.yaml`
- `configs/dq/entities/pubmed/publication.yaml`
- `configs/dq/entities/crossref/publication.yaml`
- `configs/dq/entities/openalex/publication.yaml`
- `configs/dq/entities/semanticscholar/publication.yaml`

### 5.6 Cross-Field Validation — `has_cross_reference`

**Problem:** Only ChEMBL and PubMed have cross-reference validation. ChEMBL checks {pmid, doi}, PubMed checks {pmid, doi, pmc_id}. Other providers have no such rule.

**Proposed plan:**

1. **Add `has_cross_reference` to all providers** with provider-appropriate fields:
   - CH: any_present {pmid, doi} (keep as-is)
   - PM: any_present {pmid, doi, pmc_id} (keep as-is)
   - CR: any_present {pmid, pmc_id} — CrossRef already has DOI as PK, so check for additional identifiers
   - OA: any_present {doi, pmid, pmc_id} — OpenAlex has openalex_id as PK
   - S2: any_present {doi, pmid} — S2 has paper_id as PK
2. **Set severity=warn** for all (advisory, not blocking).
3. **Rationale:** Cross-references enable composite pipeline joins. Having at least one additional identifier improves enrichment success rate.

**Files to modify:**
- `configs/dq/entities/crossref/publication.yaml`
- `configs/dq/entities/openalex/publication.yaml`
- `configs/dq/entities/semanticscholar/publication.yaml`

### 5.7 Summary Priority Matrix

| # | Field | Severity | Effort | Priority |
|---|-------|----------|--------|----------|
| 5.1 | `title` nullable | Medium | Low | P1 |
| 5.2 | `publication_type` vocabulary | High | Medium | P1 |
| 5.3 | `pmid` nullable | -- | -- | No action |
| 5.4 | `doi` nullable | -- | -- | No action |
| 5.5 | Conditional validation trigger | Medium | Medium | P2 |
| 5.6 | Cross-reference validation | Low | Low | P3 |

---

## Appendix A: Validation Constants

| Constant | Value | Source |
|----------|-------|--------|
| `MIN_PUBLICATION_YEAR` | 1500 | `domain/validation.py` |
| `MAX_PUBLICATION_YEAR` | 2100 | `domain/validation.py` |
| `DOI_REGEX_PATTERN` | `^10\.\d{4,}/\S+$` | `domain/validation.py` |
| `CHEMBL_ID_PATTERN` | `^CHEMBL\d+$` | `domain/schemas/constants.py` |
| `ISSN_PATTERN` | `^\d{4}-\d{3}[\dX]$` | `domain/schemas/constants.py` |
| `ORCID_PATTERN` | `^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$` | `domain/schemas/constants.py` |
| Gold year filter | 1950..2050 | `configs/filter/entities/*/publication.yaml` |

## Appendix B: Source Files

| Provider | Schema | DQ Config | Filter Config |
|----------|--------|-----------|---------------|
| ChEMBL | `src/bioetl/domain/schemas/chembl/publication.py` | `configs/dq/entities/chembl/publication.yaml` | `configs/filter/entities/chembl/publication.yaml` |
| PubMed | `src/bioetl/domain/schemas/pubmed/publication.py` | `configs/dq/entities/pubmed/publication.yaml` | `configs/filter/entities/pubmed/publication.yaml` |
| CrossRef | `src/bioetl/domain/schemas/crossref/publication.py` | `configs/dq/entities/crossref/publication.yaml` | `configs/filter/entities/crossref/publication.yaml` |
| OpenAlex | `src/bioetl/domain/schemas/openalex/publication.py` | `configs/dq/entities/openalex/publication.yaml` | `configs/filter/entities/openalex/publication.yaml` |
| SemanticScholar | `src/bioetl/domain/schemas/semanticscholar/publication.py` | `configs/dq/entities/semanticscholar/publication.yaml` | `configs/filter/entities/semanticscholar/publication.yaml` |
| Base | `src/bioetl/domain/schemas/common/publication_base.py` | -- | -- |
