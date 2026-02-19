# BioETL Schema Audit Report (RID-BIOETL-SCHEMA-AUDIT-20260218-015009)

## I. Карта схем пайплайна

### chembl-activity

#### 1. Общая информация

- Provider: chembl
- Entity: activity
- Pipeline name / pipeline-id: chembl-activity
- Primary keys: ['activity-id']
- Loading strategy: Silver `merge(default)`, Gold `append`
- Write mode (Silver/Gold): `merge(default)` / `append`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `METADATA-ONLY`.
  - Ключевые JSON paths (из schema-snapshot metadata): action-type, activity-comment, activity-id, activity-properties, assay-chembl-id, assay-description, assay-type, assay-variant-accession, assay-variant-mutation, bao-endpoint, bao-format, bao-label ...
- Поля метаданных: \-run-id/\-run-type/\-source-batch-id/\-ingestion-ts/\-index/content-hash/entity-id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity-id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content-hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \-run-id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \-dq-warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \-dq-error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/activity.yaml`.
- Hash exclusions: meta-fields из domain.constants.META-FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on-schema-mismatch=evolve (base config).
- Partition keys: silver=MISSING, gold=MISSING.
- Merge key correctness: uses primary-keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `append`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле           | Тип                | Nullable | Semantic role  | Breaking risk |
| -------------- | ------------------ | -------: | -------------- | ------------- |
| entity-id      | string             |      Нет | contract field | Высокий       |
| content-hash   | string             |      Нет | contract field | Высокий       |
| activity-id    | string             |      Нет | contract field | Высокий       |
| molecule-id    | string             |      Нет | contract field | Высокий       |
| target-id      | ['string', 'null'] |       Да | contract field | Средний       |
| assay-id       | ['string', 'null'] |       Да | contract field | Средний       |
| publication-id | ['string', 'null'] |       Да | contract field | Средний       |
| record-id      | ['number', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column-groups: []`).

Evidence:

- `configs/pipelines/chembl/activity.yaml`
- `configs/schemas/chembl/activity.yaml`
- `configs/quality/entities/chembl/activity.yaml`
- `docs/04-reference/contracts/gold/chembl-activity-v1.0.json`
- `data/output/bronze/chembl/activity`

### chembl-assay

#### 1. Общая информация

- Provider: chembl
- Entity: assay
- Pipeline name / pipeline-id: chembl-assay
- Primary keys: ['assay-id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `METADATA-ONLY`.
  - Ключевые JSON paths (из schema-snapshot metadata): aidx, assay-category, assay-cell-type, assay-chembl-id, assay-classifications, assay-group, assay-organism, assay-parameters, assay-strain, assay-subcellular-fraction, assay-tax-id, assay-test-type ...
- Поля метаданных: \-run-id/\-run-type/\-source-batch-id/\-ingestion-ts/\-index/content-hash/entity-id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity-id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content-hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \-run-id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \-dq-warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \-dq-error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/assay.yaml`.
- Hash exclusions: meta-fields из domain.constants.META-FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on-schema-mismatch=evolve (base config).
- Partition keys: silver=['assay-type'], gold=MISSING.
- Merge key correctness: uses primary-keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле           | Тип                | Nullable | Semantic role  | Breaking risk |
| -------------- | ------------------ | -------: | -------------- | ------------- |
| entity-id      | string             |      Нет | contract field | Высокий       |
| content-hash   | string             |      Нет | contract field | Высокий       |
| assay-id       | string             |      Нет | contract field | Высокий       |
| target-id      | ['string', 'null'] |       Да | contract field | Средний       |
| publication-id | ['string', 'null'] |       Да | contract field | Средний       |
| cell-id        | ['string', 'null'] |       Да | contract field | Средний       |
| tissue-id      | ['string', 'null'] |       Да | contract field | Средний       |
| src-id         | ['number', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column-groups: []`).

Evidence:

- `configs/pipelines/chembl/assay.yaml`
- `configs/schemas/chembl/assay.yaml`
- `configs/quality/entities/chembl/assay.yaml`
- `docs/04-reference/contracts/gold/chembl-assay-v1.0.json`
- `data/output/bronze/chembl/assay`

### chembl-assay-parameters

#### 1. Общая информация

- Provider: chembl
- Entity: assay-parameters
- Pipeline name / pipeline-id: chembl-assay-parameters
- Primary keys: ['assay-param-id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \-run-id/\-run-type/\-source-batch-id/\-ingestion-ts/\-index/content-hash/entity-id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity-id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content-hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \-run-id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \-dq-warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \-dq-error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/assay-parameters.yaml`.
- Hash exclusions: meta-fields из domain.constants.META-FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on-schema-mismatch=evolve (base config).
- Partition keys: silver=['type'], gold=MISSING.
- Merge key correctness: uses primary-keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле           | Тип                | Nullable | Semantic role  | Breaking risk |
| -------------- | ------------------ | -------: | -------------- | ------------- |
| entity-id      | string             |      Нет | contract field | Высокий       |
| content-hash   | string             |      Нет | contract field | Высокий       |
| assay-param-id | number             |      Нет | contract field | Высокий       |
| assay-id       | string             |      Нет | contract field | Высокий       |
| type           | string             |      Нет | contract field | Высокий       |
| relation       | ['string', 'null'] |       Да | contract field | Средний       |
| value          | ['number', 'null'] |       Да | contract field | Средний       |
| units          | ['string', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column-groups: []`).

Evidence:

- `configs/pipelines/chembl/assay-parameters.yaml`
- `configs/schemas/chembl/assay-parameters.yaml`
- `configs/quality/entities/chembl/assay-parameters.yaml`
- `docs/04-reference/contracts/gold/chembl-assay-parameters-v1.0.json`
- `data/output/bronze/chembl/assay-parameters`

### chembl-cell-line

#### 1. Общая информация

- Provider: chembl
- Entity: cell-line
- Pipeline name / pipeline-id: chembl-cell-line
- Primary keys: ['cell-id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `METADATA-ONLY`.
  - Ключевые JSON paths (из schema-snapshot metadata): cell-chembl-id, cell-description, cell-id, cell-name, cell-source-organism, cell-source-tax-id, cell-source-tissue, cellosaurus-id, cl-lincs-id, clo-id, efo-id
- Поля метаданных: \-run-id/\-run-type/\-source-batch-id/\-ingestion-ts/\-index/content-hash/entity-id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity-id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content-hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \-run-id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \-dq-warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \-dq-error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/cell-line.yaml`.
- Hash exclusions: meta-fields из domain.constants.META-FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on-schema-mismatch=evolve (base config).
- Partition keys: silver=MISSING, gold=MISSING.
- Merge key correctness: uses primary-keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле                    | Тип                | Nullable | Semantic role  | Breaking risk |
| ----------------------- | ------------------ | -------: | -------------- | ------------- |
| entity-id               | string             |      Нет | contract field | Высокий       |
| content-hash            | string             |      Нет | contract field | Высокий       |
| cell-id                 | string             |      Нет | contract field | Высокий       |
| cell-name               | string             |      Нет | contract field | Высокий       |
| cell-description        | ['string', 'null'] |       Да | contract field | Средний       |
| cell-source-tissue      | ['string', 'null'] |       Да | contract field | Средний       |
| cell-source-organism    | ['string', 'null'] |       Да | contract field | Средний       |
| cell-source-taxonomy-id | ['number', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column-groups: []`).

Evidence:

- `configs/pipelines/chembl/cell-line.yaml`
- `configs/schemas/chembl/cell-line.yaml`
- `configs/quality/entities/chembl/cell-line.yaml`
- `docs/04-reference/contracts/gold/chembl-cell-line-v1.0.json`
- `data/output/bronze/chembl/cell-line`

### chembl-compound-record

#### 1. Общая информация

- Provider: chembl
- Entity: compound-record
- Pipeline name / pipeline-id: chembl-compound-record
- Primary keys: ['record-id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `METADATA-ONLY`.
  - Ключевые JSON paths (из schema-snapshot metadata): compound-key, compound-name, document-chembl-id, molecule-chembl-id, record-id, src-id
- Поля метаданных: \-run-id/\-run-type/\-source-batch-id/\-ingestion-ts/\-index/content-hash/entity-id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity-id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content-hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \-run-id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \-dq-warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \-dq-error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/compound-record.yaml`.
- Hash exclusions: meta-fields из domain.constants.META-FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on-schema-mismatch=evolve (base config).
- Partition keys: silver=MISSING, gold=MISSING.
- Merge key correctness: uses primary-keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле           | Тип                | Nullable | Semantic role  | Breaking risk |
| -------------- | ------------------ | -------: | -------------- | ------------- |
| entity-id      | string             |      Нет | contract field | Высокий       |
| content-hash   | string             |      Нет | contract field | Высокий       |
| record-id      | number             |      Нет | contract field | Высокий       |
| molecule-id    | string             |      Нет | contract field | Высокий       |
| publication-id | string             |      Нет | contract field | Высокий       |
| compound-key   | ['string', 'null'] |       Да | contract field | Средний       |
| compound-name  | ['string', 'null'] |       Да | contract field | Средний       |
| src-id         | number             |      Нет | contract field | Высокий       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column-groups: []`).

Evidence:

- `configs/pipelines/chembl/compound-record.yaml`
- `configs/schemas/chembl/compound-record.yaml`
- `configs/quality/entities/chembl/compound-record.yaml`
- `docs/04-reference/contracts/gold/chembl-compound-record-v1.0.json`
- `data/output/bronze/chembl/compound-record`

### chembl-molecule

#### 1. Общая информация

- Provider: chembl
- Entity: molecule
- Pipeline name / pipeline-id: chembl-molecule
- Primary keys: ['molecule-id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \-run-id/\-run-type/\-source-batch-id/\-ingestion-ts/\-index/content-hash/entity-id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity-id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content-hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \-run-id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \-dq-warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \-dq-error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/molecule.yaml`.
- Hash exclusions: meta-fields из domain.constants.META-FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on-schema-mismatch=evolve (base config).
- Partition keys: silver=['molecule-type'], gold=MISSING.
- Merge key correctness: uses primary-keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле           | Тип                | Nullable | Semantic role  | Breaking risk |
| -------------- | ------------------ | -------: | -------------- | ------------- |
| entity-id      | string             |      Нет | contract field | Высокий       |
| content-hash   | string             |      Нет | contract field | Высокий       |
| molecule-id    | string             |      Нет | contract field | Высокий       |
| pref-name      | ['string', 'null'] |       Да | contract field | Средний       |
| molecule-type  | ['string', 'null'] |       Да | contract field | Средний       |
| structure-type | ['string', 'null'] |       Да | contract field | Средний       |
| max-phase      | ['number', 'null'] |       Да | contract field | Средний       |
| first-approval | ['number', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column-groups: []`).

Evidence:

- `configs/pipelines/chembl/molecule.yaml`
- `configs/schemas/chembl/molecule.yaml`
- `configs/quality/entities/chembl/molecule.yaml`
- `docs/04-reference/contracts/gold/chembl-molecule-v1.0.json`
- `data/output/bronze/chembl/molecule`

### chembl-protein-class

#### 1. Общая информация

- Provider: chembl
- Entity: protein-class
- Pipeline name / pipeline-id: chembl-protein-class
- Primary keys: ['protein-class-id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \-run-id/\-run-type/\-source-batch-id/\-ingestion-ts/\-index/content-hash/entity-id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity-id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content-hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \-run-id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \-dq-warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \-dq-error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/protein-class.yaml`.
- Hash exclusions: meta-fields из domain.constants.META-FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on-schema-mismatch=evolve (base config).
- Partition keys: silver=['class-level'], gold=MISSING.
- Merge key correctness: uses primary-keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле               | Тип                | Nullable | Semantic role  | Breaking risk |
| ------------------ | ------------------ | -------: | -------------- | ------------- |
| entity-id          | string             |      Нет | contract field | Высокий       |
| content-hash       | string             |      Нет | contract field | Высокий       |
| protein-class-id   | number             |      Нет | contract field | Высокий       |
| parent-id          | ['number', 'null'] |       Да | contract field | Средний       |
| class-level        | ['number', 'null'] |       Да | contract field | Средний       |
| pref-name          | ['string', 'null'] |       Да | contract field | Средний       |
| short-name         | ['string', 'null'] |       Да | contract field | Средний       |
| protein-class-desc | ['string', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column-groups: []`).

Evidence:

- `configs/pipelines/chembl/protein-class.yaml`
- `configs/schemas/chembl/protein-class.yaml`
- `configs/quality/entities/chembl/protein-class.yaml`
- `docs/04-reference/contracts/gold/chembl-protein-class-v1.0.json`
- `data/output/bronze/chembl/protein-class`

### chembl-publication

#### 1. Общая информация

- Provider: chembl
- Entity: publication
- Pipeline name / pipeline-id: chembl-publication
- Primary keys: ['publication-id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \-run-id/\-run-type/\-source-batch-id/\-ingestion-ts/\-index/content-hash/entity-id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity-id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content-hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \-run-id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \-dq-warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \-dq-error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/publication.yaml`.
- Hash exclusions: meta-fields из domain.constants.META-FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on-schema-mismatch=evolve (base config).
- Partition keys: silver=MISSING, gold=MISSING.
- Merge key correctness: uses primary-keys from pipeline config; collision risk requires entity-level validation.

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
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column-groups: []`).

Evidence:

- `configs/pipelines/chembl/publication.yaml`
- `configs/schemas/chembl/publication.yaml`
- `configs/quality/entities/chembl/publication.yaml`
- `MISSING`
- `data/output/bronze/chembl/publication`

### chembl-publication-similarity

#### 1. Общая информация

- Provider: chembl
- Entity: publication-similarity
- Pipeline name / pipeline-id: chembl-publication-similarity
- Primary keys: ['sim-id']
- Loading strategy: Silver `merge(default)`, Gold `overwrite`
- Write mode (Silver/Gold): `merge(default)` / `overwrite`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \-run-id/\-run-type/\-source-batch-id/\-ingestion-ts/\-index/content-hash/entity-id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity-id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content-hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \-run-id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \-dq-warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \-dq-error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/publication-similarity.yaml`.
- Hash exclusions: meta-fields из domain.constants.META-FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on-schema-mismatch=evolve (base config).
- Partition keys: silver=[], gold=MISSING.
- Merge key correctness: uses primary-keys from pipeline config; collision risk requires entity-level validation.

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
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column-groups: []`).

Evidence:

- `configs/pipelines/chembl/publication-similarity.yaml`
- `configs/schemas/chembl/publication-similarity.yaml`
- `configs/quality/entities/chembl/publication-similarity.yaml`
- `MISSING`
- `data/output/bronze/chembl/publication-similarity`

### chembl-publication-term

#### 1. Общая информация

- Provider: chembl
- Entity: publication-term
- Pipeline name / pipeline-id: chembl-publication-term
- Primary keys: ['entity-id']
- Loading strategy: Silver `merge(default)`, Gold `overwrite`
- Write mode (Silver/Gold): `merge(default)` / `overwrite`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \-run-id/\-run-type/\-source-batch-id/\-ingestion-ts/\-index/content-hash/entity-id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity-id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content-hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \-run-id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \-dq-warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \-dq-error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/publication-term.yaml`.
- Hash exclusions: meta-fields из domain.constants.META-FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on-schema-mismatch=evolve (base config).
- Partition keys: silver=['term-type'], gold=MISSING.
- Merge key correctness: uses primary-keys from pipeline config; collision risk requires entity-level validation.

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
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column-groups: []`).

Evidence:

- `configs/pipelines/chembl/publication-term.yaml`
- `configs/schemas/chembl/publication-term.yaml`
- `configs/quality/entities/chembl/publication-term.yaml`
- `MISSING`
- `data/output/bronze/chembl/publication-term`

### chembl-subcellular-fraction

#### 1. Общая информация

- Provider: chembl
- Entity: subcellular-fraction
- Pipeline name / pipeline-id: chembl-subcellular-fraction
- Primary keys: ['entity-id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \-run-id/\-run-type/\-source-batch-id/\-ingestion-ts/\-index/content-hash/entity-id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity-id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content-hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \-run-id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \-dq-warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \-dq-error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/subcellular-fraction.yaml`.
- Hash exclusions: meta-fields из domain.constants.META-FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on-schema-mismatch=evolve (base config).
- Partition keys: silver=MISSING, gold=MISSING.
- Merge key correctness: uses primary-keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле                 | Тип                | Nullable | Semantic role  | Breaking risk |
| -------------------- | ------------------ | -------: | -------------- | ------------- |
| entity-id            | string             |      Нет | contract field | Высокий       |
| content-hash         | string             |      Нет | contract field | Высокий       |
| subcellular-fraction | string             |      Нет | contract field | Высокий       |
| assay-count          | ['number', 'null'] |       Да | contract field | Средний       |
| example-assay-id     | ['string', 'null'] |       Да | contract field | Средний       |
| \-run-id             | string             |      Нет | contract field | Высокий       |
| \-run-type           | string             |      Нет | contract field | Высокий       |
| \-source-batch-id    | ['string', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column-groups: []`).

Evidence:

- `configs/pipelines/chembl/subcellular-fraction.yaml`
- `configs/schemas/chembl/subcellular-fraction.yaml`
- `configs/quality/entities/chembl/subcellular-fraction.yaml`
- `docs/04-reference/contracts/gold/chembl-subcellular-fraction-v1.0.json`
- `data/output/bronze/chembl/subcellular-fraction`

### chembl-target

#### 1. Общая информация

- Provider: chembl
- Entity: target
- Pipeline name / pipeline-id: chembl-target
- Primary keys: ['target-id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \-run-id/\-run-type/\-source-batch-id/\-ingestion-ts/\-index/content-hash/entity-id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity-id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content-hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \-run-id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \-dq-warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \-dq-error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/target.yaml`.
- Hash exclusions: meta-fields из domain.constants.META-FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on-schema-mismatch=evolve (base config).
- Partition keys: silver=['target-type'], gold=MISSING.
- Merge key correctness: uses primary-keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле               | Тип                 | Nullable | Semantic role  | Breaking risk |
| ------------------ | ------------------- | -------: | -------------- | ------------- |
| entity-id          | string              |      Нет | contract field | Высокий       |
| content-hash       | string              |      Нет | contract field | Высокий       |
| target-id          | string              |      Нет | contract field | Высокий       |
| pref-name          | ['string', 'null']  |       Да | contract field | Средний       |
| target-type        | ['string', 'null']  |       Да | contract field | Средний       |
| organism           | ['string', 'null']  |       Да | contract field | Средний       |
| taxonomy-id        | ['number', 'null']  |       Да | contract field | Средний       |
| species-group-flag | ['boolean', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column-groups: []`).

Evidence:

- `configs/pipelines/chembl/target.yaml`
- `configs/schemas/chembl/target.yaml`
- `configs/quality/entities/chembl/target.yaml`
- `docs/04-reference/contracts/gold/chembl-target-v1.0.json`
- `data/output/bronze/chembl/target`

### chembl-target-component

#### 1. Общая информация

- Provider: chembl
- Entity: target-component
- Pipeline name / pipeline-id: chembl-target-component
- Primary keys: ['component-id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `METADATA-ONLY`.
  - Ключевые JSON paths (из schema-snapshot metadata): accession, component-id, component-type, description, go-slims, organism, protein-classifications, sequence, target-component-synonyms, target-component-xrefs, targets, tax-id
- Поля метаданных: \-run-id/\-run-type/\-source-batch-id/\-ingestion-ts/\-index/content-hash/entity-id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity-id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content-hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \-run-id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \-dq-warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \-dq-error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/target-component.yaml`.
- Hash exclusions: meta-fields из domain.constants.META-FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on-schema-mismatch=evolve (base config).
- Partition keys: silver=['organism'], gold=MISSING.
- Merge key correctness: uses primary-keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле           | Тип                | Nullable | Semantic role  | Breaking risk |
| -------------- | ------------------ | -------: | -------------- | ------------- |
| entity-id      | string             |      Нет | contract field | Высокий       |
| content-hash   | string             |      Нет | contract field | Высокий       |
| component-id   | number             |      Нет | contract field | Высокий       |
| accession      | ['string', 'null'] |       Да | contract field | Средний       |
| component-type | ['string', 'null'] |       Да | contract field | Средний       |
| description    | ['string', 'null'] |       Да | contract field | Средний       |
| organism       | ['string', 'null'] |       Да | contract field | Средний       |
| taxonomy-id    | ['number', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column-groups: []`).

Evidence:

- `configs/pipelines/chembl/target-component.yaml`
- `configs/schemas/chembl/target-component.yaml`
- `configs/quality/entities/chembl/target-component.yaml`
- `docs/04-reference/contracts/gold/chembl-target-component-v1.0.json`
- `data/output/bronze/chembl/target-component`

### chembl-tissue

#### 1. Общая информация

- Provider: chembl
- Entity: tissue
- Pipeline name / pipeline-id: chembl-tissue
- Primary keys: ['tissue-id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \-run-id/\-run-type/\-source-batch-id/\-ingestion-ts/\-index/content-hash/entity-id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity-id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content-hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \-run-id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \-dq-warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \-dq-error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/chembl/tissue.yaml`.
- Hash exclusions: meta-fields из domain.constants.META-FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on-schema-mismatch=evolve (base config).
- Partition keys: silver=MISSING, gold=MISSING.
- Merge key correctness: uses primary-keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле       | Тип                | Nullable | Semantic role  | Breaking risk |
| ---------- | ------------------ | -------: | -------------- | ------------- |
| tissue-id  | string             |      Нет | contract field | Высокий       |
| pref-name  | string             |      Нет | contract field | Высокий       |
| bto-id     | ['string', 'null'] |       Да | contract field | Средний       |
| caloha-id  | ['string', 'null'] |       Да | contract field | Средний       |
| efo-id     | ['string', 'null'] |       Да | contract field | Средний       |
| uberon-id  | ['string', 'null'] |       Да | contract field | Средний       |
| \-run-id   | string             |      Нет | contract field | Высокий       |
| \-run-type | string             |      Нет | contract field | Высокий       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column-groups: []`).

Evidence:

- `configs/pipelines/chembl/tissue.yaml`
- `configs/schemas/chembl/tissue.yaml`
- `configs/quality/entities/chembl/tissue.yaml`
- `docs/04-reference/contracts/gold/chembl-tissue-v1.0.json`
- `data/output/bronze/chembl/tissue`

### crossref-publication

#### 1. Общая информация

- Provider: crossref
- Entity: publication
- Pipeline name / pipeline-id: crossref-publication
- Primary keys: ['doi']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \-run-id/\-run-type/\-source-batch-id/\-ingestion-ts/\-index/content-hash/entity-id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity-id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content-hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \-run-id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \-dq-warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \-dq-error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/crossref/publication.yaml`.
- Hash exclusions: meta-fields из domain.constants.META-FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on-schema-mismatch=evolve (base config).
- Partition keys: silver=MISSING, gold=MISSING.
- Merge key correctness: uses primary-keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле         | Тип                | Nullable | Semantic role  | Breaking risk |
| ------------ | ------------------ | -------: | -------------- | ------------- |
| entity-id    | string             |      Нет | contract field | Высокий       |
| content-hash | string             |      Нет | contract field | Высокий       |
| doi          | string             |      Нет | contract field | Высокий       |
| title        | ['string', 'null'] |       Да | contract field | Средний       |
| authors      | ['string', 'null'] |       Да | contract field | Средний       |
| journal      | ['string', 'null'] |       Да | contract field | Средний       |
| issn         | ['string', 'null'] |       Да | contract field | Средний       |
| issn-list    | ['string', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column-groups: []`).

Evidence:

- `configs/pipelines/crossref/publication.yaml`
- `configs/schemas/crossref/publication.yaml`
- `configs/quality/entities/crossref/publication.yaml`
- `docs/04-reference/contracts/gold/crossref-publication-v1.0.json`
- `data/output/bronze/crossref/publication`

### openalex-publication

#### 1. Общая информация

- Provider: openalex
- Entity: publication
- Pipeline name / pipeline-id: openalex-publication
- Primary keys: ['openalex-id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \-run-id/\-run-type/\-source-batch-id/\-ingestion-ts/\-index/content-hash/entity-id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity-id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content-hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \-run-id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \-dq-warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \-dq-error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/openalex/publication.yaml`.
- Hash exclusions: meta-fields из domain.constants.META-FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on-schema-mismatch=evolve (base config).
- Partition keys: silver=MISSING, gold=MISSING.
- Merge key correctness: uses primary-keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле         | Тип                | Nullable | Semantic role  | Breaking risk |
| ------------ | ------------------ | -------: | -------------- | ------------- |
| entity-id    | string             |      Нет | contract field | Высокий       |
| content-hash | string             |      Нет | contract field | Высокий       |
| openalex-id  | string             |      Нет | contract field | Высокий       |
| doi          | ['string', 'null'] |       Да | contract field | Средний       |
| pmid         | ['string', 'null'] |       Да | contract field | Средний       |
| title        | ['string', 'null'] |       Да | contract field | Средний       |
| abstract     | ['string', 'null'] |       Да | contract field | Средний       |
| authors      | ['string', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column-groups: []`).

Evidence:

- `configs/pipelines/openalex/publication.yaml`
- `configs/schemas/openalex/publication.yaml`
- `configs/quality/entities/openalex/publication.yaml`
- `docs/04-reference/contracts/gold/openalex-publication-v1.0.json`
- `data/output/bronze/openalex/publication`

### pubchem-compound

#### 1. Общая информация

- Provider: pubchem
- Entity: compound
- Pipeline name / pipeline-id: pubchem-compound
- Primary keys: ['molecule-id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \-run-id/\-run-type/\-source-batch-id/\-ingestion-ts/\-index/content-hash/entity-id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity-id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content-hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \-run-id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \-dq-warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \-dq-error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/pubchem/compound.yaml`.
- Hash exclusions: meta-fields из domain.constants.META-FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on-schema-mismatch=evolve (base config).
- Partition keys: silver=['batch-date'], gold=MISSING.
- Merge key correctness: uses primary-keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле              | Тип                | Nullable | Semantic role  | Breaking risk |
| ----------------- | ------------------ | -------: | -------------- | ------------- |
| entity-id         | string             |      Нет | contract field | Высокий       |
| molecule-id       | string             |      Нет | contract field | Высокий       |
| molecular-formula | ['string', 'null'] |       Да | contract field | Средний       |
| molecular-weight  | ['number', 'null'] |       Да | contract field | Средний       |
| canonical-smiles  | ['string', 'null'] |       Да | contract field | Средний       |
| isomeric-smiles   | ['string', 'null'] |       Да | contract field | Средний       |
| inchi             | ['string', 'null'] |       Да | contract field | Средний       |
| inchi-key         | ['string', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column-groups: []`).

Evidence:

- `configs/pipelines/pubchem/compound.yaml`
- `configs/schemas/pubchem/compound.yaml`
- `configs/quality/entities/pubchem/compound.yaml`
- `docs/04-reference/contracts/gold/pubchem-compound-v1.0.json`
- `data/output/bronze/pubchem/compound`

### pubmed-publication

#### 1. Общая информация

- Provider: pubmed
- Entity: publication
- Pipeline name / pipeline-id: pubmed-publication
- Primary keys: ['pmid']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \-run-id/\-run-type/\-source-batch-id/\-ingestion-ts/\-index/content-hash/entity-id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity-id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content-hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \-run-id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \-dq-warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \-dq-error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/pubmed/publication.yaml`.
- Hash exclusions: meta-fields из domain.constants.META-FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on-schema-mismatch=evolve (base config).
- Partition keys: silver=MISSING, gold=MISSING.
- Merge key correctness: uses primary-keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле                | Тип                 | Nullable | Semantic role  | Breaking risk |
| ------------------- | ------------------- | -------: | -------------- | ------------- |
| entity-id           | string              |      Нет | contract field | Высокий       |
| content-hash        | string              |      Нет | contract field | Высокий       |
| pmid                | string              |      Нет | contract field | Высокий       |
| doi                 | ['string', 'null']  |       Да | contract field | Средний       |
| pmc-id              | ['string', 'null']  |       Да | contract field | Средний       |
| title               | string              |      Нет | contract field | Высокий       |
| abstract            | ['string', 'null']  |       Да | contract field | Средний       |
| abstract-structured | ['boolean', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column-groups: []`).

Evidence:

- `configs/pipelines/pubmed/publication.yaml`
- `configs/schemas/pubmed/publication.yaml`
- `configs/quality/entities/pubmed/publication.yaml`
- `docs/04-reference/contracts/gold/pubmed-publication-v1.0.json`
- `data/output/bronze/pubmed/publication`

### semanticscholar-publication

#### 1. Общая информация

- Provider: semanticscholar
- Entity: publication
- Pipeline name / pipeline-id: semanticscholar-publication
- Primary keys: ['paper-id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \-run-id/\-run-type/\-source-batch-id/\-ingestion-ts/\-index/content-hash/entity-id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity-id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content-hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \-run-id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \-dq-warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \-dq-error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/semanticscholar/publication.yaml`.
- Hash exclusions: meta-fields из domain.constants.META-FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on-schema-mismatch=evolve (base config).
- Partition keys: silver=MISSING, gold=MISSING.
- Merge key correctness: uses primary-keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле         | Тип                | Nullable | Semantic role  | Breaking risk |
| ------------ | ------------------ | -------: | -------------- | ------------- |
| entity-id    | string             |      Нет | contract field | Высокий       |
| content-hash | string             |      Нет | contract field | Высокий       |
| paper-id     | string             |      Нет | contract field | Высокий       |
| doi          | ['string', 'null'] |       Да | contract field | Средний       |
| pmid         | ['string', 'null'] |       Да | contract field | Средний       |
| corpus-id    | ['number', 'null'] |       Да | contract field | Средний       |
| title        | ['string', 'null'] |       Да | contract field | Средний       |
| abstract     | ['string', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column-groups: []`).

Evidence:

- `configs/pipelines/semanticscholar/publication.yaml`
- `configs/schemas/semanticscholar/publication.yaml`
- `configs/quality/entities/semanticscholar/publication.yaml`
- `docs/04-reference/contracts/gold/semanticscholar-publication-v1.0.json`
- `data/output/bronze/semanticscholar/publication`

### uniprot-idmapping

#### 1. Общая информация

- Provider: uniprot
- Entity: idmapping
- Pipeline name / pipeline-id: uniprot-idmapping
- Primary keys: ['target-id']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `INFERRED`.
  - Ключевые JSON paths: UNKNOWN (нет JSONL sample, inference required).
- Поля метаданных: \-run-id/\-run-type/\-source-batch-id/\-ingestion-ts/\-index/content-hash/entity-id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity-id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content-hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \-run-id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \-dq-warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \-dq-error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/uniprot/idmapping.yaml`.
- Hash exclusions: meta-fields из domain.constants.META-FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on-schema-mismatch=evolve (base config).
- Partition keys: silver=[], gold=MISSING.
- Merge key correctness: uses primary-keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле                | Тип                | Nullable | Semantic role  | Breaking risk |
| ------------------- | ------------------ | -------: | -------------- | ------------- |
| entity-id           | string             |      Нет | contract field | Высокий       |
| content-hash        | string             |      Нет | contract field | Высокий       |
| target-id           | string             |      Нет | contract field | Высокий       |
| uniprot-accession   | ['string', 'null'] |       Да | contract field | Средний       |
| mapping-status      | string             |      Нет | contract field | Высокий       |
| uniprot-entry-name  | ['string', 'null'] |       Да | contract field | Средний       |
| organism-scientific | ['string', 'null'] |       Да | contract field | Средний       |
| organism-common     | ['string', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column-groups: []`).

Evidence:

- `configs/pipelines/uniprot/idmapping.yaml`
- `configs/schemas/uniprot/idmapping.yaml`
- `configs/quality/entities/uniprot/idmapping.yaml`
- `docs/04-reference/contracts/gold/uniprot-idmapping-v1.0.json`
- `data/output/bronze/uniprot/idmapping`

### uniprot-protein

#### 1. Общая информация

- Provider: uniprot
- Entity: protein
- Pipeline name / pipeline-id: uniprot-protein
- Primary keys: ['accession']
- Loading strategy: Silver `merge(default)`, Gold `scd2`
- Write mode (Silver/Gold): `merge(default)` / `scd2`

#### 2. Bronze Layer

- Формат хранения: jsonl (по базовой конфигурации), фактический sample raw JSONL в репозитории: GAP.
- Структура записи: `METADATA-ONLY`.
  - Ключевые JSON paths (из schema-snapshot metadata): annotationScore, comments, entryAudit, entryType, extraAttributes, features, genes, keywords, lineages, organism, primaryAccession, proteinDescription ...
- Поля метаданных: \-run-id/\-run-type/\-source-batch-id/\-ingestion-ts/\-index/content-hash/entity-id (по общесистемным конвенциям).
- Потенциальный schema drift: MEDIUM (для pipelines без фактического Bronze sample).
- Проблемы: nested JSON и multi-type поля не подтверждены репрезентативной выборкой N>=200 (GAP).

#### 3. Silver Schema

| Поле         | Тип    | Nullable | Source field         | Notes                       |
| ------------ | ------ | -------: | -------------------- | --------------------------- |
| entity-id    | string |  UNKNOWN | primary/business key | System prefix field         |
| content-hash | string |  UNKNOWN | hash service         | Deterministic hash expected |
| \-run-id     | string |  UNKNOWN | runtime metadata     | ADR-029 metadata            |
| \-dq-warn    | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |
| \-dq-error   | bool   |  UNKNOWN | DQ processor         | DQ flag suffix              |

Анализ:

- Типы (int→float coercion?): UNKNOWN per pipeline (нет извлечённой полной матрицы Pandera↔PyArrow в этом проходе).
- Nullable consistency: частично UNKNOWN; требуется автоматический diff Pandera DataFrameModel vs silver.py schemas.
- DQ flags / checks: externalized config `configs/quality/entities/uniprot/protein.yaml`.
- Hash exclusions: meta-fields из domain.constants.META-FIELDS.
- Ordering policy: system prefix + business + DQ suffix (фиксировано в schema conventions).
- Schema drift tolerance: Silver on-schema-mismatch=evolve (base config).
- Partition keys: silver=['organism'], gold=MISSING.
- Merge key correctness: uses primary-keys from pipeline config; collision risk requires entity-level validation.

#### 4. Gold Schema (Контракт)

- Контрактная версия: 1.0.0
- SCD2 / overwrite / append: `scd2`
- Стабильность API: strict validation expected by ADR-018; runtime enforcement requires explicit strict schema checks in GoldWriter.
- Backward compatibility: versioned JSON schema files exist for most pipelines; missing contract => HIGH risk.
- Breaking risk: type/nullable/key changes HIGH for required fields, MEDIUM for optional fields.

| Поле          | Тип                | Nullable | Semantic role  | Breaking risk |
| ------------- | ------------------ | -------: | -------------- | ------------- |
| entity-id     | string             |      Нет | contract field | Высокий       |
| content-hash  | string             |      Нет | contract field | Высокий       |
| accession     | string             |      Нет | contract field | Высокий       |
| entry-name    | ['string', 'null'] |       Да | contract field | Средний       |
| active-sites  | ['string', 'null'] |       Да | contract field | Средний       |
| binding-sites | ['string', 'null'] |       Да | contract field | Средний       |
| domains       | ['string', 'null'] |       Да | contract field | Средний       |
| features-json | ['string', 'null'] |       Да | contract field | Средний       |

#### 5. Domain ↔ Schema соответствие

- 1:1 mapping?: UNKNOWN/PARTIAL (нужен автоматизированный field-level diff Domain entity ↔ Pandera ↔ Gold contract).
- Поля отсутствуют в доменной модели?: не подтверждено, требуется diff.
- Поля есть в домене, но не в таблице?: не подтверждено, требуется diff.
- Нарушение Single Source of Truth?: вероятно PARTIAL (schema config files у части pipeline минимальные `column-groups: []`).

Evidence:

- `configs/pipelines/uniprot/protein.yaml`
- `configs/schemas/uniprot/protein.yaml`
- `configs/quality/entities/uniprot/protein.yaml`
- `docs/04-reference/contracts/gold/uniprot-protein-v1.0.json`
- `data/output/bronze/uniprot/protein`

## II. Архитектурные проблемы

| ID   | Pipeline | Категория                | Проблема                                                                                                                 | Риск   | Приоритет |
| ---- | -------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------ | ------ | --------- |
| A-01 | all      | Schema duplication       | Schema defined in multiple places (Pandera, PyArrow, JSON contract, YAML schema config) without generated SSOT.          | High   | P1        |
| A-02 | all      | Content hash instability | Hash excludes fixed meta-fields but no per-pipeline explicit exclusion spec; drift may alter hashes unexpectedly.        | Medium | P2        |
| A-03 | many     | Domain drift             | Multiple `configs/schemas/*` are empty (`column-groups: []`), violating explicit schema↔domain pairing intent (ADR-034). | High   | P1        |
| A-04 | selected | Nullable ambiguity       | Nullable policy not centrally enforced across Bronze→Silver→Gold contracts.                                              | Medium | P2        |
| A-05 | selected | Inconsistent naming      | publication/document aliases and provider-specific IDs create hidden coupling.                                           | Medium | P2        |

## III. Общесистемные проблемы

- Повторяющиеся поля в схемах: `entity-id`, `content-hash`, `-run-id`, `-dq-warn`, `-dq-error` повторяются во всех слоях без machine-verifiable centralized generator.
- Несогласованные типы между пайплайнами: publication identifiers (`doi`, `pmid`, provider-specific IDs) имеют разный naming и optionality.
- Унифицированные metadata поля ADR-029 partially present, но фактическая проверка полноты по всем pipeline outputs не автоматизирована.
- Нарушения OutputMetadata унификации: в `data/output/bronze/*` доступны только metadata snapshots, не raw JSONL outputs для подтверждения full parity.
- Риск nullable-int coercion: при наличии null в integer-полях и переходах pandas/pyarrow возможен int→float дрейф (не закрыт глобальной политикой).
- SCD2 consistency: gold modes mixed (`append`, `overwrite`, `scd2`) с разным поведением по pipeline.
- Partition strategy несогласована: часть pipelines partitioned, часть нет; rationale часто не документирован в ADR-level decision.

## IV. План улучшений

### 1. Немедленные улучшения (Low Risk)

- Add automated `schema-diff` CI job: Pandera vs PyArrow vs Gold JSON contract. Impact: высокая трассируемость; Breaking: Non-breaking; ADR: No; Migration: add report-only stage.
- Enforce explicit hash input specification per pipeline in config (`hash.include-fields`/`hash.exclude-fields`). Impact: детерминизм; Breaking: Non-breaking initially (warn mode); ADR: Maybe (if mandatory). Migration: phase warn→enforce.
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
