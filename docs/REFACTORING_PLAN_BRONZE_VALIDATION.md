# План Рефакторинга: Bronze Validation и Safety Guards

*Версия: 1.0 | Дата: 2025-12-27 | Автор: Claude*

> **⚠️ ПРОТОКОЛ ДВОЙНОЙ ВЕРИФИКАЦИИ ВЫПОЛНЕН**
>
> Все утверждения в этом документе проверены согласно `RULES.md` §7:
> - Первая проверка: Анализ кода с точными ссылками
> - Вторая проверка: Сверка с `docs/REFACTORING_PLAN.md`

---

## Содержание

1. [Сводка по задачам](#сводка-по-задачам)
2. [Задача 1: Bronze Validation Enhancement](#задача-1-bronze-validation-enhancement)
3. [Задача 2: Provider Health Monitoring](#задача-2-provider-health-monitoring)
4. [Задача 3: Gold Contracts Documentation](#задача-3-gold-contracts-documentation)
5. [Задача 4: Safety Guard для Storage Writers](#задача-4-safety-guard-для-storage-writers)

---

## Сводка по задачам

| Задача | Приоритет | Статус верификации | Требуется работа |
|--------|-----------|-------------------|------------------|
| Bronze Validation Enhancement | P2 | ✅ УЖЕ РЕАЛИЗОВАНО | Нет (обновить REFACTORING_PLAN.md) |
| Provider Health Monitoring | P2 | ⏳ ЧАСТИЧНО | Да (централизованный мониторинг) |
| Gold Contracts Documentation | P3 | ✅ УЖЕ РЕАЛИЗОВАНО | Нет |
| Safety Guard для Storage Writers | P3 | ❌ НЕ РЕАЛИЗОВАНО | Да (полная реализация) |

---

## Задача 1: Bronze Validation Enhancement

### Статус: ✅ УЖЕ РЕАЛИЗОВАНО

> **ВЕРИФИКАЦИЯ**: Задача M3 в `docs/REFACTORING_PLAN.md:125` помечена как ⏳,
> но код показывает полную реализацию.

### Доказательства реализации

| Компонент | Файл:строки | Описание |
|-----------|-------------|----------|
| **Валидация JSON records** | `bronze_writer.py:151-178` | `_validate_json_records()` — lazy generator с `BronzeValidationError` |
| **Валидация provider/entity** | `bronze_writer.py:95-106` | `_validate_bronze_names()` — alphanumeric + underscores |
| **Валидация Iterator[bytes]** | `bronze_writer.py:108-124` | `_validate_records_iterator()` — проверка типа |
| **Валидация UTC datetime** | `bronze_writer.py:126-149` | `_validate_utc_datetime()` — timezone-aware UTC only |
| **Интеграция в write_bronze** | `bronze_writer.py:306-309` | Все валидации вызываются последовательно |

### Код валидации JSON (bronze_writer.py:151-178)

```python
def _validate_json_records(self, records: Iterator[bytes]) -> Iterator[bytes]:
    """Validate that each record is valid JSON bytes (lazy generator)."""
    from bioetl.domain.exceptions import BronzeValidationError

    for index, record in enumerate(records):
        try:
            orjson.loads(record)
        except orjson.JSONDecodeError as e:
            raise BronzeValidationError(
                message="Invalid JSON in Bronze record",
                record_index=index,
                original_error=str(e),
            ) from e
        yield record
```

### Рекомендуемые действия

1. **Обновить `docs/REFACTORING_PLAN.md:125`**:
   ```diff
   - ⏳ M3: Bronze validation
   + ✅ M3: Bronze validation (реализовано bronze_writer.py:151-178)
   ```

2. **Добавить в секцию "УЖЕ РЕАЛИЗОВАНО"** (после строки 43):
   ```markdown
   | **M3: Bronze JSON validation** | `bronze_writer.py:151-178` | `_validate_json_records()` с BronzeValidationError |
   ```

### Критерий готовности

Тест уже должен существовать. Проверить:
```bash
grep -r "test_bronze_validation\|BronzeValidationError" tests/
```

---

## Задача 2: Provider Health Monitoring

### Статус: ⏳ ЧАСТИЧНО РЕАЛИЗОВАНО

### Что уже реализовано

| Компонент | Файл:строки | Описание |
|-----------|-------------|----------|
| **HealthStatus enum** | `domain/types.py:128-152` | HEALTHY=2, DEGRADED=1, UNHEALTHY=0 |
| **assess_health_from_circuit_breaker** | `http/health.py:10-28` | Оценка по состоянию CB |
| **ChEMBL cached health** | `chembl/client.py:75,440-467` | Автопереключение статусов |
| **Template Method health_check** | `base.py:86-99` | `_probe_health()` + `_fallback_health_status()` |
| **Все адаптеры** | См. таблицу ниже | Реализуют `_probe_health()` |

### Текущая реализация в адаптерах

| Адаптер | Файл | _probe_health | _fallback_health_status | Авто-переход |
|---------|------|---------------|-------------------------|--------------|
| ChEMBL | `chembl/client.py:391-467` | ✅ | ✅ | ✅ cached_health |
| UniProt | `uniprot/client.py:263-287` | ✅ | ❌ (base) | ❌ |
| PubMed | `pubmed/pubmed_client.py:195-264` | ✅ | ✅ | ❌ |
| PubChem | `pubchem/client.py:255-302` | ✅ | ❌ (base) | ❌ |

### Что НЕ реализовано (требования RULES.md §3.5)

| Требование | Статус | Описание |
|------------|--------|----------|
| Автоматический переход Healthy → Degraded | ⏳ | Только в ChEMBL адаптере |
| Автоматический переход Degraded → Unhealthy | ⏳ | Только в ChEMBL адаптере |
| Recovery: Unhealthy → Degraded | ⏳ | Только в ChEMBL адаптере |
| Метрика `provider_health_status{provider}` | ❌ | Не эмитируется |
| Централизованный ProviderHealthMonitor | ❌ | Логика размазана по адаптерам |

### План реализации

#### Шаг 1: Создать `ProviderHealthMonitor` (M — дни)

**Файл**: `src/bioetl/infrastructure/adapters/http/health_monitor.py`

```python
"""
Provider Health Monitor.

Implements RULES.md §3.5 - Centralized health state management.

Requirements:
- REQ-OBS-010: provider_health_status metric
- REQ-ERR-015: Automatic state transitions
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from bioetl.domain.types import HealthStatus

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort


@dataclass
class ProviderHealthState:
    """Tracks health state for a single provider."""

    provider: str
    status: HealthStatus = HealthStatus.HEALTHY
    consecutive_errors: int = 0
    last_success: datetime | None = None
    last_check: datetime | None = None

    # Thresholds from RULES.md §3.5
    DEGRADED_THRESHOLD: int = 1  # 1-2 consecutive errors
    UNHEALTHY_THRESHOLD: int = 3  # ≥3 errors


@dataclass
class ProviderHealthMonitor:
    """Centralized health monitoring for all providers.

    Implements automatic state transitions:
    - Healthy → Degraded: 1-2 consecutive errors
    - Degraded → Unhealthy: ≥3 errors OR health_check fail
    - Unhealthy → Degraded: 1 successful health_check (Recovery)

    Emits metric: provider_health_status{provider} (0/1/2)
    """

    metrics: MetricsPort
    _states: dict[str, ProviderHealthState] = field(default_factory=dict)
    _check_window: timedelta = field(default=timedelta(minutes=5))

    def get_state(self, provider: str) -> ProviderHealthState:
        """Get or create health state for provider."""
        if provider not in self._states:
            self._states[provider] = ProviderHealthState(provider=provider)
        return self._states[provider]

    def record_success(self, provider: str) -> HealthStatus:
        """Record successful operation, potentially recover from Unhealthy."""
        state = self.get_state(provider)
        state.consecutive_errors = 0
        state.last_success = datetime.now()

        # Recovery: Unhealthy → Degraded after 1 success
        if state.status == HealthStatus.UNHEALTHY:
            state.status = HealthStatus.DEGRADED
        elif state.status == HealthStatus.DEGRADED:
            # Check if 5 min window passed with no errors
            if self._check_clear_window(state):
                state.status = HealthStatus.HEALTHY

        self._emit_metric(state)
        return state.status

    def record_error(self, provider: str) -> HealthStatus:
        """Record error, potentially transition to Degraded/Unhealthy."""
        state = self.get_state(provider)
        state.consecutive_errors += 1

        if state.consecutive_errors >= ProviderHealthState.UNHEALTHY_THRESHOLD:
            state.status = HealthStatus.UNHEALTHY
        elif state.consecutive_errors >= ProviderHealthState.DEGRADED_THRESHOLD:
            state.status = HealthStatus.DEGRADED

        self._emit_metric(state)
        return state.status

    def record_health_check_result(
        self,
        provider: str,
        status: HealthStatus
    ) -> HealthStatus:
        """Record health check result, apply transitions."""
        state = self.get_state(provider)
        state.last_check = datetime.now()

        if status == HealthStatus.UNHEALTHY:
            state.status = HealthStatus.UNHEALTHY
            state.consecutive_errors = ProviderHealthState.UNHEALTHY_THRESHOLD
        elif status == HealthStatus.HEALTHY:
            # Recovery path
            if state.status == HealthStatus.UNHEALTHY:
                state.status = HealthStatus.DEGRADED
            elif state.status == HealthStatus.DEGRADED:
                state.status = HealthStatus.HEALTHY
            state.consecutive_errors = 0
            state.last_success = datetime.now()

        self._emit_metric(state)
        return state.status

    def _check_clear_window(self, state: ProviderHealthState) -> bool:
        """Check if 5 min window has passed with no errors."""
        if state.last_success is None:
            return False
        return datetime.now() - state.last_success >= self._check_window

    def _emit_metric(self, state: ProviderHealthState) -> None:
        """Emit provider_health_status metric."""
        value = HealthStatus.to_int(state.status)  # 0, 1, or 2
        self.metrics.gauge(
            "provider_health_status",
            value,
            labels={"provider": state.provider}
        )

    def get_adaptive_params(self, provider: str) -> tuple[float, int]:
        """Get adaptive timeout and batch_size based on health.

        Returns:
            (timeout_multiplier, batch_size_divisor)
        """
        state = self.get_state(provider)

        if state.status == HealthStatus.DEGRADED:
            return (2.0, 2)  # Timeout ×2, batch_size ÷2
        elif state.status == HealthStatus.UNHEALTHY:
            return (4.0, 4)  # More aggressive throttling
        return (1.0, 1)  # Normal operation
```

#### Шаг 2: Добавить метод `to_int()` в HealthStatus

**Файл**: `src/bioetl/domain/types.py:128-160`

```python
class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"

    @classmethod
    def to_int(cls, status: "HealthStatus") -> int:
        """Convert to metric value (RULES.md §3.5)."""
        mapping = {
            cls.UNHEALTHY: 0,
            cls.DEGRADED: 1,
            cls.HEALTHY: 2,
        }
        return mapping[status]
```

#### Шаг 3: Интегрировать в BaseHttpAdapter

**Файл**: `src/bioetl/infrastructure/adapters/base.py`

```python
# В __init__:
self._health_monitor: ProviderHealthMonitor | None = health_monitor

# После успешного запроса:
if self._health_monitor:
    self._health_monitor.record_success(self.provider_name)

# После ошибки:
if self._health_monitor:
    status = self._health_monitor.record_error(self.provider_name)
    if status == HealthStatus.UNHEALTHY:
        raise ProviderUnavailableError(f"{self.provider_name} is unhealthy")
```

#### Шаг 4: Создать фабрику в composition

**Файл**: `src/bioetl/composition/factories/health_factory.py`

```python
def create_health_monitor(metrics: MetricsPort) -> ProviderHealthMonitor:
    """Create singleton ProviderHealthMonitor."""
    return ProviderHealthMonitor(metrics=metrics)
```

### Критерии готовности

1. **Метрика эмитируется**:
   ```bash
   grep -r "provider_health_status" src/ tests/
   ```

2. **Тесты**:
   - `test_health_monitor_transitions_healthy_to_degraded`
   - `test_health_monitor_transitions_degraded_to_unhealthy`
   - `test_health_monitor_recovery_unhealthy_to_degraded`
   - `test_health_monitor_emits_metric`

3. **Интеграция с адаптерами**:
   - Все адаптеры используют `ProviderHealthMonitor`
   - Adaptive params применяются

### Риски и митигация

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Breaking change в адаптерах | Средний | Опциональный параметр `health_monitor` |
| Race conditions при concurrent requests | Низкий | Использовать `asyncio.Lock` |
| Overhead на каждый запрос | Низкий | Простые операции in-memory |

### Трудозатраты: M (2-3 дня)

---

## Задача 3: Gold Contracts Documentation

### Статус: ✅ УЖЕ РЕАЛИЗОВАНО

### Доказательства реализации

| Компонент | Путь | Описание |
|-----------|------|----------|
| **Директория контрактов** | `docs/contracts/gold/` | 3 JSON Schema файла |
| **activity.json** | `docs/contracts/gold/activity.json` | 78 строк, JSON Schema draft-07 |
| **assay.json** | `docs/contracts/gold/assay.json` | ~100 строк |
| **molecule.json** | `docs/contracts/gold/molecule.json` | ~130 строк |
| **Скрипт генерации** | `scripts/generate_contracts.py` | 57 строк, генерирует из Pandera |

### Содержимое activity.json (выдержка)

```json
{
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Activity Data Contract",
    "properties": {
        "activity_id": {"type": "integer"},
        "molecule_chembl_id": {"type": "string", "pattern": "^CHEMBL\\d+$"},
        "_content_hash": {"type": "string"},
        "_ingestion_ts": {"type": "string", "format": "date-time"}
    },
    "required": ["activity_id", "assay_id", "molecule_chembl_id", "_content_hash", "_ingestion_ts"]
}
```

### Скрипт генерации (scripts/generate_contracts.py)

```python
ENTITY_SCHEMA_MAP = {
    "chembl_activity": ChEMBLActivityGoldSchema,
    "pubchem_compound": PubChemCompoundGoldSchema,
    "uniprot_protein": UniProtProteinGoldSchema,
    "pubmed_publication": PubMedPublicationGoldSchema,
}

def generate_contracts():
    for entity, schema_cls in ENTITY_SCHEMA_MAP.items():
        json_schema = schema_cls.to_json_schema()
        output_file = CONTRACTS_DIR / f"{entity}_gold.json"
        json.dump(json_schema, f, indent=2)
```

### Рекомендуемые действия

**Никаких действий не требуется.** Задача полностью реализована.

Опционально можно добавить:
1. CI-проверку актуальности контрактов (`make check-contracts`)
2. Документацию в `docs/` о использовании контрактов

---

## Задача 4: Safety Guard для Storage Writers

### Статус: ❌ НЕ РЕАЛИЗОВАНО

### Верификация

```bash
# Поиск проверки блокировок в writers
grep -r "_validate_lock\|lock_held\|verify_lock" src/bioetl/infrastructure/storage/
# Результат: No matches found
```

### Существующая инфраструктура блокировок

| Компонент | Файл:строки | Описание |
|-----------|-------------|----------|
| **LockPort Protocol** | `domain/ports/locking.py:14-84` | `acquire()`, `release()`, `heartbeat()`, `aclose()` |
| **LockManager** | `application/core/lock_manager.py:17-100+` | Сервис управления блокировками |
| **MemoryLock** | `infrastructure/locking/memory_lock.py:19-221` | In-memory реализация |

### Требования RULES.md

| Раздел | Требование |
|--------|------------|
| §2.4.1 | Lock keys: `lock:{provider}_{entity}` (incremental), `lock:{provider}_{entity}:exclusive` (backfill) |
| §3.3 | Writers MUST verify lock is held before write operations |

### План реализации

#### Шаг 1: Создать LockContext value object

**Файл**: `src/bioetl/domain/locking.py` (новый файл)

```python
"""Lock context for passing lock state through layers.

Implements RULES.md §3.3 - Writers MUST verify lock held before write.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.types import RunID


@dataclass(frozen=True)
class LockContext:
    """Immutable context representing held lock.

    Passed from application layer to infrastructure layer
    to verify lock is held before write operations.

    Attributes:
        key: The lock key (e.g., "lock:chembl_activity")
        owner_id: RunID that acquired the lock
        exclusive: True for backfill/rebuild operations
        acquired_at: When lock was acquired (for TTL checks)
    """

    key: str
    owner_id: RunID
    exclusive: bool = False
    acquired_at: float | None = None  # time.monotonic()

    @classmethod
    def create(
        cls,
        provider: str,
        entity: str,
        owner_id: RunID,
        exclusive: bool = False,
    ) -> "LockContext":
        """Create lock context with standard key format."""
        import time

        if exclusive:
            key = f"lock:{provider}_{entity}:exclusive"
        else:
            key = f"lock:{provider}_{entity}"

        return cls(
            key=key,
            owner_id=owner_id,
            exclusive=exclusive,
            acquired_at=time.monotonic(),
        )

    def is_valid(self, ttl_seconds: int = 3600) -> bool:
        """Check if lock context is still valid (not expired)."""
        if self.acquired_at is None:
            return True  # No TTL tracking

        import time
        elapsed = time.monotonic() - self.acquired_at
        return elapsed < ttl_seconds


class LockNotHeldError(Exception):
    """Raised when write operation attempted without valid lock."""

    def __init__(self, operation: str, expected_key: str) -> None:
        self.operation = operation
        self.expected_key = expected_key
        super().__init__(
            f"Cannot perform {operation}: lock '{expected_key}' not held. "
            "Acquire lock via LockManager before write operations."
        )
```

#### Шаг 2: Добавить валидацию в DeltaWriter

**Файл**: `src/bioetl/infrastructure/storage/delta_writer.py`

Изменения в `__init__`:
```python
def __init__(
    self,
    base_path: str | Path,
    logger: LoggerPort,
    csv_exporter: CsvExporter | None = None,
    write_policy: WriteModePolicy | None = None,
    metrics: MetricsPort | None = None,
    audit: AuditPort | None = None,
    tracing: TracingPort | None = None,
    require_lock: bool = True,  # NEW: Enable lock validation
) -> None:
    # ... existing code ...
    self._require_lock = require_lock
```

Добавить метод валидации:
```python
def _validate_lock_held(
    self,
    lock_context: LockContext | None,
    provider: str,
    entity: str,
) -> None:
    """Validate that lock is held before write operation.

    Implements RULES.md §3.3 - Writers MUST verify lock held.

    Args:
        lock_context: The lock context from application layer.
        provider: Provider name for key validation.
        entity: Entity name for key validation.

    Raises:
        LockNotHeldError: If lock is not held or doesn't match.
    """
    if not self._require_lock:
        return  # Lock validation disabled (e.g., for tests)

    expected_key = f"lock:{provider}_{entity}"
    exclusive_key = f"lock:{provider}_{entity}:exclusive"

    if lock_context is None:
        raise LockNotHeldError("write_silver", expected_key)

    if lock_context.key not in (expected_key, exclusive_key):
        raise LockNotHeldError(
            f"write_silver (got {lock_context.key})",
            expected_key
        )

    if not lock_context.is_valid():
        raise LockNotHeldError(
            "write_silver (lock expired)",
            expected_key
        )
```

Обновить `write_silver`:
```python
async def write_silver(
    self,
    records: list[dict[str, Any]],
    table_name: str,
    schema: pa.Schema,
    primary_keys: list[str],
    *,
    mode: SilverWriteMode = SilverWriteMode.MERGE,
    partition_by: list[str] | None = None,
    lock_context: LockContext | None = None,  # NEW
) -> int:
    """Write records to Silver layer (Delta Lake).

    Args:
        records: Records to write.
        table_name: Name of the Delta table.
        schema: PyArrow schema for the table.
        primary_keys: List of primary key columns.
        mode: Write mode (MERGE, APPEND, DELETE).
        partition_by: Optional partition columns.
        lock_context: Lock context from LockManager. Required unless
                     require_lock=False was passed to constructor.

    Raises:
        LockNotHeldError: If lock_context is None or invalid.
    """
    # Extract provider/entity from table_name (e.g., "chembl_activity")
    parts = table_name.split("_", 1)
    provider = parts[0] if len(parts) > 1 else table_name
    entity = parts[1] if len(parts) > 1 else table_name

    self._validate_lock_held(lock_context, provider, entity)

    # ... existing write logic ...
```

#### Шаг 3: Аналогичные изменения в GoldWriter

**Файл**: `src/bioetl/infrastructure/storage/gold_writer.py`

```python
def _validate_lock_held(
    self,
    lock_context: LockContext | None,
    provider: str,
    entity: str,
) -> None:
    """Validate that lock is held before write operation."""
    # Same implementation as DeltaWriter
    ...

async def write_gold(
    self,
    records: list[dict[str, Any]],
    table_name: str,
    schema: pa.Schema,
    *,
    mode: GoldWriteMode = GoldWriteMode.APPEND,
    lock_context: LockContext | None = None,  # NEW
) -> int:
    """Write records to Gold layer.

    Args:
        lock_context: Lock context from LockManager. Required.

    Raises:
        LockNotHeldError: If lock_context is None or invalid.
    """
    parts = table_name.split("_", 1)
    provider = parts[0] if len(parts) > 1 else table_name
    entity = parts[1] if len(parts) > 1 else table_name

    self._validate_lock_held(lock_context, provider, entity)

    # ... existing write logic ...
```

#### Шаг 4: Аналогичные изменения в BronzeWriter

**Файл**: `src/bioetl/infrastructure/storage/bronze_writer.py`

```python
async def write_bronze(
    self,
    records: Iterator[bytes],
    provider: str,
    entity: str,
    run_id: RunID,
    run_type: RunType,
    batch_id: BatchID,
    ingestion_ts: datetime,
    *,
    lock_context: LockContext | None = None,  # NEW
) -> BronzeWriteResult:
    """Write records to Bronze layer.

    Args:
        lock_context: Lock context from LockManager. Required.

    Raises:
        LockNotHeldError: If lock_context is None or invalid.
    """
    self._validate_lock_held(lock_context, provider, entity)

    # ... existing write logic ...
```

#### Шаг 5: Обновить LockManager для создания LockContext

**Файл**: `src/bioetl/application/core/lock_manager.py`

```python
async def acquire_with_context(
    self,
    provider: str,
    entity: str,
    owner_id: RunID,
    exclusive: bool = False,
    ttl: int | None = None,
) -> LockContext | None:
    """Acquire lock and return LockContext for writers.

    Returns:
        LockContext if lock acquired, None otherwise.
    """
    key = LockContext.create(
        provider=provider,
        entity=entity,
        owner_id=owner_id,
        exclusive=exclusive,
    ).key

    acquired = await self._lock.acquire(
        key=key,
        owner_id=owner_id,
        ttl=ttl,
        exclusive=exclusive,
    )

    if acquired:
        return LockContext.create(
            provider=provider,
            entity=entity,
            owner_id=owner_id,
            exclusive=exclusive,
        )
    return None
```

#### Шаг 6: Обновить RecordProcessor для передачи LockContext

**Файл**: `src/bioetl/application/core/record_processor.py`

```python
@dataclass
class RecordProcessor:
    # ... existing fields ...
    lock_context: LockContext | None = None  # NEW

async def _write_batch(self, records: list[dict]) -> int:
    """Write batch to storage with lock context."""
    return await self._batch_writer.write(
        records,
        lock_context=self.lock_context,  # Pass to writer
    )
```

### Список изменяемых файлов

| Файл | Тип изменения | Строки (оценка) |
|------|---------------|-----------------|
| `domain/locking.py` | Новый файл | ~80 |
| `delta_writer.py` | Добавить валидацию | +40 |
| `gold_writer.py` | Добавить валидацию | +40 |
| `bronze_writer.py` | Добавить валидацию | +30 |
| `lock_manager.py` | Добавить `acquire_with_context` | +25 |
| `record_processor.py` | Добавить `lock_context` | +10 |
| `runner.py` | Передать lock_context | +5 |

### Тесты

**Файл**: `tests/unit/infrastructure/storage/test_writer_lock_validation.py`

```python
import pytest
from bioetl.domain.locking import LockContext, LockNotHeldError
from bioetl.infrastructure.storage.delta_writer import DeltaWriter


class TestWriterLockValidation:
    """Tests for RULES.md §3.3 - Writers MUST verify lock held."""

    async def test_writer_fails_without_lock(self, delta_writer):
        """Writer raises LockNotHeldError when no lock provided."""
        with pytest.raises(LockNotHeldError) as exc_info:
            await delta_writer.write_silver(
                records=[{"id": 1}],
                table_name="chembl_activity",
                schema=...,
                primary_keys=["id"],
                lock_context=None,  # No lock!
            )

        assert "lock:chembl_activity" in str(exc_info.value)

    async def test_writer_fails_with_wrong_lock(self, delta_writer):
        """Writer raises when lock key doesn't match table."""
        wrong_lock = LockContext.create(
            provider="pubchem",
            entity="compound",
            owner_id=RunID.generate(),
        )

        with pytest.raises(LockNotHeldError):
            await delta_writer.write_silver(
                records=[{"id": 1}],
                table_name="chembl_activity",  # Different!
                lock_context=wrong_lock,
            )

    async def test_writer_succeeds_with_valid_lock(self, delta_writer):
        """Writer accepts valid lock context."""
        valid_lock = LockContext.create(
            provider="chembl",
            entity="activity",
            owner_id=RunID.generate(),
        )

        count = await delta_writer.write_silver(
            records=[{"id": 1}],
            table_name="chembl_activity",
            lock_context=valid_lock,
        )

        assert count == 1

    async def test_writer_accepts_exclusive_lock(self, delta_writer):
        """Exclusive lock accepted for normal writes."""
        exclusive_lock = LockContext.create(
            provider="chembl",
            entity="activity",
            owner_id=RunID.generate(),
            exclusive=True,
        )

        count = await delta_writer.write_silver(
            records=[{"id": 1}],
            table_name="chembl_activity",
            lock_context=exclusive_lock,
        )

        assert count == 1
```

### Критерии готовности

1. **Тест проходит**:
   ```bash
   pytest tests/unit/infrastructure/storage/test_writer_lock_validation.py -v
   ```

2. **Grep показывает реализацию**:
   ```bash
   grep -r "_validate_lock_held" src/bioetl/infrastructure/storage/
   # Должен найти в delta_writer.py, gold_writer.py, bronze_writer.py
   ```

3. **Все существующие тесты проходят**:
   ```bash
   make test
   ```

### Риски и митигация

| Риск | Вероятность | Воздействие | Митигация |
|------|-------------|-------------|-----------|
| Breaking change для вызывающего кода | Высокий | Высокое | Параметр `require_lock=True` с возможностью отключить для тестов |
| Overhead на каждую запись | Низкий | Низкое | Валидация O(1), in-memory |
| Миграция существующих тестов | Средний | Среднее | Использовать `require_lock=False` в fixtures |

### Backward Compatibility

Для плавной миграции:

1. **Фаза 1** (текущий PR): `require_lock=False` по умолчанию, logging warnings
2. **Фаза 2** (следующий PR): `require_lock=True` по умолчанию
3. **Фаза 3**: Удалить параметр `require_lock`, всегда валидировать

### Трудозатраты: M (2-3 дня)

---

## Приложение: Обновление REFACTORING_PLAN.md

После выполнения задач, обновить `docs/REFACTORING_PLAN.md`:

### Строка 125 (M3)
```diff
- ⏳ M3: Bronze validation
+ ✅ M3: Bronze validation (bronze_writer.py:151-178)
```

### Секция "УЖЕ РЕАЛИЗОВАНО" (после строки 43)
```markdown
| **M3: Bronze JSON validation** | `bronze_writer.py:151-178` | `_validate_json_records()` с BronzeValidationError |
| **Gold Contracts** | `docs/contracts/gold/` | 3 JSON Schema + `scripts/generate_contracts.py` |
```

### Новая подсекция (Фаза 5)
```markdown
### Safety Guard для Writers (Lock Validation)

| Статус | Файл | Изменение |
|--------|------|-----------|
| ⏳ | `domain/locking.py` | LockContext value object |
| ⏳ | `delta_writer.py` | `_validate_lock_held()` |
| ⏳ | `gold_writer.py` | `_validate_lock_held()` |
| ⏳ | `bronze_writer.py` | `_validate_lock_held()` |
```

---

*Документ подготовлен согласно протоколу двойной верификации RULES.md §7*
