# 00 Activity Chembl Overview

## Pipeline

**ChemblActivityPipeline** (`src/bioetl/application/pipelines/chembl/activity/run.py`) наследует `ChemblPipelineBase` и реализует поток ETL для сущности Activity.

## Компоненты

- `extract_activity` (`src/bioetl/application/pipelines/chembl/activity/extract.py`) — orchestration точки входа extract-стадии.
- `ChemblExtractionService` (`src/bioetl/domain/services/chembl/extraction_service.py`) — загрузка сырых активностей из API или CSV.
- `ChemblResponseParser` (`src/bioetl/domain/services/chembl/response_parser.py`) — разбор и стандартизация ответов ChEMBL перед нормализацией.
- `normalize_fields` (`NormalizerMixin` в `src/bioetl/application/pipelines/chembl/base.py`) — финальное приведение типов и очистка строковых/числовых полей.
- `HashService` (`src/bioetl/domain/services/hashing.py`) — расчет `hash_business_key` и `hash_row` для детерминированной дедупликации.
- `UnifiedOutputWriter` (`src/bioetl/infrastructure/writers/unified_output_writer.py`) — атомарная запись итоговых таблиц и побочных артефактов.

## Особенности

- **CSV input**: explicit control via `input_mode` (`csv` for full dataset, `id_only` for ID lists) and `input_path`; `csv_options` configures delimiter/header without column heuristics.
- **Хеширование**: хеши рассчитываются после нормализации; набор полей для бизнес-ключа задается в `hashing.business_key_fields`, что обеспечивает воспроизводимое устранение дублей.

## Конфигурация

Файл: `configs/pipelines/chembl/activity.yaml`
Наследует: `configs/profiles/chembl_default.yaml`

## Зависимости

Опирается на базовые компоненты инфраструктуры: `UnifiedAPIClient`, `ConfigResolver`, `UnifiedLogger`.
