# Pipeline Schema Audit — Full Inventory

Date: 2026-02-18

## I. Карта схем пайплайна

### 1) Общая матрица

| Pipeline                      | Provider        | Entity                 | Primary Keys     | Silver write mode | Gold write mode | Silver partition  | Gold contract                        | Silver Pandera                   | DQ config                                                   |
| ----------------------------- | --------------- | ---------------------- | ---------------- | ----------------- | --------------- | ----------------- | ------------------------------------ | -------------------------------- | ----------------------------------------------------------- |
| chembl_activity               | chembl          | activity               | activity_id      | merge             | append          | []                | ChEMBLActivityGoldSchema             | ActivitySchema                   | configs/quality/entities/chembl/activity.yaml               |
| chembl_assay                  | chembl          | assay                  | assay_id         | merge             | scd2            | ['assay_type']    | ChEMBLAssayGoldSchema                | AssaySchema                      | configs/quality/entities/chembl/assay.yaml                  |
| chembl_assay_parameters       | chembl          | assay_parameters       | assay_param_id   | merge             | scd2            | ['type']          | ChEMBLAssayParametersGoldSchema      | AssayParametersSchema            | configs/quality/entities/chembl/assay_parameters.yaml       |
| chembl_cell_line              | chembl          | cell_line              | cell_id          | merge             | scd2            | []                | ChEMBLCellLineGoldSchema             | CellLineSchema                   | configs/quality/entities/chembl/cell_line.yaml              |
| chembl_compound_record        | chembl          | compound_record        | record_id        | merge             | scd2            | []                | ChEMBLCompoundRecordGoldSchema       | CompoundRecordSchema             | configs/quality/entities/chembl/compound_record.yaml        |
| chembl_molecule               | chembl          | molecule               | molecule_id      | merge             | scd2            | ['molecule_type'] | ChEMBLMoleculeGoldSchema             | MoleculeSchema                   | configs/quality/entities/chembl/molecule.yaml               |
| chembl_protein_class          | chembl          | protein_class          | protein_class_id | merge             | scd2            | ['class_level']   | ChEMBLProteinClassGoldSchema         | ProteinClassificationSchema      | configs/quality/entities/chembl/protein_class.yaml          |
| chembl_publication            | chembl          | publication            | publication_id   | merge             | scd2            | []                | ChEMBLDocumentGoldSchema             | ChemblPublicationSchema          | configs/quality/entities/chembl/publication.yaml            |
| chembl_publication_similarity | chembl          | publication_similarity | sim_id           | merge             | overwrite       | []                | ChEMBLDocumentSimilarityGoldSchema   | PublicationSimilaritySchema      | configs/quality/entities/chembl/publication_similarity.yaml |
| chembl_publication_term       | chembl          | publication_term       | entity_id        | merge             | overwrite       | ['term_type']     | ChEMBLDocumentTermGoldSchema         | PublicationTermSchema            | configs/quality/entities/chembl/publication_term.yaml       |
| chembl_subcellular_fraction   | chembl          | subcellular_fraction   | entity_id        | merge             | scd2            | []                | ChEMBLSubcellularFractionGoldSchema  | -                                | configs/quality/entities/chembl/subcellular_fraction.yaml   |
| chembl_target                 | chembl          | target                 | target_id        | merge             | scd2            | ['target_type']   | ChEMBLTargetGoldSchema               | TargetSchema                     | configs/quality/entities/chembl/target.yaml                 |
| chembl_target_component       | chembl          | target_component       | component_id     | merge             | scd2            | ['organism']      | ChEMBLTargetComponentGoldSchema      | TargetComponentSchema            | configs/quality/entities/chembl/target_component.yaml       |
| chembl_tissue                 | chembl          | tissue                 | tissue_id        | merge             | scd2            | []                | ChEMBLTissueGoldSchema               | -                                | configs/quality/entities/chembl/tissue.yaml                 |
| crossref_publication          | crossref        | publication            | doi              | merge             | scd2            | []                | CrossRefPublicationGoldSchema        | PublicationEnrichedSchema        | configs/quality/entities/crossref/publication.yaml          |
| openalex_publication          | openalex        | publication            | openalex_id      | merge             | scd2            | []                | OpenAlexPublicationGoldSchema        | OpenAlexPublicationSchema        | configs/quality/entities/openalex/publication.yaml          |
| pubchem_compound              | pubchem         | compound               | molecule_id      | merge             | scd2            | ['batch_date']    | PubChemCompoundGoldSchema            | PubchemMoleculeSchema            | configs/quality/entities/pubchem/compound.yaml              |
| pubmed_publication            | pubmed          | publication            | pmid             | merge             | scd2            | []                | PubMedPublicationGoldSchema          | PubMedPublicationSchema          | configs/quality/entities/pubmed/publication.yaml            |
| semanticscholar_publication   | semanticscholar | publication            | paper_id         | merge             | scd2            | []                | SemanticScholarPublicationGoldSchema | SemanticScholarPublicationSchema | configs/quality/entities/semanticscholar/publication.yaml   |
| uniprot_idmapping             | uniprot         | idmapping              | target_id        | merge             | scd2            | []                | UniProtIDMappingGoldSchema           | IDMappingSchema                  | configs/quality/entities/uniprot/idmapping.yaml             |
| uniprot_protein               | uniprot         | protein                | accession        | merge             | scd2            | ['organism']      | UniProtProteinGoldSchema             | UniprotTargetSchema              | configs/quality/entities/uniprot/protein.yaml               |

### 1.1) Composite pipelines (config-driven)

| Composite pipeline    | Seed               | Dependencies / Enrichers                                       | Join strategy                | Key policy                            | Notes                                          |
| --------------------- | ------------------ | -------------------------------------------------------------- | ---------------------------- | ------------------------------------- | ---------------------------------------------- |
| composite_activity    | chembl_activity    | chembl_compound_record                                         | left_outer                   | join `(molecule_id, publication_id)`  | High coupling to ChEMBL field semantics.       |
| composite_assay       | chembl_assay       | chembl_cell_line, chembl_tissue                                | left_outer                   | join by assay-linked keys             | Wide denormalized assay context in output.     |
| composite_molecule    | chembl_molecule    | pubchem_compound                                               | left_outer                   | join by molecular identifiers         | Strong cross-provider rename pressure.         |
| composite_target      | chembl_target      | chembl_target_component                                        | left_outer                   | join by `target_id`/component linkage | Target hierarchy and component lineage merged. |
| composite_publication | chembl_publication | crossref/openalex/pubmed/semanticscholar publication pipelines | left_outer (priority-driven) | provider-qualified + canonical fields | Highest alias/duplication and drift surface.   |

Composite-пайплайны не регистрируются через `PIPELINE_CONFIGS` и работают через отдельный composite orchestrator; для них schema policy задается merge/column_groups конфигом, а не отдельными Pandera Silver классами.

### chembl_activity

#### 1. Общая информация

- Provider: `chembl`
- Entity: `activity`
- Pipeline name: `chembl_activity`
- Primary keys: `['activity_id']`
- Loading strategy: API extract → Bronze append JSONL → Silver merge/upsert → Gold `append`
- Write mode: Silver=`merge`, Gold=`append`

#### 2. Bronze Layer

- Формат хранения: JSONL + zstd (append-only, flat_structure enabled by base config).
- Структура записи: raw provider payload; nested JSON partially flattened at transformer stage.
- Метаданные: batch-level metadata sidecar + pipeline run metadata added downstream (`_run_id`, `_run_type`, `_ingestion_ts`).
- Потенциальный schema drift: высокий для publication pipelines и ChEMBL nested objects; управляется soft validation в Silver.
- Ключевые риски Bronze: nested JSON, nullable-int coercion, provider-specific enum drift.

#### 3. Silver Schema

| Поле                      | Тип     | Nullable | Source field              | Notes                         |
| ------------------------- | ------- | -------- | ------------------------- | ----------------------------- |
| entity_id                 | str     | No       | entity_id                 |                               |
| content_hash              | str     | No       | content_hash              |                               |
| \_run_id                  | str     | No       | \_run_id                  |                               |
| \_run_type                | str     | No       | \_run_type                |                               |
| \_source_batch_id         | str     | Yes      | \_source_batch_id         |                               |
| \_ingestion_ts            | str     | No       | \_ingestion_ts            |                               |
| \_index                   | int64   | No       | \_index                   |                               |
| \_dq_warn                 | bool    | No       | \_dq_warn                 |                               |
| \_dq_error                | bool    | No       | \_dq_error                |                               |
| activity_id               | str     | No       | activity_id               |                               |
| assay_id                  | str     | No       | assay_id                  |                               |
| molecule_id               | str     | No       | molecule_id               |                               |
| target_id                 | str     | Yes      | target_id                 |                               |
| publication_id            | str     | Yes      | publication_id            |                               |
| standard_relation         | str     | Yes      | standard_relation         |                               |
| standard_value            | float64 | Yes      | standard_value            |                               |
| standard_units            | str     | Yes      | standard_units            |                               |
| standard_type             | str     | Yes      | standard_type             |                               |
| standard_flag             | int64   | Yes      | standard_flag             |                               |
| pchembl_value             | float64 | Yes      | pchembl_value             |                               |
| data_validity_comment     | str     | Yes      | data_validity_comment     |                               |
| activity_comment          | str     | Yes      | activity_comment          |                               |
| potential_duplicate       | int64   | Yes      | potential_duplicate       |                               |
| bao_endpoint              | str     | Yes      | bao_endpoint              |                               |
| uo_units                  | str     | Yes      | uo_units                  |                               |
| qudt_units                | str     | Yes      | qudt_units                |                               |
| src_id                    | int64   | Yes      | src_id                    |                               |
| record_id                 | int64   | Yes      | record_id                 |                               |
| type                      | str     | Yes      | type                      |                               |
| relation                  | str     | Yes      | relation                  |                               |
| value                     | float64 | Yes      | value                     |                               |
| units                     | str     | Yes      | units                     |                               |
| text_value                | str     | Yes      | text_value                |                               |
| standard_text_value       | str     | Yes      | standard_text_value       |                               |
| upper_value               | float64 | Yes      | upper_value               |                               |
| standard_upper_value      | float64 | Yes      | standard_upper_value      |                               |
| toid                      | float64 | Yes      | toid                      | nullable-int coercion pattern |
| manual_curation_flag      | float64 | Yes      | manual_curation_flag      |                               |
| original_activity_id      | float64 | Yes      | original_activity_id      | nullable-int coercion pattern |
| data_validity_description | str     | Yes      | data_validity_description |                               |
| ligand_efficiency_bei     | float64 | Yes      | ligand_efficiency_bei     |                               |
| ligand_efficiency_le      | float64 | Yes      | ligand_efficiency_le      |                               |
| ligand_efficiency_lle     | float64 | Yes      | ligand_efficiency_lle     |                               |
| ligand_efficiency_sei     | float64 | Yes      | ligand_efficiency_sei     |                               |
| action_type               | str     | Yes      | action_type               |                               |
| action_type_description   | str     | Yes      | action_type_description   |                               |
| action_type_parent_type   | str     | Yes      | action_type_parent_type   |                               |
| activity_properties       | str     | Yes      | activity_properties       |                               |
| canonical_smiles          | str     | Yes      | canonical_smiles          |                               |
| molecule_pref_name        | str     | Yes      | molecule_pref_name        |                               |
| parent_molecule_id        | str     | Yes      | parent_molecule_id        |                               |
| target_pref_name          | str     | Yes      | target_pref_name          |                               |
| target_organism           | str     | Yes      | target_organism           |                               |
| target_taxonomy_id        | float64 | Yes      | target_taxonomy_id        | nullable-int coercion pattern |
| assay_type                | str     | Yes      | assay_type                |                               |
| assay_description         | str     | Yes      | assay_description         |                               |
| assay_variant_accession   | str     | Yes      | assay_variant_accession   |                               |
| assay_variant_mutation    | str     | Yes      | assay_variant_mutation    |                               |
| bao_format                | str     | Yes      | bao_format                |                               |
| bao_label                 | str     | Yes      | bao_label                 |                               |
| journal                   | str     | Yes      | journal                   |                               |
| publication_doi           | str     | Yes      | publication_doi           |                               |
| publication_pmid          | str     | Yes      | publication_pmid          |                               |
| publication_pmc_id        | str     | Yes      | publication_pmc_id        |                               |
| publication_year          | Int64   | Yes      | publication_year          |                               |

Анализ: 65 columns, nullable=54, non-null=11; partition=[].

#### 4. Gold Schema (Контракт)

- Контрактная версия: class-based contract `ChEMBLActivityGoldSchema` (version field not explicit in class).
- Режим загрузки: `append`
- API стабильность: высокая при соблюдении Pandera strict и alias metadata policy.

| Поле                      | Тип     | Nullable | Semantic role | Breaking risk |
| ------------------------- | ------- | -------- | ------------- | ------------- |
| entity_id                 | str     | No       | metadata      | High          |
| content_hash              | str     | No       | metadata      | High          |
| activity_id               | str     | No       | business      | High          |
| molecule_id               | str     | No       | business      | High          |
| target_id                 | str     | Yes      | business      | Medium        |
| assay_id                  | str     | Yes      | business      | Medium        |
| publication_id            | str     | Yes      | business      | Medium        |
| record_id                 | float64 | Yes      | business      | Medium        |
| src_id                    | float64 | Yes      | business      | Medium        |
| canonical_smiles          | str     | Yes      | business      | Medium        |
| molecule_pref_name        | str     | Yes      | business      | Medium        |
| parent_molecule_id        | str     | Yes      | business      | Medium        |
| target_pref_name          | str     | Yes      | business      | Medium        |
| target_organism           | str     | Yes      | business      | Medium        |
| target_taxonomy_id        | float64 | Yes      | business      | Medium        |
| assay_type                | str     | Yes      | business      | Medium        |
| assay_description         | str     | Yes      | business      | Medium        |
| assay_variant_accession   | str     | Yes      | business      | Medium        |
| assay_variant_mutation    | str     | Yes      | business      | Medium        |
| bao_endpoint              | str     | Yes      | business      | Medium        |
| bao_format                | str     | Yes      | business      | Medium        |
| bao_label                 | str     | Yes      | business      | Medium        |
| type                      | str     | Yes      | business      | Medium        |
| value                     | float64 | Yes      | business      | Medium        |
| units                     | str     | Yes      | business      | Medium        |
| relation                  | str     | Yes      | business      | Medium        |
| upper_value               | float64 | Yes      | business      | Medium        |
| text_value                | str     | Yes      | business      | Medium        |
| standard_type             | str     | Yes      | business      | Medium        |
| standard_value            | float64 | Yes      | business      | Medium        |
| standard_units            | str     | Yes      | business      | Medium        |
| standard_relation         | str     | Yes      | business      | Medium        |
| standard_upper_value      | float64 | Yes      | business      | Medium        |
| standard_text_value       | str     | Yes      | business      | Medium        |
| standard_flag             | float64 | Yes      | business      | Medium        |
| pchembl_value             | float64 | Yes      | business      | Medium        |
| ligand_efficiency_bei     | float64 | Yes      | business      | Medium        |
| ligand_efficiency_le      | float64 | Yes      | business      | Medium        |
| ligand_efficiency_lle     | float64 | Yes      | business      | Medium        |
| ligand_efficiency_sei     | float64 | Yes      | business      | Medium        |
| qudt_units                | str     | Yes      | business      | Medium        |
| uo_units                  | str     | Yes      | business      | Medium        |
| journal                   | str     | Yes      | business      | Medium        |
| publication_year          | float64 | Yes      | business      | Medium        |
| publication_doi           | str     | Yes      | business      | Medium        |
| publication_pmid          | str     | Yes      | business      | Medium        |
| publication_pmc_id        | str     | Yes      | business      | Medium        |
| activity_comment          | str     | Yes      | business      | Medium        |
| data_validity_comment     | str     | Yes      | business      | Medium        |
| data_validity_description | str     | Yes      | business      | Medium        |
| potential_duplicate       | float64 | Yes      | business      | Medium        |
| action_type               | str     | Yes      | business      | Medium        |
| action_type_description   | str     | Yes      | business      | Medium        |
| action_type_parent_type   | str     | Yes      | business      | Medium        |
| activity_properties       | str     | Yes      | business      | Medium        |
| toid                      | float64 | Yes      | business      | Medium        |
| \_run_id                  | str     | No       | metadata      | High          |
| \_run_type                | str     | No       | metadata      | High          |
| \_source_batch_id         | str     | Yes      | metadata      | Medium        |
| \_ingestion_ts            | str     | No       | metadata      | High          |
| \_index                   | int64   | No       | metadata      | High          |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping: No
- Поля в Silver, отсутствующие в Gold: 4
  - \_dq_error, \_dq_warn, manual_curation_flag, original_activity_id
- Поля в Gold, отсутствующие в Silver: 0
- SSOT risk: medium when publication/provider-specific aliases coexist.

**DQ rules summary**

- Silver required_fields: 0; ranges: 0; columns filters: 0
- Gold required_fields: 0; ranges: 0; columns filters: 0
- Content hash policy: sha256(provider + canonical_json(record_normalized)); excludes technical fields \_ingestion_ts, \_run_id, \_run_type, _dq_\*.

### chembl_assay

#### 1. Общая информация

- Provider: `chembl`
- Entity: `assay`
- Pipeline name: `chembl_assay`
- Primary keys: `['assay_id']`
- Loading strategy: API extract → Bronze append JSONL → Silver merge/upsert → Gold `scd2`
- Write mode: Silver=`merge`, Gold=`scd2`

#### 2. Bronze Layer

- Формат хранения: JSONL + zstd (append-only, flat_structure enabled by base config).
- Структура записи: raw provider payload; nested JSON partially flattened at transformer stage.
- Метаданные: batch-level metadata sidecar + pipeline run metadata added downstream (`_run_id`, `_run_type`, `_ingestion_ts`).
- Потенциальный schema drift: высокий для publication pipelines и ChEMBL nested objects; управляется soft validation в Silver.
- Ключевые риски Bronze: nested JSON, nullable-int coercion, provider-specific enum drift.

#### 3. Silver Schema

| Поле                       | Тип     | Nullable | Source field               | Notes                         |
| -------------------------- | ------- | -------- | -------------------------- | ----------------------------- |
| entity_id                  | str     | No       | entity_id                  |                               |
| content_hash               | str     | No       | content_hash               |                               |
| \_run_id                   | str     | No       | \_run_id                   |                               |
| \_run_type                 | str     | No       | \_run_type                 |                               |
| \_source_batch_id          | str     | Yes      | \_source_batch_id          |                               |
| \_ingestion_ts             | str     | No       | \_ingestion_ts             |                               |
| \_index                    | int64   | No       | \_index                    |                               |
| \_dq_warn                  | bool    | No       | \_dq_warn                  |                               |
| \_dq_error                 | bool    | No       | \_dq_error                 |                               |
| assay_id                   | str     | No       | assay_id                   |                               |
| description                | str     | Yes      | description                |                               |
| assay_type                 | str     | Yes      | assay_type                 |                               |
| assay_type_description     | str     | Yes      | assay_type_description     |                               |
| assay_test_type            | str     | Yes      | assay_test_type            |                               |
| assay_category             | str     | Yes      | assay_category             |                               |
| assay_group                | str     | Yes      | assay_group                |                               |
| assay_organism             | str     | Yes      | assay_organism             |                               |
| assay_taxonomy_id          | float64 | Yes      | assay_taxonomy_id          | nullable-int coercion pattern |
| assay_strain               | str     | Yes      | assay_strain               |                               |
| assay_tissue               | str     | Yes      | assay_tissue               |                               |
| assay_cell_type            | str     | Yes      | assay_cell_type            |                               |
| assay_subcellular_fraction | str     | Yes      | assay_subcellular_fraction |                               |
| target_id                  | str     | Yes      | target_id                  |                               |
| relationship_type          | str     | Yes      | relationship_type          |                               |
| relationship_description   | str     | Yes      | relationship_description   |                               |
| confidence_score           | int64   | Yes      | confidence_score           |                               |
| confidence_description     | str     | Yes      | confidence_description     |                               |
| src_id                     | int64   | Yes      | src_id                     |                               |
| src_assay_id               | str     | Yes      | src_assay_id               |                               |
| publication_id             | str     | Yes      | publication_id             |                               |
| assay_pref_name            | str     | Yes      | assay_pref_name            |                               |
| score                      | float64 | Yes      | score                      |                               |
| cell_id                    | str     | Yes      | cell_id                    |                               |
| tissue_id                  | str     | Yes      | tissue_id                  |                               |
| bao_format                 | str     | Yes      | bao_format                 |                               |
| bao_label                  | str     | Yes      | bao_label                  |                               |
| aidx                       | str     | Yes      | aidx                       |                               |
| variant_accession          | str     | Yes      | variant_accession          |                               |
| variant_isoform            | str     | Yes      | variant_isoform            |                               |
| variant_mutation           | str     | Yes      | variant_mutation           |                               |
| variant_organism           | str     | Yes      | variant_organism           |                               |
| variant_sequence           | str     | Yes      | variant_sequence           |                               |
| variant_taxonomy_id        | float64 | Yes      | variant_taxonomy_id        | nullable-int coercion pattern |
| variant_sequence_json      | str     | Yes      | variant_sequence_json      |                               |
| assay_classifications      | str     | Yes      | assay_classifications      |                               |
| assay_parameters           | str     | Yes      | assay_parameters           |                               |

Анализ: 46 columns, nullable=37, non-null=9; partition=['assay_type'].

#### 4. Gold Schema (Контракт)

- Контрактная версия: class-based contract `ChEMBLAssayGoldSchema` (version field not explicit in class).
- Режим загрузки: `scd2`
- SCD config: {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}
- API стабильность: высокая при соблюдении Pandera strict и alias metadata policy.

| Поле                       | Тип     | Nullable | Semantic role | Breaking risk |
| -------------------------- | ------- | -------- | ------------- | ------------- |
| entity_id                  | str     | No       | metadata      | High          |
| content_hash               | str     | No       | metadata      | High          |
| assay_id                   | str     | No       | business      | High          |
| target_id                  | str     | Yes      | business      | Medium        |
| publication_id             | str     | Yes      | business      | Medium        |
| cell_id                    | str     | Yes      | business      | Medium        |
| tissue_id                  | str     | Yes      | business      | Medium        |
| src_id                     | float64 | Yes      | business      | Medium        |
| src_assay_id               | str     | Yes      | business      | Medium        |
| aidx                       | str     | Yes      | business      | Medium        |
| assay_type                 | str     | Yes      | business      | Medium        |
| assay_type_description     | str     | Yes      | business      | Medium        |
| assay_category             | str     | Yes      | business      | Medium        |
| assay_test_type            | str     | Yes      | business      | Medium        |
| assay_group                | str     | Yes      | business      | Medium        |
| assay_organism             | str     | Yes      | business      | Medium        |
| assay_taxonomy_id          | float64 | Yes      | business      | Medium        |
| assay_cell_type            | str     | Yes      | business      | Medium        |
| assay_tissue               | str     | Yes      | business      | Medium        |
| assay_strain               | str     | Yes      | business      | Medium        |
| assay_subcellular_fraction | str     | Yes      | business      | Medium        |
| bao_format                 | str     | Yes      | business      | Medium        |
| bao_label                  | str     | Yes      | business      | Medium        |
| description                | str     | Yes      | business      | Medium        |
| confidence_score           | float64 | Yes      | business      | Medium        |
| confidence_description     | str     | Yes      | business      | Medium        |
| relationship_type          | str     | Yes      | business      | Medium        |
| relationship_description   | str     | Yes      | business      | Medium        |
| assay_pref_name            | str     | Yes      | business      | Medium        |
| score                      | float64 | Yes      | business      | Medium        |
| variant_accession          | str     | Yes      | business      | Medium        |
| variant_isoform            | str     | Yes      | business      | Medium        |
| variant_mutation           | str     | Yes      | business      | Medium        |
| variant_organism           | str     | Yes      | business      | Medium        |
| variant_sequence           | str     | Yes      | business      | Medium        |
| variant_taxonomy_id        | float64 | Yes      | business      | Medium        |
| variant_sequence_json      | str     | Yes      | business      | Medium        |
| assay_classifications      | str     | Yes      | business      | Medium        |
| assay_parameters           | str     | Yes      | business      | Medium        |
| \_run_id                   | str     | No       | metadata      | High          |
| \_run_type                 | str     | No       | metadata      | High          |
| \_source_batch_id          | str     | Yes      | metadata      | Medium        |
| \_ingestion_ts             | str     | No       | metadata      | High          |
| \_index                    | int64   | No       | metadata      | High          |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping: No
- Поля в Silver, отсутствующие в Gold: 2
  - \_dq_error, \_dq_warn
- Поля в Gold, отсутствующие в Silver: 0
- SSOT risk: medium when publication/provider-specific aliases coexist.

**DQ rules summary**

- Silver required_fields: 0; ranges: 0; columns filters: 0
- Gold required_fields: 0; ranges: 0; columns filters: 0
- Content hash policy: sha256(provider + canonical_json(record_normalized)); excludes technical fields \_ingestion_ts, \_run_id, \_run_type, _dq_\*.

### chembl_assay_parameters

#### 1. Общая информация

- Provider: `chembl`
- Entity: `assay_parameters`
- Pipeline name: `chembl_assay_parameters`
- Primary keys: `['assay_param_id']`
- Loading strategy: API extract → Bronze append JSONL → Silver merge/upsert → Gold `scd2`
- Write mode: Silver=`merge`, Gold=`scd2`

#### 2. Bronze Layer

- Формат хранения: JSONL + zstd (append-only, flat_structure enabled by base config).
- Структура записи: raw provider payload; nested JSON partially flattened at transformer stage.
- Метаданные: batch-level metadata sidecar + pipeline run metadata added downstream (`_run_id`, `_run_type`, `_ingestion_ts`).
- Потенциальный schema drift: высокий для publication pipelines и ChEMBL nested objects; управляется soft validation в Silver.
- Ключевые риски Bronze: nested JSON, nullable-int coercion, provider-specific enum drift.

#### 3. Silver Schema

| Поле                | Тип     | Nullable | Source field        | Notes |
| ------------------- | ------- | -------- | ------------------- | ----- |
| entity_id           | str     | No       | entity_id           |       |
| content_hash        | str     | No       | content_hash        |       |
| \_run_id            | str     | No       | \_run_id            |       |
| \_run_type          | str     | No       | \_run_type          |       |
| \_source_batch_id   | str     | Yes      | \_source_batch_id   |       |
| \_ingestion_ts      | str     | No       | \_ingestion_ts      |       |
| \_index             | int64   | No       | \_index             |       |
| \_dq_warn           | bool    | No       | \_dq_warn           |       |
| \_dq_error          | bool    | No       | \_dq_error          |       |
| assay_param_id      | int64   | No       | assay_param_id      |       |
| assay_id            | str     | No       | assay_id            |       |
| type                | str     | Yes      | type                |       |
| relation            | str     | Yes      | relation            |       |
| value               | float64 | Yes      | value               |       |
| units               | str     | Yes      | units               |       |
| text_value          | str     | Yes      | text_value          |       |
| comments            | str     | Yes      | comments            |       |
| standard_type       | str     | Yes      | standard_type       |       |
| standard_relation   | str     | Yes      | standard_relation   |       |
| standard_value      | float64 | Yes      | standard_value      |       |
| standard_units      | str     | Yes      | standard_units      |       |
| standard_text_value | str     | Yes      | standard_text_value |       |

Анализ: 22 columns, nullable=12, non-null=10; partition=['type'].

#### 4. Gold Schema (Контракт)

- Контрактная версия: class-based contract `ChEMBLAssayParametersGoldSchema` (version field not explicit in class).
- Режим загрузки: `scd2`
- SCD config: {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}
- API стабильность: высокая при соблюдении Pandera strict и alias metadata policy.

| Поле                | Тип     | Nullable | Semantic role | Breaking risk |
| ------------------- | ------- | -------- | ------------- | ------------- |
| entity_id           | str     | No       | metadata      | High          |
| content_hash        | str     | No       | metadata      | High          |
| assay_param_id      | float64 | No       | business      | High          |
| assay_id            | str     | No       | business      | High          |
| type                | str     | No       | business      | High          |
| relation            | str     | Yes      | business      | Medium        |
| value               | float64 | Yes      | business      | Medium        |
| units               | str     | Yes      | business      | Medium        |
| text_value          | str     | Yes      | business      | Medium        |
| comments            | str     | Yes      | business      | Medium        |
| standard_type       | str     | Yes      | business      | Medium        |
| standard_relation   | str     | Yes      | business      | Medium        |
| standard_value      | float64 | Yes      | business      | Medium        |
| standard_units      | str     | Yes      | business      | Medium        |
| standard_text_value | str     | Yes      | business      | Medium        |
| \_run_id            | str     | No       | metadata      | High          |
| \_run_type          | str     | No       | metadata      | High          |
| \_source_batch_id   | str     | Yes      | metadata      | Medium        |
| \_ingestion_ts      | str     | No       | metadata      | High          |
| \_index             | int64   | No       | metadata      | High          |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping: No
- Поля в Silver, отсутствующие в Gold: 2
  - \_dq_error, \_dq_warn
- Поля в Gold, отсутствующие в Silver: 0
- SSOT risk: medium when publication/provider-specific aliases coexist.

**DQ rules summary**

- Silver required_fields: 0; ranges: 0; columns filters: 0
- Gold required_fields: 0; ranges: 0; columns filters: 0
- Content hash policy: sha256(provider + canonical_json(record_normalized)); excludes technical fields \_ingestion_ts, \_run_id, \_run_type, _dq_\*.

### chembl_cell_line

#### 1. Общая информация

- Provider: `chembl`
- Entity: `cell_line`
- Pipeline name: `chembl_cell_line`
- Primary keys: `['cell_id']`
- Loading strategy: API extract → Bronze append JSONL → Silver merge/upsert → Gold `scd2`
- Write mode: Silver=`merge`, Gold=`scd2`

#### 2. Bronze Layer

- Формат хранения: JSONL + zstd (append-only, flat_structure enabled by base config).
- Структура записи: raw provider payload; nested JSON partially flattened at transformer stage.
- Метаданные: batch-level metadata sidecar + pipeline run metadata added downstream (`_run_id`, `_run_type`, `_ingestion_ts`).
- Потенциальный schema drift: высокий для publication pipelines и ChEMBL nested objects; управляется soft validation в Silver.
- Ключевые риски Bronze: nested JSON, nullable-int coercion, provider-specific enum drift.

#### 3. Silver Schema

| Поле                    | Тип     | Nullable | Source field            | Notes                         |
| ----------------------- | ------- | -------- | ----------------------- | ----------------------------- |
| entity_id               | str     | No       | entity_id               |                               |
| content_hash            | str     | No       | content_hash            |                               |
| \_run_id                | str     | No       | \_run_id                |                               |
| \_run_type              | str     | No       | \_run_type              |                               |
| \_source_batch_id       | str     | Yes      | \_source_batch_id       |                               |
| \_ingestion_ts          | str     | No       | \_ingestion_ts          |                               |
| \_index                 | int64   | No       | \_index                 |                               |
| \_dq_warn               | bool    | No       | \_dq_warn               |                               |
| \_dq_error              | bool    | No       | \_dq_error              |                               |
| cell_id                 | str     | No       | cell_id                 |                               |
| cell_name               | str     | No       | cell_name               |                               |
| cell_description        | str     | Yes      | cell_description        |                               |
| cell_source_tissue      | str     | Yes      | cell_source_tissue      |                               |
| cell_source_organism    | str     | Yes      | cell_source_organism    |                               |
| cell_source_taxonomy_id | float64 | Yes      | cell_source_taxonomy_id | nullable-int coercion pattern |
| cell_type               | str     | Yes      | cell_type               |                               |
| cellosaurus_id          | str     | Yes      | cellosaurus_id          |                               |
| clo_id                  | str     | Yes      | clo_id                  |                               |
| cl_lincs_id             | str     | Yes      | cl_lincs_id             |                               |
| efo_id                  | str     | Yes      | efo_id                  |                               |

Анализ: 20 columns, nullable=10, non-null=10; partition=[].

#### 4. Gold Schema (Контракт)

- Контрактная версия: class-based contract `ChEMBLCellLineGoldSchema` (version field not explicit in class).
- Режим загрузки: `scd2`
- SCD config: {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}
- API стабильность: высокая при соблюдении Pandera strict и alias metadata policy.

| Поле                    | Тип     | Nullable | Semantic role | Breaking risk |
| ----------------------- | ------- | -------- | ------------- | ------------- |
| entity_id               | str     | No       | metadata      | High          |
| content_hash            | str     | No       | metadata      | High          |
| cell_id                 | str     | No       | business      | High          |
| cell_name               | str     | No       | business      | High          |
| cell_description        | str     | Yes      | business      | Medium        |
| cell_source_tissue      | str     | Yes      | business      | Medium        |
| cell_source_organism    | str     | Yes      | business      | Medium        |
| cell_source_taxonomy_id | float64 | Yes      | business      | Medium        |
| cellosaurus_id          | str     | Yes      | business      | Medium        |
| cl_lincs_id             | str     | Yes      | business      | Medium        |
| efo_id                  | str     | Yes      | business      | Medium        |
| \_run_id                | str     | No       | metadata      | High          |
| \_run_type              | str     | No       | metadata      | High          |
| \_source_batch_id       | str     | Yes      | metadata      | Medium        |
| \_ingestion_ts          | str     | No       | metadata      | High          |
| \_index                 | int64   | No       | metadata      | High          |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping: No
- Поля в Silver, отсутствующие в Gold: 4
  - \_dq_error, \_dq_warn, cell_type, clo_id
- Поля в Gold, отсутствующие в Silver: 0
- SSOT risk: medium when publication/provider-specific aliases coexist.

**DQ rules summary**

- Silver required_fields: 0; ranges: 0; columns filters: 0
- Gold required_fields: 0; ranges: 0; columns filters: 0
- Content hash policy: sha256(provider + canonical_json(record_normalized)); excludes technical fields \_ingestion_ts, \_run_id, \_run_type, _dq_\*.

### chembl_compound_record

#### 1. Общая информация

- Provider: `chembl`
- Entity: `compound_record`
- Pipeline name: `chembl_compound_record`
- Primary keys: `['record_id']`
- Loading strategy: API extract → Bronze append JSONL → Silver merge/upsert → Gold `scd2`
- Write mode: Silver=`merge`, Gold=`scd2`

#### 2. Bronze Layer

- Формат хранения: JSONL + zstd (append-only, flat_structure enabled by base config).
- Структура записи: raw provider payload; nested JSON partially flattened at transformer stage.
- Метаданные: batch-level metadata sidecar + pipeline run metadata added downstream (`_run_id`, `_run_type`, `_ingestion_ts`).
- Потенциальный schema drift: высокий для publication pipelines и ChEMBL nested objects; управляется soft validation в Silver.
- Ключевые риски Bronze: nested JSON, nullable-int coercion, provider-specific enum drift.

#### 3. Silver Schema

| Поле              | Тип   | Nullable | Source field      | Notes |
| ----------------- | ----- | -------- | ----------------- | ----- |
| entity_id         | str   | No       | entity_id         |       |
| content_hash      | str   | No       | content_hash      |       |
| \_run_id          | str   | No       | \_run_id          |       |
| \_run_type        | str   | No       | \_run_type        |       |
| \_source_batch_id | str   | Yes      | \_source_batch_id |       |
| \_ingestion_ts    | str   | No       | \_ingestion_ts    |       |
| \_index           | int64 | No       | \_index           |       |
| \_dq_warn         | bool  | No       | \_dq_warn         |       |
| \_dq_error        | bool  | No       | \_dq_error        |       |
| record_id         | int64 | No       | record_id         |       |
| molecule_id       | str   | No       | molecule_id       |       |
| publication_id    | str   | No       | publication_id    |       |
| src_id            | int64 | No       | src_id            |       |
| compound_key      | str   | Yes      | compound_key      |       |
| compound_name     | str   | Yes      | compound_name     |       |
| src_compound_id   | str   | Yes      | src_compound_id   |       |

Анализ: 16 columns, nullable=4, non-null=12; partition=[].

#### 4. Gold Schema (Контракт)

- Контрактная версия: class-based contract `ChEMBLCompoundRecordGoldSchema` (version field not explicit in class).
- Режим загрузки: `scd2`
- SCD config: {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}
- API стабильность: высокая при соблюдении Pandera strict и alias metadata policy.

| Поле              | Тип     | Nullable | Semantic role | Breaking risk |
| ----------------- | ------- | -------- | ------------- | ------------- |
| entity_id         | str     | No       | metadata      | High          |
| content_hash      | str     | No       | metadata      | High          |
| record_id         | float64 | No       | business      | High          |
| molecule_id       | str     | No       | business      | High          |
| publication_id    | str     | No       | business      | High          |
| compound_key      | str     | Yes      | business      | Medium        |
| compound_name     | str     | Yes      | business      | Medium        |
| src_id            | float64 | No       | business      | High          |
| src_compound_id   | str     | Yes      | business      | Medium        |
| \_run_id          | str     | No       | metadata      | High          |
| \_run_type        | str     | No       | metadata      | High          |
| \_source_batch_id | str     | Yes      | metadata      | Medium        |
| \_ingestion_ts    | str     | No       | metadata      | High          |
| \_index           | int64   | No       | metadata      | High          |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping: No
- Поля в Silver, отсутствующие в Gold: 2
  - \_dq_error, \_dq_warn
- Поля в Gold, отсутствующие в Silver: 0
- SSOT risk: medium when publication/provider-specific aliases coexist.

**DQ rules summary**

- Silver required_fields: 0; ranges: 0; columns filters: 0
- Gold required_fields: 0; ranges: 0; columns filters: 0
- Content hash policy: sha256(provider + canonical_json(record_normalized)); excludes technical fields \_ingestion_ts, \_run_id, \_run_type, _dq_\*.

### chembl_molecule

#### 1. Общая информация

- Provider: `chembl`
- Entity: `molecule`
- Pipeline name: `chembl_molecule`
- Primary keys: `['molecule_id']`
- Loading strategy: API extract → Bronze append JSONL → Silver merge/upsert → Gold `scd2`
- Write mode: Silver=`merge`, Gold=`scd2`

#### 2. Bronze Layer

- Формат хранения: JSONL + zstd (append-only, flat_structure enabled by base config).
- Структура записи: raw provider payload; nested JSON partially flattened at transformer stage.
- Метаданные: batch-level metadata sidecar + pipeline run metadata added downstream (`_run_id`, `_run_type`, `_ingestion_ts`).
- Потенциальный schema drift: высокий для publication pipelines и ChEMBL nested objects; управляется soft validation в Silver.
- Ключевые риски Bronze: nested JSON, nullable-int coercion, provider-specific enum drift.

#### 3. Silver Schema

| Поле                       | Тип     | Nullable | Source field               | Notes |
| -------------------------- | ------- | -------- | -------------------------- | ----- |
| entity_id                  | str     | No       | entity_id                  |       |
| content_hash               | str     | No       | content_hash               |       |
| \_run_id                   | str     | No       | \_run_id                   |       |
| \_run_type                 | str     | No       | \_run_type                 |       |
| \_source_batch_id          | str     | Yes      | \_source_batch_id          |       |
| \_ingestion_ts             | str     | No       | \_ingestion_ts             |       |
| \_index                    | int64   | No       | \_index                    |       |
| \_dq_warn                  | bool    | No       | \_dq_warn                  |       |
| \_dq_error                 | bool    | No       | \_dq_error                 |       |
| molecule_id                | str     | No       | molecule_id                |       |
| pref_name                  | str     | Yes      | pref_name                  |       |
| max_phase                  | float64 | Yes      | max_phase                  |       |
| structure_type             | str     | Yes      | structure_type             |       |
| molecule_type              | str     | Yes      | molecule_type              |       |
| first_approval             | float64 | Yes      | first_approval             |       |
| therapeutic_flag           | bool    | Yes      | therapeutic_flag           |       |
| oral                       | bool    | Yes      | oral                       |       |
| parenteral                 | bool    | Yes      | parenteral                 |       |
| topical                    | bool    | Yes      | topical                    |       |
| black_box_warning          | int64   | Yes      | black_box_warning          |       |
| natural_product            | int64   | Yes      | natural_product            |       |
| first_in_class             | int64   | Yes      | first_in_class             |       |
| prodrug                    | int64   | Yes      | prodrug                    |       |
| inorganic_flag             | int64   | Yes      | inorganic_flag             |       |
| polymer_flag               | int64   | Yes      | polymer_flag               |       |
| withdrawn_flag             | bool    | Yes      | withdrawn_flag             |       |
| chirality                  | int64   | Yes      | chirality                  |       |
| dosed_ingredient           | int64   | Yes      | dosed_ingredient           |       |
| availability_type          | float64 | Yes      | availability_type          |       |
| usan_year                  | float64 | Yes      | usan_year                  |       |
| usan_stem                  | str     | Yes      | usan_stem                  |       |
| usan_substem               | str     | Yes      | usan_substem               |       |
| usan_stem_definition       | str     | Yes      | usan_stem_definition       |       |
| helm_notation              | str     | Yes      | helm_notation              |       |
| molecule_species           | str     | Yes      | molecule_species           |       |
| hierarchy_parent_chembl_id | str     | Yes      | hierarchy_parent_chembl_id |       |
| hierarchy_active_chembl_id | str     | Yes      | hierarchy_active_chembl_id |       |
| hierarchy_child_chembl_id  | str     | Yes      | hierarchy_child_chembl_id  |       |
| logp                       | float64 | Yes      | logp                       |       |
| logp_method                | str     | Yes      | logp_method                |       |
| mw_freebase                | float64 | Yes      | mw_freebase                |       |
| molecular_weight           | float64 | Yes      | molecular_weight           |       |
| hba_count                  | Int64   | Yes      | hba_count                  |       |
| hbd_count                  | Int64   | Yes      | hbd_count                  |       |
| polar_surface_area         | float64 | Yes      | polar_surface_area         |       |
| rotatable_bond_count       | Int64   | Yes      | rotatable_bond_count       |       |
| ro5_violation_count        | Int64   | Yes      | ro5_violation_count        |       |
| heavy_atom_count           | Int64   | Yes      | heavy_atom_count           |       |
| aromatic_ring_count        | Int64   | Yes      | aromatic_ring_count        |       |
| qed_score                  | float64 | Yes      | qed_score                  |       |
| molecular_formula          | str     | Yes      | molecular_formula          |       |
| ro3_pass                   | str     | Yes      | ro3_pass                   |       |
| canonical_smiles           | str     | Yes      | canonical_smiles           |       |
| standard_inchi             | str     | Yes      | standard_inchi             |       |
| inchi_key                  | str     | Yes      | inchi_key                  |       |
| molecule_hierarchy         | str     | Yes      | molecule_hierarchy         |       |
| molecule_properties        | str     | Yes      | molecule_properties        |       |
| molecule_structures        | str     | Yes      | molecule_structures        |       |
| molecule_synonyms          | str     | Yes      | molecule_synonyms          |       |
| cross_references           | str     | Yes      | cross_references           |       |
| atc_classifications        | str     | Yes      | atc_classifications        |       |

Анализ: 61 columns, nullable=52, non-null=9; partition=['molecule_type'].

#### 4. Gold Schema (Контракт)

- Контрактная версия: class-based contract `ChEMBLMoleculeGoldSchema` (version field not explicit in class).
- Режим загрузки: `scd2`
- SCD config: {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}
- API стабильность: высокая при соблюдении Pandera strict и alias metadata policy.

| Поле                       | Тип     | Nullable | Semantic role | Breaking risk |
| -------------------------- | ------- | -------- | ------------- | ------------- |
| entity_id                  | str     | No       | metadata      | High          |
| content_hash               | str     | No       | metadata      | High          |
| molecule_id                | str     | No       | business      | High          |
| pref_name                  | str     | Yes      | business      | Medium        |
| molecule_type              | str     | Yes      | business      | Medium        |
| structure_type             | str     | Yes      | business      | Medium        |
| max_phase                  | float64 | Yes      | business      | Medium        |
| first_approval             | float64 | Yes      | business      | Medium        |
| chirality                  | float64 | Yes      | business      | Medium        |
| dosed_ingredient           | float64 | Yes      | business      | Medium        |
| availability_type          | float64 | Yes      | business      | Medium        |
| usan_stem                  | str     | Yes      | business      | Medium        |
| usan_stem_definition       | str     | Yes      | business      | Medium        |
| usan_substem               | str     | Yes      | business      | Medium        |
| usan_year                  | float64 | Yes      | business      | Medium        |
| helm_notation              | str     | Yes      | business      | Medium        |
| molecule_species           | str     | Yes      | business      | Medium        |
| oral                       | bool    | Yes      | business      | Medium        |
| parenteral                 | bool    | Yes      | business      | Medium        |
| topical                    | bool    | Yes      | business      | Medium        |
| black_box_warning          | float64 | Yes      | business      | Medium        |
| natural_product            | float64 | Yes      | business      | Medium        |
| first_in_class             | float64 | Yes      | business      | Medium        |
| prodrug                    | float64 | Yes      | business      | Medium        |
| therapeutic_flag           | bool    | Yes      | business      | Medium        |
| withdrawn_flag             | bool    | Yes      | business      | Medium        |
| inorganic_flag             | float64 | Yes      | business      | Medium        |
| polymer_flag               | float64 | Yes      | business      | Medium        |
| molecule_hierarchy         | str     | Yes      | business      | Medium        |
| molecule_properties        | str     | Yes      | business      | Medium        |
| molecule_structures        | str     | Yes      | business      | Medium        |
| molecule_synonyms          | str     | Yes      | business      | Medium        |
| cross_references           | str     | Yes      | business      | Medium        |
| atc_classifications        | str     | Yes      | business      | Medium        |
| hierarchy_parent_chembl_id | str     | Yes      | business      | Medium        |
| hierarchy_active_chembl_id | str     | Yes      | business      | Medium        |
| hierarchy_child_chembl_id  | str     | Yes      | business      | Medium        |
| logp                       | float64 | Yes      | business      | Medium        |
| logp_method                | str     | Yes      | business      | Medium        |
| molecular_weight           | float64 | Yes      | business      | Medium        |
| mw_freebase                | float64 | Yes      | business      | Medium        |
| polar_surface_area         | float64 | Yes      | business      | Medium        |
| rotatable_bond_count       | float64 | Yes      | business      | Medium        |
| ro5_violation_count        | float64 | Yes      | business      | Medium        |
| heavy_atom_count           | float64 | Yes      | business      | Medium        |
| aromatic_ring_count        | float64 | Yes      | business      | Medium        |
| hba_count                  | float64 | Yes      | business      | Medium        |
| hbd_count                  | float64 | Yes      | business      | Medium        |
| qed_score                  | float64 | Yes      | business      | Medium        |
| molecular_formula          | str     | Yes      | business      | Medium        |
| ro3_pass                   | str     | Yes      | business      | Medium        |
| canonical_smiles           | str     | Yes      | business      | Medium        |
| standard_inchi             | str     | Yes      | business      | Medium        |
| inchi_key                  | str     | Yes      | business      | Medium        |
| \_run_id                   | str     | No       | metadata      | High          |
| \_run_type                 | str     | No       | metadata      | High          |
| \_source_batch_id          | str     | Yes      | metadata      | Medium        |
| \_ingestion_ts             | str     | No       | metadata      | High          |
| \_index                    | int64   | No       | metadata      | High          |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping: No
- Поля в Silver, отсутствующие в Gold: 2
  - \_dq_error, \_dq_warn
- Поля в Gold, отсутствующие в Silver: 0
- SSOT risk: medium when publication/provider-specific aliases coexist.

**DQ rules summary**

- Silver required_fields: 0; ranges: 0; columns filters: 0
- Gold required_fields: 0; ranges: 0; columns filters: 0
- Content hash policy: sha256(provider + canonical_json(record_normalized)); excludes technical fields \_ingestion_ts, \_run_id, \_run_type, _dq_\*.

### chembl_protein_class

#### 1. Общая информация

- Provider: `chembl`
- Entity: `protein_class`
- Pipeline name: `chembl_protein_class`
- Primary keys: `['protein_class_id']`
- Loading strategy: API extract → Bronze append JSONL → Silver merge/upsert → Gold `scd2`
- Write mode: Silver=`merge`, Gold=`scd2`

#### 2. Bronze Layer

- Формат хранения: JSONL + zstd (append-only, flat_structure enabled by base config).
- Структура записи: raw provider payload; nested JSON partially flattened at transformer stage.
- Метаданные: batch-level metadata sidecar + pipeline run metadata added downstream (`_run_id`, `_run_type`, `_ingestion_ts`).
- Потенциальный schema drift: высокий для publication pipelines и ChEMBL nested objects; управляется soft validation в Silver.
- Ключевые риски Bronze: nested JSON, nullable-int coercion, provider-specific enum drift.

#### 3. Silver Schema

| Поле               | Тип     | Nullable | Source field       | Notes |
| ------------------ | ------- | -------- | ------------------ | ----- |
| entity_id          | str     | No       | entity_id          |       |
| content_hash       | str     | No       | content_hash       |       |
| \_run_id           | str     | No       | \_run_id           |       |
| \_run_type         | str     | No       | \_run_type         |       |
| \_source_batch_id  | str     | Yes      | \_source_batch_id  |       |
| \_ingestion_ts     | str     | No       | \_ingestion_ts     |       |
| \_index            | int64   | No       | \_index            |       |
| \_dq_warn          | bool    | No       | \_dq_warn          |       |
| \_dq_error         | bool    | No       | \_dq_error         |       |
| protein_class_id   | int64   | No       | protein_class_id   |       |
| parent_id          | Int64   | Yes      | parent_id          |       |
| replaced_by        | Int64   | Yes      | replaced_by        |       |
| pref_name          | str     | Yes      | pref_name          |       |
| short_name         | str     | Yes      | short_name         |       |
| protein_class_desc | str     | Yes      | protein_class_desc |       |
| definition         | str     | Yes      | definition         |       |
| class_level        | Int64   | Yes      | class_level        |       |
| sort_order         | Int64   | Yes      | sort_order         |       |
| downgraded         | float64 | Yes      | downgraded         |       |

Анализ: 19 columns, nullable=10, non-null=9; partition=['class_level'].

#### 4. Gold Schema (Контракт)

- Контрактная версия: class-based contract `ChEMBLProteinClassGoldSchema` (version field not explicit in class).
- Режим загрузки: `scd2`
- SCD config: {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}
- API стабильность: высокая при соблюдении Pandera strict и alias metadata policy.

| Поле               | Тип     | Nullable | Semantic role | Breaking risk |
| ------------------ | ------- | -------- | ------------- | ------------- |
| entity_id          | str     | No       | metadata      | High          |
| content_hash       | str     | No       | metadata      | High          |
| protein_class_id   | float64 | No       | business      | High          |
| parent_id          | float64 | Yes      | business      | Medium        |
| class_level        | float64 | Yes      | business      | Medium        |
| pref_name          | str     | Yes      | business      | Medium        |
| short_name         | str     | Yes      | business      | Medium        |
| protein_class_desc | str     | Yes      | business      | Medium        |
| definition         | str     | Yes      | business      | Medium        |
| sort_order         | float64 | Yes      | business      | Medium        |
| replaced_by        | float64 | Yes      | business      | Medium        |
| downgraded         | float64 | Yes      | business      | Medium        |
| \_run_id           | str     | No       | metadata      | High          |
| \_run_type         | str     | No       | metadata      | High          |
| \_source_batch_id  | str     | Yes      | metadata      | Medium        |
| \_ingestion_ts     | str     | No       | metadata      | High          |
| \_index            | int64   | No       | metadata      | High          |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping: No
- Поля в Silver, отсутствующие в Gold: 2
  - \_dq_error, \_dq_warn
- Поля в Gold, отсутствующие в Silver: 0
- SSOT risk: medium when publication/provider-specific aliases coexist.

**DQ rules summary**

- Silver required_fields: 0; ranges: 0; columns filters: 0
- Gold required_fields: 0; ranges: 0; columns filters: 0
- Content hash policy: sha256(provider + canonical_json(record_normalized)); excludes technical fields \_ingestion_ts, \_run_id, \_run_type, _dq_\*.

### chembl_publication

#### 1. Общая информация

- Provider: `chembl`
- Entity: `publication`
- Pipeline name: `chembl_publication`
- Primary keys: `['publication_id']`
- Loading strategy: API extract → Bronze append JSONL → Silver merge/upsert → Gold `scd2`
- Write mode: Silver=`merge`, Gold=`scd2`

#### 2. Bronze Layer

- Формат хранения: JSONL + zstd (append-only, flat_structure enabled by base config).
- Структура записи: raw provider payload; nested JSON partially flattened at transformer stage.
- Метаданные: batch-level metadata sidecar + pipeline run metadata added downstream (`_run_id`, `_run_type`, `_ingestion_ts`).
- Потенциальный schema drift: высокий для publication pipelines и ChEMBL nested objects; управляется soft validation в Silver.
- Ключевые риски Bronze: nested JSON, nullable-int coercion, provider-specific enum drift.

#### 3. Silver Schema

| Поле                     | Тип   | Nullable | Source field             | Notes |
| ------------------------ | ----- | -------- | ------------------------ | ----- |
| entity_id                | str   | No       | entity_id                |       |
| content_hash             | str   | No       | content_hash             |       |
| \_run_id                 | str   | No       | \_run_id                 |       |
| \_run_type               | str   | No       | \_run_type               |       |
| \_source_batch_id        | str   | Yes      | \_source_batch_id        |       |
| \_ingestion_ts           | str   | No       | \_ingestion_ts           |       |
| \_index                  | int64 | No       | \_index                  |       |
| \_dq_warn                | bool  | No       | \_dq_warn                |       |
| \_dq_error               | bool  | No       | \_dq_error               |       |
| pmid                     | str   | Yes      | pmid                     |       |
| doi                      | str   | Yes      | doi                      |       |
| pmc_id                   | str   | Yes      | pmc_id                   |       |
| title                    | str   | Yes      | title                    |       |
| abstract                 | str   | Yes      | abstract                 |       |
| authors                  | str   | Yes      | authors                  |       |
| affiliation_list         | str   | Yes      | affiliation_list         |       |
| author_orcids            | str   | Yes      | author_orcids            |       |
| author_keys              | str   | Yes      | author_keys              |       |
| journal                  | str   | Yes      | journal                  |       |
| publication_year         | Int64 | Yes      | publication_year         |       |
| publication_date         | str   | Yes      | publication_date         |       |
| publication_type         | str   | Yes      | publication_type         |       |
| publication_type_unified | str   | Yes      | publication_type_unified |       |
| publication_subclass     | str   | Yes      | publication_subclass     |       |
| publication_class        | str   | Yes      | publication_class        |       |
| language                 | str   | Yes      | language                 |       |
| page_first               | str   | Yes      | page_first               |       |
| page_last                | str   | Yes      | page_last                |       |
| citations_received       | Int64 | Yes      | citations_received       |       |
| citations_made           | Int64 | Yes      | citations_made           |       |
| is_oa                    | bool  | Yes      | is_oa                    |       |
| \_lookup_method          | str   | No       | \_lookup_method          |       |
| \_original_id            | str   | Yes      | \_original_id            |       |
| publication_id           | str   | No       | publication_id           |       |
| src_id                   | Int64 | Yes      | src_id                   |       |
| chembl_release           | str   | Yes      | chembl_release           |       |
| creation_date            | str   | Yes      | creation_date            |       |
| volume                   | str   | Yes      | volume                   |       |
| issue                    | str   | Yes      | issue                    |       |

Анализ: 39 columns, nullable=29, non-null=10; partition=[].

#### 4. Gold Schema (Контракт)

- Контрактная версия: class-based contract `ChEMBLDocumentGoldSchema` (version field not explicit in class).
- Режим загрузки: `scd2`
- SCD config: {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}
- API стабильность: высокая при соблюдении Pandera strict и alias metadata policy.

| Поле               | Тип     | Nullable | Semantic role | Breaking risk |
| ------------------ | ------- | -------- | ------------- | ------------- |
| entity_id          | str     | No       | metadata      | High          |
| content_hash       | str     | No       | metadata      | High          |
| publication_id     | str     | No       | business      | High          |
| pmid               | str     | Yes      | business      | Medium        |
| doi                | str     | Yes      | business      | Medium        |
| publication_doi    | str     | Yes      | business      | Medium        |
| publication_pmid   | str     | Yes      | business      | Medium        |
| publication_pmc_id | str     | Yes      | business      | Medium        |
| title              | str     | Yes      | business      | Medium        |
| authors            | str     | Yes      | business      | Medium        |
| abstract           | str     | Yes      | business      | Medium        |
| publication_type   | str     | Yes      | business      | Medium        |
| journal            | str     | Yes      | business      | Medium        |
| publication_year   | float64 | Yes      | business      | Medium        |
| volume             | str     | Yes      | business      | Medium        |
| issue              | str     | Yes      | business      | Medium        |
| page_first         | str     | Yes      | business      | Medium        |
| page_last          | str     | Yes      | business      | Medium        |
| citations_received | float64 | Yes      | business      | Medium        |
| citations_made     | float64 | Yes      | business      | Medium        |
| src_id             | float64 | Yes      | business      | Medium        |
| chembl_release     | str     | Yes      | business      | Medium        |
| creation_date      | str     | Yes      | business      | Medium        |
| \_source           | str     | Yes      | metadata      | Medium        |
| \_lookup_method    | str     | Yes      | metadata      | Medium        |
| \_original_id      | str     | Yes      | metadata      | Medium        |
| \_dq_warn          | bool    | No       | metadata      | High          |
| \_dq_error         | bool    | No       | metadata      | High          |
| \_run_id           | str     | No       | metadata      | High          |
| \_run_type         | str     | No       | metadata      | High          |
| \_source_batch_id  | str     | Yes      | metadata      | Medium        |
| \_ingestion_ts     | str     | No       | metadata      | High          |
| \_index            | int64   | No       | metadata      | High          |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping: No
- Поля в Silver, отсутствующие в Gold: 10
  - affiliation_list, author_keys, author_orcids, is_oa, language, pmc_id, publication_class, publication_date, publication_subclass, publication_type_unified
- Поля в Gold, отсутствующие в Silver: 4
  - \_source, publication_doi, publication_pmc_id, publication_pmid
- SSOT risk: medium when publication/provider-specific aliases coexist.

**DQ rules summary**

- Silver required_fields: 0; ranges: 0; columns filters: 0
- Gold required_fields: 0; ranges: 0; columns filters: 0
- Content hash policy: sha256(provider + canonical_json(record_normalized)); excludes technical fields \_ingestion_ts, \_run_id, \_run_type, _dq_\*.

### chembl_publication_similarity

#### 1. Общая информация

- Provider: `chembl`
- Entity: `publication_similarity`
- Pipeline name: `chembl_publication_similarity`
- Primary keys: `['sim_id']`
- Loading strategy: API extract → Bronze append JSONL → Silver merge/upsert → Gold `overwrite`
- Write mode: Silver=`merge`, Gold=`overwrite`

#### 2. Bronze Layer

- Формат хранения: JSONL + zstd (append-only, flat_structure enabled by base config).
- Структура записи: raw provider payload; nested JSON partially flattened at transformer stage.
- Метаданные: batch-level metadata sidecar + pipeline run metadata added downstream (`_run_id`, `_run_type`, `_ingestion_ts`).
- Потенциальный schema drift: высокий для publication pipelines и ChEMBL nested objects; управляется soft validation в Silver.
- Ключевые риски Bronze: nested JSON, nullable-int coercion, provider-specific enum drift.

#### 3. Silver Schema

| Поле              | Тип     | Nullable | Source field      | Notes                         |
| ----------------- | ------- | -------- | ----------------- | ----------------------------- |
| entity_id         | str     | No       | entity_id         |                               |
| content_hash      | str     | No       | content_hash      |                               |
| \_run_id          | str     | No       | \_run_id          |                               |
| \_run_type        | str     | No       | \_run_type        |                               |
| \_source_batch_id | str     | Yes      | \_source_batch_id |                               |
| \_ingestion_ts    | str     | No       | \_ingestion_ts    |                               |
| \_index           | int64   | No       | \_index           |                               |
| \_dq_warn         | bool    | No       | \_dq_warn         |                               |
| \_dq_error        | bool    | No       | \_dq_error        |                               |
| sim_id            | int64   | No       | sim_id            |                               |
| doc_1             | int64   | No       | doc_1             |                               |
| doc_2             | int64   | No       | doc_2             |                               |
| pubmed_id1        | str     | Yes      | pubmed_id1        |                               |
| pubmed_id2        | str     | Yes      | pubmed_id2        |                               |
| tid_tani          | float64 | Yes      | tid_tani          | nullable-int coercion pattern |
| mol_tani          | float64 | Yes      | mol_tani          |                               |
| avg_tani          | float64 | Yes      | avg_tani          |                               |
| max_tani          | float64 | Yes      | max_tani          |                               |

Анализ: 18 columns, nullable=7, non-null=11; partition=[].

#### 4. Gold Schema (Контракт)

- Контрактная версия: class-based contract `ChEMBLDocumentSimilarityGoldSchema` (version field not explicit in class).
- Режим загрузки: `overwrite`
- API стабильность: высокая при соблюдении Pandera strict и alias metadata policy.

| Поле              | Тип     | Nullable | Semantic role | Breaking risk |
| ----------------- | ------- | -------- | ------------- | ------------- |
| entity_id         | str     | No       | metadata      | High          |
| content_hash      | str     | No       | metadata      | High          |
| sim_id            | float64 | No       | business      | High          |
| doc_1             | float64 | No       | business      | High          |
| doc_2             | float64 | No       | business      | High          |
| pubmed_id1        | str     | Yes      | business      | Medium        |
| pubmed_id2        | str     | Yes      | business      | Medium        |
| tid_tani          | float64 | Yes      | business      | Medium        |
| mol_tani          | float64 | Yes      | business      | Medium        |
| avg_tani          | float64 | Yes      | business      | Medium        |
| max_tani          | float64 | Yes      | business      | Medium        |
| \_run_id          | str     | No       | metadata      | High          |
| \_run_type        | str     | No       | metadata      | High          |
| \_source_batch_id | str     | Yes      | metadata      | Medium        |
| \_ingestion_ts    | str     | No       | metadata      | High          |
| \_index           | int64   | No       | metadata      | High          |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping: No
- Поля в Silver, отсутствующие в Gold: 2
  - \_dq_error, \_dq_warn
- Поля в Gold, отсутствующие в Silver: 0
- SSOT risk: medium when publication/provider-specific aliases coexist.

**DQ rules summary**

- Silver required_fields: 0; ranges: 0; columns filters: 0
- Gold required_fields: 0; ranges: 0; columns filters: 0
- Content hash policy: sha256(provider + canonical_json(record_normalized)); excludes technical fields \_ingestion_ts, \_run_id, \_run_type, _dq_\*.

### chembl_publication_term

#### 1. Общая информация

- Provider: `chembl`
- Entity: `publication_term`
- Pipeline name: `chembl_publication_term`
- Primary keys: `['entity_id']`
- Loading strategy: API extract → Bronze append JSONL → Silver merge/upsert → Gold `overwrite`
- Write mode: Silver=`merge`, Gold=`overwrite`

#### 2. Bronze Layer

- Формат хранения: JSONL + zstd (append-only, flat_structure enabled by base config).
- Структура записи: raw provider payload; nested JSON partially flattened at transformer stage.
- Метаданные: batch-level metadata sidecar + pipeline run metadata added downstream (`_run_id`, `_run_type`, `_ingestion_ts`).
- Потенциальный schema drift: высокий для publication pipelines и ChEMBL nested objects; управляется soft validation в Silver.
- Ключевые риски Bronze: nested JSON, nullable-int coercion, provider-specific enum drift.

#### 3. Silver Schema

| Поле              | Тип   | Nullable | Source field      | Notes |
| ----------------- | ----- | -------- | ----------------- | ----- |
| entity_id         | str   | No       | entity_id         |       |
| content_hash      | str   | No       | content_hash      |       |
| \_run_id          | str   | No       | \_run_id          |       |
| \_run_type        | str   | No       | \_run_type        |       |
| \_source_batch_id | str   | Yes      | \_source_batch_id |       |
| \_ingestion_ts    | str   | No       | \_ingestion_ts    |       |
| \_index           | int64 | No       | \_index           |       |
| \_dq_warn         | bool  | No       | \_dq_warn         |       |
| \_dq_error        | bool  | No       | \_dq_error        |       |
| publication_id    | str   | No       | publication_id    |       |
| term              | str   | No       | term              |       |
| term_type         | str   | No       | term_type         |       |
| mesh_id           | str   | Yes      | mesh_id           |       |
| qualifier         | str   | Yes      | qualifier         |       |

Анализ: 14 columns, nullable=3, non-null=11; partition=['term_type'].

#### 4. Gold Schema (Контракт)

- Контрактная версия: class-based contract `ChEMBLDocumentTermGoldSchema` (version field not explicit in class).
- Режим загрузки: `overwrite`
- API стабильность: высокая при соблюдении Pandera strict и alias metadata policy.

| Поле              | Тип   | Nullable | Semantic role | Breaking risk |
| ----------------- | ----- | -------- | ------------- | ------------- |
| entity_id         | str   | No       | metadata      | High          |
| content_hash      | str   | No       | metadata      | High          |
| publication_id    | str   | No       | business      | High          |
| term              | str   | No       | business      | High          |
| term_type         | str   | No       | business      | High          |
| mesh_id           | str   | Yes      | business      | Medium        |
| qualifier         | str   | Yes      | business      | Medium        |
| \_run_id          | str   | No       | metadata      | High          |
| \_run_type        | str   | No       | metadata      | High          |
| \_source_batch_id | str   | Yes      | metadata      | Medium        |
| \_ingestion_ts    | str   | No       | metadata      | High          |
| \_index           | int64 | No       | metadata      | High          |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping: No
- Поля в Silver, отсутствующие в Gold: 2
  - \_dq_error, \_dq_warn
- Поля в Gold, отсутствующие в Silver: 0
- SSOT risk: medium when publication/provider-specific aliases coexist.

**DQ rules summary**

- Silver required_fields: 0; ranges: 0; columns filters: 0
- Gold required_fields: 0; ranges: 0; columns filters: 0
- Content hash policy: sha256(provider + canonical_json(record_normalized)); excludes technical fields \_ingestion_ts, \_run_id, \_run_type, _dq_\*.

### chembl_subcellular_fraction

#### 1. Общая информация

- Provider: `chembl`
- Entity: `subcellular_fraction`
- Pipeline name: `chembl_subcellular_fraction`
- Primary keys: `['entity_id']`
- Loading strategy: API extract → Bronze append JSONL → Silver merge/upsert → Gold `scd2`
- Write mode: Silver=`merge`, Gold=`scd2`

#### 2. Bronze Layer

- Формат хранения: JSONL + zstd (append-only, flat_structure enabled by base config).
- Структура записи: raw provider payload; nested JSON partially flattened at transformer stage.
- Метаданные: batch-level metadata sidecar + pipeline run metadata added downstream (`_run_id`, `_run_type`, `_ingestion_ts`).
- Потенциальный schema drift: высокий для publication pipelines и ChEMBL nested objects; управляется soft validation в Silver.
- Ключевые риски Bronze: nested JSON, nullable-int coercion, provider-specific enum drift.

#### 3. Silver Schema

Pandera schema отсутствует (используется pyarrow-only + Gold contract), что повышает риск drift до Gold.

#### 4. Gold Schema (Контракт)

- Контрактная версия: class-based contract `ChEMBLSubcellularFractionGoldSchema` (version field not explicit in class).
- Режим загрузки: `scd2`
- SCD config: {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}
- API стабильность: высокая при соблюдении Pandera strict и alias metadata policy.

| Поле                    | Тип     | Nullable | Semantic role | Breaking risk |
| ----------------------- | ------- | -------- | ------------- | ------------- |
| entity_id               | str     | No       | metadata      | High          |
| content_hash            | str     | No       | metadata      | High          |
| subcellular_fraction    | str     | No       | business      | High          |
| assay_count             | float64 | Yes      | business      | Medium        |
| example_assay_chembl_id | str     | Yes      | business      | Medium        |
| \_run_id                | str     | No       | metadata      | High          |
| \_run_type              | str     | No       | metadata      | High          |
| \_source_batch_id       | str     | Yes      | metadata      | Medium        |
| \_ingestion_ts          | str     | No       | metadata      | High          |
| \_index                 | int64   | No       | metadata      | High          |

**DQ rules summary**

- Silver required_fields: 0; ranges: 0; columns filters: 0
- Gold required_fields: 0; ranges: 0; columns filters: 0
- Content hash policy: sha256(provider + canonical_json(record_normalized)); excludes technical fields \_ingestion_ts, \_run_id, \_run_type, _dq_\*.

### chembl_target

#### 1. Общая информация

- Provider: `chembl`
- Entity: `target`
- Pipeline name: `chembl_target`
- Primary keys: `['target_id']`
- Loading strategy: API extract → Bronze append JSONL → Silver merge/upsert → Gold `scd2`
- Write mode: Silver=`merge`, Gold=`scd2`

#### 2. Bronze Layer

- Формат хранения: JSONL + zstd (append-only, flat_structure enabled by base config).
- Структура записи: raw provider payload; nested JSON partially flattened at transformer stage.
- Метаданные: batch-level metadata sidecar + pipeline run metadata added downstream (`_run_id`, `_run_type`, `_ingestion_ts`).
- Потенциальный schema drift: высокий для publication pipelines и ChEMBL nested objects; управляется soft validation в Silver.
- Ключевые риски Bronze: nested JSON, nullable-int coercion, provider-specific enum drift.

#### 3. Silver Schema

| Поле                      | Тип     | Nullable | Source field              | Notes                         |
| ------------------------- | ------- | -------- | ------------------------- | ----------------------------- |
| entity_id                 | str     | No       | entity_id                 |                               |
| content_hash              | str     | No       | content_hash              |                               |
| \_run_id                  | str     | No       | \_run_id                  |                               |
| \_run_type                | str     | No       | \_run_type                |                               |
| \_source_batch_id         | str     | Yes      | \_source_batch_id         |                               |
| \_ingestion_ts            | str     | No       | \_ingestion_ts            |                               |
| \_index                   | int64   | No       | \_index                   |                               |
| \_dq_warn                 | bool    | No       | \_dq_warn                 |                               |
| \_dq_error                | bool    | No       | \_dq_error                |                               |
| target_id                 | str     | No       | target_id                 |                               |
| target_type               | str     | Yes      | target_type               |                               |
| pref_name                 | str     | Yes      | pref_name                 |                               |
| taxonomy_id               | float64 | Yes      | taxonomy_id               | nullable-int coercion pattern |
| organism                  | str     | Yes      | organism                  |                               |
| species_group_flag        | bool    | Yes      | species_group_flag        |                               |
| description               | str     | Yes      | description               |                               |
| downgraded                | bool    | Yes      | downgraded                |                               |
| target_components         | str     | Yes      | target_components         |                               |
| cross_references          | str     | Yes      | cross_references          |                               |
| pipeline_stages           | str     | Yes      | pipeline_stages           |                               |
| target_component_synonyms | str     | Yes      | target_component_synonyms |                               |
| component_accessions      | str     | Yes      | component_accessions      |                               |
| component_descriptions    | str     | Yes      | component_descriptions    |                               |
| primary_component_id      | float64 | Yes      | primary_component_id      | nullable-int coercion pattern |
| component_ids             | str     | Yes      | component_ids             |                               |
| component_types           | str     | Yes      | component_types           |                               |
| component_relationships   | str     | Yes      | component_relationships   |                               |

Анализ: 27 columns, nullable=18, non-null=9; partition=['target_type'].

#### 4. Gold Schema (Контракт)

- Контрактная версия: class-based contract `ChEMBLTargetGoldSchema` (version field not explicit in class).
- Режим загрузки: `scd2`
- SCD config: {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}
- API стабильность: высокая при соблюдении Pandera strict и alias metadata policy.

| Поле                      | Тип     | Nullable | Semantic role | Breaking risk |
| ------------------------- | ------- | -------- | ------------- | ------------- |
| entity_id                 | str     | No       | metadata      | High          |
| content_hash              | str     | No       | metadata      | High          |
| target_id                 | str     | No       | business      | High          |
| pref_name                 | str     | Yes      | business      | Medium        |
| target_type               | str     | Yes      | business      | Medium        |
| organism                  | str     | Yes      | business      | Medium        |
| taxonomy_id               | float64 | Yes      | business      | Medium        |
| species_group_flag        | bool    | Yes      | business      | Medium        |
| description               | str     | Yes      | business      | Medium        |
| downgraded                | bool    | Yes      | business      | Medium        |
| pipeline_stages           | str     | Yes      | business      | Medium        |
| target_components         | str     | Yes      | business      | Medium        |
| cross_references          | str     | Yes      | business      | Medium        |
| target_component_synonyms | str     | Yes      | business      | Medium        |
| component_accessions      | str     | Yes      | business      | Medium        |
| primary_component_id      | float64 | Yes      | business      | Medium        |
| component_ids             | str     | Yes      | business      | Medium        |
| component_types           | str     | Yes      | business      | Medium        |
| component_relationships   | str     | Yes      | business      | Medium        |
| \_run_id                  | str     | No       | metadata      | High          |
| \_run_type                | str     | No       | metadata      | High          |
| \_source_batch_id         | str     | Yes      | metadata      | Medium        |
| \_ingestion_ts            | str     | No       | metadata      | High          |
| \_index                   | int64   | No       | metadata      | High          |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping: No
- Поля в Silver, отсутствующие в Gold: 3
  - \_dq_error, \_dq_warn, component_descriptions
- Поля в Gold, отсутствующие в Silver: 0
- SSOT risk: medium when publication/provider-specific aliases coexist.

**DQ rules summary**

- Silver required_fields: 0; ranges: 0; columns filters: 0
- Gold required_fields: 0; ranges: 0; columns filters: 0
- Content hash policy: sha256(provider + canonical_json(record_normalized)); excludes technical fields \_ingestion_ts, \_run_id, \_run_type, _dq_\*.

### chembl_target_component

#### 1. Общая информация

- Provider: `chembl`
- Entity: `target_component`
- Pipeline name: `chembl_target_component`
- Primary keys: `['component_id']`
- Loading strategy: API extract → Bronze append JSONL → Silver merge/upsert → Gold `scd2`
- Write mode: Silver=`merge`, Gold=`scd2`

#### 2. Bronze Layer

- Формат хранения: JSONL + zstd (append-only, flat_structure enabled by base config).
- Структура записи: raw provider payload; nested JSON partially flattened at transformer stage.
- Метаданные: batch-level metadata sidecar + pipeline run metadata added downstream (`_run_id`, `_run_type`, `_ingestion_ts`).
- Потенциальный schema drift: высокий для publication pipelines и ChEMBL nested objects; управляется soft validation в Silver.
- Ключевые риски Bronze: nested JSON, nullable-int coercion, provider-specific enum drift.

#### 3. Silver Schema

| Поле                       | Тип     | Nullable | Source field               | Notes                         |
| -------------------------- | ------- | -------- | -------------------------- | ----------------------------- |
| entity_id                  | str     | No       | entity_id                  |                               |
| content_hash               | str     | No       | content_hash               |                               |
| \_run_id                   | str     | No       | \_run_id                   |                               |
| \_run_type                 | str     | No       | \_run_type                 |                               |
| \_source_batch_id          | str     | Yes      | \_source_batch_id          |                               |
| \_ingestion_ts             | str     | No       | \_ingestion_ts             |                               |
| \_index                    | int64   | No       | \_index                    |                               |
| \_dq_warn                  | bool    | No       | \_dq_warn                  |                               |
| \_dq_error                 | bool    | No       | \_dq_error                 |                               |
| component_id               | int64   | No       | component_id               |                               |
| accession                  | str     | Yes      | accession                  |                               |
| component_type             | str     | Yes      | component_type             |                               |
| description                | str     | Yes      | description                |                               |
| organism                   | str     | Yes      | organism                   |                               |
| taxonomy_id                | Int64   | Yes      | taxonomy_id                |                               |
| target_component_synonyms  | str     | Yes      | target_component_synonyms  |                               |
| target_component_xrefs     | str     | Yes      | target_component_xrefs     |                               |
| protein_classifications    | str     | Yes      | protein_classifications    |                               |
| protein_classification_id  | float64 | Yes      | protein_classification_id  | nullable-int coercion pattern |
| protein_classification_ids | str     | Yes      | protein_classification_ids |                               |

Анализ: 20 columns, nullable=11, non-null=9; partition=['organism'].

#### 4. Gold Schema (Контракт)

- Контрактная версия: class-based contract `ChEMBLTargetComponentGoldSchema` (version field not explicit in class).
- Режим загрузки: `scd2`
- SCD config: {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}
- API стабильность: высокая при соблюдении Pandera strict и alias metadata policy.

| Поле                       | Тип     | Nullable | Semantic role | Breaking risk |
| -------------------------- | ------- | -------- | ------------- | ------------- |
| entity_id                  | str     | No       | metadata      | High          |
| content_hash               | str     | No       | metadata      | High          |
| component_id               | float64 | No       | business      | High          |
| accession                  | str     | Yes      | business      | Medium        |
| component_type             | str     | Yes      | business      | Medium        |
| description                | str     | Yes      | business      | Medium        |
| organism                   | str     | Yes      | business      | Medium        |
| taxonomy_id                | float64 | Yes      | business      | Medium        |
| target_component_synonyms  | str     | Yes      | business      | Medium        |
| target_component_xrefs     | str     | Yes      | business      | Medium        |
| protein_classifications    | str     | Yes      | business      | Medium        |
| protein_classification_id  | float64 | Yes      | business      | Medium        |
| protein_classification_ids | str     | Yes      | business      | Medium        |
| \_run_id                   | str     | No       | metadata      | High          |
| \_run_type                 | str     | No       | metadata      | High          |
| \_source_batch_id          | str     | Yes      | metadata      | Medium        |
| \_ingestion_ts             | str     | No       | metadata      | High          |
| \_index                    | int64   | No       | metadata      | High          |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping: No
- Поля в Silver, отсутствующие в Gold: 2
  - \_dq_error, \_dq_warn
- Поля в Gold, отсутствующие в Silver: 0
- SSOT risk: medium when publication/provider-specific aliases coexist.

**DQ rules summary**

- Silver required_fields: 0; ranges: 0; columns filters: 0
- Gold required_fields: 0; ranges: 0; columns filters: 0
- Content hash policy: sha256(provider + canonical_json(record_normalized)); excludes technical fields \_ingestion_ts, \_run_id, \_run_type, _dq_\*.

### chembl_tissue

#### 1. Общая информация

- Provider: `chembl`
- Entity: `tissue`
- Pipeline name: `chembl_tissue`
- Primary keys: `['tissue_id']`
- Loading strategy: API extract → Bronze append JSONL → Silver merge/upsert → Gold `scd2`
- Write mode: Silver=`merge`, Gold=`scd2`

#### 2. Bronze Layer

- Формат хранения: JSONL + zstd (append-only, flat_structure enabled by base config).
- Структура записи: raw provider payload; nested JSON partially flattened at transformer stage.
- Метаданные: batch-level metadata sidecar + pipeline run metadata added downstream (`_run_id`, `_run_type`, `_ingestion_ts`).
- Потенциальный schema drift: высокий для publication pipelines и ChEMBL nested objects; управляется soft validation в Silver.
- Ключевые риски Bronze: nested JSON, nullable-int coercion, provider-specific enum drift.

#### 3. Silver Schema

Pandera schema отсутствует (используется pyarrow-only + Gold contract), что повышает риск drift до Gold.

#### 4. Gold Schema (Контракт)

- Контрактная версия: class-based contract `ChEMBLTissueGoldSchema` (version field not explicit in class).
- Режим загрузки: `scd2`
- SCD config: {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}
- API стабильность: высокая при соблюдении Pandera strict и alias metadata policy.

| Поле              | Тип   | Nullable | Semantic role | Breaking risk |
| ----------------- | ----- | -------- | ------------- | ------------- |
| tissue_chembl_id  | str   | No       | business      | High          |
| pref_name         | str   | No       | business      | High          |
| bto_id            | str   | Yes      | business      | Medium        |
| caloha_id         | str   | Yes      | business      | Medium        |
| efo_id            | str   | Yes      | business      | Medium        |
| uberon_id         | str   | Yes      | business      | Medium        |
| \_run_id          | str   | No       | metadata      | High          |
| \_run_type        | str   | No       | metadata      | High          |
| \_source_batch_id | str   | Yes      | metadata      | Medium        |
| \_ingestion_ts    | str   | No       | metadata      | High          |
| \_index           | int64 | No       | metadata      | High          |

**DQ rules summary**

- Silver required_fields: 0; ranges: 0; columns filters: 0
- Gold required_fields: 0; ranges: 0; columns filters: 0
- Content hash policy: sha256(provider + canonical_json(record_normalized)); excludes technical fields \_ingestion_ts, \_run_id, \_run_type, _dq_\*.

### crossref_publication

#### 1. Общая информация

- Provider: `crossref`
- Entity: `publication`
- Pipeline name: `crossref_publication`
- Primary keys: `['doi']`
- Loading strategy: API extract → Bronze append JSONL → Silver merge/upsert → Gold `scd2`
- Write mode: Silver=`merge`, Gold=`scd2`

#### 2. Bronze Layer

- Формат хранения: JSONL + zstd (append-only, flat_structure enabled by base config).
- Структура записи: raw provider payload; nested JSON partially flattened at transformer stage.
- Метаданные: batch-level metadata sidecar + pipeline run metadata added downstream (`_run_id`, `_run_type`, `_ingestion_ts`).
- Потенциальный schema drift: высокий для publication pipelines и ChEMBL nested objects; управляется soft validation в Silver.
- Ключевые риски Bronze: nested JSON, nullable-int coercion, provider-specific enum drift.

#### 3. Silver Schema

| Поле                                 | Тип   | Nullable | Source field                         | Notes |
| ------------------------------------ | ----- | -------- | ------------------------------------ | ----- |
| entity_id                            | str   | No       | entity_id                            |       |
| content_hash                         | str   | No       | content_hash                         |       |
| \_run_id                             | str   | No       | \_run_id                             |       |
| \_run_type                           | str   | No       | \_run_type                           |       |
| \_source_batch_id                    | str   | Yes      | \_source_batch_id                    |       |
| \_ingestion_ts                       | str   | No       | \_ingestion_ts                       |       |
| \_index                              | int64 | No       | \_index                              |       |
| \_dq_warn                            | bool  | No       | \_dq_warn                            |       |
| \_dq_error                           | bool  | No       | \_dq_error                           |       |
| pmid                                 | str   | Yes      | pmid                                 |       |
| doi                                  | str   | No       | doi                                  |       |
| pmc_id                               | str   | Yes      | pmc_id                               |       |
| title                                | str   | Yes      | title                                |       |
| abstract                             | str   | Yes      | abstract                             |       |
| authors                              | str   | Yes      | authors                              |       |
| affiliation_list                     | str   | Yes      | affiliation_list                     |       |
| author_orcids                        | str   | Yes      | author_orcids                        |       |
| author_keys                          | str   | Yes      | author_keys                          |       |
| journal                              | str   | Yes      | journal                              |       |
| publication_year                     | Int64 | Yes      | publication_year                     |       |
| publication_date                     | str   | Yes      | publication_date                     |       |
| publication_type                     | str   | Yes      | publication_type                     |       |
| publication_type_unified             | str   | Yes      | publication_type_unified             |       |
| publication_subclass                 | str   | Yes      | publication_subclass                 |       |
| publication_class                    | str   | Yes      | publication_class                    |       |
| language                             | str   | Yes      | language                             |       |
| page_first                           | str   | Yes      | page_first                           |       |
| page_last                            | str   | Yes      | page_last                            |       |
| citations_received                   | Int64 | Yes      | citations_received                   |       |
| citations_made                       | Int64 | Yes      | citations_made                       |       |
| is_oa                                | bool  | Yes      | is_oa                                |       |
| \_lookup_method                      | str   | No       | \_lookup_method                      |       |
| \_original_id                        | str   | Yes      | \_original_id                        |       |
| issn                                 | str   | Yes      | issn                                 |       |
| issn_list                            | str   | Yes      | issn_list                            |       |
| publisher                            | str   | Yes      | publisher                            |       |
| published_print                      | str   | Yes      | published_print                      |       |
| published_online                     | str   | Yes      | published_online                     |       |
| license_url                          | str   | Yes      | license_url                          |       |
| subject_keywords                     | str   | Yes      | subject_keywords                     |       |
| content_domain_domains               | str   | Yes      | content_domain_domains               |       |
| content_domain_crossmark_restriction | bool  | Yes      | content_domain_crossmark_restriction |       |
| alternative_id                       | str   | Yes      | alternative_id                       |       |
| published                            | str   | Yes      | published                            |       |
| journal_name_short                   | str   | Yes      | journal_name_short                   |       |
| issn_print                           | str   | Yes      | issn_print                           |       |
| issn_electronic                      | str   | Yes      | issn_electronic                      |       |
| author_details                       | str   | Yes      | author_details                       |       |
| references                           | str   | Yes      | references                           |       |

Анализ: 49 columns, nullable=39, non-null=10; partition=[].

#### 4. Gold Schema (Контракт)

- Контрактная версия: class-based contract `CrossRefPublicationGoldSchema` (version field not explicit in class).
- Режим загрузки: `scd2`
- SCD config: {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}
- API стабильность: высокая при соблюдении Pandera strict и alias metadata policy.

| Поле                                 | Тип     | Nullable | Semantic role | Breaking risk |
| ------------------------------------ | ------- | -------- | ------------- | ------------- |
| entity_id                            | str     | No       | metadata      | High          |
| content_hash                         | str     | No       | metadata      | High          |
| doi                                  | str     | No       | business      | High          |
| title                                | str     | Yes      | business      | Medium        |
| authors                              | str     | Yes      | business      | Medium        |
| journal                              | str     | Yes      | business      | Medium        |
| issn                                 | str     | Yes      | business      | Medium        |
| issn_list                            | str     | Yes      | business      | Medium        |
| publisher                            | str     | Yes      | business      | Medium        |
| volume                               | str     | Yes      | business      | Medium        |
| issue                                | str     | Yes      | business      | Medium        |
| page_first                           | str     | Yes      | business      | Medium        |
| page_last                            | str     | Yes      | business      | Medium        |
| publication_year                     | float64 | Yes      | business      | Medium        |
| publication_date                     | str     | Yes      | business      | Medium        |
| published_print                      | str     | Yes      | business      | Medium        |
| published_online                     | str     | Yes      | business      | Medium        |
| publication_type                     | str     | Yes      | business      | Medium        |
| citations_received                   | float64 | Yes      | business      | Medium        |
| citations_made                       | float64 | Yes      | business      | Medium        |
| language                             | str     | Yes      | business      | Medium        |
| license_url                          | str     | Yes      | business      | Medium        |
| subject_keywords                     | str     | Yes      | business      | Medium        |
| content_domain_domains               | str     | Yes      | business      | Medium        |
| content_domain_crossmark_restriction | bool    | Yes      | business      | Medium        |
| alternative_id                       | str     | Yes      | business      | Medium        |
| published                            | str     | Yes      | business      | Medium        |
| journal_name_short                   | str     | Yes      | business      | Medium        |
| issn_print                           | str     | Yes      | business      | Medium        |
| issn_electronic                      | str     | Yes      | business      | Medium        |
| author_keys                          | str     | Yes      | business      | Medium        |
| author_orcids                        | str     | Yes      | business      | Medium        |
| author_details                       | str     | Yes      | business      | Medium        |
| references                           | str     | Yes      | business      | Medium        |
| \_source                             | str     | No       | metadata      | High          |
| \_lookup_method                      | str     | No       | metadata      | High          |
| \_original_id                        | str     | Yes      | metadata      | Medium        |
| \_dq_warn                            | bool    | No       | metadata      | High          |
| \_dq_error                           | bool    | No       | metadata      | High          |
| \_run_id                             | str     | No       | metadata      | High          |
| \_run_type                           | str     | No       | metadata      | High          |
| \_source_batch_id                    | str     | Yes      | metadata      | Medium        |
| \_ingestion_ts                       | str     | No       | metadata      | High          |
| \_index                              | int64   | No       | metadata      | High          |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping: No
- Поля в Silver, отсутствующие в Gold: 8
  - abstract, affiliation_list, is_oa, pmc_id, pmid, publication_class, publication_subclass, publication_type_unified
- Поля в Gold, отсутствующие в Silver: 3
  - \_source, issue, volume
- SSOT risk: medium when publication/provider-specific aliases coexist.

**DQ rules summary**

- Silver required_fields: 0; ranges: 0; columns filters: 0
- Gold required_fields: 0; ranges: 0; columns filters: 0
- Content hash policy: sha256(provider + canonical_json(record_normalized)); excludes technical fields \_ingestion_ts, \_run_id, \_run_type, _dq_\*.

### openalex_publication

#### 1. Общая информация

- Provider: `openalex`
- Entity: `publication`
- Pipeline name: `openalex_publication`
- Primary keys: `['openalex_id']`
- Loading strategy: API extract → Bronze append JSONL → Silver merge/upsert → Gold `scd2`
- Write mode: Silver=`merge`, Gold=`scd2`

#### 2. Bronze Layer

- Формат хранения: JSONL + zstd (append-only, flat_structure enabled by base config).
- Структура записи: raw provider payload; nested JSON partially flattened at transformer stage.
- Метаданные: batch-level metadata sidecar + pipeline run metadata added downstream (`_run_id`, `_run_type`, `_ingestion_ts`).
- Потенциальный schema drift: высокий для publication pipelines и ChEMBL nested objects; управляется soft validation в Silver.
- Ключевые риски Bronze: nested JSON, nullable-int coercion, provider-specific enum drift.

#### 3. Silver Schema

| Поле                      | Тип     | Nullable | Source field              | Notes |
| ------------------------- | ------- | -------- | ------------------------- | ----- |
| entity_id                 | str     | No       | entity_id                 |       |
| content_hash              | str     | No       | content_hash              |       |
| \_run_id                  | str     | No       | \_run_id                  |       |
| \_run_type                | str     | No       | \_run_type                |       |
| \_source_batch_id         | str     | Yes      | \_source_batch_id         |       |
| \_ingestion_ts            | str     | No       | \_ingestion_ts            |       |
| \_index                   | int64   | No       | \_index                   |       |
| \_dq_warn                 | bool    | No       | \_dq_warn                 |       |
| \_dq_error                | bool    | No       | \_dq_error                |       |
| pmid                      | str     | Yes      | pmid                      |       |
| doi                       | str     | Yes      | doi                       |       |
| pmc_id                    | str     | Yes      | pmc_id                    |       |
| title                     | str     | Yes      | title                     |       |
| abstract                  | str     | Yes      | abstract                  |       |
| authors                   | str     | Yes      | authors                   |       |
| affiliation_list          | str     | Yes      | affiliation_list          |       |
| author_orcids             | str     | Yes      | author_orcids             |       |
| author_keys               | str     | Yes      | author_keys               |       |
| journal                   | str     | Yes      | journal                   |       |
| publication_year          | Int64   | Yes      | publication_year          |       |
| publication_date          | str     | Yes      | publication_date          |       |
| publication_type          | str     | Yes      | publication_type          |       |
| publication_type_unified  | str     | Yes      | publication_type_unified  |       |
| publication_subclass      | str     | Yes      | publication_subclass      |       |
| publication_class         | str     | Yes      | publication_class         |       |
| language                  | str     | Yes      | language                  |       |
| page_first                | str     | Yes      | page_first                |       |
| page_last                 | str     | Yes      | page_last                 |       |
| citations_received        | Int64   | Yes      | citations_received        |       |
| citations_made            | Int64   | Yes      | citations_made            |       |
| is_oa                     | bool    | Yes      | is_oa                     |       |
| \_lookup_method           | str     | No       | \_lookup_method           |       |
| \_original_id             | str     | Yes      | \_original_id             |       |
| openalex_id               | str     | No       | openalex_id               |       |
| issn                      | str     | Yes      | issn                      |       |
| publisher                 | str     | Yes      | publisher                 |       |
| oa_status                 | str     | Yes      | oa_status                 |       |
| volume                    | str     | Yes      | volume                    |       |
| issue                     | str     | Yes      | issue                     |       |
| fwci                      | float64 | Yes      | fwci                      |       |
| is_retracted              | bool    | No       | is_retracted              |       |
| subject_topics            | str     | Yes      | subject_topics            |       |
| primary_topic             | str     | Yes      | primary_topic             |       |
| grants                    | str     | Yes      | grants                    |       |
| subject_mesh              | str     | Yes      | subject_mesh              |       |
| subject_keywords          | str     | Yes      | subject_keywords          |       |
| mag_id                    | str     | Yes      | mag_id                    |       |
| author_openalex_ids       | str     | Yes      | author_openalex_ids       |       |
| institution_ids           | str     | Yes      | institution_ids           |       |
| institution_country_codes | str     | Yes      | institution_country_codes |       |
| ror_ids                   | str     | Yes      | ror_ids                   |       |

Анализ: 51 columns, nullable=40, non-null=11; partition=[].

#### 4. Gold Schema (Контракт)

- Контрактная версия: class-based contract `OpenAlexPublicationGoldSchema` (version field not explicit in class).
- Режим загрузки: `scd2`
- SCD config: {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}
- API стабильность: высокая при соблюдении Pandera strict и alias metadata policy.

| Поле                      | Тип     | Nullable | Semantic role | Breaking risk |
| ------------------------- | ------- | -------- | ------------- | ------------- |
| entity_id                 | str     | No       | metadata      | High          |
| content_hash              | str     | No       | metadata      | High          |
| openalex_id               | str     | No       | business      | High          |
| doi                       | str     | Yes      | business      | Medium        |
| pmid                      | str     | Yes      | business      | Medium        |
| title                     | str     | Yes      | business      | Medium        |
| abstract                  | str     | Yes      | business      | Medium        |
| authors                   | str     | Yes      | business      | Medium        |
| affiliation_list          | str     | Yes      | business      | Medium        |
| subject_mesh              | str     | Yes      | business      | Medium        |
| subject_keywords          | str     | Yes      | business      | Medium        |
| mag_id                    | str     | Yes      | business      | Medium        |
| journal                   | str     | Yes      | business      | Medium        |
| issn                      | str     | Yes      | business      | Medium        |
| publisher                 | str     | Yes      | business      | Medium        |
| volume                    | str     | Yes      | business      | Medium        |
| issue                     | str     | Yes      | business      | Medium        |
| page_first                | str     | Yes      | business      | Medium        |
| page_last                 | str     | Yes      | business      | Medium        |
| publication_year          | float64 | Yes      | business      | Medium        |
| publication_date          | str     | Yes      | business      | Medium        |
| publication_type          | str     | Yes      | business      | Medium        |
| is_oa                     | bool    | Yes      | business      | Medium        |
| oa_status                 | str     | Yes      | business      | Medium        |
| is_retracted              | bool    | No       | business      | High          |
| citations_received        | float64 | Yes      | business      | Medium        |
| language                  | str     | Yes      | business      | Medium        |
| fwci                      | float64 | Yes      | business      | Medium        |
| citations_made            | float64 | Yes      | business      | Medium        |
| subject_topics            | str     | Yes      | business      | Medium        |
| primary_topic             | str     | Yes      | business      | Medium        |
| grants                    | str     | Yes      | business      | Medium        |
| institution_ids           | str     | Yes      | business      | Medium        |
| institution_country_codes | str     | Yes      | business      | Medium        |
| ror_ids                   | str     | Yes      | business      | Medium        |
| author_keys               | str     | Yes      | business      | Medium        |
| author_openalex_ids       | str     | Yes      | business      | Medium        |
| author_orcids             | str     | Yes      | business      | Medium        |
| \_source                  | str     | No       | metadata      | High          |
| \_lookup_method           | str     | No       | metadata      | High          |
| \_original_id             | str     | Yes      | metadata      | Medium        |
| \_dq_warn                 | bool    | No       | metadata      | High          |
| \_dq_error                | bool    | No       | metadata      | High          |
| \_run_id                  | str     | No       | metadata      | High          |
| \_run_type                | str     | No       | metadata      | High          |
| \_source_batch_id         | str     | Yes      | metadata      | Medium        |
| \_ingestion_ts            | str     | No       | metadata      | High          |
| \_index                   | int64   | No       | metadata      | High          |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping: No
- Поля в Silver, отсутствующие в Gold: 4
  - pmc_id, publication_class, publication_subclass, publication_type_unified
- Поля в Gold, отсутствующие в Silver: 1
  - \_source
- SSOT risk: medium when publication/provider-specific aliases coexist.

**DQ rules summary**

- Silver required_fields: 0; ranges: 0; columns filters: 0
- Gold required_fields: 0; ranges: 0; columns filters: 0
- Content hash policy: sha256(provider + canonical_json(record_normalized)); excludes technical fields \_ingestion_ts, \_run_id, \_run_type, _dq_\*.

### pubchem_compound

#### 1. Общая информация

- Provider: `pubchem`
- Entity: `compound`
- Pipeline name: `pubchem_compound`
- Primary keys: `['molecule_id']`
- Loading strategy: API extract → Bronze append JSONL → Silver merge/upsert → Gold `scd2`
- Write mode: Silver=`merge`, Gold=`scd2`

#### 2. Bronze Layer

- Формат хранения: JSONL + zstd (append-only, flat_structure enabled by base config).
- Структура записи: raw provider payload; nested JSON partially flattened at transformer stage.
- Метаданные: batch-level metadata sidecar + pipeline run metadata added downstream (`_run_id`, `_run_type`, `_ingestion_ts`).
- Потенциальный schema drift: высокий для publication pipelines и ChEMBL nested objects; управляется soft validation в Silver.
- Ключевые риски Bronze: nested JSON, nullable-int coercion, provider-specific enum drift.

#### 3. Silver Schema

| Поле                        | Тип     | Nullable | Source field                | Notes |
| --------------------------- | ------- | -------- | --------------------------- | ----- |
| entity_id                   | str     | No       | entity_id                   |       |
| content_hash                | str     | No       | content_hash                |       |
| \_run_id                    | str     | No       | \_run_id                    |       |
| \_run_type                  | str     | No       | \_run_type                  |       |
| \_source_batch_id           | str     | Yes      | \_source_batch_id           |       |
| \_ingestion_ts              | str     | No       | \_ingestion_ts              |       |
| \_index                     | int64   | No       | \_index                     |       |
| \_dq_warn                   | bool    | No       | \_dq_warn                   |       |
| \_dq_error                  | bool    | No       | \_dq_error                  |       |
| molecule_id                 | str     | No       | molecule_id                 |       |
| canonical_smiles            | str     | Yes      | canonical_smiles            |       |
| isomeric_smiles             | str     | Yes      | isomeric_smiles             |       |
| inchi                       | str     | Yes      | inchi                       |       |
| inchi_key                   | str     | Yes      | inchi_key                   |       |
| molecular_formula           | str     | Yes      | molecular_formula           |       |
| iupac_name                  | str     | Yes      | iupac_name                  |       |
| molecular_weight            | float64 | Yes      | molecular_weight            |       |
| exact_mass                  | float64 | Yes      | exact_mass                  |       |
| monoisotopic_mass           | float64 | Yes      | monoisotopic_mass           |       |
| xlogp                       | float64 | Yes      | xlogp                       |       |
| tpsa                        | float64 | Yes      | tpsa                        |       |
| complexity                  | float64 | Yes      | complexity                  |       |
| charge                      | Int64   | Yes      | charge                      |       |
| heavy_atom_count            | Int64   | Yes      | heavy_atom_count            |       |
| h_bond_donor_count          | Int64   | Yes      | h_bond_donor_count          |       |
| h_bond_acceptor_count       | Int64   | Yes      | h_bond_acceptor_count       |       |
| rotatable_bond_count        | Int64   | Yes      | rotatable_bond_count        |       |
| atom_stereo_count           | Int64   | Yes      | atom_stereo_count           |       |
| defined_atom_stereo_count   | Int64   | Yes      | defined_atom_stereo_count   |       |
| undefined_atom_stereo_count | Int64   | Yes      | undefined_atom_stereo_count |       |
| bond_stereo_count           | Int64   | Yes      | bond_stereo_count           |       |
| defined_bond_stereo_count   | Int64   | Yes      | defined_bond_stereo_count   |       |
| undefined_bond_stereo_count | Int64   | Yes      | undefined_bond_stereo_count |       |
| isotope_atom_count          | Int64   | Yes      | isotope_atom_count          |       |
| covalent_unit_count         | Int64   | Yes      | covalent_unit_count         |       |
| volume_3d                   | float64 | Yes      | volume_3d                   |       |
| conformer_count_3d          | float64 | Yes      | conformer_count_3d          |       |
| feature_acceptor_count_3d   | float64 | Yes      | feature_acceptor_count_3d   |       |
| feature_donor_count_3d      | float64 | Yes      | feature_donor_count_3d      |       |
| feature_anion_count_3d      | float64 | Yes      | feature_anion_count_3d      |       |
| feature_cation_count_3d     | float64 | Yes      | feature_cation_count_3d     |       |
| feature_ring_count_3d       | float64 | Yes      | feature_ring_count_3d       |       |
| feature_hydrophobe_count_3d | float64 | Yes      | feature_hydrophobe_count_3d |       |
| effective_rotor_count_3d    | float64 | Yes      | effective_rotor_count_3d    |       |
| conformer_rmsd_3d           | float64 | Yes      | conformer_rmsd_3d           |       |
| x_steric_quadrupole_3d      | float64 | Yes      | x_steric_quadrupole_3d      |       |
| y_steric_quadrupole_3d      | float64 | Yes      | y_steric_quadrupole_3d      |       |
| z_steric_quadrupole_3d      | float64 | Yes      | z_steric_quadrupole_3d      |       |
| feature_count_3d            | float64 | Yes      | feature_count_3d            |       |

Анализ: 49 columns, nullable=40, non-null=9; partition=['batch_date'].

#### 4. Gold Schema (Контракт)

- Контрактная версия: class-based contract `PubChemCompoundGoldSchema` (version field not explicit in class).
- Режим загрузки: `scd2`
- SCD config: {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}
- API стабильность: высокая при соблюдении Pandera strict и alias metadata policy.

| Поле              | Тип     | Nullable | Semantic role | Breaking risk |
| ----------------- | ------- | -------- | ------------- | ------------- |
| entity_id         | str     | No       | metadata      | High          |
| molecule_id       | str     | No       | business      | High          |
| molecular_formula | str     | Yes      | business      | Medium        |
| molecular_weight  | float64 | Yes      | business      | Medium        |
| canonical_smiles  | str     | Yes      | business      | Medium        |
| isomeric_smiles   | str     | Yes      | business      | Medium        |
| inchi             | str     | Yes      | business      | Medium        |
| inchi_key         | str     | Yes      | business      | Medium        |
| xlogp             | float64 | Yes      | business      | Medium        |
| tpsa              | float64 | Yes      | business      | Medium        |
| iupac_name        | str     | Yes      | business      | Medium        |
| content_hash      | str     | No       | metadata      | High          |
| \_run_id          | str     | No       | metadata      | High          |
| \_run_type        | str     | No       | metadata      | High          |
| \_source_batch_id | str     | Yes      | metadata      | Medium        |
| \_ingestion_ts    | str     | No       | metadata      | High          |
| \_index           | int64   | No       | metadata      | High          |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping: No
- Поля в Silver, отсутствующие в Gold: 32
  - \_dq_error, \_dq_warn, atom_stereo_count, bond_stereo_count, charge, complexity, conformer_count_3d, conformer_rmsd_3d, covalent_unit_count, defined_atom_stereo_count, defined_bond_stereo_count, effective_rotor_count_3d, exact_mass, feature_acceptor_count_3d, feature_anion_count_3d, feature_cation_count_3d, feature_count_3d, feature_donor_count_3d, feature_hydrophobe_count_3d, feature_ring_count_3d ...
- Поля в Gold, отсутствующие в Silver: 0
- SSOT risk: medium when publication/provider-specific aliases coexist.

**DQ rules summary**

- Silver required_fields: 0; ranges: 0; columns filters: 0
- Gold required_fields: 0; ranges: 0; columns filters: 0
- Content hash policy: sha256(provider + canonical_json(record_normalized)); excludes technical fields \_ingestion_ts, \_run_id, \_run_type, _dq_\*.

### pubmed_publication

#### 1. Общая информация

- Provider: `pubmed`
- Entity: `publication`
- Pipeline name: `pubmed_publication`
- Primary keys: `['pmid']`
- Loading strategy: API extract → Bronze append JSONL → Silver merge/upsert → Gold `scd2`
- Write mode: Silver=`merge`, Gold=`scd2`

#### 2. Bronze Layer

- Формат хранения: JSONL + zstd (append-only, flat_structure enabled by base config).
- Структура записи: raw provider payload; nested JSON partially flattened at transformer stage.
- Метаданные: batch-level metadata sidecar + pipeline run metadata added downstream (`_run_id`, `_run_type`, `_ingestion_ts`).
- Потенциальный schema drift: высокий для publication pipelines и ChEMBL nested objects; управляется soft validation в Silver.
- Ключевые риски Bronze: nested JSON, nullable-int coercion, provider-specific enum drift.

#### 3. Silver Schema

| Поле                      | Тип            | Nullable | Source field              | Notes |
| ------------------------- | -------------- | -------- | ------------------------- | ----- |
| entity_id                 | str            | No       | entity_id                 |       |
| content_hash              | str            | No       | content_hash              |       |
| \_run_id                  | str            | No       | \_run_id                  |       |
| \_run_type                | str            | No       | \_run_type                |       |
| \_source_batch_id         | str            | Yes      | \_source_batch_id         |       |
| \_ingestion_ts            | str            | No       | \_ingestion_ts            |       |
| \_index                   | int64          | No       | \_index                   |       |
| \_dq_warn                 | bool           | No       | \_dq_warn                 |       |
| \_dq_error                | bool           | No       | \_dq_error                |       |
| pmid                      | str            | No       | pmid                      |       |
| doi                       | str            | Yes      | doi                       |       |
| pmc_id                    | str            | Yes      | pmc_id                    |       |
| title                     | str            | No       | title                     |       |
| abstract                  | str            | Yes      | abstract                  |       |
| authors                   | str            | Yes      | authors                   |       |
| affiliation_list          | str            | Yes      | affiliation_list          |       |
| author_orcids             | str            | Yes      | author_orcids             |       |
| author_keys               | str            | Yes      | author_keys               |       |
| journal                   | str            | Yes      | journal                   |       |
| publication_year          | Int64          | Yes      | publication_year          |       |
| publication_date          | str            | Yes      | publication_date          |       |
| publication_type          | str            | Yes      | publication_type          |       |
| publication_type_unified  | str            | Yes      | publication_type_unified  |       |
| publication_subclass      | str            | Yes      | publication_subclass      |       |
| publication_class         | str            | Yes      | publication_class         |       |
| language                  | str            | Yes      | language                  |       |
| page_first                | str            | Yes      | page_first                |       |
| page_last                 | str            | Yes      | page_last                 |       |
| citations_received        | Int64          | Yes      | citations_received        |       |
| citations_made            | Int64          | Yes      | citations_made            |       |
| is_oa                     | bool           | Yes      | is_oa                     |       |
| \_lookup_method           | str            | No       | \_lookup_method           |       |
| \_original_id             | str            | Yes      | \_original_id             |       |
| pii                       | str            | Yes      | pii                       |       |
| mid                       | str            | Yes      | mid                       |       |
| publisher_id              | str            | Yes      | publisher_id              |       |
| abstract_structured       | bool           | Yes      | abstract_structured       |       |
| journal_name_short        | str            | Yes      | journal_name_short        |       |
| journal_iso_abbrev        | str            | Yes      | journal_iso_abbrev        |       |
| issn                      | str            | Yes      | issn                      |       |
| journal_issn_type         | str            | Yes      | journal_issn_type         |       |
| nlm_unique_id             | str            | Yes      | nlm_unique_id             |       |
| country                   | str            | Yes      | country                   |       |
| medline_pgn               | str            | Yes      | medline_pgn               |       |
| page_range                | str            | Yes      | page_range                |       |
| pub_month                 | Int64          | Yes      | pub_month                 |       |
| pub_day                   | Int64          | Yes      | pub_day                   |       |
| publication_status        | str            | Yes      | publication_status        |       |
| publication_type_list     | str            | Yes      | publication_type_list     |       |
| date_completed            | datetime64[ns] | Yes      | date_completed            |       |
| date_revised              | datetime64[ns] | Yes      | date_revised              |       |
| citation_subset           | str            | Yes      | citation_subset           |       |
| affiliation_structured    | str            | Yes      | affiliation_structured    |       |
| author_count              | Int64          | Yes      | author_count              |       |
| mesh_heading_count        | Int64          | Yes      | mesh_heading_count        |       |
| keyword_count             | Int64          | Yes      | keyword_count             |       |
| grant_count               | Int64          | Yes      | grant_count               |       |
| chemical_count            | Int64          | Yes      | chemical_count            |       |
| subject_mesh              | str            | Yes      | subject_mesh              |       |
| chemicals                 | str            | Yes      | chemicals                 |       |
| subject_keywords          | str            | Yes      | subject_keywords          |       |
| databanks                 | str            | Yes      | databanks                 |       |
| gene_symbols              | str            | Yes      | gene_symbols              |       |
| publication_types         | str            | Yes      | publication_types         |       |
| authors_with_affiliations | str            | Yes      | authors_with_affiliations |       |

Анализ: 65 columns, nullable=54, non-null=11; partition=[].

#### 4. Gold Schema (Контракт)

- Контрактная версия: class-based contract `PubMedPublicationGoldSchema` (version field not explicit in class).
- Режим загрузки: `scd2`
- SCD config: {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}
- API стабильность: высокая при соблюдении Pandera strict и alias metadata policy.

| Поле                      | Тип     | Nullable | Semantic role | Breaking risk |
| ------------------------- | ------- | -------- | ------------- | ------------- |
| entity_id                 | str     | No       | metadata      | High          |
| content_hash              | str     | No       | metadata      | High          |
| pmid                      | str     | No       | business      | High          |
| doi                       | str     | Yes      | business      | Medium        |
| pmc_id                    | str     | Yes      | business      | Medium        |
| title                     | str     | No       | business      | High          |
| abstract                  | str     | Yes      | business      | Medium        |
| abstract_structured       | bool    | Yes      | business      | Medium        |
| journal                   | str     | Yes      | business      | Medium        |
| journal_name_short        | str     | Yes      | business      | Medium        |
| journal_iso_abbrev        | str     | Yes      | business      | Medium        |
| journal_issn_type         | str     | Yes      | business      | Medium        |
| issn                      | str     | Yes      | business      | Medium        |
| nlm_unique_id             | str     | Yes      | business      | Medium        |
| volume                    | str     | Yes      | business      | Medium        |
| issue                     | str     | Yes      | business      | Medium        |
| page_range                | str     | Yes      | business      | Medium        |
| medline_pgn               | str     | Yes      | business      | Medium        |
| page_first                | str     | Yes      | business      | Medium        |
| page_last                 | str     | Yes      | business      | Medium        |
| authors                   | str     | Yes      | business      | Medium        |
| author_keys               | str     | Yes      | business      | Medium        |
| affiliation_list          | str     | Yes      | business      | Medium        |
| authors_with_affiliations | str     | Yes      | business      | Medium        |
| affiliation_structured    | str     | Yes      | business      | Medium        |
| pii                       | str     | Yes      | business      | Medium        |
| mid                       | str     | Yes      | business      | Medium        |
| publisher_id              | str     | Yes      | business      | Medium        |
| pub_month                 | float64 | Yes      | business      | Medium        |
| pub_day                   | float64 | Yes      | business      | Medium        |
| publication_date          | str     | Yes      | business      | Medium        |
| publication_year          | float64 | Yes      | business      | Medium        |
| date_completed            | str     | Yes      | business      | Medium        |
| date_revised              | str     | Yes      | business      | Medium        |
| publication_status        | str     | Yes      | business      | Medium        |
| publication_type_list     | str     | Yes      | business      | Medium        |
| publication_type          | str     | Yes      | business      | Medium        |
| publication_types         | str     | Yes      | business      | Medium        |
| subject_keywords          | str     | Yes      | business      | Medium        |
| subject_mesh              | str     | Yes      | business      | Medium        |
| chemicals                 | str     | Yes      | business      | Medium        |
| databanks                 | str     | Yes      | business      | Medium        |
| gene_symbols              | str     | Yes      | business      | Medium        |
| citation_subset           | str     | Yes      | business      | Medium        |
| language                  | str     | Yes      | business      | Medium        |
| country                   | str     | Yes      | business      | Medium        |
| author_count              | float64 | Yes      | business      | Medium        |
| mesh_heading_count        | float64 | Yes      | business      | Medium        |
| keyword_count             | float64 | Yes      | business      | Medium        |
| grant_count               | float64 | Yes      | business      | Medium        |
| citations_made            | float64 | Yes      | business      | Medium        |
| chemical_count            | float64 | Yes      | business      | Medium        |
| \_source                  | str     | No       | metadata      | High          |
| \_lookup_method           | str     | No       | metadata      | High          |
| \_original_id             | str     | Yes      | metadata      | Medium        |
| \_dq_warn                 | bool    | No       | metadata      | High          |
| \_dq_error                | bool    | No       | metadata      | High          |
| \_run_id                  | str     | No       | metadata      | High          |
| \_run_type                | str     | No       | metadata      | High          |
| \_source_batch_id         | str     | Yes      | metadata      | Medium        |
| \_ingestion_ts            | str     | No       | metadata      | High          |
| \_index                   | int64   | No       | metadata      | High          |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping: No
- Поля в Silver, отсутствующие в Gold: 6
  - author_orcids, citations_received, is_oa, publication_class, publication_subclass, publication_type_unified
- Поля в Gold, отсутствующие в Silver: 3
  - \_source, issue, volume
- SSOT risk: medium when publication/provider-specific aliases coexist.

**DQ rules summary**

- Silver required_fields: 0; ranges: 0; columns filters: 0
- Gold required_fields: 0; ranges: 0; columns filters: 0
- Content hash policy: sha256(provider + canonical_json(record_normalized)); excludes technical fields \_ingestion_ts, \_run_id, \_run_type, _dq_\*.

### semanticscholar_publication

#### 1. Общая информация

- Provider: `semanticscholar`
- Entity: `publication`
- Pipeline name: `semanticscholar_publication`
- Primary keys: `['paper_id']`
- Loading strategy: API extract → Bronze append JSONL → Silver merge/upsert → Gold `scd2`
- Write mode: Silver=`merge`, Gold=`scd2`

#### 2. Bronze Layer

- Формат хранения: JSONL + zstd (append-only, flat_structure enabled by base config).
- Структура записи: raw provider payload; nested JSON partially flattened at transformer stage.
- Метаданные: batch-level metadata sidecar + pipeline run metadata added downstream (`_run_id`, `_run_type`, `_ingestion_ts`).
- Потенциальный schema drift: высокий для publication pipelines и ChEMBL nested objects; управляется soft validation в Silver.
- Ключевые риски Bronze: nested JSON, nullable-int coercion, provider-specific enum drift.

#### 3. Silver Schema

| Поле                       | Тип   | Nullable | Source field               | Notes |
| -------------------------- | ----- | -------- | -------------------------- | ----- |
| entity_id                  | str   | No       | entity_id                  |       |
| content_hash               | str   | No       | content_hash               |       |
| \_run_id                   | str   | No       | \_run_id                   |       |
| \_run_type                 | str   | No       | \_run_type                 |       |
| \_source_batch_id          | str   | Yes      | \_source_batch_id          |       |
| \_ingestion_ts             | str   | No       | \_ingestion_ts             |       |
| \_index                    | int64 | No       | \_index                    |       |
| \_dq_warn                  | bool  | No       | \_dq_warn                  |       |
| \_dq_error                 | bool  | No       | \_dq_error                 |       |
| pmid                       | str   | Yes      | pmid                       |       |
| doi                        | str   | Yes      | doi                        |       |
| pmc_id                     | str   | Yes      | pmc_id                     |       |
| title                      | str   | Yes      | title                      |       |
| abstract                   | str   | Yes      | abstract                   |       |
| authors                    | str   | Yes      | authors                    |       |
| affiliation_list           | str   | Yes      | affiliation_list           |       |
| author_orcids              | str   | Yes      | author_orcids              |       |
| author_keys                | str   | Yes      | author_keys                |       |
| journal                    | str   | Yes      | journal                    |       |
| publication_year           | Int64 | Yes      | publication_year           |       |
| publication_date           | str   | Yes      | publication_date           |       |
| publication_type           | str   | Yes      | publication_type           |       |
| publication_type_unified   | str   | Yes      | publication_type_unified   |       |
| publication_subclass       | str   | Yes      | publication_subclass       |       |
| publication_class          | str   | Yes      | publication_class          |       |
| language                   | str   | Yes      | language                   |       |
| page_first                 | str   | Yes      | page_first                 |       |
| page_last                  | str   | Yes      | page_last                  |       |
| citations_received         | Int64 | Yes      | citations_received         |       |
| citations_made             | Int64 | Yes      | citations_made             |       |
| is_oa                      | bool  | Yes      | is_oa                      |       |
| \_lookup_method            | str   | No       | \_lookup_method            |       |
| \_original_id              | str   | Yes      | \_original_id              |       |
| paper_id                   | str   | No       | paper_id                   |       |
| dblp_id                    | str   | Yes      | dblp_id                    |       |
| corpus_id                  | Int64 | Yes      | corpus_id                  |       |
| tldr                       | str   | Yes      | tldr                       |       |
| volume                     | str   | Yes      | volume                     |       |
| page_range                 | str   | Yes      | page_range                 |       |
| influential_citation_count | Int64 | Yes      | influential_citation_count |       |
| open_access_url            | str   | Yes      | open_access_url            |       |
| oa_status                  | str   | Yes      | oa_status                  |       |
| subject_fields             | str   | Yes      | subject_fields             |       |
| publication_types          | str   | Yes      | publication_types          |       |
| author_s2_ids              | str   | Yes      | author_s2_ids              |       |
| author_h_indices           | str   | Yes      | author_h_indices           |       |
| citation_contexts          | str   | Yes      | citation_contexts          |       |

Анализ: 47 columns, nullable=37, non-null=10; partition=[].

#### 4. Gold Schema (Контракт)

- Контрактная версия: class-based contract `SemanticScholarPublicationGoldSchema` (version field not explicit in class).
- Режим загрузки: `scd2`
- SCD config: {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}
- API стабильность: высокая при соблюдении Pandera strict и alias metadata policy.

| Поле                       | Тип     | Nullable | Semantic role | Breaking risk |
| -------------------------- | ------- | -------- | ------------- | ------------- |
| entity_id                  | str     | No       | metadata      | High          |
| content_hash               | str     | No       | metadata      | High          |
| paper_id                   | str     | No       | business      | High          |
| doi                        | str     | Yes      | business      | Medium        |
| pmid                       | str     | Yes      | business      | Medium        |
| corpus_id                  | float64 | Yes      | business      | Medium        |
| title                      | str     | Yes      | business      | Medium        |
| abstract                   | str     | Yes      | business      | Medium        |
| authors                    | str     | Yes      | business      | Medium        |
| tldr                       | str     | Yes      | business      | Medium        |
| publication_year           | float64 | Yes      | business      | Medium        |
| publication_date           | str     | Yes      | business      | Medium        |
| journal                    | str     | Yes      | business      | Medium        |
| volume                     | str     | Yes      | business      | Medium        |
| issue                      | str     | Yes      | business      | Medium        |
| page_range                 | str     | Yes      | business      | Medium        |
| page_first                 | str     | Yes      | business      | Medium        |
| page_last                  | str     | Yes      | business      | Medium        |
| citations_received         | float64 | Yes      | business      | Medium        |
| citations_made             | float64 | Yes      | business      | Medium        |
| influential_citation_count | float64 | Yes      | business      | Medium        |
| is_oa                      | bool    | Yes      | business      | Medium        |
| open_access_url            | str     | Yes      | business      | Medium        |
| oa_status                  | str     | Yes      | business      | Medium        |
| subject_fields             | str     | Yes      | business      | Medium        |
| publication_type           | str     | Yes      | business      | Medium        |
| publication_types          | str     | Yes      | business      | Medium        |
| citation_contexts          | str     | Yes      | business      | Medium        |
| affiliation_list           | str     | Yes      | business      | Medium        |
| author_keys                | str     | Yes      | business      | Medium        |
| author_s2_ids              | str     | Yes      | business      | Medium        |
| author_orcids              | str     | Yes      | business      | Medium        |
| author_h_indices           | str     | Yes      | business      | Medium        |
| dblp_id                    | str     | Yes      | business      | Medium        |
| \_source                   | str     | No       | metadata      | High          |
| \_lookup_method            | str     | No       | metadata      | High          |
| \_original_id              | str     | Yes      | metadata      | Medium        |
| \_dq_warn                  | bool    | No       | metadata      | High          |
| \_dq_error                 | bool    | No       | metadata      | High          |
| \_run_id                   | str     | No       | metadata      | High          |
| \_run_type                 | str     | No       | metadata      | High          |
| \_source_batch_id          | str     | Yes      | metadata      | Medium        |
| \_ingestion_ts             | str     | No       | metadata      | High          |
| \_index                    | int64   | No       | metadata      | High          |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping: No
- Поля в Silver, отсутствующие в Gold: 5
  - language, pmc_id, publication_class, publication_subclass, publication_type_unified
- Поля в Gold, отсутствующие в Silver: 2
  - \_source, issue
- SSOT risk: medium when publication/provider-specific aliases coexist.

**DQ rules summary**

- Silver required_fields: 0; ranges: 0; columns filters: 0
- Gold required_fields: 0; ranges: 0; columns filters: 0
- Content hash policy: sha256(provider + canonical_json(record_normalized)); excludes technical fields \_ingestion_ts, \_run_id, \_run_type, _dq_\*.

### uniprot_idmapping

#### 1. Общая информация

- Provider: `uniprot`
- Entity: `idmapping`
- Pipeline name: `uniprot_idmapping`
- Primary keys: `['target_id']`
- Loading strategy: API extract → Bronze append JSONL → Silver merge/upsert → Gold `scd2`
- Write mode: Silver=`merge`, Gold=`scd2`

#### 2. Bronze Layer

- Формат хранения: JSONL + zstd (append-only, flat_structure enabled by base config).
- Структура записи: raw provider payload; nested JSON partially flattened at transformer stage.
- Метаданные: batch-level metadata sidecar + pipeline run metadata added downstream (`_run_id`, `_run_type`, `_ingestion_ts`).
- Потенциальный schema drift: высокий для publication pipelines и ChEMBL nested objects; управляется soft validation в Silver.
- Ключевые риски Bronze: nested JSON, nullable-int coercion, provider-specific enum drift.

#### 3. Silver Schema

| Поле                | Тип     | Nullable | Source field        | Notes                         |
| ------------------- | ------- | -------- | ------------------- | ----------------------------- |
| entity_id           | str     | No       | entity_id           |                               |
| content_hash        | str     | No       | content_hash        |                               |
| \_run_id            | str     | No       | \_run_id            |                               |
| \_run_type          | str     | No       | \_run_type          |                               |
| \_source_batch_id   | str     | Yes      | \_source_batch_id   |                               |
| \_ingestion_ts      | str     | No       | \_ingestion_ts      |                               |
| \_index             | int64   | No       | \_index             |                               |
| \_dq_warn           | bool    | No       | \_dq_warn           |                               |
| \_dq_error          | bool    | No       | \_dq_error          |                               |
| target_id           | str     | No       | target_id           |                               |
| uniprot_accession   | str     | Yes      | uniprot_accession   |                               |
| mapping_status      | str     | No       | mapping_status      |                               |
| uniprot_entry_name  | str     | Yes      | uniprot_entry_name  |                               |
| organism_scientific | str     | Yes      | organism_scientific |                               |
| organism_common     | str     | Yes      | organism_common     |                               |
| taxonomy_id         | float64 | Yes      | taxonomy_id         | nullable-int coercion pattern |
| protein_name        | str     | Yes      | protein_name        |                               |
| gene_primary        | str     | Yes      | gene_primary        |                               |
| sequence_length     | float64 | Yes      | sequence_length     |                               |
| sequence_mass       | float64 | Yes      | sequence_mass       |                               |
| reviewed            | bool    | Yes      | reviewed            |                               |
| annotation_score    | float64 | Yes      | annotation_score    |                               |
| all_mappings        | str     | Yes      | all_mappings        |                               |

Анализ: 23 columns, nullable=13, non-null=10; partition=[].

#### 4. Gold Schema (Контракт)

- Контрактная версия: class-based contract `UniProtIDMappingGoldSchema` (version field not explicit in class).
- Режим загрузки: `scd2`
- SCD config: {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}
- API стабильность: высокая при соблюдении Pandera strict и alias metadata policy.

| Поле                | Тип     | Nullable | Semantic role | Breaking risk |
| ------------------- | ------- | -------- | ------------- | ------------- |
| entity_id           | str     | No       | metadata      | High          |
| content_hash        | str     | No       | metadata      | High          |
| target_id           | str     | No       | business      | High          |
| uniprot_accession   | str     | Yes      | business      | Medium        |
| mapping_status      | str     | No       | business      | High          |
| uniprot_entry_name  | str     | Yes      | business      | Medium        |
| organism_scientific | str     | Yes      | business      | Medium        |
| organism_common     | str     | Yes      | business      | Medium        |
| taxonomy_id         | float64 | Yes      | business      | Medium        |
| protein_name        | str     | Yes      | business      | Medium        |
| gene_primary        | str     | Yes      | business      | Medium        |
| sequence_length     | float64 | Yes      | business      | Medium        |
| sequence_mass       | float64 | Yes      | business      | Medium        |
| reviewed            | bool    | Yes      | business      | Medium        |
| annotation_score    | float64 | Yes      | business      | Medium        |
| all_mappings        | str     | Yes      | business      | Medium        |
| \_dq_warn           | bool    | No       | metadata      | High          |
| \_run_id            | str     | No       | metadata      | High          |
| \_run_type          | str     | No       | metadata      | High          |
| \_source_batch_id   | str     | Yes      | metadata      | Medium        |
| \_ingestion_ts      | str     | No       | metadata      | High          |
| \_index             | int64   | No       | metadata      | High          |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping: No
- Поля в Silver, отсутствующие в Gold: 1
  - \_dq_error
- Поля в Gold, отсутствующие в Silver: 0
- SSOT risk: medium when publication/provider-specific aliases coexist.

**DQ rules summary**

- Silver required_fields: 0; ranges: 0; columns filters: 0
- Gold required_fields: 0; ranges: 0; columns filters: 0
- Content hash policy: sha256(provider + canonical_json(record_normalized)); excludes technical fields \_ingestion_ts, \_run_id, \_run_type, _dq_\*.

### uniprot_protein

#### 1. Общая информация

- Provider: `uniprot`
- Entity: `protein`
- Pipeline name: `uniprot_protein`
- Primary keys: `['accession']`
- Loading strategy: API extract → Bronze append JSONL → Silver merge/upsert → Gold `scd2`
- Write mode: Silver=`merge`, Gold=`scd2`

#### 2. Bronze Layer

- Формат хранения: JSONL + zstd (append-only, flat_structure enabled by base config).
- Структура записи: raw provider payload; nested JSON partially flattened at transformer stage.
- Метаданные: batch-level metadata sidecar + pipeline run metadata added downstream (`_run_id`, `_run_type`, `_ingestion_ts`).
- Потенциальный schema drift: высокий для publication pipelines и ChEMBL nested objects; управляется soft validation в Silver.
- Ключевые риски Bronze: nested JSON, nullable-int coercion, provider-specific enum drift.

#### 3. Silver Schema

| Поле                          | Тип            | Nullable | Source field                  | Notes |
| ----------------------------- | -------------- | -------- | ----------------------------- | ----- |
| features_json                 | str            | Yes      | features_json                 |       |
| domains                       | str            | Yes      | domains                       |       |
| binding_sites                 | str            | Yes      | binding_sites                 |       |
| active_sites                  | str            | Yes      | active_sites                  |       |
| keywords                      | str            | Yes      | keywords                      |       |
| topology                      | str            | Yes      | topology                      |       |
| transmembrane                 | str            | Yes      | transmembrane                 |       |
| intramembrane                 | str            | Yes      | intramembrane                 |       |
| signal_peptide                | str            | Yes      | signal_peptide                |       |
| propeptide                    | str            | Yes      | propeptide                    |       |
| glycosylation                 | str            | Yes      | glycosylation                 |       |
| lipidation                    | str            | Yes      | lipidation                    |       |
| disulfide_bond                | str            | Yes      | disulfide_bond                |       |
| modified_residue              | str            | Yes      | modified_residue              |       |
| phosphorylation               | str            | Yes      | phosphorylation               |       |
| acetylation                   | str            | Yes      | acetylation                   |       |
| ubiquitination                | str            | Yes      | ubiquitination                |       |
| isoform_names                 | str            | Yes      | isoform_names                 |       |
| isoform_ids                   | str            | Yes      | isoform_ids                   |       |
| isoform_synonyms              | str            | Yes      | isoform_synonyms              |       |
| reactions                     | str            | Yes      | reactions                     |       |
| reaction_ec_numbers           | str            | Yes      | reaction_ec_numbers           |       |
| cross_reference_count         | Int64          | Yes      | cross_reference_count         |       |
| feature_count                 | Int64          | Yes      | feature_count                 |       |
| keyword_count                 | Int64          | Yes      | keyword_count                 |       |
| publication_count             | Int64          | Yes      | publication_count             |       |
| isoform_count                 | Int64          | Yes      | isoform_count                 |       |
| go_terms                      | str            | Yes      | go_terms                      |       |
| drugbank_ids                  | str            | Yes      | drugbank_ids                  |       |
| chembl_ids                    | str            | Yes      | chembl_ids                    |       |
| guidetopharmacology_ids       | str            | Yes      | guidetopharmacology_ids       |       |
| pdb_xrefs                     | str            | Yes      | pdb_xrefs                     |       |
| interpro_xrefs                | str            | Yes      | interpro_xrefs                |       |
| pfam_xrefs                    | str            | Yes      | pfam_xrefs                    |       |
| reactome_xrefs                | str            | Yes      | reactome_xrefs                |       |
| superkingdom                  | str            | Yes      | superkingdom                  |       |
| phylum                        | str            | Yes      | phylum                        |       |
| genus                         | str            | Yes      | genus                         |       |
| molecular_function            | str            | Yes      | molecular_function            |       |
| cellular_component            | str            | Yes      | cellular_component            |       |
| function_comment              | str            | Yes      | function_comment              |       |
| catalytic_activity            | str            | Yes      | catalytic_activity            |       |
| activity_regulation           | str            | Yes      | activity_regulation           |       |
| subunit                       | str            | Yes      | subunit                       |       |
| pathway                       | str            | Yes      | pathway                       |       |
| subcellular_location          | str            | Yes      | subcellular_location          |       |
| tissue_specificity            | str            | Yes      | tissue_specificity            |       |
| alternative_products          | str            | Yes      | alternative_products          |       |
| disease_involvement           | str            | Yes      | disease_involvement           |       |
| pharmaceutical_use            | str            | Yes      | pharmaceutical_use            |       |
| similarity_comment            | str            | Yes      | similarity_comment            |       |
| caution                       | str            | Yes      | caution                       |       |
| cofactors                     | str            | Yes      | cofactors                     |       |
| biophysicochemical_properties | str            | Yes      | biophysicochemical_properties |       |
| induction                     | str            | Yes      | induction                     |       |
| entity_id                     | str            | No       | entity_id                     |       |
| content_hash                  | str            | No       | content_hash                  |       |
| \_run_id                      | str            | No       | \_run_id                      |       |
| \_run_type                    | str            | No       | \_run_type                    |       |
| \_source_batch_id             | str            | Yes      | \_source_batch_id             |       |
| \_ingestion_ts                | str            | No       | \_ingestion_ts                |       |
| \_index                       | int64          | No       | \_index                       |       |
| \_dq_warn                     | bool           | No       | \_dq_warn                     |       |
| \_dq_error                    | bool           | No       | \_dq_error                    |       |
| accession                     | str            | No       | accession                     |       |
| entry_name                    | str            | No       | entry_name                    |       |
| entry_type                    | str            | Yes      | entry_type                    |       |
| secondary_accessions          | str            | Yes      | secondary_accessions          |       |
| protein_name                  | str            | Yes      | protein_name                  |       |
| protein_short_names           | str            | Yes      | protein_short_names           |       |
| protein_alternative_names     | str            | Yes      | protein_alternative_names     |       |
| protein_ec_numbers            | str            | Yes      | protein_ec_numbers            |       |
| flag                          | str            | Yes      | flag                          |       |
| gene_primary                  | str            | Yes      | gene_primary                  |       |
| gene_synonyms                 | str            | Yes      | gene_synonyms                 |       |
| gene_orf_names                | str            | Yes      | gene_orf_names                |       |
| organism_scientific           | str            | Yes      | organism_scientific           |       |
| organism_common               | str            | Yes      | organism_common               |       |
| taxonomy_id                   | Int64          | Yes      | taxonomy_id                   |       |
| lineage                       | str            | Yes      | lineage                       |       |
| sequence                      | str            | No       | sequence                      |       |
| sequence_length               | Int64          | No       | sequence_length               |       |
| sequence_mass                 | Int64          | Yes      | sequence_mass                 |       |
| sequence_checksum             | str            | Yes      | sequence_checksum             |       |
| sequence_modified             | datetime64[ns] | Yes      | sequence_modified             |       |
| entry_version                 | Int64          | Yes      | entry_version                 |       |
| entry_created                 | datetime64[ns] | Yes      | entry_created                 |       |
| entry_modified                | datetime64[ns] | Yes      | entry_modified                |       |
| reviewed                      | bool           | No       | reviewed                      |       |
| protein_existence             | str            | Yes      | protein_existence             |       |
| annotation_score              | Int64          | Yes      | annotation_score              |       |

Анализ: 91 columns, nullable=78, non-null=13; partition=['organism'].

#### 4. Gold Schema (Контракт)

- Контрактная версия: class-based contract `UniProtProteinGoldSchema` (version field not explicit in class).
- Режим загрузки: `scd2`
- SCD config: {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}
- API стабильность: высокая при соблюдении Pandera strict и alias metadata policy.

| Поле                 | Тип     | Nullable | Semantic role | Breaking risk |
| -------------------- | ------- | -------- | ------------- | ------------- |
| entity_id            | str     | No       | metadata      | High          |
| content_hash         | str     | No       | metadata      | High          |
| accession            | str     | No       | business      | High          |
| entry_name           | str     | Yes      | business      | Medium        |
| active_sites         | str     | Yes      | business      | Medium        |
| binding_sites        | str     | Yes      | business      | Medium        |
| domains              | str     | Yes      | business      | Medium        |
| features_json        | str     | Yes      | business      | Medium        |
| activity_regulation  | str     | Yes      | business      | Medium        |
| catalytic_activity   | str     | Yes      | business      | Medium        |
| disease_involvement  | str     | Yes      | business      | Medium        |
| function_comment     | str     | Yes      | business      | Medium        |
| pathway              | str     | Yes      | business      | Medium        |
| similarity_comment   | str     | Yes      | business      | Medium        |
| subcellular_location | str     | Yes      | business      | Medium        |
| tissue_specificity   | str     | Yes      | business      | Medium        |
| chembl_ids           | str     | Yes      | business      | Medium        |
| drugbank_ids         | str     | Yes      | business      | Medium        |
| go_terms             | str     | Yes      | business      | Medium        |
| interpro_xrefs       | str     | Yes      | business      | Medium        |
| pdb_xrefs            | str     | Yes      | business      | Medium        |
| pfam_xrefs           | str     | Yes      | business      | Medium        |
| reactome_xrefs       | str     | Yes      | business      | Medium        |
| gene_names           | str     | Yes      | business      | Medium        |
| organism_id          | float64 | Yes      | business      | Medium        |
| protein_name         | str     | Yes      | business      | Medium        |
| sequence_length      | float64 | Yes      | business      | Medium        |
| annotation_score     | float64 | Yes      | business      | Medium        |
| protein_existence    | str     | Yes      | business      | Medium        |
| reviewed             | bool    | Yes      | business      | Medium        |
| \_run_id             | str     | No       | metadata      | High          |
| \_run_type           | str     | No       | metadata      | High          |
| \_source_batch_id    | str     | Yes      | metadata      | Medium        |
| \_ingestion_ts       | str     | No       | metadata      | High          |
| \_index              | int64   | No       | metadata      | High          |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping: No
- Поля в Silver, отсутствующие в Gold: 58
  - \_dq_error, \_dq_warn, acetylation, alternative_products, biophysicochemical_properties, caution, cellular_component, cofactors, cross_reference_count, disulfide_bond, entry_created, entry_modified, entry_type, entry_version, feature_count, flag, gene_orf_names, gene_primary, gene_synonyms, genus ...
- Поля в Gold, отсутствующие в Silver: 2
  - gene_names, organism_id
- SSOT risk: medium when publication/provider-specific aliases coexist.

**DQ rules summary**

- Silver required_fields: 0; ranges: 0; columns filters: 0
- Gold required_fields: 0; ranges: 0; columns filters: 0
- Content hash policy: sha256(provider + canonical_json(record_normalized)); excludes technical fields \_ingestion_ts, \_run_id, \_run_type, _dq_\*.

## II. Архитектурные проблемы

| ID   | Pipeline                                          | Категория                | Проблема                                                                                                                | Риск   | Приоритет |
| ---- | ------------------------------------------------- | ------------------------ | ----------------------------------------------------------------------------------------------------------------------- | ------ | --------- |
| A-01 | \*                                                | Schema duplication       | Publication pipelines maintain duplicated semantic fields (`type`/`publication_type`, journal variants, mesh variants). | High   | P1        |
| A-02 | chembl_activity, chembl_molecule, uniprot_protein | Nullable ambiguity       | Several identifier-like fields use float for nullable ints (coercion).                                                  | Medium | P2        |
| A-03 | chembl_tissue, chembl_subcellular_fraction        | Domain drift             | No dedicated Pandera Silver schema in factory config.                                                                   | Medium | P2        |
| A-04 | publication pipelines                             | Content hash instability | High drift in nested provider payloads increases accidental hash variability when canonicalization incomplete.          | High   | P1        |
| A-05 | composite\_\*                                     | Hidden coupling          | Composite configs tightly coupled to upstream provider-specific field names.                                            | High   | P1        |
| A-06 | pubchem_compound                                  | Over-denormalization     | Large Silver→small Gold contraction indicates heavy denormalization and data loss risk.                                 | Medium | P2        |
| A-07 | multiple                                          | Inconsistent naming      | taxonomy_id vs target_taxonomy_id, document\_\* vs publication\_\* aliases.                                             | Medium | P2        |
| A-08 | multiple                                          | Weak primary key         | Some keys are synthetic `entity_id` with upstream dependency on composite components.                                   | Medium | P2        |

## III. Общесистемные проблемы

- Повторяющиеся поля: publication domain имеет многочисленные alias-пары (doi/publication_doi, year/publication_year и т.д.).
- Несогласованные типы между пайплайнами: идентификаторы в одних пайплайнах `str`, в других `float` (nullable-int workaround).
- Metadata унификация частично соблюдается: в Gold контрактах единые `_run_id/_run_type/_ingestion_ts`, но Bronze metadata хранится sidecar-форматом.
- OutputMetadata unification (ADR-029) реализована на уровне path conventions, но composite конфиги содержат ad-hoc ordering/pattern rules.
- Избыточная ширина таблиц: uniprot_protein (91 Silver columns), pubmed_publication (65), chembl_activity (65).
- provider-qualified дублирование выражено в composite publication/activity configs.
- SCD2 consistency: большинство Gold uses scd2, но есть append/overwrite exceptions (chembl_activity append, publication_term/similarity overwrite).
- Partition strategy несогласована: от domain-driven (assay_type, organism) до batch_date-only и no partition.

## IV. План улучшений

### 1. Немедленные улучшения (Low Risk)

- Нормализовать nullable-int поля в Silver на `Int64`/`string` и убрать float IDs. Impact: medium quality gain; Breaking: non-breaking при alias columns; ADR: no; Migration: dual-write + backfill.
- Унифицировать DQ required/range policy для publication pipelines. Impact: better comparability; Breaking: non-breaking; ADR: no; Migration: config-only rollout.
- Выровнять naming (`taxonomy_id` vs `target_taxonomy_id`, `document_*` vs `publication_*`). Impact: moderate; Breaking: potentially breaking for consumers; ADR: recommended; Migration: alias period + deprecation.

### 2. Среднесрочные улучшения (Refactoring Phase)

- Пересобрать Gold publication contracts в shared contract с provider extensions. Impact: high; Breaking: controlled schema evolution; ADR: yes; Migration: v2 contracts + compatibility views.
- Добавить Pandera Silver schema для tissue/subcellular_fraction. Impact: drift reduction; Breaking: non-breaking; ADR: no; Migration: activate soft mode then strict mode.
- Упростить rename chains, фиксируя canonical name на Bronze→Silver boundary. Impact: high clarity; Breaking: moderate; ADR: yes; Migration: field alias registry + phased removals.

### 3. Архитектурные изменения (Breaking Phase)

- Изменить структуру Silver publication tables: выделить normalized sub-entities (authors, mesh, citations). Impact: very high; Breaking: yes; ADR: mandatory; Migration: parallel normalized model + CDC backfill.
- Пересмотреть Content Hash baseline (strict canonicalizer + explicit include list per entity). Impact: dedup correctness; Breaking: yes (hash changes); ADR: mandatory; Migration: dual-hash window + recompute snapshots.
- Пересмотреть SCD2 keys для composite pipelines (entity-level business keys вместо provider-qualified composites). Impact: lineage robustness; Breaking: yes; ADR: mandatory; Migration: staged table replacement + reconciliation report.

## V. Target Schema Architecture (Целевая модель)

- Bronze: standardized envelope `{provider, entity, payload, extracted_at, source_cursor}` + optional raw blob, append-only JSONL.zst.
- Silver: единый contract template (business columns + technical metadata), обязательный Pandera для каждого pipeline, explicit drift policy per field-group.
- Gold: strict API contracts versioned (`vN`), SCD policy explicit per entity, backward-compatible aliases with deprecation window.
- Metadata policy: единый обязательный набор `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_dq_warn`, `_dq_error`, `content_hash`, `entity_id`.
- Key strategy: provider-agnostic business PK + deterministic entity_id derivation function registry.
- Типовая структура: narrow core table + optional satellite tables (multivalue arrays, provenance, enrichment).
