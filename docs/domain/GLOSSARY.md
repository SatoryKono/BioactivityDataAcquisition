# BioETL Domain Glossary

Ubiquitous Language — единый словарь терминов для domain layer.

---

## Data Abstractions

### Record
- **Definition**: Single data entry with dict-like access
- **Code**: `Record` Protocol in `src/bioetl/domain/data.py`
- **Usage**: Domain contracts, type hints
- **Compatible with**: `dict[str, Any]`, `pd.Series`, `Mapping[str, Any]`

### RecordBatch
- **Definition**: Sequence of records processed together
- **Code**: `Sequence[Mapping[str, Any]]` in `src/bioetl/domain/data.py`
- **NOT**: `list[dict]` (too specific)
- **Deprecated alias**: `RawRecordBatch`, `RawRecordList`

### SourceRecordModel
- **Definition**: Pydantic model for parsing API responses at system boundaries
- **Code**: `SourceRecordModel` in `src/bioetl/domain/record_source.py`
- **Config**: `extra="allow"` — accepts any fields
- **Deprecated alias**: `SourceRecord`, `RawRecord`

### TabularData
- **Definition**: Protocol replacing `pd.DataFrame` in domain contracts
- **Code**: `TabularData` Protocol in `src/bioetl/domain/data.py`
- **Properties**: `columns`, `shape`
- **Methods**: `iterrows()`, `to_records()`, `__len__()`, `__iter__()`

---

## Hash Terminology

### hash_row
- **Definition**: Cryptographic hash of entire record
- **Algorithm**: BLAKE2b-256 (64 hex chars)
- **Code**: `HashDigest` Value Object in `src/bioetl/domain/value_objects/crypto.py`
- **Deprecated alias**: `fingerprint`

### hash_business_key
- **Definition**: Hash of business key fields only
- **Purpose**: Deduplication across records
- **Algorithm**: BLAKE2b-256 (64 hex chars)
- **Deprecated alias**: `entity_key`

### HashDigest
- **Definition**: Value Object for cryptographic hash digest (hex-encoded)
- **Code**: `src/bioetl/domain/value_objects/crypto.py`
- **Supported algorithms**: `blake2b_256`, `sha256`, `sha512`, `md5`
- **Immutable**: Yes

---

## Identifiers

### ChemblId
- **Definition**: Value Object for ChEMBL identifier
- **Format**: `CHEMBL` + digits (e.g., `CHEMBL123`)
- **Code**: `ChemblId` in `src/bioetl/domain/value_objects/identifiers.py`
- **Pattern**: `^CHEMBL\d+$`
- **Properties**: `value`, `numeric_id`

### ActivityId
- **Definition**: Numeric identifier for activity records
- **Format**: Numeric string (e.g., `"12345"`)
- **NOT**: ChemblId format — activities use plain numeric IDs

### PipelineId
- **Definition**: Value Object for pipeline identifier
- **Format**: `provider.entity` (e.g., `chembl.activity`)
- **Code**: `PipelineId` in `src/bioetl/domain/value_objects/identifiers.py`
- **Properties**: `value`, `provider`, `entity`

### RunId
- **Definition**: Value Object for pipeline run identifier
- **Format**: UUID v4 (lowercase, e.g., `a1b2c3d4-...`)
- **Code**: `RunId` in `src/bioetl/domain/value_objects/identifiers.py`
- **Factory**: `RunId.generate()`

### EntityName
- **Definition**: Value Object for entity name (snake_case)
- **Format**: `^[a-z][a-z0-9_]*$`, max 64 chars
- **Code**: `EntityName` in `src/bioetl/domain/value_objects/identifiers.py`

### StageName
- **Definition**: Value Object for pipeline stage name
- **Allowed values**: `extract`, `transform`, `validate`, `export`
- **Alias**: `load` → `export`
- **Code**: `StageName` in `src/bioetl/domain/value_objects/identifiers.py`
- **Constants**: `StageName.EXTRACT`, `StageName.TRANSFORM`, `StageName.VALIDATE`, `StageName.EXPORT`

---

## Type Aliases

### ApiPayload
- **Definition**: Raw API response payload
- **Type**: `dict[str, Any]`
- **Code**: `src/bioetl/domain/types.py`
- **Deprecated alias**: `RawPayload`

### FieldConfig
- **Definition**: Field configuration dictionary
- **Type**: `dict[str, Any]`
- **Code**: `src/bioetl/domain/types.py`

---

## Pipeline Concepts

### Pipeline
- **Definition**: Instance of `PipelineBase` implementing extract → transform → validate → write chain
- **Stages**: `extract`, `transform`, `validate`, `export`

### Stage
- **Definition**: Pipeline step with single responsibility
- **Types**: `extract`, `transform`, `validate`, `export` (alias: `load`)

### RunResult
- **Definition**: Aggregated pipeline execution state
- **Contains**: counters, metadata, artifact paths

### PipelineHook
- **Definition**: Implementation of `PipelineHookABC`
- **Methods**: `prepare_run()`, `finalize_run()`

---

## Domain Services

### SchemaRegistry
- **Definition**: Service for registering and retrieving Pandera schemas by domain entities
- **Code**: `src/bioetl/domain/schemas/registry.py`

### ValidationService
- **Definition**: Wrapper over validators applying schemas and collecting results
- **Code**: `src/bioetl/domain/validation/service.py`

---

## Source Abstractions

### RecordSourceABC
- **Definition**: Abstract base class for record sources
- **Method**: `iter_records() -> Iterable[Sequence[Mapping[str, Any]]]`
- **Code**: `src/bioetl/domain/record_source.py`
- **Deprecated alias**: `RecordSource`

### InMemoryRecordSource
- **Definition**: Simple record source backed by in-memory list
- **Code**: `src/bioetl/domain/record_source.py`
- **Options**: `chunk_size` for batching

---

## Domain Entities

### Activity
- **Definition**: Experiment result record with business key and hashes
- **Schema**: `src/bioetl/domain/schemas/chembl/activity.py`

### Assay
- **Definition**: Biological experiment description
- **Schema**: `src/bioetl/domain/schemas/chembl/assay.py`

### Molecule
- **Definition**: Tested compound/drug
- **Schema**: `src/bioetl/domain/schemas/chembl/molecule.py`

### Target
- **Definition**: Biological target linked to Assay/Activity
- **Schema**: `src/bioetl/domain/schemas/chembl/target.py`

### Publication
- **Definition**: Scientific publication reference
- **Schema**: `src/bioetl/domain/schemas/chembl/publication.py`

---

## Deprecated Terms Migration

| Deprecated | Replacement | Notes |
|------------|-------------|-------|
| `RawRecord` | `Mapping[str, Any]` | Removed completely |
| `SourceRecord` | `SourceRecordModel` | Alias kept for compatibility |
| `RawRecordDict` | `Mapping[str, Any]` | Removed |
| `RawRecordBatch` | `RecordBatch` | Use `domain.data.RecordBatch` |
| `RawRecordList` | `RecordBatch` | Use `domain.data.RecordBatch` |
| `RawPayload` | `ApiPayload` | Use `domain.types.ApiPayload` |
| `fingerprint` | `hash_row` | Terminology change |
| `entity_key` | `hash_business_key` | Terminology change |
| `RecordSource` | `RecordSourceABC` | Explicit ABC suffix |
| `load` (stage) | `export` | Stage name alias |
