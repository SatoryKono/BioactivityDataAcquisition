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
"""Unit tests for FSMStateHelperService.

Tests the FSM helper utilities extracted from CompositePipelineRunner.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.fsm_helper import (
    FSMStateHelperService,
)
from bioetl.domain.composite.state import CompositePipelineState
from tests.helpers.clock import fixed_test_clock


pytestmark = pytest.mark.unit


@dataclass
class FakeEnricherConfig:
    """Fake enricher config for testing."""

    pipeline: str = "test.enricher"
    join_keys: tuple[str, ...] = ("id",)
    required: bool = False


@dataclass
class FakeCompositeConfig:
    """Fake composite config for testing."""

    name: str = "test_composite"
    enrichers: tuple[FakeEnricherConfig, ...] = ()


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger."""
    return MagicMock()


@pytest.fixture
def composite_config() -> FakeCompositeConfig:
    """Create a test composite config."""
    return FakeCompositeConfig(
        name="test_composite",
        enrichers=(
            FakeEnricherConfig(pipeline="provider1.entity1"),
            FakeEnricherConfig(pipeline="provider2.entity2"),
        ),
    )


@pytest.fixture
def fsm_helper(composite_config: Any, mock_logger: MagicMock) -> FSMStateHelperService:
    """Create an FSM helper instance."""
    return FSMStateHelperService(
        config=composite_config,
        logger=mock_logger,
        run_id="test-run-123",
    )


class TestFSMStateHelperLogTransition:
    """Tests for FSM state transition logging."""

    def test_log_fsm_transition(
        self, fsm_helper: FSMStateHelperService, mock_logger: MagicMock
    ) -> None:
        """Should log FSM state transitions."""
        fsm_helper.log_fsm_transition(
            from_state=CompositePipelineState.NOT_STARTED,
            to_state=CompositePipelineState.SEED_RUNNING,
            stage="seed_start",
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "FSM state transition"
        assert call_args[1]["from_state"] == "not_started"
        assert call_args[1]["to_state"] == "seed_running"
        assert call_args[1]["stage"] == "seed_start"

    def test_log_fsm_transition_with_extra(
        self, fsm_helper: FSMStateHelperService, mock_logger: MagicMock
    ) -> None:
        """Should include extra context in transition logs."""
        fsm_helper.log_fsm_transition(
            from_state=CompositePipelineState.SEED_RUNNING,
            to_state=CompositePipelineState.SEED_COMPLETED,
            stage="seed_complete",
            record_count=100,
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["record_count"] == 100


class TestFSMStateHelperValidateTransition:
    """Tests for FSM state transition validation."""

    def test_validate_valid_transition(
        self, fsm_helper: FSMStateHelperService, mock_logger: MagicMock
    ) -> None:
        """Should return True for valid transitions."""
        result = fsm_helper.validate_fsm_transition(
            from_state=CompositePipelineState.NOT_STARTED,
            to_state=CompositePipelineState.SEED_RUNNING,
        )
        assert result is True
        mock_logger.warning.assert_not_called()

    def test_validate_invalid_transition(
        self, fsm_helper: FSMStateHelperService, mock_logger: MagicMock
    ) -> None:
        """Should return False and log warning for invalid transitions."""
        # NOT_STARTED cannot go directly to MERGING
        result = fsm_helper.validate_fsm_transition(
            from_state=CompositePipelineState.NOT_STARTED,
            to_state=CompositePipelineState.MERGING,
        )
        assert result is False
        mock_logger.warning.assert_called_once()

    def test_validate_resume_from_failed(
        self, fsm_helper: FSMStateHelperService, mock_logger: MagicMock
    ) -> None:
        """Should allow transitions from FAILED when allow_resume=True."""
        result = fsm_helper.validate_fsm_transition(
            from_state=CompositePipelineState.FAILED,
            to_state=CompositePipelineState.SEED_RUNNING,
            allow_resume=True,
        )
        assert result is True
        mock_logger.debug.assert_called_once()


class TestFSMStateHelperHandleResumeFromFailed:
    """Tests for resume from failed state handling."""

    def test_resume_from_failed_seed_not_completed(
        self, fsm_helper: FSMStateHelperService
    ) -> None:
        """Should resume to NOT_STARTED if seed wasn't completed."""
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="test-run-123",
            state=CompositePipelineState.FAILED,
            seed_completed=False,
            completed_enrichers=frozenset(),
        )

        result = fsm_helper.handle_resume_from_failed(
            state,
            clock=fixed_test_clock(),
        )
        assert result.state == CompositePipelineState.NOT_STARTED

    def test_resume_from_failed_enrichment_partial(
        self, fsm_helper: FSMStateHelperService
    ) -> None:
        """Should resume to ENRICHING if some enrichers completed."""
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="test-run-123",
            state=CompositePipelineState.FAILED,
            seed_completed=True,
            completed_enrichers=frozenset(["provider1.entity1"]),  # 1 of 2 completed
        )

        result = fsm_helper.handle_resume_from_failed(
            state,
            clock=fixed_test_clock(),
        )
        assert result.state == CompositePipelineState.ENRICHING

    def test_resume_from_failed_merge_failed(
        self, fsm_helper: FSMStateHelperService
    ) -> None:
        """Should resume to ENRICHMENT_COMPLETED if all enrichers done but merge failed."""
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="test-run-123",
            state=CompositePipelineState.FAILED,
            seed_completed=True,
            completed_enrichers=frozenset(
                ["provider1.entity1", "provider2.entity2"]
            ),  # All completed
        )

        result = fsm_helper.handle_resume_from_failed(
            state,
            clock=fixed_test_clock(),
        )
        assert result.state == CompositePipelineState.ENRICHMENT_COMPLETED


class TestFSMStateHelperLogResumeContext:
    """Tests for resume context logging."""

    def test_log_resume_context(
        self, fsm_helper: FSMStateHelperService, mock_logger: MagicMock
    ) -> None:
        """Should log detailed resume context."""
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="test-run-123",
            state=CompositePipelineState.ENRICHING,
            seed_completed=True,
            completed_enrichers=frozenset(["provider1.entity1"]),
        )

        fsm_helper.log_resume_context(state)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "Resuming from checkpoint"
        assert call_args[1]["seed_completed"] is True
        assert call_args[1]["completed_enrichers_count"] == 1
        assert call_args[1]["total_enrichers_count"] == 2
        assert call_args[1]["remaining_enrichers_count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
