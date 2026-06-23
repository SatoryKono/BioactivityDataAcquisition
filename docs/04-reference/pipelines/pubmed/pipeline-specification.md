# PubMed Pipeline Specification

## Overview

PubMed pipeline извлекает библиографические данные из PubMed E-utilities API.

## Purpose

Acquisition and processing of bibliographic metadata from PubMed for bioactivity research.

## Data Sources

### Primary Source

- **API:** PubMed E-utilities API
- **Base URL:** https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
- **Authentication:** API Key (optional, recommended for higher rate limits)
- **Rate Limit:** 3 requests/second without API key, 10 requests/second with API key

### Data Types

- Articles (bibliographic metadata)
- Abstracts
- MeSH terms
- Publication types
- Author information

## Pipeline Stages

### 1. Preflight

- Validates API key configuration
- Checks API availability
- Validates query parameters

### 2. Execution

#### 2.1 Data Fetch

- Executes PubMed E-utilities search
- Paginates through results
- Handles rate limiting
- Implements retry logic for transient failures

#### 2.2 Transform

- Normalizes field names
- Converts date formats
- Extracts MeSH terms
- Standardizes author names
- Enriches with PubMed Central IDs (if available)

#### 2.3 Validation

- Validates required fields (PMID, title, abstract)
- Checks date ranges
- Validates MeSH term format
- Ensures data type consistency

### 3. Postrun

- Generates run statistics
- Records metrics
- Updates lineage metadata

## Medallion Architecture

### Bronze Layer

- **Format:** Raw JSON from PubMed API
- **Location:** `data/bronze/pubmed/`
- **Schema:** Mirrors PubMed API response structure
- **Validation:** Minimal (basic structure check)

### Silver Layer

- **Format:** Normalized Parquet/Delta
- **Location:** `data/silver/pubmed/`
- **Schema:** Standardized field names and types
- **Validation:** Pandera schema validation
- **Transformations:** Date normalization, field renaming

### Gold Layer

- **Format:** Curated Parquet/Delta
- **Location:** `data/gold/pubmed/`
- **Schema:** Strict validation, deduplicated
- **Validation:** Pandera with strict constraints
- **Quality Rules:** Completeness, uniqueness, consistency

## Quarantine Handling

### Quarantine Triggers

- Missing required fields (PMID, title)
- Invalid date formats
- Malformed MeSH terms
- Duplicate PMIDs
- API rate limit errors (after retries)

### Quarantine Resolution

- Manual review of quarantined records
- Correction of data quality issues
- Re-processing with corrected data

## Data Quality Rules

### Schema Validation

- `pmid`: Required, string, unique
- `title`: Required, string, max length
- `abstract`: Optional, string
- `publication_date`: Required, ISO 8601 date
- `authors`: Optional, array of author objects
- `mesh_terms`: Optional, array of MeSH terms

### Quality Rules

- **Completeness:** PMIDs must have title and publication date
- **Uniqueness:** No duplicate PMIDs within a batch
- **Consistency:** Date ranges must be valid
- **Format:** MeSH terms must follow PubMed format

## Replay Support

- **Deterministic:** Yes (same query produces same results)
- **Idempotent:** Yes (re-running with same run_id is safe)
- **Checkpointing:** Yes (after each stage)
- **Replay Strategy:** Re-run from checkpoint or from scratch

## Checkpointing

- **Checkpoint Frequency:** After each stage (preflight, fetch, transform, validate)
- **Checkpoint Location:** `data/checkpoints/pubmed/`
- **Checkpoint Format:** JSON manifest with stage results
- **Recovery:** Automatic recovery from last successful checkpoint

## Run Lifecycle

1. **PENDING:** Run created, waiting to start
2. **RUNNING:** Pipeline executing
3. **COMPLETED:** All stages successful
4. **FAILED:** Pipeline failed (can be retried)
5. **SHUTDOWN:** Pipeline stopped by user

## Configuration

### Entity Config

- **File:** `configs/entities/pubmed/publication.yaml`
- **Key Parameters:**
  - `api_key`: PubMed API key
  - `query`: PubMed search query
  - `max_results`: Maximum records to fetch
  - `date_range`: Date range for search

## Example Commands

```bash
# Run PubMed pipeline
python -m bioetl run pubmed

# Run with specific query
python -m bioetl run pubmed --query "cancer AND 2024"

# Run with custom date range
python -m bioetl run pubmed --date-start "2024-01-01" --date-end "2024-12-31"

# Replay previous run
python -m bioetl replay --run-id run-123
```

## Dependencies

- **External:** PubMed E-utilities API
- **Internal:** Metadata enrichment services, Storage adapters, DQ framework
- **Enrichers:** CrossRef (for DOI lookup), Semantic Scholar (for additional metadata)

## Lineage

- **Source:** PubMed API
- **Transformations:** Documented in RunManifest
- **Output:** Gold layer records
- **Metadata:** Stored in RunLedger

## Observability

- **Metrics:** Records fetched, transformed, validated, quarantined
- **Logs:** Structured logs with trace correlation
- **Traces:** Distributed tracing for each pipeline stage
- **Alerts:** API failures, high quarantine rate, long running time