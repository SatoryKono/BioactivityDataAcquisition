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

    logger.info.assert_called_once_with(
        PipelineEvent.phase_started("preflight_validation"),
        composite="test_composite",
        run_id="run-123",
        composite_run_id="run-123",
        field_count=3,
    )


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

    logger.info.assert_called_once_with(
        PipelineEvent.COMPLETE,
        composite="test_composite",
        run_id="run-123",
        duration_seconds=12.5,
        status="completed_with_warnings",
        had_warnings=True,
    )
