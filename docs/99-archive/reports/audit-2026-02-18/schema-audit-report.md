# BioETL Schema Audit Report (RID-BIOETL-SCHEMA-AUDIT-20260218-015009)

## I. Карта схем пайплайна

### chembl_activity

#### 1. Общая информация

- Provider: chembl
- Entity: activity
- Pipeline name / pipeline_id: chembl_activity
- Primary keys: ['activity_id']
- Loading strategy: Silver `merge(default)`, Gold `append`
- Write mode (Silver/Gold): `merge(default)` / `append`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `METADATA_ONLY`.
  - Ключевые JSON paths (из schema_snapshot metadata): action_type, activity_comment, activity_id, activity_properties, assay_chembl_id, assay_description, assay_type, assay_variant_accession, assay_variant_mutation, bao_endpoint, bao_format, bao_label ...
- Поля метаданных: \_run_id/\_run_type/\_source_batch_id/\_ingestion_ts/\_index/content_hash/entity_id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity_id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content_hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \_run_id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \_dq_warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \_dq_error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/activity.yaml`.
- Hash exclusions: meta-fields из domain.constants.META_FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on_schema_mismatch=evolve (base config).
- Partition keys: silver=MISSING, gold=MISSING.
- Merge key correctness: uses primary_keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `append`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле           | Тип                | Nullable | Semantic role  | Breaking risk |
| -------------- | ------------------ | -------: | -------------- | ------------- |
| entity_id      | string             |      Нет | contract field | Высокий       |
| content_hash   | string             |      Нет | contract field | Высокий       |
| activity_id    | string             |      Нет | contract field | Высокий       |
| molecule_id    | string             |      Нет | contract field | Высокий       |
| target_id      | ['string', 'null'] |       Да | contract field | Средний       |
| assay_id       | ['string', 'null'] |       Да | contract field | Средний       |
| publication_id | ['string', 'null'] |       Да | contract field | Средний       |
| record_id      | ['number', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column_groups: []`).

Evidence:

- `configs/pipelines/chembl/activity.yaml`
- `configs/schemas/chembl/activity.yaml`
- `configs/quality/entities/chembl/activity.yaml`
- `docs/04-reference/contracts/gold/chembl_activity_v1.0.json`
- `data/output/bronze/chembl/activity`

### chembl_assay

#### 1. Общая информация

- Provider: chembl
- Entity: assay
- Pipeline name / pipeline_id: chembl_assay
- Primary keys: ['assay_id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `METADATA_ONLY`.
  - Ключевые JSON paths (из schema_snapshot metadata): aidx, assay_category, assay_cell_type, assay_chembl_id, assay_classifications, assay_group, assay_organism, assay_parameters, assay_strain, assay_subcellular_fraction, assay_tax_id, assay_test_type ...
- Поля метаданных: \_run_id/\_run_type/\_source_batch_id/\_ingestion_ts/\_index/content_hash/entity_id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity_id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content_hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \_run_id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \_dq_warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \_dq_error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/assay.yaml`.
- Hash exclusions: meta-fields из domain.constants.META_FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on_schema_mismatch=evolve (base config).
- Partition keys: silver=['assay_type'], gold=MISSING.
- Merge key correctness: uses primary_keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле           | Тип                | Nullable | Semantic role  | Breaking risk |
| -------------- | ------------------ | -------: | -------------- | ------------- |
| entity_id      | string             |      Нет | contract field | Высокий       |
| content_hash   | string             |      Нет | contract field | Высокий       |
| assay_id       | string             |      Нет | contract field | Высокий       |
| target_id      | ['string', 'null'] |       Да | contract field | Средний       |
| publication_id | ['string', 'null'] |       Да | contract field | Средний       |
| cell_id        | ['string', 'null'] |       Да | contract field | Средний       |
| tissue_id      | ['string', 'null'] |       Да | contract field | Средний       |
| src_id         | ['number', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column_groups: []`).

Evidence:

- `configs/pipelines/chembl/assay.yaml`
- `configs/schemas/chembl/assay.yaml`
- `configs/quality/entities/chembl/assay.yaml`
- `docs/04-reference/contracts/gold/chembl_assay_v1.0.json`
- `data/output/bronze/chembl/assay`

### chembl_assay_parameters

#### 1. Общая информация

- Provider: chembl
- Entity: assay_parameters
- Pipeline name / pipeline_id: chembl_assay_parameters
- Primary keys: ['assay_param_id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \_run_id/\_run_type/\_source_batch_id/\_ingestion_ts/\_index/content_hash/entity_id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity_id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content_hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \_run_id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \_dq_warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \_dq_error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/assay_parameters.yaml`.
- Hash exclusions: meta-fields из domain.constants.META_FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on_schema_mismatch=evolve (base config).
- Partition keys: silver=['type'], gold=MISSING.
- Merge key correctness: uses primary_keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле           | Тип                | Nullable | Semantic role  | Breaking risk |
| -------------- | ------------------ | -------: | -------------- | ------------- |
| entity_id      | string             |      Нет | contract field | Высокий       |
| content_hash   | string             |      Нет | contract field | Высокий       |
| assay_param_id | number             |      Нет | contract field | Высокий       |
| assay_id       | string             |      Нет | contract field | Высокий       |
| type           | string             |      Нет | contract field | Высокий       |
| relation       | ['string', 'null'] |       Да | contract field | Средний       |
| value          | ['number', 'null'] |       Да | contract field | Средний       |
| units          | ['string', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column_groups: []`).

Evidence:

- `configs/pipelines/chembl/assay_parameters.yaml`
- `configs/schemas/chembl/assay_parameters.yaml`
- `configs/quality/entities/chembl/assay_parameters.yaml`
- `docs/04-reference/contracts/gold/chembl_assay_parameters_v1.0.json`
- `data/output/bronze/chembl/assay_parameters`

### chembl_cell_line

#### 1. Общая информация

- Provider: chembl
- Entity: cell_line
- Pipeline name / pipeline_id: chembl_cell_line
- Primary keys: ['cell_id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `METADATA_ONLY`.
  - Ключевые JSON paths (из schema_snapshot metadata): cell_chembl_id, cell_description, cell_id, cell_name, cell_source_organism, cell_source_tax_id, cell_source_tissue, cellosaurus_id, cl_lincs_id, clo_id, efo_id
- Поля метаданных: \_run_id/\_run_type/\_source_batch_id/\_ingestion_ts/\_index/content_hash/entity_id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity_id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content_hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \_run_id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \_dq_warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \_dq_error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/cell_line.yaml`.
- Hash exclusions: meta-fields из domain.constants.META_FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on_schema_mismatch=evolve (base config).
- Partition keys: silver=MISSING, gold=MISSING.
- Merge key correctness: uses primary_keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле                    | Тип                | Nullable | Semantic role  | Breaking risk |
| ----------------------- | ------------------ | -------: | -------------- | ------------- |
| entity_id               | string             |      Нет | contract field | Высокий       |
| content_hash            | string             |      Нет | contract field | Высокий       |
| cell_id                 | string             |      Нет | contract field | Высокий       |
| cell_name               | string             |      Нет | contract field | Высокий       |
| cell_description        | ['string', 'null'] |       Да | contract field | Средний       |
| cell_source_tissue      | ['string', 'null'] |       Да | contract field | Средний       |
| cell_source_organism    | ['string', 'null'] |       Да | contract field | Средний       |
| cell_source_taxonomy_id | ['number', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column_groups: []`).

Evidence:

- `configs/pipelines/chembl/cell_line.yaml`
- `configs/schemas/chembl/cell_line.yaml`
- `configs/quality/entities/chembl/cell_line.yaml`
- `docs/04-reference/contracts/gold/chembl_cell_line_v1.0.json`
- `data/output/bronze/chembl/cell_line`

### chembl_compound_record

#### 1. Общая информация

- Provider: chembl
- Entity: compound_record
- Pipeline name / pipeline_id: chembl_compound_record
- Primary keys: ['record_id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `METADATA_ONLY`.
  - Ключевые JSON paths (из schema_snapshot metadata): compound_key, compound_name, document_chembl_id, molecule_chembl_id, record_id, src_id
- Поля метаданных: \_run_id/\_run_type/\_source_batch_id/\_ingestion_ts/\_index/content_hash/entity_id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity_id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content_hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \_run_id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \_dq_warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \_dq_error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/compound_record.yaml`.
- Hash exclusions: meta-fields из domain.constants.META_FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on_schema_mismatch=evolve (base config).
- Partition keys: silver=MISSING, gold=MISSING.
- Merge key correctness: uses primary_keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле           | Тип                | Nullable | Semantic role  | Breaking risk |
| -------------- | ------------------ | -------: | -------------- | ------------- |
| entity_id      | string             |      Нет | contract field | Высокий       |
| content_hash   | string             |      Нет | contract field | Высокий       |
| record_id      | number             |      Нет | contract field | Высокий       |
| molecule_id    | string             |      Нет | contract field | Высокий       |
| publication_id | string             |      Нет | contract field | Высокий       |
| compound_key   | ['string', 'null'] |       Да | contract field | Средний       |
| compound_name  | ['string', 'null'] |       Да | contract field | Средний       |
| src_id         | number             |      Нет | contract field | Высокий       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column_groups: []`).

Evidence:

- `configs/pipelines/chembl/compound_record.yaml`
- `configs/schemas/chembl/compound_record.yaml`
- `configs/quality/entities/chembl/compound_record.yaml`
- `docs/04-reference/contracts/gold/chembl_compound_record_v1.0.json`
- `data/output/bronze/chembl/compound_record`

### chembl_molecule

#### 1. Общая информация

- Provider: chembl
- Entity: molecule
- Pipeline name / pipeline_id: chembl_molecule
- Primary keys: ['molecule_id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \_run_id/\_run_type/\_source_batch_id/\_ingestion_ts/\_index/content_hash/entity_id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity_id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content_hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \_run_id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \_dq_warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \_dq_error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/molecule.yaml`.
- Hash exclusions: meta-fields из domain.constants.META_FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on_schema_mismatch=evolve (base config).
- Partition keys: silver=['molecule_type'], gold=MISSING.
- Merge key correctness: uses primary_keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле           | Тип                | Nullable | Semantic role  | Breaking risk |
| -------------- | ------------------ | -------: | -------------- | ------------- |
| entity_id      | string             |      Нет | contract field | Высокий       |
| content_hash   | string             |      Нет | contract field | Высокий       |
| molecule_id    | string             |      Нет | contract field | Высокий       |
| pref_name      | ['string', 'null'] |       Да | contract field | Средний       |
| molecule_type  | ['string', 'null'] |       Да | contract field | Средний       |
| structure_type | ['string', 'null'] |       Да | contract field | Средний       |
| max_phase      | ['number', 'null'] |       Да | contract field | Средний       |
| first_approval | ['number', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column_groups: []`).

Evidence:

- `configs/pipelines/chembl/molecule.yaml`
- `configs/schemas/chembl/molecule.yaml`
- `configs/quality/entities/chembl/molecule.yaml`
- `docs/04-reference/contracts/gold/chembl_molecule_v1.0.json`
- `data/output/bronze/chembl/molecule`

### chembl_protein_class

#### 1. Общая информация

- Provider: chembl
- Entity: protein_class
- Pipeline name / pipeline_id: chembl_protein_class
- Primary keys: ['protein_class_id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \_run_id/\_run_type/\_source_batch_id/\_ingestion_ts/\_index/content_hash/entity_id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity_id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content_hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \_run_id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \_dq_warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \_dq_error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/protein_class.yaml`.
- Hash exclusions: meta-fields из domain.constants.META_FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on_schema_mismatch=evolve (base config).
- Partition keys: silver=['class_level'], gold=MISSING.
- Merge key correctness: uses primary_keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле               | Тип                | Nullable | Semantic role  | Breaking risk |
| ------------------ | ------------------ | -------: | -------------- | ------------- |
| entity_id          | string             |      Нет | contract field | Высокий       |
| content_hash       | string             |      Нет | contract field | Высокий       |
| protein_class_id   | number             |      Нет | contract field | Высокий       |
| parent_id          | ['number', 'null'] |       Да | contract field | Средний       |
| class_level        | ['number', 'null'] |       Да | contract field | Средний       |
| pref_name          | ['string', 'null'] |       Да | contract field | Средний       |
| short_name         | ['string', 'null'] |       Да | contract field | Средний       |
| protein_class_desc | ['string', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column_groups: []`).

Evidence:

- `configs/pipelines/chembl/protein_class.yaml`
- `configs/schemas/chembl/protein_class.yaml`
- `configs/quality/entities/chembl/protein_class.yaml`
- `docs/04-reference/contracts/gold/chembl_protein_class_v1.0.json`
- `data/output/bronze/chembl/protein_class`

### chembl_publication

#### 1. Общая информация

- Provider: chembl
- Entity: publication
- Pipeline name / pipeline_id: chembl_publication
- Primary keys: ['publication_id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \_run_id/\_run_type/\_source_batch_id/\_ingestion_ts/\_index/content_hash/entity_id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity_id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content_hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \_run_id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \_dq_warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \_dq_error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/publication.yaml`.
- Hash exclusions: meta-fields из domain.constants.META_FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on_schema_mismatch=evolve (base config).
- Partition keys: silver=MISSING, gold=MISSING.
- Merge key correctness: uses primary_keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: MISSING
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле | Тип     | Nullable | Semantic role                  | Breaking risk |
| ---- | ------- | -------: | ------------------------------ | ------------- |
| GAP  | UNKNOWN |  UNKNOWN | Contract missing or unreadable | Высокий       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column_groups: []`).

Evidence:

- `configs/pipelines/chembl/publication.yaml`
- `configs/schemas/chembl/publication.yaml`
- `configs/quality/entities/chembl/publication.yaml`
- `MISSING`
- `data/output/bronze/chembl/publication`

### chembl_publication_similarity

#### 1. Общая информация

- Provider: chembl
- Entity: publication_similarity
- Pipeline name / pipeline_id: chembl_publication_similarity
- Primary keys: ['sim_id']
- Loading strategy: Silver `merge(default)`, Gold `overwrite`
- Write mode (Silver/Gold): `merge(default)` / `overwrite`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \_run_id/\_run_type/\_source_batch_id/\_ingestion_ts/\_index/content_hash/entity_id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity_id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content_hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \_run_id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \_dq_warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \_dq_error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/publication_similarity.yaml`.
- Hash exclusions: meta-fields из domain.constants.META_FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on_schema_mismatch=evolve (base config).
- Partition keys: silver=[], gold=MISSING.
- Merge key correctness: uses primary_keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: MISSING
- SCD2 / overwrite / append: `overwrite`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле | Тип     | Nullable | Semantic role                  | Breaking risk |
| ---- | ------- | -------: | ------------------------------ | ------------- |
| GAP  | UNKNOWN |  UNKNOWN | Contract missing or unreadable | Высокий       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column_groups: []`).

Evidence:

- `configs/pipelines/chembl/publication_similarity.yaml`
- `configs/schemas/chembl/publication_similarity.yaml`
- `configs/quality/entities/chembl/publication_similarity.yaml`
- `MISSING`
- `data/output/bronze/chembl/publication_similarity`

### chembl_publication_term

#### 1. Общая информация

- Provider: chembl
- Entity: publication_term
- Pipeline name / pipeline_id: chembl_publication_term
- Primary keys: ['entity_id']
- Loading strategy: Silver `merge(default)`, Gold `overwrite`
- Write mode (Silver/Gold): `merge(default)` / `overwrite`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \_run_id/\_run_type/\_source_batch_id/\_ingestion_ts/\_index/content_hash/entity_id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity_id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content_hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \_run_id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \_dq_warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \_dq_error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/publication_term.yaml`.
- Hash exclusions: meta-fields из domain.constants.META_FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on_schema_mismatch=evolve (base config).
- Partition keys: silver=['term_type'], gold=MISSING.
- Merge key correctness: uses primary_keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: MISSING
- SCD2 / overwrite / append: `overwrite`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле | Тип     | Nullable | Semantic role                  | Breaking risk |
| ---- | ------- | -------: | ------------------------------ | ------------- |
| GAP  | UNKNOWN |  UNKNOWN | Contract missing or unreadable | Высокий       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column_groups: []`).

Evidence:

- `configs/pipelines/chembl/publication_term.yaml`
- `configs/schemas/chembl/publication_term.yaml`
- `configs/quality/entities/chembl/publication_term.yaml`
- `MISSING`
- `data/output/bronze/chembl/publication_term`

### chembl_subcellular_fraction

#### 1. Общая информация

- Provider: chembl
- Entity: subcellular_fraction
- Pipeline name / pipeline_id: chembl_subcellular_fraction
- Primary keys: ['entity_id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \_run_id/\_run_type/\_source_batch_id/\_ingestion_ts/\_index/content_hash/entity_id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity_id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content_hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \_run_id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \_dq_warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \_dq_error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/subcellular_fraction.yaml`.
- Hash exclusions: meta-fields из domain.constants.META_FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on_schema_mismatch=evolve (base config).
- Partition keys: silver=MISSING, gold=MISSING.
- Merge key correctness: uses primary_keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле                 | Тип                | Nullable | Semantic role  | Breaking risk |
| -------------------- | ------------------ | -------: | -------------- | ------------- |
| entity_id            | string             |      Нет | contract field | Высокий       |
| content_hash         | string             |      Нет | contract field | Высокий       |
| subcellular_fraction | string             |      Нет | contract field | Высокий       |
| assay_count          | ['number', 'null'] |       Да | contract field | Средний       |
| example_assay_id     | ['string', 'null'] |       Да | contract field | Средний       |
| \_run_id             | string             |      Нет | contract field | Высокий       |
| \_run_type           | string             |      Нет | contract field | Высокий       |
| \_source_batch_id    | ['string', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column_groups: []`).

Evidence:

- `configs/pipelines/chembl/subcellular_fraction.yaml`
- `configs/schemas/chembl/subcellular_fraction.yaml`
- `configs/quality/entities/chembl/subcellular_fraction.yaml`
- `docs/04-reference/contracts/gold/chembl_subcellular_fraction_v1.0.json`
- `data/output/bronze/chembl/subcellular_fraction`

### chembl_target

#### 1. Общая информация

- Provider: chembl
- Entity: target
- Pipeline name / pipeline_id: chembl_target
- Primary keys: ['target_id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \_run_id/\_run_type/\_source_batch_id/\_ingestion_ts/\_index/content_hash/entity_id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity_id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content_hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \_run_id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \_dq_warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \_dq_error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/target.yaml`.
- Hash exclusions: meta-fields из domain.constants.META_FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on_schema_mismatch=evolve (base config).
- Partition keys: silver=['target_type'], gold=MISSING.
- Merge key correctness: uses primary_keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле               | Тип                 | Nullable | Semantic role  | Breaking risk |
| ------------------ | ------------------- | -------: | -------------- | ------------- |
| entity_id          | string              |      Нет | contract field | Высокий       |
| content_hash       | string              |      Нет | contract field | Высокий       |
| target_id          | string              |      Нет | contract field | Высокий       |
| pref_name          | ['string', 'null']  |       Да | contract field | Средний       |
| target_type        | ['string', 'null']  |       Да | contract field | Средний       |
| organism           | ['string', 'null']  |       Да | contract field | Средний       |
| taxonomy_id        | ['number', 'null']  |       Да | contract field | Средний       |
| species_group_flag | ['boolean', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column_groups: []`).

Evidence:

- `configs/pipelines/chembl/target.yaml`
- `configs/schemas/chembl/target.yaml`
- `configs/quality/entities/chembl/target.yaml`
- `docs/04-reference/contracts/gold/chembl_target_v1.0.json`
- `data/output/bronze/chembl/target`

### chembl_target_component

#### 1. Общая информация

- Provider: chembl
- Entity: target_component
- Pipeline name / pipeline_id: chembl_target_component
- Primary keys: ['component_id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `METADATA_ONLY`.
  - Ключевые JSON paths (из schema_snapshot metadata): accession, component_id, component_type, description, go_slims, organism, protein_classifications, sequence, target_component_synonyms, target_component_xrefs, targets, tax_id
- Поля метаданных: \_run_id/\_run_type/\_source_batch_id/\_ingestion_ts/\_index/content_hash/entity_id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity_id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content_hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \_run_id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \_dq_warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \_dq_error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/target_component.yaml`.
- Hash exclusions: meta-fields из domain.constants.META_FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on_schema_mismatch=evolve (base config).
- Partition keys: silver=['organism'], gold=MISSING.
- Merge key correctness: uses primary_keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле           | Тип                | Nullable | Semantic role  | Breaking risk |
| -------------- | ------------------ | -------: | -------------- | ------------- |
| entity_id      | string             |      Нет | contract field | Высокий       |
| content_hash   | string             |      Нет | contract field | Высокий       |
| component_id   | number             |      Нет | contract field | Высокий       |
| accession      | ['string', 'null'] |       Да | contract field | Средний       |
| component_type | ['string', 'null'] |       Да | contract field | Средний       |
| description    | ['string', 'null'] |       Да | contract field | Средний       |
| organism       | ['string', 'null'] |       Да | contract field | Средний       |
| taxonomy_id    | ['number', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column_groups: []`).

Evidence:

- `configs/pipelines/chembl/target_component.yaml`
- `configs/schemas/chembl/target_component.yaml`
- `configs/quality/entities/chembl/target_component.yaml`
- `docs/04-reference/contracts/gold/chembl_target_component_v1.0.json`
- `data/output/bronze/chembl/target_component`

### chembl_tissue

#### 1. Общая информация

- Provider: chembl
- Entity: tissue
- Pipeline name / pipeline_id: chembl_tissue
- Primary keys: ['tissue_id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \_run_id/\_run_type/\_source_batch_id/\_ingestion_ts/\_index/content_hash/entity_id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity_id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content_hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \_run_id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \_dq_warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \_dq_error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/tissue.yaml`.
- Hash exclusions: meta-fields из domain.constants.META_FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on_schema_mismatch=evolve (base config).
- Partition keys: silver=MISSING, gold=MISSING.
- Merge key correctness: uses primary_keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле       | Тип                | Nullable | Semantic role  | Breaking risk |
| ---------- | ------------------ | -------: | -------------- | ------------- |
| tissue_id  | string             |      Нет | contract field | Высокий       |
| pref_name  | string             |      Нет | contract field | Высокий       |
| bto_id     | ['string', 'null'] |       Да | contract field | Средний       |
| caloha_id  | ['string', 'null'] |       Да | contract field | Средний       |
| efo_id     | ['string', 'null'] |       Да | contract field | Средний       |
| uberon_id  | ['string', 'null'] |       Да | contract field | Средний       |
| \_run_id   | string             |      Нет | contract field | Высокий       |
| \_run_type | string             |      Нет | contract field | Высокий       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column_groups: []`).

Evidence:

- `configs/pipelines/chembl/tissue.yaml`
- `configs/schemas/chembl/tissue.yaml`
- `configs/quality/entities/chembl/tissue.yaml`
- `docs/04-reference/contracts/gold/chembl_tissue_v1.0.json`
- `data/output/bronze/chembl/tissue`

### crossref_publication

#### 1. Общая информация

- Provider: crossref
- Entity: publication
- Pipeline name / pipeline_id: crossref_publication
- Primary keys: ['doi']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \_run_id/\_run_type/\_source_batch_id/\_ingestion_ts/\_index/content_hash/entity_id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity_id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content_hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \_run_id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \_dq_warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \_dq_error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/crossref/publication.yaml`.
- Hash exclusions: meta-fields из domain.constants.META_FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on_schema_mismatch=evolve (base config).
- Partition keys: silver=MISSING, gold=MISSING.
- Merge key correctness: uses primary_keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле         | Тип                | Nullable | Semantic role  | Breaking risk |
| ------------ | ------------------ | -------: | -------------- | ------------- |
| entity_id    | string             |      Нет | contract field | Высокий       |
| content_hash | string             |      Нет | contract field | Высокий       |
| doi          | string             |      Нет | contract field | Высокий       |
| title        | ['string', 'null'] |       Да | contract field | Средний       |
| authors      | ['string', 'null'] |       Да | contract field | Средний       |
| journal      | ['string', 'null'] |       Да | contract field | Средний       |
| issn         | ['string', 'null'] |       Да | contract field | Средний       |
| issn_list    | ['string', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column_groups: []`).

Evidence:

- `configs/pipelines/crossref/publication.yaml`
- `configs/schemas/crossref/publication.yaml`
- `configs/quality/entities/crossref/publication.yaml`
- `docs/04-reference/contracts/gold/crossref_publication_v1.0.json`
- `data/output/bronze/crossref/publication`

### openalex_publication

#### 1. Общая информация

- Provider: openalex
- Entity: publication
- Pipeline name / pipeline_id: openalex_publication
- Primary keys: ['openalex_id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \_run_id/\_run_type/\_source_batch_id/\_ingestion_ts/\_index/content_hash/entity_id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity_id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content_hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \_run_id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \_dq_warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \_dq_error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/openalex/publication.yaml`.
- Hash exclusions: meta-fields из domain.constants.META_FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on_schema_mismatch=evolve (base config).
- Partition keys: silver=MISSING, gold=MISSING.
- Merge key correctness: uses primary_keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле         | Тип                | Nullable | Semantic role  | Breaking risk |
| ------------ | ------------------ | -------: | -------------- | ------------- |
| entity_id    | string             |      Нет | contract field | Высокий       |
| content_hash | string             |      Нет | contract field | Высокий       |
| openalex_id  | string             |      Нет | contract field | Высокий       |
| doi          | ['string', 'null'] |       Да | contract field | Средний       |
| pmid         | ['string', 'null'] |       Да | contract field | Средний       |
| title        | ['string', 'null'] |       Да | contract field | Средний       |
| abstract     | ['string', 'null'] |       Да | contract field | Средний       |
| authors      | ['string', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column_groups: []`).

Evidence:

- `configs/pipelines/openalex/publication.yaml`
- `configs/schemas/openalex/publication.yaml`
- `configs/quality/entities/openalex/publication.yaml`
- `docs/04-reference/contracts/gold/openalex_publication_v1.0.json`
- `data/output/bronze/openalex/publication`

### pubchem_compound

#### 1. Общая информация

- Provider: pubchem
- Entity: compound
- Pipeline name / pipeline_id: pubchem_compound
- Primary keys: ['molecule_id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \_run_id/\_run_type/\_source_batch_id/\_ingestion_ts/\_index/content_hash/entity_id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity_id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content_hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \_run_id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \_dq_warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \_dq_error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/pubchem/compound.yaml`.
- Hash exclusions: meta-fields из domain.constants.META_FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on_schema_mismatch=evolve (base config).
- Partition keys: silver=['batch_date'], gold=MISSING.
- Merge key correctness: uses primary_keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле              | Тип                | Nullable | Semantic role  | Breaking risk |
| ----------------- | ------------------ | -------: | -------------- | ------------- |
| entity_id         | string             |      Нет | contract field | Высокий       |
| molecule_id       | string             |      Нет | contract field | Высокий       |
| molecular_formula | ['string', 'null'] |       Да | contract field | Средний       |
| molecular_weight  | ['number', 'null'] |       Да | contract field | Средний       |
| canonical_smiles  | ['string', 'null'] |       Да | contract field | Средний       |
| isomeric_smiles   | ['string', 'null'] |       Да | contract field | Средний       |
| inchi             | ['string', 'null'] |       Да | contract field | Средний       |
| inchi_key         | ['string', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column_groups: []`).

Evidence:

- `configs/pipelines/pubchem/compound.yaml`
- `configs/schemas/pubchem/compound.yaml`
- `configs/quality/entities/pubchem/compound.yaml`
- `docs/04-reference/contracts/gold/pubchem_compound_v1.0.json`
- `data/output/bronze/pubchem/compound`

### pubmed_publication

#### 1. Общая информация

- Provider: pubmed
- Entity: publication
- Pipeline name / pipeline_id: pubmed_publication
- Primary keys: ['pmid']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \_run_id/\_run_type/\_source_batch_id/\_ingestion_ts/\_index/content_hash/entity_id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity_id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content_hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \_run_id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \_dq_warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \_dq_error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/pubmed/publication.yaml`.
- Hash exclusions: meta-fields из domain.constants.META_FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on_schema_mismatch=evolve (base config).
- Partition keys: silver=MISSING, gold=MISSING.
- Merge key correctness: uses primary_keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле                | Тип                 | Nullable | Semantic role  | Breaking risk |
| ------------------- | ------------------- | -------: | -------------- | ------------- |
| entity_id           | string              |      Нет | contract field | Высокий       |
| content_hash        | string              |      Нет | contract field | Высокий       |
| pmid                | string              |      Нет | contract field | Высокий       |
| doi                 | ['string', 'null']  |       Да | contract field | Средний       |
| pmc_id              | ['string', 'null']  |       Да | contract field | Средний       |
| title               | string              |      Нет | contract field | Высокий       |
| abstract            | ['string', 'null']  |       Да | contract field | Средний       |
| abstract_structured | ['boolean', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column_groups: []`).

Evidence:

- `configs/pipelines/pubmed/publication.yaml`
- `configs/schemas/pubmed/publication.yaml`
- `configs/quality/entities/pubmed/publication.yaml`
- `docs/04-reference/contracts/gold/pubmed_publication_v1.0.json`
- `data/output/bronze/pubmed/publication`

### semanticscholar_publication

#### 1. Общая информация

- Provider: semanticscholar
- Entity: publication
- Pipeline name / pipeline_id: semanticscholar_publication
- Primary keys: ['paper_id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \_run_id/\_run_type/\_source_batch_id/\_ingestion_ts/\_index/content_hash/entity_id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity_id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content_hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \_run_id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \_dq_warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \_dq_error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/semanticscholar/publication.yaml`.
- Hash exclusions: meta-fields из domain.constants.META_FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on_schema_mismatch=evolve (base config).
- Partition keys: silver=MISSING, gold=MISSING.
- Merge key correctness: uses primary_keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле         | Тип                | Nullable | Semantic role  | Breaking risk |
| ------------ | ------------------ | -------: | -------------- | ------------- |
| entity_id    | string             |      Нет | contract field | Высокий       |
| content_hash | string             |      Нет | contract field | Высокий       |
| paper_id     | string             |      Нет | contract field | Высокий       |
| doi          | ['string', 'null'] |       Да | contract field | Средний       |
| pmid         | ['string', 'null'] |       Да | contract field | Средний       |
| corpus_id    | ['number', 'null'] |       Да | contract field | Средний       |
| title        | ['string', 'null'] |       Да | contract field | Средний       |
| abstract     | ['string', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column_groups: []`).

Evidence:

- `configs/pipelines/semanticscholar/publication.yaml`
- `configs/schemas/semanticscholar/publication.yaml`
- `configs/quality/entities/semanticscholar/publication.yaml`
- `docs/04-reference/contracts/gold/semanticscholar_publication_v1.0.json`
- `data/output/bronze/semanticscholar/publication`

### uniprot_idmapping

#### 1. Общая информация

- Provider: uniprot
- Entity: idmapping
- Pipeline name / pipeline_id: uniprot_idmapping
- Primary keys: ['target_id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \_run_id/\_run_type/\_source_batch_id/\_ingestion_ts/\_index/content_hash/entity_id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity_id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content_hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \_run_id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \_dq_warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \_dq_error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/uniprot/idmapping.yaml`.
- Hash exclusions: meta-fields из domain.constants.META_FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on_schema_mismatch=evolve (base config).
- Partition keys: silver=[], gold=MISSING.
- Merge key correctness: uses primary_keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле                | Тип                | Nullable | Semantic role  | Breaking risk |
| ------------------- | ------------------ | -------: | -------------- | ------------- |
| entity_id           | string             |      Нет | contract field | Высокий       |
| content_hash        | string             |      Нет | contract field | Высокий       |
| target_id           | string             |      Нет | contract field | Высокий       |
| uniprot_accession   | ['string', 'null'] |       Да | contract field | Средний       |
| mapping_status      | string             |      Нет | contract field | Высокий       |
| uniprot_entry_name  | ['string', 'null'] |       Да | contract field | Средний       |
| organism_scientific | ['string', 'null'] |       Да | contract field | Средний       |
| organism_common     | ['string', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column_groups: []`).

Evidence:

- `configs/pipelines/uniprot/idmapping.yaml`
- `configs/schemas/uniprot/idmapping.yaml`
- `configs/quality/entities/uniprot/idmapping.yaml`
- `docs/04-reference/contracts/gold/uniprot_idmapping_v1.0.json`
- `data/output/bronze/uniprot/idmapping`

### uniprot_protein

#### 1. Общая информация

- Provider: uniprot
- Entity: protein
- Pipeline name / pipeline_id: uniprot_protein
- Primary keys: ['accession']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `METADATA_ONLY`.
  - Ключевые JSON paths (из schema_snapshot metadata): annotationScore, comments, entryAudit, entryType, extraAttributes, features, genes, keywords, lineages, organism, primaryAccession, proteinDescription ...
- Поля метаданных: \_run_id/\_run_type/\_source_batch_id/\_ingestion_ts/\_index/content_hash/entity_id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity_id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content_hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \_run_id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \_dq_warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \_dq_error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/uniprot/protein.yaml`.
- Hash exclusions: meta-fields из domain.constants.META_FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on_schema_mismatch=evolve (base config).
- Partition keys: silver=['organism'], gold=MISSING.
- Merge key correctness: uses primary_keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле          | Тип                | Nullable | Semantic role  | Breaking risk |
| ------------- | ------------------ | -------: | -------------- | ------------- |
| entity_id     | string             |      Нет | contract field | Высокий       |
| content_hash  | string             |      Нет | contract field | Высокий       |
| accession     | string             |      Нет | contract field | Высокий       |
| entry_name    | ['string', 'null'] |       Да | contract field | Средний       |
| active_sites  | ['string', 'null'] |       Да | contract field | Средний       |
| binding_sites | ['string', 'null'] |       Да | contract field | Средний       |
| domains       | ['string', 'null'] |       Да | contract field | Средний       |
| features_json | ['string', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column_groups: []`).

Evidence:

- `configs/pipelines/uniprot/protein.yaml`
- `configs/schemas/uniprot/protein.yaml`
- `configs/quality/entities/uniprot/protein.yaml`
- `docs/04-reference/contracts/gold/uniprot_protein_v1.0.json`
- `data/output/bronze/uniprot/protein`

## II. Архитектурные проблемы

| ID   | Pipeline | Категория                | Проблема                                                                                                                 | Риск   | Приоритет |
| ---- | -------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------ | ------ | --------- |
| A-01 | all      | Schema duplication       | Schema defined in multiple places (Pandera, PyArrow, JSON contract, YAML schema config) without generated SSOT.          | High   | P1        |
| A-02 | all      | Content hash instability | Hash excludes fixed meta-fields but no per-pipeline explicit exclusion spec; drift may alter hashes unexpectedly.        | Medium | P2        |
| A-03 | many     | Domain drift             | Multiple `configs/schemas/*` are empty (`column_groups: []`), violating explicit schema↔domain pairing intent (ADR-034). | High   | P1        |
| A-04 | selected | Nullable ambiguity       | Nullable policy not centrally enforced across Bronze→Silver→Gold contracts.                                              | Medium | P2        |
| A-05 | selected | Inconsistent naming      | publication/document aliases and provider-specific IDs create hidden coupling.                                           | Medium | P2        |

## III. Общесистемные проблемы

- Повторяющиеся поля в схемах: `entity_id`, `content_hash`, `_run_id`, `_dq_warn`, `_dq_error` повторяются во всех слоях без machine-verifiable centralized generator.
- Несогласованные типы между пайплайнами: publication identifiers (`doi`, `pmid`, provider-specific IDs) имеют разный naming и optionality.
- Унифицированные metadata поля ADR-029 partially present, но фактическая проверка полноты по всем pipeline outputs не автоматизирована.
- Нарушения OutputMetadata унификации: в `data/output/bronze/*` доступны только metadata snapshots, не raw JSONL outputs для подтверждения full parity.
- Риск nullable-int coercion: при наличии null в integer-полях и переходах pandas/pyarrow возможен int→float дрейф (не закрыт глобальной политикой).
- SCD2 consistency: gold modes mixed (`append`, `overwrite`, `scd2`) с разным поведением по pipeline.
- Partition strategy несогласована: часть pipelines partitioned, часть нет; rationale часто не документирован в ADR-level decision.

## IV. План улучшений

### 1. Немедленные улучшения (Low Risk)

- Add automated `schema_diff` CI job: Pandera vs PyArrow vs Gold JSON contract. Impact: высокая трассируемость; Breaking: Non-breaking; ADR: No; Migration: add report-only stage.
- Enforce explicit hash input specification per pipeline in config (`hash.include_fields`/`hash.exclude_fields`). Impact: детерминизм; Breaking: Non-breaking initially (warn mode); ADR: Maybe (if mandatory). Migration: phase warn→enforce.
- Populate missing `configs/schemas/*` with at least column groups + aliases. Impact: ADR-034 compliance; Breaking: Non-breaking; ADR: No; Migration: per-pipeline PRs.

### 2. Среднесрочные улучшения (Refactoring Phase)

- Introduce code-generated schemas from SSOT (domain schema registry) for Silver + Gold contracts. Impact: remove duplication; Breaking: Potentially breaking (field order/type); ADR: Yes; Migration: dual-write schema check period.
- Standardize partition policy template per entity cardinality profile. Impact: performance consistency; Breaking: Potentially breaking for path layout; ADR: Yes; Migration: backfill + reader abstraction.

### 3. Архитектурные изменения (Breaking Phase)

- Move to strict Gold compatibility gate (ADR-018 hard fail in CI + runtime). Impact: API stability; Breaking: Breaking for drifted producers; ADR: already exists (extend); Migration: contract version bump policy + deprecation window.
- Formal Domain↔Schema Pair Registry (ADR-034 executable). Impact: eliminates hidden coupling; Breaking: moderate; ADR: Yes (implementation ADR); Migration: register all 21 pipelines then enforce.

## V. Target Schema Architecture (Целевая модель)

- стандартизированная модель Bronze: mandatory raw JSONL artifact + schema profile manifest (paths/types/presence N>=200).
- унифицированный Silver contract: generated Pandera + PyArrow from one schema DSL, fixed column order and nullability matrix.
- строгий Gold API contract: versioned JSON schema + strict runtime validator + compat test suite (ADR-018).
- единый metadata policy: ADR-029 fields mandatory across Bronze/Silver/Gold + automated completeness check.
- унифицированная key strategy: explicit primary key + merge key + provider scope + collision policy in each pipeline config.
- типовая структура таблиц: system prefix, business fields by groups, DQ suffix; partition only by documented cardinality/perf rationale.

### Критерии качества схем (чеклист)

- [ ] Нет дублирования бизнес-полей.
- [ ] Типы стабильны между слоями.
- [ ] Nullable политика консистентна.
- [ ] Primary key семантически корректен.
- [ ] Content Hash детерминирован.
- [ ] Нет hidden coupling между пайплайнами.
- [ ] Breaking изменения контролируемы.
- [ ] Schema drift управляем.
