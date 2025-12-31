# ADR-021: Внедрение DDD Aggregates в Domain Layer

*   **Status**: Accepted (Implemented 2025-12-29)
*   **Date**: 2025-12-29

## Контекст

### Мотивация

В рамках развития архитектуры BioETL возникла необходимость усилить защиту бизнес-инвариантов
и улучшить модульность domain слоя. Ранее бизнес-логика была распределена между application
и domain слоями без чёткой модели владения данными.

### Проблемы до рефакторинга

1. **Отсутствие инвариантной защиты**: Batch-записи могли модифицироваться на любом этапе
2. **Размытые границы консистентности**: Непонятно, какие объекты должны изменяться транзакционно
3. **Отсутствие Event Sourcing**: Нет механизма отслеживания изменений состояния
4. **Слабая типизация идентификаторов**: `run_id` и `batch_id` были обычными строками

### Затронутые области

- `src/bioetl/domain/aggregates/` — новый пакет
- `src/bioetl/domain/value_objects/` — новый пакет
- `src/bioetl/domain/types.py` — расширен новыми типами
- `src/bioetl/domain/exceptions/` — добавлены DDD-исключения

## Решение

### 1. Добавлены DDD Aggregates

Три ключевых агрегата с защищёнными инвариантами:

#### Batch Aggregate (`domain/aggregates/batch.py`)

```python
class Batch:
    """Aggregate Root для коллекции записей.

    Инварианты:
        1. Все записи имеют один batch_id
        2. Записи нельзя добавить после seal()
        3. batch_id неизменяем
        4. Индексы записей последовательны
        5. Карантинные записи отслеживаются отдельно
    """

    def add_record(self, data: dict) -> BatchRecord: ...
    def quarantine_record(self, record: BatchRecord, error: str) -> BatchRecord: ...
    def seal(self) -> None: ...
    def mark_writing(self) -> None: ...
    def mark_committed(self, layer: str) -> None: ...
    def mark_failed(self, layer: str, error: str) -> None: ...
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
        3. end_time != None только для терминальных статусов
        4. stages нельзя модифицировать после терминального статуса
        5. run_id неизменяем после создания
    """

    def start(self) -> None: ...
    def record_stage_start(self, stage: str) -> None: ...
    def record_stage_success(self, stage: str, records: int) -> None: ...
    def record_stage_failure(self, stage: str, error: str) -> None: ...
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
        1. entry_id неизменяем
        2. Статус переходит только в указанном порядке
        3. Повторные попытки (retries) инкрементируются атомарно
    """

    def mark_retrying(self) -> None: ...
    def mark_recovered(self) -> None: ...
    def mark_dead_letter(self, reason: str) -> None: ...
```

### 2. Добавлены Value Objects

Строго типизированные идентификаторы в `domain/value_objects/`:

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
| `BatchWritten` | Batch | После `batch.mark_committed()` |
| `BatchFailed` | Batch | После `batch.mark_failed()` |
| `RecordQuarantined` | Batch | После `batch.quarantine_record()` |
| `RunStarted` | PipelineRun | После `run.start()` |
| `StageCompleted` | PipelineRun | После `run.record_stage_success()` |
| `StageFailed` | PipelineRun | После `run.record_stage_failure()` |
| `RunCompleted` | PipelineRun | После `run.complete()` |
| `RunFailed` | PipelineRun | После `run.fail()` |

### 4. Структура domain слоя после рефакторинга

```
src/bioetl/domain/
├── aggregates/           # DDD Aggregates
│   ├── __init__.py
│   ├── batch.py          # Batch Aggregate (~530 LOC)
│   ├── pipeline_run.py   # PipelineRun Aggregate (~350 LOC)
│   ├── quarantine_entry.py # QuarantineEntry Aggregate (~180 LOC)
│   └── events.py         # Domain Events (~200 LOC)
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

## Последствия

### Положительные

1. **Защита инвариантов**: State machine в агрегатах предотвращает некорректные переходы
2. **Чёткие границы консистентности**: Каждый агрегат — единица транзакционной консистентности
3. **Event Sourcing Ready**: `collect_events()` позволяет публиковать события
4. **Типобезопасность**: Value Objects исключают смешение идентификаторов
5. **Тестируемость**: Агрегаты можно тестировать изолированно без I/O
6. **Документирование бизнес-правил**: Инварианты явно описаны в docstrings

### Отрицательные

1. **Увеличение сложности**: Добавлено ~1260 LOC нового кода в domain
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
async def process_batch(self, records: list[dict]) -> None:
    batch = Batch.create(run_id=self._run_id)

    for record in records:
        batch.add_record(record)

    # Валидация
    for record in batch.all_records:
        if not self._validate(record.data):
            batch.quarantine_record(record, "Validation failed")

    batch.seal()

    # Запись
    batch.mark_writing()
    try:
        await self._writer.write(batch.records)
        batch.mark_committed("silver")
    except Exception as e:
        batch.mark_failed("silver", str(e))
        raise

    # Публикация событий
    events = batch.collect_events()
    for event in events:
        await self._event_bus.publish(event)
```

### PipelineRun Aggregate в PipelineRunner

```python
# application/core/runner.py
async def run(self) -> None:
    run = PipelineRun.create(
        run_id=self._run_id,
        pipeline_name=self._config.pipeline_name,
        run_type=self._runtime.run_type,
    )

    run.start()

    try:
        run.record_stage_start("preflight")
        await self._preflight()
        run.record_stage_success("preflight", records_processed=0)

        run.record_stage_start("execution")
        processed = await self._execute()
        run.record_stage_success("execution", records_processed=processed)

        run.record_stage_start("postrun")
        await self._postrun()
        run.record_stage_success("postrun", records_processed=0)

        run.complete()
    except Exception as e:
        run.fail(str(e))
        raise
    finally:
        events = run.collect_events()
        # Publish events...
```

## Связанные документы

- [ADR-020: Декомпозиция BasePipeline](ADR-020-basepipeline-decomposition.md) — рефакторинг application layer
- [ADR-015: Pipeline Services Lifecycle](ADR-015-pipeline-services-lifecycle.md) — lifecycle management
- [RULES.md §1.1](../../RULES.md) — Ports & Adapters Architecture
- [docs/glossary.md](../../glossary.md) — Ubiquitous Language

## Альтернативы рассмотренные

### 1. Оставить простые dataclasses

- **Плюсы**: Меньше кода, проще понять
- **Минусы**: Нет защиты инвариантов, нет state machine
- **Решение**: Отклонено

### 2. Full Event Sourcing

- **Плюсы**: Полная история изменений
- **Минусы**: Значительная сложность, требует event store
- **Решение**: Отклонено, но `collect_events()` готов к эволюции

### 3. CQRS

- **Плюсы**: Разделение чтения и записи
- **Минусы**: Over-engineering для текущего масштаба
- **Решение**: Отклонено, рассмотреть при масштабировании
