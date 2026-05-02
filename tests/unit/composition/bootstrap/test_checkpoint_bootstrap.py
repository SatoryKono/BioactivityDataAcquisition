"""Unit tests for bootstrap checkpoint and quarantine functions.

Tests bootstrap functions for checkpoint and quarantine components
used by CLI inspection operations.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from bioetl.application.core.lifecycle.checkpoint_manager import (
    CheckpointRuntimeService,
)
from bioetl.application.core.quarantine_manager import QuarantineRuntimeService
from bioetl.application.services import CheckpointService, QuarantineService
from bioetl.composition.bootstrap.assembly.checkpoint import (
    bootstrap_checkpoint_port,
    bootstrap_composite_checkpoint_port,
    bootstrap_quarantine_port,
)
from bioetl.composition.bootstrap.cli.checkpoint import (
    CLI_INSPECTION_RUN_ID,
    bootstrap_checkpoint_runtime_service,
    bootstrap_checkpoint_service,
    bootstrap_observability_workflow_service,
    bootstrap_quarantine_runtime_service,
    bootstrap_quarantine_service,
)
from bioetl.domain.ports import (
    CheckpointPort,
    CompositeCheckpointPort,
    QuarantinePort,
    TracingPort,
)
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpointAdapter
from bioetl.infrastructure.quarantine import UnifiedQuarantineAdapter
from bioetl.infrastructure.storage.support.checkpoint_writer import (
    FileCompositeCheckpointWriter,
)

TEST_ROOT = Path(tempfile.mkdtemp(prefix="bioetl-checkpoint-bootstrap-"))
CHECKPOINT_PATH = TEST_ROOT / "checkpoints"
QUARANTINE_PATH = TEST_ROOT / "quarantine"


@pytest.mark.unit
def test_checkpoint_bootstrap_public_surface_prefers_runtime_service_vocabulary() -> None:
    from bioetl.composition.bootstrap.cli import checkpoint as checkpoint_bootstrap

    assert "bootstrap_checkpoint_runtime_service" in checkpoint_bootstrap.__all__
    assert "bootstrap_quarantine_runtime_service" in checkpoint_bootstrap.__all__
    assert "bootstrap_checkpoint_manager" not in checkpoint_bootstrap.__all__
    assert "bootstrap_quarantine_manager" not in checkpoint_bootstrap.__all__


@pytest.mark.unit
class TestBootstrapQuarantinePort:
    """Tests for bootstrap_quarantine_port function."""

    def test_bootstrap_quarantine_port_returns_quarantine_port(self):
        """Test that bootstrap_quarantine_port returns a QuarantinePort."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(quarantine_path=QUARANTINE_PATH)
            result = bootstrap_quarantine_port()

        assert isinstance(result, QuarantinePort)
        assert isinstance(result, UnifiedQuarantineAdapter)

    def test_bootstrap_quarantine_port_creates_valid_instance(self):
        """Test that bootstrap_quarantine_port creates a functional quarantine instance."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                quarantine_path=Path("/custom/quarantine")
            )
            result = bootstrap_quarantine_port()

        # Verify it's a valid UnifiedQuarantineAdapter instance with correct path
        assert isinstance(result, UnifiedQuarantineAdapter)
        # Now uses centralized quarantine_path from settings
        # Use Path for cross-platform comparison (Windows uses backslashes)
        assert Path(result.base_path) == Path("/custom/quarantine")


@pytest.mark.unit
class TestBootstrapCheckpointPort:
    """Tests for bootstrap_checkpoint_port function."""

    def test_bootstrap_checkpoint_port_returns_checkpoint_port(self):
        """Test that bootstrap_checkpoint_port returns a CheckpointPort."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(checkpoint_path=CHECKPOINT_PATH)
            result = bootstrap_checkpoint_port("test_pipeline")

        assert isinstance(result, CheckpointPort)
        assert isinstance(result, LocalCheckpointAdapter)

    def test_bootstrap_checkpoint_port_passes_pipeline_name(self):
        """Test that bootstrap_checkpoint_port passes pipeline name correctly."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(checkpoint_path=CHECKPOINT_PATH)
            result = bootstrap_checkpoint_port("chembl_activity")

        assert result.pipeline_name == "chembl_activity"

    def test_bootstrap_checkpoint_port_uses_settings_path(self):
        """Test that bootstrap_checkpoint_port uses path from settings."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                checkpoint_path=Path("/custom/checkpoint/path")
            )
            result = bootstrap_checkpoint_port("test_pipeline")

        assert result.base_path == Path("/custom/checkpoint/path")


@pytest.mark.unit
class TestBootstrapCompositeCheckpointPort:
    """Tests for bootstrap_composite_checkpoint_port function."""

    def test_bootstrap_composite_checkpoint_port_returns_composite_port(self):
        """Test that bootstrap_composite_checkpoint_port returns a composite port."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(checkpoint_path=CHECKPOINT_PATH)
            result = bootstrap_composite_checkpoint_port()

        assert isinstance(result, CompositeCheckpointPort)
        assert isinstance(result, FileCompositeCheckpointWriter)

    def test_bootstrap_composite_checkpoint_port_uses_canonical_subdirectory(self):
        """Test that composite checkpoints live under checkpoint_path/composite."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                checkpoint_path=Path("/custom/output/checkpoints")
            )
            result = bootstrap_composite_checkpoint_port()

        assert result._checkpoint_dir == Path("/custom/output/checkpoints/composite")


@pytest.mark.unit
class TestBootstrapQuarantineRuntimeService:
    """Tests for bootstrap_quarantine_runtime_service function."""

    def test_bootstrap_quarantine_runtime_service_returns_runtime_service(self):
        """Test that bootstrap_quarantine_runtime_service returns QuarantineRuntimeService."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(quarantine_path=QUARANTINE_PATH)
            result = bootstrap_quarantine_runtime_service("test_pipeline")

        assert isinstance(result, QuarantineRuntimeService)

    def test_bootstrap_quarantine_runtime_service_passes_pipeline_name(self):
        """Test that bootstrap_quarantine_runtime_service passes pipeline name correctly."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(quarantine_path=QUARANTINE_PATH)
            result = bootstrap_quarantine_runtime_service("chembl_activity")

        assert result._pipeline_name == "chembl_activity"

    def test_bootstrap_quarantine_runtime_service_wires_quarantine_port(self):
        """Test that bootstrap_quarantine_runtime_service wires QuarantinePort correctly."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(quarantine_path=QUARANTINE_PATH)
            result = bootstrap_quarantine_runtime_service("test_pipeline")

        # QuarantineRuntimeService uses _quarantine attribute
        assert isinstance(result._quarantine, UnifiedQuarantineAdapter)


@pytest.mark.unit
class TestBootstrapCheckpointRuntimeService:
    """Tests for bootstrap_checkpoint_runtime_service function."""

    def test_bootstrap_checkpoint_runtime_service_returns_runtime_service(self):
        """Test that bootstrap_checkpoint_runtime_service returns CheckpointRuntimeService."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(checkpoint_path=CHECKPOINT_PATH)
            result = bootstrap_checkpoint_runtime_service("test_pipeline")

        assert isinstance(result, CheckpointRuntimeService)

    def test_bootstrap_checkpoint_runtime_service_passes_pipeline_name(self):
        """Test that bootstrap_checkpoint_runtime_service passes pipeline name correctly."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(checkpoint_path=CHECKPOINT_PATH)
            result = bootstrap_checkpoint_runtime_service("chembl_activity")

        assert result._pipeline_name == "chembl_activity"

    def test_bootstrap_checkpoint_runtime_service_wires_checkpoint_port(self):
        """Test that bootstrap_checkpoint_runtime_service wires CheckpointPort correctly."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(checkpoint_path=CHECKPOINT_PATH)
            result = bootstrap_checkpoint_runtime_service("test_pipeline")

        # CheckpointRuntimeService uses _checkpoint attribute
        assert isinstance(result._checkpoint, LocalCheckpointAdapter)

    def test_bootstrap_checkpoint_runtime_service_uses_deterministic_inspection_run_id(
        self,
    ):
        """Test that CLI inspection bootstrap avoids nondeterministic dummy run ids."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(checkpoint_path=CHECKPOINT_PATH)
            result = bootstrap_checkpoint_runtime_service("test_pipeline")

        assert isinstance(result._run_id, UUID)
        assert result._run_id == CLI_INSPECTION_RUN_ID

    def test_bootstrap_checkpoint_runtime_service_sets_resume_false(self):
        """Test that bootstrap_checkpoint_runtime_service sets resume to False."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(checkpoint_path=CHECKPOINT_PATH)
            result = bootstrap_checkpoint_runtime_service("test_pipeline")

        assert result._resume is False


@pytest.mark.unit
class TestBootstrapCheckpointService:
    """Tests for bootstrap_checkpoint_service function."""

    def test_bootstrap_checkpoint_service_returns_service(self):
        """Test that bootstrap_checkpoint_service returns CheckpointService."""
        with patch(
            "bioetl.composition.bootstrap.cli.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(checkpoint_path=CHECKPOINT_PATH)
            result = bootstrap_checkpoint_service()

        assert isinstance(result, CheckpointService)

    def test_bootstrap_checkpoint_service_uses_empty_pipeline_name(self):
        """Test that bootstrap_checkpoint_service uses empty pipeline name for global ops."""
        with patch(
            "bioetl.composition.bootstrap.cli.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(checkpoint_path=CHECKPOINT_PATH)
            result = bootstrap_checkpoint_service()

        # CheckpointService uses checkpoint_port attribute (dataclass)
        # LocalCheckpointAdapter uses pipeline_name attribute
        assert result.checkpoint_port.pipeline_name == ""

    def test_bootstrap_checkpoint_service_wires_checkpoint_port(self):
        """Test that bootstrap_checkpoint_service wires LocalCheckpointAdapter."""
        with patch(
            "bioetl.composition.bootstrap.cli.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(checkpoint_path=CHECKPOINT_PATH)
            result = bootstrap_checkpoint_service()

        # CheckpointService uses checkpoint_port attribute (dataclass)
        assert isinstance(result.checkpoint_port, LocalCheckpointAdapter)

    def test_bootstrap_checkpoint_service_resolves_metrics_and_tracing(self):
        """CLI checkpoint service should resolve operator observability ports."""
        resolved_metrics = MagicMock()
        resolved_tracer = MagicMock(spec=TracingPort)
        with (
            patch(
                "bioetl.composition.bootstrap.cli.checkpoint.get_settings"
            ) as mock_settings,
            patch(
                "bioetl.composition.bootstrap.cli.checkpoint.resolve_metrics_port",
                return_value=resolved_metrics,
            ) as mock_resolve_metrics,
            patch(
                "bioetl.composition.bootstrap.cli.checkpoint.resolve_tracing_port",
                return_value=resolved_tracer,
            ) as mock_resolve_tracing,
        ):
            settings = MagicMock(checkpoint_path=CHECKPOINT_PATH)
            mock_settings.return_value = settings
            result = bootstrap_checkpoint_service()

        assert result.metrics is resolved_metrics
        assert result.tracer is resolved_tracer
        mock_resolve_metrics.assert_called_once_with(metrics=None, settings=settings)
        mock_resolve_tracing.assert_called_once_with(
            tracer=None,
            settings=settings,
            service_name="bioetl.checkpoint_admin",
        )


@pytest.mark.unit
class TestBootstrapQuarantineService:
    """Tests for bootstrap_quarantine_service function."""

    def test_bootstrap_quarantine_service_returns_service(self):
        """Test that bootstrap_quarantine_service returns QuarantineService."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(quarantine_path=QUARANTINE_PATH)
            result = bootstrap_quarantine_service()

        assert isinstance(result, QuarantineService)

    def test_bootstrap_quarantine_service_wires_quarantine_port(self):
        """Test that bootstrap_quarantine_service wires UnifiedQuarantineAdapter."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(quarantine_path=QUARANTINE_PATH)
            result = bootstrap_quarantine_service()

        # QuarantineService uses quarantine_port attribute (dataclass)
        assert isinstance(result.quarantine_port, UnifiedQuarantineAdapter)

    def test_bootstrap_quarantine_service_resolves_metrics_port(self):
        """CLI quarantine service should resolve metrics through composition."""
        resolved_metrics = MagicMock()
        resolved_tracer = MagicMock(spec=TracingPort)
        with (
            patch(
                "bioetl.composition.bootstrap.cli.checkpoint.get_settings"
            ) as mock_settings,
            patch(
                "bioetl.composition.bootstrap.cli.checkpoint.resolve_metrics_port",
                return_value=resolved_metrics,
            ) as mock_resolve_metrics,
            patch(
                "bioetl.composition.bootstrap.cli.checkpoint.resolve_tracing_port",
                return_value=resolved_tracer,
            ) as mock_resolve_tracing,
        ):
            settings = MagicMock(quarantine_path=QUARANTINE_PATH)
            mock_settings.return_value = settings
            result = bootstrap_quarantine_service()

        assert result.metrics is resolved_metrics
        assert result.tracer is resolved_tracer
        mock_resolve_metrics.assert_called_once_with(metrics=None, settings=settings)
        mock_resolve_tracing.assert_called_once_with(
            tracer=None,
            settings=settings,
            service_name="bioetl.quarantine_admin",
        )

    def test_bootstrap_quarantine_service_wires_tracing_port(self):
        """CLI quarantine service should inject an explicit tracing port."""
        with patch(
            "bioetl.composition.bootstrap.cli.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                quarantine_path=QUARANTINE_PATH,
                observability=MagicMock(tracing_enabled=False),
            )
            result = bootstrap_quarantine_service()

        assert isinstance(result.tracer, TracingPort)


@pytest.mark.unit
class TestBootstrapObservabilityWorkflowService:
    """Tests for bootstrap_observability_workflow_service function."""

    def test_wires_tracing_port(self):
        """Workflow diagnostics bootstrap should inject an explicit tracing port."""
        with patch(
            "bioetl.composition.bootstrap.cli.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                checkpoint_path=CHECKPOINT_PATH,
                observability=MagicMock(tracing_enabled=False),
            )
            result = bootstrap_observability_workflow_service()

        assert isinstance(result.tracer, TracingPort)

    def test_wires_lineage_and_quarantine_services(self):
        """Workflow diagnostics bootstrap should wire dossier support seams."""
        checkpoint_service = MagicMock(spec=CheckpointService)
        audit_service = MagicMock()
        run_manifest_service = MagicMock()
        lineage_service = MagicMock()
        quarantine_service = MagicMock(spec=QuarantineService)
        tracer = MagicMock(spec=TracingPort)

        with (
            patch(
                "bioetl.composition.bootstrap.cli.checkpoint.get_settings"
            ) as mock_settings,
            patch(
                "bioetl.composition.bootstrap.cli.checkpoint.bootstrap_checkpoint_service",
                return_value=checkpoint_service,
            ),
            patch(
                "bioetl.composition.bootstrap.cli.checkpoint.bootstrap_audit_inspection_service",
                return_value=audit_service,
            ),
            patch(
                "bioetl.composition.bootstrap.cli.checkpoint.bootstrap_run_manifest_service",
                return_value=run_manifest_service,
            ),
            patch(
                "bioetl.composition.bootstrap.cli.checkpoint.bootstrap_lineage_service",
                return_value=lineage_service,
            ),
            patch(
                "bioetl.composition.bootstrap.cli.checkpoint.bootstrap_quarantine_service",
                return_value=quarantine_service,
            ),
            patch(
                "bioetl.composition.bootstrap.cli.checkpoint.resolve_tracing_port",
                return_value=tracer,
            ),
        ):
            mock_settings.return_value = MagicMock()
            result = bootstrap_observability_workflow_service()

        assert result.checkpoint_service is checkpoint_service
        assert result.audit_service is audit_service
        assert result.run_manifest_service is run_manifest_service
        assert result.lineage_service is lineage_service
        assert result.quarantine_service is quarantine_service
        assert result.tracer is tracer
