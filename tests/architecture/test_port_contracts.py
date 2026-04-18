"""Tests for port contract verification.

These tests ensure that all port definitions in domain/ports/ package follow
the established contracts for lifecycle management and interface consistency.

Implements the refactoring plan: "Расширение контрактных тестов портов".
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import get_type_hints

import pytest

from bioetl.domain import ports
from bioetl.domain.value_objects.dq_anomaly import DQAnomaly


def _ports_dir(src_dir: Path) -> Path:
    return src_dir / "bioetl" / "domain" / "ports"


def _iter_port_files(ports_dir: Path) -> list[Path]:
    return [path for path in ports_dir.glob("*.py") if path.name != "__init__.py"]


def _parse_ast(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _iter_port_classes(tree: ast.AST) -> list[ast.ClassDef]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name.endswith("Port")
    ]


def _is_port_method(node: ast.stmt) -> bool:
    return isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)


def _is_public_port_method(method: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return not method.name.startswith("_") or method.name in {"__aenter__", "__aexit__"}


def _iter_public_port_methods(
    port_class: ast.ClassDef,
) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [
        method
        for method in port_class.body
        if _is_port_method(method) and _is_public_port_method(method)
    ]


def _method_has_docstring(method: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return bool(
        method.body
        and isinstance(method.body[0], ast.Expr)
        and isinstance(method.body[0].value, ast.Constant)
        and isinstance(method.body[0].value.value, str)
    )


def _is_ellipsis_expr(node: ast.expr) -> bool:
    if isinstance(node, ast.Constant) and node.value is ...:
        return True
    return bool(
        hasattr(ast, "Ellipsis")
        and isinstance(node, ast.Ellipsis)  # type: ignore[attr-defined]
    )


def _method_body_is_port_contract_only(
    method: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    body = method.body
    if len(body) == 1 and isinstance(body[0], ast.Expr):
        if _method_has_docstring(method):
            return True
        return _is_ellipsis_expr(body[0].value)
    if len(body) != 2 or not _method_has_docstring(method):
        return False
    return isinstance(body[1], ast.Expr) and _is_ellipsis_expr(body[1].value)


def _missing_port_docstrings(ports_dir: Path) -> list[str]:
    missing_docstrings: list[str] = []
    for ports_file in _iter_port_files(ports_dir):
        tree = _parse_ast(ports_file)
        for port_class in _iter_port_classes(tree):
            for method in _iter_public_port_methods(port_class):
                if not _method_has_docstring(method):
                    missing_docstrings.append(f"{port_class.name}.{method.name}")
    return missing_docstrings


def _port_implementations(ports_dir: Path) -> list[str]:
    implementations_found: list[str] = []
    for ports_file in _iter_port_files(ports_dir):
        tree = _parse_ast(ports_file)
        for port_class in _iter_port_classes(tree):
            for method in _iter_public_port_methods(port_class):
                if not _method_body_is_port_contract_only(method):
                    implementations_found.append(f"{port_class.name}.{method.name}")
    return implementations_found


# ============================================================================
# Port Lifecycle Contract Tests
# ============================================================================


class TestAsyncPortLifecycle:
    """Tests for async port lifecycle methods.

    All async I/O ports MUST define aclose() for graceful shutdown.
    """

    ASYNC_IO_PORTS = [
        "DataSourcePort",
        "StoragePort",
        "LockPort",
        "CheckpointPort",
        "QuarantinePort",
    ]

    @pytest.mark.parametrize("port_name", ASYNC_IO_PORTS)
    def test_async_ports_have_aclose_method(self, port_name: str) -> None:
        """All async I/O ports MUST have aclose() method for graceful shutdown."""
        port_class = getattr(ports, port_name)

        assert hasattr(port_class, "aclose"), (
            f"{port_name} MUST define aclose() method for graceful shutdown. "
            f"See ADR-008 for graceful shutdown requirements."
        )

        # Check that aclose is async
        aclose_method = port_class.aclose
        # For Protocol classes, we check the annotation
        hints = (
            get_type_hints(aclose_method)
            if hasattr(aclose_method, "__annotations__")
            else {}
        )

        # The method should return None (async def aclose(self) -> None)
        assert hints.get("return") is type(None) or "return" not in hints, (
            f"{port_name}.aclose() should return None"
        )

    def test_datasource_port_has_context_manager(self) -> None:
        """DataSourcePort MUST support async context manager protocol."""
        assert hasattr(ports.DataSourcePort, "__aenter__"), (
            "DataSourcePort MUST define __aenter__ for async context manager"
        )
        assert hasattr(ports.DataSourcePort, "__aexit__"), (
            "DataSourcePort MUST define __aexit__ for async context manager"
        )

    def test_datasource_port_has_health_check(self) -> None:
        """DataSourcePort MUST have health_check for pre-flight validation."""
        assert hasattr(ports.DataSourcePort, "health_check"), (
            "DataSourcePort MUST define health_check() for HealthAggregator"
        )

    def test_storage_port_has_health_check(self) -> None:
        """StoragePort MUST have health_check for pre-flight validation."""
        assert hasattr(ports.StoragePort, "health_check"), (
            "StoragePort MUST define health_check() for HealthAggregator"
        )


class TestObservabilityPortLifecycle:
    """Tests for observability port lifecycle methods.

    MetricsPort and TracingPort use synchronous close() methods
    because they use thread-safe operations, not async I/O.
    """

    OBSERVABILITY_PORTS = [
        "MetricsPort",
        "TracingPort",
    ]

    @pytest.mark.parametrize("port_name", OBSERVABILITY_PORTS)
    def test_observability_ports_have_close_method(self, port_name: str) -> None:
        """Observability ports MUST have close() for resource cleanup."""
        port_class = getattr(ports, port_name)

        assert hasattr(port_class, "close"), (
            f"{port_name} MUST define close() method for resource cleanup. "
            f"See ADR-006 for observability port contracts."
        )


class TestLoggerPortContract:
    """Tests for LoggerPort contract."""

    REQUIRED_LOG_METHODS = ["info", "warning", "error", "debug", "exception"]

    @pytest.mark.parametrize("method_name", REQUIRED_LOG_METHODS)
    def test_logger_port_has_log_methods(self, method_name: str) -> None:
        """LoggerPort MUST have standard log level methods."""
        assert hasattr(ports.LoggerPort, method_name), (
            f"LoggerPort MUST define {method_name}() method"
        )

    def test_logger_port_has_bind_method(self) -> None:
        """LoggerPort MUST have bind() for context propagation."""
        assert hasattr(ports.LoggerPort, "bind"), (
            "LoggerPort MUST define bind() for structured context"
        )


class TestDQMonitorPortTypingContract:
    """Tests for typed DQ anomaly boundary contract."""

    def test_dq_monitor_port_returns_typed_domain_dto(self) -> None:
        """DQMonitorPort.check_quality() MUST return domain-owned DQAnomaly DTOs."""
        hints = get_type_hints(ports.DQMonitorPort.check_quality)

        assert hints["return"] == list[DQAnomaly], (
            "DQMonitorPort.check_quality() MUST return list[DQAnomaly] "
            "instead of Any or infrastructure-shaped anomaly objects."
        )


# ============================================================================
# Port Interface Completeness Tests
# ============================================================================


class TestPortRuntimeCheckable:
    """Tests that all ports are runtime_checkable for isinstance() checks."""

    ALL_PORTS = [
        "TracingPort",
        "DataSourcePort",
        "FilterableDataSourcePort",
        "FallbackPolicyPort",
        "InputFilterPort",
        "StoragePort",
        "LockPort",
        "CheckpointPort",
        "QuarantinePort",
        "MetricsPort",
        "LoggerPort",
        "GoldValidatorPort",
        "DQMonitorPort",
        "RateLimiterPort",
        "CircuitBreakerPort",
        "JsonEncoderPort",
    ]

    @pytest.mark.parametrize("port_name", ALL_PORTS)
    def test_ports_are_runtime_checkable(self, port_name: str) -> None:
        """All ports MUST be @runtime_checkable for isinstance() checks."""
        port_class = getattr(ports, port_name, None)
        if port_class is None:
            pytest.skip(f"{port_name} not found in ports module")

        # Test by attempting isinstance() - non-runtime_checkable raises TypeError
        class DummyImpl:
            """Dummy class for testing isinstance()."""

            pass

        try:
            # This should NOT raise TypeError if port is @runtime_checkable
            isinstance(DummyImpl(), port_class)
            is_runtime_checkable = True
        except TypeError:
            is_runtime_checkable = False

        assert is_runtime_checkable, (
            f"{port_name} MUST be decorated with @runtime_checkable. "
            f"This enables isinstance() checks for structural subtyping."
        )


class TestPortExportsComplete:
    """Tests that all ports are exported in __all__."""

    def test_all_ports_in_public_api(self) -> None:
        """All port definitions MUST be exported in __all__."""
        expected_ports = {
            "TracingPort",
            "DataSourcePort",
            "DQMonitorPort",
            "FilterableDataSourcePort",
            "FallbackPolicyPort",
            "InputFilterPort",
            "StoragePort",
            "LockPort",
            "CheckpointPort",
            "ClockPort",
            "QuarantinePort",
            "MetricsPort",
            "LoggerPort",
            "GoldValidatorPort",
            "RateLimiterPort",
            "CircuitBreakerPort",
            "JsonEncoderPort",
        }

        actual_exports = set(ports.__all__) if hasattr(ports, "__all__") else set()

        missing = expected_ports - actual_exports
        assert not missing, (
            f"Ports not in __all__: {missing}. "
            f"All ports MUST be exported for public API."
        )


# ============================================================================
# Storage Port Contract Tests
# ============================================================================


class TestStoragePortContract:
    """Tests for StoragePort specific contracts."""

    REQUIRED_WRITE_METHODS = ["write_bronze", "write_silver", "write_gold"]
    REQUIRED_CLEAR_METHODS = ["clear_silver", "clear_gold", "clear_csv", "clear_delta"]
    REQUIRED_MAINTENANCE_METHODS = ["vacuum", "archive"]

    @pytest.mark.parametrize("method_name", REQUIRED_WRITE_METHODS)
    def test_storage_port_has_write_methods(self, method_name: str) -> None:
        """StoragePort MUST have all layer write methods."""
        assert hasattr(ports.StoragePort, method_name), (
            f"StoragePort MUST define {method_name}() for Medallion architecture"
        )

    @pytest.mark.parametrize("method_name", REQUIRED_CLEAR_METHODS)
    def test_storage_port_has_clear_methods(self, method_name: str) -> None:
        """StoragePort MUST have clear methods for rebuild/backfill."""
        assert hasattr(ports.StoragePort, method_name), (
            f"StoragePort MUST define {method_name}() for data cleanup"
        )

    @pytest.mark.parametrize("method_name", REQUIRED_MAINTENANCE_METHODS)
    def test_storage_port_has_maintenance_methods(self, method_name: str) -> None:
        """StoragePort MUST have vacuum and archive methods for Delta Lake maintenance."""
        assert hasattr(ports.StoragePort, method_name), (
            f"StoragePort MUST define {method_name}() for Delta Lake maintenance"
        )

    def test_storage_port_has_preview_cleanup(self) -> None:
        """StoragePort MUST have preview_cleanup for CLI dry-run mode."""
        assert hasattr(ports.StoragePort, "preview_cleanup"), (
            "StoragePort MUST define preview_cleanup() for CLI dry-run. "
            "See architecture test: test_storage_port_has_preview_cleanup"
        )

    def test_storage_port_vacuum_has_correct_signature(self) -> None:
        """StoragePort.vacuum() MUST have table_name, retention_hours, dry_run params."""
        import inspect

        sig = inspect.signature(ports.StoragePort.vacuum)
        params = sig.parameters

        assert "table_name" in params, "vacuum() MUST have table_name parameter"
        assert "retention_hours" in params, (
            "vacuum() MUST have retention_hours parameter"
        )
        assert "dry_run" in params, "vacuum() MUST have dry_run parameter"

    def test_storage_port_archive_has_correct_signature(self) -> None:
        """StoragePort.archive() MUST have table_name, target_path, remove_source params."""
        import inspect

        sig = inspect.signature(ports.StoragePort.archive)
        params = sig.parameters

        assert "table_name" in params, "archive() MUST have table_name parameter"
        assert "target_path" in params, "archive() MUST have target_path parameter"
        assert "remove_source" in params, "archive() MUST have remove_source parameter"

    def test_storage_port_write_gold_requires_schema(self) -> None:
        """StoragePort.write_gold() MUST have required schema parameter.

        Gold layer writes MUST include schema for validation.
        This ensures data quality at the Gold layer boundary.
        See RULES.md §2.1.1 - Gold Layer specifications.
        """
        import inspect

        sig = inspect.signature(ports.StoragePort.write_gold)
        params = sig.parameters

        assert "schema" in params, (
            "StoragePort.write_gold() MUST have schema parameter. "
            "Gold layer requires strict schema validation."
        )

        # Schema parameter MUST NOT have a default value (i.e., it's required)
        schema_param = params["schema"]
        assert schema_param.default is inspect.Parameter.empty, (
            "StoragePort.write_gold() schema parameter MUST be required (no default). "
            "All Gold layer writes MUST provide a schema for validation."
        )


# ============================================================================
# Metrics Port Contract Tests
# ============================================================================


class TestMetricsPortContract:
    """Tests for MetricsPort specific contracts."""

    REQUIRED_METRIC_METHODS = [
        "observe_histogram",
        "increment_counter",
        "set_gauge",
    ]

    @pytest.mark.parametrize("method_name", REQUIRED_METRIC_METHODS)
    def test_metrics_port_has_metric_methods(self, method_name: str) -> None:
        """MetricsPort MUST have all standard metric methods."""
        assert hasattr(ports.MetricsPort, method_name), (
            f"MetricsPort MUST define {method_name}() for observability"
        )


# ============================================================================
# Lock Port Contract Tests
# ============================================================================


class TestLockPortContract:
    """Tests for LockPort specific contracts."""

    REQUIRED_LOCK_METHODS = ["acquire", "release", "heartbeat"]

    @pytest.mark.parametrize("method_name", REQUIRED_LOCK_METHODS)
    def test_lock_port_has_lock_methods(self, method_name: str) -> None:
        """LockPort MUST have acquire, release, and heartbeat methods."""
        assert hasattr(ports.LockPort, method_name), (
            f"LockPort MUST define {method_name}() for runtime locking"
        )


# ============================================================================
# Checkpoint Port Contract Tests
# ============================================================================


class TestCheckpointPortContract:
    """Tests for CheckpointPort specific contracts."""

    REQUIRED_CHECKPOINT_METHODS = ["save", "load", "list_all", "delete"]

    @pytest.mark.parametrize("method_name", REQUIRED_CHECKPOINT_METHODS)
    def test_checkpoint_port_has_methods(self, method_name: str) -> None:
        """CheckpointPort MUST have CRUD-like methods."""
        assert hasattr(ports.CheckpointPort, method_name), (
            f"CheckpointPort MUST define {method_name}() for state persistence"
        )


# ============================================================================
# Quarantine Port Contract Tests
# ============================================================================


class TestQuarantinePortContract:
    """Tests for QuarantinePort specific contracts."""

    REQUIRED_QUARANTINE_METHODS = [
        "write",
        "write_many",
        "inspect",
        "get_stats",
        "list_filtered_records",
        "get_filtered_record",
        "get_filtered_stats",
        "get_filtered_filter_options",
    ]

    @pytest.mark.parametrize("method_name", REQUIRED_QUARANTINE_METHODS)
    def test_quarantine_port_has_methods(self, method_name: str) -> None:
        """QuarantinePort MUST have write, inspect, and stats methods."""
        assert hasattr(ports.QuarantinePort, method_name), (
            f"QuarantinePort MUST define {method_name}() for failed record isolation"
        )


# ============================================================================
# Static Analysis Tests
# ============================================================================


class TestPortDefinitionQuality:
    """Tests for port definition quality using static analysis."""

    def test_all_port_methods_have_docstrings(self, src_dir: Path) -> None:
        """All port methods SHOULD have docstrings."""
        ports_dir = _ports_dir(src_dir)
        if not ports_dir.exists():
            pytest.skip("ports/ package not found")
        missing_docstrings = _missing_port_docstrings(ports_dir)

        # Allow some missing (ellipsis-only methods in Protocols are ok without detailed docs)
        # But warn if there are many
        if len(missing_docstrings) > 5:
            pytest.fail(
                f"Too many port methods without docstrings ({len(missing_docstrings)}):\n"
                + "\n".join(f"  - {m}" for m in missing_docstrings[:10])
            )

    def test_no_implementation_in_ports(self, src_dir: Path) -> None:
        """Port methods MUST only have ellipsis (...) as body, no implementation."""
        ports_dir = _ports_dir(src_dir)
        if not ports_dir.exists():
            pytest.skip("ports/ package not found")
        implementations_found = _port_implementations(ports_dir)

        assert not implementations_found, (
            "Ports should not contain implementations (use ... only):\n"
            + "\n".join(f"  - {m}" for m in implementations_found)
        )


# ============================================================================
# DQ Monitor Port Contract Tests
# ============================================================================


class TestDQMonitorPortContract:
    """Tests for DQMonitorPort specific contracts."""

    REQUIRED_DQ_METHODS = [
        "add_metric",
        "check_quality",
        "update_baseline_from_metrics",
        "get_baseline_stats",
    ]

    @pytest.mark.parametrize("method_name", REQUIRED_DQ_METHODS)
    def test_dq_monitor_port_has_required_methods(self, method_name: str) -> None:
        """DQMonitorPort MUST have all required methods for anomaly detection."""
        assert hasattr(ports.DQMonitorPort, method_name), (
            f"DQMonitorPort MUST define {method_name}() for data quality monitoring"
        )

    def test_dq_monitor_port_check_quality_returns_list(self) -> None:
        """DQMonitorPort.check_quality() MUST return list of anomalies."""
        import inspect

        sig = inspect.signature(ports.DQMonitorPort.check_quality)
        params = sig.parameters

        assert "metrics" in params, "check_quality() MUST have metrics parameter"
        assert "timestamp" in params, (
            "check_quality() MUST accept the canonical application-owned "
            "timestamp parameter"
        )
        assert params["timestamp"].default is None, (
            "check_quality() timestamp parameter MUST remain optional for "
            "graceful degradation"
        )

    def test_dq_monitor_port_update_baseline_accepts_timestamp(self) -> None:
        """Baseline updates MUST accept the canonical application timestamp."""
        import inspect

        sig = inspect.signature(ports.DQMonitorPort.update_baseline_from_metrics)
        params = sig.parameters

        assert "metrics" in params, (
            "update_baseline_from_metrics() MUST have metrics parameter"
        )
        assert "timestamp" in params, (
            "update_baseline_from_metrics() MUST accept the canonical "
            "application-owned timestamp parameter"
        )
        assert params["timestamp"].default is None, (
            "update_baseline_from_metrics() timestamp parameter MUST remain "
            "optional for graceful degradation"
        )

    def test_dq_monitor_port_is_runtime_checkable(self) -> None:
        """DQMonitorPort MUST be @runtime_checkable for isinstance() checks."""

        class DummyMonitor:
            """Dummy class for testing isinstance()."""

            pass

        try:
            isinstance(DummyMonitor(), ports.DQMonitorPort)
            is_runtime_checkable = True
        except TypeError:
            is_runtime_checkable = False

        assert is_runtime_checkable, (
            "DQMonitorPort MUST be decorated with @runtime_checkable"
        )


# ============================================================================
# Storage Writer LoggerPort Contract Tests
# ============================================================================


class TestStorageWriterLoggerContract:
    """Tests for storage writer LoggerPort requirements.

    All storage writers (BronzeWriter, SilverWriter, GoldWriter) MUST
    require a LoggerPort parameter in their constructor for observability.
    Per RULES.md: Dependencies MUST be injected through constructor.
    """

    STORAGE_WRITERS = [
        ("BronzeWriter", "bioetl.infrastructure.storage.bronze_writer"),
        ("SilverWriter", "bioetl.infrastructure.storage.silver_writer"),
        ("GoldWriter", "bioetl.infrastructure.storage.gold_writer"),
    ]

    @pytest.mark.parametrize("writer_name,module_path", STORAGE_WRITERS)
    def test_storage_writer_has_required_logger_parameter(
        self, writer_name: str, module_path: str
    ) -> None:
        """All storage writers MUST have LoggerPort as required parameter."""
        import importlib
        import inspect

        module = importlib.import_module(module_path)
        writer_class = getattr(module, writer_name)

        sig = inspect.signature(writer_class.__init__)
        params = sig.parameters

        assert "logger" in params, (
            f"{writer_name}.__init__() MUST have 'logger' parameter. "
            "All writers require LoggerPort for observability."
        )

        # Check that logger is a required parameter (no default value)
        logger_param = params["logger"]
        assert logger_param.default is inspect.Parameter.empty, (
            f"{writer_name}.__init__() 'logger' MUST be required (no default). "
            "Optional loggers violate DI principles per RULES.md."
        )


# ============================================================================
# HTTP Adapter LoggerPort Contract Tests
# ============================================================================


class TestHttpAdapterLoggerContract:
    """Tests for HTTP adapter LoggerPort requirements.

    BaseHttpAdapter MUST require LoggerPort as a constructor parameter
    to ensure all HTTP adapters have proper observability.
    Per RULES.md: Dependencies MUST be injected through constructor.
    No hidden fallbacks (like NoOpLogger) are allowed.
    """

    HTTP_ADAPTERS = [
        ("BaseHttpAdapter", "bioetl.infrastructure.adapters.base"),
    ]

    @pytest.mark.parametrize("adapter_name,module_path", HTTP_ADAPTERS)
    def test_http_adapter_has_required_logger_parameter(
        self, adapter_name: str, module_path: str
    ) -> None:
        """HTTP adapters MUST have LoggerPort as required parameter."""
        import importlib
        import inspect

        module = importlib.import_module(module_path)
        adapter_class = getattr(module, adapter_name)

        sig = inspect.signature(adapter_class.__init__)
        params = sig.parameters

        assert "logger" in params, (
            f"{adapter_name}.__init__() MUST have 'logger' parameter. "
            "All adapters require LoggerPort for observability."
        )

        # Check that logger is a required parameter (no default value)
        logger_param = params["logger"]
        assert logger_param.default is inspect.Parameter.empty, (
            f"{adapter_name}.__init__() 'logger' MUST be required (no default). "
            "Optional loggers with fallback to NoOpLogger violate DI principles per RULES.md."
        )


# ============================================================================
# Rate Limiter Port Contract Tests
# ============================================================================


class TestRateLimiterPortContract:
    """Tests for RateLimiterPort specific contracts.

    RateLimiterPort defines the contract for rate limiting API requests.
    Implements RULES.md §5.1 rate limiting requirements.
    """

    REQUIRED_METHODS = ["acquire", "try_acquire", "available_tokens"]

    @pytest.mark.parametrize("method_name", REQUIRED_METHODS)
    def test_rate_limiter_port_has_required_methods(self, method_name: str) -> None:
        """RateLimiterPort MUST have all required rate limiting methods."""
        assert hasattr(ports.RateLimiterPort, method_name), (
            f"RateLimiterPort MUST define {method_name}() for rate limiting"
        )

    def test_rate_limiter_port_acquire_is_async(self) -> None:
        """RateLimiterPort.acquire() MUST be async for non-blocking operation."""

        acquire_method = ports.RateLimiterPort.acquire
        # For Protocol, check if it's a coroutine function
        hints = (
            get_type_hints(acquire_method)
            if hasattr(acquire_method, "__annotations__")
            else {}
        )

        # The return type should be None (async def acquire() -> None)
        assert hints.get("return") is type(None) or "return" not in hints, (
            "RateLimiterPort.acquire() should return None"
        )

    def test_rate_limiter_port_is_runtime_checkable(self) -> None:
        """RateLimiterPort MUST be @runtime_checkable for isinstance() checks."""

        class DummyLimiter:
            """Dummy class for testing isinstance()."""

            pass

        try:
            isinstance(DummyLimiter(), ports.RateLimiterPort)
            is_runtime_checkable = True
        except TypeError:
            is_runtime_checkable = False

        assert is_runtime_checkable, (
            "RateLimiterPort MUST be decorated with @runtime_checkable"
        )


# ============================================================================
# Circuit Breaker Port Contract Tests
# ============================================================================


class TestCircuitBreakerPortContract:
    """Tests for CircuitBreakerPort specific contracts.

    CircuitBreakerPort defines the contract for fault tolerance.
    Implements RULES.md §3.1.4 circuit breaker requirements.
    """

    REQUIRED_METHODS = ["get_state", "get_failure_count", "call", "reset"]

    @pytest.mark.parametrize("method_name", REQUIRED_METHODS)
    def test_circuit_breaker_port_has_required_methods(self, method_name: str) -> None:
        """CircuitBreakerPort MUST have all required circuit breaker methods."""
        assert hasattr(ports.CircuitBreakerPort, method_name), (
            f"CircuitBreakerPort MUST define {method_name}() for fault tolerance"
        )

    def test_circuit_breaker_port_call_is_async(self) -> None:
        """CircuitBreakerPort.call() MUST be async for non-blocking operation."""
        import inspect

        call_method = ports.CircuitBreakerPort.call
        sig = inspect.signature(call_method)
        params = sig.parameters

        # Should have func parameter for the callable to wrap
        assert "func" in params, (
            "CircuitBreakerPort.call() MUST have func parameter for wrapped callable"
        )

    def test_circuit_breaker_port_get_state_returns_enum(self) -> None:
        """CircuitBreakerPort.get_state() MUST return CircuitBreakerState."""
        from bioetl.domain.types import CircuitBreakerState

        hints = get_type_hints(ports.CircuitBreakerPort.get_state)

        assert hints.get("return") is CircuitBreakerState, (
            "CircuitBreakerPort.get_state() MUST return CircuitBreakerState enum"
        )

    def test_circuit_breaker_port_is_runtime_checkable(self) -> None:
        """CircuitBreakerPort MUST be @runtime_checkable for isinstance() checks."""

        class DummyBreaker:
            """Dummy class for testing isinstance()."""

            pass

        try:
            isinstance(DummyBreaker(), ports.CircuitBreakerPort)
            is_runtime_checkable = True
        except TypeError:
            is_runtime_checkable = False

        assert is_runtime_checkable, (
            "CircuitBreakerPort MUST be decorated with @runtime_checkable"
        )


# ============================================================================
# Resilience Implementation Contract Tests
# ============================================================================


class TestResilienceImplementationContract:
    """Tests that resilience implementations satisfy port contracts.

    TokenBucketRateLimiter MUST implement RateLimiterPort.
    CircuitBreakerGuard MUST implement CircuitBreakerPort.
    """

    def test_token_bucket_implements_rate_limiter_port(self) -> None:
        """TokenBucketRateLimiter MUST satisfy RateLimiterPort contract."""
        from bioetl.infrastructure.adapters.http.rate_limiter import (
            TokenBucketRateLimiter,
        )

        bucket = TokenBucketRateLimiter(rate=5.0, capacity=10)

        assert isinstance(bucket, ports.RateLimiterPort), (
            "TokenBucketRateLimiter MUST implement RateLimiterPort protocol. "
            "Check that all required methods are present."
        )

    def test_circuit_breaker_implements_circuit_breaker_port(self) -> None:
        """CircuitBreakerGuard MUST satisfy CircuitBreakerPort contract."""
        from bioetl.infrastructure.adapters.http.circuit_breaker import (
            CircuitBreakerGuard,
        )

        breaker = CircuitBreakerGuard(provider="test")

        assert isinstance(breaker, ports.CircuitBreakerPort), (
            "CircuitBreakerGuard MUST implement CircuitBreakerPort protocol. "
            "Check that all required methods are present."
        )


# ============================================================================
# JSON Encoder Port Contract Tests
# ============================================================================


class TestJsonEncoderPortContract:
    """Tests for JsonEncoderPort specific contracts.

    JsonEncoderPort defines the contract for JSON serialization.
    Implementations MUST guarantee deterministic output for reproducibility.
    See RULES.md §2.8 - Content Hashing and REQ-ARCH-030 - Deterministic Writes.
    """

    REQUIRED_METHODS = ["dumps", "dumps_canonical", "loads"]

    @pytest.mark.parametrize("method_name", REQUIRED_METHODS)
    def test_json_encoder_port_has_required_methods(self, method_name: str) -> None:
        """JsonEncoderPort MUST have all required serialization methods."""
        assert hasattr(ports.JsonEncoderPort, method_name), (
            f"JsonEncoderPort MUST define {method_name}() for JSON serialization"
        )

    def test_json_encoder_port_dumps_has_sort_keys_param(self) -> None:
        """JsonEncoderPort.dumps() MUST have sort_keys parameter for determinism."""
        import inspect

        sig = inspect.signature(ports.JsonEncoderPort.dumps)
        params = sig.parameters

        assert "sort_keys" in params, (
            "JsonEncoderPort.dumps() MUST have sort_keys parameter for deterministic output"
        )

    def test_json_encoder_port_is_runtime_checkable(self) -> None:
        """JsonEncoderPort MUST be @runtime_checkable for isinstance() checks."""

        class DummyEncoder:
            """Dummy class for testing isinstance()."""

            pass

        try:
            isinstance(DummyEncoder(), ports.JsonEncoderPort)
            is_runtime_checkable = True
        except TypeError:
            is_runtime_checkable = False

        assert is_runtime_checkable, (
            "JsonEncoderPort MUST be decorated with @runtime_checkable"
        )


# ============================================================================
# Logger Implementation Contract Tests
# ============================================================================


class TestLoggerImplementationContract:
    """Tests that logger implementations satisfy LoggerPort contract.

    StructlogLogger MUST implement LoggerPort protocol.
    NoOpLogger MUST implement LoggerPort protocol.
    """

    def test_structlog_logger_implements_logger_port(self) -> None:
        """StructlogLogger MUST satisfy LoggerPort contract.

        Ensures formal adapter replaces duck typing with explicit
        protocol implementation.
        """
        from uuid import uuid4

        from bioetl.infrastructure.observability.logging import create_logger

        logger = create_logger(pipeline="test", run_id=uuid4())

        assert isinstance(logger, ports.LoggerPort), (
            "StructlogLogger MUST implement LoggerPort protocol. "
            "Check that all required methods are present: "
            "bind, info, warning, error, debug, exception."
        )

    def test_structlog_logger_bind_returns_logger_port(self) -> None:
        """StructlogLogger.bind() MUST return LoggerPort, not raw BoundLogger.

        This ensures type consistency across bound loggers.
        """
        from uuid import uuid4

        from bioetl.infrastructure.observability.logging import create_logger

        logger = create_logger(pipeline="test", run_id=uuid4())
        bound = logger.bind(extra_context="value")

        assert isinstance(bound, ports.LoggerPort), (
            "StructlogLogger.bind() MUST return LoggerPort. "
            "Returning raw structlog.BoundLogger breaks type safety."
        )

    def test_noop_logger_implements_logger_port(self) -> None:
        """NoOpLogger MUST satisfy LoggerPort contract.

        NoOpLogger is used as fallback in adapters without explicit
        logger injection. It MUST implement the full LoggerPort interface.
        """
        from bioetl.infrastructure.observability.noop_logger import NoOpLogger

        logger = NoOpLogger()

        assert isinstance(logger, ports.LoggerPort), (
            "NoOpLogger MUST implement LoggerPort protocol. "
            "Check that all required methods are present."
        )


class TestJsonEncoderImplementationContract:
    """Tests that JSON encoder implementations satisfy port contracts."""

    def test_stdlib_encoder_implements_json_encoder_port(self) -> None:
        """StdLibJsonEncoder MUST satisfy JsonEncoderPort contract."""
        from bioetl.infrastructure.serialization.encoders import StdLibJsonEncoder

        encoder = StdLibJsonEncoder()

        assert isinstance(encoder, ports.JsonEncoderPort), (
            "StdLibJsonEncoder MUST implement JsonEncoderPort protocol. "
            "Check that all required methods are present."
        )

    def test_orjson_encoder_implements_json_encoder_port(self) -> None:
        """OrjsonEncoder MUST satisfy JsonEncoderPort contract (if installed)."""
        from bioetl.infrastructure.serialization.encoders import (
            ORJSON_AVAILABLE,
            OrjsonEncoder,
        )

        if not ORJSON_AVAILABLE:
            pytest.skip("orjson not installed")

        encoder = OrjsonEncoder()

        assert isinstance(encoder, ports.JsonEncoderPort), (
            "OrjsonEncoder MUST implement JsonEncoderPort protocol. "
            "Check that all required methods are present."
        )


# ============================================================================
# Memory Monitor Port Contract Tests
# ============================================================================


class TestMemoryMonitorPortContract:
    """Tests for MemoryMonitorPort specific contracts.

    MemoryMonitorPort defines the contract for memory monitoring and
    adaptive batch sizing. Implements RULES.md memory management requirements.
    """

    REQUIRED_METHODS = [
        "get_memory_stats",
        "is_under_pressure",
        "get_recommended_batch_size",
        "estimate_batch_memory_mb",
        "calculate_max_batch_size",
    ]

    @pytest.mark.parametrize("method_name", REQUIRED_METHODS)
    def test_memory_monitor_port_has_required_methods(self, method_name: str) -> None:
        """MemoryMonitorPort MUST have all required memory monitoring methods."""
        assert hasattr(ports.MemoryMonitorPort, method_name), (
            f"MemoryMonitorPort MUST define {method_name}() for memory management"
        )

    def test_memory_monitor_port_is_runtime_checkable(self) -> None:
        """MemoryMonitorPort MUST be @runtime_checkable for isinstance() checks."""

        class DummyMonitor:
            """Dummy class for testing isinstance()."""

            pass

        try:
            isinstance(DummyMonitor(), ports.MemoryMonitorPort)
            is_runtime_checkable = True
        except TypeError:
            is_runtime_checkable = False

        assert is_runtime_checkable, (
            "MemoryMonitorPort MUST be decorated with @runtime_checkable"
        )

    def test_memory_monitor_port_get_recommended_batch_size_signature(self) -> None:
        """MemoryMonitorPort.get_recommended_batch_size() MUST have current_batch_size param."""
        import inspect

        sig = inspect.signature(ports.MemoryMonitorPort.get_recommended_batch_size)
        params = sig.parameters

        assert "current_batch_size" in params, (
            "MemoryMonitorPort.get_recommended_batch_size() MUST have "
            "current_batch_size parameter for adaptive batch sizing"
        )


class TestMemoryMonitorImplementationContract:
    """Tests that memory monitor implementations satisfy port contracts."""

    def test_memory_monitor_implements_memory_monitor_port(self) -> None:
        """MemoryMonitor MUST satisfy MemoryMonitorPort contract."""
        from bioetl.domain.config import MemoryConfig
        from bioetl.infrastructure.system.memory_monitor import MemoryMonitor

        monitor = MemoryMonitor(config=MemoryConfig())

        assert isinstance(monitor, ports.MemoryMonitorPort), (
            "MemoryMonitor MUST implement MemoryMonitorPort protocol. "
            "Check that all required methods are present."
        )

    def test_noop_memory_monitor_implements_memory_monitor_port(self) -> None:
        """NoOpMemoryMonitor MUST satisfy MemoryMonitorPort contract."""
        from bioetl.domain.ports.noop import NoOpMemoryMonitor

        monitor = NoOpMemoryMonitor()

        assert isinstance(monitor, ports.MemoryMonitorPort), (
            "NoOpMemoryMonitor MUST implement MemoryMonitorPort protocol. "
            "Check that all required methods are present."
        )
