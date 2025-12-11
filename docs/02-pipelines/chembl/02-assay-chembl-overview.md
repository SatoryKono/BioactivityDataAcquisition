# 02 Assay Chembl Overview

## Overview

- Pipeline ID `chembl.assay` is defined in `configs/pipelines/chembl/assay.yaml` with `entity: assay`, primary key `assay_chembl_id`, `input_mode: id_only`, and `serialization_mode: pipe` for nested assay attributes.
- `ChemblPipelineFactory` constructs `ChemblPipelineBase` instances, wiring extraction, transformation, validation, hashing, and loader services resolved from the pipeline container.
- `resolve_primary_key_with_filter` yields the API filter `assay_chembl_id__in`, enabling batched ID queries and ID-list expansion for offline modes.

## Flow: extract → transform → validate → export

1. **Extract**: `ChemblPipelineBase` uses `ExtractStage` with `ChemblExtractionServiceImpl` and `ChemblRecordMapper` to stream assay records as DataFrames. `RecordSourceResolver` switches between API pulls and file-backed feeds (`CsvRecordSourceImpl` or `IdListRecordSourceImpl`) based on the configured mode, reusing `assay_chembl_id__in` for batched requests.
2. **Transform**: `ChemblTransformerImpl` normalizes assay payloads through the Chembl-specific `NormalizationServiceABC`, serializes nested assay classifications/parameters with `serialize_nested` in `pipe` mode, enforces contract ordering, and drops rows missing non-generated required fields. The default post-transformer appends hashes, index, timestamps, and version metadata.
3. **Validate**: `ValidationService` enforces the assay pipeline contract, aligning columns to `ASSAY_OUTPUT_COLUMNS` and applying Pandera constraints (types, nullability, enumerations) for assay outputs.
4. **Export**: Loader implementations (`LoaderABC`) persist validated batches to `output_path` while the metadata builder records `chembl_release` and the last endpoint used in the run context.

## Inputs and outputs

- **Inputs**: API streaming by default; `csv` mode reads structured assay rows; `id_only` consumes an ID list and expands via `assay_chembl_id__in`. Provider config supplies base URL, pagination, and retry/timeout limits for API mode.
- **Outputs**: Column-ordered assay dataset with deterministic serialization for lists/dicts plus generated metadata columns and QC metadata sidecars (`chembl_release`, `database_version`, timestamps).

## Ports and adapters

- `ExtractionServiceABC` → `ChemblExtractionServiceImpl` with request builder, retry/backoff, and metadata fetch support.
- `NormalizationServiceABC` → Chembl-specific normalization service injected into `ChemblTransformerImpl`.
- `EntityModelRegistryABC` feeds `ChemblRecordMapper` for consistent assay field mapping.
- `LoaderABC` + `RunMetadataBuilderProtocol` handle persistence and metadata enrichment.
- Record sources: `CsvRecordSourceImpl` and `IdListRecordSourceImpl` map file inputs into the extraction pipeline.

## Schemas

- Raw payload guardrails: `AssayRawModel` validates assay identifiers, optional nested structures, and numeric ranges before mapping.
- Output contract: `ASSAY_OUTPUT_COLUMNS` defines canonical order for assay outputs; the pipeline contract links `schema_out` to the Pandera assay schema enforced during validation.
