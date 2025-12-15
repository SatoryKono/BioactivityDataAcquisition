# ETL Layers
*Aligned with RULES.md v5.0*

## Философия (§1)

> "Прагматичная инженерия". Избегаем избыточной сложности (Over-engineering), 
> архитектура должна ускорять вывод продукта на рынок (time-to-market).

**Паттерн**: Слоистая архитектура с инверсией зависимостей (Ports & Adapters).

---

## Слои и Контракты (§1.1)

| Слой | Ответственность | Зависимости |
|------|-----------------|-------------|
| **Domain** | Чистые функции, Protocols, бизнес-правила | Ничего |
| **Application** | Оркестрация потоков, use cases | Domain |
| **Infrastructure** | I/O (HTTP, БД, FS, Redis) | Domain, Application |
| **Interfaces** | CLI, API endpoints | Application |

### Обеспечение Контрактов (§1.1.1)

Интерфейсы определяются через `typing.Protocol` (не ABC):

```python
# domain/ports.py
from typing import Protocol, Iterator

class DataSourcePort(Protocol):
    """Port для извлечения данных."""
    async def fetch(self, query: Query) -> Iterator[RawRecord]: ...
    async def health_check(self) -> bool: ...
```

- **Design-time**: `mypy --strict` — основной механизм контроля
- **Runtime Boundary**: `@runtime_checkable` только для критичных адаптеров

---

## Domain Layer

**Расположение**: `src/bioetl/domain/`

### Компоненты

| Компонент | Расположение | Ответственность |
|-----------|--------------|-----------------|
| **Ports** | `domain/ports.py` | Protocol-интерфейсы для DI |
| **Models** | `domain/models/` | Pydantic-модели сущностей |
| **Schemas** | `domain/schemas/` | Pandera-схемы валидации |
| **Services** | `domain/services/` | Чистая бизнес-логика |
| **Rules** | `domain/rules/` | DQ правила, Schema Drift detection |

### Ключевые Сервисы

| Сервис | Назначение | Правило |
|--------|------------|---------|
| `HashService` | Content Hash (§2.8.1) | Детерминированный SHA256 |
| `ValidationService` | Pandera-валидация | §2.6 DQ thresholds |
| `NormalizationService` | Нормализация значений | §2.8.1 floats, dates, strings |
| `SchemaDriftDetector` | Обнаружение дрейфа | §2.2 Info/Warn/Critical |

### Bounded Contexts (ChEMBL)

Каждый контекст имеет собственные схемы и правила:

| Context | Schema | Location |
|---------|--------|----------|
| Activity | `ActivityTableSchema` | `domain/schemas/chembl/activity.py` |
| Assay | `AssayTableSchema` | `domain/schemas/chembl/assay.py` |
| Molecule | `MoleculeTableSchema` | `domain/schemas/chembl/molecule.py` |
| Target | `TargetTableSchema` | `domain/schemas/chembl/target.py` |
| Publication | `PublicationTableSchema` | `domain/schemas/chembl/publication.py` |

---

## Application Layer

**Расположение**: `src/bioetl/application/`

### Orchestration

Управление жизненным циклом пайплайна:

```python
class PipelineBase:
    async def run(self) -> RunResult:
        await self.prepare_run()      # Hooks, Lock acquisition
        await self.extract()          # Bronze write
        await self.transform()        # Normalization, Hash
        await self.validate()         # Pandera schemas
        await self.load()             # Silver/Gold write
        await self.finalize_run()     # Release lock, Metrics
```

### Компоненты

| Компонент | Расположение | Ответственность |
|-----------|--------------|-----------------|
| **Pipelines** | `application/pipelines/` | Конкретные пайплайны |
| **Services** | `application/services/` | Оркестрация domain/infra |
| **Observers** | `application/observers/` | Metrics, Circuit Breaker, Health |

### Circuit Breaker (§3.1.4)

```python
class CircuitBreaker:
    """Паттерн защиты от каскадных сбоев."""
    
    STATES = ["CLOSED", "OPEN", "HALF_OPEN"]
    
    # Trigger: 5 последовательных ошибок
    failure_threshold: int = 5
    
    # Open Duration: 5 минут (configurable)
    recovery_timeout: int = 300
    
    # Recovery: Half-Open → 1 пробный запрос
    # Success → Closed, Failure → Open +5 мин
```

### Provider Health Monitoring (§3.5)

| Status | Условие | Действие |
|--------|---------|----------|
| Healthy | 0 errors за 5 мин | Normal operation |
| Degraded | 1-2 consecutive errors | Timeout ×2, batch_size ÷2 |
| Unhealthy | ≥3 errors | Pause pipeline, Alert P2 |

---

## Infrastructure Layer

**Расположение**: `src/bioetl/infrastructure/`

### Adapters (Clients)

**Паттерн**: Трёхслойный

1. **Contracts**: Protocols в `domain/ports.py`
2. **Factories**: `infrastructure/clients/base/factories.py`
3. **Implementation**: Конкретные клиенты

| Провайдер | Библиотека | Rate Limit | Health Check |
|-----------|------------|------------|--------------|
| ChEMBL | `chembl_webresource_client` | Нет лимита | `/chembl/api/data/status.json` |
| PubChem | `pubchempy` | 5 req/sec | Generic Probe |
| UniProt | `unipressed` | 100 req/sec | `/rest/beta/health` |

**Legacy Wrappers (§4.1)**: Для библиотек без async:
```python
await loop.run_in_executor(thread_pool, fetch_func)
```

### Storage (§2.1, §5.3.1)

| Компонент | Расположение | Ответственность |
|-----------|--------------|-----------------|
| `DeltaLakeWriter` | `storage/delta_lake.py` | Silver/Gold write (delta-rs) |
| `BronzeWriter` | `storage/bronze_writer.py` | JSONL + zstd |
| `CheckpointManager` | `storage/checkpoint.py` | S3 + ETag atomicity |
| `S3Client` | `storage/s3_client.py` | boto3 wrapper |

### Locking (§3.3)

| Компонент | Расположение | Ответственность |
|-----------|--------------|-----------------|
| `RedisDistributedLock` | `locking/redis_lock.py` | SETNX + Heartbeat |
| `BackfillLock` | `locking/backfill_lock.py` | Exclusive lock (§2.4.1) |

**Invariants**:
- TTL: 60 секунд
- Heartbeat: каждые 20 секунд
- Max Duration: 4 часа
- Fencing Token: `owner_id` для split-brain prevention

**Safety Guard (§3.3)**: Валидация lock ownership перед Delta write:
```python
if not self._lock.validate_ownership():
    raise LockLostError("Aborting write to prevent split-brain")
```

### Security (§5.4)

| Компонент | Расположение | Ответственность |
|-----------|--------------|-----------------|
| `SaltManager` | `security/salt_manager.py` | Dual-Salt rotation (§5.4.1) |

### Quarantine (§2.6)

| Компонент | Расположение | Ответственность |
|-----------|--------------|-----------------|
| `QuarantineWriter` | `quarantine/writer.py` | Write to `common.quarantine` |
| `QuarantineOps` | `quarantine/ops.py` | inspect, replay, purge |

### Logging (§3.2)

| Компонент | Расположение | Ответственность |
|-----------|--------------|-----------------|
| `UnifiedLogger` | `logging/unified_logger.py` | Structured JSON (structlog) |

**Log Schema (§3.2.1)**:

| Поле | Обязательность | Пример |
|------|----------------|--------|
| `ts` | MUST | `2025-12-15T10:00:00Z` |
| `level` | MUST | `INFO`, `ERROR` |
| `run_id` | MUST | UUID |
| `pipeline` | MUST | `chembl_activity` |
| `stage` | MUST | `extract`, `transform`, `load` |
| `dataset` | SHOULD | `chembl.activity` |

---

## Interfaces Layer

**Расположение**: `src/bioetl/interfaces/`

### CLI

| Компонент | Расположение | Команды |
|-----------|--------------|---------|
| `main.py` | `cli/main.py` | Entry point (Typer) |
| `run.py` | `cli/commands/run.py` | Pipeline execution |
| `quarantine.py` | `cli/commands/quarantine.py` | inspect, replay, purge |
| `lock.py` | `cli/commands/lock.py` | release-lock |

---

## Cross-cutting Concerns

Сквозные аспекты инкапсулированы в infrastructure:

| Concern | Location | Dependency |
|---------|----------|------------|
| Logging | `infrastructure/logging/` | `LoggingPort` |
| Metrics | `application/observers/metrics.py` | Prometheus |
| Configuration | `infrastructure/config/` | YAML → Pydantic |
| Tracing | `application/observers/` | `run_id` correlation |

**Принцип**: Domain зависит только от Ports, не знает:
- Где хранятся настройки (YAML, ENV, CLI)
- Какие реализации логгера/метрик используются
- Какие HTTP-библиотеки применяются

---

## Layer Boundaries

### Infrastructure → Application

Adapters возвращают generic types:
- HTTP responses → `dict[str, Any]`
- Parsed records → `list[dict[str, Any]]`

Application конвертирует в domain types через mappers.

### Application → Domain

Application сервисы оркестрируют domain логику:
- `SchemaBootstrapService` регистрирует схемы
- `RecordMapperABC` валидирует и конвертирует записи

### Domain

Чистая бизнес-логика без внешних зависимостей:
- Pandera schemas
- Validation rules
- Business models

---

## Error Handling (§3.1)

### Классификация Ошибок

| Тип | Поведение | Пример |
|-----|-----------|--------|
| **Critical** | Pipeline Fail | Auth error, Schema mismatch (Gold) |
| **Recoverable** | Retry N раз | 429, 502/504, Network error |
| **Data Quality** | Log + Skip | Invalid SMILES, Missing optional field |

### Retry Strategy (§3.1.3)

```python
max_attempts = 3
multiplier = 2.0  # 1s, 2s, 4s
jitter = random.uniform(0.1, 0.5)  # Thundering herd prevention
```

### DQ Thresholds (§3.1.2)

| Threshold | Value | Action |
|-----------|-------|--------|
| Soft | >5% errors | Warning |
| Hard | >20% errors | Fail Batch |

---

## Связи с другими документами

- **Domain Objects**: [01-domain-objects.md](01-domain-objects.md)
- **Data Flow**: [03-data-flow.md](03-data-flow.md)
- **Physical Layout**: [05-physical-layout.md](05-physical-layout.md)
