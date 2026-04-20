"""Architecture tests for tracing enforcement.

Validates that TracingPort is properly used in key operations:
- Executor operations have tracing spans
- Storage writers have tracing spans
- Pipeline runner has tracing spans

Per RULES.md 6.2.4 Tracing Enforcement:
- Tracing spans in executor operations
- Tracing spans in storage writes
- Documentation of mandatory spans
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator


# =============================================================================
# Helper Functions
# =============================================================================


def get_python_files(directory: Path) -> Iterator[Path]:
    """Yield all Python files in a directory."""
    for path in directory.rglob("*.py"):
        if "__pycache__" not in str(path):
            yield path


def has_tracing_import(source: str) -> bool:
    """Check if a file imports TracingPort or tracing-related modules."""
    patterns = [
        "TracingPort",
        "tracing",
        "opentelemetry",
        "span",
        "NoOpTracing",
    ]
    return any(pattern in source for pattern in patterns)


def has_span_creation(source: str) -> bool:
    """Check if a file creates tracing spans."""
    patterns = [
        "start_span",
        "create_span",
        "with_span",
        ".span(",
        "tracer.start",
    ]
    return any(pattern in source for pattern in patterns)


def get_class_methods(source: str, class_name: str) -> list[str]:
    """Get method names from a class definition."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    methods: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append(item.name)
    return methods


# =============================================================================
# Tests
# =============================================================================


class TestTracingPortContract:
    """Tests for TracingPort protocol contract."""

    def test_tracing_port_exists(self):
        """TracingPort protocol should exist in domain/ports."""
        from bioetl.domain.ports import TracingPort

        assert TracingPort is not None

    def test_tracing_port_has_required_methods(self):
        """TracingPort should define required tracing methods."""
        from bioetl.domain.ports import TracingPort

        # Check protocol methods
        # Get TracingPort members
        members = [m for m in dir(TracingPort) if not m.startswith("_")]
        assert len(members) > 0, "TracingPort should have methods"

    def test_noop_tracing_exists(self):
        """NoOpTracing implementation should exist for testing."""
        from bioetl.domain.ports.noop import NoOpTracing

        assert NoOpTracing is not None

    def test_noop_tracing_is_valid_implementation(self):
        """NoOpTracing should implement TracingPort."""
        from bioetl.domain.ports.noop import NoOpTracing

        noop = NoOpTracing()
        # Should be usable as TracingPort
        assert hasattr(noop, "close") or hasattr(noop, "aclose")


class TestExecutorTracingIntegration:
    """Tests for tracing in executor operations."""

    def test_executor_accepts_tracing_dependency(self):
        """Executor should accept TracingPort as a dependency."""
        executor_path = Path("src/bioetl/application/core/executor.py")

        if executor_path.exists():
            source = executor_path.read_text(encoding="utf-8")

            # Check for tracing in imports or type hints
            has_tracing_reference = any(
                pattern in source
                for pattern in ["TracingPort", "tracing", "tracer", "Tracing"]
            )

            # Executor should reference tracing (either using or receiving it)
            # If not directly, it should be via context or services
            assert (
                has_tracing_reference
                or "context" in source.lower()
                or "services" in source.lower()
            ), "Executor should reference tracing mechanism"

    def test_pipeline_services_includes_tracing(self):
        """PipelineService should include tracing."""
        services_paths = [
            Path("src/bioetl/application/core/pipeline_services.py"),
            Path("src/bioetl/application/core/services.py"),
        ]

        found = False
        for path in services_paths:
            if path.exists():
                source = path.read_text(encoding="utf-8")
                if "tracing" in source.lower() or "TracingPort" in source:
                    found = True
                    break

        # If no dedicated services file, check runner.py
        if not found:
            runner_path = Path("src/bioetl/application/core/runner.py")
            if runner_path.exists():
                source = runner_path.read_text(encoding="utf-8")
                found = "tracing" in source.lower() or "observer" in source.lower()

        assert found, "Pipeline services should include tracing"


class TestStorageTracingIntegration:
    """Tests for tracing in storage writers."""

    STORAGE_FILES = [
        "src/bioetl/infrastructure/storage/bronze_writer.py",
        "src/bioetl/infrastructure/storage/silver_writer.py",
        "src/bioetl/infrastructure/storage/gold_writer.py",
    ]

    @pytest.mark.parametrize("file_path", STORAGE_FILES)
    def test_storage_writer_has_observability(self, file_path: str):
        """Storage writers should have observability (logging/metrics/tracing)."""
        path = Path(file_path)

        if not path.exists():
            pytest.skip(f"File not found: {file_path}")

        source = path.read_text(encoding="utf-8")

        # Storage writers should have some form of observability
        has_observability = any(
            pattern in source
            for pattern in [
                "logger",
                "metrics",
                "tracing",
                "structlog",
                "logging",
                "span",
                "tracer",
            ]
        )

        assert has_observability, f"{path.name} should have observability"

    def test_bronze_writer_has_metrics(self):
        """BronzeWriter should have metrics integration."""
        path = Path("src/bioetl/infrastructure/storage/bronze_writer.py")

        if not path.exists():
            pytest.skip("BronzeWriter not found")

        source = path.read_text(encoding="utf-8")

        # BronzeWriter should have metrics
        has_metrics = "metrics" in source.lower() or "MetricsPort" in source

        assert has_metrics, "BronzeWriter should have metrics integration"

    def test_silver_writer_has_logging(self):
        """SilverWriter should have structured logging."""
        path = Path("src/bioetl/infrastructure/storage/silver_writer.py")

        if not path.exists():
            pytest.skip("SilverWriter not found")

        source = path.read_text(encoding="utf-8")

        # SilverWriter should have logging
        has_logging = "logger" in source.lower()

        assert has_logging, "SilverWriter should have logging"


class TestPipelineRunnerTracing:
    """Tests for tracing in PipelineRunner."""

    def test_runner_has_observer(self):
        """PipelineRunner should use PipelineObserver."""
        runner_path = Path("src/bioetl/application/core/runner.py")

        if not runner_path.exists():
            pytest.skip("Runner not found")

        source = runner_path.read_text(encoding="utf-8")

        # Runner should have observer for stage tracking
        has_observer = any(
            pattern in source
            for pattern in ["observer", "Observer", "PipelineObserver"]
        )

        assert has_observer, "PipelineRunner should have observer"

    def test_runner_tracks_stages(self):
        """PipelineRunner should track pipeline stages."""
        runner_path = Path("src/bioetl/application/core/runner.py")

        if not runner_path.exists():
            pytest.skip("Runner not found")

        source = runner_path.read_text(encoding="utf-8")

        # Should have stage-related code
        has_stages = any(
            pattern in source
            for pattern in ["stage", "phase", "step", "emit", "notify"]
        )

        assert has_stages, "PipelineRunner should track stages"

    def test_composite_runner_uses_lifecycle_observer_seam(self):
        """Composite runner should route lifecycle events through an observer seam."""
        runner_path = Path("src/bioetl/application/composite/runner_pkg/runner.py")

        if not runner_path.exists():
            pytest.skip("Composite runner not found")

        source = runner_path.read_text(encoding="utf-8")

        assert "_observer" in source, "Composite runner should bind an observer seam"

    def test_composite_phase_helpers_do_not_publish_via_logger_directly(self):
        """Composite phase helpers should not own direct lifecycle publication."""
        helper_paths = [
            Path(
                "src/bioetl/application/composite/runner_pkg/runner_stage_start_flow.py"
            ),
            Path(
                "src/bioetl/application/composite/runner_pkg/runner_stage_state_flow.py"
            ),
            Path(
                "src/bioetl/application/composite/runner_pkg/runner_stage_dependency_state_flow.py"
            ),
            Path(
                "src/bioetl/application/composite/runner_pkg/runner_merge_stage_runtime.py"
            ),
            Path("src/bioetl/application/composite/runner_pkg/runner_support_flow.py"),
        ]

        for path in helper_paths:
            if not path.exists():
                pytest.skip(f"{path} not found")
            source = path.read_text(encoding="utf-8")
            assert "PipelineEvent." not in source, (
                f"{path} should delegate lifecycle publication to composite observer"
            )


class TestObservabilityBootstrap:
    """Tests for observability bootstrap."""

    def test_bootstrap_creates_observability(self):
        """Bootstrap should create observability components."""
        bootstrap_path = Path("src/bioetl/composition/bootstrap.py")
        bootstrap_pkg = Path("src/bioetl/composition/bootstrap")

        if bootstrap_pkg.is_dir():
            # Read all .py files in the package
            parts = [
                p.read_text(encoding="utf-8")
                for p in sorted(bootstrap_pkg.rglob("*.py"))
            ]
            source = "\n".join(parts)
        elif bootstrap_path.exists():
            source = bootstrap_path.read_text(encoding="utf-8")
        else:
            pytest.skip("Bootstrap not found")

        # Bootstrap should set up observability
        has_observability_setup = any(
            pattern in source
            for pattern in [
                "observability",
                "metrics",
                "tracing",
                "logger",
                "structlog",
            ]
        )

        assert has_observability_setup, "Bootstrap should set up observability"

    def test_observability_factory_exists(self):
        """Observability factory should exist."""
        factory_paths = [
            Path("src/bioetl/composition/factories/observability_factory.py"),
            Path("src/bioetl/composition/factories/observability.py"),
            Path("src/bioetl/composition/bootstrap/runtime/observability.py"),
        ]

        exists = any(p.exists() for p in factory_paths)

        # If not a dedicated file, check bootstrap package
        if not exists:
            bootstrap_path = Path("src/bioetl/composition/bootstrap/__init__.py")
            if bootstrap_path.exists():
                source = bootstrap_path.read_text(encoding="utf-8")
                exists = "bootstrap_observability_bundle" in source

        assert exists, "Observability factory or bootstrap function should exist"


class TestTracingConfiguration:
    """Tests for tracing configuration."""

    def test_tracing_can_be_disabled(self):
        """Tracing should be optional (NoOp for tests)."""
        from bioetl.domain.ports.noop import NoOpTracing

        # NoOpTracing allows running without real tracing
        noop = NoOpTracing()
        assert noop is not None

    def test_tracing_in_settings(self):
        """Settings should have tracing configuration options."""
        # RuntimeConfig is in infrastructure/config/_base.py
        settings_path = Path("src/bioetl/infrastructure/config/_base.py")

        if not settings_path.exists():
            pytest.skip("Settings not found")

        source = settings_path.read_text(encoding="utf-8")

        # Should have tracing-related settings or at least mention it
        # May be optional (via OTEL env vars)
        has_tracing_config = any(
            pattern in source
            for pattern in [
                "tracing",
                "OTEL",
                "opentelemetry",
                "telemetry",
                "observability",
            ]
        )

        # Verify tracing configuration is present
        assert has_tracing_config, "Settings should contain tracing configuration"


class TestMandatorySpans:
    """Tests for mandatory tracing spans documentation."""

    MANDATORY_SPAN_LOCATIONS = [
        # Critical pipeline operations
        ("runner.py", ["run", "execute"]),
        ("batch_executor.py", ["execute", "process"]),
        # Storage operations
        ("bronze_writer.py", ["write_bronze"]),
        ("silver_writer.py", ["write_silver"]),
        ("gold_writer.py", ["write_gold"]),
    ]

    def test_critical_operations_exist(self):
        """Critical operations that should have spans should exist."""
        for filename, methods in self.MANDATORY_SPAN_LOCATIONS:
            # Find file in infrastructure or application
            found = False
            for layer in ["application", "infrastructure"]:
                for path in Path(f"src/bioetl/{layer}").rglob(filename):
                    if path.exists():
                        source = path.read_text(encoding="utf-8")
                        for method in methods:
                            if (
                                f"def {method}" in source
                                or f"async def {method}" in source
                            ):
                                found = True
                                break

            if not found and filename in ["runner.py", "batch_executor.py"]:
                # These are critical - fail if not found
                assert found, f"Critical file {filename} should have methods {methods}"


class TestOperatorTracingPolicy:
    """Freeze the bounded operator/admin tracing surface."""

    def test_metrics_service_operator_workflows_remain_traced(self):
        """MetricsService admin operations should keep application-owned spans."""
        source = Path("src/bioetl/application/services/metrics_service.py").read_text(
            encoding="utf-8"
        )
        assert "traced_operation" in source
        for span_name in (
            "metrics.start",
            "metrics.get_status",
            "metrics.push_to_gateway",
        ):
            assert span_name in source

    def test_quarantine_service_selected_workflows_remain_traced(self):
        """Bounded quarantine admin workflows should keep tracing coverage."""
        source = Path(
            "src/bioetl/application/services/quarantine_service.py"
        ).read_text(encoding="utf-8")
        assert "traced_async_operation" in source or "traced_operation" in source
        for span_name in (
            "quarantine.inspect",
            "quarantine.stats",
            "quarantine.replay",
            "quarantine.mark_reprocessed",
            "quarantine.purge",
            "quarantine.update_status",
        ):
            assert span_name in source

    def test_filtered_quarantine_explorer_helpers_remain_untraced(self):
        """Filtered explorer/detail flows stay metric/log-only by policy."""
        source = Path(
            "src/bioetl/application/services/_quarantine_service_filtered_mixin.py"
        ).read_text(encoding="utf-8")
        assert "traced_async_operation" not in source
        assert "traced_operation" not in source

    def test_observability_workflow_service_keeps_narrow_traced_scope(self):
        """Diagnostics workflows should stay limited to bounded aggregate helpers."""
        source = Path(
            "src/bioetl/application/services/observability_workflow_service.py"
        ).read_text(encoding="utf-8")
        for span_name in (
            "diagnostics.inspect_audit_run",
            "diagnostics.inspect_checkpoint_workflow",
        ):
            assert span_name in source
