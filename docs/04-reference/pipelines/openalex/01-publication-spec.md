# OpenAlex Publication Pipeline Specification

*Version 1.2.0 | Aligned with RULES.md v5.20*

---

## 1. Identification

| Parameter | Value |
|-----------|-------|
| **Pipeline ID** | `openalex-publication` |
| **Provider** | OpenAlex |
| **Entity** | publication (works) |
| **API Endpoint** | `https://api.openalex.org/works` |
| **Library** | `httpx` (REST API) |
| **Rate Limit** | 10 req/sec (polite pool) |
| **Health Check** | `/works?per-page=1` |
| **Auth Type** | API Key (email-based, optional) |

---

## 2. Business Context

### 2.1. Entity Purpose

OpenAlex provides **comprehensive academic metadata**:

- **Works catalog**: 250M+ academic works
- **Concepts**: AI-assigned topic classifications
- **Institutions**: Author affiliations
- **Open Access data**: OA status and locations
- **Citation networks**: References and cited-by

### 2.2. Use Cases

1. **DOI Enrichment**: Add concepts and OA data to publications
2. **Concept Classification**: Categorize publications by topics
3. **Institution Analysis**: Track research by institution
4. **Open Access Tracking**: Monitor OA status

---

## 3. Extraction (Bronze Layer)

### 3.1. API Request

```python
import httpx

# By DOI
url = f"https://api.openalex.org/works/doi:{doi}"

# By OpenAlex ID
url = f"https://api.openalex.org/works/{openalex-id}"

# Batch search
url = "https://api.openalex.org/works"
params = {
    "filter": f"doi:{doi1}|{doi2}|{doi3}",
    "per-page": 200
}
```

### 3.2. Complete API Fields

| # | API Field | JSON Type | Nullable | Description |
|---|-----------|-----------|----------|-------------|
| 1 | `id` | string | No | OpenAlex ID (W[0-9]+) |
| 2 | `doi` | string | Yes | DOI |
| 3 | `title` | string | Yes | Title |
| 4 | `display-name` | string | Yes | Display name |
| 5 | `publication-year` | int | Yes | Year |
| 6 | `publication-date` | string | Yes | Full date |
| 7 | `type` | string | Yes | Work type |
| 8 | `cited-by-count` | int | Yes | Citation count |
| 9 | `is-oa` | boolean | Yes | Open access flag |
| 10 | `is-retracted` | boolean | Yes | Retracted flag |
| 11 | `open-access` | object | Yes | OA details |
| 12 | `authorships` | array | Yes | Authors with affiliations |
| 13 | `concepts` | array | Yes | Topic concepts |
| 14 | `primary-location` | object | Yes | Primary source |
| 15 | `biblio` | object | Yes | Bibliographic info |
| 16 | `abstract-inverted-index` | object | Yes | Abstract (inverted) |
| 17 | `language` | string | Yes | Language code |

### 3.3. Nested Structure: authorships

| Field | Type | Description |
|-------|------|-------------|
| `author.id` | string | Author OpenAlex ID |
| `author.display-name` | string | Author name |
| `author.orcid` | string | ORCID |
| `institutions[*].id` | string | Institution IDs |
| `institutions[*].display-name` | string | Institution names |
| `raw-affiliation-string` | string | Raw affiliation |

### 3.4. Nested Structure: concepts

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Concept OpenAlex ID |
| `display-name` | string | Concept name |
| `level` | int | Hierarchy level (0-5) |
| `score` | float | Relevance score (0-1) |

### 3.5. Nested Structure: primary-location

| Field | Type | Description |
|-------|------|-------------|
| `source.id` | string | Source OpenAlex ID |
| `source.display-name` | string | Journal/venue name |
| `source.issn-l` | string | ISSN-L |
| `pdf-url` | string | PDF URL |
| `landing-page-url` | string | Landing page |

---

## 4. Transformation

### 4.1. Entity ID Strategy

| Parameter | Value |
|-----------|-------|
| **Entity ID Field** | `openalex-id` |
| **ID Source** | `from-api` |
| **Format** | OpenAlex ID (W[0-9]+) |

### 4.2. Abstract Reconstruction

OpenAlex stores abstracts as inverted index. Reconstruction:

```python
def reconstruct-abstract(inverted-index: dict) -> str:
    if not inverted-index:
        return None

    # Create word position mapping
    positions = {}
    for word, indices in inverted-index.items():
        for idx in indices:
            positions[idx] = word

    # Reconstruct in order
    return " ".join(
        positions[i] for i in sorted(positions.keys())
    )
```

### 4.3. Flattening Strategy

| Nested Path | Flattened Name | Strategy |
|-------------|----------------|----------|
| `id` | `openalex-id` | Extract (strip URL prefix) |
| `open-access.is-oa` | `is-oa` | Extract boolean |
| `open-access.oa-status` | `oa-status` | Extract string |
| `primary-location.source.display-name` | `journal` | Extract |
| `primary-location.source.issn-l` | `issn` | Extract |
| `biblio.volume` | `volume` | Extract |
| `biblio.issue` | `issue` | Extract |
| `authorships[*]` | `authors` | JSON array |
| `concepts[*]` | `concepts` | JSON array |
| `abstract-inverted-index` | `abstract` | Reconstruct |

---

## 5. Validation

### 5.1. Pandera Schema

```python
class OpenAlexPublicationSchema(ETLRecordSchema):
    """OpenAlex Publication validation schema."""

    # === Primary Key ===
    openalex-id: Series[str] = pa.Field(
        nullable=False,
        str-matches=r"^W\d+$",
    )

    # === Core Fields ===
    doi: Series[str] = pa.Field(
        nullable=True,
        str-matches=DOI-REGEX-PATTERN,
    )
    title: Series[str] = pa.Field(nullable=True)
    abstract: Series[str] = pa.Field(nullable=True)
    year: Series[pd.Int64Dtype] = pa.Field(
        nullable=True,
        ge=MIN-PUBLICATION-YEAR,
        le=MAX-PUBLICATION-YEAR,
    )
    publication-date: Series[str] = pa.Field(
        nullable=True,
        str-matches=r"^\d{4}-\d{2}-\d{2}$",
    )
    doc-type: Series[str] = pa.Field(nullable=False)

    # === Journal ===
    journal: Series[str] = pa.Field(nullable=True)
    issn: Series[str] = pa.Field(nullable=True)
    publisher: Series[str] = pa.Field(nullable=True)

    # === Open Access ===
    is-oa: Series[bool] = pa.Field(nullable=True)
    oa-status: Series[str] = pa.Field(
        nullable=True,
        isin=["gold", "green", "hybrid", "bronze", "closed"],
    )

    # === Metrics ===
    citation-count: Series[pd.Int64Dtype] = pa.Field(
        nullable=True,
        ge=0,
    )

    # === Metadata ===
    language: Series[str] = pa.Field(nullable=True)
    source: Series[str] = pa.Field(nullable=False)

    # === Lookup Metadata ===
    lookup-method: Series[str] = pa.Field(
        alias="-lookup-method",
        nullable=False,
        isin=["doi", "title-fallback", "title-only", "unknown"],
    )
    original-doi: Series[str] = pa.Field(
        alias="-original-doi",
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
| `doi` | Semantic Scholar | S2 | `externalIds.DOI` |
| `openalex-id` | OpenAlex Works | OpenAlex | `id` |

---

## 7. Pipeline Configuration

```yaml
pipeline-name: openalex-publication
provider: openalex
entity-type: publication
version: "1.2.0"

primary-keys: ["openalex-id"]
silver-table: "openalex-publication"
gold-table: "openalex-publication"

source:
  type: api
  batch-size: 50

sink:
  bronze:
    path: "data/output/bronze"
  silver:
    path: "data/output/silver"
    primary-key: ["openalex-id"]
    partition-by: []
  gold:
    path: "data/output/gold"

gold-filters:
  required-fields:
    - title

input-filter:
  enabled: true
  source-path: "data/input/doi.csv"
  column-name: "doi"
  filter-field: "doi"
  batch-size: 50
```

---

## 8. Special Considerations

### 8.1. Polite Pool

```python
# Use email for higher rate limits
params = {"mailto": "admin@example.com"}
```

### 8.2. DOI vs Title Fallback

When DOI lookup fails, try title-based search:

```python
if not result:
    # Fallback to title search
    url = "https://api.openalex.org/works"
    params = {"filter": f"title.search:{title}"}
    result = await client.get(url, params=params)
    # Mark as title-fallback in -lookup-method
```
