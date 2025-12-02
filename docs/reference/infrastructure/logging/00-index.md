# Logging Infrastructure

Проект использует структурированное логирование через компонент `UnifiedLogger`.

## UnifiedLogger

Обертка над библиотекой логирования (например, `structlog` или стандартный `logging` с JSON-форматтером).

### Принципы
1. **JSON Output**: В продакшене логи пишутся в формате JSON Lines для удобной агрегации (ELK, Splunk).
2. **Context Binding**: Контекст (например, `run_id`, `entity_name`) привязывается один раз и автоматически добавляется ко всем сообщениям.
3. **No Print**: Использование `print()` запрещено, так как это нарушает структурированность вывода.

### Пример

```python
logger = UnifiedLogger()
logger.bind(run_id="123", entity="activity")

logger.info("Starting extraction", batch_size=1000)
# {"timestamp": "...", "level": "INFO", "event": "Starting extraction", "batch_size": 1000, "run_id": "123", "entity": "activity"}
```

## ProgressReporter

Для отображения прогресса в консоли (не в лог-файл) используется `ProgressReporterABC`, который обычно реализуется через `tqdm`. Он не засоряет логи, обновляя строку прогресса in-place.

## Tracer

`TracerABC` обеспечивает интеграцию с системами распределенной трассировки (OpenTelemetry), позволяя отслеживать время выполнения стадий и внешних HTTP-запросов.

