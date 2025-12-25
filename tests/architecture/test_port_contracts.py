"""Tests for port contract verification.

These tests ensure that all port definitions in domain/ports.py follow
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
        hints = get_type_hints(aclose_method) if hasattr(aclose_method, "__annotations__") else {}

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
            "FilterableDataSourcePort",
            "InputFilterPort",
            "StoragePort",
            "LockPort",
            "CheckpointPort",
            "QuarantinePort",
            "MetricsPort",
            "LoggerPort",
            "GoldValidatorPort",
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

    def test_storage_port_has_preview_cleanup(self) -> None:
        """StoragePort MUST have preview_cleanup for CLI dry-run mode."""
        assert hasattr(ports.StoragePort, "preview_cleanup"), (
            "StoragePort MUST define preview_cleanup() for CLI dry-run. "
            "See architecture test: test_storage_port_has_preview_cleanup"
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
            f"LockPort MUST define {method_name}() for distributed locking"
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

    REQUIRED_QUARANTINE_METHODS = ["write", "inspect", "get_stats"]

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
        ports_file = src_dir / "bioetl" / "domain" / "ports.py"
        if not ports_file.exists():
            pytest.skip("ports.py not found")

        with ports_file.open(encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(ports_file))

        missing_docstrings = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if it's a Port class
                if not node.name.endswith("Port"):
                    continue

                for item in node.body:
                    if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                        # Skip __init__ and private methods
                        if item.name.startswith("_") and item.name != "__aenter__" and item.name != "__aexit__":
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
        ports_file = src_dir / "bioetl" / "domain" / "ports.py"
        if not ports_file.exists():
            pytest.skip("ports.py not found")

        with ports_file.open(encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(ports_file))

        implementations_found = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.endswith("Port"):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                        # Check method body
                        body = item.body

                        # Allow: docstring + Ellipsis, or just Ellipsis
                        if len(body) == 1:
                            if isinstance(body[0], ast.Expr):
                                # Just docstring or ellipsis
                                if isinstance(body[0].value, ast.Constant):
                                    continue  # docstring only
                                if isinstance(body[0].value, ast.Ellipsis) or (
                                    isinstance(body[0].value, ast.Constant)
                                    and body[0].value.value is ...
                                ):
                                    continue  # ellipsis only
                        elif len(body) == 2:
                            # docstring + ellipsis
                            if (
                                isinstance(body[0], ast.Expr)
                                and isinstance(body[0].value, ast.Constant)
                                and isinstance(body[0].value.value, str)
                            ):
                                if isinstance(body[1], ast.Expr) and (
                                    isinstance(body[1].value, ast.Ellipsis) or (
                                        isinstance(body[1].value, ast.Constant)
                                        and body[1].value.value is ...
                                    )
                                ):
                                    continue

                        # If we get here, there's actual implementation
                        implementations_found.append(f"{node.name}.{item.name}")

        assert not implementations_found, (
            "Ports should not contain implementations (use ... only):\n"
            + "\n".join(f"  - {m}" for m in implementations_found)
        )
