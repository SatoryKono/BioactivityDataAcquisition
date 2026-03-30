---
Version: 1.0.0
Status: Accepted (Implemented 2025-12-29)
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-30'
---

# ADR-021: Внедрение DDD Aggregates в Domain Layer

**Date:** 2025-12-29
**Status:** Accepted (Implemented 2025-12-29)
**Decision makers:** @BioETL-Team

## Context

### Мотивация

В рамках развития архитектуры BioETL возникла необходимость усилить защиту бизнес-инвариантов
и улучшить модульность domain слоя. Ранее бизнес-логика была распределена между application
и domain слоями без чёткой модели владения данными.

### Проблемы до рефакторинга

1. **Отсутствие инвариантной защиты**: Batch-записи могли модифицироваться на любом этапе
2. **Размытые границы консистентности**: Непонятно, какие объекты должны изменяться транзакционно
3. **Отсутствие Event Sourcing**: Нет механизма отслеживания изменений состояния
4. **Слабая типизация идентификаторов**: `run-id` и `batch-id` были обычными строками

### Затронутые области

- `src/bioetl/domain/aggregates/` — новый пакет
- `src/bioetl/domain/value-objects/` — новый пакет
- `src/bioetl/domain/types.py` — расширен новыми типами
- `src/bioetl/domain/exceptions/` — добавлены DDD-исключения

## Decision

### 1. Добавлены DDD Aggregates

Три ключевых агрегата с защищёнными инвариантами:

#### Batch Aggregate (`domain/aggregates/batch.py`)

```python
class Batch:
    """Aggregate Root для коллекции записей.

    Инварианты:
        1. Все записи имеют один batch-id
        2. Записи нельзя добавить после seal()
        3. batch-id неизменяем
        4. Индексы записей последовательны
        5. Карантинные записи отслеживаются отдельно
    """

    def add-record(self, data: dict) -> BatchRecord: ...
    def quarantine-record(self, record: BatchRecord, error: str) -> BatchRecord: ...
    def seal(self) -> None: ...
    def mark-writing(self) -> None: ...
    def mark-committed(self, layer: str) -> None: ...
    def mark-failed(self, layer: str, error: str) -> None: ...
    def collect-events(self) -> list[DomainEvent]: ...
```

**State Machine:**
```
OPEN → SEALED → WRITING → COMMITTED
                      ↘→ FAILED
```

#### PipelineRun Aggregate (`domain/aggregates/pipeline_run.py`)

```python
class PipelineRun:
    """Aggregate Root для выполнения пайплайна.

    Инварианты:
        1. status == COMPLETED только если все стадии SUCCESS
        2. status == FAILED если хотя бы одна стадия FAILED
        3. end-time != None только для терминальных статусов
        4. stages нельзя модифицировать после терминального статуса
        5. run-id неизменяем после создания
    """

    def start(self) -> None: ...
    def record-stage-start(self, stage: str) -> None: ...
    def record-stage-success(self, stage: str, records: int) -> None: ...
    def record-stage-failure(self, stage: str, error: str) -> None: ...
    def complete(self) -> None: ...
    def fail(self, error: str) -> None: ...
    def shutdown(self) -> None: ...
```

**State Machine:**
```
PENDING → RUNNING → COMPLETED
               ↘→ FAILED
               ↘→ SHUTDOWN
```

#### QuarantineEntry Aggregate (`domain/aggregates/quarantine_entry.py`)

```python
class QuarantineEntry:
    """Aggregate для записи в карантине.

    Инварианты:
        1. entry-id неизменяем
        2. Статус переходит только в указанном порядке
        3. Повторные попытки (retries) инкрементируются атомарно
    """

    def mark-retrying(self) -> None: ...
    def mark-recovered(self) -> None: ...
    def mark-dead-letter(self, reason: str) -> None: ...
```

### 2. Добавлены Value Objects

Строго типизированные идентификаторы в `domain/value-objects/`:

```python
# Типизированные идентификаторы
class RunID(UUID): ...
class BatchID(UUID): ...
class EntityID(str): ...
class ContentHash(str): ...

# Измерения
class Measurement:
    value: float
    unit: str
    relation: str  # "=", ">", "<", "~"
```

### 3. Добавлены Domain Events

События, эмитируемые агрегатами (`domain/aggregates/events.py`):

| Event | Aggregate | Когда |
|-------|-----------|-------|
| `BatchCreated` | Batch | После `Batch.create()` |
| `BatchSealed` | Batch | После `batch.seal()` |
| `BatchWritten` | Batch | После `batch.mark-committed()` |
| `BatchFailed` | Batch | После `batch.mark-failed()` |
| `RecordQuarantined` | Batch | После `batch.quarantine-record()` |
| `RunStarted` | PipelineRun | После `run.start()` |
| `StageCompleted` | PipelineRun | После `run.record-stage-success()` |
| `StageFailed` | PipelineRun | После `run.record-stage-failure()` |
| `RunCompleted` | PipelineRun | После `run.complete()` |
| `RunFailed` | PipelineRun | После `run.fail()` |

### 4. Структура domain слоя после рефакторинга

```
src/bioetl/domain/
├── aggregates/           # DDD Aggregates
│   ├── __init__.py
│   ├── batch.py          # Batch Aggregate (536 LOC)
│   ├── pipeline_run.py   # PipelineRun Aggregate (574 LOC)
│   ├── quarantine_entry.py # QuarantineEntry Aggregate (517 LOC)
│   └── events.py         # Domain Events (197 LOC)
├── value_objects/        # Value Objects
│   ├── __init__.py
│   ├── identifiers.py    # RunID, BatchID, EntityID, ContentHash
│   └── measurements.py   # Measurement, IC50, etc.
├── entities/             # Domain Entities (per provider)
├── schemas/              # Pydantic/Pandera schemas
├── ports/                # Protocol interfaces
├── exceptions/           # Classified exceptions
├── types.py              # Type aliases
├── medallion.py          # WriteMode enums
└── ...
```

## Consequences

### Положительные

1. **Защита инвариантов**: State machine в агрегатах предотвращает некорректные переходы
2. **Чёткие границы консистентности**: Каждый агрегат — единица транзакционной консистентности
3. **Event Sourcing Ready**: `collect-events()` позволяет публиковать события
4. **Типобезопасность**: Value Objects исключают смешение идентификаторов
5. **Тестируемость**: Агрегаты можно тестировать изолированно без I/O
6. **Документирование бизнес-правил**: Инварианты явно описаны в docstrings

### Отрицательные

1. **Увеличение сложности**: Добавлено ~1824 LOC нового кода в domain
2. **Кривая обучения**: Требуется понимание DDD patterns
3. **Миграция**: Существующий код нужно адаптировать

### Риски и митигация

| Риск | Митигация | Статус |
|------|-----------|--------|
| Over-engineering | Только критичные агрегаты (Batch, Run) | Закрыт |
| Регрессии | Полное тестовое покрытие агрегатов | Закрыт |
| Сложность интеграции | Агрегаты используются в application layer | Закрыт |

## Примеры использования

### Batch Aggregate в RecordProcessor

```python
# application/core/record_processor.py
async def process-batch(self, records: list[dict]) -> None:
    batch = Batch.create(run-id=self._run_id)

    for record in records:
        batch.add-record(record)

    # Валидация
    for record in batch.all-records:
        if not self.-validate(record.data):
            batch.quarantine-record(record, "Validation failed")

    batch.seal()

    # Запись
    batch.mark-writing()
    try:
        await self.-writer.write(batch.records)
        batch.mark-committed("silver")
    except Exception as e:
        batch.mark-failed("silver", str(e))
        raise

    # Публикация событий
    events = batch.collect-events()
    for event in events:
        await self.-event-bus.publish(event)
```

### PipelineRun Aggregate в PipelineRunner

```python
# application/core/runner.py
async def run(self) -> None:
    run = PipelineRun.create(
        run-id=self._run_id,
        pipeline-name=self.-config.pipeline-name,
        run-type=self.-runtime.run-type,
    )

    run.start()

    try:
        run.record-stage-start("preflight")
        await self.-preflight()
        run.record-stage-success("preflight", records-processed=0)

        run.record-stage-start("execution")
        processed = await self.-execute()
        run.record-stage-success("execution", records-processed=processed)

        run.record-stage-start("postrun")
        await self.-postrun()
        run.record-stage-success("postrun", records-processed=0)

        run.complete()
    except Exception as e:
        run.fail(str(e))
        raise
    finally:
        events = run.collect-events()
        # Publish events...
```

## References

- [ADR-020: Декомпозиция BasePipeline](ADR-020-basepipeline-decomposition.md) — рефакторинг application layer
- [ADR-015: Pipeline Services Lifecycle](ADR-015-pipeline-services-lifecycle.md) — lifecycle management
- [RULES.md §1.1](../../00-project/RULES.md) — Ports & Adapters Architecture
- [docs/glossary.md](../../00-project/glossary.md) — Ubiquitous Language

## Alternatives Considered

### 1. Оставить простые dataclasses

- **Плюсы**: Меньше кода, проще понять
- **Минусы**: Нет защиты инвариантов, нет state machine
- **Решение**: Отклонено

### 2. Full Event Sourcing

- **Плюсы**: Полная история изменений
- **Минусы**: Значительная сложность, требует event store
- **Решение**: Отклонено, но `collect-events()` готов к эволюции

### 3. CQRS

- **Плюсы**: Разделение чтения и записи
- **Минусы**: Over-engineering для текущего масштаба
- **Решение**: Отклонено, рассмотреть при масштабировании

## Compliance

| Control | Requirement | Status | Evidence |
|---|---|---|---|
| Format | ADR MUST use standard metadata and normalized section headings | `pass` | `ADR-021-ddd-aggregates-adoption.md` |
| Status | ADR status MUST be explicit and consistent | `pass` | `Accepted (Implemented 2025-12-29)` |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a` | `metadata block` |
| Verification | Implementation and validation expectations MUST be documented | `pass` | `Verification / Acceptance Criteria` |
| References | Related ADRs, docs, or artifacts SHOULD be linked | `pass` | `References` |

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
