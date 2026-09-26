# Tracing Guide

## Overview

BioETL использует distributed tracing для отслеживания выполнения pipeline через компоненты системы.

## Trace Context

`run_id` и trace context имеют разные назначения:

- `run_id` — UUID control-plane запуска. Он остаётся основным идентификатором
  прогона в логах, manifest/ledger и replay-поверхностях.
- `trace_id` и `span_id` — идентификаторы OpenTelemetry span context. При
  активном span runtime представляет их как lowercase hex: 32 символа для
  `trace_id` и 16 символов для `span_id`.
- Если активного span нет, `trace_id` и `span_id` отсутствуют. Runtime не
  синтезирует их из UUID и не подменяет ими `run_id`.

## Span Propagation

Spans распространяются через контекст выполнения:

```python
with tracer.start_as_current_span("pipeline_execution") as span:
    span.set_attribute("pipeline_name", pipeline_name)
    span.set_attribute("bioetl.run_id", str(run_id))

    # Child span
    with tracer.start_as_current_span("data_fetch"):
        # fetch data
```

## Key Spans

- `pipeline_execution`: Весь pipeline execution
- `data_fetch`: Fetch данных из provider
- `transform`: Transform данных
- `validation`: Validation данных
- `storage_write`: Запись в storage
- `checkpoint`: Checkpoint операция

## Trace Export

Tracing данные экспортируются в OpenTelemetry-compatible backend, если он
настроен. `logging_config.trace_context_processor` автоматически добавляет
идентификаторы активного span в structured logs; `run_id` передаётся отдельно
через runtime/control-plane context.

## Configuration

Tracing конфигурируется через `src/bioetl/infrastructure/observability/tracing.py`.

## Best Practices

1. Создавать spans для значимых операций
2. Добавлять атрибуты к spans для контекста
3. Использовать span links для асинхронных операций
4. Избегать создания слишком многих spans для производительности
