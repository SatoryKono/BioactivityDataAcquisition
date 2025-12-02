# NN <Entity> <Provider> Pipeline Documentation Template

This template defines the standard structure for documenting BioETL pipelines. Replace placeholders:
- `NN` — two-digit number prefix (00, 01, 02, etc.)
- `<Entity>` — entity name (e.g., `activity`, `assay`, `target`)
- `<Provider>` — provider name (e.g., `chembl`, `pubmed`)

## File Structure

Each pipeline should have the following documentation files:

1. **`00-<entity>-<provider>-overview.md`** — Pipeline overview and architecture
2. **`01-<entity>-<provider>-extraction.md`** — Extraction stage
3. **`02-<entity>-<provider>-transformation.md`** — Transformation stage
4. **`03-<entity>-<provider>-io.md`** — Input/Output and artifacts
5. **`<entity>-schema.md`** (optional, can be in `docs/02-pipelines/schemas/`) — Pandera schema

---

## Template: 00-<entity>-<provider>-overview.md

```markdown
# 00 <Entity> <Provider> Overview

## Description

`<Entity><Provider>Pipeline` — ETL pipeline for processing <entity description> from <provider>. Pipeline code: `<entity>_<provider>`. Implements full cycle: extraction from <provider> API, transformation, validation, and result persistence.

The pipeline inherits from `<Provider>BasePipeline` (or `PipelineBase`), using shared infrastructure for <provider> pipelines.

## Module

`src/bioetl/pipelines/<provider>/<entity>/run.py`

## Inheritance

- `<Provider>BasePipeline` → `PipelineBase`
- Uses shared <provider> infrastructure through base class

## Architecture

Pipeline consists of the following stages:

1. **Extract** (`<Entity>Extractor`) — extraction of raw data from <provider> API
2. **Transform** (`<Entity>Transformer`) — transformation and enrichment
3. **Validate** — validation against Pandera schema
4. **Write** (`<Entity>Writer`) — persistence of results to files

## Key Methods

### `__init__(self, config, run_id, *, client_factory=None)`

Initializes pipeline with configuration, run_id, and optional client factory.

### `build_descriptor(self) -> <Provider>ExtractionDescriptor`

Creates extraction descriptor based on pipeline configuration.

### `extract(self, descriptor, options) -> pd.DataFrame`

Extracts raw data from <provider> API and converts to pandas DataFrame.

### `transform(self, df: pd.DataFrame, options) -> pd.DataFrame`

Transforms extracted data: enriches with domain fields, normalizes values and data types.

### `validate(self, df: pd.DataFrame, options) -> pd.DataFrame`

Validates data against Pandera schema.

### `run(self, output_dir: Path, *, run_tag=None, mode=None, extended=False, dry_run=None, sample=None, limit=None, include_qc_metrics=False, fail_on_schema_drift=True) -> RunResult`

Main execution method. Performs full cycle: configuration preparation, extract/transform/validate stages, result persistence, and QC metrics generation.

## Configuration

Pipeline configuration is in `configs/pipelines/<provider>/<entity>.yaml` and defines:
- Data fields and their types
- Pagination parameters
- Filters and constraints
- Normalization settings

## Related Components

- **<Entity>Extractor**: extraction stage (see `01-<entity>-<provider>-extraction.md`)
- **<Entity>Transformer**: transformation stage (see `02-<entity>-<provider>-transformation.md`)
- **<Entity>Writer**: write stage (see `03-<entity>-<provider>-io.md`)
- **<Provider>Client**: REST client for <provider> API (see `docs/02-pipelines/<provider>/common/01-<provider>-client.md`)
- **UnifiedOutputWriter**: unified writer for result persistence (see `docs/02-pipelines/core/04-unified-output-writer.md`)
- **SchemaRegistry**: schema registry for validation (see `docs/02-pipelines/core/05-schema-registry.md`)
```

---

## Template: 01-<entity>-<provider>-extraction.md

```markdown
# 01 <Entity> <Provider> Extraction

## Description

`<Entity>Extractor` — extraction stage class for <entity> data from <provider> API. Calls <provider> client in batches and forms resulting DataFrame with metadata. Inherits from `StageABC` and implements extraction stage interface.

## Module

`src/bioetl/pipelines/<provider>/<entity>/stages.py`

## Inheritance

Class inherits from `StageABC` and implements data extraction stage interface.

## Main Method

### `extract(self, descriptor: <Provider>ExtractionDescriptor, config: PipelineConfig, batch_size: int | None = None) -> tuple[pd.DataFrame, dict[str, Any]]`

Performs extraction of <entity> data from <provider> API.

**Parameters:**
- `descriptor` — extraction descriptor with request parameters (IDs, filters, pagination)
- `config` — pipeline configuration
- `batch_size` — batch size for processing (optional)

**Extraction Process:**

1. Client building: creation of `<Provider>Client` via `_build_client`
2. Request execution: sending requests to <provider> API via client
3. Response parsing: conversion of JSON responses to DataFrame via `<Entity>Parser`
4. Result assembly: combining data from all pages/batches into single DataFrame
5. Metadata: collection of extraction process metadata (record count, execution time)

**Returns:** tuple of DataFrame with data and metadata dictionary.

## Error Handling

Stage handles various error types:
- Network errors: retries via `RetryPolicyABC`
- Parsing errors: logging and creation of fallback rows via `_fallback_rows`
- Partial failures: continuation of processing remaining records

## Related Components

- **<Provider>Client**: REST client for <provider> API (see `docs/02-pipelines/<provider>/common/01-<provider>-client.md`)
- **<Entity>Parser**: parser for <provider> API responses (see `04-<entity>-<provider>-parser.md` if exists)
- **<Provider>ExtractionDescriptor**: extraction parameter descriptor (see common descriptor docs)
```

---

## Template: 02-<entity>-<provider>-transformation.md

```markdown
# 02 <Entity> <Provider> Transformation

## Description

`<Entity>Transformer` — transformation stage class for <entity> data. Transforms raw data from <provider> API into normalized format, enriches with domain fields, and normalizes data types. Inherits from `TransformerABC` or uses `<Provider>BaseNormalizer`.

## Module

`src/bioetl/pipelines/<provider>/<entity>/stages.py` or `normalizer.py`

## Transformation Steps

1. **Column Mapping**: Maps JSON fields to normalized column names
2. **Type Conversion**: Converts data types (strings to numbers, dates, etc.)
3. **Enrichment**: Adds computed fields, lookups, or derived values
4. **Normalization**: Standardizes formats (trimming, case conversion, etc.)

## Key Methods

### `transform(self, df: pd.DataFrame, options) -> pd.DataFrame`

Transforms DataFrame according to pipeline-specific rules.

### `normalize_column(self, series: pd.Series, column_spec: ColumnSpec) -> pd.Series`

Normalizes specific column according to specification.

## Column Specifications

Column normalization is defined in configuration or code:
- Data type conversions
- Null handling policies
- Format normalizations (dates, numbers, strings)

## Related Components

- **<Provider>BaseNormalizer**: base normalizer for <provider> (see `docs/02-pipelines/<provider>/common/00-base-<provider>-normalizer.md`)
- **TransformerABC**: transformation contract (see `docs/reference/abc/26-transformer-abc.md`)
```

---

## Template: 03-<entity>-<provider>-io.md

```markdown
# 03 <Entity> <Provider> IO

## Description

Input/Output operations and artifact management for <entity> pipeline.

## Output Artifacts

Pipeline produces the following artifacts:

1. **Data File**: `<entity>_<provider>_<run_tag>.parquet` — main data file
2. **Metadata**: `meta.yaml` — pipeline metadata (version, row count, checksums)
3. **QC Reports**: `quality_report_<entity>_<provider>.csv`, `correlation_report_<entity>_<provider>.csv`
4. **Schema**: Schema validation results

## Write Process

1. **Validation**: Data validated against Pandera schema
2. **Sorting**: Stable sort by business keys
3. **Writing**: Atomic write via `UnifiedOutputWriter`
4. **Metadata Generation**: Creation of `meta.yaml` with pipeline metadata

## Artifact Structure

```
<output_dir>/
├── <entity>_<provider>_<run_tag>.parquet
├── meta.yaml
├── quality_report_<entity>_<provider>.csv
└── correlation_report_<entity>_<provider>.csv
```

## Related Components

- **UnifiedOutputWriter**: unified writer (see `docs/02-pipelines/core/04-unified-output-writer.md`)
- **WriteArtifacts**: artifact management (see `docs/02-pipelines/core/01-write-artifacts.md`)
- **MetadataWriterABC**: metadata writing contract (see `docs/reference/abc/11-metadata-writer-abc.md`)
```

---

## Notes

- Keep documentation synchronized with code
- Use consistent terminology across all pipeline docs
- Link to related components using relative paths
- Mark auto-generated sections with `<!-- generated -->`
- Follow naming conventions from `docs/project/00-rules-summary.md`

