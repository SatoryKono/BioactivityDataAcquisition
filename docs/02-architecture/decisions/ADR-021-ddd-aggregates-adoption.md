______________________________________________________________________

Version: 1.0.0
Status: Accepted (Implemented 2025-12-29)
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-06'

______________________________________________________________________

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
1. **Размытые границы консистентности**: Непонятно, какие объекты должны изменяться транзакционно
1. **Отсутствие Event Sourcing**: Нет механизма отслеживания изменений состояния
1. **Слабая типизация идентификаторов**: `run-id` и `batch-id` были обычными строками

### Затронутые области

- `src/bioetl/domain/aggregates/` — новый пакет
- `src/bioetl/domain/value_objects/` — новый пакет rich value objects
- `src/bioetl/domain/types/` — новый пакет типизированных идентификаторов и domain type aliases
- `src/bioetl/domain/exceptions/` — добавлены DDD-исключения

## Decision

### 1. Добавлены DDD Aggregates

Три ключевых агрегата с защищёнными инвариантами:

#### Batch Aggregate (`domain/aggregates/batch.py`)

```python
class Batch:
    """Aggregate Root для коллекции записей.

    Инварианты:
        1. Все записи имеют один batch_id
        2. Записи нельзя добавить после seal(...)
        3. batch_id и run_id неизменяемы
        4. Индексы записей последовательны
        5. Карантинные записи отслеживаются отдельно
    """

    @classmethod
    def create(cls, run_id: RunID, *, created_at: datetime) -> Batch: ...

    def add_record(self, data: BronzeRecord) -> BatchRecord: ...
    def quarantine_record(
        self,
        record: BatchRecord,
        error: str,
        *,
        quarantined_at: datetime,
    ) -> BatchRecord: ...
    def seal(self, sealed_at: datetime) -> None: ...
    def mark_writing(self) -> None: ...
    def mark_committed(self, layer: str, committed_at: datetime) -> None: ...
    def mark_failed(self, layer: str, error: str, *, failed_at: datetime) -> None: ...
    def collect_events(self) -> list[DomainEvent]: ...
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
        3. ended_at != None только для терминальных статусов
        4. stages нельзя модифицировать после терминального статуса
        5. run_id неизменяем после создания
    """

    def start(self, started_at: datetime) -> None: ...
    def record_stage_start(self, stage: str, started_at: datetime) -> None: ...
    def record_stage_success(
        self,
        stage: str,
        records_processed: int,
        completed_at: datetime,
    ) -> None: ...
    def record_stage_failure(
        self,
        stage: str,
        error: str,
        failed_at: datetime,
    ) -> None: ...
    def complete(self, completed_at: datetime) -> None: ...
    def fail(self, error: str, *, failed_at: datetime) -> None: ...
    def shutdown(self, shutdown_at: datetime) -> None: ...
```

**State Machine:**

```
PENDING → RUNNING → COMPLETED
               ↘→ FAILED
               ↘→ SHUTDOWN
```

#### QuarantineEntry Aggregate (`domain/aggregates/quarantine_entry.py`)

> **Implementation note (2026-07-06):** canonical transition-level reference is
> [Aggregate State Machines](../../04-reference/domain/aggregate-state-machines.md#quarantineentry).
> The historical `mark_retrying` / `mark_recovered` / `mark_dead_letter` sketch
> below is obsolete and must not be used for operator or integration guidance.

```python
class QuarantineEntry:
    """Aggregate for one quarantined record payload.

    Invariants:
        1. entry_id, pipeline_name, error_code, payload, payload_hash are mandatory
        2. Status transitions follow the published FSM only
        3. Payload remains immutable after creation
    """

    def start_review(self) -> None: ...
    def mark_ignored(self, *, ignored_at: datetime, reason: str | None = None) -> None: ...
    def mark_reprocessed(
        self,
        *,
        reprocessed_at: datetime,
        new_record_id: str,
        reason: str | None = None,
    ) -> None: ...
    def mark_expired(self, *, expired_at: datetime) -> None: ...
```

**State Machine:**

```
NEW → UNDER_REVIEW → IGNORED
  ↘               ↘→ REPROCESSED
  ↘→ EXPIRED      ↘→ EXPIRED
```

Source: `src/bioetl/domain/aggregates/_quarantine_entry_transitions_mixin.py`

### 2. Добавлены Value Objects

Строго типизированные runtime identifiers живут в `domain/types/`, а rich value
objects с валидацией и нормализацией живут в `domain/value_objects/`:

```python
# Типизированные идентификаторы и type aliases
RunID = NewType("RunID", UUID)
BatchID = NewType("BatchID", UUID)
EntityID = NewType("EntityID", str)
ContentHash = NewType("ContentHash", str)

# Rich value objects
class ChemblId(ValueObject[str]): ...
class UniProtId(ValueObject[str]): ...
class PubChemCid(ValueObject[int]): ...
class ActivityValue:
    value: float
    unit: str
    relation: RelationOperator
```

### 3. Добавлены Domain Events

События, эмитируемые агрегатами (`domain/aggregates/events.py`):

| Event               | Aggregate   | Когда                              |
| ------------------- | ----------- | ---------------------------------- |
| `BatchCreated`      | Batch       | После `Batch.create()`             |
| `BatchSealed`       | Batch       | После `batch.seal(...)`            |
| `BatchWritten`      | Batch       | После `batch.mark_committed(...)`  |
| `BatchFailed`       | Batch       | После `batch.mark_failed(...)`     |
| `RecordQuarantined` | Batch       | После `batch.quarantine_record(...)` |
| `RunStarted`        | PipelineRun | После `run.start(...)`             |
| `StageCompleted`    | PipelineRun | После `run.record_stage_success(...)` |
| `StageFailed`       | PipelineRun | После `run.record_stage_failure(...)` |
| `RunCompleted`      | PipelineRun | После `run.complete(...)`          |
| `RunFailed`         | PipelineRun | После `run.fail(...)`              |

Domain event `event_id` values are deterministic by default: when callers do
not pass an explicit `event_id`, `DomainEvent` derives it from the concrete
event type and canonical event payload. Aggregate factories that create
replay-sensitive identities must derive them from explicit inputs rather than
calling UUID4 inside `domain`. See ADR-014.

### 4. Структура domain слоя после рефакторинга

```
src/bioetl/domain/
├── aggregates/           # DDD Aggregates
│   ├── __init__.py
│   ├── batch.py          # Public Batch facade
│   ├── pipeline_run.py   # Public PipelineRun facade
│   ├── quarantine_entry.py
│   └── events.py
├── value_objects/        # Value Objects
│   ├── __init__.py
│   ├── identifiers.py    # ChemblId, UniProtId, PubChemCid
│   └── activity_measurement.py   # ActivityValue
├── types/                # Typed identifiers and domain type aliases
│   ├── __init__.py
│   ├── identifiers.py
│   ├── enums.py
│   └── checkpoint_metadata.py
├── entities/             # Domain Entities (per provider)
├── schemas/              # Pydantic/Pandera schemas
├── ports/                # Protocol interfaces
├── exceptions/           # Classified exceptions
├── medallion.py          # WriteMode enums
└── ...
```

## Consequences

### Положительные

1. **Защита инвариантов**: State machine в агрегатах предотвращает некорректные переходы
1. **Чёткие границы консистентности**: Каждый агрегат — единица транзакционной консистентности
1. **Event Sourcing Ready**: `collect-events()` позволяет публиковать события
1. **Типобезопасность**: Value Objects исключают смешение идентификаторов
1. **Тестируемость**: Агрегаты можно тестировать изолированно без I/O
1. **Документирование бизнес-правил**: Инварианты явно описаны в docstrings

### Отрицательные

1. **Увеличение сложности**: Добавлено ~1824 LOC нового кода в domain
1. **Кривая обучения**: Требуется понимание DDD patterns
1. **Миграция**: Существующий код нужно адаптировать

### Риски и митигация

| Риск                 | Митигация                                 | Статус |
| -------------------- | ----------------------------------------- | ------ |
| Over-engineering     | Только критичные агрегаты (Batch, Run)    | Закрыт |
| Регрессии            | Полное тестовое покрытие агрегатов        | Закрыт |
| Сложность интеграции | Агрегаты используются в application layer | Закрыт |

## Примеры использования

### Batch Aggregate в RecordProcessor

```python
# application/core/record_processor.py
async def process_batch(self, records: list[dict]) -> None:
    now = self._clock.now()
    batch = Batch.create(run_id=self._run_id, created_at=now)

    for record in records:
        batch.add_record(record)

    for record in batch.records:
        if not self._validate(record.data):
            batch.quarantine_record(
                record,
                "Validation failed",
                quarantined_at=self._clock.now(),
            )

    batch.seal(self._clock.now())
    batch.mark_writing()
    try:
        await self._writer.write(batch.records)
        batch.mark_committed("silver", committed_at=self._clock.now())
    except Exception as exc:
        batch.mark_failed("silver", str(exc), failed_at=self._clock.now())
        raise

    for event in batch.collect_events():
        await self._event_bus.publish(event)
```

### PipelineRun Aggregate в PipelineRunner

```python
# application/core/runner.py
async def run(self) -> None:
    run = PipelineRun(
        run_id=self._run_id,
        run_type=self._runtime.run_type,
        pipeline_name=self._config.pipeline_name,
    )

    run.start(self._clock.now())

    try:
        run.record_stage_start("preflight", self._clock.now())
        await self._preflight()
        run.record_stage_success(
            "preflight",
            records_processed=0,
            completed_at=self._clock.now(),
        )

        run.record_stage_start("execution", self._clock.now())
        processed = await self._execute()
        run.record_stage_success(
            "execution",
            records_processed=processed,
            completed_at=self._clock.now(),
        )

        run.record_stage_start("postrun", self._clock.now())
        await self._postrun()
        run.record_stage_success(
            "postrun",
            records_processed=0,
            completed_at=self._clock.now(),
        )

        run.complete(self._clock.now())
    except Exception as exc:
        run.fail(str(exc), failed_at=self._clock.now())
        raise
    finally:
        events = run.collect_events()
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

| Control      | Requirement                                                                | Status | Evidence                             |
| ------------ | -------------------------------------------------------------------------- | ------ | ------------------------------------ |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-021-ddd-aggregates-adoption.md` |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted (Implemented 2025-12-29)`  |
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

- [x] The decision is documented with current status, date, and owner metadata.
- [x] The implementation path or adoption boundary is testable and linked from the ADR.
- [x] Supersession or migration impact is documented when the decision changes an earlier posture or is marked not applicable.
- [x] Related docs, contracts, and operational guidance are aligned with this ADR.

2026-05-25 review note: acceptance status was reconciled during the AR-014
evidence-refresh follow-up. Future changes to this ADR require updating the
`Compliance`, `Verification`, and linked governance tests in the same change.
