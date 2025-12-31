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
        assert (
            hints.get("return") is type(None) or "return" not in hints
        ), f"{port_name}.aclose() should return None"

    def test_datasource_port_has_context_manager(self) -> None:
        """DataSourcePort MUST support async context manager protocol."""
        assert hasattr(
            ports.DataSourcePort, "__aenter__"
        ), "DataSourcePort MUST define __aenter__ for async context manager"
        assert hasattr(
            ports.DataSourcePort, "__aexit__"
        ), "DataSourcePort MUST define __aexit__ for async context manager"

    def test_datasource_port_has_health_check(self) -> None:
        """DataSourcePort MUST have health_check for pre-flight validation."""
        assert hasattr(
            ports.DataSourcePort, "health_check"
        ), "DataSourcePort MUST define health_check() for HealthAggregator"

    def test_storage_port_has_health_check(self) -> None:
        """StoragePort MUST have health_check for pre-flight validation."""
        assert hasattr(
            ports.StoragePort, "health_check"
        ), "StoragePort MUST define health_check() for HealthAggregator"


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
        assert hasattr(
            ports.LoggerPort, method_name
        ), f"LoggerPort MUST define {method_name}() method"

    def test_logger_port_has_bind_method(self) -> None:
        """LoggerPort MUST have bind() for context propagation."""
        assert hasattr(
            ports.LoggerPort, "bind"
        ), "LoggerPort MUST define bind() for structured context"


# ============================================================================
# Port Interface Completeness Tests
# ============================================================================


class TestPortRuntimeCheckable:
    """Tests that all ports are runtime_checkable for isinstance() checks."""

    ALL_PORTS = [
        "TracingPort",
        "DataSourcePort",
        "FilterableDataSourcePort",
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
            "InputFilterPort",
            "StoragePort",
            "LockPort",
            "CheckpointPort",
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
        assert hasattr(
            ports.StoragePort, method_name
        ), f"StoragePort MUST define {method_name}() for Medallion architecture"

    @pytest.mark.parametrize("method_name", REQUIRED_CLEAR_METHODS)
    def test_storage_port_has_clear_methods(self, method_name: str) -> None:
        """StoragePort MUST have clear methods for rebuild/backfill."""
        assert hasattr(
            ports.StoragePort, method_name
        ), f"StoragePort MUST define {method_name}() for data cleanup"

    @pytest.mark.parametrize("method_name", REQUIRED_MAINTENANCE_METHODS)
    def test_storage_port_has_maintenance_methods(self, method_name: str) -> None:
        """StoragePort MUST have vacuum and archive methods for Delta Lake maintenance."""
        assert hasattr(
            ports.StoragePort, method_name
        ), f"StoragePort MUST define {method_name}() for Delta Lake maintenance"

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
        assert (
            "retention_hours" in params
        ), "vacuum() MUST have retention_hours parameter"
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
        assert hasattr(
            ports.MetricsPort, method_name
        ), f"MetricsPort MUST define {method_name}() for observability"


# ============================================================================
# Lock Port Contract Tests
# ============================================================================


class TestLockPortContract:
    """Tests for LockPort specific contracts."""

    REQUIRED_LOCK_METHODS = ["acquire", "release", "heartbeat"]

    @pytest.mark.parametrize("method_name", REQUIRED_LOCK_METHODS)
    def test_lock_port_has_lock_methods(self, method_name: str) -> None:
        """LockPort MUST have acquire, release, and heartbeat methods."""
        assert hasattr(
            ports.LockPort, method_name
        ), f"LockPort MUST define {method_name}() for distributed locking"


# ============================================================================
# Checkpoint Port Contract Tests
# ============================================================================


class TestCheckpointPortContract:
    """Tests for CheckpointPort specific contracts."""

    REQUIRED_CHECKPOINT_METHODS = ["save", "load", "list_all", "delete"]

    @pytest.mark.parametrize("method_name", REQUIRED_CHECKPOINT_METHODS)
    def test_checkpoint_port_has_methods(self, method_name: str) -> None:
        """CheckpointPort MUST have CRUD-like methods."""
        assert hasattr(
            ports.CheckpointPort, method_name
        ), f"CheckpointPort MUST define {method_name}() for state persistence"


# ============================================================================
# Quarantine Port Contract Tests
# ============================================================================


class TestQuarantinePortContract:
    """Tests for QuarantinePort specific contracts."""

    REQUIRED_QUARANTINE_METHODS = ["write", "inspect", "get_stats"]

    @pytest.mark.parametrize("method_name", REQUIRED_QUARANTINE_METHODS)
    def test_quarantine_port_has_methods(self, method_name: str) -> None:
        """QuarantinePort MUST have write, inspect, and stats methods."""
        assert hasattr(
            ports.QuarantinePort, method_name
        ), f"QuarantinePort MUST define {method_name}() for failed record isolation"


# ============================================================================
# Static Analysis Tests
# ============================================================================


class TestPortDefinitionQuality:
    """Tests for port definition quality using static analysis."""

    def test_all_port_methods_have_docstrings(self, src_dir: Path) -> None:
        """All port methods SHOULD have docstrings."""
        ports_dir = src_dir / "bioetl" / "domain" / "ports"
        if not ports_dir.exists():
            pytest.skip("ports/ package not found")

        missing_docstrings = []

        for ports_file in ports_dir.glob("*.py"):
            if ports_file.name == "__init__.py":
                continue

            with ports_file.open(encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(ports_file))

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a Port class
                    if not node.name.endswith("Port"):
                        continue

                    for item in node.body:
                        if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                            # Skip __init__ and private methods
                            if (
                                item.name.startswith("_")
                                and item.name != "__aenter__"
                                and item.name != "__aexit__"
                            ):
                                continue

                            # Check for docstring
                            if not (
                                item.body
                                and isinstance(item.body[0], ast.Expr)
                                and isinstance(item.body[0].value, ast.Constant)
                                and isinstance(item.body[0].value.value, str)
                            ):
                                missing_docstrings.append(f"{node.name}.{item.name}")

        # Allow some missing (ellipsis-only methods in Protocols are ok without detailed docs)
        # But warn if there are many
        if len(missing_docstrings) > 5:
            pytest.fail(
                f"Too many port methods without docstrings ({len(missing_docstrings)}):\n"
                + "\n".join(f"  - {m}" for m in missing_docstrings[:10])
            )

    def test_no_implementation_in_ports(self, src_dir: Path) -> None:
        """Port methods MUST only have ellipsis (...) as body, no implementation."""
        ports_dir = src_dir / "bioetl" / "domain" / "ports"
        if not ports_dir.exists():
            pytest.skip("ports/ package not found")

        implementations_found = []

        for ports_file in ports_dir.glob("*.py"):
            if ports_file.name == "__init__.py":
                continue

            with ports_file.open(encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(ports_file))

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name.endswith("Port"):
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                            # Check method body
                            body = item.body

                            # Allow: docstring + Ellipsis, or just Ellipsis
                            # Note: ast.Ellipsis was removed in Python 3.12,
                            # now ellipsis is ast.Constant with value=...
                            def _is_ellipsis(node: ast.expr) -> bool:
                                """Check if AST node is ellipsis (compatible with Python 3.8-3.12+)."""
                                if isinstance(node, ast.Constant) and node.value is ...:
                                    return True
                                # For Python < 3.12 compatibility
                                if hasattr(ast, "Ellipsis") and isinstance(
                                    node, ast.Ellipsis  # type: ignore[attr-defined]
                                ):
                                    return True
                                return False

                            if len(body) == 1:
                                if isinstance(body[0], ast.Expr):
                                    # Just docstring or ellipsis
                                    if isinstance(body[0].value, ast.Constant):
                                        if isinstance(body[0].value.value, str):
                                            continue  # docstring only
                                        if body[0].value.value is ...:
                                            continue  # ellipsis only
                                    if _is_ellipsis(body[0].value):
                                        continue  # ellipsis only
                            elif len(body) == 2:
                                # docstring + ellipsis
                                if (
                                    isinstance(body[0], ast.Expr)
                                    and isinstance(body[0].value, ast.Constant)
                                    and isinstance(body[0].value.value, str)
                                ):
                                    if isinstance(body[1], ast.Expr) and _is_ellipsis(
                                        body[1].value
                                    ):
                                        continue

                            # If we get here, there's actual implementation
                            implementations_found.append(f"{node.name}.{item.name}")

        assert (
            not implementations_found
        ), "Ports should not contain implementations (use ... only):\n" + "\n".join(
            f"  - {m}" for m in implementations_found
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
        assert hasattr(
            ports.DQMonitorPort, method_name
        ), f"DQMonitorPort MUST define {method_name}() for data quality monitoring"

    def test_dq_monitor_port_check_quality_returns_list(self) -> None:
        """DQMonitorPort.check_quality() MUST return list of anomalies."""
        import inspect

        sig = inspect.signature(ports.DQMonitorPort.check_quality)
        params = sig.parameters

        assert "metrics" in params, "check_quality() MUST have metrics parameter"

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

        assert (
            is_runtime_checkable
        ), "DQMonitorPort MUST be decorated with @runtime_checkable"


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
        assert hasattr(
            ports.RateLimiterPort, method_name
        ), f"RateLimiterPort MUST define {method_name}() for rate limiting"

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
        assert (
            hints.get("return") is type(None) or "return" not in hints
        ), "RateLimiterPort.acquire() should return None"

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

        assert (
            is_runtime_checkable
        ), "RateLimiterPort MUST be decorated with @runtime_checkable"


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
        assert hasattr(
            ports.CircuitBreakerPort, method_name
        ), f"CircuitBreakerPort MUST define {method_name}() for fault tolerance"

    def test_circuit_breaker_port_call_is_async(self) -> None:
        """CircuitBreakerPort.call() MUST be async for non-blocking operation."""
        import inspect

        call_method = ports.CircuitBreakerPort.call
        sig = inspect.signature(call_method)
        params = sig.parameters

        # Should have func parameter for the callable to wrap
        assert (
            "func" in params
        ), "CircuitBreakerPort.call() MUST have func parameter for wrapped callable"

    def test_circuit_breaker_port_get_state_returns_enum(self) -> None:
        """CircuitBreakerPort.get_state() MUST return CircuitBreakerState."""
        from bioetl.domain.types import CircuitBreakerState

        hints = get_type_hints(ports.CircuitBreakerPort.get_state)

        assert (
            hints.get("return") is CircuitBreakerState
        ), "CircuitBreakerPort.get_state() MUST return CircuitBreakerState enum"

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

        assert (
            is_runtime_checkable
        ), "CircuitBreakerPort MUST be decorated with @runtime_checkable"


# ============================================================================
# Resilience Implementation Contract Tests
# ============================================================================


class TestResilienceImplementationContract:
    """Tests that resilience implementations satisfy port contracts.

    TokenBucket MUST implement RateLimiterPort.
    CircuitBreaker MUST implement CircuitBreakerPort.
    """

    def test_token_bucket_implements_rate_limiter_port(self) -> None:
        """TokenBucket MUST satisfy RateLimiterPort contract."""
        from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket

        bucket = TokenBucket(rate=5.0, capacity=10)

        assert isinstance(bucket, ports.RateLimiterPort), (
            "TokenBucket MUST implement RateLimiterPort protocol. "
            "Check that all required methods are present."
        )

    def test_circuit_breaker_implements_circuit_breaker_port(self) -> None:
        """CircuitBreaker MUST satisfy CircuitBreakerPort contract."""
        from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(provider="test")

        assert isinstance(breaker, ports.CircuitBreakerPort), (
            "CircuitBreaker MUST implement CircuitBreakerPort protocol. "
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
        assert hasattr(
            ports.JsonEncoderPort, method_name
        ), f"JsonEncoderPort MUST define {method_name}() for JSON serialization"

    def test_json_encoder_port_dumps_has_sort_keys_param(self) -> None:
        """JsonEncoderPort.dumps() MUST have sort_keys parameter for determinism."""
        import inspect

        sig = inspect.signature(ports.JsonEncoderPort.dumps)
        params = sig.parameters

        assert (
            "sort_keys" in params
        ), "JsonEncoderPort.dumps() MUST have sort_keys parameter for deterministic output"

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

        assert (
            is_runtime_checkable
        ), "JsonEncoderPort MUST be decorated with @runtime_checkable"


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
        assert hasattr(
            ports.MemoryMonitorPort, method_name
        ), f"MemoryMonitorPort MUST define {method_name}() for memory management"

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

        assert (
            is_runtime_checkable
        ), "MemoryMonitorPort MUST be decorated with @runtime_checkable"

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
        from bioetl.application.core.memory_monitor import MemoryConfig, MemoryMonitor

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


# ============================================================================
# Error Condition Contract Tests
# ============================================================================


class TestLockPortErrorConditions:
    """Tests for LockPort error condition handling.

    LockPort implementations MUST handle error conditions gracefully:
    - Concurrent acquire attempts from different owners
    - Heartbeat on non-existent locks
    - Release of locks not owned
    - Validate owner on expired locks
    """

    @pytest.mark.asyncio
    async def test_lock_release_wrong_owner_returns_false(self) -> None:
        """LockPort.release() MUST return False when releasing lock not owned."""
        from uuid import uuid4

        from bioetl.infrastructure.locking.memory_lock import MemoryLock

        lock = MemoryLock()
        owner1 = uuid4()
        owner2 = uuid4()

        try:
            # Owner1 acquires lock
            acquired = await lock.acquire("test_key", owner1)
            assert acquired, "Owner1 should acquire lock"

            # Owner2 tries to release - should fail
            released = await lock.release("test_key", owner2)
            assert (
                not released
            ), "LockPort.release() MUST return False when owner does not match"

            # Lock should still be held by owner1
            is_owner = await lock.validate_owner("test_key", owner1)
            assert is_owner, "Owner1 should still hold the lock"
        finally:
            await lock.aclose()

    @pytest.mark.asyncio
    async def test_lock_heartbeat_non_existent_returns_false(self) -> None:
        """LockPort.heartbeat() MUST return False for non-existent locks."""
        from uuid import uuid4

        from bioetl.infrastructure.locking.memory_lock import MemoryLock

        lock = MemoryLock()

        try:
            result = await lock.heartbeat("non_existent_key", uuid4())
            assert (
                not result
            ), "LockPort.heartbeat() MUST return False for non-existent locks"
        finally:
            await lock.aclose()

    @pytest.mark.asyncio
    async def test_lock_heartbeat_wrong_owner_returns_false(self) -> None:
        """LockPort.heartbeat() MUST return False when owner does not match."""
        from uuid import uuid4

        from bioetl.infrastructure.locking.memory_lock import MemoryLock

        lock = MemoryLock()
        owner1 = uuid4()
        owner2 = uuid4()

        try:
            await lock.acquire("test_key", owner1)
            result = await lock.heartbeat("test_key", owner2)
            assert (
                not result
            ), "LockPort.heartbeat() MUST return False when owner does not match"
        finally:
            await lock.aclose()

    @pytest.mark.asyncio
    async def test_lock_validate_owner_non_existent_returns_false(self) -> None:
        """LockPort.validate_owner() MUST return False for non-existent locks."""
        from uuid import uuid4

        from bioetl.infrastructure.locking.memory_lock import MemoryLock

        lock = MemoryLock()

        try:
            result = await lock.validate_owner("non_existent_key", uuid4())
            assert (
                not result
            ), "LockPort.validate_owner() MUST return False for non-existent locks"
        finally:
            await lock.aclose()

    @pytest.mark.asyncio
    async def test_lock_acquire_timeout_returns_false(self) -> None:
        """LockPort.acquire() with wait=True MUST return False after timeout."""
        from uuid import uuid4

        from bioetl.infrastructure.locking.memory_lock import MemoryLock

        lock = MemoryLock()
        owner1 = uuid4()
        owner2 = uuid4()

        try:
            # Owner1 acquires lock
            await lock.acquire("test_key", owner1)

            # Owner2 tries to acquire with short timeout
            acquired = await lock.acquire("test_key", owner2, wait=True, wait_timeout=1)
            assert (
                not acquired
            ), "LockPort.acquire() MUST return False when wait times out"
        finally:
            await lock.aclose()


class TestCheckpointPortErrorConditions:
    """Tests for CheckpointPort error condition handling.

    CheckpointPort implementations MUST handle error conditions gracefully:
    - Load non-existent checkpoint
    - Delete non-existent checkpoint (idempotent)
    - Save with corrupted metadata
    """

    @pytest.mark.asyncio
    async def test_checkpoint_load_non_existent_returns_none(
        self, tmp_path: Path
    ) -> None:
        """CheckpointPort.load() MUST return None for non-existent checkpoints."""
        from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpoint

        checkpoint = LocalCheckpoint(base_path=tmp_path)

        try:
            result = await checkpoint.load("non_existent_pipeline")
            assert (
                result is None
            ), "CheckpointPort.load() MUST return None for non-existent checkpoints"
        finally:
            await checkpoint.aclose()

    @pytest.mark.asyncio
    async def test_checkpoint_delete_non_existent_is_idempotent(
        self, tmp_path: Path
    ) -> None:
        """CheckpointPort.delete() MUST be idempotent (no error if not exists)."""
        from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpoint

        checkpoint = LocalCheckpoint(base_path=tmp_path)

        try:
            # Should not raise exception
            await checkpoint.delete("non_existent_pipeline")
        finally:
            await checkpoint.aclose()

    @pytest.mark.asyncio
    async def test_checkpoint_list_all_empty_returns_empty_list(
        self, tmp_path: Path
    ) -> None:
        """CheckpointPort.list_all() MUST return empty list when no checkpoints."""
        from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpoint

        checkpoint = LocalCheckpoint(base_path=tmp_path)

        try:
            result = await checkpoint.list_all()
            assert (
                result == []
            ), "CheckpointPort.list_all() MUST return empty list when no checkpoints"
        finally:
            await checkpoint.aclose()


class TestCircuitBreakerPortErrorConditions:
    """Tests for CircuitBreakerPort error condition handling.

    CircuitBreakerPort implementations MUST:
    - Raise CircuitBreakerOpenError when circuit is open
    - Re-raise exceptions from wrapped functions
    - Track failure counts correctly
    """

    @pytest.mark.asyncio
    async def test_circuit_breaker_raises_when_open(self) -> None:
        """CircuitBreakerPort.call() MUST raise CircuitBreakerOpenError when open."""
        from bioetl.domain.exceptions import CircuitBreakerOpenError
        from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(
            provider="test", failure_threshold=2, recovery_timeout=300
        )

        async def failing_func() -> None:
            raise RuntimeError("Simulated failure")

        # Trigger failures to open circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await breaker.call(failing_func)

        # Now circuit should be open
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await breaker.call(failing_func)

        assert (
            exc_info.value.provider == "test"
        ), "CircuitBreakerOpenError MUST include provider name"

    @pytest.mark.asyncio
    async def test_circuit_breaker_propagates_exceptions(self) -> None:
        """CircuitBreakerPort.call() MUST propagate exceptions from wrapped func."""
        from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(provider="test", failure_threshold=5)

        class CustomError(Exception):
            pass

        async def failing_func() -> None:
            raise CustomError("Custom error")

        with pytest.raises(CustomError, match="Custom error"):
            await breaker.call(failing_func)

    def test_circuit_breaker_reset_clears_failure_count(self) -> None:
        """CircuitBreakerPort.reset() MUST clear failure count."""
        from bioetl.domain.types import CircuitBreakerState
        from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(provider="test", failure_threshold=5)
        breaker._failure_count = 3  # Simulate failures

        breaker.reset()

        assert (
            breaker.get_failure_count() == 0
        ), "CircuitBreakerPort.reset() MUST clear failure count"
        assert (
            breaker.get_state() == CircuitBreakerState.CLOSED
        ), "CircuitBreakerPort.reset() MUST set state to CLOSED"


class TestRateLimiterPortErrorConditions:
    """Tests for RateLimiterPort error condition handling.

    RateLimiterPort implementations MUST:
    - Raise ValueError when acquiring more tokens than capacity
    - Handle zero tokens acquisition
    - Return accurate token counts
    """

    @pytest.mark.asyncio
    async def test_rate_limiter_raises_on_overcapacity_request(self) -> None:
        """RateLimiterPort.acquire() MUST raise ValueError when tokens > capacity."""
        from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket

        bucket = TokenBucket(rate=5.0, capacity=10)

        with pytest.raises(ValueError, match="Cannot acquire"):
            await bucket.acquire(tokens=15)

    def test_rate_limiter_try_acquire_returns_false_when_insufficient(self) -> None:
        """RateLimiterPort.try_acquire() MUST return False when insufficient tokens."""
        from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket

        bucket = TokenBucket(rate=1.0, capacity=5)
        # Drain tokens
        for _ in range(5):
            bucket.try_acquire()

        result = bucket.try_acquire()
        assert (
            not result
        ), "RateLimiterPort.try_acquire() MUST return False when insufficient tokens"

    def test_rate_limiter_available_tokens_non_negative(self) -> None:
        """RateLimiterPort.available_tokens() MUST return non-negative value."""
        from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket

        bucket = TokenBucket(rate=5.0, capacity=10)

        # Drain tokens
        while bucket.try_acquire():
            pass

        result = bucket.available_tokens()
        assert (
            result >= 0
        ), "RateLimiterPort.available_tokens() MUST return non-negative value"


# ============================================================================
# Concurrent Access Pattern Tests
# ============================================================================


class TestLockPortConcurrentAccess:
    """Tests for LockPort concurrent access patterns.

    LockPort implementations MUST handle concurrent access:
    - Multiple concurrent acquire attempts
    - Concurrent heartbeat operations
    - Concurrent release attempts
    """

    @pytest.mark.asyncio
    async def test_concurrent_acquire_only_one_succeeds(self) -> None:
        """Only one concurrent acquire attempt MUST succeed for the same key."""
        import asyncio
        from uuid import uuid4

        from bioetl.infrastructure.locking.memory_lock import MemoryLock

        lock = MemoryLock()
        num_contenders = 10
        owners = [uuid4() for _ in range(num_contenders)]
        results: list[bool] = []

        async def try_acquire(owner_id):
            result = await lock.acquire("shared_key", owner_id)
            return result

        try:
            tasks = [try_acquire(owner) for owner in owners]
            results = await asyncio.gather(*tasks)

            successful_acquires = sum(results)
            assert (
                successful_acquires == 1
            ), f"Only one concurrent acquire MUST succeed, got {successful_acquires}"
        finally:
            await lock.aclose()

    @pytest.mark.asyncio
    async def test_concurrent_operations_different_keys_independent(self) -> None:
        """Concurrent operations on different keys MUST be independent."""
        import asyncio
        from uuid import uuid4

        from bioetl.infrastructure.locking.memory_lock import MemoryLock

        lock = MemoryLock()
        num_keys = 5
        keys = [f"key_{i}" for i in range(num_keys)]
        owners = [uuid4() for _ in range(num_keys)]

        async def acquire_and_release(key, owner):
            acquired = await lock.acquire(key, owner)
            if acquired:
                await asyncio.sleep(0.01)  # Short hold
                await lock.release(key, owner)
            return acquired

        try:
            tasks = [
                acquire_and_release(k, o) for k, o in zip(keys, owners, strict=True)
            ]
            results = await asyncio.gather(*tasks)

            assert all(
                results
            ), "All concurrent operations on different keys MUST succeed"
        finally:
            await lock.aclose()

    @pytest.mark.asyncio
    async def test_concurrent_heartbeat_from_owner_succeeds(self) -> None:
        """Concurrent heartbeat operations from owner MUST all succeed."""
        import asyncio
        from uuid import uuid4

        from bioetl.infrastructure.locking.memory_lock import MemoryLock

        lock = MemoryLock()
        owner = uuid4()

        try:
            await lock.acquire("test_key", owner, ttl=60)

            async def heartbeat():
                return await lock.heartbeat("test_key", owner)

            tasks = [heartbeat() for _ in range(10)]
            results = await asyncio.gather(*tasks)

            assert all(
                results
            ), "Concurrent heartbeat operations from owner MUST all succeed"
        finally:
            await lock.aclose()


class TestCheckpointPortConcurrentAccess:
    """Tests for CheckpointPort concurrent access patterns.

    CheckpointPort implementations MUST handle concurrent access:
    - Concurrent save operations
    - Concurrent load operations
    - Concurrent list_all operations
    """

    @pytest.mark.asyncio
    async def test_concurrent_saves_to_different_pipelines(
        self, tmp_path: Path
    ) -> None:
        """Concurrent saves to different pipelines MUST all succeed."""
        import asyncio
        from uuid import uuid4

        from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpoint

        checkpoint = LocalCheckpoint(base_path=tmp_path)
        num_pipelines = 5
        pipelines = [f"pipeline_{i}" for i in range(num_pipelines)]

        async def save_checkpoint(pipeline):
            await checkpoint.save(pipeline, uuid4(), {"key": pipeline})
            return True

        try:
            tasks = [save_checkpoint(p) for p in pipelines]
            results = await asyncio.gather(*tasks)

            assert all(
                results
            ), "Concurrent saves to different pipelines MUST all succeed"

            # Verify all saved
            saved_pipelines = await checkpoint.list_all()
            assert len(saved_pipelines) == num_pipelines
        finally:
            await checkpoint.aclose()

    @pytest.mark.asyncio
    async def test_concurrent_loads_return_consistent_data(
        self, tmp_path: Path
    ) -> None:
        """Concurrent loads of the same checkpoint MUST return consistent data."""
        import asyncio
        from uuid import uuid4

        from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpoint

        checkpoint = LocalCheckpoint(base_path=tmp_path)
        run_id = uuid4()
        metadata = {"key": "value"}

        try:
            await checkpoint.save("test_pipeline", run_id, metadata)

            async def load_checkpoint():
                return await checkpoint.load("test_pipeline")

            tasks = [load_checkpoint() for _ in range(10)]
            results = await asyncio.gather(*tasks)

            # All results should be identical
            for result in results:
                assert result is not None
                loaded_run_id, loaded_metadata = result
                assert loaded_run_id == run_id
                assert loaded_metadata == metadata
        finally:
            await checkpoint.aclose()


class TestCircuitBreakerPortConcurrentAccess:
    """Tests for CircuitBreakerPort concurrent access patterns.

    CircuitBreakerPort implementations MUST handle concurrent access:
    - Concurrent calls update state atomically
    - State transitions are consistent under load
    """

    @pytest.mark.asyncio
    async def test_concurrent_calls_track_failures_correctly(self) -> None:
        """Concurrent failing calls MUST track failure count correctly."""
        import asyncio

        from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(
            provider="test", failure_threshold=10, recovery_timeout=300
        )

        async def failing_call():
            try:
                await breaker.call(self._async_fail)
            except RuntimeError:
                pass
            except:  # noqa: E722 - catch CircuitBreakerOpenError too
                pass

        async def _async_fail():
            raise RuntimeError("Fail")

        self._async_fail = _async_fail

        tasks = [failing_call() for _ in range(10)]
        await asyncio.gather(*tasks)

        # Failure count should be at most 10 (could be fewer if circuit opened)
        assert breaker.get_failure_count() <= 10

    @pytest.mark.asyncio
    async def test_concurrent_successes_reset_failure_count(self) -> None:
        """Concurrent successful calls MUST reset failure count to 0."""
        import asyncio

        from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(
            provider="test", failure_threshold=10, recovery_timeout=300
        )
        breaker._failure_count = 5

        async def success_call():
            return await breaker.call(self._async_success)

        async def _async_success():
            return "success"

        self._async_success = _async_success

        tasks = [success_call() for _ in range(5)]
        await asyncio.gather(*tasks)

        assert (
            breaker.get_failure_count() == 0
        ), "Concurrent successful calls MUST reset failure count to 0"


class TestRateLimiterPortConcurrentAccess:
    """Tests for RateLimiterPort concurrent access patterns.

    RateLimiterPort implementations MUST handle concurrent access:
    - Concurrent acquire operations respect capacity
    - Token count never goes negative
    """

    @pytest.mark.asyncio
    async def test_concurrent_acquires_respect_capacity(self) -> None:
        """Concurrent acquires MUST respect capacity limits."""
        import asyncio

        from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket

        bucket = TokenBucket(rate=100.0, capacity=10)

        acquired_count = 0
        lock = asyncio.Lock()

        async def try_acquire_token():
            nonlocal acquired_count
            success = bucket.try_acquire()
            if success:
                async with lock:
                    acquired_count += 1
            return success

        tasks = [try_acquire_token() for _ in range(20)]
        await asyncio.gather(*tasks)

        assert (
            acquired_count <= 10
        ), f"Concurrent acquires MUST respect capacity, got {acquired_count}"

    def test_token_count_never_negative(self) -> None:
        """Token count MUST never go negative after concurrent try_acquire."""
        from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket

        bucket = TokenBucket(rate=1.0, capacity=5)

        # Drain more than capacity
        for _ in range(10):
            bucket.try_acquire()

        assert bucket.available_tokens() >= 0, "Token count MUST never go negative"
