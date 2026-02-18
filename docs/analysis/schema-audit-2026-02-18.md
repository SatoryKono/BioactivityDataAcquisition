# BioETL Schema Audit Report

Дата: 2026-02-18

I. Карта схем пайплайна

### 1. chembl_activity

1. Общая информация

- Provider: chembl
- Entity: activity
- Pipeline name / pipeline_id: chembl_activity
- Primary keys: ['activity_id']
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold append
- Write mode (Silver/Gold): MERGE(default)/append

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле                    | Тип                                                                                                                                                                                                                             |                                                                                                                                                                          Nullable | Source field            | Notes          |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | ----------------------- | -------------- |
| \_dq_error              | {'checks': [], 'coerce': False, 'description': 'Flag for data quality errors.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                          |                                                                                                                                                                           UNKNOWN | \_dq_error              | snapshot-based |
| \_dq_warn               | {'checks': [], 'coerce': False, 'description': 'Flag for data quality warnings.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                        |                                                                                                                                                                           UNKNOWN | \_dq_warn               | snapshot-based |
| \_index                 | {'checks': [{'name': 'greater_than_or_equal_to', 'type': 'ge'}], 'coerce': False, 'description': 'Sequential index of the record in the pipeline run.', 'dtype': 'int64', 'nullable': False, 'required': True, 'unique': False} |                                                                                                                                                                           UNKNOWN | \_index                 | snapshot-based |
| \_ingestion_ts          | {'checks': \[{'name': 'str_matches', 'regex': '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?([+-]\\d{2}:\\d{2}                                                                                                           | Z)?$'}\], 'coerce': False, 'description': 'Timestamp when the record was ingested (UTC, ISO 8601 format).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False} | UNKNOWN                 | \_ingestion_ts |
| \_run_id                | {'checks': [], 'coerce': False, 'description': 'Correlation ID for the pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                    |                                                                                                                                                                           UNKNOWN | \_run_id                | snapshot-based |
| \_run_type              | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'Type of pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                   |                                                                                                                                                                           UNKNOWN | \_run_type              | snapshot-based |
| \_source_batch_id       | {'checks': [], 'coerce': False, 'description': 'Batch context ID from the source.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                       |                                                                                                                                                                           UNKNOWN | \_source_batch_id       | snapshot-based |
| action_type             | {'checks': [], 'coerce': False, 'description': 'Action type classification.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                             |                                                                                                                                                                           UNKNOWN | action_type             | snapshot-based |
| action_type_description | {'checks': [], 'coerce': False, 'description': 'Action type description.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                                |                                                                                                                                                                           UNKNOWN | action_type_description | snapshot-based |
| action_type_parent_type | {'checks': [], 'coerce': False, 'description': 'Parent action type category.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                            |                                                                                                                                                                           UNKNOWN | action_type_parent_type | snapshot-based |
| activity_comment        | {'checks': [], 'coerce': False, 'description': 'Textual comment.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                                        |                                                                                                                                                                           UNKNOWN | activity_comment        | snapshot-based |
| activity_id             | {'checks': [], 'coerce': False, 'description': 'Primary key.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                                            |                                                                                                                                                                           UNKNOWN | activity_id             | snapshot-based |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/chembl/activity.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: MISSING/UNKNOWN.
- Merge key correctness: ['activity_id'].

4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: append (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле               | Тип                | Nullable | Semantic role | Breaking risk |
| ------------------ | ------------------ | -------: | ------------- | ------------- |
| entity_id          | string             |       No | business      | High          |
| content_hash       | string             |       No | business      | High          |
| activity_id        | string             |       No | business      | High          |
| molecule_id        | string             |       No | business      | High          |
| target_id          | ['string', 'null'] |      Yes | business      | Medium        |
| assay_id           | ['string', 'null'] |      Yes | business      | Medium        |
| publication_id     | ['string', 'null'] |      Yes | business      | Medium        |
| record_id          | ['number', 'null'] |      Yes | business      | Medium        |
| src_id             | ['number', 'null'] |      Yes | business      | Medium        |
| canonical_smiles   | ['string', 'null'] |      Yes | business      | Medium        |
| molecule_pref_name | ['string', 'null'] |      Yes | business      | Medium        |
| parent_molecule_id | ['string', 'null'] |      Yes | business      | Medium        |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/chembl/activity.yaml`
- `tests/contract/silver_schemas/snapshots/chembl_activity_schema.json`
- `docs/04-reference/contracts/gold/chembl_activity_v1.0.json`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

### 2. chembl_assay

1. Общая информация

- Provider: chembl
- Entity: assay
- Pipeline name / pipeline_id: chembl_assay
- Primary keys: ['assay_id']
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold scd2
- Write mode (Silver/Gold): MERGE(default)/scd2

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле                  | Тип                                                                                                                                                                                                                             |                                                                                                                                                                          Nullable | Source field          | Notes          |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | --------------------- | -------------- |
| \_dq_error            | {'checks': [], 'coerce': False, 'description': 'Flag for data quality errors.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                          |                                                                                                                                                                           UNKNOWN | \_dq_error            | snapshot-based |
| \_dq_warn             | {'checks': [], 'coerce': False, 'description': 'Flag for data quality warnings.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                        |                                                                                                                                                                           UNKNOWN | \_dq_warn             | snapshot-based |
| \_index               | {'checks': [{'name': 'greater_than_or_equal_to', 'type': 'ge'}], 'coerce': False, 'description': 'Sequential index of the record in the pipeline run.', 'dtype': 'int64', 'nullable': False, 'required': True, 'unique': False} |                                                                                                                                                                           UNKNOWN | \_index               | snapshot-based |
| \_ingestion_ts        | {'checks': \[{'name': 'str_matches', 'regex': '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?([+-]\\d{2}:\\d{2}                                                                                                           | Z)?$'}\], 'coerce': False, 'description': 'Timestamp when the record was ingested (UTC, ISO 8601 format).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False} | UNKNOWN               | \_ingestion_ts |
| \_run_id              | {'checks': [], 'coerce': False, 'description': 'Correlation ID for the pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                    |                                                                                                                                                                           UNKNOWN | \_run_id              | snapshot-based |
| \_run_type            | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'Type of pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                   |                                                                                                                                                                           UNKNOWN | \_run_type            | snapshot-based |
| \_source_batch_id     | {'checks': [], 'coerce': False, 'description': 'Batch context ID from the source.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                       |                                                                                                                                                                           UNKNOWN | \_source_batch_id     | snapshot-based |
| aidx                  | {'checks': [], 'coerce': False, 'description': 'Assay index.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                                            |                                                                                                                                                                           UNKNOWN | aidx                  | snapshot-based |
| assay_category        | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'Assay category.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                         |                                                                                                                                                                           UNKNOWN | assay_category        | snapshot-based |
| assay_cell_type       | {'checks': [], 'coerce': False, 'description': 'Cell type.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                                              |                                                                                                                                                                           UNKNOWN | assay_cell_type       | snapshot-based |
| assay_classifications | {'checks': [], 'coerce': False, 'description': 'JSON string of assay classifications.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                   |                                                                                                                                                                           UNKNOWN | assay_classifications | snapshot-based |
| assay_group           | {'checks': [], 'coerce': False, 'description': 'Assay group.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                                            |                                                                                                                                                                           UNKNOWN | assay_group           | snapshot-based |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/chembl/assay.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: ['assay_type'].
- Merge key correctness: ['assay_id'].

4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: scd2 (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле                   | Тип                | Nullable | Semantic role | Breaking risk |
| ---------------------- | ------------------ | -------: | ------------- | ------------- |
| entity_id              | string             |       No | business      | High          |
| content_hash           | string             |       No | business      | High          |
| assay_id               | string             |       No | business      | High          |
| target_id              | ['string', 'null'] |      Yes | business      | Medium        |
| publication_id         | ['string', 'null'] |      Yes | business      | Medium        |
| cell_id                | ['string', 'null'] |      Yes | business      | Medium        |
| tissue_id              | ['string', 'null'] |      Yes | business      | Medium        |
| src_id                 | ['number', 'null'] |      Yes | business      | Medium        |
| src_assay_id           | ['string', 'null'] |      Yes | business      | Medium        |
| aidx                   | ['string', 'null'] |      Yes | business      | Medium        |
| assay_type             | ['string', 'null'] |      Yes | business      | Medium        |
| assay_type_description | ['string', 'null'] |      Yes | business      | Medium        |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/chembl/assay.yaml`
- `tests/contract/silver_schemas/snapshots/chembl_assay_schema.json`
- `docs/04-reference/contracts/gold/chembl_assay_v1.0.json`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

### 3. chembl_assay_parameters

1. Общая информация

- Provider: chembl
- Entity: assay_parameters
- Pipeline name / pipeline_id: chembl_assay_parameters
- Primary keys: ['assay_param_id']
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold scd2
- Write mode (Silver/Gold): MERGE(default)/scd2

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле              | Тип                                                                                                                                                                                                                                        |                                                                                                                                                                          Nullable | Source field      | Notes          |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | ----------------- | -------------- |
| \_dq_error        | {'checks': [], 'coerce': False, 'description': 'Flag for data quality errors.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                                     |                                                                                                                                                                           UNKNOWN | \_dq_error        | snapshot-based |
| \_dq_warn         | {'checks': [], 'coerce': False, 'description': 'Flag for data quality warnings.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                                   |                                                                                                                                                                           UNKNOWN | \_dq_warn         | snapshot-based |
| \_index           | {'checks': [{'name': 'greater_than_or_equal_to', 'type': 'ge'}], 'coerce': False, 'description': 'Sequential index of the record in the pipeline run.', 'dtype': 'int64', 'nullable': False, 'required': True, 'unique': False}            |                                                                                                                                                                           UNKNOWN | \_index           | snapshot-based |
| \_ingestion_ts    | {'checks': \[{'name': 'str_matches', 'regex': '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?([+-]\\d{2}:\\d{2}                                                                                                                      | Z)?$'}\], 'coerce': False, 'description': 'Timestamp when the record was ingested (UTC, ISO 8601 format).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False} | UNKNOWN           | \_ingestion_ts |
| \_run_id          | {'checks': [], 'coerce': False, 'description': 'Correlation ID for the pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                               |                                                                                                                                                                           UNKNOWN | \_run_id          | snapshot-based |
| \_run_type        | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'Type of pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                              |                                                                                                                                                                           UNKNOWN | \_run_type        | snapshot-based |
| \_source_batch_id | {'checks': [], 'coerce': False, 'description': 'Batch context ID from the source.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                                  |                                                                                                                                                                           UNKNOWN | \_source_batch_id | snapshot-based |
| assay_id          | {'checks': [{'name': 'str_matches', 'regex': '^CHEMBL\\d+$'}], 'coerce': True, 'description': 'FK → Assay (ChEMBL ID format).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                      |                                                                                                                                                                           UNKNOWN | assay_id          | snapshot-based |
| assay_param_id    | {'checks': [{'name': 'greater_than_or_equal_to', 'type': 'ge'}], 'coerce': True, 'description': 'Parameter ID (PK, surrogate integer).', 'dtype': 'int64', 'nullable': False, 'required': True, 'unique': False}                           |                                                                                                                                                                           UNKNOWN | assay_param_id    | snapshot-based |
| comments          | {'checks': [], 'coerce': True, 'description': 'Additional comments.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                                                |                                                                                                                                                                           UNKNOWN | comments          | snapshot-based |
| content_hash      | {'checks': \[{'name': 'str_matches', 'regex': '^[a-f0-9]{64}$'}\], 'coerce': False, 'description': 'SHA256 hash of canonical record representation (64 hex chars).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False} |                                                                                                                                                                           UNKNOWN | content_hash      | snapshot-based |
| entity_id         | {'checks': [], 'coerce': False, 'description': 'Unique business identifier for the entity.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                         |                                                                                                                                                                           UNKNOWN | entity_id         | snapshot-based |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/chembl/assay_parameters.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: ['type'].
- Merge key correctness: ['assay_param_id'].

4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: scd2 (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле              | Тип                | Nullable | Semantic role | Breaking risk |
| ----------------- | ------------------ | -------: | ------------- | ------------- |
| entity_id         | string             |       No | business      | High          |
| content_hash      | string             |       No | business      | High          |
| assay_param_id    | number             |       No | business      | High          |
| assay_id          | string             |       No | business      | High          |
| type              | string             |       No | business      | High          |
| relation          | ['string', 'null'] |      Yes | business      | Medium        |
| value             | ['number', 'null'] |      Yes | business      | Medium        |
| units             | ['string', 'null'] |      Yes | business      | Medium        |
| text_value        | ['string', 'null'] |      Yes | business      | Medium        |
| comments          | ['string', 'null'] |      Yes | business      | Medium        |
| standard_type     | ['string', 'null'] |      Yes | business      | Medium        |
| standard_relation | ['string', 'null'] |      Yes | business      | Medium        |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/chembl/assay_parameters.yaml`
- `tests/contract/silver_schemas/snapshots/chembl_assay_parameters_schema.json`
- `docs/04-reference/contracts/gold/chembl_assay_parameters_v1.0.json`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

### 4. chembl_cell_line

1. Общая информация

- Provider: chembl
- Entity: cell_line
- Pipeline name / pipeline_id: chembl_cell_line
- Primary keys: ['cell_id']
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold scd2
- Write mode (Silver/Gold): MERGE(default)/scd2

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле                    | Тип                                                                                                                                                                                                                             |                                                                                                                                                                          Nullable | Source field            | Notes          |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | ----------------------- | -------------- |
| \_dq_error              | {'checks': [], 'coerce': False, 'description': 'Flag for data quality errors.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                          |                                                                                                                                                                           UNKNOWN | \_dq_error              | snapshot-based |
| \_dq_warn               | {'checks': [], 'coerce': False, 'description': 'Flag for data quality warnings.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                        |                                                                                                                                                                           UNKNOWN | \_dq_warn               | snapshot-based |
| \_index                 | {'checks': [{'name': 'greater_than_or_equal_to', 'type': 'ge'}], 'coerce': False, 'description': 'Sequential index of the record in the pipeline run.', 'dtype': 'int64', 'nullable': False, 'required': True, 'unique': False} |                                                                                                                                                                           UNKNOWN | \_index                 | snapshot-based |
| \_ingestion_ts          | {'checks': \[{'name': 'str_matches', 'regex': '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?([+-]\\d{2}:\\d{2}                                                                                                           | Z)?$'}\], 'coerce': False, 'description': 'Timestamp when the record was ingested (UTC, ISO 8601 format).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False} | UNKNOWN                 | \_ingestion_ts |
| \_run_id                | {'checks': [], 'coerce': False, 'description': 'Correlation ID for the pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                    |                                                                                                                                                                           UNKNOWN | \_run_id                | snapshot-based |
| \_run_type              | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'Type of pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                   |                                                                                                                                                                           UNKNOWN | \_run_type              | snapshot-based |
| \_source_batch_id       | {'checks': [], 'coerce': False, 'description': 'Batch context ID from the source.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                       |                                                                                                                                                                           UNKNOWN | \_source_batch_id       | snapshot-based |
| cell_description        | {'checks': [], 'coerce': False, 'description': 'Cell line description.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                                  |                                                                                                                                                                           UNKNOWN | cell_description        | snapshot-based |
| cell_id                 | {'checks': [{'name': 'str_matches', 'regex': '^CHEMBL\\d+$'}], 'coerce': False, 'description': 'ChEMBL ID for cell line (PK).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': True}                            |                                                                                                                                                                           UNKNOWN | cell_id                 | snapshot-based |
| cell_name               | {'checks': [], 'coerce': False, 'description': 'Cell line name (e.g., HeLa, MCF7).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                      |                                                                                                                                                                           UNKNOWN | cell_name               | snapshot-based |
| cell_source_organism    | {'checks': [], 'coerce': False, 'description': 'Source organism (e.g., Homo sapiens).', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                   |                                                                                                                                                                           UNKNOWN | cell_source_organism    | snapshot-based |
| cell_source_taxonomy_id | {'checks': [], 'coerce': False, 'description': 'NCBI Taxonomy ID for source organism (nullable int).', 'dtype': 'float64', 'nullable': True, 'required': False, 'unique': False}                                                |                                                                                                                                                                           UNKNOWN | cell_source_taxonomy_id | snapshot-based |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/chembl/cell_line.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: MISSING/UNKNOWN.
- Merge key correctness: ['cell_id'].

4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: scd2 (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле                    | Тип                | Nullable | Semantic role | Breaking risk |
| ----------------------- | ------------------ | -------: | ------------- | ------------- |
| entity_id               | string             |       No | business      | High          |
| content_hash            | string             |       No | business      | High          |
| cell_id                 | string             |       No | business      | High          |
| cell_name               | string             |       No | business      | High          |
| cell_description        | ['string', 'null'] |      Yes | business      | Medium        |
| cell_source_tissue      | ['string', 'null'] |      Yes | business      | Medium        |
| cell_source_organism    | ['string', 'null'] |      Yes | business      | Medium        |
| cell_source_taxonomy_id | ['number', 'null'] |      Yes | business      | Medium        |
| cellosaurus_id          | ['string', 'null'] |      Yes | business      | Medium        |
| cl_lincs_id             | ['string', 'null'] |      Yes | business      | Medium        |
| efo_id                  | ['string', 'null'] |      Yes | business      | Medium        |
| \_run_id                | string             |       No | metadata      | High          |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/chembl/cell_line.yaml`
- `tests/contract/silver_schemas/snapshots/chembl_cell_line_schema.json`
- `docs/04-reference/contracts/gold/chembl_cell_line_v1.0.json`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

### 5. chembl_compound_record

1. Общая информация

- Provider: chembl
- Entity: compound_record
- Pipeline name / pipeline_id: chembl_compound_record
- Primary keys: ['record_id']
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold scd2
- Write mode (Silver/Gold): MERGE(default)/scd2

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле              | Тип                                                                                                                                                                                                                                        |                                                                                                                                                                          Nullable | Source field      | Notes          |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | ----------------- | -------------- |
| \_dq_error        | {'checks': [], 'coerce': False, 'description': 'Flag for data quality errors.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                                     |                                                                                                                                                                           UNKNOWN | \_dq_error        | snapshot-based |
| \_dq_warn         | {'checks': [], 'coerce': False, 'description': 'Flag for data quality warnings.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                                   |                                                                                                                                                                           UNKNOWN | \_dq_warn         | snapshot-based |
| \_index           | {'checks': [{'name': 'greater_than_or_equal_to', 'type': 'ge'}], 'coerce': False, 'description': 'Sequential index of the record in the pipeline run.', 'dtype': 'int64', 'nullable': False, 'required': True, 'unique': False}            |                                                                                                                                                                           UNKNOWN | \_index           | snapshot-based |
| \_ingestion_ts    | {'checks': \[{'name': 'str_matches', 'regex': '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?([+-]\\d{2}:\\d{2}                                                                                                                      | Z)?$'}\], 'coerce': False, 'description': 'Timestamp when the record was ingested (UTC, ISO 8601 format).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False} | UNKNOWN           | \_ingestion_ts |
| \_run_id          | {'checks': [], 'coerce': False, 'description': 'Correlation ID for the pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                               |                                                                                                                                                                           UNKNOWN | \_run_id          | snapshot-based |
| \_run_type        | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'Type of pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                              |                                                                                                                                                                           UNKNOWN | \_run_type        | snapshot-based |
| \_source_batch_id | {'checks': [], 'coerce': False, 'description': 'Batch context ID from the source.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                                  |                                                                                                                                                                           UNKNOWN | \_source_batch_id | snapshot-based |
| compound_key      | {'checks': [], 'coerce': False, 'description': 'Original compound key in source document.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                          |                                                                                                                                                                           UNKNOWN | compound_key      | snapshot-based |
| compound_name     | {'checks': [], 'coerce': False, 'description': 'Original compound name in source document.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                         |                                                                                                                                                                           UNKNOWN | compound_name     | snapshot-based |
| content_hash      | {'checks': \[{'name': 'str_matches', 'regex': '^[a-f0-9]{64}$'}\], 'coerce': False, 'description': 'SHA256 hash of canonical record representation (64 hex chars).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False} |                                                                                                                                                                           UNKNOWN | content_hash      | snapshot-based |
| entity_id         | {'checks': [], 'coerce': False, 'description': 'Unique business identifier for the entity.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                         |                                                                                                                                                                           UNKNOWN | entity_id         | snapshot-based |
| molecule_id       | {'checks': [{'name': 'str_matches', 'regex': '^CHEMBL\\d+$'}], 'coerce': False, 'description': 'FK → Molecule.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                     |                                                                                                                                                                           UNKNOWN | molecule_id       | snapshot-based |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/chembl/compound_record.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: MISSING/UNKNOWN.
- Merge key correctness: ['record_id'].

4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: scd2 (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле              | Тип                | Nullable | Semantic role | Breaking risk |
| ----------------- | ------------------ | -------: | ------------- | ------------- |
| entity_id         | string             |       No | business      | High          |
| content_hash      | string             |       No | business      | High          |
| record_id         | number             |       No | business      | High          |
| molecule_id       | string             |       No | business      | High          |
| publication_id    | string             |       No | business      | High          |
| compound_key      | ['string', 'null'] |      Yes | business      | Medium        |
| compound_name     | ['string', 'null'] |      Yes | business      | Medium        |
| src_id            | number             |       No | business      | High          |
| src_compound_id   | ['string', 'null'] |      Yes | business      | Medium        |
| \_run_id          | string             |       No | metadata      | High          |
| \_run_type        | string             |       No | metadata      | High          |
| \_source_batch_id | ['string', 'null'] |      Yes | metadata      | Medium        |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/chembl/compound_record.yaml`
- `tests/contract/silver_schemas/snapshots/chembl_compound_record_schema.json`
- `docs/04-reference/contracts/gold/chembl_compound_record_v1.0.json`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

### 6. chembl_molecule

1. Общая информация

- Provider: chembl
- Entity: molecule
- Pipeline name / pipeline_id: chembl_molecule
- Primary keys: ['molecule_id']
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold scd2
- Write mode (Silver/Gold): MERGE(default)/scd2

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле                | Тип                                                                                                                                                                                                                             |                                                                                                                                                                          Nullable | Source field        | Notes          |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | ------------------- | -------------- |
| \_dq_error          | {'checks': [], 'coerce': False, 'description': 'Flag for data quality errors.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                          |                                                                                                                                                                           UNKNOWN | \_dq_error          | snapshot-based |
| \_dq_warn           | {'checks': [], 'coerce': False, 'description': 'Flag for data quality warnings.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                        |                                                                                                                                                                           UNKNOWN | \_dq_warn           | snapshot-based |
| \_index             | {'checks': [{'name': 'greater_than_or_equal_to', 'type': 'ge'}], 'coerce': False, 'description': 'Sequential index of the record in the pipeline run.', 'dtype': 'int64', 'nullable': False, 'required': True, 'unique': False} |                                                                                                                                                                           UNKNOWN | \_index             | snapshot-based |
| \_ingestion_ts      | {'checks': \[{'name': 'str_matches', 'regex': '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?([+-]\\d{2}:\\d{2}                                                                                                           | Z)?$'}\], 'coerce': False, 'description': 'Timestamp when the record was ingested (UTC, ISO 8601 format).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False} | UNKNOWN             | \_ingestion_ts |
| \_run_id            | {'checks': [], 'coerce': False, 'description': 'Correlation ID for the pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                    |                                                                                                                                                                           UNKNOWN | \_run_id            | snapshot-based |
| \_run_type          | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'Type of pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                   |                                                                                                                                                                           UNKNOWN | \_run_type          | snapshot-based |
| \_source_batch_id   | {'checks': [], 'coerce': False, 'description': 'Batch context ID from the source.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                       |                                                                                                                                                                           UNKNOWN | \_source_batch_id   | snapshot-based |
| aromatic_ring_count | {'checks': [{'name': 'greater_than_or_equal_to', 'type': 'ge'}], 'coerce': False, 'description': 'Aromatic rings count.', 'dtype': 'Int64', 'nullable': True, 'required': False, 'unique': False}                               |                                                                                                                                                                           UNKNOWN | aromatic_ring_count | snapshot-based |
| atc_classifications | {'checks': [], 'coerce': False, 'description': 'JSON string of ATC classifications.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                     |                                                                                                                                                                           UNKNOWN | atc_classifications | snapshot-based |
| availability_type   | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'Availability type (float for nullable int).', 'dtype': 'float64', 'nullable': True, 'required': False, 'unique': False}                         |                                                                                                                                                                           UNKNOWN | availability_type   | snapshot-based |
| black_box_warning   | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'Black box warning flag.', 'dtype': 'int64', 'nullable': True, 'required': False, 'unique': False}                                               |                                                                                                                                                                           UNKNOWN | black_box_warning   | snapshot-based |
| canonical_smiles    | {'checks': [], 'coerce': False, 'description': 'Canonical SMILES representation.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                        |                                                                                                                                                                           UNKNOWN | canonical_smiles    | snapshot-based |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/chembl/molecule.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: ['molecule_type'].
- Merge key correctness: ['molecule_id'].

4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: scd2 (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле              | Тип                | Nullable | Semantic role | Breaking risk |
| ----------------- | ------------------ | -------: | ------------- | ------------- |
| entity_id         | string             |       No | business      | High          |
| content_hash      | string             |       No | business      | High          |
| molecule_id       | string             |       No | business      | High          |
| pref_name         | ['string', 'null'] |      Yes | business      | Medium        |
| molecule_type     | ['string', 'null'] |      Yes | business      | Medium        |
| structure_type    | ['string', 'null'] |      Yes | business      | Medium        |
| max_phase         | ['number', 'null'] |      Yes | business      | Medium        |
| first_approval    | ['number', 'null'] |      Yes | business      | Medium        |
| chirality         | ['number', 'null'] |      Yes | business      | Medium        |
| dosed_ingredient  | ['number', 'null'] |      Yes | business      | Medium        |
| availability_type | ['number', 'null'] |      Yes | business      | Medium        |
| usan_stem         | ['string', 'null'] |      Yes | business      | Medium        |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/chembl/molecule.yaml`
- `tests/contract/silver_schemas/snapshots/chembl_molecule_schema.json`
- `docs/04-reference/contracts/gold/chembl_molecule_v1.0.json`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

### 7. chembl_protein_class

1. Общая информация

- Provider: chembl
- Entity: protein_class
- Pipeline name / pipeline_id: chembl_protein_class
- Primary keys: ['protein_class_id']
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold scd2
- Write mode (Silver/Gold): MERGE(default)/scd2

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле              | Тип                                                                                                                                                                                                                                        |                                                                                                                                                                          Nullable | Source field      | Notes          |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | ----------------- | -------------- |
| \_dq_error        | {'checks': [], 'coerce': False, 'description': 'Flag for data quality errors.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                                     |                                                                                                                                                                           UNKNOWN | \_dq_error        | snapshot-based |
| \_dq_warn         | {'checks': [], 'coerce': False, 'description': 'Flag for data quality warnings.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                                   |                                                                                                                                                                           UNKNOWN | \_dq_warn         | snapshot-based |
| \_index           | {'checks': [{'name': 'greater_than_or_equal_to', 'type': 'ge'}], 'coerce': False, 'description': 'Sequential index of the record in the pipeline run.', 'dtype': 'int64', 'nullable': False, 'required': True, 'unique': False}            |                                                                                                                                                                           UNKNOWN | \_index           | snapshot-based |
| \_ingestion_ts    | {'checks': \[{'name': 'str_matches', 'regex': '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?([+-]\\d{2}:\\d{2}                                                                                                                      | Z)?$'}\], 'coerce': False, 'description': 'Timestamp when the record was ingested (UTC, ISO 8601 format).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False} | UNKNOWN           | \_ingestion_ts |
| \_run_id          | {'checks': [], 'coerce': False, 'description': 'Correlation ID for the pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                               |                                                                                                                                                                           UNKNOWN | \_run_id          | snapshot-based |
| \_run_type        | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'Type of pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                              |                                                                                                                                                                           UNKNOWN | \_run_type        | snapshot-based |
| \_source_batch_id | {'checks': [], 'coerce': False, 'description': 'Batch context ID from the source.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                                  |                                                                                                                                                                           UNKNOWN | \_source_batch_id | snapshot-based |
| class_level       | {'checks': [{'name': 'greater_than_or_equal_to', 'type': 'ge'}], 'coerce': False, 'description': 'Class level.', 'dtype': 'Int64', 'nullable': True, 'required': False, 'unique': False}                                                   |                                                                                                                                                                           UNKNOWN | class_level       | snapshot-based |
| content_hash      | {'checks': \[{'name': 'str_matches', 'regex': '^[a-f0-9]{64}$'}\], 'coerce': False, 'description': 'SHA256 hash of canonical record representation (64 hex chars).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False} |                                                                                                                                                                           UNKNOWN | content_hash      | snapshot-based |
| definition        | {'checks': [], 'coerce': False, 'description': 'Definition.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                                                        |                                                                                                                                                                           UNKNOWN | definition        | snapshot-based |
| downgraded        | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'Downgraded flag.', 'dtype': 'float64', 'nullable': True, 'required': False, 'unique': False}                                                               |                                                                                                                                                                           UNKNOWN | downgraded        | snapshot-based |
| entity_id         | {'checks': [], 'coerce': False, 'description': 'Unique business identifier for the entity.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                         |                                                                                                                                                                           UNKNOWN | entity_id         | snapshot-based |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/chembl/protein_class.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: ['class_level'].
- Merge key correctness: ['protein_class_id'].

4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: scd2 (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле               | Тип                | Nullable | Semantic role | Breaking risk |
| ------------------ | ------------------ | -------: | ------------- | ------------- |
| entity_id          | string             |       No | business      | High          |
| content_hash       | string             |       No | business      | High          |
| protein_class_id   | number             |       No | business      | High          |
| parent_id          | ['number', 'null'] |      Yes | business      | Medium        |
| class_level        | ['number', 'null'] |      Yes | business      | Medium        |
| pref_name          | ['string', 'null'] |      Yes | business      | Medium        |
| short_name         | ['string', 'null'] |      Yes | business      | Medium        |
| protein_class_desc | ['string', 'null'] |      Yes | business      | Medium        |
| definition         | ['string', 'null'] |      Yes | business      | Medium        |
| sort_order         | ['number', 'null'] |      Yes | business      | Medium        |
| replaced_by        | ['number', 'null'] |      Yes | business      | Medium        |
| downgraded         | ['number', 'null'] |      Yes | business      | Medium        |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/chembl/protein_class.yaml`
- `tests/contract/silver_schemas/snapshots/chembl_protein_class_schema.json`
- `docs/04-reference/contracts/gold/chembl_protein_class_v1.0.json`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

### 8. chembl_publication

1. Общая информация

- Provider: chembl
- Entity: publication
- Pipeline name / pipeline_id: chembl_publication
- Primary keys: ['publication_id']
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold scd2
- Write mode (Silver/Gold): MERGE(default)/scd2

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле              | Тип                                                                                                                                                                                                                             |                                                                                                                                                                          Nullable | Source field      | Notes          |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | ----------------- | -------------- |
| \_dq_error        | {'checks': [], 'coerce': False, 'description': 'Flag for data quality errors.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                          |                                                                                                                                                                           UNKNOWN | \_dq_error        | snapshot-based |
| \_dq_warn         | {'checks': [], 'coerce': False, 'description': 'Flag for data quality warnings.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                        |                                                                                                                                                                           UNKNOWN | \_dq_warn         | snapshot-based |
| \_index           | {'checks': [{'name': 'greater_than_or_equal_to', 'type': 'ge'}], 'coerce': False, 'description': 'Sequential index of the record in the pipeline run.', 'dtype': 'int64', 'nullable': False, 'required': True, 'unique': False} |                                                                                                                                                                           UNKNOWN | \_index           | snapshot-based |
| \_ingestion_ts    | {'checks': \[{'name': 'str_matches', 'regex': '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?([+-]\\d{2}:\\d{2}                                                                                                           | Z)?$'}\], 'coerce': False, 'description': 'Timestamp when the record was ingested (UTC, ISO 8601 format).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False} | UNKNOWN           | \_ingestion_ts |
| \_lookup_method   | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'How record was resolved: direct, doi, pmid, title_fallback, title_only', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}  |                                                                                                                                                                           UNKNOWN | \_lookup_method   | snapshot-based |
| \_original_id     | {'checks': [], 'coerce': False, 'description': 'Original identifier from input (for fallback records)', 'dtype': 'str', 'nullable': True, 'required': True, 'unique': False}                                                    |                                                                                                                                                                           UNKNOWN | \_original_id     | snapshot-based |
| \_run_id          | {'checks': [], 'coerce': False, 'description': 'Correlation ID for the pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                    |                                                                                                                                                                           UNKNOWN | \_run_id          | snapshot-based |
| \_run_type        | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'Type of pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                   |                                                                                                                                                                           UNKNOWN | \_run_type        | snapshot-based |
| \_source_batch_id | {'checks': [], 'coerce': False, 'description': 'Batch context ID from the source.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                       |                                                                                                                                                                           UNKNOWN | \_source_batch_id | snapshot-based |
| abstract          | {'checks': [], 'coerce': False, 'description': 'Publication abstract', 'dtype': 'str', 'nullable': True, 'required': True, 'unique': False}                                                                                     |                                                                                                                                                                           UNKNOWN | abstract          | snapshot-based |
| affiliation_list  | {'checks': [], 'coerce': False, 'description': 'JSON array of unique affiliations (unified field name)', 'dtype': 'str', 'nullable': True, 'required': True, 'unique': False}                                                   |                                                                                                                                                                           UNKNOWN | affiliation_list  | snapshot-based |
| author_keys       | {'checks': [], 'coerce': False, 'description': 'Pipe-delimited short author keys (Surname_F format)', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                     |                                                                                                                                                                           UNKNOWN | author_keys       | snapshot-based |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/chembl/publication.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: MISSING/UNKNOWN.
- Merge key correctness: ['publication_id'].

4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: scd2 (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле               | Тип                | Nullable | Semantic role | Breaking risk |
| ------------------ | ------------------ | -------: | ------------- | ------------- |
| entity_id          | string             |       No | business      | High          |
| content_hash       | string             |       No | business      | High          |
| publication_id     | string             |       No | business      | High          |
| pmid               | ['string', 'null'] |      Yes | business      | Medium        |
| doi                | ['string', 'null'] |      Yes | business      | Medium        |
| publication_doi    | ['string', 'null'] |      Yes | business      | Medium        |
| publication_pmid   | ['string', 'null'] |      Yes | business      | Medium        |
| publication_pmc_id | ['string', 'null'] |      Yes | business      | Medium        |
| title              | ['string', 'null'] |      Yes | business      | Medium        |
| authors            | ['string', 'null'] |      Yes | business      | Medium        |
| abstract           | ['string', 'null'] |      Yes | business      | Medium        |
| publication_type   | ['string', 'null'] |      Yes | business      | Medium        |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/chembl/publication.yaml`
- `tests/contract/silver_schemas/snapshots/chembl_publication_schema.json`
- `docs/04-reference/contracts/gold/chembl_document_v1.0.json`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

### 9. chembl_publication_similarity

1. Общая информация

- Provider: chembl
- Entity: publication_similarity
- Pipeline name / pipeline_id: chembl_publication_similarity
- Primary keys: ['sim_id']
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold overwrite
- Write mode (Silver/Gold): MERGE(default)/overwrite

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле              | Тип                                                                                                                                                                                                                                                          |                                                                                                                                                                          Nullable | Source field      | Notes          |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | ----------------- | -------------- |
| \_dq_error        | {'checks': [], 'coerce': False, 'description': 'Flag for data quality errors.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                                                       |                                                                                                                                                                           UNKNOWN | \_dq_error        | snapshot-based |
| \_dq_warn         | {'checks': [], 'coerce': False, 'description': 'Flag for data quality warnings.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                                                     |                                                                                                                                                                           UNKNOWN | \_dq_warn         | snapshot-based |
| \_index           | {'checks': [{'name': 'greater_than_or_equal_to', 'type': 'ge'}], 'coerce': False, 'description': 'Sequential index of the record in the pipeline run.', 'dtype': 'int64', 'nullable': False, 'required': True, 'unique': False}                              |                                                                                                                                                                           UNKNOWN | \_index           | snapshot-based |
| \_ingestion_ts    | {'checks': \[{'name': 'str_matches', 'regex': '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?([+-]\\d{2}:\\d{2}                                                                                                                                        | Z)?$'}\], 'coerce': False, 'description': 'Timestamp when the record was ingested (UTC, ISO 8601 format).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False} | UNKNOWN           | \_ingestion_ts |
| \_run_id          | {'checks': [], 'coerce': False, 'description': 'Correlation ID for the pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                                                 |                                                                                                                                                                           UNKNOWN | \_run_id          | snapshot-based |
| \_run_type        | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'Type of pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                                |                                                                                                                                                                           UNKNOWN | \_run_type        | snapshot-based |
| \_source_batch_id | {'checks': [], 'coerce': False, 'description': 'Batch context ID from the source.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                                                    |                                                                                                                                                                           UNKNOWN | \_source_batch_id | snapshot-based |
| avg_tani          | {'checks': [{'name': 'greater_than_or_equal_to', 'type': 'ge'}, {'name': 'less_than_or_equal_to', 'type': 'le'}], 'coerce': False, 'description': 'Average Tanimoto coefficient.', 'dtype': 'float64', 'nullable': True, 'required': False, 'unique': False} |                                                                                                                                                                           UNKNOWN | avg_tani          | snapshot-based |
| content_hash      | {'checks': \[{'name': 'str_matches', 'regex': '^[a-f0-9]{64}$'}\], 'coerce': False, 'description': 'SHA256 hash of canonical record representation (64 hex chars).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                   |                                                                                                                                                                           UNKNOWN | content_hash      | snapshot-based |
| doc_1             | {'checks': [], 'coerce': False, 'description': 'FK to document 1.', 'dtype': 'int64', 'nullable': False, 'required': True, 'unique': False}                                                                                                                  |                                                                                                                                                                           UNKNOWN | doc_1             | snapshot-based |
| doc_2             | {'checks': [], 'coerce': False, 'description': 'FK to document 2.', 'dtype': 'int64', 'nullable': False, 'required': True, 'unique': False}                                                                                                                  |                                                                                                                                                                           UNKNOWN | doc_2             | snapshot-based |
| entity_id         | {'checks': [], 'coerce': False, 'description': 'Unique business identifier for the entity.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                                           |                                                                                                                                                                           UNKNOWN | entity_id         | snapshot-based |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/chembl/publication_similarity.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: [].
- Merge key correctness: ['sim_id'].

4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: overwrite (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле         | Тип                | Nullable | Semantic role | Breaking risk |
| ------------ | ------------------ | -------: | ------------- | ------------- |
| entity_id    | string             |       No | business      | High          |
| content_hash | string             |       No | business      | High          |
| sim_id       | number             |       No | business      | High          |
| doc_1        | number             |       No | business      | High          |
| doc_2        | number             |       No | business      | High          |
| pubmed_id1   | ['string', 'null'] |      Yes | business      | Medium        |
| pubmed_id2   | ['string', 'null'] |      Yes | business      | Medium        |
| tid_tani     | ['number', 'null'] |      Yes | business      | Medium        |
| mol_tani     | ['number', 'null'] |      Yes | business      | Medium        |
| avg_tani     | ['number', 'null'] |      Yes | business      | Medium        |
| max_tani     | ['number', 'null'] |      Yes | business      | Medium        |
| \_run_id     | string             |       No | metadata      | High          |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/chembl/publication_similarity.yaml`
- `tests/contract/silver_schemas/snapshots/chembl_publication_similarity_schema.json`
- `docs/04-reference/contracts/gold/chembl_document_similarity_v1.0.json`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

### 10. chembl_publication_term

1. Общая информация

- Provider: chembl
- Entity: publication_term
- Pipeline name / pipeline_id: chembl_publication_term
- Primary keys: ['entity_id']
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold overwrite
- Write mode (Silver/Gold): MERGE(default)/overwrite

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле              | Тип                                                                                                                                                                                                                                        |                                                                                                                                                                          Nullable | Source field      | Notes          |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | ----------------- | -------------- |
| \_dq_error        | {'checks': [], 'coerce': False, 'description': 'Flag for data quality errors.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                                     |                                                                                                                                                                           UNKNOWN | \_dq_error        | snapshot-based |
| \_dq_warn         | {'checks': [], 'coerce': False, 'description': 'Flag for data quality warnings.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                                   |                                                                                                                                                                           UNKNOWN | \_dq_warn         | snapshot-based |
| \_index           | {'checks': [{'name': 'greater_than_or_equal_to', 'type': 'ge'}], 'coerce': False, 'description': 'Sequential index of the record in the pipeline run.', 'dtype': 'int64', 'nullable': False, 'required': True, 'unique': False}            |                                                                                                                                                                           UNKNOWN | \_index           | snapshot-based |
| \_ingestion_ts    | {'checks': \[{'name': 'str_matches', 'regex': '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?([+-]\\d{2}:\\d{2}                                                                                                                      | Z)?$'}\], 'coerce': False, 'description': 'Timestamp when the record was ingested (UTC, ISO 8601 format).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False} | UNKNOWN           | \_ingestion_ts |
| \_run_id          | {'checks': [], 'coerce': False, 'description': 'Correlation ID for the pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                               |                                                                                                                                                                           UNKNOWN | \_run_id          | snapshot-based |
| \_run_type        | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'Type of pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                              |                                                                                                                                                                           UNKNOWN | \_run_type        | snapshot-based |
| \_source_batch_id | {'checks': [], 'coerce': False, 'description': 'Batch context ID from the source.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                                  |                                                                                                                                                                           UNKNOWN | \_source_batch_id | snapshot-based |
| content_hash      | {'checks': \[{'name': 'str_matches', 'regex': '^[a-f0-9]{64}$'}\], 'coerce': False, 'description': 'SHA256 hash of canonical record representation (64 hex chars).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False} |                                                                                                                                                                           UNKNOWN | content_hash      | snapshot-based |
| entity_id         | {'checks': [], 'coerce': False, 'description': 'Unique business identifier for the entity.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                         |                                                                                                                                                                           UNKNOWN | entity_id         | snapshot-based |
| mesh_id           | {'checks': [], 'coerce': False, 'description': "MeSH identifier (e.g., 'D001241').", 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                                 |                                                                                                                                                                           UNKNOWN | mesh_id           | snapshot-based |
| publication_id    | {'checks': [{'name': 'str_matches', 'regex': '^CHEMBL\\d+$'}], 'coerce': False, 'description': 'FK → Document ChEMBL ID.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                           |                                                                                                                                                                           UNKNOWN | publication_id    | snapshot-based |
| qualifier         | {'checks': [], 'coerce': False, 'description': "MeSH qualifier (e.g., 'pharmacology').", 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                             |                                                                                                                                                                           UNKNOWN | qualifier         | snapshot-based |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/chembl/publication_term.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: ['term_type'].
- Merge key correctness: ['entity_id'].

4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: overwrite (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле              | Тип                | Nullable | Semantic role | Breaking risk |
| ----------------- | ------------------ | -------: | ------------- | ------------- |
| entity_id         | string             |       No | business      | High          |
| content_hash      | string             |       No | business      | High          |
| publication_id    | string             |       No | business      | High          |
| term              | string             |       No | business      | High          |
| term_type         | string             |       No | business      | High          |
| mesh_id           | ['string', 'null'] |      Yes | business      | Medium        |
| qualifier         | ['string', 'null'] |      Yes | business      | Medium        |
| \_run_id          | string             |       No | metadata      | High          |
| \_run_type        | string             |       No | metadata      | High          |
| \_source_batch_id | ['string', 'null'] |      Yes | metadata      | Medium        |
| \_ingestion_ts    | string             |       No | metadata      | High          |
| \_index           | integer            |       No | metadata      | High          |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/chembl/publication_term.yaml`
- `tests/contract/silver_schemas/snapshots/chembl_publication_term_schema.json`
- `docs/04-reference/contracts/gold/chembl_document_term_v1.0.json`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

### 11. chembl_subcellular_fraction

1. Общая информация

- Provider: chembl
- Entity: subcellular_fraction
- Pipeline name / pipeline_id: chembl_subcellular_fraction
- Primary keys: ['entity_id']
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold scd2
- Write mode (Silver/Gold): MERGE(default)/scd2

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле            | Тип             |        Nullable | Source field    | Notes       |
| --------------- | --------------- | --------------: | --------------- | ----------- |
| MISSING/UNKNOWN | MISSING/UNKNOWN | MISSING/UNKNOWN | MISSING/UNKNOWN | no snapshot |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/chembl/subcellular_fraction.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: MISSING/UNKNOWN.
- Merge key correctness: ['entity_id'].

4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: scd2 (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле                 | Тип                | Nullable | Semantic role | Breaking risk |
| -------------------- | ------------------ | -------: | ------------- | ------------- |
| entity_id            | string             |       No | business      | High          |
| content_hash         | string             |       No | business      | High          |
| subcellular_fraction | string             |       No | business      | High          |
| assay_count          | ['number', 'null'] |      Yes | business      | Medium        |
| example_assay_id     | ['string', 'null'] |      Yes | business      | Medium        |
| \_run_id             | string             |       No | metadata      | High          |
| \_run_type           | string             |       No | metadata      | High          |
| \_source_batch_id    | ['string', 'null'] |      Yes | metadata      | Medium        |
| \_ingestion_ts       | string             |       No | metadata      | High          |
| \_index              | integer            |       No | metadata      | High          |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/chembl/subcellular_fraction.yaml`
- `docs/04-reference/contracts/gold/chembl_subcellular_fraction_v1.0.json`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

### 12. chembl_target

1. Общая информация

- Provider: chembl
- Entity: target
- Pipeline name / pipeline_id: chembl_target
- Primary keys: ['target_id']
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold scd2
- Write mode (Silver/Gold): MERGE(default)/scd2

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле                    | Тип                                                                                                                                                                                                                             |                                                                                                                                                                          Nullable | Source field            | Notes          |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | ----------------------- | -------------- |
| \_dq_error              | {'checks': [], 'coerce': False, 'description': 'Flag for data quality errors.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                          |                                                                                                                                                                           UNKNOWN | \_dq_error              | snapshot-based |
| \_dq_warn               | {'checks': [], 'coerce': False, 'description': 'Flag for data quality warnings.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                        |                                                                                                                                                                           UNKNOWN | \_dq_warn               | snapshot-based |
| \_index                 | {'checks': [{'name': 'greater_than_or_equal_to', 'type': 'ge'}], 'coerce': False, 'description': 'Sequential index of the record in the pipeline run.', 'dtype': 'int64', 'nullable': False, 'required': True, 'unique': False} |                                                                                                                                                                           UNKNOWN | \_index                 | snapshot-based |
| \_ingestion_ts          | {'checks': \[{'name': 'str_matches', 'regex': '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?([+-]\\d{2}:\\d{2}                                                                                                           | Z)?$'}\], 'coerce': False, 'description': 'Timestamp when the record was ingested (UTC, ISO 8601 format).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False} | UNKNOWN                 | \_ingestion_ts |
| \_run_id                | {'checks': [], 'coerce': False, 'description': 'Correlation ID for the pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                    |                                                                                                                                                                           UNKNOWN | \_run_id                | snapshot-based |
| \_run_type              | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'Type of pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                   |                                                                                                                                                                           UNKNOWN | \_run_type              | snapshot-based |
| \_source_batch_id       | {'checks': [], 'coerce': False, 'description': 'Batch context ID from the source.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                       |                                                                                                                                                                           UNKNOWN | \_source_batch_id       | snapshot-based |
| component_accessions    | {'checks': [], 'coerce': False, 'description': 'List of component accessions.', 'dtype': 'object', 'nullable': True, 'required': False, 'unique': False}                                                                        |                                                                                                                                                                           UNKNOWN | component_accessions    | snapshot-based |
| component_descriptions  | {'checks': [], 'coerce': False, 'description': 'List of component descriptions.', 'dtype': 'object', 'nullable': True, 'required': False, 'unique': False}                                                                      |                                                                                                                                                                           UNKNOWN | component_descriptions  | snapshot-based |
| component_ids           | {'checks': [], 'coerce': False, 'description': 'List of component IDs.', 'dtype': 'object', 'nullable': True, 'required': False, 'unique': False}                                                                               |                                                                                                                                                                           UNKNOWN | component_ids           | snapshot-based |
| component_relationships | {'checks': [], 'coerce': False, 'description': 'List of component relationships.', 'dtype': 'object', 'nullable': True, 'required': False, 'unique': False}                                                                     |                                                                                                                                                                           UNKNOWN | component_relationships | snapshot-based |
| component_types         | {'checks': [], 'coerce': False, 'description': 'List of component types.', 'dtype': 'object', 'nullable': True, 'required': False, 'unique': False}                                                                             |                                                                                                                                                                           UNKNOWN | component_types         | snapshot-based |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/chembl/target.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: ['target_type'].
- Merge key correctness: ['target_id'].

4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: scd2 (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле               | Тип                 | Nullable | Semantic role | Breaking risk |
| ------------------ | ------------------- | -------: | ------------- | ------------- |
| entity_id          | string              |       No | business      | High          |
| content_hash       | string              |       No | business      | High          |
| target_id          | string              |       No | business      | High          |
| pref_name          | ['string', 'null']  |      Yes | business      | Medium        |
| target_type        | ['string', 'null']  |      Yes | business      | Medium        |
| organism           | ['string', 'null']  |      Yes | business      | Medium        |
| taxonomy_id        | ['number', 'null']  |      Yes | business      | Medium        |
| species_group_flag | ['boolean', 'null'] |      Yes | business      | Medium        |
| description        | ['string', 'null']  |      Yes | business      | Medium        |
| downgraded         | ['boolean', 'null'] |      Yes | business      | Medium        |
| pipeline_stages    | ['string', 'null']  |      Yes | business      | Medium        |
| target_components  | ['string', 'null']  |      Yes | business      | Medium        |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/chembl/target.yaml`
- `tests/contract/silver_schemas/snapshots/chembl_target_schema.json`
- `docs/04-reference/contracts/gold/chembl_target_v1.0.json`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

### 13. chembl_target_component

1. Общая информация

- Provider: chembl
- Entity: target_component
- Pipeline name / pipeline_id: chembl_target_component
- Primary keys: ['component_id']
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold scd2
- Write mode (Silver/Gold): MERGE(default)/scd2

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле              | Тип                                                                                                                                                                                                                                        |                                                                                                                                                                          Nullable | Source field      | Notes          |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | ----------------- | -------------- |
| \_dq_error        | {'checks': [], 'coerce': False, 'description': 'Flag for data quality errors.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                                     |                                                                                                                                                                           UNKNOWN | \_dq_error        | snapshot-based |
| \_dq_warn         | {'checks': [], 'coerce': False, 'description': 'Flag for data quality warnings.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                                   |                                                                                                                                                                           UNKNOWN | \_dq_warn         | snapshot-based |
| \_index           | {'checks': [{'name': 'greater_than_or_equal_to', 'type': 'ge'}], 'coerce': False, 'description': 'Sequential index of the record in the pipeline run.', 'dtype': 'int64', 'nullable': False, 'required': True, 'unique': False}            |                                                                                                                                                                           UNKNOWN | \_index           | snapshot-based |
| \_ingestion_ts    | {'checks': \[{'name': 'str_matches', 'regex': '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?([+-]\\d{2}:\\d{2}                                                                                                                      | Z)?$'}\], 'coerce': False, 'description': 'Timestamp when the record was ingested (UTC, ISO 8601 format).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False} | UNKNOWN           | \_ingestion_ts |
| \_run_id          | {'checks': [], 'coerce': False, 'description': 'Correlation ID for the pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                               |                                                                                                                                                                           UNKNOWN | \_run_id          | snapshot-based |
| \_run_type        | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'Type of pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                              |                                                                                                                                                                           UNKNOWN | \_run_type        | snapshot-based |
| \_source_batch_id | {'checks': [], 'coerce': False, 'description': 'Batch context ID from the source.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                                  |                                                                                                                                                                           UNKNOWN | \_source_batch_id | snapshot-based |
| accession         | {'checks': [], 'coerce': False, 'description': 'UniProt accession.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                                                 |                                                                                                                                                                           UNKNOWN | accession         | snapshot-based |
| component_id      | {'checks': [], 'coerce': False, 'description': 'Component ID (primary key).', 'dtype': 'int64', 'nullable': False, 'required': True, 'unique': False}                                                                                      |                                                                                                                                                                           UNKNOWN | component_id      | snapshot-based |
| component_type    | {'checks': [], 'coerce': False, 'description': 'Component type (PROTEIN, DNA, RNA, etc.).', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                          |                                                                                                                                                                           UNKNOWN | component_type    | snapshot-based |
| content_hash      | {'checks': \[{'name': 'str_matches', 'regex': '^[a-f0-9]{64}$'}\], 'coerce': False, 'description': 'SHA256 hash of canonical record representation (64 hex chars).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False} |                                                                                                                                                                           UNKNOWN | content_hash      | snapshot-based |
| description       | {'checks': [], 'coerce': False, 'description': 'Component description.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                                             |                                                                                                                                                                           UNKNOWN | description       | snapshot-based |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/chembl/target_component.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: ['organism'].
- Merge key correctness: ['component_id'].

4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: scd2 (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле                      | Тип                | Nullable | Semantic role | Breaking risk |
| ------------------------- | ------------------ | -------: | ------------- | ------------- |
| entity_id                 | string             |       No | business      | High          |
| content_hash              | string             |       No | business      | High          |
| component_id              | number             |       No | business      | High          |
| accession                 | ['string', 'null'] |      Yes | business      | Medium        |
| component_type            | ['string', 'null'] |      Yes | business      | Medium        |
| description               | ['string', 'null'] |      Yes | business      | Medium        |
| organism                  | ['string', 'null'] |      Yes | business      | Medium        |
| taxonomy_id               | ['number', 'null'] |      Yes | business      | Medium        |
| target_component_synonyms | ['string', 'null'] |      Yes | business      | Medium        |
| target_component_xrefs    | ['string', 'null'] |      Yes | business      | Medium        |
| protein_classifications   | ['string', 'null'] |      Yes | business      | Medium        |
| protein_classification_id | ['number', 'null'] |      Yes | business      | Medium        |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/chembl/target_component.yaml`
- `tests/contract/silver_schemas/snapshots/chembl_target_component_schema.json`
- `docs/04-reference/contracts/gold/chembl_target_component_v1.0.json`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

### 14. chembl_tissue

1. Общая информация

- Provider: chembl
- Entity: tissue
- Pipeline name / pipeline_id: chembl_tissue
- Primary keys: ['tissue_id']
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold scd2
- Write mode (Silver/Gold): MERGE(default)/scd2

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле            | Тип             |        Nullable | Source field    | Notes       |
| --------------- | --------------- | --------------: | --------------- | ----------- |
| MISSING/UNKNOWN | MISSING/UNKNOWN | MISSING/UNKNOWN | MISSING/UNKNOWN | no snapshot |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/chembl/tissue.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: MISSING/UNKNOWN.
- Merge key correctness: ['tissue_id'].

4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: scd2 (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле              | Тип                | Nullable | Semantic role | Breaking risk |
| ----------------- | ------------------ | -------: | ------------- | ------------- |
| tissue_id         | string             |       No | business      | High          |
| pref_name         | string             |       No | business      | High          |
| bto_id            | ['string', 'null'] |      Yes | business      | Medium        |
| caloha_id         | ['string', 'null'] |      Yes | business      | Medium        |
| efo_id            | ['string', 'null'] |      Yes | business      | Medium        |
| uberon_id         | ['string', 'null'] |      Yes | business      | Medium        |
| \_run_id          | string             |       No | metadata      | High          |
| \_run_type        | string             |       No | metadata      | High          |
| \_source_batch_id | ['string', 'null'] |      Yes | metadata      | Medium        |
| \_ingestion_ts    | string             |       No | metadata      | High          |
| \_index           | integer            |       No | metadata      | High          |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/chembl/tissue.yaml`
- `docs/04-reference/contracts/gold/chembl_tissue_v1.0.json`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

### 15. composite_activity

1. Общая информация

- Provider: composite
- Entity: activity
- Pipeline name / pipeline_id: composite_activity
- Primary keys: MISSING/UNKNOWN
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold APPEND(default)
- Write mode (Silver/Gold): MERGE(default)/APPEND(default)

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле            | Тип             |        Nullable | Source field    | Notes       |
| --------------- | --------------- | --------------: | --------------- | ----------- |
| MISSING/UNKNOWN | MISSING/UNKNOWN | MISSING/UNKNOWN | MISSING/UNKNOWN | no snapshot |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/composite/activity.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: MISSING/UNKNOWN.
- Merge key correctness: MISSING/UNKNOWN.

4. Gold Schema (Контракт)

- Контрактная версия: MISSING/UNKNOWN
- SCD2 / overwrite / append: APPEND(default) (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле            | Тип             |        Nullable | Semantic role   | Breaking risk |
| --------------- | --------------- | --------------: | --------------- | ------------- |
| MISSING/UNKNOWN | MISSING/UNKNOWN | MISSING/UNKNOWN | MISSING/UNKNOWN | High          |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/composite/activity.yaml`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

### 16. composite_assay

1. Общая информация

- Provider: composite
- Entity: assay
- Pipeline name / pipeline_id: composite_assay
- Primary keys: MISSING/UNKNOWN
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold APPEND(default)
- Write mode (Silver/Gold): MERGE(default)/APPEND(default)

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле            | Тип             |        Nullable | Source field    | Notes       |
| --------------- | --------------- | --------------: | --------------- | ----------- |
| MISSING/UNKNOWN | MISSING/UNKNOWN | MISSING/UNKNOWN | MISSING/UNKNOWN | no snapshot |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/composite/assay.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: MISSING/UNKNOWN.
- Merge key correctness: MISSING/UNKNOWN.

4. Gold Schema (Контракт)

- Контрактная версия: MISSING/UNKNOWN
- SCD2 / overwrite / append: APPEND(default) (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле            | Тип             |        Nullable | Semantic role   | Breaking risk |
| --------------- | --------------- | --------------: | --------------- | ------------- |
| MISSING/UNKNOWN | MISSING/UNKNOWN | MISSING/UNKNOWN | MISSING/UNKNOWN | High          |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/composite/assay.yaml`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

### 17. composite_molecule

1. Общая информация

- Provider: composite
- Entity: molecule
- Pipeline name / pipeline_id: composite_molecule
- Primary keys: MISSING/UNKNOWN
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold APPEND(default)
- Write mode (Silver/Gold): MERGE(default)/APPEND(default)

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле            | Тип             |        Nullable | Source field    | Notes       |
| --------------- | --------------- | --------------: | --------------- | ----------- |
| MISSING/UNKNOWN | MISSING/UNKNOWN | MISSING/UNKNOWN | MISSING/UNKNOWN | no snapshot |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/composite/molecule.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: MISSING/UNKNOWN.
- Merge key correctness: MISSING/UNKNOWN.

4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: APPEND(default) (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле               | Тип                | Nullable | Semantic role | Breaking risk |
| ------------------ | ------------------ | -------: | ------------- | ------------- |
| entity_id          | string             |       No | business      | High          |
| content_hash       | string             |       No | business      | High          |
| \_dq_warn          | boolean            |       No | metadata      | High          |
| \_dq_error         | boolean            |       No | metadata      | High          |
| \_run_id           | string             |       No | metadata      | High          |
| \_run_type         | string             |       No | metadata      | High          |
| \_source_batch_id  | ['string', 'null'] |      Yes | metadata      | Medium        |
| \_ingestion_ts     | string             |       No | metadata      | High          |
| \_index            | integer            |       No | metadata      | High          |
| \_source           | ['string', 'null'] |      Yes | metadata      | Medium        |
| \_composite_run_id | string             |       No | metadata      | High          |
| \_source_providers | string             |       No | metadata      | High          |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/composite/molecule.yaml`
- `docs/04-reference/contracts/gold/composite_molecule_v1.0.json`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

### 18. composite_publication

1. Общая информация

- Provider: composite
- Entity: publication
- Pipeline name / pipeline_id: composite_publication
- Primary keys: MISSING/UNKNOWN
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold APPEND(default)
- Write mode (Silver/Gold): MERGE(default)/APPEND(default)

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле            | Тип             |        Nullable | Source field    | Notes       |
| --------------- | --------------- | --------------: | --------------- | ----------- |
| MISSING/UNKNOWN | MISSING/UNKNOWN | MISSING/UNKNOWN | MISSING/UNKNOWN | no snapshot |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/composite/publication.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: MISSING/UNKNOWN.
- Merge key correctness: MISSING/UNKNOWN.

4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: APPEND(default) (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле              | Тип                | Nullable | Semantic role | Breaking risk |
| ----------------- | ------------------ | -------: | ------------- | ------------- |
| entity_id         | string             |       No | business      | High          |
| content_hash      | string             |       No | business      | High          |
| \_dq_warn         | boolean            |       No | metadata      | High          |
| \_dq_error        | boolean            |       No | metadata      | High          |
| \_run_id          | string             |       No | metadata      | High          |
| \_run_type        | string             |       No | metadata      | High          |
| \_source_batch_id | ['string', 'null'] |      Yes | metadata      | Medium        |
| \_ingestion_ts    | string             |       No | metadata      | High          |
| \_index           | integer            |       No | metadata      | High          |
| \_source          | ['string', 'null'] |      Yes | metadata      | Medium        |
| \_lookup_method   | ['string', 'null'] |      Yes | metadata      | Medium        |
| \_original_id     | ['string', 'null'] |      Yes | metadata      | Medium        |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/composite/publication.yaml`
- `docs/04-reference/contracts/gold/composite_publication_v1.0.json`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

### 19. composite_target

1. Общая информация

- Provider: composite
- Entity: target
- Pipeline name / pipeline_id: composite_target
- Primary keys: MISSING/UNKNOWN
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold APPEND(default)
- Write mode (Silver/Gold): MERGE(default)/APPEND(default)

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле            | Тип             |        Nullable | Source field    | Notes       |
| --------------- | --------------- | --------------: | --------------- | ----------- |
| MISSING/UNKNOWN | MISSING/UNKNOWN | MISSING/UNKNOWN | MISSING/UNKNOWN | no snapshot |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/composite/target.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: MISSING/UNKNOWN.
- Merge key correctness: MISSING/UNKNOWN.

4. Gold Schema (Контракт)

- Контрактная версия: MISSING/UNKNOWN
- SCD2 / overwrite / append: APPEND(default) (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле            | Тип             |        Nullable | Semantic role   | Breaking risk |
| --------------- | --------------- | --------------: | --------------- | ------------- |
| MISSING/UNKNOWN | MISSING/UNKNOWN | MISSING/UNKNOWN | MISSING/UNKNOWN | High          |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/composite/target.yaml`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

### 20. crossref_publication

1. Общая информация

- Provider: crossref
- Entity: publication
- Pipeline name / pipeline_id: crossref_publication
- Primary keys: ['doi']
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold scd2
- Write mode (Silver/Gold): MERGE(default)/scd2

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле              | Тип                                                                                                                                                                                                                             |                                                                                                                                                                          Nullable | Source field      | Notes          |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | ----------------- | -------------- |
| \_dq_error        | {'checks': [], 'coerce': False, 'description': 'Flag for data quality errors.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                          |                                                                                                                                                                           UNKNOWN | \_dq_error        | snapshot-based |
| \_dq_warn         | {'checks': [], 'coerce': False, 'description': 'Flag for data quality warnings.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                        |                                                                                                                                                                           UNKNOWN | \_dq_warn         | snapshot-based |
| \_index           | {'checks': [{'name': 'greater_than_or_equal_to', 'type': 'ge'}], 'coerce': False, 'description': 'Sequential index of the record in the pipeline run.', 'dtype': 'int64', 'nullable': False, 'required': True, 'unique': False} |                                                                                                                                                                           UNKNOWN | \_index           | snapshot-based |
| \_ingestion_ts    | {'checks': \[{'name': 'str_matches', 'regex': '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?([+-]\\d{2}:\\d{2}                                                                                                           | Z)?$'}\], 'coerce': False, 'description': 'Timestamp when the record was ingested (UTC, ISO 8601 format).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False} | UNKNOWN           | \_ingestion_ts |
| \_lookup_method   | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'How record was resolved: direct, doi, pmid, title_fallback, title_only', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}  |                                                                                                                                                                           UNKNOWN | \_lookup_method   | snapshot-based |
| \_original_id     | {'checks': [], 'coerce': False, 'description': 'Original identifier from input (for fallback records)', 'dtype': 'str', 'nullable': True, 'required': True, 'unique': False}                                                    |                                                                                                                                                                           UNKNOWN | \_original_id     | snapshot-based |
| \_run_id          | {'checks': [], 'coerce': False, 'description': 'Correlation ID for the pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                    |                                                                                                                                                                           UNKNOWN | \_run_id          | snapshot-based |
| \_run_type        | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'Type of pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                   |                                                                                                                                                                           UNKNOWN | \_run_type        | snapshot-based |
| \_source_batch_id | {'checks': [], 'coerce': False, 'description': 'Batch context ID from the source.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                       |                                                                                                                                                                           UNKNOWN | \_source_batch_id | snapshot-based |
| abstract          | {'checks': [], 'coerce': False, 'description': 'Publication abstract', 'dtype': 'str', 'nullable': True, 'required': True, 'unique': False}                                                                                     |                                                                                                                                                                           UNKNOWN | abstract          | snapshot-based |
| affiliation_list  | {'checks': [], 'coerce': False, 'description': 'JSON array of unique affiliations (unified field name)', 'dtype': 'str', 'nullable': True, 'required': True, 'unique': False}                                                   |                                                                                                                                                                           UNKNOWN | affiliation_list  | snapshot-based |
| alternative_id    | {'checks': [], 'coerce': False, 'description': 'Alternative IDs (publisher-specific, e.g., PII)', 'dtype': 'object', 'nullable': True, 'required': True, 'unique': False}                                                       |                                                                                                                                                                           UNKNOWN | alternative_id    | snapshot-based |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/crossref/publication.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: MISSING/UNKNOWN.
- Merge key correctness: ['doi'].

4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: scd2 (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле         | Тип                | Nullable | Semantic role | Breaking risk |
| ------------ | ------------------ | -------: | ------------- | ------------- |
| entity_id    | string             |       No | business      | High          |
| content_hash | string             |       No | business      | High          |
| doi          | string             |       No | business      | High          |
| title        | ['string', 'null'] |      Yes | business      | Medium        |
| authors      | ['string', 'null'] |      Yes | business      | Medium        |
| journal      | ['string', 'null'] |      Yes | business      | Medium        |
| issn         | ['string', 'null'] |      Yes | business      | Medium        |
| issn_list    | ['string', 'null'] |      Yes | business      | Medium        |
| publisher    | ['string', 'null'] |      Yes | business      | Medium        |
| volume       | ['string', 'null'] |      Yes | business      | Medium        |
| issue        | ['string', 'null'] |      Yes | business      | Medium        |
| page_first   | ['string', 'null'] |      Yes | business      | Medium        |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/crossref/publication.yaml`
- `tests/contract/silver_schemas/snapshots/crossref_publication_schema.json`
- `docs/04-reference/contracts/gold/crossref_publication_v1.0.json`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

### 21. openalex_publication

1. Общая информация

- Provider: openalex
- Entity: publication
- Pipeline name / pipeline_id: openalex_publication
- Primary keys: ['openalex_id']
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold scd2
- Write mode (Silver/Gold): MERGE(default)/scd2

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле              | Тип                                                                                                                                                                                                                             |                                                                                                                                                                          Nullable | Source field      | Notes          |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | ----------------- | -------------- |
| \_dq_error        | {'checks': [], 'coerce': False, 'description': 'Flag for data quality errors.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                          |                                                                                                                                                                           UNKNOWN | \_dq_error        | snapshot-based |
| \_dq_warn         | {'checks': [], 'coerce': False, 'description': 'Flag for data quality warnings.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                        |                                                                                                                                                                           UNKNOWN | \_dq_warn         | snapshot-based |
| \_index           | {'checks': [{'name': 'greater_than_or_equal_to', 'type': 'ge'}], 'coerce': False, 'description': 'Sequential index of the record in the pipeline run.', 'dtype': 'int64', 'nullable': False, 'required': True, 'unique': False} |                                                                                                                                                                           UNKNOWN | \_index           | snapshot-based |
| \_ingestion_ts    | {'checks': \[{'name': 'str_matches', 'regex': '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?([+-]\\d{2}:\\d{2}                                                                                                           | Z)?$'}\], 'coerce': False, 'description': 'Timestamp when the record was ingested (UTC, ISO 8601 format).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False} | UNKNOWN           | \_ingestion_ts |
| \_lookup_method   | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'How record was resolved: direct, doi, pmid, title_fallback, title_only', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}  |                                                                                                                                                                           UNKNOWN | \_lookup_method   | snapshot-based |
| \_original_id     | {'checks': [], 'coerce': False, 'description': 'Original identifier from input (for fallback records)', 'dtype': 'str', 'nullable': True, 'required': True, 'unique': False}                                                    |                                                                                                                                                                           UNKNOWN | \_original_id     | snapshot-based |
| \_run_id          | {'checks': [], 'coerce': False, 'description': 'Correlation ID for the pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                    |                                                                                                                                                                           UNKNOWN | \_run_id          | snapshot-based |
| \_run_type        | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'Type of pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                   |                                                                                                                                                                           UNKNOWN | \_run_type        | snapshot-based |
| \_source_batch_id | {'checks': [], 'coerce': False, 'description': 'Batch context ID from the source.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                       |                                                                                                                                                                           UNKNOWN | \_source_batch_id | snapshot-based |
| abstract          | {'checks': [], 'coerce': False, 'description': 'Publication abstract', 'dtype': 'str', 'nullable': True, 'required': True, 'unique': False}                                                                                     |                                                                                                                                                                           UNKNOWN | abstract          | snapshot-based |
| affiliation_list  | {'checks': [], 'coerce': False, 'description': 'JSON array of unique affiliations (unified field name)', 'dtype': 'str', 'nullable': True, 'required': True, 'unique': False}                                                   |                                                                                                                                                                           UNKNOWN | affiliation_list  | snapshot-based |
| author_keys       | {'checks': [], 'coerce': False, 'description': 'Pipe-delimited short author keys (Surname_F format)', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                     |                                                                                                                                                                           UNKNOWN | author_keys       | snapshot-based |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/openalex/publication.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: MISSING/UNKNOWN.
- Merge key correctness: ['openalex_id'].

4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: scd2 (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле             | Тип                | Nullable | Semantic role | Breaking risk |
| ---------------- | ------------------ | -------: | ------------- | ------------- |
| entity_id        | string             |       No | business      | High          |
| content_hash     | string             |       No | business      | High          |
| openalex_id      | string             |       No | business      | High          |
| doi              | ['string', 'null'] |      Yes | business      | Medium        |
| pmid             | ['string', 'null'] |      Yes | business      | Medium        |
| title            | ['string', 'null'] |      Yes | business      | Medium        |
| abstract         | ['string', 'null'] |      Yes | business      | Medium        |
| authors          | ['string', 'null'] |      Yes | business      | Medium        |
| affiliation_list | ['string', 'null'] |      Yes | business      | Medium        |
| subject_mesh     | ['string', 'null'] |      Yes | business      | Medium        |
| subject_keywords | ['string', 'null'] |      Yes | business      | Medium        |
| mag_id           | ['string', 'null'] |      Yes | business      | Medium        |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/openalex/publication.yaml`
- `tests/contract/silver_schemas/snapshots/openalex_publication_schema.json`
- `docs/04-reference/contracts/gold/openalex_publication_v1.0.json`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

### 22. pubchem_compound

1. Общая информация

- Provider: pubchem
- Entity: compound
- Pipeline name / pipeline_id: pubchem_compound
- Primary keys: ['molecule_id']
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold scd2
- Write mode (Silver/Gold): MERGE(default)/scd2

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле              | Тип                                                                                                                                                                                                                             |                                                                                                                                                                          Nullable | Source field      | Notes          |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | ----------------- | -------------- |
| \_dq_error        | {'checks': [], 'coerce': False, 'description': 'Flag for data quality errors.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                          |                                                                                                                                                                           UNKNOWN | \_dq_error        | snapshot-based |
| \_dq_warn         | {'checks': [], 'coerce': False, 'description': 'Flag for data quality warnings.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                        |                                                                                                                                                                           UNKNOWN | \_dq_warn         | snapshot-based |
| \_index           | {'checks': [{'name': 'greater_than_or_equal_to', 'type': 'ge'}], 'coerce': False, 'description': 'Sequential index of the record in the pipeline run.', 'dtype': 'int64', 'nullable': False, 'required': True, 'unique': False} |                                                                                                                                                                           UNKNOWN | \_index           | snapshot-based |
| \_ingestion_ts    | {'checks': \[{'name': 'str_matches', 'regex': '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?([+-]\\d{2}:\\d{2}                                                                                                           | Z)?$'}\], 'coerce': False, 'description': 'Timestamp when the record was ingested (UTC, ISO 8601 format).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False} | UNKNOWN           | \_ingestion_ts |
| \_run_id          | {'checks': [], 'coerce': False, 'description': 'Correlation ID for the pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                    |                                                                                                                                                                           UNKNOWN | \_run_id          | snapshot-based |
| \_run_type        | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'Type of pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                   |                                                                                                                                                                           UNKNOWN | \_run_type        | snapshot-based |
| \_source_batch_id | {'checks': [], 'coerce': False, 'description': 'Batch context ID from the source.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                       |                                                                                                                                                                           UNKNOWN | \_source_batch_id | snapshot-based |
| atom_stereo_count | {'checks': [{'name': 'atom_stereo_count_non_negative'}], 'coerce': False, 'description': 'Total stereocenters', 'dtype': 'Int64', 'nullable': True, 'required': False, 'unique': False}                                         |                                                                                                                                                                           UNKNOWN | atom_stereo_count | snapshot-based |
| bond_stereo_count | {'checks': [{'name': 'bond_stereo_count_non_negative'}], 'coerce': False, 'description': 'Total E/Z bonds', 'dtype': 'Int64', 'nullable': True, 'required': False, 'unique': False}                                             |                                                                                                                                                                           UNKNOWN | bond_stereo_count | snapshot-based |
| canonical_smiles  | {'checks': [{'name': 'canonical_smiles_length'}], 'coerce': False, 'description': 'Canonical SMILES string', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                              |                                                                                                                                                                           UNKNOWN | canonical_smiles  | snapshot-based |
| charge            | {'checks': [{'name': 'charge_range'}], 'coerce': False, 'description': 'Formal charge', 'dtype': 'Int64', 'nullable': True, 'required': False, 'unique': False}                                                                 |                                                                                                                                                                           UNKNOWN | charge            | snapshot-based |
| complexity        | {'checks': [{'name': 'complexity_non_negative'}], 'coerce': False, 'description': 'Structural complexity score', 'dtype': 'float64', 'nullable': True, 'required': False, 'unique': False}                                      |                                                                                                                                                                           UNKNOWN | complexity        | snapshot-based |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/pubchem/compound.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: ['batch_date'].
- Merge key correctness: ['molecule_id'].

4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: scd2 (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле              | Тип                | Nullable | Semantic role | Breaking risk |
| ----------------- | ------------------ | -------: | ------------- | ------------- |
| entity_id         | string             |       No | business      | High          |
| molecule_id       | string             |       No | business      | High          |
| molecular_formula | ['string', 'null'] |      Yes | business      | Medium        |
| molecular_weight  | ['number', 'null'] |      Yes | business      | Medium        |
| canonical_smiles  | ['string', 'null'] |      Yes | business      | Medium        |
| isomeric_smiles   | ['string', 'null'] |      Yes | business      | Medium        |
| inchi             | ['string', 'null'] |      Yes | business      | Medium        |
| inchi_key         | ['string', 'null'] |      Yes | business      | Medium        |
| xlogp             | ['number', 'null'] |      Yes | business      | Medium        |
| tpsa              | ['number', 'null'] |      Yes | business      | Medium        |
| iupac_name        | ['string', 'null'] |      Yes | business      | Medium        |
| content_hash      | string             |       No | business      | High          |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/pubchem/compound.yaml`
- `tests/contract/silver_schemas/snapshots/pubchem_compound_schema.json`
- `docs/04-reference/contracts/gold/pubchem_compound_v1.0.json`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

### 23. pubmed_publication

1. Общая информация

- Provider: pubmed
- Entity: publication
- Pipeline name / pipeline_id: pubmed_publication
- Primary keys: ['pmid']
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold scd2
- Write mode (Silver/Gold): MERGE(default)/scd2

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле                | Тип                                                                                                                                                                                                                             |                                                                                                                                                                          Nullable | Source field        | Notes          |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | ------------------- | -------------- |
| \_dq_error          | {'checks': [], 'coerce': False, 'description': 'Flag for data quality errors.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                          |                                                                                                                                                                           UNKNOWN | \_dq_error          | snapshot-based |
| \_dq_warn           | {'checks': [], 'coerce': False, 'description': 'Flag for data quality warnings.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                        |                                                                                                                                                                           UNKNOWN | \_dq_warn           | snapshot-based |
| \_index             | {'checks': [{'name': 'greater_than_or_equal_to', 'type': 'ge'}], 'coerce': False, 'description': 'Sequential index of the record in the pipeline run.', 'dtype': 'int64', 'nullable': False, 'required': True, 'unique': False} |                                                                                                                                                                           UNKNOWN | \_index             | snapshot-based |
| \_ingestion_ts      | {'checks': \[{'name': 'str_matches', 'regex': '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?([+-]\\d{2}:\\d{2}                                                                                                           | Z)?$'}\], 'coerce': False, 'description': 'Timestamp when the record was ingested (UTC, ISO 8601 format).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False} | UNKNOWN             | \_ingestion_ts |
| \_lookup_method     | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'How record was resolved: direct, doi, pmid, title_fallback, title_only', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}  |                                                                                                                                                                           UNKNOWN | \_lookup_method     | snapshot-based |
| \_original_id       | {'checks': [], 'coerce': False, 'description': 'Original identifier from input (for fallback records)', 'dtype': 'str', 'nullable': True, 'required': True, 'unique': False}                                                    |                                                                                                                                                                           UNKNOWN | \_original_id       | snapshot-based |
| \_run_id            | {'checks': [], 'coerce': False, 'description': 'Correlation ID for the pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                    |                                                                                                                                                                           UNKNOWN | \_run_id            | snapshot-based |
| \_run_type          | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'Type of pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                   |                                                                                                                                                                           UNKNOWN | \_run_type          | snapshot-based |
| \_source_batch_id   | {'checks': [], 'coerce': False, 'description': 'Batch context ID from the source.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                       |                                                                                                                                                                           UNKNOWN | \_source_batch_id   | snapshot-based |
| abstract            | {'checks': [], 'coerce': False, 'description': 'Publication abstract', 'dtype': 'str', 'nullable': True, 'required': True, 'unique': False}                                                                                     |                                                                                                                                                                           UNKNOWN | abstract            | snapshot-based |
| abstract_structured | {'checks': [], 'coerce': False, 'description': 'Whether abstract has NLM sections', 'dtype': 'bool', 'nullable': True, 'required': True, 'unique': False}                                                                       |                                                                                                                                                                           UNKNOWN | abstract_structured | snapshot-based |
| affiliation_list    | {'checks': [], 'coerce': False, 'description': 'JSON array of unique affiliations (unified field name)', 'dtype': 'str', 'nullable': True, 'required': True, 'unique': False}                                                   |                                                                                                                                                                           UNKNOWN | affiliation_list    | snapshot-based |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/pubmed/publication.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: MISSING/UNKNOWN.
- Merge key correctness: ['pmid'].

4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: scd2 (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле                | Тип                 | Nullable | Semantic role | Breaking risk |
| ------------------- | ------------------- | -------: | ------------- | ------------- |
| entity_id           | string              |       No | business      | High          |
| content_hash        | string              |       No | business      | High          |
| pmid                | string              |       No | business      | High          |
| doi                 | ['string', 'null']  |      Yes | business      | Medium        |
| pmc_id              | ['string', 'null']  |      Yes | business      | Medium        |
| title               | string              |       No | business      | High          |
| abstract            | ['string', 'null']  |      Yes | business      | Medium        |
| abstract_structured | ['boolean', 'null'] |      Yes | business      | Medium        |
| journal             | ['string', 'null']  |      Yes | business      | Medium        |
| journal_name_short  | ['string', 'null']  |      Yes | business      | Medium        |
| journal_iso_abbrev  | ['string', 'null']  |      Yes | business      | Medium        |
| journal_issn_type   | ['string', 'null']  |      Yes | business      | Medium        |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/pubmed/publication.yaml`
- `tests/contract/silver_schemas/snapshots/pubmed_publication_schema.json`
- `docs/04-reference/contracts/gold/pubmed_publication_v1.0.json`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

### 24. semanticscholar_publication

1. Общая информация

- Provider: semanticscholar
- Entity: publication
- Pipeline name / pipeline_id: semanticscholar_publication
- Primary keys: ['paper_id']
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold scd2
- Write mode (Silver/Gold): MERGE(default)/scd2

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле              | Тип                                                                                                                                                                                                                             |                                                                                                                                                                          Nullable | Source field      | Notes          |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | ----------------- | -------------- |
| \_dq_error        | {'checks': [], 'coerce': False, 'description': 'Flag for data quality errors.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                          |                                                                                                                                                                           UNKNOWN | \_dq_error        | snapshot-based |
| \_dq_warn         | {'checks': [], 'coerce': False, 'description': 'Flag for data quality warnings.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                        |                                                                                                                                                                           UNKNOWN | \_dq_warn         | snapshot-based |
| \_index           | {'checks': [{'name': 'greater_than_or_equal_to', 'type': 'ge'}], 'coerce': False, 'description': 'Sequential index of the record in the pipeline run.', 'dtype': 'int64', 'nullable': False, 'required': True, 'unique': False} |                                                                                                                                                                           UNKNOWN | \_index           | snapshot-based |
| \_ingestion_ts    | {'checks': \[{'name': 'str_matches', 'regex': '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?([+-]\\d{2}:\\d{2}                                                                                                           | Z)?$'}\], 'coerce': False, 'description': 'Timestamp when the record was ingested (UTC, ISO 8601 format).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False} | UNKNOWN           | \_ingestion_ts |
| \_lookup_method   | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'How record was resolved: direct, doi, pmid, title_fallback, title_only', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}  |                                                                                                                                                                           UNKNOWN | \_lookup_method   | snapshot-based |
| \_original_id     | {'checks': [], 'coerce': False, 'description': 'Original identifier from input (for fallback records)', 'dtype': 'str', 'nullable': True, 'required': True, 'unique': False}                                                    |                                                                                                                                                                           UNKNOWN | \_original_id     | snapshot-based |
| \_run_id          | {'checks': [], 'coerce': False, 'description': 'Correlation ID for the pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                    |                                                                                                                                                                           UNKNOWN | \_run_id          | snapshot-based |
| \_run_type        | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'Type of pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                   |                                                                                                                                                                           UNKNOWN | \_run_type        | snapshot-based |
| \_source_batch_id | {'checks': [], 'coerce': False, 'description': 'Batch context ID from the source.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                       |                                                                                                                                                                           UNKNOWN | \_source_batch_id | snapshot-based |
| abstract          | {'checks': [], 'coerce': False, 'description': 'Publication abstract', 'dtype': 'str', 'nullable': True, 'required': True, 'unique': False}                                                                                     |                                                                                                                                                                           UNKNOWN | abstract          | snapshot-based |
| affiliation_list  | {'checks': [], 'coerce': False, 'description': 'JSON array of unique affiliations (unified field name)', 'dtype': 'str', 'nullable': True, 'required': True, 'unique': False}                                                   |                                                                                                                                                                           UNKNOWN | affiliation_list  | snapshot-based |
| author_h_indices  | {'checks': [], 'coerce': False, 'description': 'Author h-index values (JSON array, null for missing)', 'dtype': 'str', 'nullable': True, 'required': True, 'unique': False}                                                     |                                                                                                                                                                           UNKNOWN | author_h_indices  | snapshot-based |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/semanticscholar/publication.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: MISSING/UNKNOWN.
- Merge key correctness: ['paper_id'].

4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: scd2 (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле             | Тип                | Nullable | Semantic role | Breaking risk |
| ---------------- | ------------------ | -------: | ------------- | ------------- |
| entity_id        | string             |       No | business      | High          |
| content_hash     | string             |       No | business      | High          |
| paper_id         | string             |       No | business      | High          |
| doi              | ['string', 'null'] |      Yes | business      | Medium        |
| pmid             | ['string', 'null'] |      Yes | business      | Medium        |
| corpus_id        | ['number', 'null'] |      Yes | business      | Medium        |
| title            | ['string', 'null'] |      Yes | business      | Medium        |
| abstract         | ['string', 'null'] |      Yes | business      | Medium        |
| authors          | ['string', 'null'] |      Yes | business      | Medium        |
| tldr             | ['string', 'null'] |      Yes | business      | Medium        |
| publication_year | ['number', 'null'] |      Yes | business      | Medium        |
| publication_date | ['string', 'null'] |      Yes | business      | Medium        |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/semanticscholar/publication.yaml`
- `tests/contract/silver_schemas/snapshots/semanticscholar_publication_schema.json`
- `docs/04-reference/contracts/gold/semanticscholar_publication_v1.0.json`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

### 25. uniprot_idmapping

1. Общая информация

- Provider: uniprot
- Entity: idmapping
- Pipeline name / pipeline_id: uniprot_idmapping
- Primary keys: ['target_id']
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold scd2
- Write mode (Silver/Gold): MERGE(default)/scd2

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле              | Тип                                                                                                                                                                                                                                                                  |                                                                                                                                                                          Nullable | Source field      | Notes          |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | ----------------- | -------------- |
| \_dq_error        | {'checks': [], 'coerce': False, 'description': 'Flag for data quality errors.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                                                               |                                                                                                                                                                           UNKNOWN | \_dq_error        | snapshot-based |
| \_dq_warn         | {'checks': [], 'coerce': False, 'description': 'Flag for data quality warnings.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                                                             |                                                                                                                                                                           UNKNOWN | \_dq_warn         | snapshot-based |
| \_index           | {'checks': [{'name': 'greater_than_or_equal_to', 'type': 'ge'}], 'coerce': False, 'description': 'Sequential index of the record in the pipeline run.', 'dtype': 'int64', 'nullable': False, 'required': True, 'unique': False}                                      |                                                                                                                                                                           UNKNOWN | \_index           | snapshot-based |
| \_ingestion_ts    | {'checks': \[{'name': 'str_matches', 'regex': '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?([+-]\\d{2}:\\d{2}                                                                                                                                                | Z)?$'}\], 'coerce': False, 'description': 'Timestamp when the record was ingested (UTC, ISO 8601 format).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False} | UNKNOWN           | \_ingestion_ts |
| \_run_id          | {'checks': [], 'coerce': False, 'description': 'Correlation ID for the pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                                                         |                                                                                                                                                                           UNKNOWN | \_run_id          | snapshot-based |
| \_run_type        | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'Type of pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                                        |                                                                                                                                                                           UNKNOWN | \_run_type        | snapshot-based |
| \_source_batch_id | {'checks': [], 'coerce': False, 'description': 'Batch context ID from the source.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                                                            |                                                                                                                                                                           UNKNOWN | \_source_batch_id | snapshot-based |
| all_mappings      | {'checks': [], 'coerce': False, 'description': 'JSON array of all accessions when multiple mappings found', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                                    |                                                                                                                                                                           UNKNOWN | all_mappings      | snapshot-based |
| annotation_score  | {'checks': [{'name': 'greater_than_or_equal_to', 'type': 'ge'}, {'name': 'less_than_or_equal_to', 'type': 'le'}], 'coerce': True, 'description': 'Quality score 1-5 (5 = best annotated)', 'dtype': 'float64', 'nullable': True, 'required': False, 'unique': False} |                                                                                                                                                                           UNKNOWN | annotation_score  | snapshot-based |
| content_hash      | {'checks': \[{'name': 'str_matches', 'regex': '^[a-f0-9]{64}$'}\], 'coerce': False, 'description': 'SHA256 hash of canonical record representation (64 hex chars).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                           |                                                                                                                                                                           UNKNOWN | content_hash      | snapshot-based |
| entity_id         | {'checks': [], 'coerce': False, 'description': 'Unique business identifier for the entity.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                                                   |                                                                                                                                                                           UNKNOWN | entity_id         | snapshot-based |
| gene_primary      | {'checks': [], 'coerce': False, 'description': 'Primary gene name', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                                                                            |                                                                                                                                                                           UNKNOWN | gene_primary      | snapshot-based |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/uniprot/idmapping.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: [].
- Merge key correctness: ['target_id'].

4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: scd2 (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле                | Тип                | Nullable | Semantic role | Breaking risk |
| ------------------- | ------------------ | -------: | ------------- | ------------- |
| entity_id           | string             |       No | business      | High          |
| content_hash        | string             |       No | business      | High          |
| target_id           | string             |       No | business      | High          |
| uniprot_accession   | ['string', 'null'] |      Yes | business      | Medium        |
| mapping_status      | string             |       No | business      | High          |
| uniprot_entry_name  | ['string', 'null'] |      Yes | business      | Medium        |
| organism_scientific | ['string', 'null'] |      Yes | business      | Medium        |
| organism_common     | ['string', 'null'] |      Yes | business      | Medium        |
| taxonomy_id         | ['number', 'null'] |      Yes | business      | Medium        |
| protein_name        | ['string', 'null'] |      Yes | business      | Medium        |
| gene_primary        | ['string', 'null'] |      Yes | business      | Medium        |
| sequence_length     | ['number', 'null'] |      Yes | business      | Medium        |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/uniprot/idmapping.yaml`
- `tests/contract/silver_schemas/snapshots/uniprot_idmapping_schema.json`
- `docs/04-reference/contracts/gold/uniprot_idmapping_v1.0.json`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

### 26. uniprot_protein

1. Общая информация

- Provider: uniprot
- Entity: protein
- Pipeline name / pipeline_id: uniprot_protein
- Primary keys: ['accession']
- Loading strategy: Bronze append-only → Silver MERGE(default) → Gold scd2
- Write mode (Silver/Gold): MERGE(default)/scd2

2. Bronze Layer

- Формат хранения: JSONL + zstd (архитектурный стандарт), фактическая выборка N>=200 по большинству pipeline в репозитории недоступна → INFERRED.
- Структура записи:
  - Минимальный пример JSON (INFERRED): `{ "source_id": "...", "payload": {...}, "_run_id": "...", "_ingestion_ts": "..." }`
  - Ключевые JSON paths: `$.payload.*`, `$._run_id`, `$._run_type`, `$._source_batch_id`, `$._ingestion_ts`, `$._index`.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error`.
- Потенциальный schema drift: MEDIUM/HIGH для nested payload.
- Проблемы:
  - неструктурированные поля: `payload`/JSON blobs (INFERRED)
  - нестабильные типы: nullable numeric
  - nested JSON: списки/объекты (authors, crossrefs, properties)

3. Silver Schema

| Поле                 | Тип                                                                                                                                                                                                                             |                                                                                                                                                                          Nullable | Source field         | Notes          |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | -------------------- | -------------- |
| \_dq_error           | {'checks': [], 'coerce': False, 'description': 'Flag for data quality errors.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                          |                                                                                                                                                                           UNKNOWN | \_dq_error           | snapshot-based |
| \_dq_warn            | {'checks': [], 'coerce': False, 'description': 'Flag for data quality warnings.', 'dtype': 'bool', 'nullable': False, 'required': True, 'unique': False}                                                                        |                                                                                                                                                                           UNKNOWN | \_dq_warn            | snapshot-based |
| \_index              | {'checks': [{'name': 'greater_than_or_equal_to', 'type': 'ge'}], 'coerce': False, 'description': 'Sequential index of the record in the pipeline run.', 'dtype': 'int64', 'nullable': False, 'required': True, 'unique': False} |                                                                                                                                                                           UNKNOWN | \_index              | snapshot-based |
| \_ingestion_ts       | {'checks': \[{'name': 'str_matches', 'regex': '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?([+-]\\d{2}:\\d{2}                                                                                                           | Z)?$'}\], 'coerce': False, 'description': 'Timestamp when the record was ingested (UTC, ISO 8601 format).', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False} | UNKNOWN              | \_ingestion_ts |
| \_run_id             | {'checks': [], 'coerce': False, 'description': 'Correlation ID for the pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                                    |                                                                                                                                                                           UNKNOWN | \_run_id             | snapshot-based |
| \_run_type           | {'checks': [{'name': 'isin', 'type': 'isin'}], 'coerce': False, 'description': 'Type of pipeline run.', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                                   |                                                                                                                                                                           UNKNOWN | \_run_type           | snapshot-based |
| \_source_batch_id    | {'checks': [], 'coerce': False, 'description': 'Batch context ID from the source.', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                       |                                                                                                                                                                           UNKNOWN | \_source_batch_id    | snapshot-based |
| accession            | {'checks': [{'name': 'accession_format'}], 'coerce': False, 'description': 'UniProt primary accession (PK)', 'dtype': 'str', 'nullable': False, 'required': True, 'unique': False}                                              |                                                                                                                                                                           UNKNOWN | accession            | snapshot-based |
| acetylation          | {'checks': [], 'coerce': False, 'description': 'JSON array of acetylation sites', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                         |                                                                                                                                                                           UNKNOWN | acetylation          | snapshot-based |
| active_sites         | {'checks': [], 'coerce': False, 'description': 'JSON array of active site features', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                      |                                                                                                                                                                           UNKNOWN | active_sites         | snapshot-based |
| activity_regulation  | {'checks': [], 'coerce': False, 'description': 'JSON array of activity regulation info', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                                  |                                                                                                                                                                           UNKNOWN | activity_regulation  | snapshot-based |
| alternative_products | {'checks': [], 'coerce': False, 'description': 'JSON array of alternative splicing/isoforms', 'dtype': 'str', 'nullable': True, 'required': False, 'unique': False}                                                             |                                                                                                                                                                           UNKNOWN | alternative_products | snapshot-based |

Анализ:

- Типы (int→float coercion?): риск есть при nullable-int в pandas/arrow цепочке.
- Nullable consistency: частично UNKNOWN (в snapshots nullable не хранится).
- DQ flags / checks: externalized DQ config `configs/quality/entities/uniprot/protein.yaml` + `_dq_warn/_dq_error`.
- Hash exclusions: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_warn`, `_dq_error`, `_source_batch_id`, `_index`.
- Ordering policy: system fields prefix, business fields, DQ suffix.
- Schema drift tolerance: Silver soft-validation с мониторингом drift метрик.
- Partition keys: ['organism'].
- Merge key correctness: ['accession'].

4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: scd2 (SCD2 per-entity часто MISSING/UNKNOWN).
- Стабильность API: строгая валидация по ADR-018.
- Backward compatibility: через versioned contracts (`*_v1.0.json`).
- Breaking risk: High для type/remove/rename required и key/granularity изменений.

| Поле                | Тип                | Nullable | Semantic role | Breaking risk |
| ------------------- | ------------------ | -------: | ------------- | ------------- |
| entity_id           | string             |       No | business      | High          |
| content_hash        | string             |       No | business      | High          |
| accession           | string             |       No | business      | High          |
| entry_name          | ['string', 'null'] |      Yes | business      | Medium        |
| active_sites        | ['string', 'null'] |      Yes | business      | Medium        |
| binding_sites       | ['string', 'null'] |      Yes | business      | Medium        |
| domains             | ['string', 'null'] |      Yes | business      | Medium        |
| features_json       | ['string', 'null'] |      Yes | business      | Medium        |
| activity_regulation | ['string', 'null'] |      Yes | business      | Medium        |
| catalytic_activity  | ['string', 'null'] |      Yes | business      | Medium        |
| disease_involvement | ['string', 'null'] |      Yes | business      | Medium        |
| function_comment    | ['string', 'null'] |      Yes | business      | Medium        |

5. Domain ↔ Schema соответствие

- 1:1 mapping? Частично (transformer + domain entity + schema), не полностью machine-readable.
- Поля отсутствуют в доменной модели? Есть технические metadata-поля, добавляемые в pipeline/writer.
- Поля есть в домене, но не в таблице? Возможны для nested/auxiliary, требуется automated diff.
- Нарушение Single Source of Truth? Частичное: определения распределены по Pandera/PyArrow/Gold contract/YAML.
  Evidence:
- `configs/pipelines/uniprot/protein.yaml`
- `tests/contract/silver_schemas/snapshots/uniprot_protein_schema.json`
- `docs/04-reference/contracts/gold/uniprot_protein_v1.0.json`
- `src/bioetl/composition/factories/pipeline_factories.py`
- `src/bioetl/infrastructure/schemas/silver.py`
- `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`

II. Архитектурные проблемы

| ID   | Pipeline                         | Категория                | Проблема                                                                               | Риск   | Приоритет |
| ---- | -------------------------------- | ------------------------ | -------------------------------------------------------------------------------------- | ------ | --------- |
| A-01 | ALL                              | Schema duplication       | Pandera + PyArrow + Gold JSON contract дублируют описание полей без единого генератора | High   | P1        |
| A-02 | ALL                              | Nullable ambiguity       | Nullable не полностью трассируем в тестовых snapshots Silver                           | High   | P1        |
| A-03 | ALL                              | Content hash instability | Риск различий null/missing/nested canonicalization при drift                           | Medium | P2        |
| A-04 | chembl_publication\*             | Inconsistent naming      | publication/document naming shim создает скрытое связывание                            | Medium | P2        |
| A-05 | composite\_\*                    | Hidden coupling          | configs/pipelines/composite/\* присутствуют, но в factory registry не зарегистрированы | High   | P1        |
| A-06 | ALL                              | Domain drift             | Явная pair-matrix domain↔schema↔config (ADR-034) неполная                              | High   | P1        |
| A-07 | pubchem_compound/uniprot_protein | Over-denormalization     | Широкие записи с JSON-string полями осложняют типовую стабильность                     | Medium | P2        |
| A-08 | ALL                              | Weak primary key         | Часть merge key policy не формализована явно в конфиге                                 | Medium | P2        |

III. Общесистемные проблемы

- Повторяющиеся бизнес/технические поля в разных схемах без единого schema-source.
- Несогласованные типы id/year полей между pipeline (string vs int).
- Output Metadata (ADR-029) реализован моделями, но не везде явно закреплен в pipeline contracts.
- Избыточная ширина таблиц и наличие provider-qualified/JSON-string колонок.
- Nullable-int coercion риск при переходах pandas↔arrow↔delta.
- SCD2 consistency: по многим pipeline gold strategy = append, explicit SCD2 правила MISSING/UNKNOWN.
- Partition strategy неоднородна (в одних pipeline есть partition_by, в других пусто).

IV. План улучшений

1. Немедленные улучшения (Low Risk)

- В CI генерировать per-pipeline schema manifest (Pandera/PyArrow/Gold/nullable/order).
  - Impact: высокий; Breaking / Non-breaking: Non-breaking; Нужен ли ADR: Нет; Миграционная стратегия: gradual warn→fail.
- Добавить automated Bronze shape profiler (N>=200, JSON paths/types/presence).
  - Impact: высокий; Breaking / Non-breaking: Non-breaking; Нужен ли ADR: Нет; Миграционная стратегия: nightly artifacts.

2. Среднесрочные улучшения (Refactoring Phase)

- Ввести единый DSL/registry для генерации Silver+Gold схем и проверок ADR-034 pairs.
  - Impact: высокий; Breaking / Non-breaking: Non-breaking (internal); Нужен ли ADR: Да; Миграционная стратегия: dual-source, parity tests.
- Формализовать rename chains в явных mapping specs per pipeline.
  - Impact: средний; Breaking / Non-breaking: Non-breaking; Нужен ли ADR: Да; Миграционная стратегия: adapters over legacy mappings.

3. Архитектурные изменения (Breaking Phase)

- Унифицировать типы ключевых полей и выпустить Gold v2 contracts.
  - Impact: высокий; Breaking / Non-breaking: Breaking; Нужен ли ADR: Да; Миграционная стратегия: version bump + backfill + compatibility views.
- Явно определить SCD2 для историзуемых сущностей.
  - Impact: высокий; Breaking / Non-breaking: Breaking; Нужен ли ADR: Да; Миграционная стратегия: phased dual-write (`current/history`).

V. Target Schema Architecture (Целевая модель)

- Стандартизированная Bronze: raw payload + обязательные metadata + shape-profile артефакт.
- Унифицированный Silver contract: canonical order, explicit nullable/checks/keys/partition.
- Строгий Gold API contract: semver + strict validation (ADR-018) + compatibility policy.
- Единая metadata policy по ADR-029 для Bronze/Silver/Gold outputs.
- Унифицированная key strategy: provider-scoped PK + formal merge keys + collision policy.
- Типовая структура таблиц: system prefix → business core → enrichment blocks → DQ suffix.

Критерии качества схем (в конце, чеклистом):

- [ ] Нет дублирования бизнес-полей.
- [ ] Типы стабильны между слоями.
- [ ] Nullable политика консистентна.
- [ ] Primary key семантически корректен.
- [ ] Content Hash детерминирован.
- [ ] Нет hidden coupling между пайплайнами.
- [ ] Breaking изменения контролируемы.
- [ ] Schema drift управляем.
