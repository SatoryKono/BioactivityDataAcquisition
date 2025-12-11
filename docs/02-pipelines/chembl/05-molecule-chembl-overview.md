# 05 Molecule Chembl Overview

## Overview

- Pipeline ID `chembl.molecule` is configured in `configs/pipelines/chembl/molecule.yaml` with `entity: molecule`, primary key `molecule_chembl_id`, `input_mode: id_only`, and `serialization_mode: pipe` for nested structure fields.
- `ChemblPipelineFactory` builds `ChemblPipelineBase` instances with Chembl-specific extraction, normalization, validation, hashing, and loader services resolved from the pipeline container.
- `resolve_primary_key_with_filter` derives `molecule_chembl_id__in` to batch API requests and expand ID lists for offline modes.

## Flow: extract → transform → validate → export

1. **Extract**: `ChemblPipelineBase` wires `ExtractStage` with `ChemblExtractionServiceImpl` and `ChemblRecordMapper` to stream molecule payloads. `RecordSourceResolver` switches between API mode and file-backed inputs (`CsvRecordSourceImpl` or `IdListRecordSourceImpl`) based on configuration, applying `molecule_chembl_id__in` for ID batches.
2. **Transform**: `ChemblTransformerImpl` normalizes molecule payloads via the Chembl-specific `NormalizationServiceABC`, serializes nested structure/properties with `serialize_nested` (`pipe` mode), enforces contract column order, and drops rows missing required non-generated fields. Post-transform hashing/indexing/timestamp enrichment is applied automatically.
3. **Validate**: `ValidationService` aligns output with `MOLECULE_OUTPUT_COLUMNS` and the Pandera molecule schema defined in the pipeline contract, ensuring deterministic columns and constraint enforcement.
4. **Export**: The configured `LoaderABC` writes validated molecules to `output_path`, while the metadata builder records `chembl_release` and last-endpoint details from `ChemblPipelineBase._enrich_context`.

## Inputs and outputs

- **Inputs**: API streaming by default; `csv` mode reads structured molecule rows; `id_only` mode consumes molecule IDs and queries via `molecule_chembl_id__in`. Provider config carries base URL, pagination, retries, and rate limits.
- **Outputs**: Column-ordered molecule dataset with deterministic serialization for nested fields plus generated metadata columns (hashes, index, timestamps, release version).

## Ports and adapters

- `ExtractionServiceABC` → `ChemblExtractionServiceImpl` with request builder, retry/backoff, and metadata fetch support.
- `NormalizationServiceABC` → Chembl normalization service injected into `ChemblTransformerImpl`.
- `EntityModelRegistryABC` feeds `ChemblRecordMapper` for molecule mapping.
- `LoaderABC` + `RunMetadataBuilderProtocol` handle persistence and metadata enrichment.
- Record sources: `CsvRecordSourceImpl` and `IdListRecordSourceImpl` adapt CSV/ID-list inputs into the extraction flow.

## Schemas

- Raw payload guardrails: `MoleculeRawModel` validates molecule identifiers, structures, and properties before mapping.
- Output contract: `MOLECULE_OUTPUT_COLUMNS` defines canonical order; the pipeline contract binds `schema_out` to the molecule Pandera schema enforced during validation.
