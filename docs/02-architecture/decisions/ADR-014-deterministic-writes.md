---
Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-30'
---

# ADR-014: Deterministic Writes and Retries

**Date:** 2025-12-24
**Status:** Accepted
**Decision makers:** @BioETL-Team

## Context

Для обеспечения воспроизводимости и упрощения отладки пайплайнов необходим детерминизм:

1. **Проблема отладки**: При расследовании инцидентов невозможно воспроизвести точное поведение из-за:
   - `random.uniform()` в retry jitter
   - `datetime.now()` вызывается в разных местах с микросекундными различиями

2. **Проблема тестирования**: Тесты с random/datetime.now() flaky и непредсказуемы

3. **Источники недетерминизма в кодовой базе**:

| Файл | Паттерн | Контекст |
|------|---------|----------|
| `infrastructure/adapters/http/client.py` | `random.uniform()` | Retry jitter |
| `infrastructure/storage/gold_writer.py` | `random.uniform()` | Write backoff |
| `infrastructure/storage/bronze_writer.py` | `datetime.now()` | Ingestion timestamp |
| `infrastructure/quarantine/unified.py` | `datetime.now()` | Error timestamp |

## Decision

### 1. Детерминистичный Retry Jitter

Добавлен режим `deterministic=True` в `RetryConfig`:

```python
@dataclass
class RetryConfig:
    max-attempts: int = 3
    base-delay: float = 1.0
    jitter: float = 0.1
    deterministic: bool = False  # NEW
    jitter-seed: int | None = None  # NEW

    def calculate-delay(self, attempt: int, url: str = "") -> float:
        delay = self.base-delay * (self.multiplier ** attempt)

        if self.deterministic:
            # Hash-based deterministic jitter
            hash-input = f"{attempt}:{url}:{self.jitter-seed or 0}"
            jitter-factor = (hash(hash-input) % 1000) / 1000.0
            delay += delay * self.jitter * (jitter-factor * 2 - 1)
        else:
            delay += random.uniform(-delay * self.jitter, delay * self.jitter)

        return max(0.0, delay)
```

### 2. Запрет random в Storage Writers

- Удалён `import random` из `gold_writer.py`
- `random.uniform(0, 0.1)` заменён на фиксированный `0.05`
- Архитектурный тест `test-no-random-in-writers` блокирует регрессии

### 3. Единый Источник Времени

`PipelineContext.started_at` — единственный источник timestamps для batch:

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
# Application layer
ingestion_ts = self.-context.started_at

# Infrastructure layer - receives timestamp
await bronze-writer.write-bronze(..., ingestion_ts=ingestion_ts)
await quarantine.write(..., ingestion_ts=ingestion_ts)
```

### 4. Архитектурные Тесты

| Тест | Цель |
|------|------|
| `test-no-random-in-writers` | Блокирует `import random` в `infrastructure/storage/` |
| `test-no-datetime-now-in-infrastructure` | Блокирует `datetime.now()` в `infrastructure/` |
| `test-no-structlog-in-application-interfaces` | Блокирует прямой импорт `structlog` в `application/` и `interfaces/` |

### 5. Изоляция логирования

Application и interfaces слои **MUST NOT** импортировать `structlog` напрямую — использовать абстракцию `LoggerPort` из `domain.ports`. Это обеспечивает:
- Тестируемость (можно подменить логгер в тестах)
- Независимость от конкретной реализации
- Единообразие обработки ошибок

## Consequences

### Положительные

1. **Воспроизводимость**: Одинаковые входные данные → одинаковое поведение
2. **Тестируемость**: Детерминистичные тесты без flakiness
3. **Отладка**: Можно воспроизвести точную последовательность событий
4. **Консистентность**: Все записи в batch имеют одинаковый `_ingestion_ts`

### Отрицательные

1. **API усложнение**: Дополнительные параметры (`ingestion_ts`, `deterministic`)
2. **Миграция**: Требуется обновление всех вызовов infrastructure компонентов
3. **Backward compatibility**: Fallback на `datetime.now()` при отсутствии параметра

## Implementation

### Изменённые файлы

| Файл | Изменение |
|------|-----------|
| `domain/context.py` | Добавлен `started_at` field |
| `application/core/record_processor.py` | Использует `context.started_at` |
| `application/core/base.py` | Использует `PipelineContext.create()` |
| `infrastructure/adapters/http/client.py` | Добавлен `deterministic` mode |
| `infrastructure/storage/gold_writer.py` | Удалён `random`, фиксированный backoff |
| `infrastructure/storage/bronze_writer.py` | Принимает `ingestion_ts` параметр |
| `infrastructure/quarantine/unified.py` | Принимает `ingestion_ts` параметр |
| `domain/ports/quarantine.py` | Обновлён `QuarantinePort.write()` |

### Архитектурные тесты

- `tests/architecture/test_no_random_in_writers.py`
- `tests/architecture/test_no_datetime_now_in_infrastructure.py`
- `tests/architecture/test_no_structlog_in_application_interfaces.py`

## Compliance

| Control | Requirement | Status | Evidence |
|---|---|---|---|
| Format | ADR MUST use standard metadata and normalized section headings | `pass` | `ADR-014-deterministic-writes.md` |
| Status | ADR status MUST be explicit and consistent | `pass` | `Accepted` |
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

## References

- `<link-or-path>`
