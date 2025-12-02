# Data Flow

End-to-end description of data flow in BioETL framework, from external API to final artifacts.

## Overview

BioETL processes data through a standardized pipeline: **Extract → Transform → Validate → Write**. This document describes the complete flow using Activity ChEMBL pipeline as an example.

## High-Level Flow

```
External API (ChEMBL)
    ↓
SourceClient (ChemblClient)
    ↓
Extractor (ActivityExtractor)
    ↓
Parser (ActivityParser)
    ↓
Transformer (ActivityTransformer)
    ↓
Normalizer (ActivityNormalizer)
    ↓
Validator (ValidationService)
    ↓
Writer (ActivityWriter)
    ↓
Artifacts (Parquet, meta.yaml, QC reports)
```

## Detailed Stage-by-Stage Flow

### Stage 1: Extract

**Component:** `ActivityExtractor` (implements `StageABC`)

**Input:**
- `ChemblExtractionDescriptor` — parameters defining what to extract (IDs, filters, pagination)
- `PipelineConfig` — pipeline configuration
- `batch_size` (optional) — batch size for processing

**Process:**

1. **Client Building**
   - Creates `ChemblClient` via `_build_client()`
   - Client uses `UnifiedAPIClient` internally
   - Applies HTTP infrastructure (retry policy, rate limiter, circuit breaker)

2. **Request Execution**
   - Sends requests to ChEMBL API `/activity` endpoint
   - Handles pagination automatically via `PaginatorABC`
   - Batches requests according to `BatchPlan` (25 IDs per request limit)

3. **Response Parsing**
   - Receives JSON responses from API
   - Passes to `ActivityParser` for conversion to DataFrame
   - Parser uses `ColumnMapping` to map JSON fields to DataFrame columns

4. **Result Assembly**
   - Combines data from all pages/batches into single DataFrame
   - Collects extraction metadata (record count, execution time, errors)

**Output:**
- `pd.DataFrame` — raw data from API
- `dict[str, Any]` — extraction metadata

**Error Handling:**
- Network errors: retries via `RetryPolicyABC`
- Parsing errors: creates fallback rows via `_fallback_rows()`
- Partial failures: continues processing remaining records

### Stage 2: Transform

**Component:** `ActivityTransformer` (implements `StageABC`)

**Input:**
- `pd.DataFrame` — raw data from extraction stage

**Process:**

1. **Domain Enrichment**
   - Adds domain fields via `_domain_enrich()` (e.g., `chembl_release`)
   - Enriches with computed fields or lookups

2. **Normalization**
   - Applies `ActivityNormalizer` which wraps `BaseChemblNormalizer`
   - Uses `ColumnNormalizationSpec` for each column:
     - Type conversion (strings → numbers, dates, etc.)
     - Default value filling
     - Custom transformations via transformer functions

3. **Schema Alignment**
   - Ensures DataFrame structure matches target schema
   - Reorders columns if needed

**Output:**
- `pd.DataFrame` — normalized and enriched data

### Stage 3: Validate

**Component:** `ValidationService` (uses `ValidatorABC`)

**Input:**
- `pd.DataFrame` — transformed data
- `SchemaRegistry` — provides Pandera schema (`ChEMBLActivitySchema`)

**Process:**

1. **Schema Lookup**
   - Retrieves schema from `SchemaRegistry` by entity name
   - Schema defines: column names, types, constraints, order

2. **Validation**
   - Calls `schema.validate(df)` with `strict=True`, `ordered=True`
   - Checks:
     - All required columns present
     - Column order matches schema
     - Data types match schema
     - Constraints satisfied (ranges, categories, regex)

3. **Error Handling**
   - On validation failure: raises `SchemaValidationError` with details
   - Empty DataFrame: creates empty DataFrame with correct structure

**Output:**
- `pd.DataFrame` — validated data (unchanged if valid)

### Stage 4: Write

**Component:** `ActivityWriter` (implements `StageABC`)

**Input:**
- `pd.DataFrame` — validated data
- `WriteArtifacts` — artifact paths (planned by `ActivityArtifactPlanner`)
- `run_stem` — file name stem
- `output_dir` — output directory

**Process:**

1. **Artifact Planning**
   - `ActivityArtifactPlanner.plan()` creates directory structure:
     ```
     <output_dir>/
     └── <run_stem>/
         ├── activity_<run_stem>.parquet
         ├── meta.yaml
         ├── quality_report_activity_chembl.csv
         └── correlation_report_activity_chembl.csv
     ```

2. **Data Preparation**
   - Stable sort by business keys (deterministic order)
   - Ensure column order matches schema

3. **Atomic Write**
   - Uses `UnifiedOutputWriter.write_dataset_atomic()`
   - Writes to temporary file, then `os.replace()` for atomicity
   - Format: Parquet (or CSV if configured)

4. **Metadata Generation**
   - Creates `meta.yaml` with:
     - Pipeline version
     - ChEMBL release version
     - Row count
     - Checksums (MD5, SHA256)
     - Execution metadata

5. **QC Reports** (if enabled)
   - `quality_report_activity_chembl.csv` — data quality metrics
   - `correlation_report_activity_chembl.csv` — correlation analysis

**Output:**
- `WriteResult` — write metrics and artifact paths
- Files on disk: Parquet, meta.yaml, QC reports

## Component Interactions

### HTTP Infrastructure

All external API calls go through HTTP infrastructure:

- **Rate Limiter** (`RateLimiterABC`) — limits requests per second
- **Retry Policy** (`RetryPolicyABC`) — exponential backoff on failures
- **Circuit Breaker** — stops requests if API is down
- **HTTP Cache** (`CacheABC`) — caches responses (optional)

### Configuration Flow

1. **Base Profile** (`configs/profiles/chembl_default.yaml`)
   - Common settings for all ChEMBL pipelines

2. **Environment Profile** (`development.yaml` or `production.yaml`)
   - Overrides base profile

3. **Pipeline Config** (`configs/pipelines/chembl/activity.yaml`)
   - Entity-specific settings

4. **CLI Overrides** (`--set key=value`)
   - Runtime overrides

5. **Environment Variables** (`BIOETL_*`)
   - Highest priority

### Logging and Observability

All stages use `UnifiedLogger` with structured logging:

- **Run Context**: `run_id`, `pipeline`, `stage`, `dataset`, `source`
- **Structured Events**: key-value pairs for filtering
- **Error Tracking**: exceptions logged with full context

## Example: Complete Activity Pipeline Run

```python
# 1. Initialize pipeline
pipeline = ChemblActivityPipeline(
    config=load_config("configs/pipelines/chembl/activity.yaml"),
    run_id="run_20240101_001"
)

# 2. Build extraction descriptor
descriptor = pipeline.build_descriptor()
# descriptor contains: ids, filters, pagination, batch_plan

# 3. Run pipeline
result = pipeline.run(
    output_dir=Path("./output"),
    run_tag="activity_20240101",
    mode="production"
)

# Flow:
# Extract: descriptor → ChemblClient → API → ActivityParser → DataFrame
# Transform: DataFrame → ActivityNormalizer → normalized DataFrame
# Validate: DataFrame → SchemaRegistry → ValidationService → validated DataFrame
# Write: DataFrame → ActivityWriter → UnifiedOutputWriter → artifacts
```

## Determinism Guarantees

The pipeline ensures deterministic output:

1. **Stable Sorting**: Data sorted by business keys before writing
2. **Column Order**: Matches schema `column_order` exactly
3. **UTC Timestamps**: All timestamps in UTC
4. **Canonical JSON**: Ordered keys in metadata JSON
5. **Atomic Writes**: temp file → `os.replace()` prevents partial writes

## Related Documentation

- **[Pipeline Base](../02-pipelines/00-pipeline-base.md)** — Base pipeline architecture
- **[Unified API Client](../02-pipelines/03-unified-api-client.md)** — HTTP client infrastructure
- **[Activity Pipeline](../02-pipelines/chembl/activity/00-activity-chembl-overview.md)** — Activity pipeline details
- **[Schema Registry](../02-pipelines/05-schema-registry.md)** — Schema validation
- **[Validation Service](../02-pipelines/06-validation-service.md)** — Data validation

