"""Unit tests for bootstrap checkpoint and quarantine functions.

Tests bootstrap functions for checkpoint and quarantine components
used by CLI inspection operations.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from bioetl.application.core.lifecycle.checkpoint_manager import (
    CheckpointManagerService as CheckpointManager,
)
from bioetl.application.core.quarantine_manager import QuarantineManagerService
from bioetl.application.services import CheckpointService, QuarantineService
from bioetl.composition.bootstrap.assembly.checkpoint import (
    bootstrap_checkpoint_port,
    bootstrap_composite_checkpoint_port,
    bootstrap_quarantine_port,
)
from bioetl.composition.bootstrap.cli.checkpoint import (
    bootstrap_checkpoint_manager,
    bootstrap_checkpoint_service,
    bootstrap_observability_workflow_service,
    bootstrap_quarantine_manager,
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


@pytest.mark.unit
class TestBootstrapQuarantinePort:
    """Tests for bootstrap_quarantine_port function."""

    def test_bootstrap_quarantine_port_returns_quarantine_port(self):
        """Test that bootstrap_quarantine_port returns a QuarantinePort."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                quarantine_path=Path("/tmp/quarantine")
            )
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
            mock_settings.return_value = MagicMock(
                checkpoint_path=Path("/tmp/checkpoints")
            )
            result = bootstrap_checkpoint_port("test_pipeline")

        assert isinstance(result, CheckpointPort)
        assert isinstance(result, LocalCheckpointAdapter)

    def test_bootstrap_checkpoint_port_passes_pipeline_name(self):
        """Test that bootstrap_checkpoint_port passes pipeline name correctly."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                checkpoint_path=Path("/tmp/checkpoints")
            )
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
            mock_settings.return_value = MagicMock(
                checkpoint_path=Path("/tmp/checkpoints")
            )
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
class TestBootstrapQuarantineManager:
    """Tests for bootstrap_quarantine_manager function."""

    def test_bootstrap_quarantine_manager_returns_manager(self):
        """Test that bootstrap_quarantine_manager returns QuarantineManagerService."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                quarantine_path=Path("/tmp/quarantine")
            )
            result = bootstrap_quarantine_manager("test_pipeline")

        assert isinstance(result, QuarantineManagerService)

    def test_bootstrap_quarantine_manager_passes_pipeline_name(self):
        """Test that bootstrap_quarantine_manager passes pipeline name correctly."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                quarantine_path=Path("/tmp/quarantine")
            )
            result = bootstrap_quarantine_manager("chembl_activity")

        assert result._pipeline_name == "chembl_activity"

    def test_bootstrap_quarantine_manager_wires_quarantine_port(self):
        """Test that bootstrap_quarantine_manager wires QuarantinePort correctly."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                quarantine_path=Path("/tmp/quarantine")
            )
            result = bootstrap_quarantine_manager("test_pipeline")

        # QuarantineManagerService uses _quarantine attribute
        assert isinstance(result._quarantine, UnifiedQuarantineAdapter)


@pytest.mark.unit
class TestBootstrapCheckpointManager:
    """Tests for bootstrap_checkpoint_manager function."""

    def test_bootstrap_checkpoint_manager_returns_manager(self):
        """Test that bootstrap_checkpoint_manager returns CheckpointManager."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                checkpoint_path=Path("/tmp/checkpoints")
            )
            result = bootstrap_checkpoint_manager("test_pipeline")

        assert isinstance(result, CheckpointManager)

    def test_bootstrap_checkpoint_manager_passes_pipeline_name(self):
        """Test that bootstrap_checkpoint_manager passes pipeline name correctly."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                checkpoint_path=Path("/tmp/checkpoints")
            )
            result = bootstrap_checkpoint_manager("chembl_activity")

        assert result._pipeline_name == "chembl_activity"

    def test_bootstrap_checkpoint_manager_wires_checkpoint_port(self):
        """Test that bootstrap_checkpoint_manager wires CheckpointPort correctly."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                checkpoint_path=Path("/tmp/checkpoints")
            )
            result = bootstrap_checkpoint_manager("test_pipeline")

        # CheckpointManager uses _checkpoint attribute
        assert isinstance(result._checkpoint, LocalCheckpointAdapter)

    def test_bootstrap_checkpoint_manager_generates_run_id(self):
        """Test that bootstrap_checkpoint_manager generates a UUID run_id."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                checkpoint_path=Path("/tmp/checkpoints")
            )
            result = bootstrap_checkpoint_manager("test_pipeline")

        assert isinstance(result._run_id, UUID)

    def test_bootstrap_checkpoint_manager_sets_resume_false(self):
        """Test that bootstrap_checkpoint_manager sets resume to False."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                checkpoint_path=Path("/tmp/checkpoints")
            )
            result = bootstrap_checkpoint_manager("test_pipeline")

        assert result._resume is False


@pytest.mark.unit
class TestBootstrapCheckpointService:
    """Tests for bootstrap_checkpoint_service function."""

    def test_bootstrap_checkpoint_service_returns_service(self):
        """Test that bootstrap_checkpoint_service returns CheckpointService."""
        with patch(
            "bioetl.composition.bootstrap.cli.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                checkpoint_path=Path("/tmp/checkpoints")
            )
            result = bootstrap_checkpoint_service()

        assert isinstance(result, CheckpointService)

    def test_bootstrap_checkpoint_service_uses_empty_pipeline_name(self):
        """Test that bootstrap_checkpoint_service uses empty pipeline name for global ops."""
        with patch(
            "bioetl.composition.bootstrap.cli.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                checkpoint_path=Path("/tmp/checkpoints")
            )
            result = bootstrap_checkpoint_service()

        # CheckpointService uses checkpoint_port attribute (dataclass)
        # LocalCheckpointAdapter uses pipeline_name attribute
        assert result.checkpoint_port.pipeline_name == ""

    def test_bootstrap_checkpoint_service_wires_checkpoint_port(self):
        """Test that bootstrap_checkpoint_service wires LocalCheckpointAdapter."""
        with patch(
            "bioetl.composition.bootstrap.cli.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                checkpoint_path=Path("/tmp/checkpoints")
            )
            result = bootstrap_checkpoint_service()

        # CheckpointService uses checkpoint_port attribute (dataclass)
        assert isinstance(result.checkpoint_port, LocalCheckpointAdapter)


@pytest.mark.unit
class TestBootstrapQuarantineService:
    """Tests for bootstrap_quarantine_service function."""

    def test_bootstrap_quarantine_service_returns_service(self):
        """Test that bootstrap_quarantine_service returns QuarantineService."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                quarantine_path=Path("/tmp/quarantine")
            )
            result = bootstrap_quarantine_service()

        assert isinstance(result, QuarantineService)

    def test_bootstrap_quarantine_service_wires_quarantine_port(self):
        """Test that bootstrap_quarantine_service wires UnifiedQuarantineAdapter."""
        with patch(
            "bioetl.composition.bootstrap.assembly.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                quarantine_path=Path("/tmp/quarantine")
            )
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
            settings = MagicMock(quarantine_path=Path("/tmp/quarantine"))
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
                quarantine_path=Path("/tmp/quarantine"),
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
                checkpoint_path=Path("/tmp/checkpoints"),
                observability=MagicMock(tracing_enabled=False),
            )
            result = bootstrap_observability_workflow_service()

        assert isinstance(result.tracer, TracingPort)
