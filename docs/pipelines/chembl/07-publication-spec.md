# ChEMBL Publication (Document) Pipeline Specification

*Version 1.1.0 | Aligned with RULES.md v5.11*

---

## 1. Identification

| Parameter | Value |
|-----------|-------|
| **Pipeline ID** | `chembl_publication` |
| **Provider** | ChEMBL (EBI) |
| **Entity** | document |
| **API Endpoint** | `https://www.ebi.ac.uk/chembl/api/data/document` |
| **Library** | `chembl_webresource_client` |
| **Rate Limit** | None |
| **Health Check** | `/chembl/api/data/status.json` |
| **Auth Type** | None (public API) |

---

## 2. Business Context

### 2.1. Entity Purpose

Documents represent **scientific publications** that are sources of ChEMBL data:

- **Data provenance**: Track original source of bioactivity data
- **Literature mining**: Access publication metadata
- **Cross-database linking**: DOI and PubMed ID mapping
- **Patent data**: Track patent-derived information

### 2.2. Use Cases

1. **Citation Analysis**: Track publications with most bioactivity data
2. **Data Attribution**: Credit original data sources
3. **Literature Review**: Access abstracts and journal information
4. **Cross-Provider Enrichment**: Link to PubMed, CrossRef for metadata

### 2.3. Entity Relationships

```
document
    │
    ├──◄──FK──activity.document_chembl_id (1:M)
    │
    ├──◄──FK──assay.document_chembl_id (1:M)
    │
    └──◄──FK──compound_record.document_chembl_id (1:M)
```

---

## 3. Extraction (Bronze Layer)

### 3.1. Complete API Fields

| # | API Field | JSON Type | Nullable | Description |
|---|-----------|-----------|----------|-------------|
| 1 | `document_chembl_id` | string | No | Primary key |
| 2 | `doc_type` | string | Yes | PUBLICATION/PATENT/DATASET/BOOK |
| 3 | `src_id` | integer | Yes | Source ID |
| 4 | `pubmed_id` | integer | Yes | PubMed ID |
| 5 | `doi` | string | Yes | DOI |
| 6 | `patent_id` | string | Yes | Patent ID |
| 7 | `title` | string | Yes | Title |
| 8 | `authors` | string | Yes | Authors string |
| 9 | `abstract` | string | Yes | Abstract |
| 10 | `journal` | string | Yes | Journal abbreviation |
| 11 | `journal_full_title` | string | Yes | Full journal title |
| 12 | `year` | integer | Yes | Publication year |
| 13 | `volume` | string | Yes | Volume |
| 14 | `issue` | string | Yes | Issue |
| 15 | `first_page` | string | Yes | First page |
| 16 | `last_page` | string | Yes | Last page |

---

## 4. Validation

### 4.1. Pandera Schema

```python
class ChemblPublicationSchema(ETLRecordSchema):
    """ChEMBL Publication validation schema for Silver layer."""

    # === Primary Key ===
    document_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
    )

    # === External Identifiers ===
    pubmed_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^\d+$",
    )
    doi: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=DOI_REGEX_PATTERN,
    )
    patent_id: Series[str] | None = pa.Field(nullable=True)
    src_id: Series[int] | None = pa.Field(nullable=True)

    # === Metadata ===
    title: Series[str] | None = pa.Field(nullable=True)
    doc_type: Series[str] | None = pa.Field(
        nullable=True,
        isin=["PUBLICATION", "PATENT", "DATASET", "BOOK"],
    )
    authors: Series[str] | None = pa.Field(nullable=True)
    abstract: Series[str] | None = pa.Field(nullable=True)
    journal: Series[str] | None = pa.Field(nullable=True)
    journal_full_title: Series[str] | None = pa.Field(nullable=True)
    year: Series[int] | None = pa.Field(
        nullable=True,
        ge=MIN_PUBLICATION_YEAR,  # 1800
        le=MAX_PUBLICATION_YEAR,  # 2100
    )
    volume: Series[str] | None = pa.Field(nullable=True)
    issue: Series[str] | None = pa.Field(nullable=True)
    first_page: Series[str] | None = pa.Field(nullable=True)
    last_page: Series[str] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = False
        coerce = True
```

---

## 5. Cross-Provider Mapping

| This Entity Field | Maps To | Provider | Field |
|-------------------|---------|----------|-------|
| `pubmed_id` | PubMed | PubMed | `pmid` |
| `doi` | CrossRef | CrossRef | `DOI` |
| `doi` | OpenAlex | OpenAlex | `doi` |
| `doi` | Semantic Scholar | S2 | `doi` |

---

## 6. Pipeline Configuration

```yaml
pipeline_name: chembl_publication
provider: chembl
entity_type: document
version: "1.1.0"

primary_keys: ["document_chembl_id"]
silver_table: "chembl_publication"
gold_table: "chembl_publication"

gold_filters:
  required_fields:
    - title
  columns:
    doc_type: [PUBLICATION]

input_filter:
  enabled: true
  source_path: "data/input/document.csv"
  column_name: "document_chembl_id"
  filter_field: "document_chembl_id"
  batch_size: 20
```
