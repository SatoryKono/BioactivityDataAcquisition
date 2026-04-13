"""Focused tests for composite lifecycle publication service."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.application.composite.lifecycle_observer_service import (
    CompositeLifecycleObserverService,
)
from bioetl.domain.events import PipelineEvent


@pytest.mark.unit
def test_emit_phase_started_preserves_correlation_details() -> None:
    logger = MagicMock()
    observer = CompositeLifecycleObserverService(logger=logger)

    observer.emit_phase_started(
        composite_name="test_composite",
        run_id="run-123",
        phase_name="preflight_validation",
        details={
            "composite": "test_composite",
            "run_id": "run-123",
            "composite_run_id": "run-123",
            "field_count": 3,
        },
    )

    logger.info.assert_called_once()
    event_name = logger.info.call_args.args[0]
    log_kwargs = logger.info.call_args.kwargs
    assert event_name == PipelineEvent.phase_started("preflight_validation")
    assert log_kwargs["composite"] == "test_composite"
    assert log_kwargs["run_id"] == "run-123"
    assert log_kwargs["composite_run_id"] == "run-123"
    assert log_kwargs["field_count"] == 3
    assert log_kwargs["pipeline"] == "composite:test_composite"
    assert log_kwargs["provider"] == "composite"
    assert log_kwargs["run_type"] == "composite"
    assert log_kwargs["phase"] == "preflight_validation"
    assert log_kwargs["entity"] == "test_composite"
    assert "event" not in log_kwargs


@pytest.mark.unit
def test_emit_run_completed_marks_warning_status_when_present() -> None:
    logger = MagicMock()
    observer = CompositeLifecycleObserverService(logger=logger)

    observer.emit_run_completed(
        composite_name="test_composite",
        run_id="run-123",
        duration_seconds=12.5,
        had_warnings=True,
    )

    logger.info.assert_called_once()
    event_name = logger.info.call_args.args[0]
    log_kwargs = logger.info.call_args.kwargs
    assert event_name == PipelineEvent.COMPLETE
    assert log_kwargs["composite"] == "test_composite"
    assert log_kwargs["run_id"] == "run-123"
    assert log_kwargs["duration_seconds"] == 12.5
    assert log_kwargs["status"] == "completed_with_warnings"
    assert log_kwargs["had_warnings"] is True
    assert log_kwargs["phase"] == "cleanup"
    assert log_kwargs["pipeline"] == "composite:test_composite"
    assert log_kwargs["provider"] == "composite"
    assert log_kwargs["run_type"] == "composite"
