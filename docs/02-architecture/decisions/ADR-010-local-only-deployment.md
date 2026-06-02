______________________________________________________________________

Version: 1.1.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-01'

______________________________________________________________________

# ADR-010: Local-Only Deployment Strategy

**Date:** 2025-12-23
**Status:** Accepted
**Last updated:** 2026-01-02
**Decision makers:** @BioETL-Team
**Supersedes:** [ADR-003](ADR-003-in-memory-locking-strategy.md) (original multi-instance lock posture)

## Context

BioETL изначально проектировался с поддержкой облачной инфраструктуры:

- S3 для хранения Bronze/Silver/Gold слоёв
- Redis для распределённых блокировок
- Prefect для оркестрации пайплайнов

Однако анализ реальных сценариев использования показал, что:

1. Проект используется преимущественно для локальной разработки и исследований
1. Облачное развёртывание не планируется в обозримом будущем
1. Поддержка облачной инфраструктуры добавляет значительную сложность
1. Зависимости от внешних сервисов усложняют локальную разработку

## Decision

Переход на **исключительно локальное развертывание** с использованием:

- **Локальная файловая система** для всех слоёв данных (Bronze, Silver, Gold)
- **In-memory блокировки** (MemoryLock) вместо Redis
- **Локальные checkpoints** вместо S3
- **CLI-based execution** вместо Prefect orchestration

### Strict Single Instance Constraint

Система спроектирована как **Single Instance Application**.

- **ЗАПРЕЩЕНО** запускать несколько экземпляров одного пайплайна одновременно.
- **ЗАПРЕЩЕНО** горизонтальное масштабирование (Horizontal Scaling).
- **ОТКАЗ ОТ REDIS**: Использование Redis Lock и межпроцессной lock-координации **ЗАПРЕЩЕНО**.
- Система полагается на эксклюзивный доступ к файловой системе.
- Блокировки `MemoryLock` работают только в пределах одного процесса и не защищают от гонок между процессами.

## Justification

### 1. Упрощение архитектуры

| До                            | После                  |
| ----------------------------- | ---------------------- |
| S3 + boto3                    | Локальная ФС (pathlib) |
| Redis + aioredis              | MemoryLock             |
| Prefect + tasks               | CLI + PipelineRunner   |
| Application runtime Docker Compose (minio, redis) | Python venv только; reviewed optional helper compose files are adjunct tooling only |

### 2. Уменьшение зависимостей

Удалены зависимости:

- `boto3`, `boto3-stubs` (AWS SDK)
- `redis`, `aioredis` (Redis client)
- `prefect` (Workflow orchestration)
- `fakeredis`, `moto` (Test mocks)
- `pytest-docker` (Docker integration tests)

### 3. Упрощение разработки

- Нет необходимости в Docker для запуска тестов
- Быстрый старт: `make install && make test`
- Отладка без внешних сервисов

### 4. Достаточность для use cases

Локальный запуск полностью покрывает:

- Исследования и прототипирование
- Разовые загрузки данных
- Локальную аналитику
- CI/CD тестирование

## Implementation

### Storage

```python
# Было
writer = BronzeWriter(
    bucket="bronze-bucket",
    endpoint_url="http://minio:9000",
    access - key="...",
    secret - key="...",
)

# Стало
writer = BronzeWriter(base_path=Path("data/output/bronze"))
```

### Locking

```python
# Было
lock = RedisDistributedLock(redis - client)

# Стало
lock = MemoryLock()
```

#### MemoryLock Features (RULES.md §3.3)

Хотя MemoryLock работает только в пределах одного процесса, он реализует **полный функционал LockPort**:

| Функционал               | Реализация                                                                             | Файл:строки              |
| ------------------------ | -------------------------------------------------------------------------------------- | ------------------------ |
| **TTL-based expiration** | `_ttl_checker_loop()` — фоновая задача проверяет и освобождает просроченные блокировки | `memory_lock.py:43-64`   |
| **Heartbeat**            | `heartbeat()` — продлевает TTL блокировки на original_ttl                              | `memory_lock.py:176-204` |
| **Safety Guard**         | `validate_owner()` — проверяет владельца перед записью в storage                       | `memory_lock.py:206-238` |
| **Graceful Shutdown**    | `aclose()` — отменяет TTL checker и освобождает все блокировки                         | `memory_lock.py:240-256` |

**Конфигурация по умолчанию** (из `PipelineSettings`):

- `heartbeat_interval = 30s` (см. `config.py:238`)
- `effective_lock_ttl = heartbeat_interval * 3 = 90s`
- TTL check interval = 1s

**Пример использования:**

```python
lock = MemoryLock()
await lock.acquire(key="pipeline:chembl", owner_id=run_id, ttl=90)

# В пайплайне — периодически продлевать
await lock.heartbeat(key="pipeline:chembl", owner_id=run_id)

# Перед записью — проверить владельца (Safety Guard)
if not await lock.validate_owner(key="pipeline:chembl", owner_id=run_id):
    raise LockNotHeldError("Lock lost during processing")

await lock.release(key="pipeline:chembl", owner_id=run_id)
```

**Ограничения:**

- Не защищает от гонок между процессами (by design)
- Требует single-instance deployment (см. Strict Single Instance Constraint)

### Checkpoints

```python
# Было
checkpoint = S3Checkpoint(bucket="checkpoints", endpoint_url="...")

# Стало
checkpoint = LocalCheckpoint(base_path=Path("data/output/checkpoints"))
```

### Configuration

```python
# Было
class Settings:
    aws: AWSSettings
    s3: S3Settings
    redis: RedisSettings


# Стало
class Settings:
    data_dir: Path = Path("data")

    @property
    def bronze_path(self) -> Path:
        return self.data_dir / "output" / "bronze"
```

## Consequences

### Positive

1. **Простота**: Меньше кода, меньше конфигурации, меньше точек отказа
1. **Портативность**: Работает на любой машине с Python 3.11+
1. **Тестируемость**: Unit тесты работают без внешних сервисов
1. **Быстрый старт**: Новые разработчики могут начать работу мгновенно

### Negative

1. **Нет распределённого запуска**: Только один процесс может работать с данными
1. **Нет облачного масштабирования**: Ограничено локальным диском
1. **Нет отказоустойчивости**: Нет репликации данных

### Mitigation

При необходимости облачного развёртывания в будущем:

1. Порты (Protocols) в domain слое остались неизменными
1. **Однако**, внедрение межпроцессной lock-координации (Redis) потребует пересмотра этого ADR и явного одобрения, так как текущая стратегия — жесткий Local-Only.
1. Hexagonal архитектура позволяет добавлять адаптеры, но это **ЗАПРЕЩЕНО** текущей политикой.

## References

- [ADR-002](ADR-002-medallion-architecture.md): Medallion Architecture — сохраняется, меняется только storage backend (Updated: 2025-05-20)
- [ADR-003](ADR-003-in-memory-locking-strategy.md): In-Memory Locking — детализация стратегии блокировок (Updated: 2025-12-23)
- [ADR-005](ADR-005-composition-layer-separation.md): Composition Layer — упрощён, удалены cloud factories (Updated: 2025-12-18)
- [ADR-008](ADR-008-graceful-shutdown-strategy.md): Graceful Shutdown — MemoryLock shutdown behavior (Updated: 2025-12-22)
- [ADR-011](ADR-011-remove-watermark-mechanism.md): Remove Watermark — simplification aligned with Local-Only (Updated: 2025-12-23)
- [ADR-022](ADR-022-tracing-noop.md): NoOp Tracing — NoOp pattern consistent with Local-Only (no external infra) (Updated: 2025-12-27)

## Rollout

При обновлении с предыдущих версий:

1. Удалить или деклассифицировать Docker Compose конфигурацию (minio, redis),
   если она используется как application runtime, storage, locking или
   orchestration path.
1. Reviewed root-level helper compose files MAY remain only under
   `BIOETL_DOCKER_HELPER_ADR010_ADJUNCT` governance and MUST NOT be used by
   application logic.
1. Обновить переменные окружения application runtime (удалить AWS-*, REDIS-*).
1. Переустановить зависимости: `pip install -e .[dev]`
1. Перенести данные из S3 в локальную директорию `data/`

## Migration Notes

При migration / reconciliation with current published storage docs используйте
современную output-root topology:

- Bronze data -> `data/output/bronze/`
- Silver data -> `data/output/silver/`
- Gold data -> `data/output/gold/`
- Checkpoints -> `data/output/checkpoints/`

Исторические локальные пути вида `data/bronze` и `data/checkpoints` следует
трактовать как pre-ADR-025 simplification, а не как current canonical storage
layout.

## Compliance

| Control      | Requirement                                                                | Status     | Evidence                             |
| ------------ | -------------------------------------------------------------------------- | ---------- | ------------------------------------ |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass`     | `ADR-010-local-only-deployment.md`   |
| Status       | ADR status MUST be explicit and consistent                                 | `pass`     | `Accepted`                           |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `declared` | `metadata block`                     |
| Verification | Implementation and validation expectations MUST be documented              | `pass`     | `Verification / Acceptance Criteria` |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass`     | `References`                         |

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
