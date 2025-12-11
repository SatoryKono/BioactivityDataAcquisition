# 03 Target Chembl Overview

## Overview

- Pipeline ID `chembl.target` comes from `configs/pipelines/chembl/target.yaml` with `entity: target`, primary key `target_chembl_id`, `input_mode: id_only`, and `serialization_mode: pipe`.
- `ChemblPipelineFactory` instantiates `ChemblPipelineBase`, injecting extraction, normalization, validation, hashing, and loader services resolved from the pipeline container for the target entity.
- `resolve_primary_key_with_filter` derives `target_chembl_id__in` for API batching and ID-list driven lookups.

## Flow: extract → transform → validate → export

1. **Extract**: `ChemblPipelineBase` composes an `ExtractStage` that streams target payloads via `ChemblExtractionServiceImpl` and `ChemblRecordMapper`. `RecordSourceResolver` switches between API, `csv`, and `id_only` feeds using `CsvRecordSourceImpl` or `IdListRecordSourceImpl`, applying the `target_chembl_id__in` filter for ID batches.
2. **Transform**: `ChemblTransformerImpl` normalizes target records through the Chembl-aware `NormalizationServiceABC`, serializes nested target fields with `serialize_nested` (`pipe` mode), enforces contract column ordering, and removes rows missing required fields. Post-transform hashing/indexing/timestamp enrichment is applied automatically.
3. **Validate**: `ValidationService` aligns output with `TARGET_OUTPUT_COLUMNS` and the Pandera target schema specified by the pipeline contract, ensuring deterministic column sets and constraint enforcement.
4. **Export**: The configured `LoaderABC` writes validated targets to `output_path` while metadata builders include `chembl_release` and last-endpoint hints from `ChemblPipelineBase._enrich_context`.

## Inputs and outputs

- **Inputs**: Default API streaming; `csv` mode for structured local rows; `id_only` mode expands IDs via `target_chembl_id__in`. Provider config covers base URL, pagination, retries, and rate limits.
- **Outputs**: Ordered target dataset with deterministic serialization for nested structures, generated metadata columns, and QC metadata sidecars (hashes, timestamps, release version).

## Ports and adapters

- `ExtractionServiceABC` → `ChemblExtractionServiceImpl` backed by the ChEMBL client and response parser.
- `NormalizationServiceABC` → Chembl normalization service injected into `ChemblTransformerImpl`.
- `EntityModelRegistryABC` powers `ChemblRecordMapper` for target field mapping.
- `LoaderABC` + `RunMetadataBuilderProtocol` handle persistence and run metadata assembly.
- Record sources: `CsvRecordSourceImpl` and `IdListRecordSourceImpl` adapt CSV/ID-list inputs when not streaming directly from the API.

## Schemas

- Raw payload guardrails: `TargetRawModel` validates identifier formats and optional nested payloads before mapping.
- Output contract: `TARGET_OUTPUT_COLUMNS` defines canonical order; the pipeline contract binds `schema_out` to the target Pandera schema enforced during validation.
