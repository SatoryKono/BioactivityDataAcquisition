# ADR-013: Асинхронная очистка хранилища в PipelineRunner

**Status:** Accepted
**Date:** 2025-12-24
**Decision makers:** @BioETL-Team

## Context

На момент принятия ADR путь очистки в `PipelineRunner` был представлен через
приватный метод `_clear_exports()`, который вызывал асинхронные методы
`StoragePort.clear_silver()` и `StoragePort.clear_gold()`. Изначально этот путь
был определён как синхронный (`def`), что приводило к синтаксической ошибке при
использовании `await`.

В текущей архитектуре тот же инвариант реализован через
`MedallionLifecycleService.prepare_for_run()`, который делегирует
policy-driven очистку в `MedallionLifecycleService.clear()`.

Также требовалось формализовать политику очистки данных в зависимости от типа запуска (RunType).

## Decision

### 1. Асинхронная сигнатура

Исторически `_clear_exports()` был переведён в асинхронный путь очистки.
В текущем коде канонический pre-run вызов выглядит так:

```python
await self._lifecycle_service.prepare_for_run(
    config=self._config,
    runtime=self._runtime,
)
```

Внутри lifecycle service очистка остаётся асинхронной:

```python
result = await self.clear(
    policy=policy,
    silver_table=silver_table,
    gold_table=gold_table,
    dry_run=runtime.dry_run,
)
```

### 2. Политика очистки по RunType

Очистка происходит ТОЛЬКО для destructive run types:

| RunType | Очистка | Обоснование |
|---------|---------|-------------|
| `INCREMENTAL` | ❌ | Merge/upsert сохраняет существующие данные |
| `BACKFILL` | ✅ | Заполнение исторических данных |
| `REBUILD` | ✅ | Полная перестройка таблицы |

Для `INCREMENTAL` effective policy не очищает слои:

```python
from bioetl.domain.medallion import MedallionPolicy

policy = MedallionPolicy.for_run_type(runtime.run_type)
assert policy.should_clear_silver is False
assert policy.should_clear_gold is False
```

### 3. Порядок операций в run()

```
1. services.__aenter__()           # Инициализация сервисов
2. lock_manager.__aenter__()       # Захват блокировки
3. await preflight.validate_infrastructure()
4. await lifecycle_service.prepare_for_run()
5. await checkpoint_manager.load() # Если start_offset не задан вручную
6. await executor.execute()        # Выполнение пайплайна
7. await postrun.run()             # DQ + post-run maintenance
8. await checkpoint_manager.delete()
9. lock_manager.__aexit__()        # Освобождение блокировки
10. services.__aexit__()           # Закрытие сервисов
```

### 4. Dry-run поддержка

Параметр `dry-run` передаётся в методы очистки:

```python
silver_cleared = await self.storage.clear_silver(silver_table, dry_run=dry_run)
gold_cleared = await self.storage.clear_gold(gold_table, dry_run=dry_run)
```

## Consequences

### Positive

- **Корректная работа** с асинхронным `StoragePort`
- **Явные инварианты** Medallion архитектуры зафиксированы в коде
- **Тестируемость** через `CallRecorder` pattern в интеграционных тестах
- **Dry-run** позволяет preview очистки без изменения данных

### Negative

- **Breaking change** на момент внедрения для тестов, вызывавших старый cleanup path напрямую
- Требуется `AsyncMock` для `storage.clear_silver/clear_gold` в тестах

### Migration

Историческая миграция требовала перевести cleanup path на async seam.
В текущем коде тесты обычно мокают `lifecycle_service.prepare_for_run()` или
проверяют вызовы `storage.clear_silver/clear_gold` через lifecycle service:

```python
# До:
def test_clear_exports(...):
    runner._clear_exports()  # historical seam
    services.storage.clear_silver = MagicMock(return_value=0)

# После:
@pytest.mark.asyncio
async def test_clear_exports(...):
    services.storage.clear_silver = AsyncMock(return_value=0)
    await lifecycle_service.prepare_for_run(config, runtime)
```

## Related ADRs

- [ADR-012](ADR-012-storage-clear-contract-and-run-id.md): Storage Clear Contract — defines the contract being implemented
- [ADR-015](ADR-015-pipeline-services-lifecycle.md): Pipeline Services Lifecycle — async cleanup coordination

## References

- CLAUDE.md §3: Medallion Architecture
- tests/integration/test_runner_lifecycle.py — Тесты инвариантов
