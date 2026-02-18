# BioETL Schema Audit Report

## I. Карта схем пайплайна

### chembl_activity

1. Общая информация

- Provider: chembl
- Entity: activity
- Pipeline name / pipeline_id: chembl_activity
- Primary keys: ['activity_id']
- Loading strategy: incremental/default (implicit)
- Write mode (Silver/Gold): silver={}, gold={'mode': 'append'}

2. Bronze Layer

- Формат хранения: ожидается JSONL + zstd (см. BronzeWriter); фактический артефакт: `data/output/bronze/chembl/activity`.
- Структура записи:
  - Минимальный пример JSON: GAP (raw sample not found in repository artifacts for this pipeline).
  - Ключевые JSON paths: INFERRED from API/Pydantic model + transformer.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts` (общий metadata contract).
- Потенциальный schema drift: Artifact exists but contains metadata snapshot JSON, not raw JSONL stream.
- Проблемы: nested JSON / multi-type поля зависят от provider API; требуется профилирование сырого JSONL.

3. Silver Schema
   | Поле | Тип | Nullable | Source field | Notes |
   |\---|---|---:|---|---|
   | entity_id | string | UNKNOWN | generated | present in CHEMBL_ACTIVITY_SCHEMA |
   | content_hash | string | UNKNOWN | generated | canonical hash |
   | \_run_id | string | UNKNOWN | metadata | metadata unified |
   | activity_id | UNKNOWN | UNKNOWN | source API field | business/merge key candidate |
   Анализ:

- Типы (int→float coercion?): UNKNOWN per-pipeline; Pandera class `ActivitySchema` exists for most pipelines.
- Nullable consistency: частично покрыто Pandera+PyArrow, но полная матрица Pandera↔Delta требует runtime schema dump (GAP).
- DQ flags / checks: внешние entity/provider YAML по ADR-027; inline DQ минимален.
- Hash exclusions: META_FIELDS исключаются из content hash.
- Ordering policy: canonical column ordering перед записью.
- Schema drift tolerance: Silver поддерживает policy error/evolve/ignore.
- Partition keys: []/MISSING.
- Merge key correctness: использует primary_keys из pipeline config; корректность зависит от стабильности source IDs.

4. Gold Schema (Контракт)

- Контрактная версия: explicit version field в contract class отсутствует (GAP).
- SCD2 / overwrite / append: append
- Стабильность API: strict Pandera required на Gold writer (ADR-018).
- Backward compatibility: drift не допускается без контрактных изменений; version bump process не формализован в коде (GAP).
- Breaking risk: средний/высокий для PK/type/nullable изменений; низкий для add nullable column.

| Поле                                           | Тип                |      Nullable | Semantic role       | Breaking risk |
| ---------------------------------------------- | ------------------ | ------------: | ------------------- | ------------- |
| entity_id                                      | string             |       UNKNOWN | stable entity key   | HIGH          |
| content_hash                                   | string             |       UNKNOWN | version fingerprint | MEDIUM        |
| activity_id                                    | UNKNOWN            |       UNKNOWN | business key        | HIGH          |
| \_valid_from/\_valid_to/\_is_current/\_version | timestamp/bool/int | mode-specific | SCD2 system columns | MEDIUM        |

5. Domain ↔ Schema соответствие

- 1:1 mapping?: Частично, для publication-family много flatten/normalization.
- Поля отсутствуют в доменной модели?: UNKNOWN (нужен автоматический diff domain entity ↔ contract).
- Поля есть в домене, но не в таблице?: UNKNOWN/GAP.
- Нарушение Single Source of Truth?: риск средний из-за параллельного существования domain entities, Pandera schema, Gold contract, YAML schema config.
  Evidence:
- configs/pipelines/chembl/activity.yaml
- src/bioetl/composition/factories/pipeline_factories.py
- src/bioetl/infrastructure/schemas/silver.py (CHEMBL_ACTIVITY_SCHEMA)
- src/bioetl/domain/contracts/gold/\*.py (ChEMBLActivityGoldSchema)
- src/bioetl/domain/schemas/\*\*/\* (ActivitySchema)

### chembl_assay

1. Общая информация

- Provider: chembl
- Entity: assay
- Pipeline name / pipeline_id: chembl_assay
- Primary keys: ['assay_id']
- Loading strategy: incremental/default (implicit)
- Write mode (Silver/Gold): silver={'partition_by': ['assay_type']}, gold={'mode': 'scd2', 'scd_config': {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}}

2. Bronze Layer

- Формат хранения: ожидается JSONL + zstd (см. BronzeWriter); фактический артефакт: `data/output/bronze/chembl/assay`.
- Структура записи:
  - Минимальный пример JSON: GAP (raw sample not found in repository artifacts for this pipeline).
  - Ключевые JSON paths: INFERRED from API/Pydantic model + transformer.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts` (общий metadata contract).
- Потенциальный schema drift: Artifact exists but contains metadata snapshot JSON, not raw JSONL stream.
- Проблемы: nested JSON / multi-type поля зависят от provider API; требуется профилирование сырого JSONL.

3. Silver Schema
   | Поле | Тип | Nullable | Source field | Notes |
   |\---|---|---:|---|---|
   | entity_id | string | UNKNOWN | generated | present in CHEMBL_ASSAY_SCHEMA |
   | content_hash | string | UNKNOWN | generated | canonical hash |
   | \_run_id | string | UNKNOWN | metadata | metadata unified |
   | assay_id | UNKNOWN | UNKNOWN | source API field | business/merge key candidate |
   Анализ:

- Типы (int→float coercion?): UNKNOWN per-pipeline; Pandera class `AssaySchema` exists for most pipelines.
- Nullable consistency: частично покрыто Pandera+PyArrow, но полная матрица Pandera↔Delta требует runtime schema dump (GAP).
- DQ flags / checks: внешние entity/provider YAML по ADR-027; inline DQ минимален.
- Hash exclusions: META_FIELDS исключаются из content hash.
- Ordering policy: canonical column ordering перед записью.
- Schema drift tolerance: Silver поддерживает policy error/evolve/ignore.
- Partition keys: ['assay_type'].
- Merge key correctness: использует primary_keys из pipeline config; корректность зависит от стабильности source IDs.

4. Gold Schema (Контракт)

- Контрактная версия: explicit version field в contract class отсутствует (GAP).
- SCD2 / overwrite / append: scd2
- Стабильность API: strict Pandera required на Gold writer (ADR-018).
- Backward compatibility: drift не допускается без контрактных изменений; version bump process не формализован в коде (GAP).
- Breaking risk: средний/высокий для PK/type/nullable изменений; низкий для add nullable column.

| Поле                                           | Тип                |      Nullable | Semantic role       | Breaking risk |
| ---------------------------------------------- | ------------------ | ------------: | ------------------- | ------------- |
| entity_id                                      | string             |       UNKNOWN | stable entity key   | HIGH          |
| content_hash                                   | string             |       UNKNOWN | version fingerprint | MEDIUM        |
| assay_id                                       | UNKNOWN            |       UNKNOWN | business key        | HIGH          |
| \_valid_from/\_valid_to/\_is_current/\_version | timestamp/bool/int | mode-specific | SCD2 system columns | MEDIUM        |

5. Domain ↔ Schema соответствие

- 1:1 mapping?: Частично, для publication-family много flatten/normalization.
- Поля отсутствуют в доменной модели?: UNKNOWN (нужен автоматический diff domain entity ↔ contract).
- Поля есть в домене, но не в таблице?: UNKNOWN/GAP.
- Нарушение Single Source of Truth?: риск средний из-за параллельного существования domain entities, Pandera schema, Gold contract, YAML schema config.
  Evidence:
- configs/pipelines/chembl/assay.yaml
- src/bioetl/composition/factories/pipeline_factories.py
- src/bioetl/infrastructure/schemas/silver.py (CHEMBL_ASSAY_SCHEMA)
- src/bioetl/domain/contracts/gold/\*.py (ChEMBLAssayGoldSchema)
- src/bioetl/domain/schemas/\*\*/\* (AssaySchema)

### chembl_assay_parameters

1. Общая информация

- Provider: chembl
- Entity: assay_parameters
- Pipeline name / pipeline_id: chembl_assay_parameters
- Primary keys: ['assay_param_id']
- Loading strategy: incremental/default (implicit)
- Write mode (Silver/Gold): silver={'partition_by': ['type']}, gold={'mode': 'scd2', 'scd_config': {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}}

2. Bronze Layer

- Формат хранения: ожидается JSONL + zstd (см. BronzeWriter); фактический артефакт: `MISSING`.
- Структура записи:
  - Минимальный пример JSON: GAP (raw sample not found in repository artifacts for this pipeline).
  - Ключевые JSON paths: INFERRED from API/Pydantic model + transformer.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts` (общий metadata contract).
- Потенциальный schema drift: INFERRED from Pydantic+transformer.
- Проблемы: nested JSON / multi-type поля зависят от provider API; требуется профилирование сырого JSONL.

3. Silver Schema
   | Поле | Тип | Nullable | Source field | Notes |
   |\---|---|---:|---|---|
   | entity_id | string | UNKNOWN | generated | present in CHEMBL_ASSAY_PARAMETERS_SCHEMA |
   | content_hash | string | UNKNOWN | generated | canonical hash |
   | \_run_id | string | UNKNOWN | metadata | metadata unified |
   | assay_param_id | UNKNOWN | UNKNOWN | source API field | business/merge key candidate |
   Анализ:

- Типы (int→float coercion?): UNKNOWN per-pipeline; Pandera class `AssayParametersSchema` exists for most pipelines.
- Nullable consistency: частично покрыто Pandera+PyArrow, но полная матрица Pandera↔Delta требует runtime schema dump (GAP).
- DQ flags / checks: внешние entity/provider YAML по ADR-027; inline DQ минимален.
- Hash exclusions: META_FIELDS исключаются из content hash.
- Ordering policy: canonical column ordering перед записью.
- Schema drift tolerance: Silver поддерживает policy error/evolve/ignore.
- Partition keys: ['type'].
- Merge key correctness: использует primary_keys из pipeline config; корректность зависит от стабильности source IDs.

4. Gold Schema (Контракт)

- Контрактная версия: explicit version field в contract class отсутствует (GAP).
- SCD2 / overwrite / append: scd2
- Стабильность API: strict Pandera required на Gold writer (ADR-018).
- Backward compatibility: drift не допускается без контрактных изменений; version bump process не формализован в коде (GAP).
- Breaking risk: средний/высокий для PK/type/nullable изменений; низкий для add nullable column.

| Поле                                           | Тип                |      Nullable | Semantic role       | Breaking risk |
| ---------------------------------------------- | ------------------ | ------------: | ------------------- | ------------- |
| entity_id                                      | string             |       UNKNOWN | stable entity key   | HIGH          |
| content_hash                                   | string             |       UNKNOWN | version fingerprint | MEDIUM        |
| assay_param_id                                 | UNKNOWN            |       UNKNOWN | business key        | HIGH          |
| \_valid_from/\_valid_to/\_is_current/\_version | timestamp/bool/int | mode-specific | SCD2 system columns | MEDIUM        |

5. Domain ↔ Schema соответствие

- 1:1 mapping?: Частично, для publication-family много flatten/normalization.
- Поля отсутствуют в доменной модели?: UNKNOWN (нужен автоматический diff domain entity ↔ contract).
- Поля есть в домене, но не в таблице?: UNKNOWN/GAP.
- Нарушение Single Source of Truth?: риск средний из-за параллельного существования domain entities, Pandera schema, Gold contract, YAML schema config.
  Evidence:
- configs/pipelines/chembl/assay_parameters.yaml
- src/bioetl/composition/factories/pipeline_factories.py
- src/bioetl/infrastructure/schemas/silver.py (CHEMBL_ASSAY_PARAMETERS_SCHEMA)
- src/bioetl/domain/contracts/gold/\*.py (ChEMBLAssayParametersGoldSchema)
- src/bioetl/domain/schemas/\*\*/\* (AssayParametersSchema)

### chembl_cell_line

1. Общая информация

- Provider: chembl
- Entity: cell_line
- Pipeline name / pipeline_id: chembl_cell_line
- Primary keys: ['cell_id']
- Loading strategy: incremental/default (implicit)
- Write mode (Silver/Gold): silver={}, gold={'mode': 'scd2', 'scd_config': {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}}

2. Bronze Layer

- Формат хранения: ожидается JSONL + zstd (см. BronzeWriter); фактический артефакт: `data/output/bronze/chembl/cell_line`.
- Структура записи:
  - Минимальный пример JSON: GAP (raw sample not found in repository artifacts for this pipeline).
  - Ключевые JSON paths: INFERRED from API/Pydantic model + transformer.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts` (общий metadata contract).
- Потенциальный schema drift: Artifact exists but contains metadata snapshot JSON, not raw JSONL stream.
- Проблемы: nested JSON / multi-type поля зависят от provider API; требуется профилирование сырого JSONL.

3. Silver Schema
   | Поле | Тип | Nullable | Source field | Notes |
   |\---|---|---:|---|---|
   | entity_id | string | UNKNOWN | generated | present in CHEMBL_CELL_LINE_SCHEMA |
   | content_hash | string | UNKNOWN | generated | canonical hash |
   | \_run_id | string | UNKNOWN | metadata | metadata unified |
   | cell_id | UNKNOWN | UNKNOWN | source API field | business/merge key candidate |
   Анализ:

- Типы (int→float coercion?): UNKNOWN per-pipeline; Pandera class `CellLineSchema` exists for most pipelines.
- Nullable consistency: частично покрыто Pandera+PyArrow, но полная матрица Pandera↔Delta требует runtime schema dump (GAP).
- DQ flags / checks: внешние entity/provider YAML по ADR-027; inline DQ минимален.
- Hash exclusions: META_FIELDS исключаются из content hash.
- Ordering policy: canonical column ordering перед записью.
- Schema drift tolerance: Silver поддерживает policy error/evolve/ignore.
- Partition keys: []/MISSING.
- Merge key correctness: использует primary_keys из pipeline config; корректность зависит от стабильности source IDs.

4. Gold Schema (Контракт)

- Контрактная версия: explicit version field в contract class отсутствует (GAP).
- SCD2 / overwrite / append: scd2
- Стабильность API: strict Pandera required на Gold writer (ADR-018).
- Backward compatibility: drift не допускается без контрактных изменений; version bump process не формализован в коде (GAP).
- Breaking risk: средний/высокий для PK/type/nullable изменений; низкий для add nullable column.

| Поле                                           | Тип                |      Nullable | Semantic role       | Breaking risk |
| ---------------------------------------------- | ------------------ | ------------: | ------------------- | ------------- |
| entity_id                                      | string             |       UNKNOWN | stable entity key   | HIGH          |
| content_hash                                   | string             |       UNKNOWN | version fingerprint | MEDIUM        |
| cell_id                                        | UNKNOWN            |       UNKNOWN | business key        | HIGH          |
| \_valid_from/\_valid_to/\_is_current/\_version | timestamp/bool/int | mode-specific | SCD2 system columns | MEDIUM        |

5. Domain ↔ Schema соответствие

- 1:1 mapping?: Частично, для publication-family много flatten/normalization.
- Поля отсутствуют в доменной модели?: UNKNOWN (нужен автоматический diff domain entity ↔ contract).
- Поля есть в домене, но не в таблице?: UNKNOWN/GAP.
- Нарушение Single Source of Truth?: риск средний из-за параллельного существования domain entities, Pandera schema, Gold contract, YAML schema config.
  Evidence:
- configs/pipelines/chembl/cell_line.yaml
- src/bioetl/composition/factories/pipeline_factories.py
- src/bioetl/infrastructure/schemas/silver.py (CHEMBL_CELL_LINE_SCHEMA)
- src/bioetl/domain/contracts/gold/\*.py (ChEMBLCellLineGoldSchema)
- src/bioetl/domain/schemas/\*\*/\* (CellLineSchema)

### chembl_compound_record

1. Общая информация

- Provider: chembl
- Entity: compound_record
- Pipeline name / pipeline_id: chembl_compound_record
- Primary keys: ['record_id']
- Loading strategy: incremental/default (implicit)
- Write mode (Silver/Gold): silver={}, gold={'mode': 'scd2', 'scd_config': {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}}

2. Bronze Layer

- Формат хранения: ожидается JSONL + zstd (см. BronzeWriter); фактический артефакт: `data/output/bronze/chembl/compound_record`.
- Структура записи:
  - Минимальный пример JSON: GAP (raw sample not found in repository artifacts for this pipeline).
  - Ключевые JSON paths: INFERRED from API/Pydantic model + transformer.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts` (общий metadata contract).
- Потенциальный schema drift: Artifact exists but contains metadata snapshot JSON, not raw JSONL stream.
- Проблемы: nested JSON / multi-type поля зависят от provider API; требуется профилирование сырого JSONL.

3. Silver Schema
   | Поле | Тип | Nullable | Source field | Notes |
   |\---|---|---:|---|---|
   | entity_id | string | UNKNOWN | generated | present in CHEMBL_COMPOUND_RECORD_SCHEMA |
   | content_hash | string | UNKNOWN | generated | canonical hash |
   | \_run_id | string | UNKNOWN | metadata | metadata unified |
   | record_id | UNKNOWN | UNKNOWN | source API field | business/merge key candidate |
   Анализ:

- Типы (int→float coercion?): UNKNOWN per-pipeline; Pandera class `CompoundRecordSchema` exists for most pipelines.
- Nullable consistency: частично покрыто Pandera+PyArrow, но полная матрица Pandera↔Delta требует runtime schema dump (GAP).
- DQ flags / checks: внешние entity/provider YAML по ADR-027; inline DQ минимален.
- Hash exclusions: META_FIELDS исключаются из content hash.
- Ordering policy: canonical column ordering перед записью.
- Schema drift tolerance: Silver поддерживает policy error/evolve/ignore.
- Partition keys: []/MISSING.
- Merge key correctness: использует primary_keys из pipeline config; корректность зависит от стабильности source IDs.

4. Gold Schema (Контракт)

- Контрактная версия: explicit version field в contract class отсутствует (GAP).
- SCD2 / overwrite / append: scd2
- Стабильность API: strict Pandera required на Gold writer (ADR-018).
- Backward compatibility: drift не допускается без контрактных изменений; version bump process не формализован в коде (GAP).
- Breaking risk: средний/высокий для PK/type/nullable изменений; низкий для add nullable column.

| Поле                                           | Тип                |      Nullable | Semantic role       | Breaking risk |
| ---------------------------------------------- | ------------------ | ------------: | ------------------- | ------------- |
| entity_id                                      | string             |       UNKNOWN | stable entity key   | HIGH          |
| content_hash                                   | string             |       UNKNOWN | version fingerprint | MEDIUM        |
| record_id                                      | UNKNOWN            |       UNKNOWN | business key        | HIGH          |
| \_valid_from/\_valid_to/\_is_current/\_version | timestamp/bool/int | mode-specific | SCD2 system columns | MEDIUM        |

5. Domain ↔ Schema соответствие

- 1:1 mapping?: Частично, для publication-family много flatten/normalization.
- Поля отсутствуют в доменной модели?: UNKNOWN (нужен автоматический diff domain entity ↔ contract).
- Поля есть в домене, но не в таблице?: UNKNOWN/GAP.
- Нарушение Single Source of Truth?: риск средний из-за параллельного существования domain entities, Pandera schema, Gold contract, YAML schema config.
  Evidence:
- configs/pipelines/chembl/compound_record.yaml
- src/bioetl/composition/factories/pipeline_factories.py
- src/bioetl/infrastructure/schemas/silver.py (CHEMBL_COMPOUND_RECORD_SCHEMA)
- src/bioetl/domain/contracts/gold/\*.py (ChEMBLCompoundRecordGoldSchema)
- src/bioetl/domain/schemas/\*\*/\* (CompoundRecordSchema)

### chembl_molecule

1. Общая информация

- Provider: chembl
- Entity: molecule
- Pipeline name / pipeline_id: chembl_molecule
- Primary keys: ['molecule_id']
- Loading strategy: incremental/default (implicit)
- Write mode (Silver/Gold): silver={'partition_by': ['molecule_type']}, gold={'mode': 'scd2', 'scd_config': {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}}

2. Bronze Layer

- Формат хранения: ожидается JSONL + zstd (см. BronzeWriter); фактический артефакт: `MISSING`.
- Структура записи:
  - Минимальный пример JSON: GAP (raw sample not found in repository artifacts for this pipeline).
  - Ключевые JSON paths: INFERRED from API/Pydantic model + transformer.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts` (общий metadata contract).
- Потенциальный schema drift: INFERRED from Pydantic+transformer.
- Проблемы: nested JSON / multi-type поля зависят от provider API; требуется профилирование сырого JSONL.

3. Silver Schema
   | Поле | Тип | Nullable | Source field | Notes |
   |\---|---|---:|---|---|
   | entity_id | string | UNKNOWN | generated | present in CHEMBL_MOLECULE_SCHEMA |
   | content_hash | string | UNKNOWN | generated | canonical hash |
   | \_run_id | string | UNKNOWN | metadata | metadata unified |
   | molecule_id | UNKNOWN | UNKNOWN | source API field | business/merge key candidate |
   Анализ:

- Типы (int→float coercion?): UNKNOWN per-pipeline; Pandera class `MoleculeSchema` exists for most pipelines.
- Nullable consistency: частично покрыто Pandera+PyArrow, но полная матрица Pandera↔Delta требует runtime schema dump (GAP).
- DQ flags / checks: внешние entity/provider YAML по ADR-027; inline DQ минимален.
- Hash exclusions: META_FIELDS исключаются из content hash.
- Ordering policy: canonical column ordering перед записью.
- Schema drift tolerance: Silver поддерживает policy error/evolve/ignore.
- Partition keys: ['molecule_type'].
- Merge key correctness: использует primary_keys из pipeline config; корректность зависит от стабильности source IDs.

4. Gold Schema (Контракт)

- Контрактная версия: explicit version field в contract class отсутствует (GAP).
- SCD2 / overwrite / append: scd2
- Стабильность API: strict Pandera required на Gold writer (ADR-018).
- Backward compatibility: drift не допускается без контрактных изменений; version bump process не формализован в коде (GAP).
- Breaking risk: средний/высокий для PK/type/nullable изменений; низкий для add nullable column.

| Поле                                           | Тип                |      Nullable | Semantic role       | Breaking risk |
| ---------------------------------------------- | ------------------ | ------------: | ------------------- | ------------- |
| entity_id                                      | string             |       UNKNOWN | stable entity key   | HIGH          |
| content_hash                                   | string             |       UNKNOWN | version fingerprint | MEDIUM        |
| molecule_id                                    | UNKNOWN            |       UNKNOWN | business key        | HIGH          |
| \_valid_from/\_valid_to/\_is_current/\_version | timestamp/bool/int | mode-specific | SCD2 system columns | MEDIUM        |

5. Domain ↔ Schema соответствие

- 1:1 mapping?: Частично, для publication-family много flatten/normalization.
- Поля отсутствуют в доменной модели?: UNKNOWN (нужен автоматический diff domain entity ↔ contract).
- Поля есть в домене, но не в таблице?: UNKNOWN/GAP.
- Нарушение Single Source of Truth?: риск средний из-за параллельного существования domain entities, Pandera schema, Gold contract, YAML schema config.
  Evidence:
- configs/pipelines/chembl/molecule.yaml
- src/bioetl/composition/factories/pipeline_factories.py
- src/bioetl/infrastructure/schemas/silver.py (CHEMBL_MOLECULE_SCHEMA)
- src/bioetl/domain/contracts/gold/\*.py (ChEMBLMoleculeGoldSchema)
- src/bioetl/domain/schemas/\*\*/\* (MoleculeSchema)

### chembl_protein_class

1. Общая информация

- Provider: chembl
- Entity: protein_class
- Pipeline name / pipeline_id: chembl_protein_class
- Primary keys: ['protein_class_id']
- Loading strategy: incremental/default (implicit)
- Write mode (Silver/Gold): silver={'partition_by': ['class_level']}, gold={'mode': 'scd2', 'scd_config': {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}}

2. Bronze Layer

- Формат хранения: ожидается JSONL + zstd (см. BronzeWriter); фактический артефакт: `MISSING`.
- Структура записи:
  - Минимальный пример JSON: GAP (raw sample not found in repository artifacts for this pipeline).
  - Ключевые JSON paths: INFERRED from API/Pydantic model + transformer.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts` (общий metadata contract).
- Потенциальный schema drift: INFERRED from Pydantic+transformer.
- Проблемы: nested JSON / multi-type поля зависят от provider API; требуется профилирование сырого JSONL.

3. Silver Schema
   | Поле | Тип | Nullable | Source field | Notes |
   |\---|---|---:|---|---|
   | entity_id | string | UNKNOWN | generated | present in CHEMBL_PROTEIN_CLASS_SCHEMA |
   | content_hash | string | UNKNOWN | generated | canonical hash |
   | \_run_id | string | UNKNOWN | metadata | metadata unified |
   | protein_class_id | UNKNOWN | UNKNOWN | source API field | business/merge key candidate |
   Анализ:

- Типы (int→float coercion?): UNKNOWN per-pipeline; Pandera class `ProteinClassificationSchema` exists for most pipelines.
- Nullable consistency: частично покрыто Pandera+PyArrow, но полная матрица Pandera↔Delta требует runtime schema dump (GAP).
- DQ flags / checks: внешние entity/provider YAML по ADR-027; inline DQ минимален.
- Hash exclusions: META_FIELDS исключаются из content hash.
- Ordering policy: canonical column ordering перед записью.
- Schema drift tolerance: Silver поддерживает policy error/evolve/ignore.
- Partition keys: ['class_level'].
- Merge key correctness: использует primary_keys из pipeline config; корректность зависит от стабильности source IDs.

4. Gold Schema (Контракт)

- Контрактная версия: explicit version field в contract class отсутствует (GAP).
- SCD2 / overwrite / append: scd2
- Стабильность API: strict Pandera required на Gold writer (ADR-018).
- Backward compatibility: drift не допускается без контрактных изменений; version bump process не формализован в коде (GAP).
- Breaking risk: средний/высокий для PK/type/nullable изменений; низкий для add nullable column.

| Поле                                           | Тип                |      Nullable | Semantic role       | Breaking risk |
| ---------------------------------------------- | ------------------ | ------------: | ------------------- | ------------- |
| entity_id                                      | string             |       UNKNOWN | stable entity key   | HIGH          |
| content_hash                                   | string             |       UNKNOWN | version fingerprint | MEDIUM        |
| protein_class_id                               | UNKNOWN            |       UNKNOWN | business key        | HIGH          |
| \_valid_from/\_valid_to/\_is_current/\_version | timestamp/bool/int | mode-specific | SCD2 system columns | MEDIUM        |

5. Domain ↔ Schema соответствие

- 1:1 mapping?: Частично, для publication-family много flatten/normalization.
- Поля отсутствуют в доменной модели?: UNKNOWN (нужен автоматический diff domain entity ↔ contract).
- Поля есть в домене, но не в таблице?: UNKNOWN/GAP.
- Нарушение Single Source of Truth?: риск средний из-за параллельного существования domain entities, Pandera schema, Gold contract, YAML schema config.
  Evidence:
- configs/pipelines/chembl/protein_class.yaml
- src/bioetl/composition/factories/pipeline_factories.py
- src/bioetl/infrastructure/schemas/silver.py (CHEMBL_PROTEIN_CLASS_SCHEMA)
- src/bioetl/domain/contracts/gold/\*.py (ChEMBLProteinClassGoldSchema)
- src/bioetl/domain/schemas/\*\*/\* (ProteinClassificationSchema)

### chembl_publication

1. Общая информация

- Provider: chembl
- Entity: publication
- Pipeline name / pipeline_id: chembl_publication
- Primary keys: ['publication_id']
- Loading strategy: full_scan_only
- Write mode (Silver/Gold): silver={'flat_structure': True}, gold={'mode': 'scd2', 'scd_config': {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}, 'flat_structure': True}

2. Bronze Layer

- Формат хранения: ожидается JSONL + zstd (см. BronzeWriter); фактический артефакт: `MISSING`.
- Структура записи:
  - Минимальный пример JSON: GAP (raw sample not found in repository artifacts for this pipeline).
  - Ключевые JSON paths: INFERRED from API/Pydantic model + transformer.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts` (общий metadata contract).
- Потенциальный schema drift: INFERRED from Pydantic+transformer.
- Проблемы: nested JSON / multi-type поля зависят от provider API; требуется профилирование сырого JSONL.

3. Silver Schema
   | Поле | Тип | Nullable | Source field | Notes |
   |\---|---|---:|---|---|
   | entity_id | string | UNKNOWN | generated | present in CHEMBL_PUBLICATION_SCHEMA |
   | content_hash | string | UNKNOWN | generated | canonical hash |
   | \_run_id | string | UNKNOWN | metadata | metadata unified |
   | publication_id | UNKNOWN | UNKNOWN | source API field | business/merge key candidate |
   Анализ:

- Типы (int→float coercion?): UNKNOWN per-pipeline; Pandera class `ChemblPublicationSchema` exists for most pipelines.
- Nullable consistency: частично покрыто Pandera+PyArrow, но полная матрица Pandera↔Delta требует runtime schema dump (GAP).
- DQ flags / checks: внешние entity/provider YAML по ADR-027; inline DQ минимален.
- Hash exclusions: META_FIELDS исключаются из content hash.
- Ordering policy: canonical column ordering перед записью.
- Schema drift tolerance: Silver поддерживает policy error/evolve/ignore.
- Partition keys: []/MISSING.
- Merge key correctness: использует primary_keys из pipeline config; корректность зависит от стабильности source IDs.

4. Gold Schema (Контракт)

- Контрактная версия: explicit version field в contract class отсутствует (GAP).
- SCD2 / overwrite / append: scd2
- Стабильность API: strict Pandera required на Gold writer (ADR-018).
- Backward compatibility: drift не допускается без контрактных изменений; version bump process не формализован в коде (GAP).
- Breaking risk: средний/высокий для PK/type/nullable изменений; низкий для add nullable column.

| Поле                                           | Тип                |      Nullable | Semantic role       | Breaking risk |
| ---------------------------------------------- | ------------------ | ------------: | ------------------- | ------------- |
| entity_id                                      | string             |       UNKNOWN | stable entity key   | HIGH          |
| content_hash                                   | string             |       UNKNOWN | version fingerprint | MEDIUM        |
| publication_id                                 | UNKNOWN            |       UNKNOWN | business key        | HIGH          |
| \_valid_from/\_valid_to/\_is_current/\_version | timestamp/bool/int | mode-specific | SCD2 system columns | MEDIUM        |

5. Domain ↔ Schema соответствие

- 1:1 mapping?: Частично, для publication-family много flatten/normalization.
- Поля отсутствуют в доменной модели?: UNKNOWN (нужен автоматический diff domain entity ↔ contract).
- Поля есть в домене, но не в таблице?: UNKNOWN/GAP.
- Нарушение Single Source of Truth?: риск средний из-за параллельного существования domain entities, Pandera schema, Gold contract, YAML schema config.
  Evidence:
- configs/pipelines/chembl/publication.yaml
- src/bioetl/composition/factories/pipeline_factories.py
- src/bioetl/infrastructure/schemas/silver.py (CHEMBL_PUBLICATION_SCHEMA)
- src/bioetl/domain/contracts/gold/\*.py (ChEMBLDocumentGoldSchema)
- src/bioetl/domain/schemas/\*\*/\* (ChemblPublicationSchema)

### chembl_publication_similarity

1. Общая информация

- Provider: chembl
- Entity: publication_similarity
- Pipeline name / pipeline_id: chembl_publication_similarity
- Primary keys: ['sim_id']
- Loading strategy: full_scan_only
- Write mode (Silver/Gold): silver={'partition_by': []}, gold={'mode': 'overwrite'}

2. Bronze Layer

- Формат хранения: ожидается JSONL + zstd (см. BronzeWriter); фактический артефакт: `MISSING`.
- Структура записи:
  - Минимальный пример JSON: GAP (raw sample not found in repository artifacts for this pipeline).
  - Ключевые JSON paths: INFERRED from API/Pydantic model + transformer.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts` (общий metadata contract).
- Потенциальный schema drift: INFERRED from Pydantic+transformer.
- Проблемы: nested JSON / multi-type поля зависят от provider API; требуется профилирование сырого JSONL.

3. Silver Schema
   | Поле | Тип | Nullable | Source field | Notes |
   |\---|---|---:|---|---|
   | entity_id | string | UNKNOWN | generated | present in CHEMBL_DOCUMENT_SIMILARITY_SCHEMA |
   | content_hash | string | UNKNOWN | generated | canonical hash |
   | \_run_id | string | UNKNOWN | metadata | metadata unified |
   | sim_id | UNKNOWN | UNKNOWN | source API field | business/merge key candidate |
   Анализ:

- Типы (int→float coercion?): UNKNOWN per-pipeline; Pandera class `PublicationSimilaritySchema` exists for most pipelines.
- Nullable consistency: частично покрыто Pandera+PyArrow, но полная матрица Pandera↔Delta требует runtime schema dump (GAP).
- DQ flags / checks: внешние entity/provider YAML по ADR-027; inline DQ минимален.
- Hash exclusions: META_FIELDS исключаются из content hash.
- Ordering policy: canonical column ordering перед записью.
- Schema drift tolerance: Silver поддерживает policy error/evolve/ignore.
- Partition keys: [].
- Merge key correctness: использует primary_keys из pipeline config; корректность зависит от стабильности source IDs.

4. Gold Schema (Контракт)

- Контрактная версия: explicit version field в contract class отсутствует (GAP).
- SCD2 / overwrite / append: overwrite
- Стабильность API: strict Pandera required на Gold writer (ADR-018).
- Backward compatibility: drift не допускается без контрактных изменений; version bump process не формализован в коде (GAP).
- Breaking risk: средний/высокий для PK/type/nullable изменений; низкий для add nullable column.

| Поле                                           | Тип                |      Nullable | Semantic role       | Breaking risk |
| ---------------------------------------------- | ------------------ | ------------: | ------------------- | ------------- |
| entity_id                                      | string             |       UNKNOWN | stable entity key   | HIGH          |
| content_hash                                   | string             |       UNKNOWN | version fingerprint | MEDIUM        |
| sim_id                                         | UNKNOWN            |       UNKNOWN | business key        | HIGH          |
| \_valid_from/\_valid_to/\_is_current/\_version | timestamp/bool/int | mode-specific | SCD2 system columns | MEDIUM        |

5. Domain ↔ Schema соответствие

- 1:1 mapping?: Частично, для publication-family много flatten/normalization.
- Поля отсутствуют в доменной модели?: UNKNOWN (нужен автоматический diff domain entity ↔ contract).
- Поля есть в домене, но не в таблице?: UNKNOWN/GAP.
- Нарушение Single Source of Truth?: риск средний из-за параллельного существования domain entities, Pandera schema, Gold contract, YAML schema config.
  Evidence:
- configs/pipelines/chembl/publication_similarity.yaml
- src/bioetl/composition/factories/pipeline_factories.py
- src/bioetl/infrastructure/schemas/silver.py (CHEMBL_DOCUMENT_SIMILARITY_SCHEMA)
- src/bioetl/domain/contracts/gold/\*.py (ChEMBLDocumentSimilarityGoldSchema)
- src/bioetl/domain/schemas/\*\*/\* (PublicationSimilaritySchema)

### chembl_publication_term

1. Общая информация

- Provider: chembl
- Entity: publication_term
- Pipeline name / pipeline_id: chembl_publication_term
- Primary keys: ['entity_id']
- Loading strategy: full_scan_only
- Write mode (Silver/Gold): silver={'partition_by': ['term_type']}, gold={'mode': 'overwrite'}

2. Bronze Layer

- Формат хранения: ожидается JSONL + zstd (см. BronzeWriter); фактический артефакт: `MISSING`.
- Структура записи:
  - Минимальный пример JSON: GAP (raw sample not found in repository artifacts for this pipeline).
  - Ключевые JSON paths: INFERRED from API/Pydantic model + transformer.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts` (общий metadata contract).
- Потенциальный schema drift: INFERRED from Pydantic+transformer.
- Проблемы: nested JSON / multi-type поля зависят от provider API; требуется профилирование сырого JSONL.

3. Silver Schema
   | Поле | Тип | Nullable | Source field | Notes |
   |\---|---|---:|---|---|
   | entity_id | string | UNKNOWN | generated | present in CHEMBL_DOCUMENT_TERM_SCHEMA |
   | content_hash | string | UNKNOWN | generated | canonical hash |
   | \_run_id | string | UNKNOWN | metadata | metadata unified |
   | entity_id | UNKNOWN | UNKNOWN | source API field | business/merge key candidate |
   Анализ:

- Типы (int→float coercion?): UNKNOWN per-pipeline; Pandera class `PublicationTermSchema` exists for most pipelines.
- Nullable consistency: частично покрыто Pandera+PyArrow, но полная матрица Pandera↔Delta требует runtime schema dump (GAP).
- DQ flags / checks: внешние entity/provider YAML по ADR-027; inline DQ минимален.
- Hash exclusions: META_FIELDS исключаются из content hash.
- Ordering policy: canonical column ordering перед записью.
- Schema drift tolerance: Silver поддерживает policy error/evolve/ignore.
- Partition keys: ['term_type'].
- Merge key correctness: использует primary_keys из pipeline config; корректность зависит от стабильности source IDs.

4. Gold Schema (Контракт)

- Контрактная версия: explicit version field в contract class отсутствует (GAP).
- SCD2 / overwrite / append: overwrite
- Стабильность API: strict Pandera required на Gold writer (ADR-018).
- Backward compatibility: drift не допускается без контрактных изменений; version bump process не формализован в коде (GAP).
- Breaking risk: средний/высокий для PK/type/nullable изменений; низкий для add nullable column.

| Поле                                           | Тип                |      Nullable | Semantic role       | Breaking risk |
| ---------------------------------------------- | ------------------ | ------------: | ------------------- | ------------- |
| entity_id                                      | string             |       UNKNOWN | stable entity key   | HIGH          |
| content_hash                                   | string             |       UNKNOWN | version fingerprint | MEDIUM        |
| entity_id                                      | UNKNOWN            |       UNKNOWN | business key        | HIGH          |
| \_valid_from/\_valid_to/\_is_current/\_version | timestamp/bool/int | mode-specific | SCD2 system columns | MEDIUM        |

5. Domain ↔ Schema соответствие

- 1:1 mapping?: Частично, для publication-family много flatten/normalization.
- Поля отсутствуют в доменной модели?: UNKNOWN (нужен автоматический diff domain entity ↔ contract).
- Поля есть в домене, но не в таблице?: UNKNOWN/GAP.
- Нарушение Single Source of Truth?: риск средний из-за параллельного существования domain entities, Pandera schema, Gold contract, YAML schema config.
  Evidence:
- configs/pipelines/chembl/publication_term.yaml
- src/bioetl/composition/factories/pipeline_factories.py
- src/bioetl/infrastructure/schemas/silver.py (CHEMBL_DOCUMENT_TERM_SCHEMA)
- src/bioetl/domain/contracts/gold/\*.py (ChEMBLDocumentTermGoldSchema)
- src/bioetl/domain/schemas/\*\*/\* (PublicationTermSchema)

### chembl_subcellular_fraction

1. Общая информация

- Provider: chembl
- Entity: subcellular_fraction
- Pipeline name / pipeline_id: chembl_subcellular_fraction
- Primary keys: ['entity_id']
- Loading strategy: full_scan_only
- Write mode (Silver/Gold): silver={}, gold={'mode': 'scd2', 'scd_config': {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}}

2. Bronze Layer

- Формат хранения: ожидается JSONL + zstd (см. BronzeWriter); фактический артефакт: `MISSING`.
- Структура записи:
  - Минимальный пример JSON: GAP (raw sample not found in repository artifacts for this pipeline).
  - Ключевые JSON paths: INFERRED from API/Pydantic model + transformer.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts` (общий metadata contract).
- Потенциальный schema drift: INFERRED from Pydantic+transformer.
- Проблемы: nested JSON / multi-type поля зависят от provider API; требуется профилирование сырого JSONL.

3. Silver Schema
   | Поле | Тип | Nullable | Source field | Notes |
   |\---|---|---:|---|---|
   | entity_id | string | UNKNOWN | generated | present in CHEMBL_SUBCELLULAR_FRACTION_SCHEMA |
   | content_hash | string | UNKNOWN | generated | canonical hash |
   | \_run_id | string | UNKNOWN | metadata | metadata unified |
   | entity_id | UNKNOWN | UNKNOWN | source API field | business/merge key candidate |
   Анализ:

- Типы (int→float coercion?): UNKNOWN per-pipeline; Pandera class `MISSING` exists for most pipelines.
- Nullable consistency: частично покрыто Pandera+PyArrow, но полная матрица Pandera↔Delta требует runtime schema dump (GAP).
- DQ flags / checks: внешние entity/provider YAML по ADR-027; inline DQ минимален.
- Hash exclusions: META_FIELDS исключаются из content hash.
- Ordering policy: canonical column ordering перед записью.
- Schema drift tolerance: Silver поддерживает policy error/evolve/ignore.
- Partition keys: []/MISSING.
- Merge key correctness: использует primary_keys из pipeline config; корректность зависит от стабильности source IDs.

4. Gold Schema (Контракт)

- Контрактная версия: explicit version field в contract class отсутствует (GAP).
- SCD2 / overwrite / append: scd2
- Стабильность API: strict Pandera required на Gold writer (ADR-018).
- Backward compatibility: drift не допускается без контрактных изменений; version bump process не формализован в коде (GAP).
- Breaking risk: средний/высокий для PK/type/nullable изменений; низкий для add nullable column.

| Поле                                           | Тип                |      Nullable | Semantic role       | Breaking risk |
| ---------------------------------------------- | ------------------ | ------------: | ------------------- | ------------- |
| entity_id                                      | string             |       UNKNOWN | stable entity key   | HIGH          |
| content_hash                                   | string             |       UNKNOWN | version fingerprint | MEDIUM        |
| entity_id                                      | UNKNOWN            |       UNKNOWN | business key        | HIGH          |
| \_valid_from/\_valid_to/\_is_current/\_version | timestamp/bool/int | mode-specific | SCD2 system columns | MEDIUM        |

5. Domain ↔ Schema соответствие

- 1:1 mapping?: Частично, для publication-family много flatten/normalization.
- Поля отсутствуют в доменной модели?: UNKNOWN (нужен автоматический diff domain entity ↔ contract).
- Поля есть в домене, но не в таблице?: UNKNOWN/GAP.
- Нарушение Single Source of Truth?: риск средний из-за параллельного существования domain entities, Pandera schema, Gold contract, YAML schema config.
  Evidence:
- configs/pipelines/chembl/subcellular_fraction.yaml
- src/bioetl/composition/factories/pipeline_factories.py
- src/bioetl/infrastructure/schemas/silver.py (CHEMBL_SUBCELLULAR_FRACTION_SCHEMA)
- src/bioetl/domain/contracts/gold/\*.py (ChEMBLSubcellularFractionGoldSchema)
- src/bioetl/domain/schemas/\*\*/\* (MISSING)

### chembl_target

1. Общая информация

- Provider: chembl
- Entity: target
- Pipeline name / pipeline_id: chembl_target
- Primary keys: ['target_id']
- Loading strategy: incremental/default (implicit)
- Write mode (Silver/Gold): silver={'partition_by': ['target_type']}, gold={'mode': 'scd2', 'scd_config': {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}}

2. Bronze Layer

- Формат хранения: ожидается JSONL + zstd (см. BronzeWriter); фактический артефакт: `MISSING`.
- Структура записи:
  - Минимальный пример JSON: GAP (raw sample not found in repository artifacts for this pipeline).
  - Ключевые JSON paths: INFERRED from API/Pydantic model + transformer.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts` (общий metadata contract).
- Потенциальный schema drift: INFERRED from Pydantic+transformer.
- Проблемы: nested JSON / multi-type поля зависят от provider API; требуется профилирование сырого JSONL.

3. Silver Schema
   | Поле | Тип | Nullable | Source field | Notes |
   |\---|---|---:|---|---|
   | entity_id | string | UNKNOWN | generated | present in CHEMBL_TARGET_SCHEMA |
   | content_hash | string | UNKNOWN | generated | canonical hash |
   | \_run_id | string | UNKNOWN | metadata | metadata unified |
   | target_id | UNKNOWN | UNKNOWN | source API field | business/merge key candidate |
   Анализ:

- Типы (int→float coercion?): UNKNOWN per-pipeline; Pandera class `TargetSchema` exists for most pipelines.
- Nullable consistency: частично покрыто Pandera+PyArrow, но полная матрица Pandera↔Delta требует runtime schema dump (GAP).
- DQ flags / checks: внешние entity/provider YAML по ADR-027; inline DQ минимален.
- Hash exclusions: META_FIELDS исключаются из content hash.
- Ordering policy: canonical column ordering перед записью.
- Schema drift tolerance: Silver поддерживает policy error/evolve/ignore.
- Partition keys: ['target_type'].
- Merge key correctness: использует primary_keys из pipeline config; корректность зависит от стабильности source IDs.

4. Gold Schema (Контракт)

- Контрактная версия: explicit version field в contract class отсутствует (GAP).
- SCD2 / overwrite / append: scd2
- Стабильность API: strict Pandera required на Gold writer (ADR-018).
- Backward compatibility: drift не допускается без контрактных изменений; version bump process не формализован в коде (GAP).
- Breaking risk: средний/высокий для PK/type/nullable изменений; низкий для add nullable column.

| Поле                                           | Тип                |      Nullable | Semantic role       | Breaking risk |
| ---------------------------------------------- | ------------------ | ------------: | ------------------- | ------------- |
| entity_id                                      | string             |       UNKNOWN | stable entity key   | HIGH          |
| content_hash                                   | string             |       UNKNOWN | version fingerprint | MEDIUM        |
| target_id                                      | UNKNOWN            |       UNKNOWN | business key        | HIGH          |
| \_valid_from/\_valid_to/\_is_current/\_version | timestamp/bool/int | mode-specific | SCD2 system columns | MEDIUM        |

5. Domain ↔ Schema соответствие

- 1:1 mapping?: Частично, для publication-family много flatten/normalization.
- Поля отсутствуют в доменной модели?: UNKNOWN (нужен автоматический diff domain entity ↔ contract).
- Поля есть в домене, но не в таблице?: UNKNOWN/GAP.
- Нарушение Single Source of Truth?: риск средний из-за параллельного существования domain entities, Pandera schema, Gold contract, YAML schema config.
  Evidence:
- configs/pipelines/chembl/target.yaml
- src/bioetl/composition/factories/pipeline_factories.py
- src/bioetl/infrastructure/schemas/silver.py (CHEMBL_TARGET_SCHEMA)
- src/bioetl/domain/contracts/gold/\*.py (ChEMBLTargetGoldSchema)
- src/bioetl/domain/schemas/\*\*/\* (TargetSchema)

### chembl_target_component

1. Общая информация

- Provider: chembl
- Entity: target_component
- Pipeline name / pipeline_id: chembl_target_component
- Primary keys: ['component_id']
- Loading strategy: incremental/default (implicit)
- Write mode (Silver/Gold): silver={'partition_by': ['organism']}, gold={'mode': 'scd2', 'scd_config': {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}}

2. Bronze Layer

- Формат хранения: ожидается JSONL + zstd (см. BronzeWriter); фактический артефакт: `data/output/bronze/chembl/target_component`.
- Структура записи:
  - Минимальный пример JSON: GAP (raw sample not found in repository artifacts for this pipeline).
  - Ключевые JSON paths: INFERRED from API/Pydantic model + transformer.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts` (общий metadata contract).
- Потенциальный schema drift: Artifact exists but contains metadata snapshot JSON, not raw JSONL stream.
- Проблемы: nested JSON / multi-type поля зависят от provider API; требуется профилирование сырого JSONL.

3. Silver Schema
   | Поле | Тип | Nullable | Source field | Notes |
   |\---|---|---:|---|---|
   | entity_id | string | UNKNOWN | generated | present in CHEMBL_TARGET_COMPONENT_SCHEMA |
   | content_hash | string | UNKNOWN | generated | canonical hash |
   | \_run_id | string | UNKNOWN | metadata | metadata unified |
   | component_id | UNKNOWN | UNKNOWN | source API field | business/merge key candidate |
   Анализ:

- Типы (int→float coercion?): UNKNOWN per-pipeline; Pandera class `TargetComponentSchema` exists for most pipelines.
- Nullable consistency: частично покрыто Pandera+PyArrow, но полная матрица Pandera↔Delta требует runtime schema dump (GAP).
- DQ flags / checks: внешние entity/provider YAML по ADR-027; inline DQ минимален.
- Hash exclusions: META_FIELDS исключаются из content hash.
- Ordering policy: canonical column ordering перед записью.
- Schema drift tolerance: Silver поддерживает policy error/evolve/ignore.
- Partition keys: ['organism'].
- Merge key correctness: использует primary_keys из pipeline config; корректность зависит от стабильности source IDs.

4. Gold Schema (Контракт)

- Контрактная версия: explicit version field в contract class отсутствует (GAP).
- SCD2 / overwrite / append: scd2
- Стабильность API: strict Pandera required на Gold writer (ADR-018).
- Backward compatibility: drift не допускается без контрактных изменений; version bump process не формализован в коде (GAP).
- Breaking risk: средний/высокий для PK/type/nullable изменений; низкий для add nullable column.

| Поле                                           | Тип                |      Nullable | Semantic role       | Breaking risk |
| ---------------------------------------------- | ------------------ | ------------: | ------------------- | ------------- |
| entity_id                                      | string             |       UNKNOWN | stable entity key   | HIGH          |
| content_hash                                   | string             |       UNKNOWN | version fingerprint | MEDIUM        |
| component_id                                   | UNKNOWN            |       UNKNOWN | business key        | HIGH          |
| \_valid_from/\_valid_to/\_is_current/\_version | timestamp/bool/int | mode-specific | SCD2 system columns | MEDIUM        |

5. Domain ↔ Schema соответствие

- 1:1 mapping?: Частично, для publication-family много flatten/normalization.
- Поля отсутствуют в доменной модели?: UNKNOWN (нужен автоматический diff domain entity ↔ contract).
- Поля есть в домене, но не в таблице?: UNKNOWN/GAP.
- Нарушение Single Source of Truth?: риск средний из-за параллельного существования domain entities, Pandera schema, Gold contract, YAML schema config.
  Evidence:
- configs/pipelines/chembl/target_component.yaml
- src/bioetl/composition/factories/pipeline_factories.py
- src/bioetl/infrastructure/schemas/silver.py (CHEMBL_TARGET_COMPONENT_SCHEMA)
- src/bioetl/domain/contracts/gold/\*.py (ChEMBLTargetComponentGoldSchema)
- src/bioetl/domain/schemas/\*\*/\* (TargetComponentSchema)

### chembl_tissue

1. Общая информация

- Provider: chembl
- Entity: tissue
- Pipeline name / pipeline_id: chembl_tissue
- Primary keys: ['tissue_id']
- Loading strategy: incremental/default (implicit)
- Write mode (Silver/Gold): silver={}, gold={'mode': 'scd2', 'scd_config': {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}}

2. Bronze Layer

- Формат хранения: ожидается JSONL + zstd (см. BronzeWriter); фактический артефакт: `MISSING`.
- Структура записи:
  - Минимальный пример JSON: GAP (raw sample not found in repository artifacts for this pipeline).
  - Ключевые JSON paths: INFERRED from API/Pydantic model + transformer.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts` (общий metadata contract).
- Потенциальный schema drift: INFERRED from Pydantic+transformer.
- Проблемы: nested JSON / multi-type поля зависят от provider API; требуется профилирование сырого JSONL.

3. Silver Schema
   | Поле | Тип | Nullable | Source field | Notes |
   |\---|---|---:|---|---|
   | entity_id | string | UNKNOWN | generated | present in CHEMBL_TISSUE_SCHEMA |
   | content_hash | string | UNKNOWN | generated | canonical hash |
   | \_run_id | string | UNKNOWN | metadata | metadata unified |
   | tissue_id | UNKNOWN | UNKNOWN | source API field | business/merge key candidate |
   Анализ:

- Типы (int→float coercion?): UNKNOWN per-pipeline; Pandera class `MISSING` exists for most pipelines.
- Nullable consistency: частично покрыто Pandera+PyArrow, но полная матрица Pandera↔Delta требует runtime schema dump (GAP).
- DQ flags / checks: внешние entity/provider YAML по ADR-027; inline DQ минимален.
- Hash exclusions: META_FIELDS исключаются из content hash.
- Ordering policy: canonical column ordering перед записью.
- Schema drift tolerance: Silver поддерживает policy error/evolve/ignore.
- Partition keys: []/MISSING.
- Merge key correctness: использует primary_keys из pipeline config; корректность зависит от стабильности source IDs.

4. Gold Schema (Контракт)

- Контрактная версия: explicit version field в contract class отсутствует (GAP).
- SCD2 / overwrite / append: scd2
- Стабильность API: strict Pandera required на Gold writer (ADR-018).
- Backward compatibility: drift не допускается без контрактных изменений; version bump process не формализован в коде (GAP).
- Breaking risk: средний/высокий для PK/type/nullable изменений; низкий для add nullable column.

| Поле                                           | Тип                |      Nullable | Semantic role       | Breaking risk |
| ---------------------------------------------- | ------------------ | ------------: | ------------------- | ------------- |
| entity_id                                      | string             |       UNKNOWN | stable entity key   | HIGH          |
| content_hash                                   | string             |       UNKNOWN | version fingerprint | MEDIUM        |
| tissue_id                                      | UNKNOWN            |       UNKNOWN | business key        | HIGH          |
| \_valid_from/\_valid_to/\_is_current/\_version | timestamp/bool/int | mode-specific | SCD2 system columns | MEDIUM        |

5. Domain ↔ Schema соответствие

- 1:1 mapping?: Частично, для publication-family много flatten/normalization.
- Поля отсутствуют в доменной модели?: UNKNOWN (нужен автоматический diff domain entity ↔ contract).
- Поля есть в домене, но не в таблице?: UNKNOWN/GAP.
- Нарушение Single Source of Truth?: риск средний из-за параллельного существования domain entities, Pandera schema, Gold contract, YAML schema config.
  Evidence:
- configs/pipelines/chembl/tissue.yaml
- src/bioetl/composition/factories/pipeline_factories.py
- src/bioetl/infrastructure/schemas/silver.py (CHEMBL_TISSUE_SCHEMA)
- src/bioetl/domain/contracts/gold/\*.py (ChEMBLTissueGoldSchema)
- src/bioetl/domain/schemas/\*\*/\* (MISSING)

### crossref_publication

1. Общая информация

- Provider: crossref
- Entity: publication
- Pipeline name / pipeline_id: crossref_publication
- Primary keys: ['doi']
- Loading strategy: full_scan_only
- Write mode (Silver/Gold): silver={'flat_structure': True}, gold={'mode': 'scd2', 'scd_config': {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}, 'flat_structure': True}

2. Bronze Layer

- Формат хранения: ожидается JSONL + zstd (см. BronzeWriter); фактический артефакт: `MISSING`.
- Структура записи:
  - Минимальный пример JSON: GAP (raw sample not found in repository artifacts for this pipeline).
  - Ключевые JSON paths: INFERRED from API/Pydantic model + transformer.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts` (общий metadata contract).
- Потенциальный schema drift: INFERRED from Pydantic+transformer.
- Проблемы: nested JSON / multi-type поля зависят от provider API; требуется профилирование сырого JSONL.

3. Silver Schema
   | Поле | Тип | Nullable | Source field | Notes |
   |\---|---|---:|---|---|
   | entity_id | string | UNKNOWN | generated | present in CROSSREF_PUBLICATION_SCHEMA |
   | content_hash | string | UNKNOWN | generated | canonical hash |
   | \_run_id | string | UNKNOWN | metadata | metadata unified |
   | doi | UNKNOWN | UNKNOWN | source API field | business/merge key candidate |
   Анализ:

- Типы (int→float coercion?): UNKNOWN per-pipeline; Pandera class `PublicationEnrichedSchema` exists for most pipelines.
- Nullable consistency: частично покрыто Pandera+PyArrow, но полная матрица Pandera↔Delta требует runtime schema dump (GAP).
- DQ flags / checks: внешние entity/provider YAML по ADR-027; inline DQ минимален.
- Hash exclusions: META_FIELDS исключаются из content hash.
- Ordering policy: canonical column ordering перед записью.
- Schema drift tolerance: Silver поддерживает policy error/evolve/ignore.
- Partition keys: []/MISSING.
- Merge key correctness: использует primary_keys из pipeline config; корректность зависит от стабильности source IDs.

4. Gold Schema (Контракт)

- Контрактная версия: explicit version field в contract class отсутствует (GAP).
- SCD2 / overwrite / append: scd2
- Стабильность API: strict Pandera required на Gold writer (ADR-018).
- Backward compatibility: drift не допускается без контрактных изменений; version bump process не формализован в коде (GAP).
- Breaking risk: средний/высокий для PK/type/nullable изменений; низкий для add nullable column.

| Поле                                           | Тип                |      Nullable | Semantic role       | Breaking risk |
| ---------------------------------------------- | ------------------ | ------------: | ------------------- | ------------- |
| entity_id                                      | string             |       UNKNOWN | stable entity key   | HIGH          |
| content_hash                                   | string             |       UNKNOWN | version fingerprint | MEDIUM        |
| doi                                            | UNKNOWN            |       UNKNOWN | business key        | HIGH          |
| \_valid_from/\_valid_to/\_is_current/\_version | timestamp/bool/int | mode-specific | SCD2 system columns | MEDIUM        |

5. Domain ↔ Schema соответствие

- 1:1 mapping?: Частично, для publication-family много flatten/normalization.
- Поля отсутствуют в доменной модели?: UNKNOWN (нужен автоматический diff domain entity ↔ contract).
- Поля есть в домене, но не в таблице?: UNKNOWN/GAP.
- Нарушение Single Source of Truth?: риск средний из-за параллельного существования domain entities, Pandera schema, Gold contract, YAML schema config.
  Evidence:
- configs/pipelines/crossref/publication.yaml
- src/bioetl/composition/factories/pipeline_factories.py
- src/bioetl/infrastructure/schemas/silver.py (CROSSREF_PUBLICATION_SCHEMA)
- src/bioetl/domain/contracts/gold/\*.py (CrossRefPublicationGoldSchema)
- src/bioetl/domain/schemas/\*\*/\* (PublicationEnrichedSchema)

### openalex_publication

1. Общая информация

- Provider: openalex
- Entity: publication
- Pipeline name / pipeline_id: openalex_publication
- Primary keys: ['openalex_id']
- Loading strategy: full_scan_only
- Write mode (Silver/Gold): silver={'flat_structure': True}, gold={'mode': 'scd2', 'scd_config': {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}, 'flat_structure': True}

2. Bronze Layer

- Формат хранения: ожидается JSONL + zstd (см. BronzeWriter); фактический артефакт: `MISSING`.
- Структура записи:
  - Минимальный пример JSON: GAP (raw sample not found in repository artifacts for this pipeline).
  - Ключевые JSON paths: INFERRED from API/Pydantic model + transformer.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts` (общий metadata contract).
- Потенциальный schema drift: INFERRED from Pydantic+transformer.
- Проблемы: nested JSON / multi-type поля зависят от provider API; требуется профилирование сырого JSONL.

3. Silver Schema
   | Поле | Тип | Nullable | Source field | Notes |
   |\---|---|---:|---|---|
   | entity_id | string | UNKNOWN | generated | present in OPENALEX_PUBLICATION_SCHEMA |
   | content_hash | string | UNKNOWN | generated | canonical hash |
   | \_run_id | string | UNKNOWN | metadata | metadata unified |
   | openalex_id | UNKNOWN | UNKNOWN | source API field | business/merge key candidate |
   Анализ:

- Типы (int→float coercion?): UNKNOWN per-pipeline; Pandera class `OpenAlexPublicationSchema` exists for most pipelines.
- Nullable consistency: частично покрыто Pandera+PyArrow, но полная матрица Pandera↔Delta требует runtime schema dump (GAP).
- DQ flags / checks: внешние entity/provider YAML по ADR-027; inline DQ минимален.
- Hash exclusions: META_FIELDS исключаются из content hash.
- Ordering policy: canonical column ordering перед записью.
- Schema drift tolerance: Silver поддерживает policy error/evolve/ignore.
- Partition keys: []/MISSING.
- Merge key correctness: использует primary_keys из pipeline config; корректность зависит от стабильности source IDs.

4. Gold Schema (Контракт)

- Контрактная версия: explicit version field в contract class отсутствует (GAP).
- SCD2 / overwrite / append: scd2
- Стабильность API: strict Pandera required на Gold writer (ADR-018).
- Backward compatibility: drift не допускается без контрактных изменений; version bump process не формализован в коде (GAP).
- Breaking risk: средний/высокий для PK/type/nullable изменений; низкий для add nullable column.

| Поле                                           | Тип                |      Nullable | Semantic role       | Breaking risk |
| ---------------------------------------------- | ------------------ | ------------: | ------------------- | ------------- |
| entity_id                                      | string             |       UNKNOWN | stable entity key   | HIGH          |
| content_hash                                   | string             |       UNKNOWN | version fingerprint | MEDIUM        |
| openalex_id                                    | UNKNOWN            |       UNKNOWN | business key        | HIGH          |
| \_valid_from/\_valid_to/\_is_current/\_version | timestamp/bool/int | mode-specific | SCD2 system columns | MEDIUM        |

5. Domain ↔ Schema соответствие

- 1:1 mapping?: Частично, для publication-family много flatten/normalization.
- Поля отсутствуют в доменной модели?: UNKNOWN (нужен автоматический diff domain entity ↔ contract).
- Поля есть в домене, но не в таблице?: UNKNOWN/GAP.
- Нарушение Single Source of Truth?: риск средний из-за параллельного существования domain entities, Pandera schema, Gold contract, YAML schema config.
  Evidence:
- configs/pipelines/openalex/publication.yaml
- src/bioetl/composition/factories/pipeline_factories.py
- src/bioetl/infrastructure/schemas/silver.py (OPENALEX_PUBLICATION_SCHEMA)
- src/bioetl/domain/contracts/gold/\*.py (OpenAlexPublicationGoldSchema)
- src/bioetl/domain/schemas/\*\*/\* (OpenAlexPublicationSchema)

### pubchem_compound

1. Общая информация

- Provider: pubchem
- Entity: compound
- Pipeline name / pipeline_id: pubchem_compound
- Primary keys: ['molecule_id']
- Loading strategy: incremental/default (implicit)
- Write mode (Silver/Gold): silver={'partition_by': ['batch_date']}, gold={'mode': 'scd2', 'scd_config': {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}}

2. Bronze Layer

- Формат хранения: ожидается JSONL + zstd (см. BronzeWriter); фактический артефакт: `MISSING`.
- Структура записи:
  - Минимальный пример JSON: GAP (raw sample not found in repository artifacts for this pipeline).
  - Ключевые JSON paths: INFERRED from API/Pydantic model + transformer.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts` (общий metadata contract).
- Потенциальный schema drift: INFERRED from Pydantic+transformer.
- Проблемы: nested JSON / multi-type поля зависят от provider API; требуется профилирование сырого JSONL.

3. Silver Schema
   | Поле | Тип | Nullable | Source field | Notes |
   |\---|---|---:|---|---|
   | entity_id | string | UNKNOWN | generated | present in PUBCHEM_COMPOUND_SCHEMA |
   | content_hash | string | UNKNOWN | generated | canonical hash |
   | \_run_id | string | UNKNOWN | metadata | metadata unified |
   | molecule_id | UNKNOWN | UNKNOWN | source API field | business/merge key candidate |
   Анализ:

- Типы (int→float coercion?): UNKNOWN per-pipeline; Pandera class `PubchemMoleculeSchema` exists for most pipelines.
- Nullable consistency: частично покрыто Pandera+PyArrow, но полная матрица Pandera↔Delta требует runtime schema dump (GAP).
- DQ flags / checks: внешние entity/provider YAML по ADR-027; inline DQ минимален.
- Hash exclusions: META_FIELDS исключаются из content hash.
- Ordering policy: canonical column ordering перед записью.
- Schema drift tolerance: Silver поддерживает policy error/evolve/ignore.
- Partition keys: ['batch_date'].
- Merge key correctness: использует primary_keys из pipeline config; корректность зависит от стабильности source IDs.

4. Gold Schema (Контракт)

- Контрактная версия: explicit version field в contract class отсутствует (GAP).
- SCD2 / overwrite / append: scd2
- Стабильность API: strict Pandera required на Gold writer (ADR-018).
- Backward compatibility: drift не допускается без контрактных изменений; version bump process не формализован в коде (GAP).
- Breaking risk: средний/высокий для PK/type/nullable изменений; низкий для add nullable column.

| Поле                                           | Тип                |      Nullable | Semantic role       | Breaking risk |
| ---------------------------------------------- | ------------------ | ------------: | ------------------- | ------------- |
| entity_id                                      | string             |       UNKNOWN | stable entity key   | HIGH          |
| content_hash                                   | string             |       UNKNOWN | version fingerprint | MEDIUM        |
| molecule_id                                    | UNKNOWN            |       UNKNOWN | business key        | HIGH          |
| \_valid_from/\_valid_to/\_is_current/\_version | timestamp/bool/int | mode-specific | SCD2 system columns | MEDIUM        |

5. Domain ↔ Schema соответствие

- 1:1 mapping?: Частично, для publication-family много flatten/normalization.
- Поля отсутствуют в доменной модели?: UNKNOWN (нужен автоматический diff domain entity ↔ contract).
- Поля есть в домене, но не в таблице?: UNKNOWN/GAP.
- Нарушение Single Source of Truth?: риск средний из-за параллельного существования domain entities, Pandera schema, Gold contract, YAML schema config.
  Evidence:
- configs/pipelines/pubchem/compound.yaml
- src/bioetl/composition/factories/pipeline_factories.py
- src/bioetl/infrastructure/schemas/silver.py (PUBCHEM_COMPOUND_SCHEMA)
- src/bioetl/domain/contracts/gold/\*.py (PubChemCompoundGoldSchema)
- src/bioetl/domain/schemas/\*\*/\* (PubchemMoleculeSchema)

### pubmed_publication

1. Общая информация

- Provider: pubmed
- Entity: publication
- Pipeline name / pipeline_id: pubmed_publication
- Primary keys: ['pmid']
- Loading strategy: full_scan_only
- Write mode (Silver/Gold): silver={'flat_structure': True}, gold={'mode': 'scd2', 'scd_config': {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}, 'flat_structure': True}

2. Bronze Layer

- Формат хранения: ожидается JSONL + zstd (см. BronzeWriter); фактический артефакт: `MISSING`.
- Структура записи:
  - Минимальный пример JSON: GAP (raw sample not found in repository artifacts for this pipeline).
  - Ключевые JSON paths: INFERRED from API/Pydantic model + transformer.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts` (общий metadata contract).
- Потенциальный schema drift: INFERRED from Pydantic+transformer.
- Проблемы: nested JSON / multi-type поля зависят от provider API; требуется профилирование сырого JSONL.

3. Silver Schema
   | Поле | Тип | Nullable | Source field | Notes |
   |\---|---|---:|---|---|
   | entity_id | string | UNKNOWN | generated | present in PUBMED_PUBLICATION_SCHEMA |
   | content_hash | string | UNKNOWN | generated | canonical hash |
   | \_run_id | string | UNKNOWN | metadata | metadata unified |
   | pmid | UNKNOWN | UNKNOWN | source API field | business/merge key candidate |
   Анализ:

- Типы (int→float coercion?): UNKNOWN per-pipeline; Pandera class `PubMedPublicationSchema` exists for most pipelines.
- Nullable consistency: частично покрыто Pandera+PyArrow, но полная матрица Pandera↔Delta требует runtime schema dump (GAP).
- DQ flags / checks: внешние entity/provider YAML по ADR-027; inline DQ минимален.
- Hash exclusions: META_FIELDS исключаются из content hash.
- Ordering policy: canonical column ordering перед записью.
- Schema drift tolerance: Silver поддерживает policy error/evolve/ignore.
- Partition keys: []/MISSING.
- Merge key correctness: использует primary_keys из pipeline config; корректность зависит от стабильности source IDs.

4. Gold Schema (Контракт)

- Контрактная версия: explicit version field в contract class отсутствует (GAP).
- SCD2 / overwrite / append: scd2
- Стабильность API: strict Pandera required на Gold writer (ADR-018).
- Backward compatibility: drift не допускается без контрактных изменений; version bump process не формализован в коде (GAP).
- Breaking risk: средний/высокий для PK/type/nullable изменений; низкий для add nullable column.

| Поле                                           | Тип                |      Nullable | Semantic role       | Breaking risk |
| ---------------------------------------------- | ------------------ | ------------: | ------------------- | ------------- |
| entity_id                                      | string             |       UNKNOWN | stable entity key   | HIGH          |
| content_hash                                   | string             |       UNKNOWN | version fingerprint | MEDIUM        |
| pmid                                           | UNKNOWN            |       UNKNOWN | business key        | HIGH          |
| \_valid_from/\_valid_to/\_is_current/\_version | timestamp/bool/int | mode-specific | SCD2 system columns | MEDIUM        |

5. Domain ↔ Schema соответствие

- 1:1 mapping?: Частично, для publication-family много flatten/normalization.
- Поля отсутствуют в доменной модели?: UNKNOWN (нужен автоматический diff domain entity ↔ contract).
- Поля есть в домене, но не в таблице?: UNKNOWN/GAP.
- Нарушение Single Source of Truth?: риск средний из-за параллельного существования domain entities, Pandera schema, Gold contract, YAML schema config.
  Evidence:
- configs/pipelines/pubmed/publication.yaml
- src/bioetl/composition/factories/pipeline_factories.py
- src/bioetl/infrastructure/schemas/silver.py (PUBMED_PUBLICATION_SCHEMA)
- src/bioetl/domain/contracts/gold/\*.py (PubMedPublicationGoldSchema)
- src/bioetl/domain/schemas/\*\*/\* (PubMedPublicationSchema)

### semanticscholar_publication

1. Общая информация

- Provider: semanticscholar
- Entity: publication
- Pipeline name / pipeline_id: semanticscholar_publication
- Primary keys: ['paper_id']
- Loading strategy: full_scan_only
- Write mode (Silver/Gold): silver={'flat_structure': True}, gold={'mode': 'scd2', 'scd_config': {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}, 'flat_structure': True}

2. Bronze Layer

- Формат хранения: ожидается JSONL + zstd (см. BronzeWriter); фактический артефакт: `MISSING`.
- Структура записи:
  - Минимальный пример JSON: GAP (raw sample not found in repository artifacts for this pipeline).
  - Ключевые JSON paths: INFERRED from API/Pydantic model + transformer.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts` (общий metadata contract).
- Потенциальный schema drift: INFERRED from Pydantic+transformer.
- Проблемы: nested JSON / multi-type поля зависят от provider API; требуется профилирование сырого JSONL.

3. Silver Schema
   | Поле | Тип | Nullable | Source field | Notes |
   |\---|---|---:|---|---|
   | entity_id | string | UNKNOWN | generated | present in SEMANTICSCHOLAR_PUBLICATION_SCHEMA |
   | content_hash | string | UNKNOWN | generated | canonical hash |
   | \_run_id | string | UNKNOWN | metadata | metadata unified |
   | paper_id | UNKNOWN | UNKNOWN | source API field | business/merge key candidate |
   Анализ:

- Типы (int→float coercion?): UNKNOWN per-pipeline; Pandera class `SemanticScholarPublicationSchema` exists for most pipelines.
- Nullable consistency: частично покрыто Pandera+PyArrow, но полная матрица Pandera↔Delta требует runtime schema dump (GAP).
- DQ flags / checks: внешние entity/provider YAML по ADR-027; inline DQ минимален.
- Hash exclusions: META_FIELDS исключаются из content hash.
- Ordering policy: canonical column ordering перед записью.
- Schema drift tolerance: Silver поддерживает policy error/evolve/ignore.
- Partition keys: []/MISSING.
- Merge key correctness: использует primary_keys из pipeline config; корректность зависит от стабильности source IDs.

4. Gold Schema (Контракт)

- Контрактная версия: explicit version field в contract class отсутствует (GAP).
- SCD2 / overwrite / append: scd2
- Стабильность API: strict Pandera required на Gold writer (ADR-018).
- Backward compatibility: drift не допускается без контрактных изменений; version bump process не формализован в коде (GAP).
- Breaking risk: средний/высокий для PK/type/nullable изменений; низкий для add nullable column.

| Поле                                           | Тип                |      Nullable | Semantic role       | Breaking risk |
| ---------------------------------------------- | ------------------ | ------------: | ------------------- | ------------- |
| entity_id                                      | string             |       UNKNOWN | stable entity key   | HIGH          |
| content_hash                                   | string             |       UNKNOWN | version fingerprint | MEDIUM        |
| paper_id                                       | UNKNOWN            |       UNKNOWN | business key        | HIGH          |
| \_valid_from/\_valid_to/\_is_current/\_version | timestamp/bool/int | mode-specific | SCD2 system columns | MEDIUM        |

5. Domain ↔ Schema соответствие

- 1:1 mapping?: Частично, для publication-family много flatten/normalization.
- Поля отсутствуют в доменной модели?: UNKNOWN (нужен автоматический diff domain entity ↔ contract).
- Поля есть в домене, но не в таблице?: UNKNOWN/GAP.
- Нарушение Single Source of Truth?: риск средний из-за параллельного существования domain entities, Pandera schema, Gold contract, YAML schema config.
  Evidence:
- configs/pipelines/semanticscholar/publication.yaml
- src/bioetl/composition/factories/pipeline_factories.py
- src/bioetl/infrastructure/schemas/silver.py (SEMANTICSCHOLAR_PUBLICATION_SCHEMA)
- src/bioetl/domain/contracts/gold/\*.py (SemanticScholarPublicationGoldSchema)
- src/bioetl/domain/schemas/\*\*/\* (SemanticScholarPublicationSchema)

### uniprot_idmapping

1. Общая информация

- Provider: uniprot
- Entity: idmapping
- Pipeline name / pipeline_id: uniprot_idmapping
- Primary keys: ['target_id']
- Loading strategy: incremental/default (implicit)
- Write mode (Silver/Gold): silver={'partition_by': []}, gold={'mode': 'scd2', 'scd_config': {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}}

2. Bronze Layer

- Формат хранения: ожидается JSONL + zstd (см. BronzeWriter); фактический артефакт: `MISSING`.
- Структура записи:
  - Минимальный пример JSON: GAP (raw sample not found in repository artifacts for this pipeline).
  - Ключевые JSON paths: INFERRED from API/Pydantic model + transformer.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts` (общий metadata contract).
- Потенциальный schema drift: INFERRED from Pydantic+transformer.
- Проблемы: nested JSON / multi-type поля зависят от provider API; требуется профилирование сырого JSONL.

3. Silver Schema
   | Поле | Тип | Nullable | Source field | Notes |
   |\---|---|---:|---|---|
   | entity_id | string | UNKNOWN | generated | present in UNIPROT_ID_MAPPING_SCHEMA |
   | content_hash | string | UNKNOWN | generated | canonical hash |
   | \_run_id | string | UNKNOWN | metadata | metadata unified |
   | target_id | UNKNOWN | UNKNOWN | source API field | business/merge key candidate |
   Анализ:

- Типы (int→float coercion?): UNKNOWN per-pipeline; Pandera class `IDMappingSchema` exists for most pipelines.
- Nullable consistency: частично покрыто Pandera+PyArrow, но полная матрица Pandera↔Delta требует runtime schema dump (GAP).
- DQ flags / checks: внешние entity/provider YAML по ADR-027; inline DQ минимален.
- Hash exclusions: META_FIELDS исключаются из content hash.
- Ordering policy: canonical column ordering перед записью.
- Schema drift tolerance: Silver поддерживает policy error/evolve/ignore.
- Partition keys: [].
- Merge key correctness: использует primary_keys из pipeline config; корректность зависит от стабильности source IDs.

4. Gold Schema (Контракт)

- Контрактная версия: explicit version field в contract class отсутствует (GAP).
- SCD2 / overwrite / append: scd2
- Стабильность API: strict Pandera required на Gold writer (ADR-018).
- Backward compatibility: drift не допускается без контрактных изменений; version bump process не формализован в коде (GAP).
- Breaking risk: средний/высокий для PK/type/nullable изменений; низкий для add nullable column.

| Поле                                           | Тип                |      Nullable | Semantic role       | Breaking risk |
| ---------------------------------------------- | ------------------ | ------------: | ------------------- | ------------- |
| entity_id                                      | string             |       UNKNOWN | stable entity key   | HIGH          |
| content_hash                                   | string             |       UNKNOWN | version fingerprint | MEDIUM        |
| target_id                                      | UNKNOWN            |       UNKNOWN | business key        | HIGH          |
| \_valid_from/\_valid_to/\_is_current/\_version | timestamp/bool/int | mode-specific | SCD2 system columns | MEDIUM        |

5. Domain ↔ Schema соответствие

- 1:1 mapping?: Частично, для publication-family много flatten/normalization.
- Поля отсутствуют в доменной модели?: UNKNOWN (нужен автоматический diff domain entity ↔ contract).
- Поля есть в домене, но не в таблице?: UNKNOWN/GAP.
- Нарушение Single Source of Truth?: риск средний из-за параллельного существования domain entities, Pandera schema, Gold contract, YAML schema config.
  Evidence:
- configs/pipelines/uniprot/idmapping.yaml
- src/bioetl/composition/factories/pipeline_factories.py
- src/bioetl/infrastructure/schemas/silver.py (UNIPROT_ID_MAPPING_SCHEMA)
- src/bioetl/domain/contracts/gold/\*.py (UniProtIDMappingGoldSchema)
- src/bioetl/domain/schemas/\*\*/\* (IDMappingSchema)

### uniprot_protein

1. Общая информация

- Provider: uniprot
- Entity: protein
- Pipeline name / pipeline_id: uniprot_protein
- Primary keys: ['accession']
- Loading strategy: incremental/default (implicit)
- Write mode (Silver/Gold): silver={'partition_by': ['organism']}, gold={'mode': 'scd2', 'scd_config': {'valid_from': '\_valid_from', 'valid_to': '\_valid_to', 'is_current': '\_is_current', 'version': '\_version'}}

2. Bronze Layer

- Формат хранения: ожидается JSONL + zstd (см. BronzeWriter); фактический артефакт: `data/output/bronze/uniprot/protein`.
- Структура записи:
  - Минимальный пример JSON: GAP (raw sample not found in repository artifacts for this pipeline).
  - Ключевые JSON paths: INFERRED from API/Pydantic model + transformer.
- Поля метаданных: `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts` (общий metadata contract).
- Потенциальный schema drift: Artifact exists but contains metadata snapshot JSON, not raw JSONL stream.
- Проблемы: nested JSON / multi-type поля зависят от provider API; требуется профилирование сырого JSONL.

3. Silver Schema
   | Поле | Тип | Nullable | Source field | Notes |
   |\---|---|---:|---|---|
   | entity_id | string | UNKNOWN | generated | present in UNIPROT_PROTEIN_SCHEMA |
   | content_hash | string | UNKNOWN | generated | canonical hash |
   | \_run_id | string | UNKNOWN | metadata | metadata unified |
   | accession | UNKNOWN | UNKNOWN | source API field | business/merge key candidate |
   Анализ:

- Типы (int→float coercion?): UNKNOWN per-pipeline; Pandera class `UniprotTargetSchema` exists for most pipelines.
- Nullable consistency: частично покрыто Pandera+PyArrow, но полная матрица Pandera↔Delta требует runtime schema dump (GAP).
- DQ flags / checks: внешние entity/provider YAML по ADR-027; inline DQ минимален.
- Hash exclusions: META_FIELDS исключаются из content hash.
- Ordering policy: canonical column ordering перед записью.
- Schema drift tolerance: Silver поддерживает policy error/evolve/ignore.
- Partition keys: ['organism'].
- Merge key correctness: использует primary_keys из pipeline config; корректность зависит от стабильности source IDs.

4. Gold Schema (Контракт)

- Контрактная версия: explicit version field в contract class отсутствует (GAP).
- SCD2 / overwrite / append: scd2
- Стабильность API: strict Pandera required на Gold writer (ADR-018).
- Backward compatibility: drift не допускается без контрактных изменений; version bump process не формализован в коде (GAP).
- Breaking risk: средний/высокий для PK/type/nullable изменений; низкий для add nullable column.

| Поле                                           | Тип                |      Nullable | Semantic role       | Breaking risk |
| ---------------------------------------------- | ------------------ | ------------: | ------------------- | ------------- |
| entity_id                                      | string             |       UNKNOWN | stable entity key   | HIGH          |
| content_hash                                   | string             |       UNKNOWN | version fingerprint | MEDIUM        |
| accession                                      | UNKNOWN            |       UNKNOWN | business key        | HIGH          |
| \_valid_from/\_valid_to/\_is_current/\_version | timestamp/bool/int | mode-specific | SCD2 system columns | MEDIUM        |

5. Domain ↔ Schema соответствие

- 1:1 mapping?: Частично, для publication-family много flatten/normalization.
- Поля отсутствуют в доменной модели?: UNKNOWN (нужен автоматический diff domain entity ↔ contract).
- Поля есть в домене, но не в таблице?: UNKNOWN/GAP.
- Нарушение Single Source of Truth?: риск средний из-за параллельного существования domain entities, Pandera schema, Gold contract, YAML schema config.
  Evidence:
- configs/pipelines/uniprot/protein.yaml
- src/bioetl/composition/factories/pipeline_factories.py
- src/bioetl/infrastructure/schemas/silver.py (UNIPROT_PROTEIN_SCHEMA)
- src/bioetl/domain/contracts/gold/\*.py (UniProtProteinGoldSchema)
- src/bioetl/domain/schemas/\*\*/\* (UniprotTargetSchema)

## II. Архитектурные проблемы

| ID   | Pipeline                                             | Категория                | Проблема                                                                                                 | Риск   | Приоритет |
| ---- | ---------------------------------------------------- | ------------------------ | -------------------------------------------------------------------------------------------------------- | ------ | --------- |
| A-01 | \*                                                   | Schema duplication       | Domain entities + Pandera + Gold contracts + YAML schema overlays создают множественные источники схемы. | High   | P1        |
| A-02 | publication pipelines                                | Hidden coupling          | rename chain и field groups завязаны на порядок применения Silver→Gold.                                  | Medium | P2        |
| A-03 | \*                                                   | Nullable ambiguity       | Явные nullable матрицы Pandera↔PyArrow↔Delta не материализованы в одном месте.                           | Medium | P2        |
| A-04 | chembl_publication_term, chembl_subcellular_fraction | Weak primary key         | hash-prefix/entity_id ключи могут коллидировать при неверной нормализации.                               | Medium | P2        |
| A-05 | \*                                                   | Content hash instability | нормализация null/missing и nested dict order чувствительны к schema drift.                              | Medium | P2        |
| A-06 | \*                                                   | Inconsistent naming      | entity_type vs table/class naming (publication/document/work) усложняет трассировку.                     | Low    | P3        |

## III. Общесистемные проблемы

- Повторяющиеся поля: `entity_id`, `content_hash`, `_run_id`, `_run_type`, `_source_batch_id` во всех Silver/Gold (ожидаемо), но правила nullable/semantic role не централизованы в одном контракте.
- Несогласованные типы между пайплайнами: publication-семейство имеет разные представления авторов/идентификаторов (list[string] vs flattened string).
- OutputMetadata унификация: ADR-029 реализован частично через модели metadata, но не все артефакты в `data/output/bronze` содержат raw records+унифицированные поля одновременно.
- Избыточная ширина: publication/openalex/pubmed/crossref Gold контракты широкие (44-62 полей).
- Nullable-int coercion риски: при чтении pandas возможен int→float для nullable целочисленных колонок (требует явной dtype policy).
- SCD2 consistency: большинство pipeline в SCD2, но есть append/overwrite исключения → нужен governance список исключений.
- Partition strategy: часть pipeline имеет semantic partitions, часть `[]`; консистентность и skews не документированы.

## IV. План улучшений

1. Немедленные улучшения (Low Risk)

- Сгенерировать machine-readable schema matrix (Pandera/PyArrow/Gold) per pipeline. Impact: высокая наблюдаемость; Breaking: Non-breaking; ADR: нет; Миграция: добавить CI-отчёт.
- Добавить raw Bronze shape профилирование (JSON paths + type frequencies) в metadata sidecar. Impact: drift visibility; Breaking: Non-breaking; ADR: нет.

2. Среднесрочные улучшения (Refactoring Phase)

- Ввести единый Schema Registry artifact (single source for nullable/type/order). Impact: снизить дублирование; Breaking: Potentially breaking for tooling; ADR: да.
- Формализовать versioning Gold contracts (semver + changelog + bump guard). Impact: ADR-018 compliance; Breaking: Non-breaking runtime, process change.

3. Архитектурные изменения (Breaking Phase)

- Унифицировать rename chain DSL и автоматическую верификацию Silver→Gold. Impact: снижение hidden coupling; Breaking: breaking for existing YAMLs; ADR: да.
- Нормализовать key strategy (provider-scoped PK + collision budget + deterministic canonicalization profile v2). Impact: data correctness; Breaking: да; Миграция: dual-write + backfill + hash_v1/hash_v2 coexistence.

## V. Target Schema Architecture (Целевая модель)

- Bronze: обязательный raw JSONL.zst + sidecar profile (paths/types/presence) per batch.
- Silver: единый declarative contract (columns/type/nullable/order/checks/partition/merge keys) генерирует Pandera + PyArrow + Delta DDL.
- Gold: strict API contract с версионированием, compatibility matrix и CI diff gate (ADR-018).
- Metadata policy: единый набор `_run_id`, `_run_type`, `_ingestion_ts`, `_source_batch_id`, lineage refs (ADR-029).
- Key strategy: provider-scoped business key + deterministic entity_id + content_hash profile versioning.
- Типовая структура таблиц: core business columns → standardized metadata tail → optional dq columns suffix.

Критерии качества схем (чеклист):

- [ ] Нет дублирования бизнес-полей.
- [ ] Типы стабильны между слоями.
- [ ] Nullable политика консистентна.
- [ ] Primary key семантически корректен.
- [ ] Content Hash детерминирован.
- [ ] Нет hidden coupling между пайплайнами.
- [ ] Breaking изменения контролируемы.
- [ ] Schema drift управляем.
