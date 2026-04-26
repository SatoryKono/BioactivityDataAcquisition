______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-013: Асинхронная очистка хранилища в PipelineRunner

**Date:** 2025-12-24
**Status:** Accepted
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

| RunType       | Очистка | Обоснование                                |
| ------------- | ------- | ------------------------------------------ |
| `INCREMENTAL` | ❌      | Merge/upsert сохраняет существующие данные |
| `BACKFILL`    | ✅      | Заполнение исторических данных             |
| `REBUILD`     | ✅      | Полная перестройка таблицы                 |

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

## References

- [ADR-012](ADR-012-storage-clear-contract-and-run-id.md): Storage Clear Contract — defines the contract being implemented
- [ADR-015](ADR-015-pipeline-services-lifecycle.md): Pipeline Services Lifecycle — async cleanup coordination

## References

- CLAUDE.md §3: Medallion Architecture
- tests/integration/test_runner_lifecycle.py — Тесты инвариантов

## Compliance

| Control      | Requirement                                                                | Status | Evidence                             |
| ------------ | -------------------------------------------------------------------------- | ------ | ------------------------------------ |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-013-async-storage-cleanup.md`   |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                           |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                     |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria` |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                         |

## Rollout

- Rollout steps MUST be sequenced before broad adoption.
- Documentation, configuration, and test surfaces SHOULD be updated in the same change set when the decision is implemented.
- Breaking or migration-sensitive adoption SHOULD include an explicit transition window.

## Rollback

- Rollback MUST identify the last known-good behavior or artifact set.
- If the decision changes contracts, configuration, or storage semantics, rollback SHOULD include data and compatibility checks.
- Rollback triggers SHOULD be observable through tests, runtime signals, or regression symptoms.

## Verification

- Verify architecture, configuration, and documentation changes against the current codebase.
- Run the relevant tests, validators, or parity checks before considering the ADR fully adopted.
- Confirm downstream docs and contracts reflect the same decision boundaries.

## Acceptance Criteria

- [ ] The decision is documented with current status, date, and owner metadata.
- [ ] The implementation path or adoption boundary is testable and linked from the ADR.
- [ ] Supersession or migration impact is documented when the decision changes an earlier posture.
- [ ] Related docs, contracts, and operational guidance are aligned with this ADR.
