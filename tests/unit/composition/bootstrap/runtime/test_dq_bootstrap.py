# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for DQ monitor bootstrap helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.composition.bootstrap.runtime.dq_bootstrap import (
    bootstrap_dq_monitor,
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
    """Tests for bootstrap_dq_monitor."""

    def test_returns_none_when_disabled(self) -> None:
        settings = _make_settings(enabled=False)
        assert bootstrap_dq_monitor(settings=settings) is None

    def test_returns_dq_monitor_port_when_enabled(self) -> None:
        settings = _make_settings(enabled=True)
        result = bootstrap_dq_monitor(settings=settings)
        assert result is not None
        assert isinstance(result, DQMonitorPort)

    def test_uses_noop_logger_when_none_provided(self) -> None:
        mock_noop_factory = MagicMock(return_value=NoOpLogger())
        mock_monitor_factory = MagicMock()
        mock_monitor = MagicMock(spec=DQMonitorPort)
        mock_monitor.detector = MagicMock()
        mock_monitor_factory.return_value = mock_monitor

        bootstrap_dq_monitor(
            settings=_make_settings(enabled=True),
            logger=None,
            monitor_factory=mock_monitor_factory,
            noop_logger_factory=mock_noop_factory,
        )

        mock_noop_factory.assert_called_once()

    def test_uses_provided_logger(self) -> None:
        mock_noop_factory = MagicMock()
        mock_monitor_factory = MagicMock()
        mock_monitor = MagicMock(spec=DQMonitorPort)
        mock_monitor.detector = MagicMock()
        mock_monitor_factory.return_value = mock_monitor
        provided_logger = MagicMock()

        bootstrap_dq_monitor(
            settings=_make_settings(enabled=True),
            logger=provided_logger,
            monitor_factory=mock_monitor_factory,
            noop_logger_factory=mock_noop_factory,
        )

        mock_noop_factory.assert_not_called()
        assert mock_monitor_factory.call_args.kwargs["logger"] is provided_logger

    def test_passes_baseline_window_to_monitor(self) -> None:
        mock_monitor = MagicMock(spec=DQMonitorPort)
        mock_monitor.detector = MagicMock()
        mock_monitor_factory = MagicMock(return_value=mock_monitor)

        bootstrap_dq_monitor(
            settings=_make_settings(enabled=True, baseline_window=14),
            monitor_factory=mock_monitor_factory,
        )

        assert mock_monitor_factory.call_args.kwargs["baseline_window"] == 14

    def test_passes_z_score_threshold_to_monitor(self) -> None:
        mock_monitor = MagicMock(spec=DQMonitorPort)
        mock_monitor.detector = MagicMock()
        mock_monitor_factory = MagicMock(return_value=mock_monitor)

        bootstrap_dq_monitor(
            settings=_make_settings(enabled=True, z_score_threshold=3.0),
            monitor_factory=mock_monitor_factory,
        )

        assert mock_monitor_factory.call_args.kwargs[
            "z_score_threshold"
        ] == pytest.approx(3.0)

    def test_configures_min_baseline_samples(self) -> None:
        mock_monitor = MagicMock(spec=DQMonitorPort)
        mock_detector = MagicMock()
        mock_monitor.detector = mock_detector
        mock_monitor_factory = MagicMock(return_value=mock_monitor)

        bootstrap_dq_monitor(
            settings=_make_settings(enabled=True, min_baseline_samples=5),
            monitor_factory=mock_monitor_factory,
        )

        assert mock_detector.min_baseline_samples == 5

    def test_sets_error_rate_threshold(self) -> None:
        mock_monitor = MagicMock(spec=DQMonitorPort)
        mock_detector = MagicMock()
        mock_monitor.detector = mock_detector
        mock_monitor_factory = MagicMock(return_value=mock_monitor)

        bootstrap_dq_monitor(
            settings=_make_settings(enabled=True, error_rate_max=0.15),
            monitor_factory=mock_monitor_factory,
        )

        mock_detector.set_threshold.assert_any_call(
            "error_rate",
            min_value=0.0,
            max_value=0.15,
        )

    def test_sets_quality_score_threshold(self) -> None:
        mock_monitor = MagicMock(spec=DQMonitorPort)
        mock_detector = MagicMock()
        mock_monitor.detector = mock_detector
        mock_monitor_factory = MagicMock(return_value=mock_monitor)

        bootstrap_dq_monitor(
            settings=_make_settings(enabled=True, quality_score_min=0.90),
            monitor_factory=mock_monitor_factory,
        )

        mock_detector.set_threshold.assert_any_call(
            "quality_score",
            min_value=0.90,
            max_value=1.0,
        )

    def test_monitor_factory_receives_correct_args(self) -> None:
        mock_monitor = MagicMock(spec=DQMonitorPort)
        mock_monitor.detector = MagicMock()
        mock_monitor_factory = MagicMock(return_value=mock_monitor)

        bootstrap_dq_monitor(
            settings=_make_settings(
                enabled=True,
                baseline_window=10,
                z_score_threshold=2.0,
            ),
            monitor_factory=mock_monitor_factory,
        )

        kwargs = mock_monitor_factory.call_args.kwargs
        assert "logger" in kwargs
        assert kwargs["baseline_window"] == 10
        assert kwargs["z_score_threshold"] == pytest.approx(2.0)
