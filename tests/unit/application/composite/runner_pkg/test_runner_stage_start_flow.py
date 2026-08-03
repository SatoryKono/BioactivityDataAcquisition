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
"""Focused tests for shared composite phase-start choreography."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.composite.lifecycle_observer_service import (
    CompositeLifecycleObserverService,
)
from bioetl.application.composite.runner_pkg.runner_stage_start_flow import (
    start_composite_phase,
)
from bioetl.domain.composite.state import CompositePipelineState


class _PhaseStartHarness:
    def __init__(self) -> None:
        self._config = SimpleNamespace(name="composite_demo")
        self._logger = MagicMock()
        self._observer_logger = MagicMock()
        self._observer = CompositeLifecycleObserverService(logger=self._observer_logger)
        self._run_id_str = "run-123"
        self._transition_state_with_fsm_log = MagicMock(
            return_value=SimpleNamespace(state=CompositePipelineState.ENRICHING)
        )
        self._call_save_checkpoint_safe = AsyncMock(return_value=True)
        self.started: list[str] = []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_composite_phase_transitions_saves_and_logs() -> None:
    harness = _PhaseStartHarness()
    state = SimpleNamespace(state=CompositePipelineState.SEED_COMPLETED)

    result = await start_composite_phase(
        harness,
        state,
        to_state=CompositePipelineState.ENRICHING,
        stage="enrichment_start",
        checkpoint_operation="enrichment_running",
        phase_name="enrichment",
        transition_details={"enrichers": ["a", "b"], "count": 2},
        log_details={"enrichers": ["a", "b"], "count": 2},
        on_started=lambda: harness.started.append("called"),
    )

    assert result.state == CompositePipelineState.ENRICHING
    harness._transition_state_with_fsm_log.assert_called_once_with(
        state,
        CompositePipelineState.ENRICHING,
        stage="enrichment_start",
        validate=True,
        enrichers=["a", "b"],
        count=2,
    )
    harness._call_save_checkpoint_safe.assert_awaited_once_with(
        result,
        "enrichment_running",
    )
    assert harness.started == ["called"]
    harness._observer_logger.info.assert_called_once()
    log_kwargs = harness._observer_logger.info.call_args.kwargs
    assert log_kwargs["composite"] == "composite_demo"
    assert log_kwargs["run_id"] == "run-123"
    assert log_kwargs["enrichers"] == ["a", "b"]
    assert log_kwargs["count"] == 2
