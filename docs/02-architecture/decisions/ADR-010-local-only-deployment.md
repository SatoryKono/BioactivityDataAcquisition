# ADR-010: Local-Only Deployment Strategy

*   **Status**: Accepted
*   **Date**: 2025-12-23
*   **Supersedes**: ADR-003 (Redis for Distributed Locking)

## Context

BioETL изначально проектировался с поддержкой облачной инфраструктуры:
- S3 для хранения Bronze/Silver/Gold слоёв
- Redis для распределённых блокировок
- Prefect для оркестрации пайплайнов

Однако анализ реальных сценариев использования показал, что:
1. Проект используется преимущественно для локальной разработки и исследований
2. Облачное развёртывание не планируется в обозримом будущем
3. Поддержка облачной инфраструктуры добавляет значительную сложность
4. Зависимости от внешних сервисов усложняют локальную разработку

## The Decision

Переход на **исключительно локальное развертывание** с использованием:
- **Локальная файловая система** для всех слоёв данных (Bronze, Silver, Gold)
- **In-memory блокировки** (MemoryLock) вместо Redis
- **Локальные checkpoints** вместо S3
- **CLI-based execution** вместо Prefect orchestration

### Strict Single Instance Constraint
Система спроектирована как **Single Instance Application**.
- **ЗАПРЕЩЕНО** запускать несколько экземпляров одного пайплайна одновременно.
- **ЗАПРЕЩЕНО** горизонтальное масштабирование (Horizontal Scaling).
- **ОТКАЗ ОТ REDIS**: Использование Redis Lock и распределенных блокировок **ЗАПРЕЩЕНО**.
- Система полагается на эксклюзивный доступ к файловой системе.
- Блокировки `MemoryLock` работают только в пределах одного процесса и не защищают от гонок между процессами.

## Justification

### 1. Упрощение архитектуры

| До | После |
|---|---|
| S3 + boto3 | Локальная ФС (pathlib) |
| Redis + aioredis | MemoryLock |
| Prefect + tasks | CLI + PipelineRunner |
| Docker Compose (minio, redis) | Python venv только |

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
    access_key="...",
    secret_key="..."
)

# Стало
writer = BronzeWriter(base_path=Path("data/bronze"))
```

### Locking

```python
# Было
lock = RedisDistributedLock(redis_client)

# Стало
lock = MemoryLock()
```

#### MemoryLock Features (RULES.md §3.3)

Хотя MemoryLock работает только в пределах одного процесса, он реализует **полный функционал LockPort**:

| Функционал | Реализация | Файл:строки |
|------------|------------|-------------|
| **TTL-based expiration** | `_ttl_checker_loop()` — фоновая задача проверяет и освобождает просроченные блокировки | `memory_lock.py:43-64` |
| **Heartbeat** | `heartbeat()` — продлевает TTL блокировки на original_ttl | `memory_lock.py:176-204` |
| **Safety Guard** | `validate_owner()` — проверяет владельца перед записью в storage | `memory_lock.py:206-238` |
| **Graceful Shutdown** | `aclose()` — отменяет TTL checker и освобождает все блокировки | `memory_lock.py:240-256` |

**Конфигурация по умолчанию** (из `PipelineSettings`):
- `heartbeat_interval = 20s` (см. `config.py:254`)
- `effective_lock_ttl = heartbeat_interval * 3 = 60s`
- TTL check interval = 1s

**Пример использования:**

```python
lock = MemoryLock()
await lock.acquire(key="pipeline:chembl", owner_id=run_id, ttl=60)

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
checkpoint = S3Checkpoint(
    bucket="checkpoints",
    endpoint_url="..."
)

# Стало
checkpoint = LocalCheckpoint(base_path=Path("data/checkpoints"))
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
        return self.data_dir / "bronze"
```

## Consequences

### Positive

1. **Простота**: Меньше кода, меньше конфигурации, меньше точек отказа
2. **Портативность**: Работает на любой машине с Python 3.11+
3. **Тестируемость**: Unit тесты работают без внешних сервисов
4. **Быстрый старт**: Новые разработчики могут начать работу мгновенно

### Negative

1. **Нет распределённого запуска**: Только один процесс может работать с данными
2. **Нет облачного масштабирования**: Ограничено локальным диском
3. **Нет отказоустойчивости**: Нет репликации данных

### Mitigation

При необходимости облачного развёртывания в будущем:
1. Порты (Protocols) в domain слое остались неизменными
2. **Однако**, внедрение распределенных блокировок (Redis) потребует пересмотра этого ADR и явного одобрения, так как текущая стратегия — жесткий Local-Only.
3. Hexagonal архитектура позволяет добавлять адаптеры, но это **ЗАПРЕЩЕНО** текущей политикой.

## Related ADRs

- [ADR-002](ADR-002-medallion-architecture.md): Medallion Architecture — сохраняется, меняется только storage backend
- [ADR-003](ADR-003-in-memory-locking-strategy.md): In-Memory Locking — детализация стратегии блокировок
- [ADR-005](ADR-005-composition-layer-separation.md): Composition Layer — упрощён, удалены cloud factories
- [ADR-008](ADR-008-graceful-shutdown-strategy.md): Graceful Shutdown — MemoryLock shutdown behavior
- [ADR-011](ADR-011-remove-watermark-mechanism.md): Remove Watermark — simplification aligned with Local-Only
- [ADR-022](ADR-022-tracing-noop.md): NoOp Tracing — NoOp pattern consistent with Local-Only (no external infra)

## Migration Notes

При обновлении с предыдущих версий:
1. Удалить Docker Compose конфигурацию (minio, redis)
2. Обновить переменные окружения (удалить AWS_*, REDIS_*)
3. Переустановить зависимости: `pip install -e .[dev]`
4. Перенести данные из S3 в локальную директорию `data/`
