# Architecture Audit Report: Data Schema End-to-End

Date: 2026-02-18
Scope: pipeline schemas (Bronze/Silver/Gold), contracts, DQ and config strategy

## I. Карта схем пайплайна

### chembl_activity

**1. Общая информация**

- Provider: `chembl`
- Entity: `activity`
- Pipeline name: `chembl_activity`
- Primary keys: `['activity_id']`
- Loading strategy: `incremental_or_default`
- Write mode (Silver/Gold): `merge(default)` / `append`

**2. Bronze Layer**

- Формат хранения: JSONL + zstd, append-only (базовый contract в `_base.yaml`).
- Структура записи: provider-specific JSON payload + metadata envelope.
- Metadata поля: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, DQ sidecar/report.
- Потенциальный schema drift: nested JSON, optional arrays/objects, нестабильные nullable-int поля при flattening.

**3. Silver Schema**

- Полей в Silver: 62; nullable: 62.
- Partition strategy: `<default:none>`.
- DQ rules: 9 (`configs/quality/entities/chembl/activity.yaml`).
- Rename chain markers in filters: 0.
- Merge key correctness: все PK есть в Silver = True.

| Поле                      | Тип          | Nullable | Source field              | Notes |
| ------------------------- | ------------ | -------- | ------------------------- | ----- |
| `entity_id`               | `pa.string(` | `True`   | `entity_id`               |       |
| `content_hash`            | `pa.string(` | `True`   | `content_hash`            |       |
| `_run_id`                 | `pa.string(` | `True`   | `_run_id`                 |       |
| `_run_type`               | `pa.string(` | `True`   | `_run_type`               |       |
| `_source_batch_id`        | `pa.string(` | `True`   | `_source_batch_id`        |       |
| `_ingestion_ts`           | `pa.string(` | `True`   | `_ingestion_ts`           |       |
| `_index`                  | `pa.int64(`  | `True`   | `_index`                  |       |
| `action_type`             | `pa.string(` | `True`   | `action_type`             |       |
| `action_type_description` | `pa.string(` | `True`   | `action_type_description` |       |
| `action_type_parent_type` | `pa.string(` | `True`   | `action_type_parent_type` |       |
| `activity_comment`        | `pa.string(` | `True`   | `activity_comment`        |       |
| `activity_id`             | `pa.string(` | `True`   | `activity_id`             | PK    |
| `activity_properties`     | `pa.string(` | `True`   | `activity_properties`     |       |
| `assay_id`                | `pa.string(` | `True`   | `assay_id`                |       |
| `assay_description`       | `pa.string(` | `True`   | `assay_description`       |       |
| `assay_type`              | `pa.string(` | `True`   | `assay_type`              |       |
| `assay_variant_accession` | `pa.string(` | `True`   | `assay_variant_accession` |       |
| `assay_variant_mutation`  | `pa.string(` | `True`   | `assay_variant_mutation`  |       |
| ...                       | ...          | ...      | ...                       | ...   |

**4. Gold Schema (Контракт)**

- Контрактная валидация: strict Pandera DataFrameModel (ADR-018).
- Contract version: in-code schema + ADR governance.
- SCD2 / overwrite / append mode: `append`.
- Backward compatibility risk: MEDIUM.

| Поле                      | Тип             | Nullable | Semantic role | Breaking risk |
| ------------------------- | --------------- | -------- | ------------- | ------------- |
| `entity_id`               | `Series[str]`   | `False`  | metadata      | LOW           |
| `content_hash`            | `Series[str]`   | `False`  | metadata      | LOW           |
| `activity_id`             | `Series[str]`   | `False`  | key           | HIGH          |
| `molecule_id`             | `Series[str]`   | `False`  | business      | MEDIUM        |
| `target_id`               | `Series[str]`   | `True`   | business      | MEDIUM        |
| `assay_id`                | `Series[str]`   | `True`   | business      | MEDIUM        |
| `publication_id`          | `Series[str]`   | `True`   | business      | MEDIUM        |
| `record_id`               | `Series[float]` | `True`   | business      | MEDIUM        |
| `src_id`                  | `Series[float]` | `True`   | business      | MEDIUM        |
| `canonical_smiles`        | `Series[str]`   | `True`   | business      | MEDIUM        |
| `molecule_pref_name`      | `Series[str]`   | `True`   | business      | MEDIUM        |
| `parent_molecule_id`      | `Series[str]`   | `True`   | business      | MEDIUM        |
| `target_pref_name`        | `Series[str]`   | `True`   | business      | MEDIUM        |
| `target_organism`         | `Series[str]`   | `True`   | business      | MEDIUM        |
| `target_taxonomy_id`      | `Series[float]` | `True`   | business      | MEDIUM        |
| `assay_type`              | `Series[str]`   | `True`   | business      | MEDIUM        |
| `assay_description`       | `Series[str]`   | `True`   | business      | MEDIUM        |
| `assay_variant_accession` | `Series[str]`   | `True`   | business      | MEDIUM        |
| ...                       | ...             | ...      | ...           | ...           |

**5. Domain ↔ Schema соответствие**

- Silver↔Gold parity покрывается `verify_schema_parity.py` для данного пайплайна.
- Риски drift: Pydantic API models, domain entities и Silver flattening связаны не везде через единый declarative mapping.

### chembl_assay

**1. Общая информация**

- Provider: `chembl`
- Entity: `assay`
- Pipeline name: `chembl_assay`
- Primary keys: `['assay_id']`
- Loading strategy: `incremental_or_default`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

**2. Bronze Layer**

- Формат хранения: JSONL + zstd, append-only (базовый contract в `_base.yaml`).
- Структура записи: provider-specific JSON payload + metadata envelope.
- Metadata поля: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, DQ sidecar/report.
- Потенциальный schema drift: nested JSON, optional arrays/objects, нестабильные nullable-int поля при flattening.

**3. Silver Schema**

- Полей в Silver: 46; nullable: 46.
- Partition strategy: `['assay_type']`.
- DQ rules: 5 (`configs/quality/entities/chembl/assay.yaml`).
- Rename chain markers in filters: 0.
- Merge key correctness: все PK есть в Silver = True.

| Поле                         | Тип          | Nullable | Source field                 | Notes |
| ---------------------------- | ------------ | -------- | ---------------------------- | ----- |
| `entity_id`                  | `pa.string(` | `True`   | `entity_id`                  |       |
| `content_hash`               | `pa.string(` | `True`   | `content_hash`               |       |
| `_run_id`                    | `pa.string(` | `True`   | `_run_id`                    |       |
| `_run_type`                  | `pa.string(` | `True`   | `_run_type`                  |       |
| `_source_batch_id`           | `pa.string(` | `True`   | `_source_batch_id`           |       |
| `_ingestion_ts`              | `pa.string(` | `True`   | `_ingestion_ts`              |       |
| `_index`                     | `pa.int64(`  | `True`   | `_index`                     |       |
| `aidx`                       | `pa.string(` | `True`   | `aidx`                       |       |
| `assay_category`             | `pa.string(` | `True`   | `assay_category`             |       |
| `assay_cell_type`            | `pa.string(` | `True`   | `assay_cell_type`            |       |
| `assay_id`                   | `pa.string(` | `True`   | `assay_id`                   | PK    |
| `assay_classifications`      | `pa.string(` | `True`   | `assay_classifications`      |       |
| `assay_group`                | `pa.string(` | `True`   | `assay_group`                |       |
| `assay_organism`             | `pa.string(` | `True`   | `assay_organism`             |       |
| `assay_parameters`           | `pa.string(` | `True`   | `assay_parameters`           |       |
| `assay_pref_name`            | `pa.string(` | `True`   | `assay_pref_name`            |       |
| `assay_strain`               | `pa.string(` | `True`   | `assay_strain`               |       |
| `assay_subcellular_fraction` | `pa.string(` | `True`   | `assay_subcellular_fraction` |       |
| ...                          | ...          | ...      | ...                          | ...   |

**4. Gold Schema (Контракт)**

- Контрактная валидация: strict Pandera DataFrameModel (ADR-018).
- Contract version: in-code schema + ADR governance.
- SCD2 / overwrite / append mode: `scd2`.
- Backward compatibility risk: MEDIUM.

| Поле                     | Тип             | Nullable | Semantic role | Breaking risk |
| ------------------------ | --------------- | -------- | ------------- | ------------- |
| `entity_id`              | `Series[str]`   | `False`  | metadata      | LOW           |
| `content_hash`           | `Series[str]`   | `False`  | metadata      | LOW           |
| `assay_id`               | `Series[str]`   | `False`  | key           | HIGH          |
| `target_id`              | `Series[str]`   | `True`   | business      | MEDIUM        |
| `publication_id`         | `Series[str]`   | `True`   | business      | MEDIUM        |
| `cell_id`                | `Series[str]`   | `True`   | business      | MEDIUM        |
| `tissue_id`              | `Series[str]`   | `True`   | business      | MEDIUM        |
| `src_id`                 | `Series[float]` | `True`   | business      | MEDIUM        |
| `src_assay_id`           | `Series[str]`   | `True`   | business      | MEDIUM        |
| `aidx`                   | `Series[str]`   | `True`   | business      | MEDIUM        |
| `assay_type`             | `Series[str]`   | `True`   | business      | MEDIUM        |
| `assay_type_description` | `Series[str]`   | `True`   | business      | MEDIUM        |
| `assay_category`         | `Series[str]`   | `True`   | business      | MEDIUM        |
| `assay_test_type`        | `Series[str]`   | `True`   | business      | MEDIUM        |
| `assay_group`            | `Series[str]`   | `True`   | business      | MEDIUM        |
| `assay_organism`         | `Series[str]`   | `True`   | business      | MEDIUM        |
| `assay_taxonomy_id`      | `Series[float]` | `True`   | business      | MEDIUM        |
| `assay_cell_type`        | `Series[str]`   | `True`   | business      | MEDIUM        |
| ...                      | ...             | ...      | ...           | ...           |

**5. Domain ↔ Schema соответствие**

- Silver↔Gold parity покрывается `verify_schema_parity.py` для данного пайплайна.
- Риски drift: Pydantic API models, domain entities и Silver flattening связаны не везде через единый declarative mapping.

### chembl_assay_parameters

**1. Общая информация**

- Provider: `chembl`
- Entity: `assay_parameters`
- Pipeline name: `chembl_assay_parameters`
- Primary keys: `['assay_param_id']`
- Loading strategy: `incremental_or_default`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

**2. Bronze Layer**

- Формат хранения: JSONL + zstd, append-only (базовый contract в `_base.yaml`).
- Структура записи: provider-specific JSON payload + metadata envelope.
- Metadata поля: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, DQ sidecar/report.
- Потенциальный schema drift: nested JSON, optional arrays/objects, нестабильные nullable-int поля при flattening.

**3. Silver Schema**

- Полей в Silver: 22; nullable: 22.
- Partition strategy: `['type']`.
- DQ rules: 4 (`configs/quality/entities/chembl/assay_parameters.yaml`).
- Rename chain markers in filters: 0.
- Merge key correctness: все PK есть в Silver = True.

| Поле                  | Тип           | Nullable | Source field          | Notes |
| --------------------- | ------------- | -------- | --------------------- | ----- |
| `entity_id`           | `pa.string(`  | `True`   | `entity_id`           |       |
| `content_hash`        | `pa.string(`  | `True`   | `content_hash`        |       |
| `_run_id`             | `pa.string(`  | `True`   | `_run_id`             |       |
| `_run_type`           | `pa.string(`  | `True`   | `_run_type`           |       |
| `_source_batch_id`    | `pa.string(`  | `True`   | `_source_batch_id`    |       |
| `_ingestion_ts`       | `pa.string(`  | `True`   | `_ingestion_ts`       |       |
| `_index`              | `pa.int64(`   | `True`   | `_index`              |       |
| `assay_id`            | `pa.string(`  | `True`   | `assay_id`            |       |
| `assay_param_id`      | `pa.int64(`   | `True`   | `assay_param_id`      | PK    |
| `comments`            | `pa.string(`  | `True`   | `comments`            |       |
| `relation`            | `pa.string(`  | `True`   | `relation`            |       |
| `standard_relation`   | `pa.string(`  | `True`   | `standard_relation`   |       |
| `standard_text_value` | `pa.string(`  | `True`   | `standard_text_value` |       |
| `standard_type`       | `pa.string(`  | `True`   | `standard_type`       |       |
| `standard_units`      | `pa.string(`  | `True`   | `standard_units`      |       |
| `standard_value`      | `pa.float64(` | `True`   | `standard_value`      |       |
| `text_value`          | `pa.string(`  | `True`   | `text_value`          |       |
| `type`                | `pa.string(`  | `True`   | `type`                |       |
| ...                   | ...           | ...      | ...                   | ...   |

**4. Gold Schema (Контракт)**

- Контрактная валидация: strict Pandera DataFrameModel (ADR-018).
- Contract version: in-code schema + ADR governance.
- SCD2 / overwrite / append mode: `scd2`.
- Backward compatibility risk: MEDIUM.

| Поле                  | Тип             | Nullable | Semantic role | Breaking risk |
| --------------------- | --------------- | -------- | ------------- | ------------- |
| `entity_id`           | `Series[str]`   | `False`  | metadata      | LOW           |
| `content_hash`        | `Series[str]`   | `False`  | metadata      | LOW           |
| `assay_id`            | `Series[str]`   | `False`  | business      | MEDIUM        |
| `type`                | `Series[str]`   | `False`  | business      | MEDIUM        |
| `relation`            | `Series[str]`   | `True`   | business      | MEDIUM        |
| `value`               | `Series[float]` | `True`   | business      | MEDIUM        |
| `units`               | `Series[str]`   | `True`   | business      | MEDIUM        |
| `text_value`          | `Series[str]`   | `True`   | business      | MEDIUM        |
| `comments`            | `Series[str]`   | `True`   | business      | MEDIUM        |
| `standard_type`       | `Series[str]`   | `True`   | business      | MEDIUM        |
| `standard_relation`   | `Series[str]`   | `True`   | business      | MEDIUM        |
| `standard_value`      | `Series[float]` | `True`   | business      | MEDIUM        |
| `standard_units`      | `Series[str]`   | `True`   | business      | MEDIUM        |
| `standard_text_value` | `Series[str]`   | `True`   | business      | MEDIUM        |
| `run_id`              | `Series[str]`   | `False`  | metadata      | LOW           |
| `run_type`            | `Series[str]`   | `False`  | metadata      | LOW           |
| `source_batch_id`     | `Series[str]`   | `True`   | metadata      | LOW           |
| `ingestion_ts`        | `Series[str]`   | `False`  | metadata      | LOW           |
| ...                   | ...             | ...      | ...           | ...           |

**5. Domain ↔ Schema соответствие**

- Silver↔Gold parity покрывается `verify_schema_parity.py` для данного пайплайна.
- Риски drift: Pydantic API models, domain entities и Silver flattening связаны не везде через единый declarative mapping.

### chembl_cell_line

**1. Общая информация**

- Provider: `chembl`
- Entity: `cell_line`
- Pipeline name: `chembl_cell_line`
- Primary keys: `['cell_id']`
- Loading strategy: `incremental_or_default`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

**2. Bronze Layer**

- Формат хранения: JSONL + zstd, append-only (базовый contract в `_base.yaml`).
- Структура записи: provider-specific JSON payload + metadata envelope.
- Metadata поля: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, DQ sidecar/report.
- Потенциальный schema drift: nested JSON, optional arrays/objects, нестабильные nullable-int поля при flattening.

**3. Silver Schema**

- Полей в Silver: 17; nullable: 17.
- Partition strategy: `<default:none>`.
- DQ rules: 4 (`configs/quality/entities/chembl/cell_line.yaml`).
- Rename chain markers in filters: 0.
- Merge key correctness: все PK есть в Silver = True.

| Поле                   | Тип          | Nullable | Source field           | Notes |
| ---------------------- | ------------ | -------- | ---------------------- | ----- |
| `entity_id`            | `pa.string(` | `True`   | `entity_id`            |       |
| `content_hash`         | `pa.string(` | `True`   | `content_hash`         |       |
| `_run_id`              | `pa.string(` | `True`   | `_run_id`              |       |
| `_run_type`            | `pa.string(` | `True`   | `_run_type`            |       |
| `_source_batch_id`     | `pa.string(` | `True`   | `_source_batch_id`     |       |
| `_ingestion_ts`        | `pa.string(` | `True`   | `_ingestion_ts`        |       |
| `_index`               | `pa.int64(`  | `True`   | `_index`               |       |
| `cell_id`              | `pa.string(` | `True`   | `cell_id`              | PK    |
| `cell_description`     | `pa.string(` | `True`   | `cell_description`     |       |
| `cell_name`            | `pa.string(` | `True`   | `cell_name`            |       |
| `cell_source_organism` | `pa.string(` | `True`   | `cell_source_organism` |       |
| `cell_source_tissue`   | `pa.string(` | `True`   | `cell_source_tissue`   |       |
| `cellosaurus_id`       | `pa.string(` | `True`   | `cellosaurus_id`       |       |
| `cl_lincs_id`          | `pa.string(` | `True`   | `cl_lincs_id`          |       |
| `efo_id`               | `pa.string(` | `True`   | `efo_id`               |       |
| `_dq_error`            | `pa.bool_(`  | `True`   | `_dq_error`            |       |
| `_dq_warn`             | `pa.bool_(`  | `True`   | `_dq_warn`             |       |

**4. Gold Schema (Контракт)**

- Контрактная валидация: strict Pandera DataFrameModel (ADR-018).
- Contract version: in-code schema + ADR governance.
- SCD2 / overwrite / append mode: `scd2`.
- Backward compatibility risk: LOW.

| Поле                   | Тип           | Nullable | Semantic role | Breaking risk |
| ---------------------- | ------------- | -------- | ------------- | ------------- |
| `entity_id`            | `Series[str]` | `False`  | metadata      | LOW           |
| `content_hash`         | `Series[str]` | `False`  | metadata      | LOW           |
| `cell_id`              | `Series[str]` | `False`  | key           | HIGH          |
| `cell_name`            | `Series[str]` | `False`  | business      | MEDIUM        |
| `cell_description`     | `Series[str]` | `True`   | business      | MEDIUM        |
| `cell_source_tissue`   | `Series[str]` | `True`   | business      | MEDIUM        |
| `cell_source_organism` | `Series[str]` | `True`   | business      | MEDIUM        |
| `cellosaurus_id`       | `Series[str]` | `True`   | business      | MEDIUM        |
| `cl_lincs_id`          | `Series[str]` | `True`   | business      | MEDIUM        |
| `efo_id`               | `Series[str]` | `True`   | business      | MEDIUM        |
| `run_id`               | `Series[str]` | `False`  | metadata      | LOW           |
| `run_type`             | `Series[str]` | `False`  | metadata      | LOW           |
| `source_batch_id`      | `Series[str]` | `True`   | metadata      | LOW           |
| `ingestion_ts`         | `Series[str]` | `False`  | metadata      | LOW           |
| `index`                | `Series[int]` | `False`  | metadata      | LOW           |

**5. Domain ↔ Schema соответствие**

- Silver↔Gold parity покрывается `verify_schema_parity.py` для данного пайплайна.
- Риски drift: Pydantic API models, domain entities и Silver flattening связаны не везде через единый declarative mapping.

### chembl_compound_record

**1. Общая информация**

- Provider: `chembl`
- Entity: `compound_record`
- Pipeline name: `chembl_compound_record`
- Primary keys: `['record_id']`
- Loading strategy: `incremental_or_default`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

**2. Bronze Layer**

- Формат хранения: JSONL + zstd, append-only (базовый contract в `_base.yaml`).
- Структура записи: provider-specific JSON payload + metadata envelope.
- Metadata поля: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, DQ sidecar/report.
- Потенциальный schema drift: nested JSON, optional arrays/objects, нестабильные nullable-int поля при flattening.

**3. Silver Schema**

- Полей в Silver: 16; nullable: 16.
- Partition strategy: `<default:none>`.
- DQ rules: 5 (`configs/quality/entities/chembl/compound_record.yaml`).
- Rename chain markers in filters: 0.
- Merge key correctness: все PK есть в Silver = True.

| Поле               | Тип          | Nullable | Source field       | Notes |
| ------------------ | ------------ | -------- | ------------------ | ----- |
| `entity_id`        | `pa.string(` | `True`   | `entity_id`        |       |
| `content_hash`     | `pa.string(` | `True`   | `content_hash`     |       |
| `_run_id`          | `pa.string(` | `True`   | `_run_id`          |       |
| `_run_type`        | `pa.string(` | `True`   | `_run_type`        |       |
| `_source_batch_id` | `pa.string(` | `True`   | `_source_batch_id` |       |
| `_ingestion_ts`    | `pa.string(` | `True`   | `_ingestion_ts`    |       |
| `_index`           | `pa.int64(`  | `True`   | `_index`           |       |
| `compound_key`     | `pa.string(` | `True`   | `compound_key`     |       |
| `compound_name`    | `pa.string(` | `True`   | `compound_name`    |       |
| `publication_id`   | `pa.string(` | `True`   | `publication_id`   |       |
| `molecule_id`      | `pa.string(` | `True`   | `molecule_id`      |       |
| `record_id`        | `pa.int64(`  | `True`   | `record_id`        | PK    |
| `src_compound_id`  | `pa.string(` | `True`   | `src_compound_id`  |       |
| `src_id`           | `pa.int64(`  | `True`   | `src_id`           |       |
| `_dq_error`        | `pa.bool_(`  | `True`   | `_dq_error`        |       |
| `_dq_warn`         | `pa.bool_(`  | `True`   | `_dq_warn`         |       |

**4. Gold Schema (Контракт)**

- Контрактная валидация: strict Pandera DataFrameModel (ADR-018).
- Contract version: in-code schema + ADR governance.
- SCD2 / overwrite / append mode: `scd2`.
- Backward compatibility risk: MEDIUM.

| Поле              | Тип             | Nullable | Semantic role | Breaking risk |
| ----------------- | --------------- | -------- | ------------- | ------------- |
| `entity_id`       | `Series[str]`   | `False`  | metadata      | LOW           |
| `content_hash`    | `Series[str]`   | `False`  | metadata      | LOW           |
| `record_id`       | `Series[float]` | `False`  | key           | HIGH          |
| `molecule_id`     | `Series[str]`   | `False`  | business      | MEDIUM        |
| `publication_id`  | `Series[str]`   | `False`  | business      | MEDIUM        |
| `compound_key`    | `Series[str]`   | `True`   | business      | MEDIUM        |
| `compound_name`   | `Series[str]`   | `True`   | business      | MEDIUM        |
| `src_id`          | `Series[float]` | `False`  | business      | MEDIUM        |
| `src_compound_id` | `Series[str]`   | `True`   | business      | MEDIUM        |
| `run_id`          | `Series[str]`   | `False`  | metadata      | LOW           |
| `run_type`        | `Series[str]`   | `False`  | metadata      | LOW           |
| `source_batch_id` | `Series[str]`   | `True`   | metadata      | LOW           |
| `ingestion_ts`    | `Series[str]`   | `False`  | metadata      | LOW           |
| `index`           | `Series[int]`   | `False`  | metadata      | LOW           |

**5. Domain ↔ Schema соответствие**

- Silver↔Gold parity покрывается `verify_schema_parity.py` для данного пайплайна.
- Риски drift: Pydantic API models, domain entities и Silver flattening связаны не везде через единый declarative mapping.

### chembl_document

**1. Общая информация**

- Provider: `chembl`
- Entity: `publication`
- Pipeline name: `chembl_document`
- Primary keys: `['publication_id']`
- Loading strategy: `full_scan_only`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

**2. Bronze Layer**

- Формат хранения: JSONL + zstd, append-only (базовый contract в `_base.yaml`).
- Структура записи: provider-specific JSON payload + metadata envelope.
- Metadata поля: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, DQ sidecar/report.
- Потенциальный schema drift: nested JSON, optional arrays/objects, нестабильные nullable-int поля при flattening.

**3. Silver Schema**

- Полей в Silver: 35; nullable: 35.
- Partition strategy: `<default:none>`.
- DQ rules: 14 (`configs/quality/entities/chembl/publication.yaml`).
- Rename chain markers in filters: 0.
- Merge key correctness: все PK есть в Silver = True.

| Поле               | Тип          | Nullable | Source field       | Notes |
| ------------------ | ------------ | -------- | ------------------ | ----- |
| `entity_id`        | `pa.string(` | `True`   | `entity_id`        |       |
| `content_hash`     | `pa.string(` | `True`   | `content_hash`     |       |
| `_run_id`          | `pa.string(` | `True`   | `_run_id`          |       |
| `_run_type`        | `pa.string(` | `True`   | `_run_type`        |       |
| `_source_batch_id` | `pa.string(` | `True`   | `_source_batch_id` |       |
| `_source`          | `pa.string(` | `True`   | `_source`          |       |
| `_ingestion_ts`    | `pa.string(` | `True`   | `_ingestion_ts`    |       |
| `_index`           | `pa.int64(`  | `True`   | `_index`           |       |
| `_lookup_method`   | `pa.string(` | `True`   | `_lookup_method`   |       |
| `_original_id`     | `pa.string(` | `True`   | `_original_id`     |       |
| `authors`          | `pa.string(` | `True`   | `authors`          |       |
| `title`            | `pa.string(` | `True`   | `title`            |       |
| `journal`          | `pa.string(` | `True`   | `journal`          |       |
| `publication_year` | `pa.int64(`  | `True`   | `publication_year` |       |
| `volume`           | `pa.string(` | `True`   | `volume`           |       |
| `issue`            | `pa.string(` | `True`   | `issue`            |       |
| `page_first`       | `pa.string(` | `True`   | `page_first`       |       |
| `page_last`        | `pa.string(` | `True`   | `page_last`        |       |
| ...                | ...          | ...      | ...                | ...   |

**4. Gold Schema (Контракт)**

- Контрактная валидация: strict Pandera DataFrameModel (ADR-018).
- Contract version: in-code schema + ADR governance.
- SCD2 / overwrite / append mode: `scd2`.
- Backward compatibility risk: MEDIUM.

| Поле                 | Тип             | Nullable | Semantic role | Breaking risk |
| -------------------- | --------------- | -------- | ------------- | ------------- |
| `entity_id`          | `Series[str]`   | `False`  | metadata      | LOW           |
| `content_hash`       | `Series[str]`   | `False`  | metadata      | LOW           |
| `publication_id`     | `Series[str]`   | `False`  | key           | HIGH          |
| `pmid`               | `Series[str]`   | `True`   | business      | MEDIUM        |
| `doi`                | `Series[str]`   | `True`   | business      | MEDIUM        |
| `publication_doi`    | `Series[str]`   | `True`   | business      | MEDIUM        |
| `publication_pmid`   | `Series[str]`   | `True`   | business      | MEDIUM        |
| `publication_pmc_id` | `Series[str]`   | `True`   | business      | MEDIUM        |
| `title`              | `Series[str]`   | `True`   | business      | MEDIUM        |
| `authors`            | `Series[str]`   | `True`   | business      | MEDIUM        |
| `abstract`           | `Series[str]`   | `True`   | business      | MEDIUM        |
| `publication_type`   | `Series[str]`   | `True`   | business      | MEDIUM        |
| `journal`            | `Series[str]`   | `True`   | business      | MEDIUM        |
| `publication_year`   | `Series[float]` | `True`   | business      | MEDIUM        |
| `volume`             | `Series[str]`   | `True`   | business      | MEDIUM        |
| `issue`              | `Series[str]`   | `True`   | business      | MEDIUM        |
| `page_first`         | `Series[str]`   | `True`   | business      | MEDIUM        |
| `page_last`          | `Series[str]`   | `True`   | business      | MEDIUM        |
| ...                  | ...             | ...      | ...           | ...           |

**5. Domain ↔ Schema соответствие**

- Silver↔Gold parity покрывается `verify_schema_parity.py` для данного пайплайна.
- Риски drift: Pydantic API models, domain entities и Silver flattening связаны не везде через единый declarative mapping.

### chembl_document_similarity

**1. Общая информация**

- Provider: `chembl`
- Entity: `publication_similarity`
- Pipeline name: `chembl_document_similarity`
- Primary keys: `['sim_id']`
- Loading strategy: `full_scan_only`
- Write mode (Silver/Gold): `merge(default)` / `overwrite`

**2. Bronze Layer**

- Формат хранения: JSONL + zstd, append-only (базовый contract в `_base.yaml`).
- Структура записи: provider-specific JSON payload + metadata envelope.
- Metadata поля: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, DQ sidecar/report.
- Потенциальный schema drift: nested JSON, optional arrays/objects, нестабильные nullable-int поля при flattening.

**3. Silver Schema**

- Полей в Silver: 18; nullable: 18.
- Partition strategy: `[]`.
- DQ rules: 6 (`configs/quality/entities/chembl/publication_similarity.yaml`).
- Rename chain markers in filters: 0.
- Merge key correctness: все PK есть в Silver = True.

| Поле               | Тип           | Nullable | Source field       | Notes |
| ------------------ | ------------- | -------- | ------------------ | ----- |
| `entity_id`        | `pa.string(`  | `True`   | `entity_id`        |       |
| `content_hash`     | `pa.string(`  | `True`   | `content_hash`     |       |
| `_run_id`          | `pa.string(`  | `True`   | `_run_id`          |       |
| `_run_type`        | `pa.string(`  | `True`   | `_run_type`        |       |
| `_source_batch_id` | `pa.string(`  | `True`   | `_source_batch_id` |       |
| `_ingestion_ts`    | `pa.string(`  | `True`   | `_ingestion_ts`    |       |
| `_index`           | `pa.int64(`   | `True`   | `_index`           |       |
| `avg_tani`         | `pa.float64(` | `True`   | `avg_tani`         |       |
| `doc_1`            | `pa.int64(`   | `True`   | `doc_1`            |       |
| `doc_2`            | `pa.int64(`   | `True`   | `doc_2`            |       |
| `max_tani`         | `pa.float64(` | `True`   | `max_tani`         |       |
| `mol_tani`         | `pa.float64(` | `True`   | `mol_tani`         |       |
| `pubmed_id1`       | `pa.string(`  | `True`   | `pubmed_id1`       |       |
| `pubmed_id2`       | `pa.string(`  | `True`   | `pubmed_id2`       |       |
| `sim_id`           | `pa.int64(`   | `True`   | `sim_id`           | PK    |
| `tid_tani`         | `pa.float64(` | `True`   | `tid_tani`         |       |
| `_dq_error`        | `pa.bool_(`   | `True`   | `_dq_error`        |       |
| `_dq_warn`         | `pa.bool_(`   | `True`   | `_dq_warn`         |       |

**4. Gold Schema (Контракт)**

- Контрактная валидация: strict Pandera DataFrameModel (ADR-018).
- Contract version: in-code schema + ADR governance.
- SCD2 / overwrite / append mode: `overwrite`.
- Backward compatibility risk: MEDIUM.

| Поле              | Тип             | Nullable | Semantic role | Breaking risk |
| ----------------- | --------------- | -------- | ------------- | ------------- |
| `entity_id`       | `Series[str]`   | `False`  | metadata      | LOW           |
| `content_hash`    | `Series[str]`   | `False`  | metadata      | LOW           |
| `sim_id`          | `Series[float]` | `False`  | key           | HIGH          |
| `doc_1`           | `Series[float]` | `False`  | business      | MEDIUM        |
| `doc_2`           | `Series[float]` | `False`  | business      | MEDIUM        |
| `pubmed_id1`      | `Series[str]`   | `True`   | business      | MEDIUM        |
| `pubmed_id2`      | `Series[str]`   | `True`   | business      | MEDIUM        |
| `tid_tani`        | `Series[float]` | `True`   | business      | MEDIUM        |
| `mol_tani`        | `Series[float]` | `True`   | business      | MEDIUM        |
| `avg_tani`        | `Series[float]` | `True`   | business      | MEDIUM        |
| `max_tani`        | `Series[float]` | `True`   | business      | MEDIUM        |
| `run_id`          | `Series[str]`   | `False`  | metadata      | LOW           |
| `run_type`        | `Series[str]`   | `False`  | metadata      | LOW           |
| `source_batch_id` | `Series[str]`   | `True`   | metadata      | LOW           |
| `ingestion_ts`    | `Series[str]`   | `False`  | metadata      | LOW           |
| `index`           | `Series[int]`   | `False`  | metadata      | LOW           |

**5. Domain ↔ Schema соответствие**

- Silver↔Gold parity покрывается `verify_schema_parity.py` для данного пайплайна.
- Риски drift: Pydantic API models, domain entities и Silver flattening связаны не везде через единый declarative mapping.

### chembl_document_term

**1. Общая информация**

- Provider: `chembl`
- Entity: `publication_term`
- Pipeline name: `chembl_document_term`
- Primary keys: `['entity_id']`
- Loading strategy: `full_scan_only`
- Write mode (Silver/Gold): `merge(default)` / `overwrite`

**2. Bronze Layer**

- Формат хранения: JSONL + zstd, append-only (базовый contract в `_base.yaml`).
- Структура записи: provider-specific JSON payload + metadata envelope.
- Metadata поля: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, DQ sidecar/report.
- Потенциальный schema drift: nested JSON, optional arrays/objects, нестабильные nullable-int поля при flattening.

**3. Silver Schema**

- Полей в Silver: 14; nullable: 14.
- Partition strategy: `['term_type']`.
- DQ rules: 5 (`configs/quality/entities/chembl/publication_term.yaml`).
- Rename chain markers in filters: 0.
- Merge key correctness: все PK есть в Silver = True.

| Поле               | Тип          | Nullable | Source field       | Notes |
| ------------------ | ------------ | -------- | ------------------ | ----- |
| `entity_id`        | `pa.string(` | `True`   | `entity_id`        | PK    |
| `content_hash`     | `pa.string(` | `True`   | `content_hash`     |       |
| `_run_id`          | `pa.string(` | `True`   | `_run_id`          |       |
| `_run_type`        | `pa.string(` | `True`   | `_run_type`        |       |
| `_source_batch_id` | `pa.string(` | `True`   | `_source_batch_id` |       |
| `_ingestion_ts`    | `pa.string(` | `True`   | `_ingestion_ts`    |       |
| `_index`           | `pa.int64(`  | `True`   | `_index`           |       |
| `publication_id`   | `pa.string(` | `True`   | `publication_id`   |       |
| `mesh_id`          | `pa.string(` | `True`   | `mesh_id`          |       |
| `qualifier`        | `pa.string(` | `True`   | `qualifier`        |       |
| `term`             | `pa.string(` | `True`   | `term`             |       |
| `term_type`        | `pa.string(` | `True`   | `term_type`        |       |
| `_dq_error`        | `pa.bool_(`  | `True`   | `_dq_error`        |       |
| `_dq_warn`         | `pa.bool_(`  | `True`   | `_dq_warn`         |       |

**4. Gold Schema (Контракт)**

- Контрактная валидация: strict Pandera DataFrameModel (ADR-018).
- Contract version: in-code schema + ADR governance.
- SCD2 / overwrite / append mode: `overwrite`.
- Backward compatibility risk: LOW.

| Поле              | Тип           | Nullable | Semantic role | Breaking risk |
| ----------------- | ------------- | -------- | ------------- | ------------- |
| `entity_id`       | `Series[str]` | `False`  | metadata      | LOW           |
| `content_hash`    | `Series[str]` | `False`  | metadata      | LOW           |
| `publication_id`  | `Series[str]` | `False`  | business      | MEDIUM        |
| `term`            | `Series[str]` | `False`  | business      | MEDIUM        |
| `term_type`       | `Series[str]` | `False`  | business      | MEDIUM        |
| `mesh_id`         | `Series[str]` | `True`   | business      | MEDIUM        |
| `qualifier`       | `Series[str]` | `True`   | business      | MEDIUM        |
| `run_id`          | `Series[str]` | `False`  | metadata      | LOW           |
| `run_type`        | `Series[str]` | `False`  | metadata      | LOW           |
| `source_batch_id` | `Series[str]` | `True`   | metadata      | LOW           |
| `ingestion_ts`    | `Series[str]` | `False`  | metadata      | LOW           |
| `index`           | `Series[int]` | `False`  | metadata      | LOW           |

**5. Domain ↔ Schema соответствие**

- Silver↔Gold parity покрывается `verify_schema_parity.py` для данного пайплайна.
- Риски drift: Pydantic API models, domain entities и Silver flattening связаны не везде через единый declarative mapping.

### chembl_molecule

**1. Общая информация**

- Provider: `chembl`
- Entity: `molecule`
- Pipeline name: `chembl_molecule`
- Primary keys: `['molecule_id']`
- Loading strategy: `incremental_or_default`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

**2. Bronze Layer**

- Формат хранения: JSONL + zstd, append-only (базовый contract в `_base.yaml`).
- Структура записи: provider-specific JSON payload + metadata envelope.
- Metadata поля: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, DQ sidecar/report.
- Потенциальный schema drift: nested JSON, optional arrays/objects, нестабильные nullable-int поля при flattening.

**3. Silver Schema**

- Полей в Silver: 61; nullable: 61.
- Partition strategy: `['molecule_type']`.
- DQ rules: 10 (`configs/quality/entities/chembl/molecule.yaml`).
- Rename chain markers in filters: 0.
- Merge key correctness: все PK есть в Silver = True.

| Поле                         | Тип           | Nullable | Source field                 | Notes |
| ---------------------------- | ------------- | -------- | ---------------------------- | ----- |
| `entity_id`                  | `pa.string(`  | `True`   | `entity_id`                  |       |
| `content_hash`               | `pa.string(`  | `True`   | `content_hash`               |       |
| `_run_id`                    | `pa.string(`  | `True`   | `_run_id`                    |       |
| `_run_type`                  | `pa.string(`  | `True`   | `_run_type`                  |       |
| `_source_batch_id`           | `pa.string(`  | `True`   | `_source_batch_id`           |       |
| `_ingestion_ts`              | `pa.string(`  | `True`   | `_ingestion_ts`              |       |
| `_index`                     | `pa.int64(`   | `True`   | `_index`                     |       |
| `atc_classifications`        | `pa.string(`  | `True`   | `atc_classifications`        |       |
| `availability_type`          | `pa.float64(` | `True`   | `availability_type`          |       |
| `black_box_warning`          | `pa.int64(`   | `True`   | `black_box_warning`          |       |
| `canonical_smiles`           | `pa.string(`  | `True`   | `canonical_smiles`           |       |
| `chirality`                  | `pa.int64(`   | `True`   | `chirality`                  |       |
| `cross_references`           | `pa.string(`  | `True`   | `cross_references`           |       |
| `dosed_ingredient`           | `pa.int64(`   | `True`   | `dosed_ingredient`           |       |
| `first_approval`             | `pa.float64(` | `True`   | `first_approval`             |       |
| `first_in_class`             | `pa.int64(`   | `True`   | `first_in_class`             |       |
| `helm_notation`              | `pa.string(`  | `True`   | `helm_notation`              |       |
| `hierarchy_active_chembl_id` | `pa.string(`  | `True`   | `hierarchy_active_chembl_id` |       |
| ...                          | ...           | ...      | ...                          | ...   |

**4. Gold Schema (Контракт)**

- Контрактная валидация: strict Pandera DataFrameModel (ADR-018).
- Contract version: in-code schema + ADR governance.
- SCD2 / overwrite / append mode: `scd2`.
- Backward compatibility risk: MEDIUM.

| Поле                   | Тип             | Nullable | Semantic role | Breaking risk |
| ---------------------- | --------------- | -------- | ------------- | ------------- |
| `entity_id`            | `Series[str]`   | `False`  | metadata      | LOW           |
| `content_hash`         | `Series[str]`   | `False`  | metadata      | LOW           |
| `molecule_id`          | `Series[str]`   | `False`  | key           | HIGH          |
| `pref_name`            | `Series[str]`   | `True`   | business      | MEDIUM        |
| `molecule_type`        | `Series[str]`   | `True`   | business      | MEDIUM        |
| `structure_type`       | `Series[str]`   | `True`   | business      | MEDIUM        |
| `max_phase`            | `Series[float]` | `True`   | business      | MEDIUM        |
| `first_approval`       | `Series[float]` | `True`   | business      | MEDIUM        |
| `chirality`            | `Series[float]` | `True`   | business      | MEDIUM        |
| `dosed_ingredient`     | `Series[float]` | `True`   | business      | MEDIUM        |
| `availability_type`    | `Series[float]` | `True`   | business      | MEDIUM        |
| `usan_stem`            | `Series[str]`   | `True`   | business      | MEDIUM        |
| `usan_stem_definition` | `Series[str]`   | `True`   | business      | MEDIUM        |
| `usan_substem`         | `Series[str]`   | `True`   | business      | MEDIUM        |
| `usan_year`            | `Series[float]` | `True`   | business      | MEDIUM        |
| `helm_notation`        | `Series[str]`   | `True`   | business      | MEDIUM        |
| `molecule_species`     | `Series[str]`   | `True`   | business      | MEDIUM        |
| `oral`                 | `Series[bool]`  | `True`   | business      | MEDIUM        |
| ...                    | ...             | ...      | ...           | ...           |

**5. Domain ↔ Schema соответствие**

- Silver↔Gold parity покрывается `verify_schema_parity.py` для данного пайплайна.
- Риски drift: Pydantic API models, domain entities и Silver flattening связаны не везде через единый declarative mapping.

### chembl_protein_class

**1. Общая информация**

- Provider: `chembl`
- Entity: `protein_class`
- Pipeline name: `chembl_protein_class`
- Primary keys: `['protein_class_id']`
- Loading strategy: `incremental_or_default`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

**2. Bronze Layer**

- Формат хранения: JSONL + zstd, append-only (базовый contract в `_base.yaml`).
- Структура записи: provider-specific JSON payload + metadata envelope.
- Metadata поля: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, DQ sidecar/report.
- Потенциальный schema drift: nested JSON, optional arrays/objects, нестабильные nullable-int поля при flattening.

**3. Silver Schema**

- Полей в Silver: 19; nullable: 19.
- Partition strategy: `['class_level']`.
- DQ rules: 5 (`configs/quality/entities/chembl/protein_class.yaml`).
- Rename chain markers in filters: 0.
- Merge key correctness: все PK есть в Silver = True.

| Поле                 | Тип          | Nullable | Source field         | Notes |
| -------------------- | ------------ | -------- | -------------------- | ----- |
| `entity_id`          | `pa.string(` | `True`   | `entity_id`          |       |
| `content_hash`       | `pa.string(` | `True`   | `content_hash`       |       |
| `_run_id`            | `pa.string(` | `True`   | `_run_id`            |       |
| `_run_type`          | `pa.string(` | `True`   | `_run_type`          |       |
| `_source_batch_id`   | `pa.string(` | `True`   | `_source_batch_id`   |       |
| `_ingestion_ts`      | `pa.string(` | `True`   | `_ingestion_ts`      |       |
| `_index`             | `pa.int64(`  | `True`   | `_index`             |       |
| `class_level`        | `pa.int64(`  | `True`   | `class_level`        |       |
| `definition`         | `pa.string(` | `True`   | `definition`         |       |
| `downgraded`         | `pa.int64(`  | `True`   | `downgraded`         |       |
| `parent_id`          | `pa.int64(`  | `True`   | `parent_id`          |       |
| `pref_name`          | `pa.string(` | `True`   | `pref_name`          |       |
| `protein_class_desc` | `pa.string(` | `True`   | `protein_class_desc` |       |
| `protein_class_id`   | `pa.int64(`  | `True`   | `protein_class_id`   | PK    |
| `replaced_by`        | `pa.int64(`  | `True`   | `replaced_by`        |       |
| `short_name`         | `pa.string(` | `True`   | `short_name`         |       |
| `sort_order`         | `pa.int64(`  | `True`   | `sort_order`         |       |
| `_dq_error`          | `pa.bool_(`  | `True`   | `_dq_error`          |       |
| ...                  | ...          | ...      | ...                  | ...   |

**4. Gold Schema (Контракт)**

- Контрактная валидация: strict Pandera DataFrameModel (ADR-018).
- Contract version: in-code schema + ADR governance.
- SCD2 / overwrite / append mode: `scd2`.
- Backward compatibility risk: MEDIUM.

| Поле                 | Тип             | Nullable | Semantic role | Breaking risk |
| -------------------- | --------------- | -------- | ------------- | ------------- |
| `entity_id`          | `Series[str]`   | `False`  | metadata      | LOW           |
| `content_hash`       | `Series[str]`   | `False`  | metadata      | LOW           |
| `protein_class_id`   | `Series[float]` | `False`  | key           | HIGH          |
| `parent_id`          | `Series[float]` | `True`   | business      | MEDIUM        |
| `class_level`        | `Series[float]` | `True`   | business      | MEDIUM        |
| `pref_name`          | `Series[str]`   | `True`   | business      | MEDIUM        |
| `short_name`         | `Series[str]`   | `True`   | business      | MEDIUM        |
| `protein_class_desc` | `Series[str]`   | `True`   | business      | MEDIUM        |
| `definition`         | `Series[str]`   | `True`   | business      | MEDIUM        |
| `sort_order`         | `Series[float]` | `True`   | business      | MEDIUM        |
| `replaced_by`        | `Series[float]` | `True`   | business      | MEDIUM        |
| `downgraded`         | `Series[float]` | `True`   | business      | MEDIUM        |
| `run_id`             | `Series[str]`   | `False`  | metadata      | LOW           |
| `run_type`           | `Series[str]`   | `False`  | metadata      | LOW           |
| `source_batch_id`    | `Series[str]`   | `True`   | metadata      | LOW           |
| `ingestion_ts`       | `Series[str]`   | `False`  | metadata      | LOW           |
| `index`              | `Series[int]`   | `False`  | metadata      | LOW           |

**5. Domain ↔ Schema соответствие**

- Silver↔Gold parity покрывается `verify_schema_parity.py` для данного пайплайна.
- Риски drift: Pydantic API models, domain entities и Silver flattening связаны не везде через единый declarative mapping.

### chembl_target

**1. Общая информация**

- Provider: `chembl`
- Entity: `target`
- Pipeline name: `chembl_target`
- Primary keys: `['target_id']`
- Loading strategy: `incremental_or_default`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

**2. Bronze Layer**

- Формат хранения: JSONL + zstd, append-only (базовый contract в `_base.yaml`).
- Структура записи: provider-specific JSON payload + metadata envelope.
- Metadata поля: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, DQ sidecar/report.
- Потенциальный schema drift: nested JSON, optional arrays/objects, нестабильные nullable-int поля при flattening.

**3. Silver Schema**

- Полей в Silver: 27; nullable: 27.
- Partition strategy: `['target_type']`.
- DQ rules: 5 (`configs/quality/entities/chembl/target.yaml`).
- Rename chain markers in filters: 0.
- Merge key correctness: все PK есть в Silver = True.

| Поле                      | Тип          | Nullable | Source field              | Notes |
| ------------------------- | ------------ | -------- | ------------------------- | ----- |
| `entity_id`               | `pa.string(` | `True`   | `entity_id`               |       |
| `content_hash`            | `pa.string(` | `True`   | `content_hash`            |       |
| `_run_id`                 | `pa.string(` | `True`   | `_run_id`                 |       |
| `_run_type`               | `pa.string(` | `True`   | `_run_type`               |       |
| `_source_batch_id`        | `pa.string(` | `True`   | `_source_batch_id`        |       |
| `_ingestion_ts`           | `pa.string(` | `True`   | `_ingestion_ts`           |       |
| `_index`                  | `pa.int64(`  | `True`   | `_index`                  |       |
| `component_accessions`    | `pa.string(` | `True`   | `component_accessions`    |       |
| `component_descriptions`  | `pa.string(` | `True`   | `component_descriptions`  |       |
| `component_ids`           | `pa.string(` | `True`   | `component_ids`           |       |
| `component_relationships` | `pa.string(` | `True`   | `component_relationships` |       |
| `component_types`         | `pa.string(` | `True`   | `component_types`         |       |
| `cross_references`        | `pa.string(` | `True`   | `cross_references`        |       |
| `description`             | `pa.string(` | `True`   | `description`             |       |
| `downgraded`              | `pa.bool_(`  | `True`   | `downgraded`              |       |
| `organism`                | `pa.string(` | `True`   | `organism`                |       |
| `pipeline_stages`         | `pa.string(` | `True`   | `pipeline_stages`         |       |
| `pref_name`               | `pa.string(` | `True`   | `pref_name`               |       |
| ...                       | ...          | ...      | ...                       | ...   |

**4. Gold Schema (Контракт)**

- Контрактная валидация: strict Pandera DataFrameModel (ADR-018).
- Contract version: in-code schema + ADR governance.
- SCD2 / overwrite / append mode: `scd2`.
- Backward compatibility risk: LOW.

| Поле                        | Тип            | Nullable | Semantic role | Breaking risk |
| --------------------------- | -------------- | -------- | ------------- | ------------- |
| `entity_id`                 | `Series[str]`  | `False`  | metadata      | LOW           |
| `content_hash`              | `Series[str]`  | `False`  | metadata      | LOW           |
| `target_id`                 | `Series[str]`  | `False`  | key           | HIGH          |
| `pref_name`                 | `Series[str]`  | `True`   | business      | MEDIUM        |
| `target_type`               | `Series[str]`  | `True`   | business      | MEDIUM        |
| `organism`                  | `Series[str]`  | `True`   | business      | MEDIUM        |
| `species_group_flag`        | `Series[bool]` | `True`   | business      | MEDIUM        |
| `description`               | `Series[str]`  | `True`   | business      | MEDIUM        |
| `downgraded`                | `Series[bool]` | `True`   | business      | MEDIUM        |
| `pipeline_stages`           | `Series[str]`  | `True`   | business      | MEDIUM        |
| `target_components`         | `Series[str]`  | `True`   | business      | MEDIUM        |
| `cross_references`          | `Series[str]`  | `True`   | business      | MEDIUM        |
| `target_component_synonyms` | `Series[str]`  | `True`   | business      | MEDIUM        |
| `component_accessions`      | `Series[str]`  | `True`   | business      | MEDIUM        |
| `component_ids`             | `Series[str]`  | `True`   | business      | MEDIUM        |
| `component_types`           | `Series[str]`  | `True`   | business      | MEDIUM        |
| `component_relationships`   | `Series[str]`  | `True`   | business      | MEDIUM        |
| `run_id`                    | `Series[str]`  | `False`  | metadata      | LOW           |
| ...                         | ...            | ...      | ...           | ...           |

**5. Domain ↔ Schema соответствие**

- Silver↔Gold parity покрывается `verify_schema_parity.py` для данного пайплайна.
- Риски drift: Pydantic API models, domain entities и Silver flattening связаны не везде через единый declarative mapping.

### chembl_target_component

**1. Общая информация**

- Provider: `chembl`
- Entity: `target_component`
- Pipeline name: `chembl_target_component`
- Primary keys: `['component_id']`
- Loading strategy: `incremental_or_default`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

**2. Bronze Layer**

- Формат хранения: JSONL + zstd, append-only (базовый contract в `_base.yaml`).
- Структура записи: provider-specific JSON payload + metadata envelope.
- Metadata поля: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, DQ sidecar/report.
- Потенциальный schema drift: nested JSON, optional arrays/objects, нестабильные nullable-int поля при flattening.

**3. Silver Schema**

- Полей в Silver: 20; nullable: 20.
- Partition strategy: `['organism']`.
- DQ rules: 5 (`configs/quality/entities/chembl/target_component.yaml`).
- Rename chain markers in filters: 0.
- Merge key correctness: все PK есть в Silver = True.

| Поле                         | Тип          | Nullable | Source field                 | Notes |
| ---------------------------- | ------------ | -------- | ---------------------------- | ----- |
| `entity_id`                  | `pa.string(` | `True`   | `entity_id`                  |       |
| `content_hash`               | `pa.string(` | `True`   | `content_hash`               |       |
| `_run_id`                    | `pa.string(` | `True`   | `_run_id`                    |       |
| `_run_type`                  | `pa.string(` | `True`   | `_run_type`                  |       |
| `_source_batch_id`           | `pa.string(` | `True`   | `_source_batch_id`           |       |
| `_ingestion_ts`              | `pa.string(` | `True`   | `_ingestion_ts`              |       |
| `_index`                     | `pa.int64(`  | `True`   | `_index`                     |       |
| `accession`                  | `pa.string(` | `True`   | `accession`                  |       |
| `component_id`               | `pa.int64(`  | `True`   | `component_id`               | PK    |
| `component_type`             | `pa.string(` | `True`   | `component_type`             |       |
| `description`                | `pa.string(` | `True`   | `description`                |       |
| `organism`                   | `pa.string(` | `True`   | `organism`                   |       |
| `protein_classification_id`  | `pa.int64(`  | `True`   | `protein_classification_id`  |       |
| `protein_classification_ids` | `pa.string(` | `True`   | `protein_classification_ids` |       |
| `protein_classifications`    | `pa.string(` | `True`   | `protein_classifications`    |       |
| `target_component_synonyms`  | `pa.string(` | `True`   | `target_component_synonyms`  |       |
| `target_component_xrefs`     | `pa.string(` | `True`   | `target_component_xrefs`     |       |
| `taxonomy_id`                | `pa.int64(`  | `True`   | `taxonomy_id`                |       |
| ...                          | ...          | ...      | ...                          | ...   |

**4. Gold Schema (Контракт)**

- Контрактная валидация: strict Pandera DataFrameModel (ADR-018).
- Contract version: in-code schema + ADR governance.
- SCD2 / overwrite / append mode: `scd2`.
- Backward compatibility risk: LOW.

| Поле                         | Тип           | Nullable | Semantic role | Breaking risk |
| ---------------------------- | ------------- | -------- | ------------- | ------------- |
| `entity_id`                  | `Series[str]` | `False`  | metadata      | LOW           |
| `content_hash`               | `Series[str]` | `False`  | metadata      | LOW           |
| `accession`                  | `Series[str]` | `True`   | business      | MEDIUM        |
| `component_type`             | `Series[str]` | `True`   | business      | MEDIUM        |
| `description`                | `Series[str]` | `True`   | business      | MEDIUM        |
| `organism`                   | `Series[str]` | `True`   | business      | MEDIUM        |
| `target_component_synonyms`  | `Series[str]` | `True`   | business      | MEDIUM        |
| `target_component_xrefs`     | `Series[str]` | `True`   | business      | MEDIUM        |
| `protein_classifications`    | `Series[str]` | `True`   | business      | MEDIUM        |
| `protein_classification_ids` | `Series[str]` | `True`   | business      | MEDIUM        |
| `run_id`                     | `Series[str]` | `False`  | metadata      | LOW           |
| `run_type`                   | `Series[str]` | `False`  | metadata      | LOW           |
| `source_batch_id`            | `Series[str]` | `True`   | metadata      | LOW           |
| `ingestion_ts`               | `Series[str]` | `False`  | metadata      | LOW           |
| `index`                      | `Series[int]` | `False`  | metadata      | LOW           |

**5. Domain ↔ Schema соответствие**

- Silver↔Gold parity покрывается `verify_schema_parity.py` для данного пайплайна.
- Риски drift: Pydantic API models, domain entities и Silver flattening связаны не везде через единый declarative mapping.

### chembl_tissue

**1. Общая информация**

- Provider: `chembl`
- Entity: `tissue`
- Pipeline name: `chembl_tissue`
- Primary keys: `['tissue_id']`
- Loading strategy: `incremental_or_default`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

**2. Bronze Layer**

- Формат хранения: JSONL + zstd, append-only (базовый contract в `_base.yaml`).
- Структура записи: provider-specific JSON payload + metadata envelope.
- Metadata поля: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, DQ sidecar/report.
- Потенциальный schema drift: nested JSON, optional arrays/objects, нестабильные nullable-int поля при flattening.

**3. Silver Schema**

- Полей в Silver: 15; nullable: 15.
- Partition strategy: `<default:none>`.
- DQ rules: 6 (`configs/quality/entities/chembl/tissue.yaml`).
- Rename chain markers in filters: 0.
- Merge key correctness: все PK есть в Silver = True.

| Поле               | Тип          | Nullable | Source field       | Notes |
| ------------------ | ------------ | -------- | ------------------ | ----- |
| `entity_id`        | `pa.string(` | `True`   | `entity_id`        |       |
| `content_hash`     | `pa.string(` | `True`   | `content_hash`     |       |
| `_run_id`          | `pa.string(` | `True`   | `_run_id`          |       |
| `_run_type`        | `pa.string(` | `True`   | `_run_type`        |       |
| `_source_batch_id` | `pa.string(` | `True`   | `_source_batch_id` |       |
| `_ingestion_ts`    | `pa.string(` | `True`   | `_ingestion_ts`    |       |
| `_index`           | `pa.int64(`  | `True`   | `_index`           |       |
| `bto_id`           | `pa.string(` | `True`   | `bto_id`           |       |
| `caloha_id`        | `pa.string(` | `True`   | `caloha_id`        |       |
| `efo_id`           | `pa.string(` | `True`   | `efo_id`           |       |
| `pref_name`        | `pa.string(` | `True`   | `pref_name`        |       |
| `tissue_id`        | `pa.string(` | `True`   | `tissue_id`        | PK    |
| `uberon_id`        | `pa.string(` | `True`   | `uberon_id`        |       |
| `_dq_error`        | `pa.bool_(`  | `True`   | `_dq_error`        |       |
| `_dq_warn`         | `pa.bool_(`  | `True`   | `_dq_warn`         |       |

**4. Gold Schema (Контракт)**

- Контрактная валидация: strict Pandera DataFrameModel (ADR-018).
- Contract version: in-code schema + ADR governance.
- SCD2 / overwrite / append mode: `scd2`.
- Backward compatibility risk: LOW.

| Поле              | Тип           | Nullable | Semantic role | Breaking risk |
| ----------------- | ------------- | -------- | ------------- | ------------- |
| `run_id`          | `Series[str]` | `False`  | metadata      | LOW           |
| `run_type`        | `Series[str]` | `False`  | metadata      | LOW           |
| `source_batch_id` | `Series[str]` | `True`   | metadata      | LOW           |
| `ingestion_ts`    | `Series[str]` | `False`  | metadata      | LOW           |
| `index`           | `Series[int]` | `False`  | metadata      | LOW           |

**5. Domain ↔ Schema соответствие**

- Silver↔Gold parity покрывается `verify_schema_parity.py` для данного пайплайна.
- Риски drift: Pydantic API models, domain entities и Silver flattening связаны не везде через единый declarative mapping.

### chembl_subcellular_fraction

**1. Общая информация**

- Provider: `chembl`
- Entity: `subcellular_fraction`
- Pipeline name: `chembl_subcellular_fraction`
- Primary keys: `['entity_id']`
- Loading strategy: `full_scan_only`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

**2. Bronze Layer**

- Формат хранения: JSONL + zstd, append-only (базовый contract в `_base.yaml`).
- Структура записи: provider-specific JSON payload + metadata envelope.
- Metadata поля: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, DQ sidecar/report.
- Потенциальный schema drift: nested JSON, optional arrays/objects, нестабильные nullable-int поля при flattening.

**3. Silver Schema**

- Полей в Silver: 12; nullable: 12.
- Partition strategy: `<default:none>`.
- DQ rules: 4 (`configs/quality/entities/chembl/subcellular_fraction.yaml`).
- Rename chain markers in filters: 0.
- Merge key correctness: все PK есть в Silver = True.

| Поле                   | Тип          | Nullable | Source field           | Notes |
| ---------------------- | ------------ | -------- | ---------------------- | ----- |
| `entity_id`            | `pa.string(` | `True`   | `entity_id`            | PK    |
| `content_hash`         | `pa.string(` | `True`   | `content_hash`         |       |
| `_run_id`              | `pa.string(` | `True`   | `_run_id`              |       |
| `_run_type`            | `pa.string(` | `True`   | `_run_type`            |       |
| `_source_batch_id`     | `pa.string(` | `True`   | `_source_batch_id`     |       |
| `_ingestion_ts`        | `pa.string(` | `True`   | `_ingestion_ts`        |       |
| `_index`               | `pa.int64(`  | `True`   | `_index`               |       |
| `assay_count`          | `pa.int64(`  | `True`   | `assay_count`          |       |
| `example_assay_id`     | `pa.string(` | `True`   | `example_assay_id`     |       |
| `subcellular_fraction` | `pa.string(` | `True`   | `subcellular_fraction` |       |
| `_dq_error`            | `pa.bool_(`  | `True`   | `_dq_error`            |       |
| `_dq_warn`             | `pa.bool_(`  | `True`   | `_dq_warn`             |       |

**4. Gold Schema (Контракт)**

- Контрактная валидация: strict Pandera DataFrameModel (ADR-018).
- Contract version: in-code schema + ADR governance.
- SCD2 / overwrite / append mode: `scd2`.
- Backward compatibility risk: LOW.

| Поле              | Тип           | Nullable | Semantic role | Breaking risk |
| ----------------- | ------------- | -------- | ------------- | ------------- |
| `entity_id`       | `Series[str]` | `False`  | metadata      | LOW           |
| `content_hash`    | `Series[str]` | `False`  | metadata      | LOW           |
| `run_id`          | `Series[str]` | `False`  | metadata      | LOW           |
| `run_type`        | `Series[str]` | `False`  | metadata      | LOW           |
| `source_batch_id` | `Series[str]` | `True`   | metadata      | LOW           |
| `ingestion_ts`    | `Series[str]` | `False`  | metadata      | LOW           |
| `index`           | `Series[int]` | `False`  | metadata      | LOW           |

**5. Domain ↔ Schema соответствие**

- Silver↔Gold parity покрывается `verify_schema_parity.py` для данного пайплайна.
- Риски drift: Pydantic API models, domain entities и Silver flattening связаны не везде через единый declarative mapping.

### pubchem_compound

**1. Общая информация**

- Provider: `pubchem`
- Entity: `compound`
- Pipeline name: `pubchem_compound`
- Primary keys: `['molecule_id']`
- Loading strategy: `incremental_or_default`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

**2. Bronze Layer**

- Формат хранения: JSONL + zstd, append-only (базовый contract в `_base.yaml`).
- Структура записи: provider-specific JSON payload + metadata envelope.
- Metadata поля: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, DQ sidecar/report.
- Потенциальный schema drift: nested JSON, optional arrays/objects, нестабильные nullable-int поля при flattening.

**3. Silver Schema**

- Полей в Silver: 35; nullable: 35.
- Partition strategy: `['batch_date']`.
- DQ rules: 10 (`configs/quality/entities/pubchem/compound.yaml`).
- Rename chain markers in filters: 0.
- Merge key correctness: все PK есть в Silver = True.

| Поле                        | Тип           | Nullable | Source field                | Notes |
| --------------------------- | ------------- | -------- | --------------------------- | ----- |
| `entity_id`                 | `pa.string(`  | `True`   | `entity_id`                 |       |
| `content_hash`              | `pa.string(`  | `True`   | `content_hash`              |       |
| `_run_id`                   | `pa.string(`  | `True`   | `_run_id`                   |       |
| `_run_type`                 | `pa.string(`  | `True`   | `_run_type`                 |       |
| `_source_batch_id`          | `pa.string(`  | `True`   | `_source_batch_id`          |       |
| `_ingestion_ts`             | `pa.string(`  | `True`   | `_ingestion_ts`             |       |
| `_index`                    | `pa.int64(`   | `True`   | `_index`                    |       |
| `canonical_smiles`          | `pa.string(`  | `True`   | `canonical_smiles`          |       |
| `molecule_id`               | `pa.string(`  | `True`   | `molecule_id`               | PK    |
| `complexity`                | `pa.float64(` | `True`   | `complexity`                |       |
| `conformer_count_3d`        | `pa.float64(` | `True`   | `conformer_count_3d`        |       |
| `conformer_rmsd_3d`         | `pa.float64(` | `True`   | `conformer_rmsd_3d`         |       |
| `effective_rotor_count_3d`  | `pa.float64(` | `True`   | `effective_rotor_count_3d`  |       |
| `exact_mass`                | `pa.float64(` | `True`   | `exact_mass`                |       |
| `feature_acceptor_count_3d` | `pa.float64(` | `True`   | `feature_acceptor_count_3d` |       |
| `feature_anion_count_3d`    | `pa.float64(` | `True`   | `feature_anion_count_3d`    |       |
| `feature_cation_count_3d`   | `pa.float64(` | `True`   | `feature_cation_count_3d`   |       |
| `feature_count_3d`          | `pa.float64(` | `True`   | `feature_count_3d`          |       |
| ...                         | ...           | ...      | ...                         | ...   |

**4. Gold Schema (Контракт)**

- Контрактная валидация: strict Pandera DataFrameModel (ADR-018).
- Contract version: in-code schema + ADR governance.
- SCD2 / overwrite / append mode: `scd2`.
- Backward compatibility risk: MEDIUM.

| Поле                | Тип             | Nullable | Semantic role | Breaking risk |
| ------------------- | --------------- | -------- | ------------- | ------------- |
| `entity_id`         | `Series[str]`   | `False`  | metadata      | LOW           |
| `molecular_formula` | `Series[str]`   | `True`   | business      | MEDIUM        |
| `canonical_smiles`  | `Series[str]`   | `True`   | business      | MEDIUM        |
| `isomeric_smiles`   | `Series[str]`   | `True`   | business      | MEDIUM        |
| `inchi`             | `Series[str]`   | `True`   | business      | MEDIUM        |
| `inchi_key`         | `Series[str]`   | `True`   | business      | MEDIUM        |
| `logp`              | `Series[float]` | `True`   | business      | MEDIUM        |
| `iupac_name`        | `Series[str]`   | `True`   | business      | MEDIUM        |
| `content_hash`      | `Series[str]`   | `False`  | metadata      | LOW           |
| `run_id`            | `Series[str]`   | `False`  | metadata      | LOW           |
| `run_type`          | `Series[str]`   | `False`  | metadata      | LOW           |
| `source_batch_id`   | `Series[str]`   | `True`   | metadata      | LOW           |
| `ingestion_ts`      | `Series[str]`   | `False`  | metadata      | LOW           |
| `index`             | `Series[int]`   | `False`  | metadata      | LOW           |

**5. Domain ↔ Schema соответствие**

- Silver↔Gold parity покрывается `verify_schema_parity.py` для данного пайплайна.
- Риски drift: Pydantic API models, domain entities и Silver flattening связаны не везде через единый declarative mapping.

### pubmed_publication

**1. Общая информация**

- Provider: `pubmed`
- Entity: `publication`
- Pipeline name: `pubmed_publication`
- Primary keys: `['pmid']`
- Loading strategy: `full_scan_only`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

**2. Bronze Layer**

- Формат хранения: JSONL + zstd, append-only (базовый contract в `_base.yaml`).
- Структура записи: provider-specific JSON payload + metadata envelope.
- Metadata поля: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, DQ sidecar/report.
- Потенциальный schema drift: nested JSON, optional arrays/objects, нестабильные nullable-int поля при flattening.

**3. Silver Schema**

- Полей в Silver: 60; nullable: 60.
- Partition strategy: `<default:none>`.
- DQ rules: 13 (`configs/quality/entities/pubmed/publication.yaml`).
- Rename chain markers in filters: 0.
- Merge key correctness: все PK есть в Silver = True.

| Поле                        | Тип          | Nullable | Source field                | Notes |
| --------------------------- | ------------ | -------- | --------------------------- | ----- |
| `entity_id`                 | `pa.string(` | `True`   | `entity_id`                 |       |
| `content_hash`              | `pa.string(` | `True`   | `content_hash`              |       |
| `_run_id`                   | `pa.string(` | `True`   | `_run_id`                   |       |
| `_run_type`                 | `pa.string(` | `True`   | `_run_type`                 |       |
| `_source_batch_id`          | `pa.string(` | `True`   | `_source_batch_id`          |       |
| `_source`                   | `pa.string(` | `True`   | `_source`                   |       |
| `_ingestion_ts`             | `pa.string(` | `True`   | `_ingestion_ts`             |       |
| `_index`                    | `pa.int64(`  | `True`   | `_index`                    |       |
| `_lookup_method`            | `pa.string(` | `True`   | `_lookup_method`            |       |
| `_original_id`              | `pa.string(` | `True`   | `_original_id`              |       |
| `abstract`                  | `pa.string(` | `True`   | `abstract`                  |       |
| `affiliation_list`          | `pa.string(` | `True`   | `affiliation_list`          |       |
| `affiliation_structured`    | `pa.string(` | `True`   | `affiliation_structured`    |       |
| `author_count`              | `pa.int64(`  | `True`   | `author_count`              |       |
| `author_keys`               | `pa.string(` | `True`   | `author_keys`               |       |
| `authors`                   | `pa.string(` | `True`   | `authors`                   |       |
| `authors_with_affiliations` | `pa.string(` | `True`   | `authors_with_affiliations` |       |
| `chemical_count`            | `pa.int64(`  | `True`   | `chemical_count`            |       |
| ...                         | ...          | ...      | ...                         | ...   |

**4. Gold Schema (Контракт)**

- Контрактная валидация: strict Pandera DataFrameModel (ADR-018).
- Contract version: in-code schema + ADR governance.
- SCD2 / overwrite / append mode: `scd2`.
- Backward compatibility risk: MEDIUM.

| Поле                 | Тип           | Nullable | Semantic role | Breaking risk |
| -------------------- | ------------- | -------- | ------------- | ------------- |
| `entity_id`          | `Series[str]` | `False`  | metadata      | LOW           |
| `content_hash`       | `Series[str]` | `False`  | metadata      | LOW           |
| `pmid`               | `Series[str]` | `False`  | key           | HIGH          |
| `doi`                | `Series[str]` | `True`   | business      | MEDIUM        |
| `pmc_id`             | `Series[str]` | `True`   | business      | MEDIUM        |
| `title`              | `Series[str]` | `False`  | business      | MEDIUM        |
| `abstract`           | `Series[str]` | `True`   | business      | MEDIUM        |
| `journal`            | `Series[str]` | `True`   | business      | MEDIUM        |
| `journal_name_short` | `Series[str]` | `True`   | business      | MEDIUM        |
| `journal_iso_abbrev` | `Series[str]` | `True`   | business      | MEDIUM        |
| `issn`               | `Series[str]` | `True`   | business      | MEDIUM        |
| `nlm_unique_id`      | `Series[str]` | `True`   | business      | MEDIUM        |
| `volume`             | `Series[str]` | `True`   | business      | MEDIUM        |
| `issue`              | `Series[str]` | `True`   | business      | MEDIUM        |
| `page_range`         | `Series[str]` | `True`   | business      | MEDIUM        |
| `medline_pgn`        | `Series[str]` | `True`   | business      | MEDIUM        |
| `page_first`         | `Series[str]` | `True`   | business      | MEDIUM        |
| `page_last`          | `Series[str]` | `True`   | business      | MEDIUM        |
| ...                  | ...           | ...      | ...           | ...           |

**5. Domain ↔ Schema соответствие**

- Silver↔Gold parity покрывается `verify_schema_parity.py` для данного пайплайна.
- Риски drift: Pydantic API models, domain entities и Silver flattening связаны не везде через единый declarative mapping.

### crossref_publication

**1. Общая информация**

- Provider: `crossref`
- Entity: `publication`
- Pipeline name: `crossref_publication`
- Primary keys: `['doi']`
- Loading strategy: `full_scan_only`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

**2. Bronze Layer**

- Формат хранения: JSONL + zstd, append-only (базовый contract в `_base.yaml`).
- Структура записи: provider-specific JSON payload + metadata envelope.
- Metadata поля: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, DQ sidecar/report.
- Потенциальный schema drift: nested JSON, optional arrays/objects, нестабильные nullable-int поля при flattening.

**3. Silver Schema**

- Полей в Silver: 45; nullable: 45.
- Partition strategy: `<default:none>`.
- DQ rules: 11 (`configs/quality/entities/crossref/publication.yaml`).
- Rename chain markers in filters: 0.
- Merge key correctness: все PK есть в Silver = True.

| Поле                                   | Тип          | Nullable | Source field                           | Notes |
| -------------------------------------- | ------------ | -------- | -------------------------------------- | ----- |
| `entity_id`                            | `pa.string(` | `True`   | `entity_id`                            |       |
| `content_hash`                         | `pa.string(` | `True`   | `content_hash`                         |       |
| `_run_id`                              | `pa.string(` | `True`   | `_run_id`                              |       |
| `_run_type`                            | `pa.string(` | `True`   | `_run_type`                            |       |
| `_source_batch_id`                     | `pa.string(` | `True`   | `_source_batch_id`                     |       |
| `_source`                              | `pa.string(` | `True`   | `_source`                              |       |
| `_ingestion_ts`                        | `pa.string(` | `True`   | `_ingestion_ts`                        |       |
| `_index`                               | `pa.int64(`  | `True`   | `_index`                               |       |
| `_lookup_method`                       | `pa.string(` | `True`   | `_lookup_method`                       |       |
| `_original_id`                         | `pa.string(` | `True`   | `_original_id`                         |       |
| `abstract`                             | `pa.string(` | `True`   | `abstract`                             |       |
| `author_details`                       | `pa.string(` | `True`   | `author_details`                       |       |
| `author_keys`                          | `pa.string(` | `True`   | `author_keys`                          |       |
| `author_orcids`                        | `pa.string(` | `True`   | `author_orcids`                        |       |
| `authors`                              | `pa.string(` | `True`   | `authors`                              |       |
| `citations_made`                       | `pa.int64(`  | `True`   | `citations_made`                       |       |
| `content_domain_crossmark_restriction` | `pa.bool_(`  | `True`   | `content_domain_crossmark_restriction` |       |
| `content_domain_domains`               | `pa.string(` | `True`   | `content_domain_domains`               |       |
| ...                                    | ...          | ...      | ...                                    | ...   |

**4. Gold Schema (Контракт)**

- Контрактная валидация: strict Pandera DataFrameModel (ADR-018).
- Contract version: in-code schema + ADR governance.
- SCD2 / overwrite / append mode: `scd2`.
- Backward compatibility risk: MEDIUM.

| Поле                 | Тип             | Nullable | Semantic role | Breaking risk |
| -------------------- | --------------- | -------- | ------------- | ------------- |
| `entity_id`          | `Series[str]`   | `False`  | metadata      | LOW           |
| `content_hash`       | `Series[str]`   | `False`  | metadata      | LOW           |
| `doi`                | `Series[str]`   | `False`  | key           | HIGH          |
| `title`              | `Series[str]`   | `True`   | business      | MEDIUM        |
| `authors`            | `Series[str]`   | `True`   | business      | MEDIUM        |
| `journal`            | `Series[str]`   | `True`   | business      | MEDIUM        |
| `issn`               | `Series[str]`   | `True`   | business      | MEDIUM        |
| `issn_list`          | `Series[str]`   | `True`   | business      | MEDIUM        |
| `publisher`          | `Series[str]`   | `True`   | business      | MEDIUM        |
| `volume`             | `Series[str]`   | `True`   | business      | MEDIUM        |
| `issue`              | `Series[str]`   | `True`   | business      | MEDIUM        |
| `page_first`         | `Series[str]`   | `True`   | business      | MEDIUM        |
| `page_last`          | `Series[str]`   | `True`   | business      | MEDIUM        |
| `publication_date`   | `Series[str]`   | `True`   | business      | MEDIUM        |
| `published_print`    | `Series[str]`   | `True`   | business      | MEDIUM        |
| `published_online`   | `Series[str]`   | `True`   | business      | MEDIUM        |
| `citations_received` | `Series[float]` | `True`   | business      | MEDIUM        |
| `citations_made`     | `Series[float]` | `True`   | business      | MEDIUM        |
| ...                  | ...             | ...      | ...           | ...           |

**5. Domain ↔ Schema соответствие**

- Silver↔Gold parity покрывается `verify_schema_parity.py` для данного пайплайна.
- Риски drift: Pydantic API models, domain entities и Silver flattening связаны не везде через единый declarative mapping.

### openalex_publication

**1. Общая информация**

- Provider: `openalex`
- Entity: `publication`
- Pipeline name: `openalex_publication`
- Primary keys: `['openalex_id']`
- Loading strategy: `full_scan_only`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

**2. Bronze Layer**

- Формат хранения: JSONL + zstd, append-only (базовый contract в `_base.yaml`).
- Структура записи: provider-specific JSON payload + metadata envelope.
- Metadata поля: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, DQ sidecar/report.
- Потенциальный schema drift: nested JSON, optional arrays/objects, нестабильные nullable-int поля при flattening.

**3. Silver Schema**

- Полей в Silver: 49; nullable: 49.
- Partition strategy: `<default:none>`.
- DQ rules: 14 (`configs/quality/entities/openalex/publication.yaml`).
- Rename chain markers in filters: 0.
- Merge key correctness: все PK есть в Silver = True.

| Поле                  | Тип          | Nullable | Source field          | Notes |
| --------------------- | ------------ | -------- | --------------------- | ----- |
| `entity_id`           | `pa.string(` | `True`   | `entity_id`           |       |
| `content_hash`        | `pa.string(` | `True`   | `content_hash`        |       |
| `_run_id`             | `pa.string(` | `True`   | `_run_id`             |       |
| `_run_type`           | `pa.string(` | `True`   | `_run_type`           |       |
| `_source_batch_id`    | `pa.string(` | `True`   | `_source_batch_id`    |       |
| `_source`             | `pa.string(` | `True`   | `_source`             |       |
| `_ingestion_ts`       | `pa.string(` | `True`   | `_ingestion_ts`       |       |
| `_index`              | `pa.int64(`  | `True`   | `_index`              |       |
| `_lookup_method`      | `pa.string(` | `True`   | `_lookup_method`      |       |
| `_original_id`        | `pa.string(` | `True`   | `_original_id`        |       |
| `abstract`            | `pa.string(` | `True`   | `abstract`            |       |
| `affiliation_list`    | `pa.string(` | `True`   | `affiliation_list`    |       |
| `author_keys`         | `pa.string(` | `True`   | `author_keys`         |       |
| `author_openalex_ids` | `pa.string(` | `True`   | `author_openalex_ids` |       |
| `author_orcids`       | `pa.string(` | `True`   | `author_orcids`       |       |
| `authors`             | `pa.string(` | `True`   | `authors`             |       |
| `citations_made`      | `pa.int64(`  | `True`   | `citations_made`      |       |
| `citations_received`  | `pa.int64(`  | `True`   | `citations_received`  |       |
| ...                   | ...          | ...      | ...                   | ...   |

**4. Gold Schema (Контракт)**

- Контрактная валидация: strict Pandera DataFrameModel (ADR-018).
- Contract version: in-code schema + ADR governance.
- SCD2 / overwrite / append mode: `scd2`.
- Backward compatibility risk: MEDIUM.

| Поле               | Тип           | Nullable | Semantic role | Breaking risk |
| ------------------ | ------------- | -------- | ------------- | ------------- |
| `entity_id`        | `Series[str]` | `False`  | metadata      | LOW           |
| `content_hash`     | `Series[str]` | `False`  | metadata      | LOW           |
| `openalex_id`      | `Series[str]` | `False`  | key           | HIGH          |
| `doi`              | `Series[str]` | `True`   | business      | MEDIUM        |
| `pmid`             | `Series[str]` | `True`   | business      | MEDIUM        |
| `title`            | `Series[str]` | `True`   | business      | MEDIUM        |
| `abstract`         | `Series[str]` | `True`   | business      | MEDIUM        |
| `authors`          | `Series[str]` | `True`   | business      | MEDIUM        |
| `affiliation_list` | `Series[str]` | `True`   | business      | MEDIUM        |
| `subject_mesh`     | `Series[str]` | `True`   | business      | MEDIUM        |
| `subject_keywords` | `Series[str]` | `True`   | business      | MEDIUM        |
| `mag_id`           | `Series[str]` | `True`   | business      | MEDIUM        |
| `journal`          | `Series[str]` | `True`   | business      | MEDIUM        |
| `issn`             | `Series[str]` | `True`   | business      | MEDIUM        |
| `publisher`        | `Series[str]` | `True`   | business      | MEDIUM        |
| `volume`           | `Series[str]` | `True`   | business      | MEDIUM        |
| `issue`            | `Series[str]` | `True`   | business      | MEDIUM        |
| `page_first`       | `Series[str]` | `True`   | business      | MEDIUM        |
| ...                | ...           | ...      | ...           | ...           |

**5. Domain ↔ Schema соответствие**

- Silver↔Gold parity покрывается `verify_schema_parity.py` для данного пайплайна.
- Риски drift: Pydantic API models, domain entities и Silver flattening связаны не везде через единый declarative mapping.

### semanticscholar_publication

**1. Общая информация**

- Provider: `semanticscholar`
- Entity: `publication`
- Pipeline name: `semanticscholar_publication`
- Primary keys: `['paper_id']`
- Loading strategy: `full_scan_only`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

**2. Bronze Layer**

- Формат хранения: JSONL + zstd, append-only (базовый contract в `_base.yaml`).
- Структура записи: provider-specific JSON payload + metadata envelope.
- Metadata поля: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, DQ sidecar/report.
- Потенциальный schema drift: nested JSON, optional arrays/objects, нестабильные nullable-int поля при flattening.

**3. Silver Schema**

- Полей в Silver: 43; nullable: 43.
- Partition strategy: `<default:none>`.
- DQ rules: 13 (`configs/quality/entities/semanticscholar/publication.yaml`).
- Rename chain markers in filters: 0.
- Merge key correctness: все PK есть в Silver = True.

| Поле                | Тип          | Nullable | Source field        | Notes |
| ------------------- | ------------ | -------- | ------------------- | ----- |
| `entity_id`         | `pa.string(` | `True`   | `entity_id`         |       |
| `content_hash`      | `pa.string(` | `True`   | `content_hash`      |       |
| `_run_id`           | `pa.string(` | `True`   | `_run_id`           |       |
| `_run_type`         | `pa.string(` | `True`   | `_run_type`         |       |
| `_source_batch_id`  | `pa.string(` | `True`   | `_source_batch_id`  |       |
| `_source`           | `pa.string(` | `True`   | `_source`           |       |
| `_ingestion_ts`     | `pa.string(` | `True`   | `_ingestion_ts`     |       |
| `_index`            | `pa.int64(`  | `True`   | `_index`            |       |
| `_lookup_method`    | `pa.string(` | `True`   | `_lookup_method`    |       |
| `_original_id`      | `pa.string(` | `True`   | `_original_id`      |       |
| `abstract`          | `pa.string(` | `True`   | `abstract`          |       |
| `affiliation_list`  | `pa.string(` | `True`   | `affiliation_list`  |       |
| `author_h_indices`  | `pa.string(` | `True`   | `author_h_indices`  |       |
| `author_keys`       | `pa.string(` | `True`   | `author_keys`       |       |
| `author_orcids`     | `pa.string(` | `True`   | `author_orcids`     |       |
| `author_s2_ids`     | `pa.string(` | `True`   | `author_s2_ids`     |       |
| `citation_contexts` | `pa.string(` | `True`   | `citation_contexts` |       |
| `citations_made`    | `pa.int64(`  | `True`   | `citations_made`    |       |
| ...                 | ...          | ...      | ...                 | ...   |

**4. Gold Schema (Контракт)**

- Контрактная валидация: strict Pandera DataFrameModel (ADR-018).
- Contract version: in-code schema + ADR governance.
- SCD2 / overwrite / append mode: `scd2`.
- Backward compatibility risk: MEDIUM.

| Поле               | Тип             | Nullable | Semantic role | Breaking risk |
| ------------------ | --------------- | -------- | ------------- | ------------- |
| `entity_id`        | `Series[str]`   | `False`  | metadata      | LOW           |
| `content_hash`     | `Series[str]`   | `False`  | metadata      | LOW           |
| `paper_id`         | `Series[str]`   | `False`  | key           | HIGH          |
| `doi`              | `Series[str]`   | `True`   | business      | MEDIUM        |
| `pmid`             | `Series[str]`   | `True`   | business      | MEDIUM        |
| `corpus_id`        | `Series[float]` | `True`   | business      | MEDIUM        |
| `title`            | `Series[str]`   | `True`   | business      | MEDIUM        |
| `abstract`         | `Series[str]`   | `True`   | business      | MEDIUM        |
| `authors`          | `Series[str]`   | `True`   | business      | MEDIUM        |
| `tldr`             | `Series[str]`   | `True`   | business      | MEDIUM        |
| `publication_date` | `Series[str]`   | `True`   | business      | MEDIUM        |
| `journal`          | `Series[str]`   | `True`   | business      | MEDIUM        |
| `volume`           | `Series[str]`   | `True`   | business      | MEDIUM        |
| `issue`            | `Series[str]`   | `True`   | business      | MEDIUM        |
| `page_range`       | `Series[str]`   | `True`   | business      | MEDIUM        |
| `page_first`       | `Series[str]`   | `True`   | business      | MEDIUM        |
| `page_last`        | `Series[str]`   | `True`   | business      | MEDIUM        |
| `citations_made`   | `Series[float]` | `True`   | business      | MEDIUM        |
| ...                | ...             | ...      | ...           | ...           |

**5. Domain ↔ Schema соответствие**

- Silver↔Gold parity покрывается `verify_schema_parity.py` для данного пайплайна.
- Риски drift: Pydantic API models, domain entities и Silver flattening связаны не везде через единый declarative mapping.

### uniprot_protein

**1. Общая информация**

- Provider: `uniprot`
- Entity: `protein`
- Pipeline name: `uniprot_protein`
- Primary keys: `['accession']`
- Loading strategy: `incremental_or_default`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

**2. Bronze Layer**

- Формат хранения: JSONL + zstd, append-only (базовый contract в `_base.yaml`).
- Структура записи: provider-specific JSON payload + metadata envelope.
- Metadata поля: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, DQ sidecar/report.
- Потенциальный schema drift: nested JSON, optional arrays/objects, нестабильные nullable-int поля при flattening.

**3. Silver Schema**

- Полей в Silver: 59; nullable: 59.
- Partition strategy: `['organism']`.
- DQ rules: 18 (`configs/quality/entities/uniprot/protein.yaml`).
- Rename chain markers in filters: 0.
- Merge key correctness: все PK есть в Silver = True.

| Поле                  | Тип          | Nullable | Source field          | Notes |
| --------------------- | ------------ | -------- | --------------------- | ----- |
| `entity_id`           | `pa.string(` | `True`   | `entity_id`           |       |
| `content_hash`        | `pa.string(` | `True`   | `content_hash`        |       |
| `_run_id`             | `pa.string(` | `True`   | `_run_id`             |       |
| `_run_type`           | `pa.string(` | `True`   | `_run_type`           |       |
| `_source_batch_id`    | `pa.string(` | `True`   | `_source_batch_id`    |       |
| `_ingestion_ts`       | `pa.string(` | `True`   | `_ingestion_ts`       |       |
| `_index`              | `pa.int64(`  | `True`   | `_index`              |       |
| `accession`           | `pa.string(` | `True`   | `accession`           | PK    |
| `acetylation`         | `pa.string(` | `True`   | `acetylation`         |       |
| `active_sites`        | `pa.string(` | `True`   | `active_sites`        |       |
| `activity_regulation` | `pa.string(` | `True`   | `activity_regulation` |       |
| `annotation_score`    | `pa.int64(`  | `True`   | `annotation_score`    |       |
| `binding_sites`       | `pa.string(` | `True`   | `binding_sites`       |       |
| `catalytic_activity`  | `pa.string(` | `True`   | `catalytic_activity`  |       |
| `cellular_component`  | `pa.string(` | `True`   | `cellular_component`  |       |
| `chembl_ids`          | `pa.string(` | `True`   | `chembl_ids`          |       |
| `disease_involvement` | `pa.string(` | `True`   | `disease_involvement` |       |
| `disulfide_bond`      | `pa.string(` | `True`   | `disulfide_bond`      |       |
| ...                   | ...          | ...      | ...                   | ...   |

**4. Gold Schema (Контракт)**

- Контрактная валидация: strict Pandera DataFrameModel (ADR-018).
- Contract version: in-code schema + ADR governance.
- SCD2 / overwrite / append mode: `scd2`.
- Backward compatibility risk: MEDIUM.

| Поле                   | Тип           | Nullable | Semantic role | Breaking risk |
| ---------------------- | ------------- | -------- | ------------- | ------------- |
| `entity_id`            | `Series[str]` | `False`  | metadata      | LOW           |
| `content_hash`         | `Series[str]` | `False`  | metadata      | LOW           |
| `accession`            | `Series[str]` | `False`  | key           | HIGH          |
| `entry_name`           | `Series[str]` | `True`   | business      | MEDIUM        |
| `active_sites`         | `Series[str]` | `True`   | business      | MEDIUM        |
| `binding_sites`        | `Series[str]` | `True`   | business      | MEDIUM        |
| `domains`              | `Series[str]` | `True`   | business      | MEDIUM        |
| `features_json`        | `Series[str]` | `True`   | business      | MEDIUM        |
| `activity_regulation`  | `Series[str]` | `True`   | business      | MEDIUM        |
| `catalytic_activity`   | `Series[str]` | `True`   | business      | MEDIUM        |
| `disease_involvement`  | `Series[str]` | `True`   | business      | MEDIUM        |
| `function_comment`     | `Series[str]` | `True`   | business      | MEDIUM        |
| `pathway`              | `Series[str]` | `True`   | business      | MEDIUM        |
| `similarity_comment`   | `Series[str]` | `True`   | business      | MEDIUM        |
| `subcellular_location` | `Series[str]` | `True`   | business      | MEDIUM        |
| `tissue_specificity`   | `Series[str]` | `True`   | business      | MEDIUM        |
| `chembl_ids`           | `Series[str]` | `True`   | business      | MEDIUM        |
| `drugbank_ids`         | `Series[str]` | `True`   | business      | MEDIUM        |
| ...                    | ...           | ...      | ...           | ...           |

**5. Domain ↔ Schema соответствие**

- Silver↔Gold parity покрывается `verify_schema_parity.py` для данного пайплайна.
- Риски drift: Pydantic API models, domain entities и Silver flattening связаны не везде через единый declarative mapping.

### uniprot_idmapping

**1. Общая информация**

- Provider: `uniprot`
- Entity: `idmapping`
- Pipeline name: `uniprot_idmapping`
- Primary keys: `['target_id']`
- Loading strategy: `incremental_or_default`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

**2. Bronze Layer**

- Формат хранения: JSONL + zstd, append-only (базовый contract в `_base.yaml`).
- Структура записи: provider-specific JSON payload + metadata envelope.
- Metadata поля: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, DQ sidecar/report.
- Потенциальный schema drift: nested JSON, optional arrays/objects, нестабильные nullable-int поля при flattening.

**3. Silver Schema**

- Полей в Silver: 23; nullable: 23.
- Partition strategy: `[]`.
- DQ rules: 4 (`configs/quality/entities/uniprot/idmapping.yaml`).
- Rename chain markers in filters: 0.
- Merge key correctness: все PK есть в Silver = True.

| Поле                  | Тип          | Nullable | Source field          | Notes |
| --------------------- | ------------ | -------- | --------------------- | ----- |
| `entity_id`           | `pa.string(` | `True`   | `entity_id`           |       |
| `content_hash`        | `pa.string(` | `True`   | `content_hash`        |       |
| `_run_id`             | `pa.string(` | `True`   | `_run_id`             |       |
| `_run_type`           | `pa.string(` | `True`   | `_run_type`           |       |
| `_source_batch_id`    | `pa.string(` | `True`   | `_source_batch_id`    |       |
| `_ingestion_ts`       | `pa.string(` | `True`   | `_ingestion_ts`       |       |
| `_index`              | `pa.int64(`  | `True`   | `_index`              |       |
| `all_mappings`        | `pa.string(` | `True`   | `all_mappings`        |       |
| `annotation_score`    | `pa.int64(`  | `True`   | `annotation_score`    |       |
| `gene_primary`        | `pa.string(` | `True`   | `gene_primary`        |       |
| `mapping_status`      | `pa.string(` | `True`   | `mapping_status`      |       |
| `organism_common`     | `pa.string(` | `True`   | `organism_common`     |       |
| `organism_scientific` | `pa.string(` | `True`   | `organism_scientific` |       |
| `protein_name`        | `pa.string(` | `True`   | `protein_name`        |       |
| `reviewed`            | `pa.bool_(`  | `True`   | `reviewed`            |       |
| `sequence_length`     | `pa.int64(`  | `True`   | `sequence_length`     |       |
| `sequence_mass`       | `pa.int64(`  | `True`   | `sequence_mass`       |       |
| `target_id`           | `pa.string(` | `True`   | `target_id`           | PK    |
| ...                   | ...          | ...      | ...                   | ...   |

**4. Gold Schema (Контракт)**

- Контрактная валидация: strict Pandera DataFrameModel (ADR-018).
- Contract version: in-code schema + ADR governance.
- SCD2 / overwrite / append mode: `scd2`.
- Backward compatibility risk: MEDIUM.

| Поле                  | Тип             | Nullable | Semantic role | Breaking risk |
| --------------------- | --------------- | -------- | ------------- | ------------- |
| `entity_id`           | `Series[str]`   | `False`  | metadata      | LOW           |
| `content_hash`        | `Series[str]`   | `False`  | metadata      | LOW           |
| `target_id`           | `Series[str]`   | `False`  | key           | HIGH          |
| `uniprot_accession`   | `Series[str]`   | `True`   | business      | MEDIUM        |
| `mapping_status`      | `Series[str]`   | `False`  | business      | MEDIUM        |
| `uniprot_entry_name`  | `Series[str]`   | `True`   | business      | MEDIUM        |
| `organism_scientific` | `Series[str]`   | `True`   | business      | MEDIUM        |
| `organism_common`     | `Series[str]`   | `True`   | business      | MEDIUM        |
| `taxonomy_id`         | `Series[float]` | `True`   | business      | MEDIUM        |
| `protein_name`        | `Series[str]`   | `True`   | business      | MEDIUM        |
| `gene_primary`        | `Series[str]`   | `True`   | business      | MEDIUM        |
| `sequence_length`     | `Series[float]` | `True`   | business      | MEDIUM        |
| `sequence_mass`       | `Series[float]` | `True`   | business      | MEDIUM        |
| `reviewed`            | `Series[bool]`  | `True`   | business      | MEDIUM        |
| `all_mappings`        | `Series[str]`   | `True`   | business      | MEDIUM        |
| `dq_warn`             | `Series[bool]`  | `False`  | business      | MEDIUM        |
| `run_id`              | `Series[str]`   | `False`  | metadata      | LOW           |
| `run_type`            | `Series[str]`   | `False`  | metadata      | LOW           |
| ...                   | ...             | ...      | ...           | ...           |

**5. Domain ↔ Schema соответствие**

- Silver↔Gold parity покрывается `verify_schema_parity.py` для данного пайплайна.
- Риски drift: Pydantic API models, domain entities и Silver flattening связаны не везде через единый declarative mapping.

### composite_activity (composite)

**1. Общая информация**

- Composite pipeline агрегирует несколько Silver таблиц по join keys.
  **2. Bronze Layer**
- Bronze напрямую не используется; входом служат Silver таблицы source pipeline-ов.
  **3. Silver Schema**
- Silver схема формируется merge-конфигурацией и provider-qualified полями.
  **4. Gold Schema (Контракт)**
- Для composite publication/molecule есть Gold contracts; target/activity требуют harmonization-проверки.
  **5. Domain ↔ Schema соответствие**
- Наибольший риск drift из-за wide-schema merge + source priority rules.

### composite_assay (composite)

**1. Общая информация**

- Composite pipeline агрегирует несколько Silver таблиц по join keys.
  **2. Bronze Layer**
- Bronze напрямую не используется; входом служат Silver таблицы source pipeline-ов.
  **3. Silver Schema**
- Silver схема формируется merge-конфигурацией и provider-qualified полями.
  **4. Gold Schema (Контракт)**
- Для composite publication/molecule есть Gold contracts; target/activity требуют harmonization-проверки.
  **5. Domain ↔ Schema соответствие**
- Наибольший риск drift из-за wide-schema merge + source priority rules.

### composite_molecule (composite)

**1. Общая информация**

- Composite pipeline агрегирует несколько Silver таблиц по join keys.
  **2. Bronze Layer**
- Bronze напрямую не используется; входом служат Silver таблицы source pipeline-ов.
  **3. Silver Schema**
- Silver схема формируется merge-конфигурацией и provider-qualified полями.
  **4. Gold Schema (Контракт)**
- Для composite publication/molecule есть Gold contracts; target/activity требуют harmonization-проверки.
  **5. Domain ↔ Schema соответствие**
- Наибольший риск drift из-за wide-schema merge + source priority rules.

### composite_publication (composite)

**1. Общая информация**

- Composite pipeline агрегирует несколько Silver таблиц по join keys.
  **2. Bronze Layer**
- Bronze напрямую не используется; входом служат Silver таблицы source pipeline-ов.
  **3. Silver Schema**
- Silver схема формируется merge-конфигурацией и provider-qualified полями.
  **4. Gold Schema (Контракт)**
- Для composite publication/molecule есть Gold contracts; target/activity требуют harmonization-проверки.
  **5. Domain ↔ Schema соответствие**
- Наибольший риск drift из-за wide-schema merge + source priority rules.

### composite_target (composite)

**1. Общая информация**

- Composite pipeline агрегирует несколько Silver таблиц по join keys.
  **2. Bronze Layer**
- Bronze напрямую не используется; входом служат Silver таблицы source pipeline-ов.
  **3. Silver Schema**
- Silver схема формируется merge-конфигурацией и provider-qualified полями.
  **4. Gold Schema (Контракт)**
- Для composite publication/molecule есть Gold contracts; target/activity требуют harmonization-проверки.
  **5. Domain ↔ Schema соответствие**
- Наибольший риск drift из-за wide-schema merge + source priority rules.

## II. Архитектурные проблемы

| ID  | Pipeline                      | Категория             | Проблема                                          | Риск   | Приоритет |
| --- | ----------------------------- | --------------------- | ------------------------------------------------- | ------ | --------- |
| 1   | `chembl_activity`             | Type inconsistency    | Nullable int -> float coercion между Silver/Gold  | Medium | P2        |
| 2   | `chembl_assay`                | Type inconsistency    | Nullable int -> float coercion между Silver/Gold  | Medium | P2        |
| 3   | `chembl_assay_parameters`     | Type inconsistency    | Nullable int -> float coercion между Silver/Gold  | Medium | P2        |
| 4   | `chembl_compound_record`      | Type inconsistency    | Nullable int -> float coercion между Silver/Gold  | Medium | P2        |
| 5   | `chembl_document`             | Type inconsistency    | Nullable int -> float coercion между Silver/Gold  | Medium | P2        |
| 6   | `chembl_document_similarity`  | Type inconsistency    | Nullable int -> float coercion между Silver/Gold  | Medium | P2        |
| 7   | `chembl_document_similarity`  | Partition strategy    | Отсутствует partition key в Silver                | Low    | P3        |
| 8   | `chembl_molecule`             | Type inconsistency    | Nullable int -> float coercion между Silver/Gold  | Medium | P2        |
| 9   | `chembl_protein_class`        | Type inconsistency    | Nullable int -> float coercion между Silver/Gold  | Medium | P2        |
| 10  | `pubchem_compound`            | Type inconsistency    | Nullable int -> float coercion между Silver/Gold  | Medium | P2        |
| 11  | `pubmed_publication`          | Type inconsistency    | Nullable int -> float coercion между Silver/Gold  | Medium | P2        |
| 12  | `crossref_publication`        | Type inconsistency    | Nullable int -> float coercion между Silver/Gold  | Medium | P2        |
| 13  | `openalex_publication`        | Type inconsistency    | Nullable int -> float coercion между Silver/Gold  | Medium | P2        |
| 14  | `semanticscholar_publication` | Type inconsistency    | Nullable int -> float coercion между Silver/Gold  | Medium | P2        |
| 15  | `uniprot_protein`             | Type inconsistency    | Nullable int -> float coercion между Silver/Gold  | Medium | P2        |
| 16  | `uniprot_idmapping`           | Type inconsistency    | Nullable int -> float coercion между Silver/Gold  | Medium | P2        |
| 17  | `uniprot_idmapping`           | Partition strategy    | Отсутствует partition key в Silver                | Low    | P3        |
| 18  | `composite_activity`          | Overloaded Gold layer | Высокая ширина таблицы и provider-qualified дубли | Medium | P2        |
| 19  | `composite_assay`             | Overloaded Gold layer | Высокая ширина таблицы и provider-qualified дубли | Medium | P2        |
| 20  | `composite_molecule`          | Overloaded Gold layer | Высокая ширина таблицы и provider-qualified дубли | Medium | P2        |
| 21  | `composite_publication`       | Overloaded Gold layer | Высокая ширина таблицы и provider-qualified дубли | Medium | P2        |
| 22  | `composite_target`            | Overloaded Gold layer | Высокая ширина таблицы и provider-qualified дубли | Medium | P2        |

## III. Общесистемные проблемы

- Повторяемые поля и типы между публикационными pipeline-ами (`doi`, `pmid`, `title`, `authors`) представлены с разной nullable/typing политикой.
- Наблюдается несогласованность partition strategy и write mode между схожими сущностями.
- Output metadata унифицирована частично; composite добавляет provider-qualified отклонения от единого API слоя.
- Nullable-int coercion pattern системно создает риски потери семантики идентификаторов и сравнения ключей.
- SCD2 политика неоднородна по pipeline-ам и нуждается в унифицированном ADR-профиле.

## IV. План улучшений

### 1. Немедленные улучшения (Low Risk)

- Исправление типов: убрать неоднозначные nullable-int поля через явные nullable integer типы (Impact: Medium; Breaking: Non-breaking; ADR: No; Migration: schema patch + backfill validation).
- Унификация nullable policy для PK/FK и metadata (Impact: Medium; Breaking: Non-breaking; ADR: No; Migration: config + pandera constraints).
- Выравнивание DQ policy и naming conventions в filters/contracts (Impact: Low; Breaking: Non-breaking; ADR: No; Migration: staged config rollout).

### 2. Среднесрочные улучшения (Refactoring Phase)

- Пересборка Gold contracts для публикационных и composite pipeline-ов (Impact: High; Breaking: Potentially breaking; ADR: Yes; Migration: contract v2 + compatibility views).
- Унификация primary key strategy across providers (Impact: High; Breaking: Potentially breaking; ADR: Yes; Migration: dual-key period + consumer migration).
- Вынос повторяющихся полей в shared contracts и сокращение rename chains (Impact: Medium; Breaking: Mostly non-breaking; ADR: Yes; Migration: generated mapping + parity CI).

### 3. Архитектурные изменения (Breaking Phase)

- Изменение структуры Silver на canonical typed sub-structures для nested JSON (Impact: High; Breaking: Breaking; ADR: Mandatory; Migration: dual-write Silver v1/v2).
- Изменение Content Hash алгоритма на include-list + version tag (Impact: High; Breaking: Breaking; ADR: Mandatory; Migration: full rehash + SCD reset).
- Декомпозиция чрезмерно широких Gold/composite таблиц в core + extension entities (Impact: High; Breaking: Breaking; ADR: Mandatory; Migration: semantic adapters + phased cutover).

## V. Target Schema Architecture (Целевая модель)

- Стандартизированный Bronze: raw payload + normalized metadata envelope, единый набор технических полей.
- Унифицированный Silver contract: строгие типы, единая nullable policy, provider extension в отдельных колонках/таблицах.
- Строгий Gold API contract: versioned schema, explicit backward compatibility matrix, controlled breaking changes.
- Единая metadata policy: обязательные lineage + DQ поля во всех пайплайнах.
- Унифицированная key strategy: semantic PK + deterministic content_hash + explicit composite key fallback.
- Типовая структура: `identifiers`, `business_core`, `business_extensions`, `lineage_metadata`, `dq_flags`.

## Verification Log

- `python src/tools/verify_schema_parity.py --mode all`
- `rg -n "loading_strategy|partition_by|mode" configs/pipelines -g "*.yaml"`
- `rg -n "content_hash|HASH_EXCLUDE_FIELDS" src/bioetl`
- `find configs/quality/entities -maxdepth 3 -type f`
