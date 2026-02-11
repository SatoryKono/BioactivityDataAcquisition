# Semantic Scholar Publication Pipeline Specification

*Version 1.2.0 | Aligned with RULES.md v5.17*

---

## 1. Identification

| Parameter | Value |
|-----------|-------|
| **Pipeline ID** | `semanticscholar_publication` |
| **Provider** | Semantic Scholar |
| **Entity** | publication (paper) |
| **API Endpoint** | `https://api.semanticscholar.org/graph/v1/paper/` |
| **Library** | `httpx` (REST API) |
| **Rate Limit** | 100 req/5min (public), higher with API key |
| **Health Check** | `/paper/search?query=test&limit=1` |
| **Auth Type** | API Key (recommended) |

---

## 2. Business Context

### 2.1. Entity Purpose

Semantic Scholar provides **AI-enhanced academic data**:

- **Paper metadata**: Titles, abstracts, authors
- **Citation graph**: References and citations with context
- **TLDR summaries**: AI-generated paper summaries
- **Influential citations**: Quality-weighted citation metrics
- **Fields of Study**: AI-assigned research areas

### 2.2. Use Cases

1. **Citation Impact**: Track influential citations (not just counts)
2. **TLDR Summaries**: Quick paper understanding
3. **Research Area Analysis**: Classify by fields of study
4. **Cross-Database Linking**: Maps to DOI, PubMed, arXiv

---

## 3. Extraction (Bronze Layer)

### 3.1. API Request

```python
import httpx

# By Paper ID
url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}"

# By DOI
url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"

# By PubMed ID
url = f"https://api.semanticscholar.org/graph/v1/paper/PMID:{pmid}"

# Common params
params = {
    "fields": "paperId,corpusId,externalIds,title,abstract,tldr,"
              "year,referenceCount,citationCount,influentialCitationCount,"
              "isOpenAccess,openAccessPdf,fieldsOfStudy,s2FieldsOfStudy,"
              "publicationTypes,publicationDate,journal,authors"
}
headers = {"x-api-key": api_key}  # Optional but recommended
```

### 3.2. Complete API Fields

| # | API Field | JSON Type | Nullable | Description |
|---|-----------|-----------|----------|-------------|
| 1 | `paperId` | string | No | S2 Paper ID (40-char hex) |
| 2 | `corpusId` | int | Yes | S2 Corpus ID |
| 3 | `externalIds` | object | Yes | External IDs (DOI, PMID, etc.) |
| 4 | `title` | string | Yes | Paper title |
| 5 | `abstract` | string | Yes | Abstract text |
| 6 | `tldr` | object | Yes | AI-generated summary |
| 7 | `year` | int | Yes | Publication year |
| 8 | `referenceCount` | int | Yes | Number of references |
| 9 | `citationCount` | int | Yes | Number of citations |
| 10 | `influentialCitationCount` | int | Yes | Influential citations |
| 11 | `isOpenAccess` | boolean | Yes | OA flag |
| 12 | `openAccessPdf` | object | Yes | OA PDF info |
| 13 | `fieldsOfStudy` | array | Yes | Research fields |
| 14 | `s2FieldsOfStudy` | array | Yes | S2-specific fields |
| 15 | `publicationTypes` | array | Yes | Publication types |
| 16 | `publicationDate` | string | Yes | Full date |
| 17 | `journal` | object | Yes | Journal info |
| 18 | `authors` | array | Yes | Author list |

### 3.3. Nested Structure: externalIds

| Field | Type | Description |
|-------|------|-------------|
| `DOI` | string | DOI |
| `PubMed` | string | PubMed ID |
| `PMCID` | string | PMC ID |
| `ArXiv` | string | arXiv ID |
| `MAG` | string | Microsoft Academic Graph ID |
| `CorpusId` | int | S2 Corpus ID |

### 3.4. Nested Structure: tldr

| Field | Type | Description |
|-------|------|-------------|
| `model` | string | Model used |
| `text` | string | TLDR summary text |

### 3.5. Nested Structure: journal

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Journal name |
| `volume` | string | Volume |
| `pages` | string | Page range |

---

## 4. Transformation

### 4.1. Entity ID Strategy

| Parameter | Value |
|-----------|-------|
| **Entity ID Field** | `paper_id` |
| **ID Source** | `from_api` |
| **Format** | 40-character hex string |

### 4.2. Flattening Strategy

| Nested Path | Flattened Name | Strategy |
|-------------|----------------|----------|
| `paperId` | `paper_id` | Direct |
| `externalIds.DOI` | `doi` | Extract |
| `externalIds.PubMed` | `pmid` | Extract |
| `externalIds.PMCID` | `pmcid` | Extract |
| `externalIds.ArXiv` | `arxiv_id` | Extract |
| `tldr.text` | `tldr` | Extract |
| `journal.name` | `journal` | Extract |
| `journal.volume` | `volume` | Extract |
| `journal.pages` | `pages` | Extract |
| `openAccessPdf.url` | `open_access_url` | Extract |
| `fieldsOfStudy` | `fields_of_study` | JSON array |
| `publicationTypes` | `publication_types` | JSON array |
| `authors[*]` | `authors` | JSON array |

---

## 5. Validation

### 5.1. Pandera Schema

```python
class SemanticScholarPublicationSchema(ETLRecordSchema):
    """Semantic Scholar Publication validation schema."""

    # === Primary Key ===
    paper_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^[a-f0-9]{40}$",
    )

    # === External Identifiers ===
    doi: Series[str] = pa.Field(
        nullable=True,
        str_matches=DOI_REGEX_PATTERN,
    )
    pmid: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^\d+$",
    )
    pmcid: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^PMC\d+$",
    )
    arxiv_id: Series[str] = pa.Field(nullable=True)
    corpus_id: Series[int] = pa.Field(nullable=True, ge=0)

    # === Core Fields ===
    title: Series[str] = pa.Field(nullable=True)
    abstract: Series[str] = pa.Field(nullable=True)
    tldr: Series[str] = pa.Field(nullable=True)
    year: Series[int] = pa.Field(
        nullable=True,
        ge=MIN_PUBLICATION_YEAR,
        le=MAX_PUBLICATION_YEAR,
    )
    publication_date: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^\d{4}-\d{2}-\d{2}$",
    )

    # === Journal/Venue ===
    journal: Series[str] = pa.Field(nullable=True)
    volume: Series[str] = pa.Field(nullable=True)
    pages: Series[str] = pa.Field(nullable=True)
    venue: Series[str] = pa.Field(nullable=True)

    # === Metrics ===
    citation_count: Series[int] = pa.Field(nullable=True, ge=0)
    reference_count: Series[int] = pa.Field(nullable=True, ge=0)

    # === Open Access ===
    is_oa: Series[bool] = pa.Field(nullable=True)
    open_access_url: Series[str] = pa.Field(nullable=True)
    oa_status: Series[str] = pa.Field(
        nullable=True,
        isin=["gold", "green", "hybrid", "bronze", "closed"],
    )

    # === Classification ===
    fields_of_study: Series[str] = pa.Field(nullable=True)  # JSON
    publication_types: Series[str] = pa.Field(nullable=True)  # JSON

    # === Authors ===
    authors: Series[str] = pa.Field(nullable=True)  # JSON

    # === Source Tracking ===
    source: Series[str] = pa.Field(
        nullable=False,
        eq="semanticscholar",
    )

    # === Lookup Metadata ===
    lookup_method: Series[str] = pa.Field(
        alias="_lookup_method",
        nullable=False,
        isin=["doi", "title_fallback", "title_only", "unknown"],
    )
    original_doi: Series[str] = pa.Field(
        alias="_original_doi",
        nullable=True,
    )

    class Config:
        strict = "filter"
        coerce = True
```

---

## 6. Cross-Provider Mapping

| This Entity Field | Maps To | Provider | Field |
|-------------------|---------|----------|-------|
| `doi` | ChEMBL | ChEMBL | `document.doi` |
| `doi` | CrossRef | CrossRef | `DOI` |
| `doi` | OpenAlex | OpenAlex | `doi` |
| `pmid` | PubMed | PubMed | `pmid` |
| `arxiv_id` | arXiv | arXiv | ID |

---

## 7. Pipeline Configuration

```yaml
pipeline_name: semanticscholar_publication
provider: semanticscholar
entity_type: publication
version: "1.2.0"

primary_keys: ["paper_id"]
silver_table: "semanticscholar_publication"
gold_table: "semanticscholar_publication"

source:
  type: api
  batch_size: 100

sink:
  bronze:
    path: "data/output/bronze"
  silver:
    path: "data/output/silver"
    primary_key: ["paper_id"]
    partition_by: []
  gold:
    path: "data/output/gold"

gold_filters:
  required_fields:
    - title

input_filter:
  enabled: true
  source_path: "data/input/doi.csv"
  column_name: "doi"
  filter_field: "doi"
  batch_size: 100
```

---

## 8. Special Considerations

### 8.1. Rate Limiting

- **Public**: 100 requests per 5 minutes
- **With API key**: Higher limits (varies)
- **Batch endpoint**: Use for multiple papers

### 8.2. Batch Requests

```python
# Batch lookup (up to 500 papers)
url = "https://api.semanticscholar.org/graph/v1/paper/batch"
body = {"ids": paper_ids}
params = {"fields": "paperId,title,abstract,..."}
```

### 8.3. DOI Resolution Fallback

When DOI lookup fails, try other identifiers or title search.
