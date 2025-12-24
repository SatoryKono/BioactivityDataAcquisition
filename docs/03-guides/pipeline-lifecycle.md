# Жизненный цикл пайплайна

Этот документ описывает последовательность операций при выполнении пайплайна BioETL.

## Порядок выполнения PipelineRunner.run()

```mermaid
sequenceDiagram
    participant CLI
    participant Runner
    participant Services
    participant Lock
    participant Storage
    participant Checkpoint
    participant Executor

    CLI->>Runner: run()
    Runner->>Services: __aenter__()
    Runner->>Lock: __aenter__() (acquire)
    alt RunType == REBUILD or BACKFILL
        Runner->>Storage: clear_silver()
        Runner->>Storage: clear_gold()
    end
    Runner->>Checkpoint: load_checkpoint()
    Runner->>Executor: execute()
    Runner->>Checkpoint: delete_checkpoint()
    Runner->>Lock: __aexit__() (release)
    Runner->>Services: __aexit__()
```

## Очистка слоёв по типу запуска

| RunType | clear_silver | clear_gold | Обоснование |
|---------|--------------|------------|-------------|
| `INCREMENTAL` | ❌ | ❌ | Merge/upsert сохраняет существующие данные |
| `BACKFILL` | ✅ | ✅ | Заполнение исторических данных |
| `REBUILD` | ✅ | ✅ | Полная перестройка таблицы |

### Почему incremental не очищает данные?

Medallion архитектура требует идемпотентности для инкрементальных обновлений:

1. **Silver слой**: Использует merge/upsert по `content_hash`
2. **Gold слой**: Применяет SCD Type 2 или партиционирование

Удаление данных при incremental run привело бы к потере исторических записей.

## Инварианты блокировки

Блокировка (`LockManager`) гарантирует:

1. **Эксклюзивный доступ**: Только один процесс выполняет пайплайн
2. **Heartbeat**: Периодическое продление TTL блокировки
3. **Graceful release**: Освобождение в `finally` даже при ошибках

```python
async with self._lock_manager:
    # Блокировка захвачена
    await self._clear_exports()
    await self._checkpoint_manager.load_checkpoint()
    await self._executor.execute()
    # Блокировка освобождается автоматически
```

## Политика метрик (fail_fast)

Параметр `BIOETL_FAIL_FAST_METRICS` управляет поведением при ошибках запуска Prometheus сервера:

| Значение | Поведение |
|----------|-----------|
| `false` (default) | Warning в лог, метрики отключаются, пайплайн продолжает работу |
| `true` | Исключение `MetricsServerError`, пайплайн не запускается |

### Рекомендации

- **Development/CI**: `false` — не блокировать из-за занятых портов
- **Production с мониторингом**: `true` — гарантировать наличие метрик

### Пример настройки

```bash
# Строгий режим для production
export BIOETL_FAIL_FAST_METRICS=true

# Или в конфиге
metrics:
  port: 8000
  fail_fast: true
```

## Graceful Shutdown

При получении `SIGTERM`/`SIGINT`:

1. `ShutdownSignal.set()` активируется
2. Текущий батч завершается
3. Checkpoint сохраняется
4. Lock освобождается
5. Exit code 0

См. [ADR-008: Graceful Shutdown Strategy](../02-architecture/decisions/ADR-008-graceful-shutdown-strategy.md)

## Связанные документы

- [ADR-012: Storage Clear Contract](../02-architecture/decisions/ADR-012-storage-clear-contract-and-run-id.md)
- [ADR-013: Async Storage Cleanup](../02-architecture/decisions/ADR-013-async-storage-cleanup.md)
- [Running Pipelines](./running-pipelines.md)
