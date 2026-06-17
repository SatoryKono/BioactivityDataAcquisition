______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-014: Deterministic Writes and Retries

**Date:** 2025-12-24
**Status:** Accepted
**Decision makers:** @BioETL-Team

## Context

Для обеспечения воспроизводимости и упрощения отладки пайплайнов необходим детерминизм:

1. **Проблема отладки**: При расследовании инцидентов невозможно воспроизвести точное поведение из-за:

   - `random.uniform()` в retry jitter
   - `datetime.now()` вызывается в разных местах с микросекундными различиями

1. **Проблема тестирования**: Тесты с random/datetime.now() flaky и непредсказуемы

1. **Источники недетерминизма в кодовой базе**:

| Файл                                      | Паттерн            | Контекст            |
| ----------------------------------------- | ------------------ | ------------------- |
| `infrastructure/adapters/http/client.py`  | `random.uniform()` | Retry jitter        |
| `infrastructure/storage/gold_writer.py`   | `random.uniform()` | Write backoff       |
| `infrastructure/storage/bronze_writer.py` | `datetime.now()`   | Ingestion timestamp |
| `infrastructure/quarantine/unified.py`    | `datetime.now()`   | Error timestamp     |

## Decision

### 1. Детерминистичный Retry Jitter

Добавлен режим `deterministic=True` в `RetryConfig`:

```python
@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0
    jitter: float = 0.1
    deterministic: bool = False  # NEW
    jitter_seed: int | None = None  # NEW

    def calculate_delay(self, attempt: int, url: str = "") -> float:
        delay = self.base_delay * (self.multiplier ** attempt)

        if self.deterministic:
            # Hash-based deterministic jitter; do not use Python's salted hash().
            import hashlib

            hash_input = f"{attempt}:{url}:{self.jitter_seed or 0}".encode("utf-8")
            jitter_raw = int(hashlib.md5(hash_input, usedforsecurity=False).hexdigest()[:8], 16)
            jitter_factor = (jitter_raw % 1000) / 1000.0
            delay += delay * self.jitter * (jitter_factor * 2 - 1)
        else:
            delay += random.uniform(-delay * self.jitter, delay * self.jitter)

        return max(0.0, delay)
```

### 2. Запрет random в Storage Writers

- Удалён `import random` из `gold_writer.py`
- `random.uniform(0, 0.1)` заменён на фиксированный `0.05`
- Архитектурный тест `test-no-random-in-writers` блокирует регрессии

### 3. Единый Источник Времени

`PipelineContext.started_at` в `domain/context.py` — канонический source-of-time seam для pipeline runtime:

```python
@dataclass(frozen=True)
class PipelineContext:
    run-id: RunID
    run-type: RunType
    logger: LoggerPort
    started_at: datetime = field(default-factory=-now-utc)

    @classmethod
    def create(cls, run-id, run-type, logger, started_at=None):
        return cls(..., started_at=started_at or datetime.now(UTC))
```

Infrastructure компоненты получают timestamp как параметр:

```python
# Application/composition layer
ingestion_ts = self.-context.started_at

# Infrastructure layer - receives timestamp
await bronze-writer.write-bronze(..., ingestion_ts=ingestion_ts)
await quarantine.write(..., ingestion_ts=ingestion_ts)
```

Domain business paths не должны создавать текущее время самостоятельно:

- aggregate lifecycle transitions получают `started_at/completed_at/failed_at/...` явно
- read-model расчёты используют либо сохранённый terminal timestamp, либо explicit `reference_time`
- operational/reporting structures получают `checked_at` / `execution_timestamp` из application/runtime seam
- replay-critical application/composition surfaces (runtime timing helper, composite checkpoint state transitions, manifest creation, and composition entrypoints) MUST принимать `ClockPort` или explicit timestamp/reference time, а не читать локальный wall-clock внутри helper'ов

`ClockPort` ownership is intentionally split:

- the contract is owned by `bioetl.domain.ports.ClockPort`;
- application services and helpers accept `ClockPort` or explicit timestamp/reference-time inputs and may use `bioetl.application.runtime_clock.resolve_runtime_clock` to fail closed when a required clock is missing;
- `bioetl.infrastructure.time.SystemClock` is the concrete system-time adapter;
- composition/bootstrap modules wire `SystemClock` into application services, while `domain`, `application`, and `interfaces` must not instantiate infrastructure clocks directly.

### 4. Deterministic Domain Identities

Replay-sensitive domain aggregates and domain events MUST NOT create hidden UUID4
values. Aggregate IDs and default domain event IDs are derived from explicit
canonical inputs:

- `Batch.create(...)` derives `BatchID` from `run_id`, `start_index`,
  `created_at`, and metadata.
- `QuarantineEntry.create(...)` derives `entry_id` from pipeline, error,
  payload hash, run/batch IDs, explicit timestamp, and metadata.
- `DomainEvent` derives a default `event_id` from the concrete event type and
  event payload; callers may still pass an explicit `event_id` when replaying a
  persisted event.
- `tests/fixtures/golden/domain/deterministic_identity_v1.json` pins the
  namespace/canonicalization contract for these IDs. Any change to the golden
  values is a compatibility event and requires an ADR update.
- Runtime `uuid4` defaults in `application/` and `composition/` are not domain
  identities. They must stay classified in
  `configs/quality/runtime_uuid_seams.yaml`; replay-critical identity must be
  explicit or derived via deterministic domain identity.
- Replay-critical checkpoint/manifest timestamps must be caller-owned:
  application services use `ClockPort` or explicit timestamp parameters, while
  storage adapters must not add hidden wall-clock metadata.

### 5. Архитектурные Тесты

| Тест                                          | Цель                                                                                                                |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `test-no-random-in-writers`                   | Блокирует `import random` в `infrastructure/storage/`                                                               |
| `test-no-datetime-now-in-infrastructure`      | Блокирует `datetime.now()` в `infrastructure/`                                                                      |
| `test-no-datetime-now-in-domain`              | Блокирует `datetime.now()` в `domain/` вне `domain/context.py`                                                      |
| `test-replay-critical-time-seams`             | Блокирует `datetime.now()` в replay-critical `application/` и `composition/` runtime/checkpoint/control-plane seams |
| `test-no-structlog-in-application-interfaces` | Блокирует прямой импорт `structlog` в `application/` и `interfaces/`                                                |
| `test_domain_aggregate_identity_surfaces_do_not_call_uuid4` | Блокирует hidden UUID4 в replay-sensitive aggregate/event identity surfaces |
| `test_runtime_uuid4_generation_seams_are_classified` | Блокирует новые не классифицированные `uuid4` seams в `application/` и `composition/` |
| `test_deterministic_identity_golden_contract_is_stable` | Фиксирует golden values для domain identity namespace/canonicalization |
| `test_replay_critical_checkpoint_surfaces_do_not_call_wall_clock_directly` | Блокирует прямой wall-clock в checkpoint persistence surfaces |

### 6. Изоляция логирования

Application и interfaces слои **MUST NOT** импортировать `structlog` напрямую — использовать абстракцию `LoggerPort` из `domain.ports`. Это обеспечивает:

- Тестируемость (можно подменить логгер в тестах)
- Независимость от конкретной реализации
- Единообразие обработки ошибок

## Consequences

### Положительные

1. **Воспроизводимость**: Одинаковые входные данные → одинаковое поведение
1. **Тестируемость**: Детерминистичные тесты без flakiness
1. **Отладка**: Можно воспроизвести точную последовательность событий
1. **Консистентность**: Все записи в batch имеют одинаковый `_ingestion_ts`

### Отрицательные

1. **API усложнение**: Дополнительные параметры (`ingestion_ts`, `deterministic`)
1. **Миграция**: Требуется обновление всех вызовов infrastructure компонентов
1. **API discipline**: replay-critical seams больше нельзя quietly переводить на локальный wall-clock fallback; время должно приходить из `ClockPort` или explicit timestamp parameter

## Implementation

### Изменённые файлы

| Файл                                      | Изменение                              |
| ----------------------------------------- | -------------------------------------- |
| `domain/context.py`                       | Добавлен `started_at` field            |
| `application/core/record_processor.py`    | Использует `context.started_at`        |
| `application/core/base.py`                | Использует `PipelineContext.create()`  |
| `infrastructure/adapters/http/client.py`  | Добавлен `deterministic` mode          |
| `infrastructure/storage/gold_writer.py`   | Удалён `random`, фиксированный backoff |
| `infrastructure/storage/bronze_writer.py` | Принимает `ingestion_ts` параметр      |
| `infrastructure/quarantine/unified.py`    | Принимает `ingestion_ts` параметр      |
| `domain/ports/quarantine.py`              | Обновлён `QuarantinePort.write()`      |

### Архитектурные тесты

- `tests/architecture/test_no_random_in_writers.py`
- `tests/architecture/test_no_datetime_now_in_infrastructure.py`
- `tests/architecture/test_replay_critical_time_seams.py`
- `tests/architecture/test_no_structlog_in_application_interfaces.py`

## Compliance

| Control      | Requirement                                                                | Status | Evidence                             |
| ------------ | -------------------------------------------------------------------------- | ------ | ------------------------------------ |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-014-deterministic-writes.md`    |
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

## References

- [ADR-044: RunManifest/RunLedger Control Plane](ADR-044-run-manifest-ledger-control-plane.md)
- [Runtime Clock Port](../../../src/bioetl/domain/ports/runtime/clock.py)
- [SystemClock adapter](../../../src/bioetl/infrastructure/time/system_clock.py)
