# Architecture Audit Report — Data Schemas

Date: 2026-02-18

Scope: all 21 configured pipelines in `configs/pipelines/**`.

## Executive Summary

- Total pipelines audited: 21.
- Issues detected: 9 structural concerns (see sections II/III).
- Content hash algorithm is centralized and deterministic (`sha256(provider + canonical_json(normalized_record))`).
- DQ rules are externalized per ADR-027 (entity YAML files), but strictness varies by pipeline.

## I. Карта схем пайплайна

### 1) Общая информация (все пайплайны)

| Pipeline                      | Provider        | Entity                 | Primary keys     | Silver mode | Gold mode | Silver partition | Bronze model                | Pandera Silver                   | Gold contract                        |
| ----------------------------- | --------------- | ---------------------- | ---------------- | ----------- | --------- | ---------------- | --------------------------- | -------------------------------- | ------------------------------------ |
| chembl_activity               | chembl          | activity               | activity_id      | merge       | append    | —                | ChemblActivityRecord        | ActivitySchema                   | ChEMBLActivityGoldSchema             |
| chembl_assay                  | chembl          | assay                  | assay_id         | merge       | scd2      | assay_type       | ChemblAssayRecord           | AssaySchema                      | ChEMBLAssayGoldSchema                |
| chembl_assay_parameters       | chembl          | assay_parameters       | assay_param_id   | merge       | scd2      | type             | raw dict / no typed model   | AssayParametersSchema            | ChEMBLAssayParametersGoldSchema      |
| chembl_cell_line              | chembl          | cell_line              | cell_id          | merge       | scd2      | —                | ChemblCellLineRecord        | CellLineSchema                   | ChEMBLCellLineGoldSchema             |
| chembl_compound_record        | chembl          | compound_record        | record_id        | merge       | scd2      | —                | raw dict / no typed model   | CompoundRecordSchema             | ChEMBLCompoundRecordGoldSchema       |
| chembl_molecule               | chembl          | molecule               | molecule_id      | merge       | scd2      | molecule_type    | ChemblMoleculeRecord        | MoleculeSchema                   | ChEMBLMoleculeGoldSchema             |
| chembl_protein_class          | chembl          | protein_class          | protein_class_id | merge       | scd2      | class_level      | raw dict / no typed model   | ProteinClassificationSchema      | ChEMBLProteinClassGoldSchema         |
| chembl_publication            | chembl          | publication            | publication_id   | merge       | scd2      | —                | ChemblPublicationApiRecord  | ChemblPublicationSchema          | ChEMBLDocumentGoldSchema             |
| chembl_publication_similarity | chembl          | publication_similarity | sim_id           | merge       | overwrite | —                | raw dict / no typed model   | PublicationSimilaritySchema      | ChEMBLDocumentSimilarityGoldSchema   |
| chembl_publication_term       | chembl          | publication_term       | entity_id        | merge       | overwrite | term_type        | raw dict / no typed model   | PublicationTermSchema            | ChEMBLDocumentTermGoldSchema         |
| chembl_subcellular_fraction   | chembl          | subcellular_fraction   | entity_id        | merge       | scd2      | —                | raw dict / no typed model   | —                                | ChEMBLSubcellularFractionGoldSchema  |
| chembl_target                 | chembl          | target                 | target_id        | merge       | scd2      | target_type      | ChemblTargetRecord          | TargetSchema                     | ChEMBLTargetGoldSchema               |
| chembl_target_component       | chembl          | target_component       | component_id     | merge       | scd2      | organism         | ChemblTargetComponentRecord | TargetComponentSchema            | ChEMBLTargetComponentGoldSchema      |
| chembl_tissue                 | chembl          | tissue                 | tissue_id        | merge       | scd2      | —                | raw dict / no typed model   | —                                | ChEMBLTissueGoldSchema               |
| crossref_publication          | crossref        | publication            | doi              | merge       | scd2      | —                | CrossRefPublicationRecord   | PublicationEnrichedSchema        | CrossRefPublicationGoldSchema        |
| openalex_publication          | openalex        | publication            | openalex_id      | merge       | scd2      | —                | raw dict / no typed model   | OpenAlexPublicationSchema        | OpenAlexPublicationGoldSchema        |
| pubchem_compound              | pubchem         | compound               | molecule_id      | merge       | scd2      | batch_date       | PubchemMoleculeApiRecord    | PubchemMoleculeSchema            | PubChemCompoundGoldSchema            |
| pubmed_publication            | pubmed          | publication            | pmid             | merge       | scd2      | —                | PubMedArticleRecord         | PubMedPublicationSchema          | PubMedPublicationGoldSchema          |
| semanticscholar_publication   | semanticscholar | publication            | paper_id         | merge       | scd2      | —                | raw dict / no typed model   | SemanticScholarPublicationSchema | SemanticScholarPublicationGoldSchema |
| uniprot_idmapping             | uniprot         | idmapping              | target_id        | merge       | scd2      | —                | raw dict / no typed model   | IDMappingSchema                  | UniProtIDMappingGoldSchema           |
| uniprot_protein               | uniprot         | protein                | accession        | merge       | scd2      | organism         | UniProtProteinRecord        | UniprotTargetSchema              | UniProtProteinGoldSchema             |

### 2) Детализация по каждому пайплайну

#### chembl_activity

- **Provider/Entity**: `chembl/activity`.
- **Bronze**: JSONL append, модель источника: `ChemblActivityRecord`; метаданные слоя `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index` добавляются на Silver этапе.
- **Silver**: `ActivitySchema`; полей: 56; mandatory (nullable=False): 3; primary keys: activity_id.
- **Gold**: `ChEMBLActivityGoldSchema`; полей: 61; mandatory: 8; режим записи: `append`.
- **DQ**: field/cross/conditional = 5/2/2; required-поля: activity_id.
- **Rename chain Silver→Gold**: line 185: renames={"action_type_action_type": "action_type"},
- **Content hash**: единый алгоритм доменного слоя (нормализация + canonical JSON + SHA256); исключаются meta fields и `_dq_*`.
- **Partition strategy**: без партиционирования (potential scan amplification).
- **Risk**: nullable-int coercion через float для полей: toid, original_activity_id, target_taxonomy_id.

#### chembl_assay

- **Provider/Entity**: `chembl/assay`.
- **Bronze**: JSONL append, модель источника: `ChemblAssayRecord`; метаданные слоя `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index` добавляются на Silver этапе.
- **Silver**: `AssaySchema`; полей: 37; mandatory (nullable=False): 1; primary keys: assay_id.
- **Gold**: `ChEMBLAssayGoldSchema`; полей: 44; mandatory: 7; режим записи: `scd2`.
- **DQ**: field/cross/conditional = 4/1/0; required-поля: assay_id.
- **Rename chain Silver→Gold**: line 46: _VARIANT_RENAMES: dict[str, str] = {; line 64: data, "variant_", \_VARIANT_FIELDS, renames=\_VARIANT_RENAMES
- **Content hash**: единый алгоритм доменного слоя (нормализация + canonical JSON + SHA256); исключаются meta fields и `_dq_*`.
- **Partition strategy**: assay_type
- **Risk**: nullable-int coercion через float для полей: assay_taxonomy_id, variant_taxonomy_id.

#### chembl_assay_parameters

- **Provider/Entity**: `chembl/assay_parameters`.
- **Bronze**: JSONL append, модель источника: `нет явной Pydantic-модели (raw JSON/dict)`; метаданные слоя `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index` добавляются на Silver этапе.
- **Silver**: `AssayParametersSchema`; полей: 13; mandatory (nullable=False): 2; primary keys: assay_param_id.
- **Gold**: `ChEMBLAssayParametersGoldSchema`; полей: 20; mandatory: 9; режим записи: `scd2`.
- **DQ**: field/cross/conditional = 3/1/0; required-поля: не заданы явно в field_validations.
- **Rename chain Silver→Gold**: явные renames не обнаружены (identity mapping или field_specs без rename).
- **Content hash**: единый алгоритм доменного слоя (нормализация + canonical JSON + SHA256); исключаются meta fields и `_dq_*`.
- **Partition strategy**: type

#### chembl_cell_line

- **Provider/Entity**: `chembl/cell_line`.
- **Bronze**: JSONL append, модель источника: `ChemblCellLineRecord`; метаданные слоя `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index` добавляются на Silver этапе.
- **Silver**: `CellLineSchema`; полей: 11; mandatory (nullable=False): 2; primary keys: cell_id.
- **Gold**: `ChEMBLCellLineGoldSchema`; полей: 16; mandatory: 8; режим записи: `scd2`.
- **DQ**: field/cross/conditional = 4/0/0; required-поля: не заданы явно в field_validations.
- **Rename chain Silver→Gold**: явные renames не обнаружены (identity mapping или field_specs без rename).
- **Content hash**: единый алгоритм доменного слоя (нормализация + canonical JSON + SHA256); исключаются meta fields и `_dq_*`.
- **Partition strategy**: без партиционирования (potential scan amplification).
- **Risk**: nullable-int coercion через float для полей: cell_source_taxonomy_id.

#### chembl_compound_record

- **Provider/Entity**: `chembl/compound_record`.
- **Bronze**: JSONL append, модель источника: `нет явной Pydantic-модели (raw JSON/dict)`; метаданные слоя `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index` добавляются на Silver этапе.
- **Silver**: `CompoundRecordSchema`; полей: 7; mandatory (nullable=False): 4; primary keys: record_id.
- **Gold**: `ChEMBLCompoundRecordGoldSchema`; полей: 14; mandatory: 10; режим записи: `scd2`.
- **DQ**: field/cross/conditional = 4/1/0; required-поля: не заданы явно в field_validations.
- **Rename chain Silver→Gold**: явные renames не обнаружены (identity mapping или field_specs без rename).
- **Content hash**: единый алгоритм доменного слоя (нормализация + canonical JSON + SHA256); исключаются meta fields и `_dq_*`.
- **Partition strategy**: без партиционирования (potential scan amplification).

#### chembl_molecule

- **Provider/Entity**: `chembl/molecule`.
- **Bronze**: JSONL append, модель источника: `ChemblMoleculeRecord`; метаданные слоя `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index` добавляются на Silver этапе.
- **Silver**: `MoleculeSchema`; полей: 52; mandatory (nullable=False): 1; primary keys: molecule_id.
- **Gold**: `ChEMBLMoleculeGoldSchema`; полей: 59; mandatory: 7; режим записи: `scd2`.
- **DQ**: field/cross/conditional = 9/1/0; required-поля: molecule_id.
- **Rename chain Silver→Gold**: line 39: \_HIERARCHY_RENAMES: dict[str, str] = {; line 61: \_PROPERTIES_RENAMES: dict[str, str] = {; line 84: \_STRUCTURES_RENAMES: dict[str, str] = {; line 194: renames=\_STRUCTURES_RENAMES,
- **Content hash**: единый алгоритм доменного слоя (нормализация + canonical JSON + SHA256); исключаются meta fields и `_dq_*`.
- **Partition strategy**: molecule_type

#### chembl_protein_class

- **Provider/Entity**: `chembl/protein_class`.
- **Bronze**: JSONL append, модель источника: `нет явной Pydantic-модели (raw JSON/dict)`; метаданные слоя `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index` добавляются на Silver этапе.
- **Silver**: `ProteinClassificationSchema`; полей: 10; mandatory (nullable=False): 1; primary keys: protein_class_id.
- **Gold**: `ChEMBLProteinClassGoldSchema`; полей: 17; mandatory: 7; режим записи: `scd2`.
- **DQ**: field/cross/conditional = 4/1/0; required-поля: не заданы явно в field_validations.
- **Rename chain Silver→Gold**: явные renames не обнаружены (identity mapping или field_specs без rename).
- **Content hash**: единый алгоритм доменного слоя (нормализация + canonical JSON + SHA256); исключаются meta fields и `_dq_*`.
- **Partition strategy**: class_level

#### chembl_publication

- **Provider/Entity**: `chembl/publication`.
- **Bronze**: JSONL append, модель источника: `ChemblPublicationApiRecord`; метаданные слоя `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index` добавляются на Silver этапе.
- **Silver**: `ChemblPublicationSchema`; полей: 10; mandatory (nullable=False): 2; primary keys: publication_id.
- **Gold**: `ChEMBLDocumentGoldSchema`; полей: 33; mandatory: 9; режим записи: `scd2`.
- **DQ**: field/cross/conditional = 11/2/1; required-поля: не заданы явно в field_validations.
- **Rename chain Silver→Gold**: явные renames не обнаружены (identity mapping или field_specs без rename).
- **Content hash**: единый алгоритм доменного слоя (нормализация + canonical JSON + SHA256); исключаются meta fields и `_dq_*`.
- **Partition strategy**: без партиционирования (potential scan amplification).

#### chembl_publication_similarity

- **Provider/Entity**: `chembl/publication_similarity`.
- **Bronze**: JSONL append, модель источника: `нет явной Pydantic-модели (raw JSON/dict)`; метаданные слоя `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index` добавляются на Silver этапе.
- **Silver**: `PublicationSimilaritySchema`; полей: 9; mandatory (nullable=False): 3; primary keys: sim_id.
- **Gold**: `ChEMBLDocumentSimilarityGoldSchema`; полей: 16; mandatory: 9; режим записи: `overwrite`.
- **DQ**: field/cross/conditional = 5/1/0; required-поля: не заданы явно в field_validations.
- **Rename chain Silver→Gold**: явные renames не обнаружены (identity mapping или field_specs без rename).
- **Content hash**: единый алгоритм доменного слоя (нормализация + canonical JSON + SHA256); исключаются meta fields и `_dq_*`.
- **Partition strategy**: без партиционирования (potential scan amplification).
- **Risk**: nullable-int coercion через float для полей: tid_tani.

#### chembl_publication_term

- **Provider/Entity**: `chembl/publication_term`.
- **Bronze**: JSONL append, модель источника: `нет явной Pydantic-модели (raw JSON/dict)`; метаданные слоя `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index` добавляются на Silver этапе.
- **Silver**: `PublicationTermSchema`; полей: 5; mandatory (nullable=False): 3; primary keys: entity_id.
- **Gold**: `ChEMBLDocumentTermGoldSchema`; полей: 12; mandatory: 9; режим записи: `overwrite`.
- **DQ**: field/cross/conditional = 4/1/0; required-поля: не заданы явно в field_validations.
- **Rename chain Silver→Gold**: явные renames не обнаружены (identity mapping или field_specs без rename).
- **Content hash**: единый алгоритм доменного слоя (нормализация + canonical JSON + SHA256); исключаются meta fields и `_dq_*`.
- **Partition strategy**: term_type

#### chembl_subcellular_fraction

- **Provider/Entity**: `chembl/subcellular_fraction`.
- **Bronze**: JSONL append, модель источника: `нет явной Pydantic-модели (raw JSON/dict)`; метаданные слоя `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index` добавляются на Silver этапе.
- **Silver**: `нет привязки Pandera`; полей: 0; mandatory (nullable=False): 0; primary keys: entity_id.
- **Gold**: `ChEMBLSubcellularFractionGoldSchema`; полей: 10; mandatory: 7; режим записи: `scd2`.
- **DQ**: field/cross/conditional = 4/0/0; required-поля: не заданы явно в field_validations.
- **Rename chain Silver→Gold**: явные renames не обнаружены (identity mapping или field_specs без rename).
- **Content hash**: единый алгоритм доменного слоя (нормализация + canonical JSON + SHA256); исключаются meta fields и `_dq_*`.
- **Partition strategy**: без партиционирования (potential scan amplification).

#### chembl_target

- **Provider/Entity**: `chembl/target`.
- **Bronze**: JSONL append, модель источника: `ChemblTargetRecord`; метаданные слоя `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index` добавляются на Silver этапе.
- **Silver**: `TargetSchema`; полей: 18; mandatory (nullable=False): 1; primary keys: target_id.
- **Gold**: `ChEMBLTargetGoldSchema`; полей: 24; mandatory: 7; режим записи: `scd2`.
- **DQ**: field/cross/conditional = 4/1/0; required-поля: target_id.
- **Rename chain Silver→Gold**: явные renames не обнаружены (identity mapping или field_specs без rename).
- **Content hash**: единый алгоритм доменного слоя (нормализация + canonical JSON + SHA256); исключаются meta fields и `_dq_*`.
- **Partition strategy**: target_type
- **Risk**: nullable-int coercion через float для полей: taxonomy_id, primary_component_id.

#### chembl_target_component

- **Provider/Entity**: `chembl/target_component`.
- **Bronze**: JSONL append, модель источника: `ChemblTargetComponentRecord`; метаданные слоя `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index` добавляются на Silver этапе.
- **Silver**: `TargetComponentSchema`; полей: 11; mandatory (nullable=False): 1; primary keys: component_id.
- **Gold**: `ChEMBLTargetComponentGoldSchema`; полей: 18; mandatory: 7; режим записи: `scd2`.
- **DQ**: field/cross/conditional = 4/1/0; required-поля: не заданы явно в field_validations.
- **Rename chain Silver→Gold**: явные renames не обнаружены (identity mapping или field_specs без rename).
- **Content hash**: единый алгоритм доменного слоя (нормализация + canonical JSON + SHA256); исключаются meta fields и `_dq_*`.
- **Partition strategy**: organism
- **Risk**: nullable-int coercion через float для полей: protein_classification_id.

#### chembl_tissue

- **Provider/Entity**: `chembl/tissue`.
- **Bronze**: JSONL append, модель источника: `нет явной Pydantic-модели (raw JSON/dict)`; метаданные слоя `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index` добавляются на Silver этапе.
- **Silver**: `нет привязки Pandera`; полей: 0; mandatory (nullable=False): 0; primary keys: tissue_id.
- **Gold**: `ChEMBLTissueGoldSchema`; полей: 11; mandatory: 6; режим записи: `scd2`.
- **DQ**: field/cross/conditional = 6/0/0; required-поля: не заданы явно в field_validations.
- **Rename chain Silver→Gold**: явные renames не обнаружены (identity mapping или field_specs без rename).
- **Content hash**: единый алгоритм доменного слоя (нормализация + canonical JSON + SHA256); исключаются meta fields и `_dq_*`.
- **Partition strategy**: без партиционирования (potential scan amplification).

#### crossref_publication

- **Provider/Entity**: `crossref/publication`.
- **Bronze**: JSONL append, модель источника: `CrossRefPublicationRecord`; метаданные слоя `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index` добавляются на Silver этапе.
- **Silver**: `PublicationEnrichedSchema`; полей: 23; mandatory (nullable=False): 2; primary keys: doi.
- **Gold**: `CrossRefPublicationGoldSchema`; полей: 44; mandatory: 11; режим записи: `scd2`.
- **DQ**: field/cross/conditional = 9/1/1; required-поля: не заданы явно в field_validations.
- **Rename chain Silver→Gold**: явные renames не обнаружены (identity mapping или field_specs без rename).
- **Content hash**: единый алгоритм доменного слоя (нормализация + canonical JSON + SHA256); исключаются meta fields и `_dq_*`.
- **Partition strategy**: без партиционирования (potential scan amplification).

#### openalex_publication

- **Provider/Entity**: `openalex/publication`.
- **Bronze**: JSONL append, модель источника: `нет явной Pydantic-модели (raw JSON/dict)`; метаданные слоя `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index` добавляются на Silver этапе.
- **Silver**: `OpenAlexPublicationSchema`; полей: 20; mandatory (nullable=False): 3; primary keys: openalex_id.
- **Gold**: `OpenAlexPublicationGoldSchema`; полей: 48; mandatory: 12; режим записи: `scd2`.
- **DQ**: field/cross/conditional = 12/1/1; required-поля: не заданы явно в field_validations.
- **Rename chain Silver→Gold**: явные renames не обнаружены (identity mapping или field_specs без rename).
- **Content hash**: единый алгоритм доменного слоя (нормализация + canonical JSON + SHA256); исключаются meta fields и `_dq_*`.
- **Partition strategy**: без партиционирования (potential scan amplification).

#### pubchem_compound

- **Provider/Entity**: `pubchem/compound`.
- **Bronze**: JSONL append, модель источника: `PubchemMoleculeApiRecord`; метаданные слоя `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index` добавляются на Silver этапе.
- **Silver**: `PubchemMoleculeSchema`; полей: 40; mandatory (nullable=False): 1; primary keys: molecule_id.
- **Gold**: `PubChemCompoundGoldSchema`; полей: 17; mandatory: 7; режим записи: `scd2`.
- **DQ**: field/cross/conditional = 9/1/0; required-поля: molecule_id.
- **Rename chain Silver→Gold**: явные renames не обнаружены (identity mapping или field_specs без rename).
- **Content hash**: единый алгоритм доменного слоя (нормализация + canonical JSON + SHA256); исключаются meta fields и `_dq_*`.
- **Partition strategy**: batch_date

#### pubmed_publication

- **Provider/Entity**: `pubmed/publication`.
- **Bronze**: JSONL append, модель источника: `PubMedArticleRecord`; метаданные слоя `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index` добавляются на Silver этапе.
- **Silver**: `PubMedPublicationSchema`; полей: 37; mandatory (nullable=False): 3; primary keys: pmid.
- **Gold**: `PubMedPublicationGoldSchema`; полей: 62; mandatory: 12; режим записи: `scd2`.
- **DQ**: field/cross/conditional = 11/2/0; required-поля: не заданы явно в field_validations.
- **Rename chain Silver→Gold**: явные renames не обнаружены (identity mapping или field_specs без rename).
- **Content hash**: единый алгоритм доменного слоя (нормализация + canonical JSON + SHA256); исключаются meta fields и `_dq_*`.
- **Partition strategy**: без партиционирования (potential scan amplification).

#### semanticscholar_publication

- **Provider/Entity**: `semanticscholar/publication`.
- **Bronze**: JSONL append, модель источника: `нет явной Pydantic-модели (raw JSON/dict)`; метаданные слоя `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index` добавляются на Silver этапе.
- **Silver**: `SemanticScholarPublicationSchema`; полей: 17; mandatory (nullable=False): 2; primary keys: paper_id.
- **Gold**: `SemanticScholarPublicationGoldSchema`; полей: 44; mandatory: 11; режим записи: `scd2`.
- **DQ**: field/cross/conditional = 11/1/1; required-поля: не заданы явно в field_validations.
- **Rename chain Silver→Gold**: явные renames не обнаружены (identity mapping или field_specs без rename).
- **Content hash**: единый алгоритм доменного слоя (нормализация + canonical JSON + SHA256); исключаются meta fields и `_dq_*`.
- **Partition strategy**: без партиционирования (potential scan amplification).

#### uniprot_idmapping

- **Provider/Entity**: `uniprot/idmapping`.
- **Bronze**: JSONL append, модель источника: `нет явной Pydantic-модели (raw JSON/dict)`; метаданные слоя `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index` добавляются на Silver этапе.
- **Silver**: `IDMappingSchema`; полей: 14; mandatory (nullable=False): 2; primary keys: target_id.
- **Gold**: `UniProtIDMappingGoldSchema`; полей: 22; mandatory: 9; режим записи: `scd2`.
- **DQ**: field/cross/conditional = 3/0/1; required-поля: не заданы явно в field_validations.
- **Rename chain Silver→Gold**: явные renames не обнаружены (identity mapping или field_specs без rename).
- **Content hash**: единый алгоритм доменного слоя (нормализация + canonical JSON + SHA256); исключаются meta fields и `_dq_*`.
- **Partition strategy**: без партиционирования (potential scan amplification).
- **Risk**: nullable-int coercion через float для полей: taxonomy_id.

#### uniprot_protein

- **Provider/Entity**: `uniprot/protein`.
- **Bronze**: JSONL append, модель источника: `UniProtProteinRecord`; метаданные слоя `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index` добавляются на Silver этапе.
- **Silver**: `UniprotTargetSchema`; полей: 0; mandatory (nullable=False): 0; primary keys: accession.
- **Gold**: `UniProtProteinGoldSchema`; полей: 35; mandatory: 7; режим записи: `scd2`.
- **DQ**: field/cross/conditional = 17/1/0; required-поля: не заданы явно в field_validations.
- **Rename chain Silver→Gold**: явные renames не обнаружены (identity mapping или field_specs без rename).
- **Content hash**: единый алгоритм доменного слоя (нормализация + canonical JSON + SHA256); исключаются meta fields и `_dq_*`.
- **Partition strategy**: organism

## II. Архитектурные проблемы

| ID  | Pipeline                      | Категория                | Проблема                                                                                           | Риск                               | Приоритет |
| --- | ----------------------------- | ------------------------ | -------------------------------------------------------------------------------------------------- | ---------------------------------- | --------- |
| A01 | chembl_activity               | Type inconsistency       | Nullable-int represented as float in Silver                                                        | Высокий (breaking analytics/joins) | P1        |
| A02 | chembl_assay                  | Type inconsistency       | Nullable-int represented as float in Silver                                                        | Высокий (breaking analytics/joins) | P1        |
| A03 | chembl_cell_line              | Type inconsistency       | Nullable-int represented as float in Silver                                                        | Высокий (breaking analytics/joins) | P1        |
| A04 | chembl_publication_similarity | Type inconsistency       | Nullable-int represented as float in Silver                                                        | Высокий (breaking analytics/joins) | P1        |
| A05 | chembl_subcellular_fraction   | Schema duplication       | Missing Pandera Silver schema binding                                                              | Средний (drift/validation gap)     | P2        |
| A06 | chembl_target                 | Type inconsistency       | Nullable-int represented as float in Silver                                                        | Высокий (breaking analytics/joins) | P1        |
| A07 | chembl_target_component       | Type inconsistency       | Nullable-int represented as float in Silver                                                        | Высокий (breaking analytics/joins) | P1        |
| A08 | chembl_tissue                 | Schema duplication       | Missing Pandera Silver schema binding                                                              | Средний (drift/validation gap)     | P2        |
| A09 | uniprot_idmapping             | Type inconsistency       | Nullable-int represented as float in Silver                                                        | Высокий (breaking analytics/joins) | P1        |
| A10 | ALL                           | Inconsistent naming      | provider-specific id aliases (e.g., assay_chembl_id→assay_id) partially normalized in transformers | Medium                             | P2        |
| A11 | ALL                           | Hidden coupling          | Gold contracts depend on transformer flattening conventions not formalized in shared contract DSL  | High                               | P1        |
| A12 | ALL                           | Weak primary key         | single-field PK in some pipelines may not cover semantic uniqueness for historical snapshots       | High                               | P1        |
| A13 | ALL                           | Content hash instability | exclude_none flag and serializer choices can diverge if not pinned in one policy                   | Medium                             | P2        |

## III. Общесистемные проблемы

- Повторяемые metadata-поля (`entity_id`, `content_hash`, `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_error`, `_dq_warn`) унифицированы на Silver, но в Bronze они не типизированы единым контрактом.
- Наблюдается неоднородность nullable/int: часть идентификаторов хранится как `float` для nullable-сценариев (например `taxonomy_id`, `toid`, `original_activity_id`).
- Большинство таблиц не используют `partition_by`, что повышает стоимость сканов и merge при росте объема.
- Rename-цепочки сосредоточены в отдельных трансформерах (assay/molecule/activity), но нет централизованного реестра mappings (риск hidden coupling).
- Gold-публикационные контракты между provider-пайплайнами близки, но не полностью вынесены в shared contract (дублирование).
- DQ externalization внедрена, но rule density сильно различается по сущностям; нет единого минимального baseline для required/range/enum на всех провайдерах.

## IV. План улучшений

### 1) Немедленные улучшения (Low Risk)

| Change                                                                             | Impact                          | Breaking                              | ADR                         | Migration                                                         |
| ---------------------------------------------------------------------------------- | ------------------------------- | ------------------------------------- | --------------------------- | ----------------------------------------------------------------- |
| Нормализовать nullable-int поля (`float` → nullable integer dtype в Pandera/Delta) | Повышение точности join/BI      | Non-breaking (с кастами в write path) | Нет (обновление стандартов) | Backfill Silver с safe_cast + dual-read период                    |
| Ввести baseline DQ profile (required + basic ranges) для всех entities             | Снижение silent data corruption | Non-breaking                          | Нет                         | Добавить provider/entity defaults и включить мониторинг fail-rate |
| Унифицировать naming aliases в одном mapping registry                              | Снижение hidden coupling        | Non-breaking                          | Нет                         | Вынести словари renames в shared module, покрыть тестами          |

### 2) Среднесрочные улучшения (Refactoring Phase)

| Change                                                           | Impact                             | Breaking                   | ADR                     | Migration                                                     |
| ---------------------------------------------------------------- | ---------------------------------- | -------------------------- | ----------------------- | ------------------------------------------------------------- |
| Пересборка Gold contracts через shared publication/molecule ядра | Меньше дублирования и domain drift | Potentially breaking       | Да (обновление ADR-034) | Версионирование контрактов v1→v2, compatibility view          |
| Унифицировать PK strategy (бизнес-ключ + provider + version)     | Корректный SCD2 и дедупликация     | Breaking для merge условий | Да                      | Dual-key phase, затем switch merge predicate                  |
| Централизовать Silver→Gold rename chains (config-driven)         | Прозрачность трансформаций         | Non-breaking               | Нет                     | Инкрементальный перенос transform logic в declarative mapping |

### 3) Архитектурные изменения (Breaking Phase)

| Change                                                                                                        | Impact                               | Breaking                         | ADR | Migration                                                              |
| ------------------------------------------------------------------------------------------------------------- | ------------------------------------ | -------------------------------- | --- | ---------------------------------------------------------------------- |
| Ввести унифицированный Bronze typed envelope (metadata + payload)                                             | Контролируемый schema drift на входе | Breaking для ingest adapters     | Да  | Параллельная запись old/new Bronze, cutover после валидации            |
| Пересмотреть Content Hash policy (зафиксировать exclude_none и canonical serializer на уровне config version) | Детерминизм кросс-версий             | Breaking для исторических hashes | Да  | Пересчет hash в shadow-колонку, затем переключение                     |
| Декомпозиция перегруженных Gold таблиц (особенно publication) на ядро + satellite                             | Уменьшение ширины/латентности        | Breaking API contracts           | Да  | Introduce new tables + compatibility views + phased consumer migration |

## V. Target Schema Architecture (Целевая модель)

- **Bronze**: единый envelope `{metadata, payload}`; metadata строгая, payload provider-specific; append-only JSONL+zstd.
- **Silver**: единый системный префикс колонок + нормализованные бизнес-ключи + DQ suffix; обязательный Pandera validation и Delta schema registry.
- **Gold**: строгие API contracts по ADR-018, версия контракта обязательна, backward-compatibility policy фиксирована.
- **Metadata policy**: полная унификация OutputMetadata по ADR-029 для всех слоев и пайплайнов.
- **Key strategy**: `entity_id` как технический ключ + явный business composite key + SCD2 technical columns в Gold.
- **Table template**: `SYSTEM_PREFIX + CORE_FIELDS + PROVIDER_EXTENSION + DQ_SUFFIX` с одинаковым порядком колонок и naming policy.

## Verification Log

- `rg --files | head -200`
- `sed -n '180,520p' src/bioetl/composition/factories/pipeline_factories.py`
- `sed -n '1,220p' configs/pipelines/chembl/activity.yaml`
- `sed -n '1,220p' configs/quality/entities/chembl/activity.yaml`
- `sed -n '1,140p' src/bioetl/infrastructure/schemas/silver.py`
- `sed -n '1,260p' src/bioetl/domain/schemas/chembl/activity.py`
- `sed -n '1,260p' src/bioetl/infrastructure/adapters/chembl/models.py`
- `sed -n '1,280p' src/bioetl/domain/transformations.py`
- `python ... (AST+YAML audit generator)`
