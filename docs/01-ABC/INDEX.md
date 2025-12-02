# ABC Index

Каталог абстрактно-базовых классов (ABC) проекта BioETL.

<!-- generated -->

## Overview

Этот каталог содержит документацию для всех абстрактных базовых классов (ABC) и протоколов проекта. Каждый ABC определяет контракт для конкретной области ответственности в пайплайне обработки данных.

## ABC Classes

| # | ABC Class | Description | File |
|---|-----------|-------------|------|
| 00 | [BusinessKeyDeriverABC](00-business-key-deriver-abc.md) | Вычисление бизнес-ключа записи для дедупликации | `00-business-key-deriver-abc.md` |
| 01 | [CacheABC](01-cache-abc.md) | Абстрактный кэш | `01-cache-abc.md` |
| 02 | [CLICommandABC](02-cli-command-abc.md) | Интерфейс для плагинной команды CLI | `02-cli-command-abc.md` |
| 03 | [ConfigResolverABC](03-config-resolver-abc.md) | Загрузка и объединение конфигурации | `03-config-resolver-abc.md` |
| 04 | [DeduplicatorABC](04-deduplicator-abc.md) | Удаление дубликатов из потока записей | `04-deduplicator-abc.md` |
| 05 | [DQRuleABC](05-dq-rule-abc.md) | Правило контроля качества данных | `05-dq-rule-abc.md` |
| 06 | [ErrorPolicyABC](06-error-policy-abc.md) | Стратегия реакции на ошибки в пайплайне | `06-error-policy-abc.md` |
| 07 | [HasherABC](07-hasher-abc.md) | Интерфейс хеширования записей и ключей | `07-hasher-abc.md` |
| 08 | [LoggerAdapterABC](08-logger-adapter-abc.md) | Интерфейс структурированного логгера | `08-logger-adapter-abc.md` |
| 09 | [LookupEnricherABC](09-lookup-enricher-abc.md) | Обогащение записи на основе внешнего словаря | `09-lookup-enricher-abc.md` |
| 10 | [MergeStrategyABC](10-merge-strategy-abc.md) | Объединение дубликатов с одним бизнес-ключом | `10-merge-strategy-abc.md` |
| 11 | [MetadataWriterABC](11-metadata-writer-abc.md) | Сохранение служебных метаданных | `11-metadata-writer-abc.md` |
| 12 | [PaginatorABC](12-paginator-abc.md) | Стратегия постраничного обхода | `12-paginator-abc.md` |
| 13 | [PathStrategyABC](13-path-strategy-abc.md) | Правила построения путей вывода данных | `13-path-strategy-abc.md` |
| 14 | [PipelineHookABC](14-pipeline-hook-abc.md) | Хуки наблюдения за выполнением пайплайна | `14-pipeline-hook-abc.md` |
| 15 | [ProgressReporterABC](15-progress-reporter-abc.md) | Агрегированная отчётность о ходе выполнения | `15-progress-reporter-abc.md` |
| 16 | [RateLimiterABC](16-rate-limiter-abc.md) | Ограничение частоты запросов и параллелизма | `16-rate-limiter-abc.md` |
| 17 | [RequestBuilderABC](17-request-builder-abc.md) | Построение транспортных запросов к источникам | `17-request-builder-abc.md` |
| 18 | [ResponseParserABC](18-response-parser-abc.md) | Разбор транспортных ответов во входные записи | `18-response-parser-abc.md` |
| 19 | [RetryPolicyABC](19-retry-policy-abc.md) | Стратегия повторных попыток при ошибках | `19-retry-policy-abc.md` |
| 20 | [SchemaProviderABC](20-schema-provider-abc.md) | Поставка объекта схемы данных для валидации | `20-schema-provider-abc.md` |
| 21 | [SecretProviderABC](21-secret-provider-abc.md) | Доступ к секретным данным | `21-secret-provider-abc.md` |
| 22 | [SideInputProviderABC](22-side-input-provider-abc.md) | Доступ к сайд-инпутам для обогащения | `22-side-input-provider-abc.md` |
| 23 | [SourceClientABC](23-source-client-abc.md) | Клиент для общения с внешним источником данных | `23-source-client-abc.md` |
| 24 | [StageABC](24-stage-abc.md) | Стадия конвейера обработки данных | `24-stage-abc.md` |
| 25 | [TracerABC](25-tracer-abc.md) | Интерфейс трассировки метрик | `25-tracer-abc.md` |
| 26 | [TransformerABC](26-transformer-abc.md) | Преобразование записи в нормализованную форму | `26-transformer-abc.md` |
| 27 | [ValidatorABC](27-validator-abc.md) | Проверка записи по схеме | `27-validator-abc.md` |
| 28 | [WriterABC](28-writer-abc.md) | Запись коллекции записей в хранилище | `28-writer-abc.md` |

## Adding New ABC Classes

При добавлении нового ABC класса:

1. Создайте файл документации в формате `NN-<name>-abc.md` (kebab-case)
2. Обновите этот индексный файл
3. Обновите `src/bioetl/clients/base/abc_registry.yaml`
4. Обновите `src/bioetl/clients/base/abc_impls.yaml`
