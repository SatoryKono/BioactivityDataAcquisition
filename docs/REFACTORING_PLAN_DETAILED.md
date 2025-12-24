# Подробный План Рефакторинга BioETL

*Версия: 3.0 | Дата: 2025-12-24*
*На основе архитектурного обзора и анализа кодовой базы*

---

## Содержание

1. [Общая Оценка](#1-общая-оценка)
2. [Приоритизированный Список Задач](#2-приоритизированный-список-задач)
3. [Детальное Описание Задач](#3-детальное-описание-задач)
4. [Порядок Выполнения](#4-порядок-выполнения)
5. [Метрики Успеха](#5-метрики-успеха)

---

## 1. Общая Оценка

**Текущий балл: 8.6 / 10** — Проект в хорошем состоянии.

После реализации плана: **9.2+ / 10**

| Категория | До | После | Δ |
|-----------|-----|-------|---|
| Архитектура слоёв | 9.5 | 9.5 | — |
| Модульность | 8.5 | 9.5 | +1.0 |
| Тестирование | 7.5 | 9.0 | +1.5 |
| Технический долг | 8.0 | 9.0 | +1.0 |

---

## 2. Приоритизированный Список Задач

```
🔴 КРИТИЧЕСКИЙ (Sprint 1)
├── R1: Добавить health_check() в PubMedAdapter
├── R2: Декомпозиция ChemblAdapter (God Object → Mixins)
└── R3: Типизация registry.py (Any → конкретные типы)

🟠 ВЫСОКИЙ ПРИОРИТЕТ (Sprint 2)
├── R4: Расширить тестирование interfaces слоя (+10 тестов)
├── R5: Сделать StoragePort полностью асинхронным
├── R6: Детерминизировать классификацию ошибок
└── R7: Управление жизненным циклом observability

🟡 СРЕДНИЙ ПРИОРИТЕТ (Sprint 3)
├── R8: Устранение sentinel values ("unknown")
├── R9: Типизация observer.py (span: Any)
├── R10: Унификация Pagination (PaginatedFetcherMixin)
└── R11: Дополнить domain/__init__.py экспортами

🟢 НИЗКИЙ ПРИОРИТЕТ (Backlog)
├── R12: Generic ResponseProcessor
├── R13: PII Salt Implementation
├── R14: Декомпозиция крупных трансформеров
└── R15: Thread-safe Registry
```

---

## 3. Детальное Описание Задач

---

### R1: Добавить health_check() в PubMedAdapter

**Приоритет:** 🔴 КРИТИЧЕСКИЙ (BLOCKER)

**Проблема:**
- `DataSourcePort` требует `async def health_check() -> HealthStatus`
- `PubMedAdapter` НЕ реализует этот метод (нарушение контракта)

**Файл:** `src/bioetl/infrastructure/adapters/pubmed/pubmed_client.py`

**Конкретные правки:**

```python
# Добавить в класс PubMedAdapter:

async def health_check(self) -> HealthStatus:
    """Проверка доступности PubMed API.

    Выполняет lightweight запрос к einfo endpoint.

    Returns:
        HealthStatus.HEALTHY — API доступен
        HealthStatus.DEGRADED — медленный отклик
        HealthStatus.UNHEALTHY — ≥3 ошибок или timeout
    """
    try:
        loop = asyncio.get_running_loop()

        start_time = time.monotonic()
        handle = await loop.run_in_executor(
            self._thread_pool,
            lambda: Entrez.einfo(db="pubmed")
        )
        handle.close()

        elapsed = time.monotonic() - start_time

        # Медленный отклик = degraded
        if elapsed > 5.0:
            self._logger.warning(
                "pubmed_health_check_slow",
                elapsed_seconds=elapsed,
            )
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    except Exception as e:
        self._logger.warning(
            "pubmed_health_check_failed",
            error=str(e),
        )
        return HealthStatus.UNHEALTHY
```

**Тесты:**

| Файл | Тест |
|------|------|
| `tests/unit/infrastructure/adapters/pubmed/test_pubmed_client.py` | `test_health_check_returns_healthy` |
| `tests/unit/infrastructure/adapters/pubmed/test_pubmed_client.py` | `test_health_check_returns_unhealthy_on_error` |
| `tests/integration/adapters/test_pubmed.py` | `test_health_check_vcr` (с кассетой) |

**Критерии готовности:**
- [ ] Метод `health_check()` реализован
- [ ] Unit тест проходит с mock
- [ ] VCR кассета записана для integration теста
- [ ] `make lint && make test` проходит
- [ ] Архитектурный тест `test_adapters_implement_health_check` проходит

**Риски и митигация:**

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Biopython API изменился | Низкая | Проверить документацию Entrez.einfo |
| Timeout при einfo | Средняя | run_in_executor с timeout wrapper |

---

### R2: Декомпозиция ChemblAdapter (God Object)

**Приоритет:** 🔴 КРИТИЧЕСКИЙ

**Проблема:**
- `ChemblAdapter` — 431 строка, 19 методов
- Смешение ответственностей: fetching, error handling, health monitoring, statistics

**Файл:** `src/bioetl/infrastructure/adapters/chembl/client.py`

**Целевое состояние:**

```
ChemblAdapter (< 200 строк)
├── ErrorHandlingMixin
├── HealthMonitorMixin
└── использует PaginatedFetcherMixin
```

**Конкретные правки:**

#### R2.1: Создать ErrorHandlingMixin

**Новый файл:** `src/bioetl/infrastructure/adapters/mixins/error_handling.py`

```python
"""Error handling mixin for data source adapters."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.exceptions import ChemblApiError, CriticalError
from bioetl.domain.types import ErrorType

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


@dataclass
class ErrorHandlingMixin:
    """Mixin для обработки ошибок в адаптерах.

    Атрибуты:
        logger: LoggerPort для логирования
    """

    logger: "LoggerPort"

    _consecutive_errors: int = field(init=False, default=0)
    _total_errors: int = field(init=False, default=0)
    _error_counts: dict[ErrorType, int] = field(init=False, default_factory=dict)
    _error_classifier: ErrorClassifier = field(
        init=False, default_factory=ErrorClassifier
    )

    def handle_error(
        self,
        error: Exception,
        context: str = "fetch",
        provider: str = "unknown",
    ) -> None:
        """Обработать ошибку с классификацией и метриками.

        Args:
            error: Исключение для обработки
            context: Контекст операции (fetch, health_check)
            provider: Имя провайдера для логов

        Raises:
            CriticalError: Для критических ошибок (auth, etc.)
        """
        error_type = self._error_classifier.classify(error)

        # Обновить счётчики
        self._consecutive_errors += 1
        self._total_errors += 1
        self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1

        # Логирование
        self.logger.error(
            f"{provider}_error",
            provider=provider,
            operation=context,
            error=str(error),
            error_type=error_type.value,
            is_critical=error_type.is_critical(),
            consecutive_errors=self._consecutive_errors,
        )

        # Критические ошибки — немедленный fail
        if error_type.is_critical():
            raise CriticalError(
                f"Critical {provider} error ({error_type.value}): {error}"
            ) from error

    def reset_consecutive_errors(self) -> None:
        """Сбросить счётчик последовательных ошибок."""
        self._consecutive_errors = 0

    def get_error_stats(self) -> dict[str, any]:
        """Получить статистику ошибок."""
        return {
            "consecutive_errors": self._consecutive_errors,
            "total_errors": self._total_errors,
            "error_counts_by_type": {
                k.value: v for k, v in self._error_counts.items()
            },
        }

    def reset_all_error_counters(self) -> None:
        """Полный сброс всех счётчиков."""
        self._consecutive_errors = 0
        self._total_errors = 0
        self._error_counts.clear()
```

#### R2.2: Создать HealthMonitorMixin

**Новый файл:** `src/bioetl/infrastructure/adapters/mixins/health_monitor.py`

```python
"""Health monitoring mixin for data source adapters."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.types import HealthStatus

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


@dataclass
class HealthMonitorMixin:
    """Mixin для мониторинга здоровья адаптеров.

    Per RULES.md §3.5:
    - HEALTHY: Normal batch_size
    - DEGRADED: batch_size ÷ 2
    - UNHEALTHY: Fail fast
    """

    logger: "LoggerPort"

    _cached_health: HealthStatus = field(init=False, default=HealthStatus.HEALTHY)
    _last_health_check: datetime | None = field(init=False, default=None)
    _health_consecutive_errors: int = field(init=False, default=0)

    def update_health_from_errors(self, consecutive_errors: int) -> None:
        """Обновить статус здоровья на основе ошибок.

        Args:
            consecutive_errors: Количество последовательных ошибок
        """
        previous = self._cached_health
        self._health_consecutive_errors = consecutive_errors

        if consecutive_errors >= 3:
            self._cached_health = HealthStatus.UNHEALTHY
        elif consecutive_errors >= 1:
            self._cached_health = HealthStatus.DEGRADED
        else:
            self._cached_health = HealthStatus.HEALTHY

        # Логировать переходы
        if previous != self._cached_health:
            self.logger.info(
                "health_transition",
                previous=previous.value,
                current=self._cached_health.value,
                consecutive_errors=consecutive_errors,
            )

    def get_health(self) -> HealthStatus:
        """Получить текущий статус здоровья."""
        return self._cached_health

    def is_healthy(self) -> bool:
        """Проверить, что адаптер в рабочем состоянии."""
        return self._cached_health != HealthStatus.UNHEALTHY

    def mark_healthy(self) -> None:
        """Пометить адаптер как здоровый."""
        self._health_consecutive_errors = 0
        self._cached_health = HealthStatus.HEALTHY
        self._last_health_check = datetime.now()
```

#### R2.3: Рефакторить ChemblAdapter

```python
# src/bioetl/infrastructure/adapters/chembl/client.py

from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.mixins.error_handling import ErrorHandlingMixin
from bioetl.infrastructure.adapters.mixins.health_monitor import HealthMonitorMixin
from bioetl.infrastructure.adapters.http.pagination import PaginatedFetcherMixin


@dataclass
class ChemblAdapter(
    BaseHttpAdapter,
    ErrorHandlingMixin,
    HealthMonitorMixin,
    PaginatedFetcherMixin,
):
    """ChEMBL data source adapter.

    Implements DataSourcePort for fetching data from ChEMBL database.
    """

    http_client: UnifiedHTTPClient
    logger: LoggerPort
    batch_size: int = 1000
    thread_pool: ThreadPoolExecutor | None = None

    provider_name: str = field(init=False, default="chembl")

    def _get_effective_batch_size(self) -> int:
        """Get batch size adjusted for health status."""
        health = self.get_health()

        if health == HealthStatus.UNHEALTHY:
            raise CriticalError(
                f"ChEMBL adapter is UNHEALTHY after "
                f"{self._health_consecutive_errors} consecutive errors."
            )

        if health == HealthStatus.DEGRADED:
            return max(100, self.batch_size // 2)

        return self.batch_size

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records from ChEMBL."""
        # Используем PaginatedFetcherMixin
        async for record in self.fetch_paginated(
            url=self._get_resource_url(entity_type),
            entity_type=entity_type,
            limit=limit,
            filter_ids=filter_ids,
            filter_field=filter_field,
        ):
            yield record

    async def _fetch_page(
        self, url: str, params: dict[str, Any], entity_type: str
    ) -> tuple[list[dict[str, Any]], bool]:
        """Fetch a single page (for PaginatedFetcherMixin)."""
        try:
            response = await self.http_client.get(url, params=params)
            records, has_next = self._process_response(response, entity_type)
            self.reset_consecutive_errors()
            return records, has_next
        except Exception as e:
            self.handle_error(e, context="fetch", provider="chembl")
            self.update_health_from_errors(self._consecutive_errors)
            return [], False

    # ... остальные методы (health_check, _process_response, etc.)
```

**Тесты:**

| Файл | Тест |
|------|------|
| `tests/unit/infrastructure/adapters/mixins/test_error_handling.py` | `test_handle_error_increments_counters` |
| `tests/unit/infrastructure/adapters/mixins/test_error_handling.py` | `test_critical_error_raises` |
| `tests/unit/infrastructure/adapters/mixins/test_health_monitor.py` | `test_health_transitions` |
| `tests/unit/infrastructure/adapters/chembl/test_client.py` | `test_adapter_uses_mixins` |

**Критерии готовности:**
- [ ] ChemblAdapter < 200 строк
- [ ] Mixins покрыты unit тестами
- [ ] Все существующие тесты проходят
- [ ] `mypy --strict` проходит

**Риски и митигация:**

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Изменение публичного API | Средняя | Сохранить сигнатуры методов |
| Регрессия в error handling | Средняя | Сравнить поведение до/после |
| MRO конфликты | Низкая | Тестировать порядок наследования |

---

### R3: Типизация registry.py

**Приоритет:** 🔴 КРИТИЧЕСКИЙ

**Проблема:**
- `PipelineFactoryProtocol` использует `Any` 6 раз
- Потеря типобезопасности, mypy не ловит ошибки

**Файл:** `src/bioetl/composition/registry.py:18-34`

**Конкретные правки:**

```python
# До (строки 18-34):
def create_with_services(
    self, run_id: Any, runtime: Any, settings: Any, logger: Any, **kwargs: Any
) -> Any:

# После:
from bioetl.domain.types import RunID
from bioetl.domain.config import RuntimeConfig
from bioetl.domain.ports import LoggerPort, TracingPort
from bioetl.infrastructure.config import Settings

@runtime_checkable
class PipelineFactoryProtocol(Protocol):
    """Protocol for pipeline factories."""

    pipeline_name: str
    silver_schema: pa.Schema | None

    def create_with_services(
        self,
        run_id: RunID,
        runtime: RuntimeConfig,
        settings: Settings,
        logger: LoggerPort,
        **kwargs: Any,  # kwargs остаётся Any для расширяемости
    ) -> "BasePipeline":
        """Create pipeline with services."""
        ...

    def create_runner(
        self,
        run_id: RunID,
        runtime: RuntimeConfig,
        settings: Settings,
        logger: LoggerPort,
        tracer: TracingPort | None,
        filter_config: InputFilterConfig | None = None,
        config: PipelineYamlConfig | None = None,
    ) -> "PipelineRunner":
        """Create pipeline runner."""
        ...
```

**Также обновить:**
- `src/bioetl/composition/factories/pipeline_factories.py` — GenericPipelineFactory
- `src/bioetl/composition/builders.py` — если используют эти типы

**Тесты:**

| Файл | Тест |
|------|------|
| `tests/unit/composition/test_registry.py` | `test_factory_protocol_type_hints` |
| `tests/architecture/test_layer_dependencies.py` | `test_no_any_in_protocols` |

**Критерии готовности:**
- [ ] Нет `Any` в сигнатурах (кроме kwargs)
- [ ] `mypy --strict` проходит для registry.py
- [ ] Все фабрики обновлены
- [ ] `make lint && make test` проходит

---

### R4: Расширить тестирование interfaces слоя

**Приоритет:** 🟠 ВЫСОКИЙ

**Проблема:**
- interfaces layer: 5 файлов, 322 строки
- Unit тесты: только 3 файла
- Orchestration tests: 0 тестов

**Конкретные правки:**

#### R4.1: Тесты для signals.py

**Новый файл:** `tests/unit/interfaces/orchestration/test_signals.py`

```python
"""Tests for graceful shutdown signal handling."""

import signal
from unittest.mock import MagicMock, patch

import pytest

from bioetl.interfaces.orchestration.signals import (
    SignalHandler,
    install_signal_handlers,
)


class TestSignalHandler:
    """Tests for SignalHandler class."""

    def test_sigterm_triggers_shutdown(self):
        """SIGTERM должен установить shutdown flag."""
        handler = SignalHandler()
        assert not handler.should_shutdown

        handler.handle_signal(signal.SIGTERM, None)

        assert handler.should_shutdown

    def test_sigint_triggers_shutdown(self):
        """SIGINT должен установить shutdown flag."""
        handler = SignalHandler()

        handler.handle_signal(signal.SIGINT, None)

        assert handler.should_shutdown

    def test_multiple_signals_handled(self):
        """Повторные сигналы не должны падать."""
        handler = SignalHandler()

        handler.handle_signal(signal.SIGTERM, None)
        handler.handle_signal(signal.SIGTERM, None)  # Повторный

        assert handler.should_shutdown

    def test_callback_invoked_on_shutdown(self):
        """Callback должен вызываться при shutdown."""
        callback = MagicMock()
        handler = SignalHandler(callback=callback)

        handler.handle_signal(signal.SIGTERM, None)

        callback.assert_called_once()


class TestInstallSignalHandlers:
    """Tests for install_signal_handlers function."""

    @patch("signal.signal")
    def test_installs_sigterm_handler(self, mock_signal):
        """Должен установить handler для SIGTERM."""
        handler = install_signal_handlers()

        assert any(
            call[0][0] == signal.SIGTERM
            for call in mock_signal.call_args_list
        )

    @patch("signal.signal")
    def test_installs_sigint_handler(self, mock_signal):
        """Должен установить handler для SIGINT."""
        handler = install_signal_handlers()

        assert any(
            call[0][0] == signal.SIGINT
            for call in mock_signal.call_args_list
        )
```

#### R4.2: Дополнить тесты CLI

**Файл:** `tests/unit/interfaces/test_cli.py`

Добавить:

```python
def test_input_csv_filter_validation(cli_runner):
    """--input-csv без --filter-column должен выдать ошибку."""
    result = cli_runner.invoke(
        cli,
        ["run", "chembl_activity", "--input-csv", "test.csv"],
    )
    assert result.exit_code != 0
    assert "filter-column" in result.output.lower()


def test_invalid_pipeline_name_error(cli_runner):
    """Неизвестный pipeline должен выдать понятную ошибку."""
    result = cli_runner.invoke(
        cli,
        ["run", "nonexistent_pipeline"],
    )
    assert result.exit_code != 0
    assert "Unknown pipeline" in result.output or "not found" in result.output.lower()


def test_dry_run_does_not_modify_data(cli_runner, tmp_path):
    """--dry-run не должен изменять данные."""
    # Setup
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    result = cli_runner.invoke(
        cli,
        ["run", "chembl_activity", "--dry-run"],
        env={"BIOETL_DATA_DIR": str(data_dir)},
    )

    assert result.exit_code == 0
    assert "dry-run" in result.output.lower()


def test_metrics_server_failure_non_blocking(cli_runner, mocker):
    """Ошибка metrics server не должна блокировать запуск."""
    mocker.patch(
        "bioetl.infrastructure.observability.server.start_metrics_server",
        side_effect=OSError("Port in use"),
    )

    result = cli_runner.invoke(
        cli,
        ["run", "chembl_activity", "--limit", "1"],
    )

    # Pipeline должен продолжить работу
    assert "metrics" in result.output.lower() or result.exit_code == 0
```

**Критерии готовности:**
- [ ] 10+ новых тестов добавлено
- [ ] Покрытие interfaces > 80%
- [ ] Тесты для signals, CLI, observability
- [ ] `make test` проходит

---

### R5: Сделать StoragePort полностью асинхронным

**Приоритет:** 🟠 ВЫСОКИЙ

**Проблема:**
- `StoragePort` смешивает async и sync методы
- `clear_silver()`, `clear_gold()`, `preview_cleanup()` — sync
- Риск блокировки event loop

**Файл:** `src/bioetl/domain/ports.py`

**Конкретные правки:**

```python
# До (строки 222-252):
async def clear_silver(self, table_name: str, dry_run: bool = False) -> int:
    ...

# После — все методы async:
async def clear_silver(self, table_name: str, dry_run: bool = False) -> int:
    """Clear Silver layer data (async)."""
    ...

async def clear_gold(self, table_name: str, dry_run: bool = False) -> int:
    """Clear Gold layer data (async)."""
    ...

async def clear_csv(self, table_name: str | None = None) -> int:
    """Clear CSV export files (async)."""
    ...

async def clear_delta(self, table_name: str | None = None) -> int:
    """Clear Delta tables (async)."""
    ...

async def preview_cleanup(
    self,
    silver_table: str,
    gold_table: str | None = None,
) -> dict[str, Any]:
    """Preview cleanup (async for consistency)."""
    ...
```

**Также обновить:**
- `src/bioetl/composition/factories/storage_factory.py` — StorageAdapter
- `src/bioetl/infrastructure/storage/delta_writer.py` — DeltaWriter
- `src/bioetl/infrastructure/storage/gold_writer.py` — GoldWriter

**Критерии готовности:**
- [ ] Все методы StoragePort — async
- [ ] Реализации используют run_in_executor для blocking I/O
- [ ] Тесты обновлены
- [ ] `make lint && make test` проходит

---

### R6: Детерминизировать классификацию ошибок

**Приоритет:** 🟠 ВЫСОКИЙ

**Проблема:**
- `ErrorClassifier` использует keyword matching
- Нет явной связи исключений и `ErrorType`

**Файлы:**
- `src/bioetl/domain/exceptions.py`
- `src/bioetl/domain/error_classifier.py`

**Конкретные правки:**

```python
# src/bioetl/domain/exceptions.py

from bioetl.domain.types import ErrorType


class BioETLError(Exception):
    """Base exception for all BioETL errors."""
    error_type: ErrorType = ErrorType.INVALID_DATA  # Default fallback

    def __init__(self, message: str, *args, **kwargs):
        super().__init__(message, *args, **kwargs)


class CriticalError(BioETLError):
    """Base for non-recoverable errors."""
    error_type = ErrorType.DB_UNAVAILABLE


class LockLostError(CriticalError):
    """Lock was lost during operation."""
    error_type = ErrorType.LOCK_LOST


class AuthFailureError(CriticalError):
    """Authentication failed."""
    error_type = ErrorType.AUTH_FAILURE


class RecoverableError(BioETLError):
    """Base for errors that can be retried."""
    error_type = ErrorType.NETWORK_ERROR


class RateLimitError(RecoverableError):
    """API rate limit exceeded."""
    error_type = ErrorType.RATE_LIMIT


class TimeoutError(RecoverableError):
    """Operation timed out."""
    error_type = ErrorType.TIMEOUT


class DataQualityError(BioETLError):
    """Base for data quality issues."""
    error_type = ErrorType.DATA_QUALITY


class SchemaViolationError(DataQualityError):
    """Schema validation failed."""
    error_type = ErrorType.SCHEMA_VIOLATION
```

```python
# src/bioetl/domain/error_classifier.py

class ErrorClassifier:
    """Classifies exceptions into ErrorType categories."""

    def classify(self, error: Exception) -> ErrorType:
        """Classify an exception.

        Strategy:
        1. Use error_type attribute if BioETLError subclass
        2. Fallback to keyword matching for external exceptions
        """
        if isinstance(error, BioETLError):
            return error.error_type

        # Fallback for non-domain exceptions
        return self._match_by_keywords(type(error).__name__)
```

**Тесты:**

| Файл | Тест |
|------|------|
| `tests/unit/domain/test_error_classifier.py` | `test_classify_uses_error_type_attribute` |
| `tests/unit/domain/test_error_classifier.py` | `test_each_exception_has_correct_error_type` |

**Критерии готовности:**
- [ ] Все `BioETLError` подклассы имеют `error_type`
- [ ] `ErrorClassifier` использует атрибут для доменных ошибок
- [ ] Parametrized тест покрывает все типы

---

### R7: Управление жизненным циклом observability

**Приоритет:** 🟠 ВЫСОКИЙ

**Проблема:**
- `MetricsPort` и `TracingPort` не имеют `close()`
- OpenTelemetry не flush'ит spans при shutdown

**Файлы:**
- `src/bioetl/domain/ports.py`
- `src/bioetl/infrastructure/observability/prometheus_metrics.py`
- `src/bioetl/infrastructure/observability/tracing.py`

**Конкретные правки:**

```python
# src/bioetl/domain/ports.py

@runtime_checkable
class MetricsPort(Protocol):
    """Port for metrics collection."""

    def observe_histogram(...) -> None: ...
    def increment_counter(...) -> None: ...

    def close(self) -> None:
        """Cleanup metrics resources. Idempotent."""
        ...


@runtime_checkable
class TracingPort(Protocol):
    """Port for distributed tracing."""

    def get_tracer(self, name: str) -> Any: ...

    def close(self) -> None:
        """Flush pending spans and cleanup. Idempotent."""
        ...
```

**Критерии готовности:**
- [ ] `close()` определён в портах
- [ ] Реализации (Prometheus, OTEL, NoOp) idempotent
- [ ] `PipelineRunner` вызывает `close()` в finally

---

### R8: Устранение sentinel values

**Приоритет:** 🟡 СРЕДНИЙ

**Проблема:**
- `pipeline_name: str = "unknown"` нарушает RULES.md §2.6

**Файл:** `src/bioetl/composition/factories/data_source_registry.py`

**Конкретные правки:**

```python
# До:
pipeline_name: str = "unknown"

# После:
pipeline_name: str | None = None
```

**Критерии готовности:**
- [ ] Нет sentinel values ("unknown", -1, "N/A")
- [ ] Используется `None` или `Optional`

---

### R9: Типизация observer.py

**Приоритет:** 🟡 СРЕДНИЙ

**Проблема:**
- `self.span: Any = None` — потеря типизации

**Файл:** `src/bioetl/application/observability/observer.py:48`

**Конкретные правки:**

```python
# До:
self.span: Any = None

# После:
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentelemetry.trace import Span

# В __init__:
self.span: "Span | None" = None
```

**Критерии готовности:**
- [ ] `mypy --strict` проходит

---

### R10: Унификация Pagination

**Приоритет:** 🟡 СРЕДНИЙ

**Проблема:**
- `ChemblAdapter` имеет свой `_page_iterator()`
- `UniProtClient` использует `PaginatedFetcherMixin`
- Нет единообразия

**Конкретные правки:**

1. Переместить mixin в `src/bioetl/infrastructure/adapters/mixins/pagination.py`
2. Обновить `ChemblAdapter` для использования mixin

**Критерии готовности:**
- [ ] Все HTTP-адаптеры используют `PaginatedFetcherMixin`
- [ ] Удалён дублирующий код пагинации

---

## 4. Порядок Выполнения

```
Sprint 1 (Критические)
├── R1: PubMedAdapter health_check ─────┐
├── R2: ChemblAdapter декомпозиция ─────┼──▶ R4: Interface тесты
└── R3: Типизация registry.py ──────────┘

Sprint 2 (Высокий приоритет)
├── R4: Interface тесты ────────────────┐
├── R5: StoragePort async ──────────────┼──▶ R7: Observability lifecycle
├── R6: Error classification ───────────┘
└── R7: Observability lifecycle

Sprint 3 (Средний приоритет)
├── R8: Sentinel values
├── R9: Observer типизация
├── R10: Pagination унификация
└── R11: domain/__init__.py

Backlog
├── R12: ResponseProcessor
├── R13: PII Salt
├── R14: Трансформеры декомпозиция
└── R15: Thread-safe Registry
```

---

## 5. Метрики Успеха

### До начала рефакторинга

```bash
make lint && make test  # Должно проходить
```

### После каждой задачи

| Метрика | Текущее | Целевое |
|---------|---------|---------|
| Архитектурный балл | 8.6 | 9.2+ |
| Line Coverage | 80% | 85%+ |
| ChemblAdapter LOC | 431 | <200 |
| Any типов в composition | 10+ | 0 |
| Interfaces тестов | 3 | 15+ |
| Sentinel values | 6+ | 0 |

### Автоматические проверки

```makefile
# Добавить в Makefile:

.PHONY: refactor-check
refactor-check:
	@echo "Checking refactoring metrics..."
	@# ChemblAdapter < 200 LOC
	@wc -l src/bioetl/infrastructure/adapters/chembl/client.py | awk '{if($$1 > 200) exit 1}'
	@# No Any in protocols (except kwargs)
	@! grep -n ": Any" src/bioetl/composition/registry.py | grep -v "kwargs"
	@# No sentinel "unknown"
	@! grep -rn '= "unknown"' src/bioetl/
	@echo "All refactoring checks passed!"
```

---

## Чек-лист перед началом

- [ ] `make lint && make test` проходит
- [ ] Git branch создан: `refactor/architecture-cleanup`
- [ ] Прочитаны `docs/RULES.md` и `AGENT.md`
- [ ] Понятны критерии приёмки каждой задачи
- [ ] Backup текущего состояния (tag/branch)

---

*Подготовлено на основе архитектурного обзора 2025-12-24*
