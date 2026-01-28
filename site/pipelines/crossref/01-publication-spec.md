# CrossRef Publication Pipeline Specification

*Version 1.1.0 | Aligned with RULES.md v5.14*

---

## 1. Identification

| Parameter | Value |
|-----------|-------|
| **Pipeline ID** | `crossref_publication` |
| **Provider** | CrossRef |
| **Entity** | publication |
| **API Endpoint** | `https://api.crossref.org/works/` |
| **Library** | `httpx` (REST API) |
| **Rate Limit** | 50 req/sec (polite pool with mailto) |
| **Health Check** | `/works?rows=1` |
| **Auth Type** | None (mailto header for polite pool) |

---

## 2. Business Context

### 2.1. Entity Purpose

CrossRef provides **authoritative DOI metadata**:

- **DOI resolution**: Canonical metadata for publications
- **Citation data**: Reference counts and cited-by counts
- **Funder information**: Grant and funding data
- **License data**: Open access and usage rights
- **Type classification**: Article, preprint, book chapter, etc.

### 2.2. Use Cases

1. **DOI Enrichment**: Add metadata to ChEMBL documents by DOI
2. **Citation Analysis**: Track citation counts
3. **Funder Analysis**: Identify funding sources
4. **Open Access Tracking**: Determine OA status

---

## 3. Extraction (Bronze Layer)

### 3.1. API Request

```python
import httpx

# Single DOI lookup
url = f"https://api.crossref.org/works/{doi}"
headers = {"User-Agent": "BioETL/1.0 (mailto:email@example.com)"}
response = await client.get(url, headers=headers)
```

### 3.2. Complete API Fields

| # | API Field | JSON Type | Nullable | Description |
|---|-----------|-----------|----------|-------------|
| 1 | `DOI` | string | No | Primary key |
| 2 | `title` | array | Yes | Title(s) |
| 3 | `author` | array | Yes | Authors |
| 4 | `container-title` | array | Yes | Journal name(s) |
| 5 | `publisher` | string | Yes | Publisher |
| 6 | `published-print` | object | Yes | Print date |
| 7 | `published-online` | object | Yes | Online date |
| 8 | `volume` | string | Yes | Volume |
| 9 | `issue` | string | Yes | Issue |
| 10 | `page` | string | Yes | Page range |
| 11 | `type` | string | Yes | Work type |
| 12 | `ISSN` | array | Yes | ISSNs |
| 13 | `subject` | array | Yes | Subjects |
| 14 | `abstract` | string | Yes | Abstract (HTML) |
| 15 | `is-referenced-by-count` | int | Yes | Cited by count |
| 16 | `references-count` | int | Yes | Reference count |
| 17 | `license` | array | Yes | License info |
| 18 | `funder` | array | Yes | Funders |
| 19 | `link` | array | Yes | Links |
| 20 | `language` | string | Yes | Language code |

---

## 4. Transformation

### 4.1. Entity ID Strategy

| Parameter | Value |
|-----------|-------|
| **Entity ID Field** | `doi` |
| **ID Source** | `from_api` |
| **Format** | DOI (10.xxx/yyy) |

### 4.2. Field Normalization

| Field | Normalization | Before | After |
|-------|---------------|--------|-------|
| `doi` | lowercase, strip | `"10.1234/ABC "` | `"10.1234/abc"` |
| `title` | Extract first | `["Title 1"]` | `"Title 1"` |
| `author` | Format names | `[{given, family}]` | JSON array |
| `container-title` | Extract first | `["Journal"]` | `"Journal"` |
| `page` | Split to first/last | `"123-456"` | first=123, last=456 |
| `published-print.date-parts` | Parse to date | `[[2024,1,15]]` | `"2024-01-15"` |
| `abstract` | Strip HTML | `"<p>Text</p>"` | `"Text"` |

### 4.3. Flattening Strategy

| Nested Path | Flattened Name | Strategy |
|-------------|----------------|----------|
| `title[0]` | `title` | Extract first |
| `container-title[0]` | `journal` | Extract first |
| `author[*]` | `authors` | JSON array |
| `published-print.date-parts[0]` | `year`, `published_print` | Parse |
| `published-online.date-parts[0]` | `published_online` | Parse |
| `ISSN` | `issn` | JSON array |
| `subject` | `subjects` | JSON array |
| `funder[*]` | `funders` | JSON array (separate table option) |
| `license[0].URL` | `license_url` | Extract first |

---

## 5. Validation

### 5.1. Pandera Schema

```python
class PublicationEnrichedSchema(ETLRecordSchema):
    """CrossRef-enriched Publication validation schema."""

    # === Primary Key ===
    doi: Series[str] = pa.Field(
        nullable=False,
        str_matches=DOI_REGEX_PATTERN,
    )

    # === Core Metadata ===
    title: Series[str] | None = pa.Field(nullable=True, str_length={"min_value": 1})
    abstract: Series[str] | None = pa.Field(nullable=True)

    # === Authors ===
    authors: Series[str] | None = pa.Field(nullable=True)  # JSON array

    # === Journal Information ===
    journal: Series[str] | None = pa.Field(nullable=True)
    issn: Series[str] | None = pa.Field(nullable=True)  # JSON array
    publisher: Series[str] | None = pa.Field(nullable=True)

    # === Publication Details ===
    volume: Series[str] | None = pa.Field(nullable=True)
    issue: Series[str] | None = pa.Field(nullable=True)
    first_page: Series[str] | None = pa.Field(nullable=True)
    last_page: Series[str] | None = pa.Field(nullable=True)

    # === Dates ===
    year: Series[int] | None = pa.Field(
        nullable=True,
        ge=MIN_PUBLICATION_YEAR,
        le=MAX_PUBLICATION_YEAR,
    )
    published_print: Series[str] | None = pa.Field(nullable=True)
    published_online: Series[str] | None = pa.Field(nullable=True)

    # === Document Type ===
    doc_type: Series[str] = pa.Field(
        nullable=False,
        isin=["PUBLICATION", "PREPRINT"],
    )

    # === Citation Metrics ===
    citation_count: Series[int] | None = pa.Field(nullable=True, ge=0)
    reference_count: Series[int] | None = pa.Field(nullable=True, ge=0)

    # === Additional Metadata ===
    language: Series[str] | None = pa.Field(nullable=True)
    license_url: Series[str] | None = pa.Field(nullable=True)
    subjects: Series[str] | None = pa.Field(nullable=True)  # JSON array

    # === Source Tracking ===
    source: Series[str] = pa.Field(nullable=False, eq="crossref")

    class Config:
        strict = True
        ordered = True
        coerce = True
```

---

## 6. Cross-Provider Mapping

| This Entity Field | Maps To | Provider | Field |
|-------------------|---------|----------|-------|
| `doi` | ChEMBL | ChEMBL | `document.doi` |
| `doi` | OpenAlex | OpenAlex | `doi` |
| `doi` | Semantic Scholar | S2 | `externalIds.DOI` |
| `doi` | PubMed | PubMed | ArticleIdList/DOI |

---

## 7. Pipeline Configuration

```yaml
pipeline_name: crossref_publication
provider: crossref
entity_type: publication
version: "1.1.0"

primary_keys: ["doi"]
silver_table: "crossref_publication"
gold_table: "crossref_publication"

source:
  type: api
  batch_size: 50

sink:
  bronze:
    path: "data/output/bronze"
  silver:
    path: "data/output/silver"
    primary_key: ["doi"]
    partition_by: []
  gold:
    path: "data/output/gold"

gold_filters:
  required_fields:
    - title
  columns:
    doc_type: [PUBLICATION]

input_filter:
  enabled: true
  source_path: "data/input/doi.csv"
  column_name: "doi"
  filter_field: "doi"
  batch_size: 50
```

---

## 8. Special Considerations

### 8.1. Polite Pool

```python
# Use mailto header for higher rate limits
headers = {
    "User-Agent": "BioETL/1.0 (mailto:admin@example.com)"
}
```

### 8.2. Rate Limiting

- Without mailto: ~1 req/sec
- With mailto: ~50 req/sec
- Implement exponential backoff for 429 responses
