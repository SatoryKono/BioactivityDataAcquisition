"""Unit tests for composition/_bootstrap/checkpoint.py.

Tests bootstrap functions for checkpoint and quarantine components
used by CLI inspection operations.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.quarantine_manager import QuarantineManager
from bioetl.application.services import CheckpointService, QuarantineService
from bioetl.composition._bootstrap.checkpoint import (
    bootstrap_checkpoint,
    bootstrap_checkpoint_manager,
    bootstrap_checkpoint_service,
    bootstrap_quarantine,
    bootstrap_quarantine_manager,
    bootstrap_quarantine_service,
)
from bioetl.domain.ports import CheckpointPort, QuarantinePort
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpoint
from bioetl.infrastructure.quarantine import UnifiedQuarantine


@pytest.mark.unit
class TestBootstrapQuarantine:
    """Tests for bootstrap_quarantine function."""

    def test_bootstrap_quarantine_returns_quarantine_port(self):
        """Test that bootstrap_quarantine returns a QuarantinePort."""
        with patch(
            "bioetl.composition._bootstrap.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                quarantine_path=Path("/tmp/quarantine")
            )
            result = bootstrap_quarantine()

        assert isinstance(result, QuarantinePort)
        assert isinstance(result, UnifiedQuarantine)

    def test_bootstrap_quarantine_creates_valid_instance(self):
        """Test that bootstrap_quarantine creates a functional quarantine instance."""
        with patch(
            "bioetl.composition._bootstrap.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                quarantine_path=Path("/custom/quarantine")
            )
            result = bootstrap_quarantine()

        # Verify it's a valid UnifiedQuarantine instance with correct path
        assert isinstance(result, UnifiedQuarantine)
        # Now uses centralized quarantine_path from settings
        # Use Path for cross-platform comparison (Windows uses backslashes)
        assert Path(result.base_path) == Path("/custom/quarantine")


@pytest.mark.unit
class TestBootstrapCheckpoint:
    """Tests for bootstrap_checkpoint function."""

    def test_bootstrap_checkpoint_returns_checkpoint_port(self):
        """Test that bootstrap_checkpoint returns a CheckpointPort."""
        with patch(
            "bioetl.composition._bootstrap.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                checkpoint_path=Path("/tmp/checkpoints")
            )
            result = bootstrap_checkpoint("test_pipeline")

        assert isinstance(result, CheckpointPort)
        assert isinstance(result, LocalCheckpoint)

    def test_bootstrap_checkpoint_passes_pipeline_name(self):
        """Test that bootstrap_checkpoint passes pipeline name correctly."""
        with patch(
            "bioetl.composition._bootstrap.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                checkpoint_path=Path("/tmp/checkpoints")
            )
            result = bootstrap_checkpoint("chembl_activity")

        assert result.pipeline_name == "chembl_activity"

    def test_bootstrap_checkpoint_uses_settings_path(self):
        """Test that bootstrap_checkpoint uses path from settings."""
        with patch(
            "bioetl.composition._bootstrap.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                checkpoint_path=Path("/custom/checkpoint/path")
            )
            result = bootstrap_checkpoint("test_pipeline")

        assert result.base_path == Path("/custom/checkpoint/path")


@pytest.mark.unit
class TestBootstrapQuarantineManager:
    """Tests for bootstrap_quarantine_manager function."""

    def test_bootstrap_quarantine_manager_returns_manager(self):
        """Test that bootstrap_quarantine_manager returns QuarantineManager."""
        with patch(
            "bioetl.composition._bootstrap.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                quarantine_path=Path("/tmp/quarantine")
            )
            result = bootstrap_quarantine_manager("test_pipeline")

        assert isinstance(result, QuarantineManager)

    def test_bootstrap_quarantine_manager_passes_pipeline_name(self):
        """Test that bootstrap_quarantine_manager passes pipeline name correctly."""
        with patch(
            "bioetl.composition._bootstrap.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                quarantine_path=Path("/tmp/quarantine")
            )
            result = bootstrap_quarantine_manager("chembl_activity")

        assert result._pipeline_name == "chembl_activity"

    def test_bootstrap_quarantine_manager_wires_quarantine_port(self):
        """Test that bootstrap_quarantine_manager wires QuarantinePort correctly."""
        with patch(
            "bioetl.composition._bootstrap.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                quarantine_path=Path("/tmp/quarantine")
            )
            result = bootstrap_quarantine_manager("test_pipeline")

        # QuarantineManager uses _quarantine attribute
        assert isinstance(result._quarantine, UnifiedQuarantine)


@pytest.mark.unit
class TestBootstrapCheckpointManager:
    """Tests for bootstrap_checkpoint_manager function."""

    def test_bootstrap_checkpoint_manager_returns_manager(self):
        """Test that bootstrap_checkpoint_manager returns CheckpointManager."""
        with patch(
            "bioetl.composition._bootstrap.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                checkpoint_path=Path("/tmp/checkpoints")
            )
            result = bootstrap_checkpoint_manager("test_pipeline")

        assert isinstance(result, CheckpointManager)

    def test_bootstrap_checkpoint_manager_passes_pipeline_name(self):
        """Test that bootstrap_checkpoint_manager passes pipeline name correctly."""
        with patch(
            "bioetl.composition._bootstrap.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                checkpoint_path=Path("/tmp/checkpoints")
            )
            result = bootstrap_checkpoint_manager("chembl_activity")

        assert result._pipeline_name == "chembl_activity"

    def test_bootstrap_checkpoint_manager_wires_checkpoint_port(self):
        """Test that bootstrap_checkpoint_manager wires CheckpointPort correctly."""
        with patch(
            "bioetl.composition._bootstrap.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                checkpoint_path=Path("/tmp/checkpoints")
            )
            result = bootstrap_checkpoint_manager("test_pipeline")

        # CheckpointManager uses _checkpoint attribute
        assert isinstance(result._checkpoint, LocalCheckpoint)

    def test_bootstrap_checkpoint_manager_generates_run_id(self):
        """Test that bootstrap_checkpoint_manager generates a UUID run_id."""
        with patch(
            "bioetl.composition._bootstrap.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                checkpoint_path=Path("/tmp/checkpoints")
            )
            result = bootstrap_checkpoint_manager("test_pipeline")

        assert isinstance(result._run_id, UUID)

    def test_bootstrap_checkpoint_manager_sets_resume_false(self):
        """Test that bootstrap_checkpoint_manager sets resume to False."""
        with patch(
            "bioetl.composition._bootstrap.checkpoint.get_settings"
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
            "bioetl.composition._bootstrap.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                checkpoint_path=Path("/tmp/checkpoints")
            )
            result = bootstrap_checkpoint_service()

        assert isinstance(result, CheckpointService)

    def test_bootstrap_checkpoint_service_uses_empty_pipeline_name(self):
        """Test that bootstrap_checkpoint_service uses empty pipeline name for global ops."""
        with patch(
            "bioetl.composition._bootstrap.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                checkpoint_path=Path("/tmp/checkpoints")
            )
            result = bootstrap_checkpoint_service()

        # CheckpointService uses checkpoint_port attribute (dataclass)
        # LocalCheckpoint uses pipeline_name attribute
        assert result.checkpoint_port.pipeline_name == ""

    def test_bootstrap_checkpoint_service_wires_checkpoint_port(self):
        """Test that bootstrap_checkpoint_service wires LocalCheckpoint."""
        with patch(
            "bioetl.composition._bootstrap.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                checkpoint_path=Path("/tmp/checkpoints")
            )
            result = bootstrap_checkpoint_service()

        # CheckpointService uses checkpoint_port attribute (dataclass)
        assert isinstance(result.checkpoint_port, LocalCheckpoint)


@pytest.mark.unit
class TestBootstrapQuarantineService:
    """Tests for bootstrap_quarantine_service function."""

    def test_bootstrap_quarantine_service_returns_service(self):
        """Test that bootstrap_quarantine_service returns QuarantineService."""
        with patch(
            "bioetl.composition._bootstrap.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                quarantine_path=Path("/tmp/quarantine")
            )
            result = bootstrap_quarantine_service()

        assert isinstance(result, QuarantineService)

    def test_bootstrap_quarantine_service_wires_quarantine_port(self):
        """Test that bootstrap_quarantine_service wires UnifiedQuarantine."""
        with patch(
            "bioetl.composition._bootstrap.checkpoint.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                quarantine_path=Path("/tmp/quarantine")
            )
            result = bootstrap_quarantine_service()

        # QuarantineService uses quarantine_port attribute (dataclass)
        assert isinstance(result.quarantine_port, UnifiedQuarantine)
