# PubMed Publication Pipeline Specification

*Version 1.1.0 | Aligned with RULES.md v5.14*

---

## 1. Identification

| Parameter | Value |
|-----------|-------|
| **Pipeline ID** | `pubmed_publication` |
| **Provider** | PubMed (NCBI) |
| **Entity** | publication |
| **API Endpoint** | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/` |
| **Library** | `httpx` (E-utilities API) |
| **Rate Limit** | 3 req/sec (10 with API key) |
| **Health Check** | `/einfo.fcgi` |
| **Auth Type** | API Key (NCBI_API_KEY) |

---

## 2. Business Context

### 2.1. Entity Purpose

PubMed publications are **biomedical literature** with MeSH indexing:

- **MEDLINE citations**: Curated biomedical literature
- **MeSH terms**: Medical Subject Headings for categorization
- **Author affiliations**: Institution data
- **Grant information**: Funding sources
- **Cross-database links**: DOI, PMC, ChEMBL

### 2.2. Use Cases

1. **Literature Mining**: Search biomedical publications
2. **MeSH-based Filtering**: Find papers by medical terms
3. **Citation Enrichment**: Add metadata to ChEMBL documents
4. **Funding Analysis**: Track grant-supported research

---

## 3. Extraction (Bronze Layer)

### 3.1. API Request

```python
import httpx

# Step 1: Search for PMIDs (esearch)
search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
params = {
    "db": "pubmed",
    "term": f"{pmid}[uid]",
    "retmode": "json",
    "api_key": api_key
}

# Step 2: Fetch full records (efetch)
fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
params = {
    "db": "pubmed",
    "id": ",".join(pmids),
    "rettype": "xml",
    "retmode": "xml",
    "api_key": api_key
}
```

### 3.2. Complete API Fields (from XML)

| # | XML Path | Type | Nullable | Description |
|---|----------|------|----------|-------------|
| 1 | `PMID` | int | No | PubMed ID (PK) |
| 2 | `ArticleTitle` | str | No | Title |
| 3 | `Abstract/AbstractText` | str | Yes | Abstract |
| 4 | `AuthorList/Author` | array | Yes | Authors |
| 5 | `Journal/Title` | str | Yes | Journal name |
| 6 | `Journal/ISOAbbreviation` | str | Yes | ISO abbreviation |
| 7 | `Journal/ISSN` | str | Yes | ISSN |
| 8 | `PubDate/Year` | int | Yes | Publication year |
| 9 | `PubDate/Month` | str | Yes | Publication month |
| 10 | `Volume` | str | Yes | Volume |
| 11 | `Issue` | str | Yes | Issue |
| 12 | `MedlinePgn` | str | Yes | Page numbers |
| 13 | `ArticleIdList/DOI` | str | Yes | DOI |
| 14 | `ArticleIdList/PMC` | str | Yes | PMC ID |
| 15 | `MeshHeadingList` | array | Yes | MeSH terms |
| 16 | `KeywordList` | array | Yes | Keywords |
| 17 | `PublicationTypeList` | array | Yes | Publication types |
| 18 | `Language` | str | Yes | Language code |
| 19 | `GrantList` | array | Yes | Grants |

---

## 4. Transformation

### 4.1. Entity ID Strategy

| Parameter | Value |
|-----------|-------|
| **Entity ID Field** | `pmid` |
| **ID Source** | `from_api` |
| **Format** | Integer (positive) |

### 4.2. XML Parsing Notes

PubMed returns XML. Key transformations:

| XML Element | Silver Field | Transformation |
|-------------|--------------|----------------|
| `PMID` | `pmid` | Parse as int |
| `Abstract/AbstractText[@Label]` | `abstract_structured` | Check for structured |
| `AuthorList/Author/ForeName + LastName` | `authors` | Concatenate |
| `MeshHeadingList/MeshHeading` | `mesh_headings` | JSON array |
| `PubDate/Year + Month + Day` | `publication_date` | Parse to date |

---

## 5. Validation

### 5.1. Pandera Schema

```python
class ArticleSchema(ETLRecordSchema):
    """PubMed Article validation schema for Silver layer."""

    # === Primary Key ===
    pmid: Series[int] = pa.Field(nullable=False, ge=1)

    # === External Identifiers ===
    doi: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=DOI_REGEX_PATTERN,
    )
    pmc_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^PMC\d+$",
    )

    # === Article Content ===
    title: Series[str] = pa.Field(nullable=False, str_length={"min_value": 1})
    abstract: Series[str] | None = pa.Field(nullable=True)
    abstract_structured: Series[bool] | None = pa.Field(nullable=True)
    vernacular_title: Series[str] | None = pa.Field(nullable=True)
    language: Series[str] | None = pa.Field(nullable=True)

    # === Journal Information ===
    journal_title: Series[str] | None = pa.Field(nullable=True)
    journal_iso_abbrev: Series[str] | None = pa.Field(nullable=True)
    journal_issn: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^\d{4}-\d{3}[\dX]$",
    )
    country: Series[str] | None = pa.Field(nullable=True)

    # === Publication Details ===
    volume: Series[str] | None = pa.Field(nullable=True)
    issue: Series[str] | None = pa.Field(nullable=True)
    medline_pgn: Series[str] | None = pa.Field(nullable=True)
    year: Series[int] | None = pa.Field(
        nullable=True,
        ge=MIN_PUBLICATION_YEAR,
        le=MAX_PUBLICATION_YEAR,
    )
    pub_month: Series[int] | None = pa.Field(nullable=True, ge=1, le=12)
    pub_day: Series[int] | None = pa.Field(nullable=True, ge=1, le=31)
    publication_status: Series[str] | None = pa.Field(
        nullable=True,
        isin=["ppublish", "epublish", "aheadofprint"],
    )

    # === Dates ===
    date_completed: Series[date] | None = pa.Field(nullable=True)
    date_revised: Series[date] | None = pa.Field(nullable=True)

    # === Counts ===
    author_count: Series[int] | None = pa.Field(nullable=True, ge=0)
    mesh_heading_count: Series[int] | None = pa.Field(nullable=True, ge=0)
    keyword_count: Series[int] | None = pa.Field(nullable=True, ge=0)
    grant_count: Series[int] | None = pa.Field(nullable=True, ge=0)
    reference_count: Series[int] | None = pa.Field(nullable=True, ge=0)

    class Config:
        strict = True
        ordered = True
        coerce = True
```

---

## 6. Cross-Provider Mapping

| This Entity Field | Maps To | Provider | Field |
|-------------------|---------|----------|-------|
| `pmid` | ChEMBL | ChEMBL | `document.pubmed_id` |
| `doi` | CrossRef | CrossRef | `DOI` |
| `doi` | OpenAlex | OpenAlex | `doi` |
| `pmc_id` | PMC | PMC | PMCID |

---

## 7. Pipeline Configuration

```yaml
pipeline_name: pubmed_publication
provider: pubmed
entity_type: publications
version: "1.1.0"

primary_keys: ["pmid"]
silver_table: "pubmed_publication"
gold_table: "pubmed_publication"

source:
  type: api
  batch_size: 200  # E-utilities limit

dq_rules:
  soft_fail_threshold: 0.05
  hard_fail_threshold: 0.20

sink:
  bronze:
    path: "data/output/bronze"
  silver:
    path: "data/output/silver"
    primary_key: ["pmid"]
    partition_by: []
  gold:
    path: "data/output/gold"

gold_filters:
  required_fields:
    - title

input_filter:
  enabled: true
  source_path: "data/input/pubmed.csv"
  column_name: "pmid"
  filter_field: "pmid"
  batch_size: 200
```

---

## 8. Special Considerations

### 8.1. API Key Configuration

```bash
# Environment variable
export NCBI_API_KEY=your_api_key

# Increases rate limit from 3 to 10 req/sec
```

### 8.2. XML Parsing

- Use robust XML parser (lxml)
- Handle missing elements gracefully
- Extract structured abstracts by Label attribute
