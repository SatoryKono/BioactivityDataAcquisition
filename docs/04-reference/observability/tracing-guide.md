# Tracing Guide

## Overview

BioETL использует distributed tracing для отслеживания выполнения pipeline через компоненты системы.

## Trace Context

Каждый pipeline run имеет уникальный `trace_id`:

```python
trace_id = str(uuid.uuid4())
```

## Span Propagation

Spans распространяются через контекст выполнения:

```python
with tracer.start_as_current_span("pipeline_execution") as span:
    span.set_attribute("pipeline_name", pipeline_name)
    span.set_attribute("run_id", run_id)
    
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

Tracing данные экспортируются в OpenTelemetry-compatible backend (если настроен).

## Configuration

Tracing конфигурируется через `src/bioetl/infrastructure/observability/tracing.py`.

## Best Practices

1. Создавать spans для значимых операций
2. Добавлять атрибуты к spans для контекста
3. Использовать span links для асинхронных операций
4. Избегать создания слишком многих spans для производительности