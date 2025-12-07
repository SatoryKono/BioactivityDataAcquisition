# 00 Common Logic

## Текущая реализация

- Базовый класс: `ChemblPipelineBase` (`src/bioetl/application/pipelines/chembl/base.py`) — собирает `ChemblExtractorImpl`, `ChemblTransformerImpl`, `HashService`, `ValidationService`, `UnifiedOutputWriter`.
- DI и провайдеры: `PipelineContainer` + `ProviderRegistryLoader` (`configs/providers.yaml`) регистрируют `ChemblProviderComponentsFactory` и создают клиента/сервис экстракции/нормализации.
- Универсальный пайплайн: `ChemblPipelineBase` (`base.py`) используется напрямую для любой сущности; `primary_key` берётся из `PipelineConfig` (`primary_key` или `pipeline.primary_key`, иначе `<entity>_id`).
- Экстрактор: `ChemblExtractorImpl` (`extractor.py`) — режимы `input_mode`: `api` (по умолчанию), `csv`, `id_only`; использует `CsvRecordSourceImpl`/`IdListRecordSourceImpl` без эвристик колонок.
- Трансформер: `ChemblTransformerImpl` (`transformer.py`) — последовательность `pre_transform -> do_transform -> normalize -> enforce_schema -> drop_nulls(required)`; обязательные столбцы подтягиваются из `PipelineSchemaModel`.
- Хуки: `LoggingPipelineHookImpl` + `MetricsPipelineHookImpl` (Prometheus метрики стадий) через `HooksManager`/`StageRunnerFacade`; политика ошибок по умолчанию `FailFastErrorPolicyImpl`.

## Жизненный цикл (run)

1) `iter_chunks` вызывает `ChemblExtractorImpl` (API/CSV/ID list).  
2) `transform` применяет `ChemblTransformerImpl` + post-transform цепочку по умолчанию (`HashColumnsTransformerImpl`, `IndexColumnTransformerImpl`, `DatabaseVersionTransformerImpl`, `FulldateTransformerImpl`).
3) `validate` использует `ValidationService` + Pandera-схемы (`domain/schemas/chembl/*`).  
4) `write` — `UnifiedOutputWriter`: стабильная сортировка по `hashing.business_key_fields`, атомарная запись `<entity>.csv`, checksum, `meta.yaml`.  
5) Error handling — `ErrorPolicyABC` (по умолчанию fail-fast; retry/skip через хуки). Все события проходят через `PipelineHookABC`.

## Конфигурация

- Файл пайплайна: `configs/pipelines/chembl/<entity>.yaml`.
- Ключевые поля: `input_mode`, `input_path`, `csv_options`, `primary_key`, `hashing.business_key_fields`, `provider`, `entity_name`.
- Для сухого прогона использовать `--dry-run`; для уменьшения выборки — `--limit`.
