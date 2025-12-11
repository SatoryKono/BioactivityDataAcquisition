# 01 Activity Chembl Overview

## Overview

- Pipeline ID `chembl.activity` is configured in `configs/pipelines/chembl/activity.yaml` with `entity: activity`, primary key `activity_id`, `input_mode: id_only`, and `serialization_mode: pipe` for nested structures.
- Pipelines are instantiated by `ChemblPipelineFactory`, which builds `ChemblPipelineBase` with provider-specific extraction, normalization, validation, hashing, and loader wiring from the pipeline container.
- Primary key resolution uses `resolve_primary_key_with_filter`, yielding the API filter `activity_id__in` for batching and file-based ID expansion.

## Flow: extract → transform → validate → export

1. **Extract**: `ChemblPipelineBase` wires an `ExtractStage` that uses `ChemblExtractionServiceImpl` (via the provider) and `ChemblRecordMapper` to stream raw ChEMBL payloads into DataFrames. `RecordSourceResolver` switches between API mode and file-backed sources (`CsvRecordSourceImpl` or `IdListRecordSourceImpl`) based on `input_mode`, applying the `activity_id__in` filter for batched lookups.
2. **Transform**: `ChemblTransformerImpl` runs pre-transform hooks (no-op), normalizes fields through the injected `NormalizationServiceABC` (Chembl flavor), serializes nested lists/dicts with `serialize_nested` using the configured `pipe` mode, enforces contract column order, and drops rows missing required non-generated columns. The default post-transformer then adds `hash_row`, `hash_business_key`, `index`, timestamps, and source version metadata.
3. **Validate**: `ValidationService` checks the output against the pipeline contract, aligning columns to `ACTIVITY_OUTPUT_COLUMNS` and ensuring Pandera constraints (types, nullable flags, ranges) defined for the ChEMBL activity schema.
4. **Export**: The injected `LoaderABC` writes normalized, validated batches to `output_path`, while the metadata builder attaches `chembl_release` and the last endpoint used from `ChemblPipelineBase._enrich_context`.

## Inputs and outputs

- **Inputs**: `api` (default streaming), `csv` (structured rows read via `CsvRecordSourceImpl`), or `id_only` (ID list expanded via API using `activity_id__in`). Provider config supplies base URL, pagination, and retry limits.
- **Outputs**: Ordered activity table columns plus generated metadata fields, deterministic serialization for arrays/objects, and `meta.yaml` entries populated with release/version context.

## Ports and adapters

- `ExtractionServiceABC` → `ChemblExtractionServiceImpl` with request builder, retry-aware client, and version lookup.
- `NormalizationServiceABC` → provider factory builds Chembl normalization service used inside `ChemblTransformerImpl`.
- `EntityModelRegistryABC` feeds `ChemblRecordMapper` for consistent field mapping.
- `LoaderABC` + `RunMetadataBuilderProtocol` handle output persistence and metadata sidecars.
- Record sources: `CsvRecordSourceImpl` and `IdListRecordSourceImpl` adapt CSV/ID-list inputs to the extraction port.

## Schemas

- Raw payload guardrails: `ActivityRawModel` validates action types, pChEMBL ranges, and ID formats at the boundary.
- Output contract: `ACTIVITY_OUTPUT_COLUMNS` defines canonical column order, and the pipeline contract points `schema_out` to the activity Pandera schema enforced during validation.
