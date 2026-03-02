# ADR-013: Асинхронная очистка хранилища в PipelineRunner

**Status:** Accepted
**Date:** 2025-12-24
**Decision makers:** @BioETL-Team

## Context

Метод `-clear-exports()` в `PipelineRunner` вызывает асинхронные методы `StoragePort.clear-silver()` и `StoragePort.clear-gold()`. Изначально метод был определён как синхронный (`def`), что приводило к синтаксической ошибке при использовании `await`.

Также требовалось формализовать политику очистки данных в зависимости от типа запуска (RunType).

## Decision

### 1. Асинхронная сигнатура

`-clear-exports()` объявляется как `async def`:

```python
async def -clear-exports(self) -> None:
    """Clear export files and Delta tables at the start of a pipeline run."""
    ...
```

Вызов из `run()` использует `await`:

```python
await self.-clear-exports()
```

### 2. Политика очистки по RunType

Очистка происходит ТОЛЬКО для destructive run types:

| RunType | Очистка | Обоснование |
|---------|---------|-------------|
| `INCREMENTAL` | ❌ | Merge/upsert сохраняет существующие данные |
| `BACKFILL` | ✅ | Заполнение исторических данных |
| `REBUILD` | ✅ | Полная перестройка таблицы |

Для `INCREMENTAL` метод возвращает сразу (early return):

```python
from bioetl.domain.types import RunType

should-clear = self.-runtime.run-type in (RunType.REBUILD, RunType.BACKFILL)
if not should-clear:
    self.-logger.debug("Skipping clear for incremental run")
    return
```

### 3. Порядок операций в run()

```
1. services.--aenter--()           # Инициализация сервисов
2. lock-manager.--aenter--()       # Захват блокировки
3. await -clear-exports()          # Очистка (только REBUILD/BACKFILL)
4. await checkpoint-manager.load() # Загрузка чекпоинта
5. await executor.execute()        # Выполнение пайплайна
6. await checkpoint-manager.delete()# Удаление чекпоинта
7. lock-manager.--aexit--()        # Освобождение блокировки
8. services.--aexit--()            # Закрытие сервисов
```

### 4. Dry-run поддержка

Параметр `dry-run` передаётся в методы очистки:

```python
silver-cleared = await storage.clear-silver(silver-table, dry-run=self.-runtime.dry-run)
gold-cleared = await storage.clear-gold(gold-table, dry-run=self.-runtime.dry-run)
```

## Consequences

### Positive

- **Корректная работа** с асинхронным `StoragePort`
- **Явные инварианты** Medallion архитектуры зафиксированы в коде
- **Тестируемость** через `CallRecorder` pattern в интеграционных тестах
- **Dry-run** позволяет preview очистки без изменения данных

### Negative

- **Breaking change** для тестов, вызывающих `-clear-exports()` напрямую
- Требуется `AsyncMock` для `storage.clear-silver/clear-gold` в тестах

### Migration

Тесты необходимо обновить:

```python
# До:
def test-clear-exports(...):
    runner.-clear-exports()
    services.storage.clear-silver = MagicMock(return-value=0)

# После:
@pytest.mark.asyncio
async def test-clear-exports(...):
    await runner.-clear-exports()
    services.storage.clear-silver = AsyncMock(return-value=0)
```

## Related ADRs

- [ADR-012](ADR-012-storage-clear-contract-and-run-id.md): Storage Clear Contract — defines the contract being implemented
- [ADR-015](ADR-015-pipeline-services-lifecycle.md): Pipeline Services Lifecycle — async cleanup coordination

## References

- CLAUDE.md §3: Medallion Architecture
- tests/integration/test-runner-lifecycle.py — Тесты инвариантов
