# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Gold Layer Transformation**: Реализована трансформация Silver → Gold с исключением JSON полей
  - Добавлен `GoldTransformCallback` protocol в `application/core/protocols.py`
  - Добавлен метод `transform_for_gold()` в `BasePipeline` с константой `GOLD_EXCLUDE_FIELDS`
  - `RecordProcessor` теперь применяет Gold-трансформацию перед записью
  - `ChEMBLMoleculeGoldSchema` расширена 27 плоскими полями (hierarchy_*, property_*, structure_*)

- **Unified Transformers**: Унифицированы трансформеры всех пайплайнов
  - Добавлен `TransformerPort` protocol в `application/core/protocols.py`
  - Добавлен `BaseTransformer` с Template Method паттерном
  - Все трансформеры ChEMBL/PubChem/PubMed/UniProt унифицированы

- **E2E Tests**: Добавлен полный набор E2E-тестов для Local-Only архитектуры (`tests/e2e/`)
  - `test_chembl_activity_full_cycle` - полный цикл ChEMBL Activity pipeline
  - `test_chembl_target_full_cycle` - полный цикл ChEMBL Target pipeline
  - `test_chembl_molecule_full_cycle` - полный цикл ChEMBL Molecule pipeline
  - `test_chembl_document_full_cycle` - полный цикл ChEMBL Document pipeline
  - `test_uniprot_protein_full_cycle` - полный цикл UniProt Protein pipeline
  - `test_pipeline_idempotency` - проверка идемпотентности merge/upsert
  - `test_pipeline_resume_from_checkpoint` - проверка возобновления с чекпоинта
- **E2E Helpers**: Добавлены helper-функции для E2E-тестов в `tests/e2e/conftest.py`:
  - `create_test_context()` - создание контекста пайплайна
  - `assert_bronze_files_exist()` - проверка Bronze-файлов
  - `assert_silver_table_has_records()` - проверка Silver Delta-таблицы
  - `assert_gold_table_has_records()` - проверка Gold Delta-таблицы

### Fixed

- **Atomic Write Encoding**: `atomic_write()` теперь поддерживает параметр `encoding` для
  корректной записи UTF-8 на Windows (ранее использовалась системная кодировка cp1251)
- **DQ Metrics**: `BatchMetricsRecorder.track_quarantined_records()` теперь включает `run_type`
  в метки метрик для лучшей observability
- **CLI Safety**: Исправлена логика `--dry-run` для rebuild/backfill — теперь показывает preview
  без вызова bootstrap (раннее завершение)
- **GoldValidator Protocol Compliance**: Исправлен возврат `ValidationResult` вместо `list[dict]`
  в `PanderaGoldValidator` и `NoOpGoldValidator` для соответствия `GoldValidatorPort` протоколу.
  Ранее вызывало `AttributeError: 'list' object has no attribute 'valid'` в E2E тестах.
- **Integration Tests**: Добавлен обязательный параметр `run_id` в тесты пайплайнов
  `test_pubchem_pipeline.py` и `test_uniprot_pipeline.py` (требуется после изменения сигнатуры BasePipeline).
- **Target Pipeline**: Исправлено извлечение `cross_references` - теперь агрегируется из
  `target_components[].target_component_xrefs[]` вместо пустого поля на уровне target
- **PubChem Tests**: Исправлены тесты PubChemClient (удалён неиспользуемый параметр `watermark`)
- **CheckpointManager**: Удалён параметр `watermark_extractor` из `GenericPipelineFactory`
- **Config Snapshots**: Удалено поле `watermark_field` из golden master snapshots
- **Target Component Config**: Добавлен `forensic_retention: true` в `target_component.yaml`

### Changed

- **E2E Conftest**: Переработан `tests/e2e/conftest.py` для Local-Only архитектуры
  (удалены зависимости от Docker/MinIO/Redis)

### Removed

- **interfaces/factories/**: Удалён неиспользуемый пакет `src/bioetl/interfaces/factories/`

### BREAKING CHANGES

- **ChEMBL Molecule Gold Schema**: JSON поля исключены из Gold слоя:
  - Удалены: `molecule_hierarchy`, `molecule_properties`, `molecule_structures`,
    `molecule_synonyms`, `cross_references`, `atc_classifications`
  - Добавлены плоские поля: `hierarchy_parent_chembl_id`, `hierarchy_active_chembl_id`,
    `property_mw_freebase`, `property_alogp`, `property_hba`, `property_hbd`,
    `property_psa`, `property_rtb`, `property_ro5_violations`, `property_qed_weighted`,
    `property_full_molformula`, `structure_canonical_smiles`, `structure_standard_inchi`,
    `structure_standard_inchi_key`
  - Silver слой сохраняет JSON для forensic целей
  - **Migration**: Выполнить `--run-type=rebuild` для chembl_molecule

- **BasePipeline signature changed**: Constructor now requires `run_id` as 4th parameter:
  `BasePipeline(config, runtime, services, run_id)`. This ensures consistent run identification
  across all components (logs, metrics, checkpoints). See ADR-012.

- **StoragePort extended**: Added `clear_silver(table_name)` and `clear_gold(table_name)` methods
  to `StoragePort` protocol. Custom storage adapters MUST implement these methods.

- **Medallion invariants enforced**: `PipelineRunner._clear_exports()` now only clears data for
  `rebuild`/`backfill` runs. Incremental runs use merge/upsert without clearing existing data.

- Removed deprecated `BasePipeline.from_params()` method. Use the constructor with 4 parameters.
