"""Unit tests for deprecated bootstrap alias DeprecationWarning emissions.

Verifies that each deprecated bootstrap alias emits a DeprecationWarning
when called, guiding callers to the canonical replacement function.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


@pytest.mark.unit
class TestAssemblyDeprecationWarnings:
    """Tests for deprecated aliases in assembly bootstrap layer."""

    @patch("bioetl.composition.bootstrap.assembly.checkpoint.get_settings")
    def test_bootstrap_quarantine_emits_deprecation_warning(
        self, mock_get_settings: MagicMock
    ) -> None:
        """bootstrap_quarantine must emit DeprecationWarning."""
        mock_get_settings.return_value = MagicMock(
            quarantine_path=Path("/tmp/quarantine"),
        )
        from bioetl.composition.bootstrap.assembly.checkpoint import (
            bootstrap_quarantine,
        )

        with pytest.warns(DeprecationWarning, match="bootstrap_quarantine.*deprecated"):
            bootstrap_quarantine()

    @patch("bioetl.composition.bootstrap.assembly.checkpoint.get_settings")
    def test_bootstrap_checkpoint_emits_deprecation_warning(
        self, mock_get_settings: MagicMock
    ) -> None:
        """bootstrap_checkpoint must emit DeprecationWarning."""
        mock_get_settings.return_value = MagicMock(
            checkpoint_path=Path("/tmp/checkpoints"),
        )
        from bioetl.composition.bootstrap.assembly.checkpoint import (
            bootstrap_checkpoint,
        )

        with pytest.warns(DeprecationWarning, match="bootstrap_checkpoint.*deprecated"):
            bootstrap_checkpoint(pipeline_name="test")

    @patch("bioetl.composition.bootstrap.assembly.storage.get_settings")
    def test_bootstrap_storage_emits_deprecation_warning(
        self, mock_get_settings: MagicMock
    ) -> None:
        """bootstrap_storage must emit DeprecationWarning."""
        mock_get_settings.return_value = MagicMock(
            data_dir="/tmp/data",
        )
        from bioetl.composition.bootstrap.assembly.storage import bootstrap_storage

        with pytest.warns(DeprecationWarning, match="bootstrap_storage.*deprecated"):
            bootstrap_storage()


@pytest.mark.unit
class TestCliDeprecationWarnings:
    """Tests for deprecated aliases in CLI bootstrap layer."""

    @patch("bioetl.composition.bootstrap.assembly.storage.get_settings")
    def test_bootstrap_cleanup_emits_deprecation_warning(
        self, mock_get_settings: MagicMock
    ) -> None:
        """bootstrap_cleanup must emit DeprecationWarning."""
        mock_get_settings.return_value = MagicMock(
            data_dir="/tmp/data",
        )
        from bioetl.composition.bootstrap.cli.storage import bootstrap_cleanup

        with pytest.warns(DeprecationWarning, match="bootstrap_cleanup.*deprecated"):
            bootstrap_cleanup()


@pytest.mark.unit
class TestObservabilityDeprecationWarnings:
    """Tests for deprecated aliases in runtime observability bootstrap layer."""

    def test_bootstrap_logger_emits_deprecation_warning(self) -> None:
        """bootstrap_logger must emit DeprecationWarning."""
        from bioetl.composition.bootstrap.runtime.observability import bootstrap_logger

        with pytest.warns(DeprecationWarning, match="bootstrap_logger.*deprecated"):
            bootstrap_logger(pipeline="test")

    def test_bootstrap_tracer_emits_deprecation_warning(self) -> None:
        """bootstrap_tracer must emit DeprecationWarning."""
        mock_settings = MagicMock()
        mock_settings.observability.tracing_enabled = False

        from bioetl.composition.bootstrap.runtime.observability import bootstrap_tracer

        with pytest.warns(DeprecationWarning, match="bootstrap_tracer.*deprecated"):
            bootstrap_tracer(settings=mock_settings)

    def test_bootstrap_metrics_emits_deprecation_warning(self) -> None:
        """bootstrap_metrics must emit DeprecationWarning."""
        mock_settings = MagicMock()
        mock_settings.observability.metrics_enabled = False

        from bioetl.composition.bootstrap.runtime.observability import (
            bootstrap_metrics,
        )

        with pytest.warns(DeprecationWarning, match="bootstrap_metrics.*deprecated"):
            bootstrap_metrics(settings=mock_settings)

    def test_bootstrap_dq_monitor_emits_deprecation_warning(self) -> None:
        """bootstrap_dq_monitor must emit DeprecationWarning."""
        mock_settings = MagicMock()
        mock_settings.observability.dq_monitor_enabled = False

        from bioetl.composition.bootstrap.runtime.observability import (
            bootstrap_dq_monitor,
        )

        with pytest.warns(DeprecationWarning, match="bootstrap_dq_monitor.*deprecated"):
            bootstrap_dq_monitor(settings=mock_settings)

    def test_bootstrap_observability_emits_deprecation_warning(self) -> None:
        """bootstrap_observability must emit DeprecationWarning."""
        mock_settings = MagicMock()
        mock_settings.observability.tracing_enabled = False
        mock_settings.observability.metrics_enabled = False
        mock_settings.observability.dq_monitor_enabled = False
        mock_settings.env = "dev"

        from bioetl.composition.bootstrap.runtime.observability import (
            bootstrap_observability,
        )

        with pytest.warns(
            DeprecationWarning, match="bootstrap_observability.*deprecated"
        ):
            bootstrap_observability(
                pipeline="test",
                run_id=uuid4(),
                settings=mock_settings,
            )


@pytest.mark.unit
class TestPipelineDeprecationWarnings:
    """Tests for deprecated aliases in runtime pipeline bootstrap layer."""

    @patch("bioetl.composition.bootstrap.runtime.pipeline.bootstrap_pipeline_runner")
    def test_bootstrap_pipeline_emits_deprecation_warning(
        self, mock_runner: MagicMock
    ) -> None:
        """bootstrap_pipeline must emit DeprecationWarning."""
        mock_runner.return_value = MagicMock()
        from bioetl.composition.bootstrap.runtime.pipeline import bootstrap_pipeline

        with pytest.warns(DeprecationWarning, match="bootstrap_pipeline.*deprecated"):
            bootstrap_pipeline(ctx=MagicMock())

    @patch("bioetl.composition.bootstrap.runtime.composite.bootstrap_composite_runner")
    def test_bootstrap_composite_pipeline_emits_deprecation_warning(
        self, mock_runner: MagicMock
    ) -> None:
        """bootstrap_composite_pipeline must emit DeprecationWarning."""
        mock_runner.return_value = MagicMock()
        from bioetl.composition.bootstrap.runtime.composite import (
            bootstrap_composite_pipeline,
        )

        with pytest.warns(
            DeprecationWarning, match="bootstrap_composite_pipeline.*deprecated"
        ):
            bootstrap_composite_pipeline(
                config=MagicMock(),
                runtime=MagicMock(),
            )
