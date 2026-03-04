"""Unit tests for backward-compatible bootstrap aliases.

Alias functions are retained for compatibility and should delegate to
canonical bootstrap entry points without emitting deprecation warnings.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


@pytest.mark.unit
class TestBootstrapAliases:
    @patch("bioetl.composition.bootstrap.assembly.checkpoint.get_settings")
    def test_bootstrap_quarantine_alias_delegates(
        self, mock_get_settings: MagicMock, tmp_path: Path
    ) -> None:
        mock_get_settings.return_value = MagicMock(
            quarantine_path=tmp_path / "quarantine"
        )
        from bioetl.composition.bootstrap.assembly.checkpoint import (
            bootstrap_quarantine,
        )

        assert bootstrap_quarantine() is not None

    @patch("bioetl.composition.bootstrap.assembly.checkpoint.get_settings")
    def test_bootstrap_checkpoint_alias_delegates(
        self, mock_get_settings: MagicMock, tmp_path: Path
    ) -> None:
        mock_get_settings.return_value = MagicMock(
            checkpoint_path=tmp_path / "checkpoints"
        )
        from bioetl.composition.bootstrap.assembly.checkpoint import (
            bootstrap_checkpoint,
        )

        assert bootstrap_checkpoint(pipeline_name="test") is not None

    @patch("bioetl.composition.bootstrap.assembly.storage.get_settings")
    def test_bootstrap_storage_alias_delegates(
        self, mock_get_settings: MagicMock, tmp_path: Path
    ) -> None:
        mock_get_settings.return_value = MagicMock(data_dir=str(tmp_path / "data"))
        from bioetl.composition.bootstrap.assembly.storage import bootstrap_storage

        assert bootstrap_storage() is not None

    @patch("bioetl.composition.bootstrap.assembly.storage.get_settings")
    def test_bootstrap_cleanup_alias_delegates(
        self, mock_get_settings: MagicMock, tmp_path: Path
    ) -> None:
        mock_get_settings.return_value = MagicMock(data_dir=str(tmp_path / "data"))
        from bioetl.composition.bootstrap.cli.storage import bootstrap_cleanup

        assert bootstrap_cleanup() is not None

    def test_observability_aliases_delegate(self) -> None:
        mock_settings = MagicMock()
        mock_settings.observability.tracing_enabled = False
        mock_settings.observability.metrics_enabled = False
        mock_settings.observability.dq_monitor_enabled = False
        mock_settings.observability.metrics_server_enabled = False
        mock_settings.env = "dev"

        from bioetl.composition.bootstrap.runtime.observability import (
            bootstrap_dq_monitor,
            bootstrap_logger,
            bootstrap_metrics,
            bootstrap_observability,
            bootstrap_tracer,
        )

        assert bootstrap_logger(pipeline="test") is not None
        assert bootstrap_tracer(settings=mock_settings) is not None
        assert bootstrap_metrics(settings=mock_settings) is not None
        assert bootstrap_dq_monitor(settings=mock_settings) is None
        assert (
            bootstrap_observability(
                pipeline="test",
                run_id=uuid4(),
                settings=mock_settings,
            )
            is not None
        )
