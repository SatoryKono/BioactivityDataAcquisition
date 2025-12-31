# ADR-013: Асинхронная очистка хранилища в PipelineRunner

*   **Status**: Accepted
*   **Date**: 2024-12-24

## Context

Метод `_clear_exports()` в `PipelineRunner` вызывает асинхронные методы `StoragePort.clear_silver()` и `StoragePort.clear_gold()`. Изначально метод был определён как синхронный (`def`), что приводило к синтаксической ошибке при использовании `await`.

Также требовалось формализовать политику очистки данных в зависимости от типа запуска (RunType).

## Decision

### 1. Асинхронная сигнатура

`_clear_exports()` объявляется как `async def`:

```python
async def _clear_exports(self) -> None:
    """Clear export files and Delta tables at the start of a pipeline run."""
    ...
```

Вызов из `run()` использует `await`:

```python
await self._clear_exports()
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

should_clear = self._runtime.run_type in (RunType.REBUILD, RunType.BACKFILL)
if not should_clear:
    self._logger.debug("Skipping clear for incremental run")
    return
```

### 3. Порядок операций в run()

```
1. services.__aenter__()           # Инициализация сервисов
2. lock_manager.__aenter__()       # Захват блокировки
3. await _clear_exports()          # Очистка (только REBUILD/BACKFILL)
4. await checkpoint_manager.load() # Загрузка чекпоинта
5. await executor.execute()        # Выполнение пайплайна
6. await checkpoint_manager.delete()# Удаление чекпоинта
7. lock_manager.__aexit__()        # Освобождение блокировки
8. services.__aexit__()            # Закрытие сервисов
```

### 4. Dry-run поддержка

Параметр `dry_run` передаётся в методы очистки:

```python
silver_cleared = await storage.clear_silver(silver_table, dry_run=self._runtime.dry_run)
gold_cleared = await storage.clear_gold(gold_table, dry_run=self._runtime.dry_run)
```

## Consequences

### Positive

- **Корректная работа** с асинхронным `StoragePort`
- **Явные инварианты** Medallion архитектуры зафиксированы в коде
- **Тестируемость** через `CallRecorder` pattern в интеграционных тестах
- **Dry-run** позволяет preview очистки без изменения данных

### Negative

- **Breaking change** для тестов, вызывающих `_clear_exports()` напрямую
- Требуется `AsyncMock` для `storage.clear_silver/clear_gold` в тестах

### Migration

Тесты необходимо обновить:

```python
# До:
def test_clear_exports(...):
    runner._clear_exports()
    services.storage.clear_silver = MagicMock(return_value=0)

# После:
@pytest.mark.asyncio
async def test_clear_exports(...):
    await runner._clear_exports()
    services.storage.clear_silver = AsyncMock(return_value=0)
```

## Related ADRs

- [ADR-012](ADR-012-storage-clear-contract-and-run-id.md): Storage Clear Contract — defines the contract being implemented
- [ADR-015](ADR-015-pipeline-services-lifecycle.md): Pipeline Services Lifecycle — async cleanup coordination

## References

- CLAUDE.md §3: Medallion Architecture
- tests/integration/test_runner_lifecycle.py — Тесты инвариантов
