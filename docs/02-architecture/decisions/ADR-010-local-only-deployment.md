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

- **ADR-003**: Superseded — Redis больше не используется
- **ADR-002**: Medallion Architecture — сохраняется, меняется только storage backend
- **ADR-005**: Composition Layer — упрощён, удалены cloud factories

## Migration Notes

При обновлении с предыдущих версий:
1. Удалить Docker Compose конфигурацию (minio, redis)
2. Обновить переменные окружения (удалить AWS_*, REDIS_*)
3. Переустановить зависимости: `pip install -e .[dev]`
4. Перенести данные из S3 в локальную директорию `data/`
