"""Unit tests for DQ monitor bootstrap helpers.

Tests bootstrap_dq_monitor_port and its deprecated alias bootstrap_dq_monitor,
verifying correct wiring and feature-flag gating.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.composition.bootstrap.runtime.dq_bootstrap import (
    bootstrap_dq_monitor,
    bootstrap_dq_monitor_port,
)
from bioetl.domain.ports import DQMonitorPort
from bioetl.infrastructure.observability.noop_logger import NoOpLogger


def _make_settings(
    *,
    enabled: bool = True,
    baseline_window: int = 7,
    z_score_threshold: float = 2.5,
    min_baseline_samples: int = 3,
    error_rate_max: float = 0.10,
    quality_score_min: float = 0.80,
) -> SimpleNamespace:
    """Create a minimal Settings-like object for DQ bootstrap tests."""
    return SimpleNamespace(
        observability=SimpleNamespace(
            dq_monitor_enabled=enabled,
            dq_baseline_window=baseline_window,
            dq_z_score_threshold=z_score_threshold,
            dq_min_baseline_samples=min_baseline_samples,
            dq_error_rate_max=error_rate_max,
            dq_quality_score_min=quality_score_min,
        )
    )


@pytest.mark.unit
class TestBootstrapDqMonitorPort:
    """Tests for bootstrap_dq_monitor_port."""

    def test_returns_none_when_disabled(self) -> None:
        """Should return None when dq_monitor_enabled is False."""
        settings = _make_settings(enabled=False)

        result = bootstrap_dq_monitor_port(settings=settings)

        assert result is None

    def test_returns_dq_monitor_port_when_enabled(self) -> None:
        """Should return a DQMonitorPort implementation when enabled."""
        settings = _make_settings(enabled=True)

        result = bootstrap_dq_monitor_port(settings=settings)

        assert result is not None
        assert isinstance(result, DQMonitorPort)

    def test_uses_noop_logger_when_none_provided(self) -> None:
        """Should create a NoOpLogger when logger parameter is None."""
        mock_noop_cls = MagicMock(return_value=NoOpLogger())
        mock_monitor_cls = MagicMock()
        mock_monitor = MagicMock(spec=DQMonitorPort)
        mock_monitor.detector = MagicMock()
        mock_monitor_cls.return_value = mock_monitor

        settings = _make_settings(enabled=True)

        bootstrap_dq_monitor_port(
            settings=settings,
            logger=None,
            monitor_cls=mock_monitor_cls,
            noop_logger_cls=mock_noop_cls,
        )

        mock_noop_cls.assert_called_once()

    def test_uses_provided_logger(self) -> None:
        """Should use the provided logger, not create a new NoOpLogger."""
        mock_noop_cls = MagicMock()
        mock_monitor_cls = MagicMock()
        mock_monitor = MagicMock(spec=DQMonitorPort)
        mock_monitor.detector = MagicMock()
        mock_monitor_cls.return_value = mock_monitor

        provided_logger = MagicMock()
        settings = _make_settings(enabled=True)

        bootstrap_dq_monitor_port(
            settings=settings,
            logger=provided_logger,
            monitor_cls=mock_monitor_cls,
            noop_logger_cls=mock_noop_cls,
        )

        mock_noop_cls.assert_not_called()
        call_kwargs = mock_monitor_cls.call_args.kwargs
        assert call_kwargs["logger"] is provided_logger

    def test_passes_baseline_window_to_monitor(self) -> None:
        """Should pass dq_baseline_window from settings to monitor constructor."""
        mock_monitor = MagicMock(spec=DQMonitorPort)
        mock_monitor.detector = MagicMock()
        mock_monitor_cls = MagicMock(return_value=mock_monitor)

        settings = _make_settings(enabled=True, baseline_window=14)

        bootstrap_dq_monitor_port(
            settings=settings,
            monitor_cls=mock_monitor_cls,
        )

        call_kwargs = mock_monitor_cls.call_args.kwargs
        assert call_kwargs["baseline_window"] == 14

    def test_passes_z_score_threshold_to_monitor(self) -> None:
        """Should pass dq_z_score_threshold from settings to monitor constructor."""
        mock_monitor = MagicMock(spec=DQMonitorPort)
        mock_monitor.detector = MagicMock()
        mock_monitor_cls = MagicMock(return_value=mock_monitor)

        settings = _make_settings(enabled=True, z_score_threshold=3.0)

        bootstrap_dq_monitor_port(
            settings=settings,
            monitor_cls=mock_monitor_cls,
        )

        call_kwargs = mock_monitor_cls.call_args.kwargs
        assert call_kwargs["z_score_threshold"] == 3.0

    def test_configures_min_baseline_samples(self) -> None:
        """Should set detector.min_baseline_samples from settings."""
        mock_monitor = MagicMock(spec=DQMonitorPort)
        mock_detector = MagicMock()
        mock_monitor.detector = mock_detector
        mock_monitor_cls = MagicMock(return_value=mock_monitor)

        settings = _make_settings(enabled=True, min_baseline_samples=5)

        bootstrap_dq_monitor_port(
            settings=settings,
            monitor_cls=mock_monitor_cls,
        )

        assert mock_detector.min_baseline_samples == 5

    def test_sets_error_rate_threshold(self) -> None:
        """Should configure error_rate threshold via detector.set_threshold."""
        mock_monitor = MagicMock(spec=DQMonitorPort)
        mock_detector = MagicMock()
        mock_monitor.detector = mock_detector
        mock_monitor_cls = MagicMock(return_value=mock_monitor)

        settings = _make_settings(enabled=True, error_rate_max=0.15)

        bootstrap_dq_monitor_port(
            settings=settings,
            monitor_cls=mock_monitor_cls,
        )

        mock_detector.set_threshold.assert_any_call(
            "error_rate",
            min_value=0.0,
            max_value=0.15,
        )

    def test_sets_quality_score_threshold(self) -> None:
        """Should configure quality_score threshold via detector.set_threshold."""
        mock_monitor = MagicMock(spec=DQMonitorPort)
        mock_detector = MagicMock()
        mock_monitor.detector = mock_detector
        mock_monitor_cls = MagicMock(return_value=mock_monitor)

        settings = _make_settings(enabled=True, quality_score_min=0.90)

        bootstrap_dq_monitor_port(
            settings=settings,
            monitor_cls=mock_monitor_cls,
        )

        mock_detector.set_threshold.assert_any_call(
            "quality_score",
            min_value=0.90,
            max_value=1.0,
        )

    def test_di_monitor_cls_receives_correct_args(self) -> None:
        """Monitor class should be constructed with logger, baseline_window, z_score_threshold."""
        mock_monitor = MagicMock(spec=DQMonitorPort)
        mock_monitor.detector = MagicMock()
        mock_monitor_cls = MagicMock(return_value=mock_monitor)

        settings = _make_settings(
            enabled=True,
            baseline_window=10,
            z_score_threshold=2.0,
        )

        bootstrap_dq_monitor_port(
            settings=settings,
            monitor_cls=mock_monitor_cls,
        )

        mock_monitor_cls.assert_called_once()
        kwargs = mock_monitor_cls.call_args.kwargs
        assert "logger" in kwargs
        assert kwargs["baseline_window"] == 10
        assert kwargs["z_score_threshold"] == 2.0


@pytest.mark.unit
class TestBootstrapDqMonitorAlias:
    """Tests for bootstrap_dq_monitor (deprecated alias)."""

    def test_alias_returns_none_when_disabled(self) -> None:
        """Alias should return None when dq_monitor_enabled is False."""
        settings = _make_settings(enabled=False)

        result = bootstrap_dq_monitor(settings=settings)

        assert result is None

    def test_alias_returns_monitor_when_enabled(self) -> None:
        """Alias should return DQMonitorPort when enabled."""
        settings = _make_settings(enabled=True)

        result = bootstrap_dq_monitor(settings=settings)

        assert result is not None
        assert isinstance(result, DQMonitorPort)

    def test_alias_delegates_to_port_variant(self) -> None:
        """bootstrap_dq_monitor should produce same result as bootstrap_dq_monitor_port."""
        settings = _make_settings(enabled=False)

        result_alias = bootstrap_dq_monitor(settings=settings)
        result_canonical = bootstrap_dq_monitor_port(settings=settings)

        # Both should return None when disabled
        assert result_alias == result_canonical
