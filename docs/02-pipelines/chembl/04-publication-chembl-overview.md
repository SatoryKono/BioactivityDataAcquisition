# 04 Publication Chembl Overview

## Overview

- Pipeline ID `chembl.publication` is defined in `configs/pipelines/chembl/publication.yaml` with `entity: publication`, primary key `document_chembl_id`, `input_mode: id_only`, and `serialization_mode: pipe` for nested metadata fields.
- `ChemblPipelineFactory` creates `ChemblPipelineBase` instances that wire extraction, normalization, validation, hashing, and loader services from the pipeline container for publication/document runs.
- Primary key resolution via `resolve_primary_key_with_filter` yields `document_chembl_id__in` for batched API filters and ID-list ingestion.

## Flow: extract → transform → validate → export

1. **Extract**: `ChemblPipelineBase` composes `ExtractStage` with `ChemblExtractionServiceImpl` and `ChemblRecordMapper` to stream publication records. `RecordSourceResolver` toggles between API streaming and file-backed inputs (`CsvRecordSourceImpl` or `IdListRecordSourceImpl`) depending on mode, applying `document_chembl_id__in` when expanding ID lists.
2. **Transform**: `ChemblTransformerImpl` normalizes publication payloads through the Chembl-specific `NormalizationServiceABC`, serializes nested authors/keywords/journal metadata with `serialize_nested` (`pipe` mode), enforces contract column order, and drops rows missing non-generated required fields. Post-transform hashing, indexing, timestamps, and version metadata are attached automatically.
3. **Validate**: `ValidationService` enforces the publication pipeline contract, aligning columns to `PUBLICATION_OUTPUT_COLUMNS` and Pandera schema constraints for document outputs.
4. **Export**: `LoaderABC` instances persist validated batches to `output_path`, while the metadata builder captures `chembl_release` and last-endpoint hints from `ChemblPipelineBase._enrich_context` for `meta.yaml` and sidecars.

## Inputs and outputs

- **Inputs**: Default API streaming; `csv` mode reads structured publication rows; `id_only` mode consumes document IDs and queries via `document_chembl_id__in`. Provider config sets base URL, pagination, timeout, retry, and rate limit parameters.
- **Outputs**: Column-ordered publication dataset with deterministic serialization of nested fields plus generated metadata columns (`hash_row`, `hash_business_key`, `index`, timestamps, release version).

## Ports and adapters

- `ExtractionServiceABC` → `ChemblExtractionServiceImpl` with ChEMBL request builder and version lookup.
- `NormalizationServiceABC` → Chembl normalization service injected into `ChemblTransformerImpl`.
- `EntityModelRegistryABC` feeds `ChemblRecordMapper` for publication-specific mapping.
- `LoaderABC` + `RunMetadataBuilderProtocol` manage persistence and metadata enrichment.
- Record sources: `CsvRecordSourceImpl` and `IdListRecordSourceImpl` adapt CSV and ID-list inputs when not streaming directly from the API.

## Schemas

- Raw payload guardrails: `PublicationRawModel` validates document identifiers and optional nested metadata before mapping.
- Output contract: `PUBLICATION_OUTPUT_COLUMNS` provides canonical column order; the pipeline contract binds `schema_out` to the Pandera publication schema enforced during validation.
