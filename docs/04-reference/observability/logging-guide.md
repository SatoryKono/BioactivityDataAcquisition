# Logging Guide

## Overview

BioETL использует structured logging с интеграцией в observability stack.

## Log Levels

- **DEBUG**: Детальная информация для debugging
- **INFO**: Информационные сообщения о нормальной работе
- **WARNING**: Предупреждения о потенциальных проблемах
- **ERROR**: Ошибки, которые не прерывают выполнение
- **CRITICAL**: Критические ошибки, прерывающие выполнение

## Structured Logging Format

BioETL использует structured logging с JSON форматом:

```json
{
  "timestamp": "2026-06-04T14:00:00Z",
  "level": "INFO",
  "logger": "bioetl.application.services.pipeline",
  "message": "Pipeline started",
  "pipeline": "chembl",
  "run_id": "6f9a5182-7d48-5aa7-99a0-19da16d70e23",
  "provider": "chembl",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7"
}
```

## Log Correlation

`run_id` — основной correlation identifier запуска. Он выдаётся control-plane и
связывает logs с manifest/ledger и replay evidence. Logger bootstrap должен
получать его явно. До появления `run_id` bootstrap может использовать только
локальный deterministic occurrence fallback; этот fallback не является replay
identity и не зависит от PID.

При активном OpenTelemetry span `trace_context_processor` автоматически
добавляет `trace_id` и `span_id` в lowercase hex. Без активного span эти поля не
добавляются. Не создавайте `trace_id` вручную и не подменяйте им `run_id`:

```python
run_logger = logger.bind(run_id=str(run_id), pipeline=pipeline_name)
run_logger.info("Processing record", record_id=record_id)
```

## Key Loggers

- `bioetl.application`: Application layer logs
- `bioetl.infrastructure`: Infrastructure layer logs
- `bioetl.domain`: Domain layer logs (minimal)
- `bioetl.interfaces`: CLI/API logs

## Configuration

Logging конфигурируется через `src/bioetl/infrastructure/observability/logging_config.py`.

### Key Functions

**secret_filter_processor**
- Автоматически маскирует секреты в логах (API keys, tokens, passwords, authorization headers)
- Сохраняет UUID-формат идентификаторы (run_id, batch_id, content_hash)
- Рекурсивно обрабатывает вложенные словари

**trace_context_processor**
- Автоматически добавляет `trace_id` и `span_id` из текущего OTel span
- Коррелирует логи с distributed tracing
- Работает только при активном span

**_resolve_log_file_path()**
- Разрешает путь к файлу логов в следующем порядке:
  1. `BIOETL_LOG_FILE` environment variable (явное переопределение)
  2. Нет файла sink во время pytest runs
  3. `reports/logs/bioetl.log` для нормальной работы

### Configuration Options

```python
from bioetl.infrastructure.observability.logging_config import configure_logging

# JSON формат (production)
configure_logging(json_format=True, log_level="INFO")

# Console формат (development)
configure_logging(json_format=False, log_level="DEBUG")

# Принудительная переконфигурация
configure_logging(force=True)
```

## Best Practices

1. Использовать appropriate log levels
2. Включать context в structured logs
3. Коррелировать logs с traces
4. Избегать логирования чувствительных данных
