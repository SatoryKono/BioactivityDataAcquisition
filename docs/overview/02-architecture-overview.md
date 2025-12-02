# Architecture Overview

## Диаграмма уровней

Архитектура BioETL построена по слоистому принципу (Layered Architecture) с четким разделением ответственности.

```text
┌─────────────────────────────────────────────────┐
│           CLI / Orchestration Layer             │
│  CLICommandABC, PipelineBase, StageDescriptor   │
│  (Управление запуском, стадиями, ресурсами)     │
├─────────────────────────────────────────────────┤
│              Monitoring Layer                   │
│  PipelineHookABC, LoggerAdapterABC, TracerABC   │
│  (Логирование, метрики, трассировка, прогресс)  │
├─────────────────────────────────────────────────┤
│             Data Access Layer                   │
│  SourceClientABC, RequestBuilderABC, CacheABC   │
│  (HTTP-запросы, пагинация, ретраи, лимиты)      │
├─────────────────────────────────────────────────┤
│           Transformation Layer                  │
│  TransformerABC, LookupEnricherABC, HasherABC   │
│  (Нормализация, очистка, дедупликация, ключи)   │
├─────────────────────────────────────────────────┤
│          Schema & Validation Layer              │
│  Pandera schemas, ValidatorABC, SchemaRegistry  │
│  (Проверка типов, форматов, обязательных полей) │
├─────────────────────────────────────────────────┤
│               Output Layer                      │
│  WriterABC, MetadataWriterABC, QC artifacts     │
│  (Атомарная запись, метаданные, отчеты качества)│
└─────────────────────────────────────────────────┘
```

## Ключевые принципы

### 1. Детерминизм
Идентичные входные данные и конфигурация должны давать **битово-идентичный** результат.
- Стабильная сортировка строк и колонок.
- UTC-время для всех timestamp.
- Каноническая сериализация JSON.

### 2. Validate-before-write
Никакие данные не записываются в итоговое хранилище без успешной валидации через Pandera-схему.
- Строгая типизация.
- Проверка форматов (Regex для ID).
- Фиксированный порядок колонок (`column_order`).

### 3. Structured Logging
Использование только `UnifiedLogger` для генерации структурированных логов (JSON/Key-Value). `print()` запрещен.

### 4. Unified API Access
Все внешние запросы идут через `UnifiedAPIClient`, который обеспечивает:
- Automatic Retries (exponential backoff).
- Rate Limiting (token bucket).
- Circuit Breaker (предотвращение каскадных сбоев).

## Поток данных (Data Flow)

Стандартный цикл выполнения пайплайна:

`extract` (извлечение сырых данных) → `transform` (нормализация и обогащение) → `validate` (проверка схемы) → `write` (сохранение).

Подробнее см. [Data Flow](../architecture/03-data-flow.md).

## Ссылки
- [Детальное описание слоев (ETL Layers)](../architecture/02-etl-layers.md)
- [ABC-объекты домена](../architecture/01-domain-objects.md)

