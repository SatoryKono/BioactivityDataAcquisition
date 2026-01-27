# openalex-publication

OpenAlex Works pipeline for scholarly publication metadata with DOI resolution and title-based fallback.

---

## Overview

The `openalex_publication` pipeline ingests scholarly work records from the [OpenAlex Works API](https://docs.openalex.org/api-entities/works), transforming them through Bronze (raw JSON), Silver (normalized), and Gold (analytics-ready) layers.

**Key Features:**
- Batch DOI resolution with automatic title-based fallback
- Abstract reconstruction from inverted index format
- PII-compliant author name hashing
- Hierarchical topic classification (replacing deprecated concepts)
- Open Access status tracking (gold/green/hybrid/bronze/closed)
- Full lineage tracking with lookup method metadata

**Use Cases:**
- DOI-to-metadata resolution for publication enrichment
- Citation analysis and bibliometric research
- Open Access landscape monitoring
- Author disambiguation (via institution IDs)

---

## Pipeline Identity

| Property | Value |
|----------|-------|
| **Pipeline Name** | `openalex_publication` |
| **Version** | 1.2.0 |
| **Provider** | `openalex` |
| **Entity Type** | `publication` |
| **Primary Key** | `openalex_id` |
| **Loading Strategy** | `full_scan_only` (ADR-030, ADR-031) |
| **Batch Size** | 50 records |

### Storage Paths

| Layer | Path | Format |
|-------|------|--------|
| Bronze | `data/output/bronze/openalex/publication` | ZSTD-compressed JSONL |
| Silver | `data/output/silver/openalex/publication` | Delta Lake (partitioned by `year`) |
| Gold | `data/output/gold/openalex/publication` | Delta Lake / Parquet |

---

## Source API

### Endpoint

| Property | Value |
|----------|-------|
| **Base URL** | `https://api.openalex.org` |
| **Endpoint** | `/works` |
| **Format** | JSON |
| **Authentication** | Email-based (polite pool) |
| **Rate Limit** | ~10 req/sec (polite pool) |

### Resolution Methods

The pipeline supports multiple identifier resolution strategies:

| Method | Endpoint Pattern | Priority |
|--------|------------------|----------|
| **Direct** | `/works/{openalex_id}` | 1 (highest) |
| **DOI** | `/works/doi:{doi}` | 2 |
| **Title Fallback** | `/works?filter=title.search:{title}` | 3 (lowest) |

When DOI resolution fails, the pipeline automatically falls back to title-based search. The resolution method is tracked in `_lookup_method` for data quality auditing.

### API Response Structure

```json
{
  "id": "https://openalex.org/W2148763428",
  "doi": "https://doi.org/10.1038/nature12373",
  "title": "Example Publication Title",
  "abstract_inverted_index": {"the": [0, 5], "protein": [1], ...},
  "authorships": [...],
  "primary_location": {"source": {...}},
  "open_access": {"is_oa": true, "oa_status": "gold"},
  "cited_by_count": 150,
  ...
}
```

---

## Silver Output Contract

### Field Mapping

#### System Fields (Prefix)

| Silver Field | Type | Source | Description |
|--------------|------|--------|-------------|
| `entity_id` | string | Computed | UUID hash of business data |
| `content_hash` | string | Computed | SHA-256 of normalized content |
| `_run_id` | string | Context | Pipeline execution ID |
| `_run_type` | string | Context | "incremental" or "full_scan" |
| `_source_batch_id` | string | Adapter | Batch identifier |
| `_source` | string | Fixed | Always "openalex" |
| `_ingestion_ts` | string | Context | ISO 8601 timestamp |
| `_index` | int64 | Processor | Record index within batch |

#### Lookup Metadata

| Silver Field | Type | Source | Values |
|--------------|------|--------|--------|
| `_lookup_method` | string | Adapter | "direct" \| "doi" \| "title_fallback" \| "unknown" |
| `_original_id` | string | Adapter | Original identifier if fallback used |

#### Primary Identifier

| API Field | Silver Field | Type | Extraction |
|-----------|--------------|------|------------|
| `id` | `openalex_id` | string | URL to ID extraction |

**Extraction Logic:**
```
"https://openalex.org/W2148763428" → "W2148763428"
```

#### Cross-Reference Identifiers

| API Field | Silver Field | Type | Extraction |
|-----------|--------------|------|------------|
| `doi` | `doi` | string | URL normalization via `DOI` Value Object |
| `ids.pmid` | `pmid` | string | URL extraction (last path segment) |
| `ids.pmcid` | `pmc_id` | string | URL extraction |
| `ids.mag` | `mag_id` | string | Integer/string to string coercion |

**External ID URL Patterns:**
- PMID: `https://pubmed.ncbi.nlm.nih.gov/12345678` → `"12345678"`
- PMCID: `https://www.ncbi.nlm.nih.gov/pmc/articles/PMC123456` → `"PMC123456"`

#### Core Metadata

| API Field | Silver Field | Type | Notes |
|-----------|--------------|------|-------|
| `title` | `title` | string | Publication title |
| `abstract_inverted_index` | `abstract` | string | Reconstructed + HTML stripped |
| `type` | `type` | string | Raw OpenAlex type |
| `type` | `doc_type` | string | Mapped to unified type |
| `language` | `language` | string | ISO 639 code |
| `is_retracted` | `is_retracted` | bool | Default: False |

#### Authors & Affiliations

| API Field | Silver Field | Type | Notes |
|-----------|--------------|------|-------|
| `authorships[].author.display_name` | `authors` | string (JSON) | **PII hashed** |
| `authorships[].institutions[].display_name` | `affiliations` | string (JSON) | Sorted, deduplicated |
| `authorships[].institutions[].id` | `institution_ids` | list[string] | OpenAlex institution IDs |
| `authorships[].institutions[].country_code` | `institution_country_codes` | list[string] | ISO 2-letter codes |

#### Journal & Venue

| API Field | Silver Field | Type |
|-----------|--------------|------|
| `primary_location.source.display_name` | `journal` | string |
| `primary_location.source.issn_l` | `issn` | string |
| `primary_location.source.host_organization_name` | `publisher` | string |

#### Bibliographic Information

| API Field | Silver Field | Type |
|-----------|--------------|------|
| `biblio.volume` | `volume` | string |
| `biblio.issue` | `issue` | string |
| `biblio.first_page` | `first_page` | string |
| `biblio.last_page` | `last_page` | string |

#### Dates

| API Field | Silver Field | Type | Validation |
|-----------|--------------|------|------------|
| `publication_year` | `year` | int64 | 1500-2100 range |
| `publication_date` | `publication_date` | string | ISO 8601 normalized |

#### Open Access

| API Field | Silver Field | Type | Values |
|-----------|--------------|------|--------|
| `open_access.is_oa` | `is_oa` | bool | true/false/null |
| `open_access.oa_status` | `oa_status` | string | gold/green/hybrid/bronze/closed |

#### Classification

| API Field | Silver Field | Type | Notes |
|-----------|--------------|------|-------|
| `topics[0..9]` | `topics` | list[dict] | Hierarchical (new format) |
| `primary_topic` | `primary_topic` | dict | Most relevant topic |
| `concepts[0..9]` | `concepts` | list[string] | **DEPRECATED** |
| `mesh[].descriptor_name` | `mesh` | list[string] | MeSH terms |
| `keywords[].display_name` | `keywords` | list[string] | Author keywords |
| `grants[]` | `grants` | list[dict] | Funding information |

#### Metrics

| API Field | Silver Field | Type | Notes |
|-----------|--------------|------|-------|
| `cited_by_count` | `citation_count` | int64 | Unified field name |
| `referenced_works_count` | `referenced_works_count` | int64 | Reference count |
| `fwci` | `fwci` | float64 | Field-Weighted Citation Impact |

#### DQ Flags (Suffix)

| Silver Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `_dq_warn` | bool | False | Soft threshold exceeded |
| `_dq_error` | bool | False | Hard threshold exceeded |

---

## Transformations (Silver)

### Abstract Reconstruction from Inverted Index

OpenAlex stores abstracts in an inverted index format where each word maps to its positions in the text. The transformer reconstructs the original text:

**Algorithm:**
1. Parse the inverted index: `{word: [pos1, pos2, ...]}`
2. Build position-word pairs: `[(pos, word), ...]`
3. Sort by position
4. Join words with spaces
5. Strip HTML tags (OpenAlex may include markup)

**Example:**
```
Input:
{
  "the": [0, 5],
  "protein": [1],
  "structure": [2],
  "is": [3],
  "complex": [4]
}

Output: "the protein structure is complex the"
```

This approach preserves word order while handling repeated words correctly.

### PII Hashing (Authors)

Author names are classified as PII and hashed before storage (RULES.md 5.4):

```
Input:  ["John Smith", "Jane Doe"]
Output: ["sha256:a1b2c3...", "sha256:d4e5f6..."]
```

The hashed values are JSON-serialized for storage in the `authors` field.

### Affiliation Deduplication

Institution names are deduplicated and sorted for deterministic output:

```
Input:  ["MIT", "Harvard", "MIT", "Stanford"]
Output: ["Harvard", "MIT", "Stanford"]
```

### External ID URL Parsing

All external identifiers are extracted from URL format to bare IDs:

| Source Format | Extracted |
|---------------|-----------|
| `https://openalex.org/W123` | `W123` |
| `https://doi.org/10.1038/...` | `10.1038/...` |
| `https://pubmed.ncbi.nlm.nih.gov/12345` | `12345` |

### Topics Structure (Hierarchical)

Each topic includes 4-level classification hierarchy:

```json
{
  "id": "T1234",
  "display_name": "Machine Learning",
  "score": 0.95,
  "subfield": "Artificial Intelligence",
  "field": "Computer Science",
  "domain": "Physical Sciences"
}
```

---

## Gold Output Contract

### Schema Definition

**Schema Class:** `OpenAlexPublicationGoldSchema`

| Field | Type | Nullable | Constraints |
|-------|------|----------|-------------|
| `entity_id` | string | **No** | - |
| `content_hash` | string | **No** | - |
| `openalex_id` | string | **No** | Primary key |
| `doi` | string | Yes | - |
| `pmid` | string | Yes | - |
| `title` | string | Yes | - |
| `abstract` | string | Yes | - |
| `authors` | string | Yes | JSON list |
| `affiliations` | list[str] | Yes | - |
| `concepts` | list[str] | Yes | - |
| `mesh` | list[str] | Yes | - |
| `keywords` | list[str] | Yes | - |
| `mag_id` | string | Yes | - |
| `journal` | string | Yes | - |
| `issn` | string | Yes | - |
| `publisher` | string | Yes | - |
| `first_page` | string | Yes | - |
| `last_page` | string | Yes | - |
| `year` | float | Yes | ge=1500, le=2100, coerce=True |
| `publication_date` | string | Yes | - |
| `type` | string | Yes | Raw OpenAlex type |
| `is_oa` | bool | Yes | coerce=True |
| `oa_status` | string | Yes | - |
| `citation_count` | float | Yes | ge=0, coerce=True |
| `language` | string | Yes | - |
| `_source` | string | **No** | Always "openalex" |
| `_lookup_method` | string | **No** | Resolution method |
| `_original_id` | string | Yes | - |
| `_dq_warn` | bool | **No** | default=False |
| `_dq_error` | bool | **No** | default=False |
| `_run_id` | string | **No** | - |
| `_run_type` | string | **No** | - |
| `_source_batch_id` | string | Yes | - |
| `_ingestion_ts` | string | **No** | - |
| `_index` | int | **No** | - |

### Required Fields

The following fields are required (nullable=False):
- `entity_id`, `content_hash` (system)
- `openalex_id` (primary key)
- `_source`, `_lookup_method` (tracking)
- `_dq_warn`, `_dq_error` (quality flags)
- `_run_id`, `_run_type`, `_ingestion_ts`, `_index` (lineage)

### Year Constraints

- **Minimum:** 1500 (historical publications)
- **Maximum:** 2100 (future-proof)
- **Coercion:** Integer to float for nullable support

### Citation Count Constraint

- **Minimum:** 0 (non-negative)
- **Coercion:** Integer to float for nullable support

---

## Gold Filters and Exclusions

### Fields Excluded from Gold

The following Silver fields are **excluded** from Gold output:

| Field | Reason |
|-------|--------|
| `topics` | Complex nested structure |
| `primary_topic` | Complex nested structure |
| `grants` | Complex nested structure |
| `pmc_id` | Not collected for OpenAlex |
| `doc_type` | Gold uses raw `type` instead |
| `institution_ids` | Denormalized institution data |
| `institution_country_codes` | Denormalized institution data |
| `referenced_works_count` | Reference metric |
| `fwci` | Citation impact metric |
| `is_retracted` | Retraction flag |

### Filter Configuration Hierarchy

Filters are loaded from (ADR-028, ADR-029):
1. `configs/filter/_defaults.yaml` (global)
2. `configs/filter/providers/openalex.yaml` (provider)
3. `configs/filter/entities/openalex/publication.yaml` (entity)

---

## Data Quality Checklist

### URL Parsing Failures

| Check | Severity | Threshold |
|-------|----------|-----------|
| Invalid OpenAlex ID URL | Error | 0% |
| Invalid DOI URL format | Warning | 5% |
| Invalid PMID URL format | Warning | 10% |

### Missing Identifiers

| Check | Severity | Notes |
|-------|----------|-------|
| Missing `openalex_id` | Error | Primary key required |
| Missing `doi` | Warning | Expected for most records |
| Missing `pmid` | Info | Not all works have PMID |

### Abstract Reconstruction

| Check | Severity | Threshold |
|-------|----------|-----------|
| Empty inverted index | Warning | 30% |
| Reconstruction failure | Error | 1% |
| HTML tags remaining | Warning | 5% |

### Open Access Consistency

| Check | Severity | Notes |
|-------|----------|-------|
| `is_oa=true` but `oa_status=closed` | Warning | Inconsistent OA data |
| `is_oa=null` | Info | Unknown OA status |
| Invalid `oa_status` value | Error | Must be known status |

### Author/Affiliation Extraction

| Check | Severity | Threshold |
|-------|----------|-----------|
| Empty authors list | Warning | 10% |
| PII hashing failure | Error | 0% |
| Empty affiliations | Info | 40% (many works lack affiliations) |

---

## Lineage

### Data Flow

```mermaid
sequenceDiagram
    participant API as OpenAlex API
    participant Bronze as Bronze Layer
    participant Silver as Silver Layer
    participant Gold as Gold Layer
    participant Composite as composite_publication

    API->>Bronze: Raw JSON (ZSTD)
    Bronze->>Silver: Transform + Validate
    Note over Silver: PII hashing<br/>Abstract reconstruction<br/>ID extraction
    Silver->>Gold: Filter + Refine
    Note over Gold: Exclude complex fields<br/>Apply constraints
    Gold-->>Composite: Feed merger
```

### Upstream Sources

| Source | Description |
|--------|-------------|
| OpenAlex Works API | Primary data source |
| DOI resolution | Via `/works/doi:{doi}` |
| Title search | Fallback via `?filter=title.search:{title}` |

### Downstream Consumers

| Consumer | Usage |
|----------|-------|
| `composite_publication` | Silver merge input |
| Analytics dashboards | Gold layer queries |
| DOI enrichment services | Publication metadata lookup |

### Composite Pipeline Integration

The `composite_publication` pipeline uses OpenAlex Silver data as an enricher:

```yaml
# composite_publication config excerpt
enrichers:
  - name: openalex_publication
    source: silver/openalex/publication
    join_keys: [doi, pmid]
    priority: 2
```

---

## Examples

### Sample Bronze Record

```json
{
  "id": "https://openalex.org/W2148763428",
  "doi": "https://doi.org/10.1038/nature12373",
  "title": "Crystal structure of a bacterial homologue",
  "abstract_inverted_index": {
    "The": [0],
    "crystal": [1],
    "structure": [2],
    "reveals": [3]
  },
  "authorships": [
    {
      "author": {
        "id": "https://openalex.org/A1234567890",
        "display_name": "John Smith"
      },
      "institutions": [
        {
          "id": "https://openalex.org/I1234567890",
          "display_name": "University of Oxford",
          "country_code": "GB"
        }
      ]
    }
  ],
  "primary_location": {
    "source": {
      "display_name": "Nature",
      "issn_l": "0028-0836",
      "host_organization_name": "Springer Nature"
    }
  },
  "open_access": {
    "is_oa": true,
    "oa_status": "hybrid"
  },
  "cited_by_count": 150,
  "publication_year": 2013,
  "publication_date": "2013-08-15"
}
```

### Sample Silver Record

```json
{
  "entity_id": "uuid-abc123...",
  "content_hash": "sha256:def456...",
  "openalex_id": "W2148763428",
  "doi": "10.1038/nature12373",
  "pmid": null,
  "title": "Crystal structure of a bacterial homologue",
  "abstract": "The crystal structure reveals",
  "authors": "[\"sha256:author1...\"]",
  "affiliations": "[\"University of Oxford\"]",
  "institution_ids": ["I1234567890"],
  "institution_country_codes": ["GB"],
  "journal": "Nature",
  "issn": "0028-0836",
  "publisher": "Springer Nature",
  "is_oa": true,
  "oa_status": "hybrid",
  "citation_count": 150,
  "year": 2013,
  "publication_date": "2013-08-15",
  "_source": "openalex",
  "_lookup_method": "doi",
  "_run_id": "run-123",
  "_dq_warn": false,
  "_dq_error": false
}
```

---

## Entity Relationship Diagram

```mermaid
erDiagram
    WORK ||--o{ AUTHORSHIP : has
    WORK ||--o| PRIMARY_LOCATION : has
    WORK ||--o{ TOPIC : classified_by
    WORK ||--o{ CONCEPT : tagged_with
    WORK ||--o{ GRANT : funded_by
    WORK ||--o{ MESH_TERM : indexed_by

    AUTHORSHIP ||--o{ INSTITUTION : affiliated_with

    WORK {
        string openalex_id PK
        string doi
        string pmid
        string title
        string abstract
        int citation_count
        int year
        string publication_date
        bool is_oa
        string oa_status
    }

    AUTHORSHIP {
        string author_id
        string display_name "PII - hashed"
    }

    INSTITUTION {
        string institution_id
        string display_name
        string country_code
    }

    PRIMARY_LOCATION {
        string journal_name
        string issn
        string publisher
    }

    TOPIC {
        string topic_id
        string display_name
        float score
        string subfield
        string field
        string domain
    }

    CONCEPT {
        string display_name "DEPRECATED"
    }

    GRANT {
        string funder_id
        string funder_name
        string award_id
    }

    MESH_TERM {
        string descriptor_name
    }
```

**Note:** Institutions, Topics, Concepts, Grants, and MeSH terms are stored as JSON arrays in Silver, not as normalized tables.

---

## Known Limitations / TODO

### Current Limitations

1. **Full Scan Only**: No incremental loading due to OpenAlex API offset pagination instability (ADR-030, ADR-031).

2. **Topics Not in Gold**: Hierarchical topic classification is excluded from Gold schema due to complex nested structure.

3. **Concepts Deprecated**: The `concepts` field is deprecated by OpenAlex (2024). Use `topics` for new development.

4. **Title Fallback Accuracy**: Title-based search may return incorrect matches for common titles. The `_lookup_method` field allows filtering these records.

5. **Abstract Coverage**: Not all OpenAlex works have abstracts. The inverted index may be empty or null.

6. **PII Hashing Irreversibility**: Author names cannot be recovered once hashed. Store raw names separately if needed for display.

### Future Enhancements

- [ ] Add `topics` and `grants` to Gold schema with flattened structure
- [ ] Implement incremental loading when OpenAlex stabilizes cursor pagination
- [ ] Add author ORCID extraction from `authorships[].author.orcid`
- [ ] Add related works extraction (`related_works[]`)
- [ ] Add citation context extraction from `referenced_works[]`

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.2.0 | 2026-01 | Added topics/primary_topic extraction (new OpenAlex format) |
| 1.1.0 | 2025-12 | Added institution_ids and country_codes extraction |
| 1.0.0 | 2025-10 | Initial release with DOI resolution and title fallback |

---

## References

- [OpenAlex Works API Documentation](https://docs.openalex.org/api-entities/works)
- [OpenAlex Data Model](https://docs.openalex.org/about-the-data)
- [ADR-030: OpenAlex Offset Stability](../02-architecture/decisions/ADR-030-openalex-offset-stability.md)
- [ADR-031: Full Scan Loading Strategy](../02-architecture/decisions/ADR-031-full-scan-loading.md)
- [RULES.md 5.4: PII Handling](../RULES.md#54-pii-handling)
