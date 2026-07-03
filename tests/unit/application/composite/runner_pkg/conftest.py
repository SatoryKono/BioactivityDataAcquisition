"""Fixtures for runner_pkg tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.lifecycle_observer_service import (
    CompositeLifecycleObserverService,
)
from bioetl.domain.composite.state import CompositePipelineState


@pytest.fixture
def mock_host():
    """Mock host for runner stage tests."""
    observer_logger = MagicMock()
    observer = CompositeLifecycleObserverService(logger=observer_logger)
    
    host = SimpleNamespace(
        _config=SimpleNamespace(name="composite_demo"),
        _logger=MagicMock(),
        _observer_logger=observer_logger,
        _observer=observer,
        _run_id_str="run-123",
        _transition_state_with_fsm_log=MagicMock(
            return_value=SimpleNamespace(state=CompositePipelineState.DEPENDENCIES_COMPLETED)
        ),
        _call_save_checkpoint_safe=AsyncMock(return_value=True),
        _record_dependencies_stage_started=MagicMock(),
        _persist_failed_state=AsyncMock(return_value=True),
    )
    return host


@pytest.fixture
def mock_state():
    """Mock checkpoint state for runner stage tests."""
    return SimpleNamespace(state=CompositePipelineState.SEED_COMPLETED)
