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
"""Fixtures for runner_pkg tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.composite.lifecycle_observer_service import (
    CompositeLifecycleObserverService,
)
from bioetl.domain.composite.state import CompositePipelineState


@pytest.fixture
def mock_host():
    """Mock host for runner stage tests."""
    observer = MagicMock(spec=CompositeLifecycleObserverService)

    def _transition_state(
        _state: object,
        to_state: CompositePipelineState,
        **_: object,
    ) -> SimpleNamespace:
        return SimpleNamespace(state=to_state)

    host = SimpleNamespace(
        _config=SimpleNamespace(name="composite_demo"),
        _logger=MagicMock(),
        _observer_logger=MagicMock(),
        _observer=observer,
        _run_id_str="run-123",
        _transition_state_with_fsm_log=MagicMock(side_effect=_transition_state),
        _call_save_checkpoint_safe=AsyncMock(return_value=True),
        _record_dependencies_stage_started=MagicMock(),
        _persist_failed_state=AsyncMock(return_value=True),
    )
    return host


@pytest.fixture
def mock_state():
    """Mock checkpoint state for runner stage tests."""
    return SimpleNamespace(state=CompositePipelineState.SEED_COMPLETED)
