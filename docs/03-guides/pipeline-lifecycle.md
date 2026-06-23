______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Жизненный цикл пайплайна

Этот документ описывает последовательность операций при выполнении пайплайна BioETL.

## Порядок выполнения PipelineRunner.run()

> **Diagram:** See [`04-pipeline-execution-flow.mmd`](../02-architecture/diagrams/architecture/04-pipeline-execution-flow.mmd)
> *(rendered не публикуются; используй source `.mmd`)*

## Очистка слоёв по типу запуска

| RunType       | clear-silver | clear-gold | Обоснование                                |
| ------------- | ------------ | ---------- | ------------------------------------------ |
| `INCREMENTAL` | ❌           | ❌         | Merge/upsert сохраняет существующие данные |
| `BACKFILL`    | ✅           | ✅         | Заполнение исторических данных             |
| `REBUILD`     | ✅           | ✅         | Полная перестройка таблицы                 |

### Почему incremental не очищает данные?

Medallion архитектура требует идемпотентности для инкрементальных обновлений:

1. **Silver слой**: Использует merge/upsert по `content-hash`
1. **Gold слой**: Применяет SCD Type 2 или партиционирование

Удаление данных при incremental run привело бы к потере исторических записей.

## Инварианты блокировки

Блокировка (`LockRuntimeService`) гарантирует:

1. **Эксклюзивный доступ**: Только один процесс выполняет пайплайн
1. **Heartbeat**: Периодическое продление TTL блокировки
1. **Graceful release**: Освобождение в `finally` даже при ошибках

```python
async with self._services, self._lock_runtime_service:
    # Блокировка захвачена, инфраструктура и lifecycle подготовлены
    await self._preflight_service.validate_infrastructure(self._services)
    await self._lifecycle_service.prepare_for_run(
        config=self._config,
        runtime=self._runtime,
    )
    await self._checkpoint_manager.load_checkpoint()
    await self._executor.execute()
    # Блокировка освобождается автоматически
```

## Политика метрик (fail_fast)

Параметр `BIOETL_OBSERVABILITY__METRICS_FAIL_FAST` управляет поведением при ошибках запуска Prometheus сервера. Для production launcher paths (`BIOETL_ENV=prod` и `BIOETL_TEST_MODE=false`) дефолт разрешается как `true`, если параметр не задан явно.

| Значение | Поведение                                                      |
| -------- | -------------------------------------------------------------- |
| `false`  | Warning в лог, метрики отключаются, пайплайн продолжает работу |
| `true`   | Исключение `MetricsServerError`, пайплайн не запускается       |

### Рекомендации

- **Development/CI**: `false` — не блокировать из-за занятых портов.
- **Production с мониторингом**: `true` — гарантировать наличие метрик; это runtime default для production launcher paths.
- **Production opt-out**: допускается только явной настройкой `BIOETL_OBSERVABILITY__METRICS_FAIL_FAST=false`.

### Пример настройки

```bash
# Строгий режим для production
export BIOETL_ENV=prod
export BIOETL_OBSERVABILITY__METRICS_FAIL_FAST=true

# Или в конфиге
observability:
  metrics_fail_fast: true
```

## Graceful Shutdown

При получении `SIGTERM`/`SIGINT`:

1. `ShutdownSignal.set()` активируется
1. Текущий батч завершается
1. Checkpoint сохраняется
1. Lock освобождается
1. Exit code 0

См. [ADR-015: Pipeline Services Lifecycle](../02-architecture/decisions/ADR-015-pipeline-services-lifecycle.md).
`ADR-008` сохраняется только как historical/superseded context.

## Жизненный цикл Composite Pipeline

Composite pipelines используют отдельный оркестратор (`CompositePipelineRunner`)
вместо стандартного `PipelineRunner` + `Transformer`.

> **Diagram:** See [`08-composite-pipeline.mmd`](../02-architecture/diagrams/architecture/08-composite-pipeline.mmd)
> *(rendered не публикуются; используй source `.mmd`)*

### Ключевые отличия

1. **Без трансформеров**: Composite не использует `*Transformer` классы
1. **Оркестрация**: `application/composite/` содержит 15 модулей сервисов
1. **Merge**: `MergeService` выполняет JOIN по `join_keys` из composite-конфига
1. **Fan-out**: Enrichers могут выполняться параллельно (если `optional: true`)

См. [ADR-026: Composite Pipeline Pattern](../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md)

## Связанные документы

- [ADR-012: Storage Clear Contract](../02-architecture/decisions/ADR-012-storage-clear-contract-and-run-id.md)
- [ADR-013: Async Storage Cleanup](../02-architecture/decisions/ADR-013-async-storage-cleanup.md)
- [Running Pipelines](./running-pipelines.md)
