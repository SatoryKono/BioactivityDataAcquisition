______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-012: Storage Clear Contract and Run ID Consistency

**Date:** 2025-12-23
**Status:** Accepted
**Decision makers:** @BioETL-Team

## Context

Два архитектурных вопроса требовали решения:

### Проблема 1: Дублирование run-id

На момент принятия ADR `BasePipeline` создавал собственный `run_id` внутри
pipeline-конструктора, игнорируя идентификатор, уже созданный на входной
границе оркестрации. В пользовательском CLI-потоке это проявлялось через
`PipelineRunContext`, но проблема была общей для любого entrypoint. Это
приводило к рассинхронизации:

- CLI логировал один `run-id`
- Записи в Silver содержали другой `run-id` в метаполе `_run_id`
- Чекпоинты и блокировки использовали третий идентификатор

### Проблема 2: Reflection для очистки хранилища

Исторически cleanup path в `PipelineRunner` проверял доступность операций
очистки через reflection вместо явного port-контракта. Упрощённо это выглядело
так:

```python
if hasattr(storage, "clear_csv"):
    await storage.clear_csv(table_name)
if hasattr(storage, "clear_delta"):
    await storage.clear_delta(table_name)
```

Это нарушало принцип явных контрактов, затрудняло статический анализ и
смешивало cross-layer maintenance API с pre-run Medallion cleanup.

### Проблема 3: Нарушение Medallion-инвариантов

Очистка Silver/Gold выполнялась для **всех** типов запусков, включая `incremental`. Это противоречило семантике merge/upsert для инкрементальных обновлений.

## Decision

### 1. Единый run-id от orchestration boundary до метаполей

- `BasePipeline.__init__()` принимает `run_id` как обязательный параметр
- `run_id` создаётся или принимается на orchestration boundary, а затем
  прокидывается неизменным вниз по стеку
- Все компоненты (logger, context, checkpoints, locks) используют один `run_id`

**Изменённая сигнатура (исторический фокус ADR: `run_id` стал обязательным):**

```python
class BasePipeline(ABC):
    @classmethod
    def create(
        cls,
        run_id: RunID,
        runtime: RuntimeConfig,
        services: PipelineService,
        config: PipelineConfig,
        shutdown_signal: ShutdownSignal,
        transformer: BaseTransformer | None = None,
    ) -> Self:
        ...

    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        services: PipelineService,
        run_id: RunID,
        shutdown_signal: ShutdownSignal,
        transformer: BaseTransformer | None = None,
    ) -> None:
```

В текущем standard pipeline flow каноническая генерация/принятие `run_id`
происходит в `PipelineRunnerService.run()`: сервис принимает внешний `run_id`
или создаёт `effective_run_id`, затем передаёт его в `PipelineRunContext`,
`BasePipeline`, lock/checkpoint services и записи в storage без повторной
локальной генерации внутри pipeline:

```python
effective_run_id: RunID = cast(RunID, run_id or uuid4())
context = self._build_context(
    pipeline_name=pipeline_name,
    run_id=effective_run_id,
    options=effective_options,
)
```

### 2. Формализация API очистки в historical `StoragePort` / current narrow storage ports

Cleanup был переведён на явный async port-контракт. Исторический
aggregate-facade `StoragePort` больше retired; в текущем коде канонические
методы объявлены в narrow storage ports:

```python
async def clear_silver(self, table_name: str, dry_run: bool = False) -> int:
    """Clear Silver layer data for a specific table."""
    ...


async def clear_gold(self, table_name: str, dry_run: bool = False) -> int:
    """Clear Gold layer data for a specific table."""
    ...
```

`preview_cleanup()` остаётся синхронной maintenance-операцией, а
`clear_csv()` / `clear_delta()` остаются отдельными async helper-методами для
cross-layer обслуживания. При этом основной pre-run lifecycle больше не
выбирает cleanup path через `hasattr()`: текущий application-level seam идёт
через `MedallionLifecycleService.clear()`, который вызывает
`storage.clear_silver()` и `storage.clear_gold()` напрямую. На уровне
реализации storage adapter оборачивает синхронный writer cleanup через
`run_in_executor`, но для application-layer контракт остаётся async.

### 3. Medallion-инварианты по run-type

Очистка выполняется **только** для destructive run types:

```python
policy = MedallionPolicy.for_run_type(runtime.run_type)
assert policy.should_clear_silver == (runtime.run_type is not RunType.INCREMENTAL)
assert policy.should_clear_gold == (runtime.run_type is not RunType.INCREMENTAL)
```

| Run Type      | Очистка | Обоснование                    |
| ------------- | ------- | ------------------------------ |
| `incremental` | НЕТ     | Merge/upsert по content-hash   |
| `backfill`    | ДА      | Заполнение исторических данных |
| `rebuild`     | ДА      | Полная перестройка таблицы     |

В текущем runner flow эти инварианты применяются через pre-run вызов
`PipelineRunner.run()` -> `MedallionLifecycleService.prepare_for_run()`.
Post-run maintenance идёт отдельным путём:
`PostrunService.run_vacuum_if_enabled()` ->
`MedallionLifecycleService.finalize_run()`.

## Consequences

### Positive

- **Трассируемость**: Один `run_id` во всех слоях и компонентах
- **Типобезопасность**: Явные методы в narrow storage ports вместо reflection
- **Data Integrity**: Incremental runs не удаляют существующие данные
- **Тестируемость**: Можно проверить контракт через type checking

### Negative

- **Breaking change на момент принятия ADR**: pipeline constructors начали
  требовать явный `run_id`; позднее сигнатуры эволюционировали дальше
- **Миграция тестов**: тесты и bootstrap helpers должны были перестать
  полагаться на локальную генерацию `run_id` внутри pipeline

### Risks

| Риск                         | Вероятность | Митигация                                   |
| ---------------------------- | ----------- | ------------------------------------------- |
| Чекпоинты со старым форматом | Низкая      | `load()` игнорирует `run_id` в файле        |
| Дубликаты при incremental    | Средняя     | Merge по `content_hash` предотвращает дубли |

## References

- [ADR-001](ADR-001-delta-lake-vs-parquet.md): Delta Lake vs Parquet — storage format being cleared
- [ADR-002](ADR-002-medallion-architecture.md): Medallion Architecture — Medallion invariants for clear operations
- [ADR-013](ADR-013-async-storage-cleanup.md): Async Storage Cleanup — async implementation of clear methods

## References

- RULES.md §1.1 — Ports & Adapters architecture
- CLAUDE.md §3.2 — Content Hash нормализация

## Compliance

| Control      | Requirement                                                                | Status | Evidence                                       |
| ------------ | -------------------------------------------------------------------------- | ------ | ---------------------------------------------- |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-012-storage-clear-contract-and-run-id.md` |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                                     |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                               |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria`           |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                                   |

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
