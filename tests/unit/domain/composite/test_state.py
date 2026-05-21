"""Unit tests for composite pipeline FSM states.

Tests for CompositePipelineState enum and state transition validation.
"""

from __future__ import annotations

import pytest

from bioetl.domain.composite.state import (
    CompositePipelineState,
    can_transition,
    get_transition_rules,
    validate_transition,
)
from bioetl.domain.exceptions import InvalidStateError


class TestCompositePipelineStateEnum:
    """Tests for CompositePipelineState enum values."""

    def test_all_required_states_exist(self):
        """All required FSM states should be defined."""
        expected_states = {
            "NOT_STARTED",
            "SEED_RUNNING",
            "SEED_COMPLETED",
            "DEPENDENCIES_RUNNING",
            "DEPENDENCIES_COMPLETED",
            "ENRICHING",
            "ENRICHMENT_COMPLETED",
            "MERGING",
            "CROSS_VALIDATION_RUNNING",
            "CROSS_VALIDATION_COMPLETED",
            "COMPLETED",
            "FAILED",
        }
        actual_states = {state.name for state in CompositePipelineState}
        assert actual_states == expected_states

    def test_state_values_are_lowercase(self):
        """All state values should be lowercase strings."""
        for state in CompositePipelineState:
            assert state.value == state.value.lower()
            assert state.value == state.name.lower()

    def test_state_inherits_from_str(self):
        """States should be string-compatible for serialization."""
        state = CompositePipelineState.SEED_RUNNING
        assert isinstance(state, str)
        assert state == "seed_running"

    def test_from_string_valid(self):
        """from_string should parse valid state strings."""
        assert (
            CompositePipelineState.from_string("seed_running")
            == CompositePipelineState.SEED_RUNNING
        )
        assert (
            CompositePipelineState.from_string("SEED_RUNNING")
            == CompositePipelineState.SEED_RUNNING
        )
        assert (
            CompositePipelineState.from_string("Seed_Running")
            == CompositePipelineState.SEED_RUNNING
        )

    def test_from_string_invalid_raises(self):
        """from_string should raise ValueError for invalid strings."""
        with pytest.raises(ValueError, match="Invalid composite pipeline state"):
            CompositePipelineState.from_string("invalid_state")

    def test_from_string_error_lists_valid_states(self):
        """from_string error should list valid states."""
        with pytest.raises(ValueError) as exc_info:
            CompositePipelineState.from_string("bogus")
        assert "not_started" in str(exc_info.value)
        assert "completed" in str(exc_info.value)


class TestTerminalStates:
    """Tests for terminal state detection."""

    def test_completed_is_terminal(self):
        """COMPLETED should be a terminal state."""
        assert CompositePipelineState.COMPLETED.is_terminal is True

    def test_failed_is_terminal(self):
        """FAILED should be a terminal state."""
        assert CompositePipelineState.FAILED.is_terminal is True

    def test_non_terminal_states(self):
        """Non-terminal states should return is_terminal=False."""
        non_terminal = [
            CompositePipelineState.NOT_STARTED,
            CompositePipelineState.SEED_RUNNING,
            CompositePipelineState.SEED_COMPLETED,
            CompositePipelineState.DEPENDENCIES_RUNNING,
            CompositePipelineState.DEPENDENCIES_COMPLETED,
            CompositePipelineState.ENRICHING,
            CompositePipelineState.ENRICHMENT_COMPLETED,
            CompositePipelineState.MERGING,
        ]
        for state in non_terminal:
            assert state.is_terminal is False, f"{state} should not be terminal"


class TestActiveStates:
    """Tests for active state detection."""

    def test_seed_running_is_active(self):
        """SEED_RUNNING should be an active state."""
        assert CompositePipelineState.SEED_RUNNING.is_active is True

    def test_enriching_is_active(self):
        """ENRICHING should be an active state."""
        assert CompositePipelineState.ENRICHING.is_active is True

    def test_merging_is_active(self):
        """MERGING should be an active state."""
        assert CompositePipelineState.MERGING.is_active is True

    def test_non_active_states(self):
        """Non-active states should return is_active=False."""
        non_active = [
            CompositePipelineState.NOT_STARTED,
            CompositePipelineState.SEED_COMPLETED,
            CompositePipelineState.DEPENDENCIES_COMPLETED,
            CompositePipelineState.ENRICHMENT_COMPLETED,
            CompositePipelineState.COMPLETED,
            CompositePipelineState.FAILED,
        ]
        for state in non_active:
            assert state.is_active is False, f"{state} should not be active"


class TestSuccessState:
    """Tests for success state detection."""

    def test_completed_is_success(self):
        """Only COMPLETED should be considered success."""
        assert CompositePipelineState.COMPLETED.is_success is True

    def test_other_states_not_success(self):
        """All other states should not be success."""
        for state in CompositePipelineState:
            if state != CompositePipelineState.COMPLETED:
                assert state.is_success is False, f"{state} should not be success"


class TestValidTransitions:
    """Tests for valid state transitions."""

    @pytest.mark.parametrize(
        "current,target",
        [
            (CompositePipelineState.NOT_STARTED, CompositePipelineState.SEED_RUNNING),
            (
                CompositePipelineState.SEED_RUNNING,
                CompositePipelineState.SEED_COMPLETED,
            ),
            (CompositePipelineState.SEED_RUNNING, CompositePipelineState.FAILED),
            (CompositePipelineState.SEED_COMPLETED, CompositePipelineState.ENRICHING),
            (
                CompositePipelineState.ENRICHING,
                CompositePipelineState.ENRICHMENT_COMPLETED,
            ),
            (CompositePipelineState.ENRICHING, CompositePipelineState.FAILED),
            (
                CompositePipelineState.ENRICHMENT_COMPLETED,
                CompositePipelineState.MERGING,
            ),
            (
                CompositePipelineState.MERGING,
                CompositePipelineState.CROSS_VALIDATION_RUNNING,
            ),
            (CompositePipelineState.MERGING, CompositePipelineState.COMPLETED),
            (CompositePipelineState.MERGING, CompositePipelineState.FAILED),
            (
                CompositePipelineState.CROSS_VALIDATION_RUNNING,
                CompositePipelineState.CROSS_VALIDATION_COMPLETED,
            ),
            (
                CompositePipelineState.CROSS_VALIDATION_RUNNING,
                CompositePipelineState.FAILED,
            ),
            (
                CompositePipelineState.CROSS_VALIDATION_COMPLETED,
                CompositePipelineState.COMPLETED,
            ),
        ],
    )
    def test_valid_transition_allowed(
        self, current: CompositePipelineState, target: CompositePipelineState
    ):
        """Valid transitions should be allowed."""
        assert current.can_transition_to(target) is True
        # Should not raise
        current.validate_transition(target)

    @pytest.mark.parametrize(
        "current,target",
        [
            (CompositePipelineState.NOT_STARTED, CompositePipelineState.SEED_RUNNING),
            (
                CompositePipelineState.SEED_RUNNING,
                CompositePipelineState.SEED_COMPLETED,
            ),
            (CompositePipelineState.SEED_COMPLETED, CompositePipelineState.ENRICHING),
            (
                CompositePipelineState.ENRICHING,
                CompositePipelineState.ENRICHMENT_COMPLETED,
            ),
            (
                CompositePipelineState.ENRICHMENT_COMPLETED,
                CompositePipelineState.MERGING,
            ),
            (CompositePipelineState.MERGING, CompositePipelineState.COMPLETED),
        ],
    )
    def test_module_level_can_transition(
        self, current: CompositePipelineState, target: CompositePipelineState
    ):
        """Module-level can_transition should work for valid transitions."""
        assert can_transition(current, target) is True

    @pytest.mark.parametrize(
        "current,target",
        [
            (CompositePipelineState.NOT_STARTED, CompositePipelineState.SEED_RUNNING),
            (CompositePipelineState.SEED_COMPLETED, CompositePipelineState.ENRICHING),
        ],
    )
    def test_module_level_validate_transition(
        self, current: CompositePipelineState, target: CompositePipelineState
    ):
        """Module-level validate_transition should not raise for valid transitions."""
        # Should not raise
        validate_transition(current, target)


class TestInvalidTransitions:
    """Tests for invalid state transitions."""

    @pytest.mark.parametrize(
        "current,target",
        [
            # Cannot skip states
            (CompositePipelineState.NOT_STARTED, CompositePipelineState.ENRICHING),
            (CompositePipelineState.NOT_STARTED, CompositePipelineState.MERGING),
            (CompositePipelineState.NOT_STARTED, CompositePipelineState.COMPLETED),
            (CompositePipelineState.SEED_COMPLETED, CompositePipelineState.MERGING),
            (CompositePipelineState.SEED_COMPLETED, CompositePipelineState.COMPLETED),
            (CompositePipelineState.ENRICHING, CompositePipelineState.COMPLETED),
            # Cannot go backwards
            (CompositePipelineState.SEED_RUNNING, CompositePipelineState.NOT_STARTED),
            (CompositePipelineState.ENRICHING, CompositePipelineState.SEED_RUNNING),
            (CompositePipelineState.MERGING, CompositePipelineState.ENRICHING),
            (CompositePipelineState.COMPLETED, CompositePipelineState.NOT_STARTED),
            # Cannot transition from terminal states
            (CompositePipelineState.COMPLETED, CompositePipelineState.SEED_RUNNING),
            (CompositePipelineState.COMPLETED, CompositePipelineState.FAILED),
            (CompositePipelineState.FAILED, CompositePipelineState.NOT_STARTED),
            (CompositePipelineState.FAILED, CompositePipelineState.SEED_RUNNING),
            (CompositePipelineState.FAILED, CompositePipelineState.COMPLETED),
            # Cannot transition to self (except implicitly allowed)
            (CompositePipelineState.NOT_STARTED, CompositePipelineState.NOT_STARTED),
            (CompositePipelineState.SEED_RUNNING, CompositePipelineState.SEED_RUNNING),
            # Cannot start enriching before seed completes
            (CompositePipelineState.SEED_RUNNING, CompositePipelineState.ENRICHING),
        ],
    )
    def test_invalid_transition_not_allowed(
        self, current: CompositePipelineState, target: CompositePipelineState
    ):
        """Invalid transitions should not be allowed."""
        assert current.can_transition_to(target) is False

    @pytest.mark.parametrize(
        "current,target",
        [
            (CompositePipelineState.NOT_STARTED, CompositePipelineState.ENRICHING),
            (CompositePipelineState.COMPLETED, CompositePipelineState.SEED_RUNNING),
            (CompositePipelineState.FAILED, CompositePipelineState.NOT_STARTED),
        ],
    )
    def test_invalid_transition_raises_exception(
        self, current: CompositePipelineState, target: CompositePipelineState
    ):
        """Invalid transitions should raise InvalidStateError."""
        with pytest.raises(InvalidStateError) as exc_info:
            current.validate_transition(target)

        error = exc_info.value
        assert error.current_state == current.value
        assert target.value in error.attempted_operation
        assert current.value in str(error)
        assert target.value in str(error)

    def test_module_level_can_transition_invalid(self):
        """Module-level can_transition should return False for invalid transitions."""
        assert (
            can_transition(
                CompositePipelineState.NOT_STARTED,
                CompositePipelineState.MERGING,
            )
            is False
        )

    def test_module_level_validate_transition_raises(self):
        """Module-level validate_transition should raise for invalid transitions."""
        with pytest.raises(InvalidStateError):
            validate_transition(
                CompositePipelineState.NOT_STARTED,
                CompositePipelineState.MERGING,
            )


class TestTerminalStateTransitions:
    """Tests that terminal states have no allowed transitions."""

    def test_completed_has_no_transitions(self):
        """COMPLETED should have no allowed transitions."""
        assert CompositePipelineState.COMPLETED.allowed_transitions == frozenset()

    def test_failed_has_no_transitions(self):
        """FAILED should have no allowed transitions."""
        assert CompositePipelineState.FAILED.allowed_transitions == frozenset()

    def test_completed_cannot_transition_anywhere(self):
        """COMPLETED should not allow transition to any state."""
        for target in CompositePipelineState:
            assert CompositePipelineState.COMPLETED.can_transition_to(target) is False

    def test_failed_cannot_transition_anywhere(self):
        """FAILED should not allow transition to any state."""
        for target in CompositePipelineState:
            assert CompositePipelineState.FAILED.can_transition_to(target) is False


class TestAllowedTransitions:
    """Tests for allowed_transitions property."""

    def test_not_started_allowed_transitions(self):
        """NOT_STARTED should only allow transition to SEED_RUNNING."""
        allowed = CompositePipelineState.NOT_STARTED.allowed_transitions
        assert allowed == frozenset({CompositePipelineState.SEED_RUNNING})

    def test_seed_running_allowed_transitions(self):
        """SEED_RUNNING should allow SEED_COMPLETED or FAILED."""
        allowed = CompositePipelineState.SEED_RUNNING.allowed_transitions
        assert allowed == frozenset(
            {CompositePipelineState.SEED_COMPLETED, CompositePipelineState.FAILED}
        )

    def test_enriching_allowed_transitions(self):
        """ENRICHING should allow ENRICHMENT_COMPLETED or FAILED."""
        allowed = CompositePipelineState.ENRICHING.allowed_transitions
        assert allowed == frozenset(
            {CompositePipelineState.ENRICHMENT_COMPLETED, CompositePipelineState.FAILED}
        )

    def test_enrichment_completed_allowed_transitions(self):
        """ENRICHMENT_COMPLETED should allow MERGING only."""
        allowed = CompositePipelineState.ENRICHMENT_COMPLETED.allowed_transitions
        assert allowed == frozenset({CompositePipelineState.MERGING})

    def test_merging_allowed_transitions(self):
        """MERGING should allow CROSS_VALIDATION_RUNNING or COMPLETED."""
        allowed = CompositePipelineState.MERGING.allowed_transitions
        assert allowed == frozenset(
            {
                CompositePipelineState.CROSS_VALIDATION_RUNNING,
                CompositePipelineState.COMPLETED,
                CompositePipelineState.FAILED,
            }
        )

    def test_cross_validation_running_allowed_transitions(self):
        """CROSS_VALIDATION_RUNNING should allow CROSS_VALIDATION_COMPLETED or FAILED."""
        allowed = CompositePipelineState.CROSS_VALIDATION_RUNNING.allowed_transitions
        assert allowed == frozenset(
            {
                CompositePipelineState.CROSS_VALIDATION_COMPLETED,
                CompositePipelineState.FAILED,
            }
        )

    def test_cross_validation_completed_allowed_transitions(self):
        """CROSS_VALIDATION_COMPLETED should allow COMPLETED only."""
        allowed = CompositePipelineState.CROSS_VALIDATION_COMPLETED.allowed_transitions
        assert allowed == frozenset({CompositePipelineState.COMPLETED})


class TestMetricValue:
    """Tests for metric value conversion."""

    def test_metric_values_are_unique(self):
        """Each state should have a unique metric value."""
        values = [state.to_metric_value() for state in CompositePipelineState]
        assert len(values) == len(set(values))

    def test_not_started_is_zero(self):
        """NOT_STARTED should have metric value 0."""
        assert CompositePipelineState.NOT_STARTED.to_metric_value() == 0

    def test_metric_values_are_integers(self):
        """All metric values should be integers."""
        for state in CompositePipelineState:
            value = state.to_metric_value()
            assert isinstance(value, int)
            assert 0 <= value <= 11

    def test_metric_values_progress_through_pipeline(self):
        """Metric values should generally increase through pipeline stages."""
        # Happy path progression (with dependencies)
        progression = [
            CompositePipelineState.NOT_STARTED,
            CompositePipelineState.SEED_RUNNING,
            CompositePipelineState.SEED_COMPLETED,
            CompositePipelineState.DEPENDENCIES_RUNNING,
            CompositePipelineState.DEPENDENCIES_COMPLETED,
            CompositePipelineState.ENRICHING,
            CompositePipelineState.ENRICHMENT_COMPLETED,
            CompositePipelineState.MERGING,
            CompositePipelineState.COMPLETED,
        ]
        values = [state.to_metric_value() for state in progression]
        assert values == sorted(values)


class TestGetTransitionRules:
    """Tests for get_transition_rules function."""

    def test_returns_mapping_for_all_states(self):
        """get_transition_rules should return rules for all states."""
        rules = get_transition_rules()
        assert len(rules) == len(CompositePipelineState)
        for state in CompositePipelineState:
            assert state in rules

    def test_rules_contain_frozensets(self):
        """All rule values should be frozensets."""
        rules = get_transition_rules()
        for state, allowed in rules.items():
            assert isinstance(allowed, frozenset), f"{state} should have frozenset"

    def test_rules_match_instance_allowed_transitions(self):
        """Rules should match each state's allowed_transitions property."""
        rules = get_transition_rules()
        for state in CompositePipelineState:
            assert rules[state] == state.allowed_transitions


class TestHappyPathScenario:
    """Integration test for complete pipeline execution scenario."""

    def test_complete_happy_path(self):
        """Complete pipeline should follow valid state progression."""
        state = CompositePipelineState.NOT_STARTED
        progression = []

        # Start seed
        state.validate_transition(CompositePipelineState.SEED_RUNNING)
        state = CompositePipelineState.SEED_RUNNING
        progression.append(state)

        # Seed completes
        state.validate_transition(CompositePipelineState.SEED_COMPLETED)
        state = CompositePipelineState.SEED_COMPLETED
        progression.append(state)

        # Start enrichment
        state.validate_transition(CompositePipelineState.ENRICHING)
        state = CompositePipelineState.ENRICHING
        progression.append(state)

        # Enrichment completes
        state.validate_transition(CompositePipelineState.ENRICHMENT_COMPLETED)
        state = CompositePipelineState.ENRICHMENT_COMPLETED
        progression.append(state)

        # Start merge
        state.validate_transition(CompositePipelineState.MERGING)
        state = CompositePipelineState.MERGING
        progression.append(state)

        # Merge completes
        state.validate_transition(CompositePipelineState.COMPLETED)
        state = CompositePipelineState.COMPLETED
        progression.append(state)

        # Verify final state
        assert state.is_terminal is True
        assert state.is_success is True
        assert len(progression) == 6

    def test_seed_failure_path(self):
        """Pipeline should transition to FAILED if seed fails."""
        state = CompositePipelineState.NOT_STARTED

        # Start seed
        state.validate_transition(CompositePipelineState.SEED_RUNNING)
        state = CompositePipelineState.SEED_RUNNING

        # Seed fails
        state.validate_transition(CompositePipelineState.FAILED)
        state = CompositePipelineState.FAILED

        assert state.is_terminal is True
        assert state.is_success is False

    def test_enrichment_failure_path(self):
        """Pipeline should transition to FAILED if required enrichment fails."""
        state = CompositePipelineState.ENRICHING

        # Required enricher fails
        state.validate_transition(CompositePipelineState.FAILED)
        state = CompositePipelineState.FAILED

        assert state.is_terminal is True
        assert state.is_success is False

    def test_merge_failure_path(self):
        """Pipeline should transition to FAILED if merge fails."""
        state = CompositePipelineState.MERGING

        # Merge fails directly from the active merge phase
        state.validate_transition(CompositePipelineState.FAILED)
        state = CompositePipelineState.FAILED

        assert state.is_terminal is True
        assert state.is_success is False


class TestResumableStates:
    """Tests for resumable state detection."""

    def test_seed_completed_is_resumable(self):
        """SEED_COMPLETED should be resumable."""
        assert CompositePipelineState.SEED_COMPLETED.is_resumable is True

    def test_enriching_is_resumable(self):
        """ENRICHING should be resumable."""
        assert CompositePipelineState.ENRICHING.is_resumable is True

    def test_enrichment_completed_is_resumable(self):
        """ENRICHMENT_COMPLETED should be resumable."""
        assert CompositePipelineState.ENRICHMENT_COMPLETED.is_resumable is True

    def test_failed_is_resumable(self):
        """FAILED should be resumable to allow merge retry."""
        assert CompositePipelineState.FAILED.is_resumable is True

    def test_not_started_not_resumable(self):
        """NOT_STARTED should not be resumable."""
        assert CompositePipelineState.NOT_STARTED.is_resumable is False

    def test_seed_running_not_resumable(self):
        """SEED_RUNNING should not be resumable (work in progress)."""
        assert CompositePipelineState.SEED_RUNNING.is_resumable is False

    def test_merging_not_resumable(self):
        """MERGING should not be resumable (work in progress)."""
        assert CompositePipelineState.MERGING.is_resumable is False

    def test_completed_not_resumable(self):
        """COMPLETED should not be resumable (already done)."""
        assert CompositePipelineState.COMPLETED.is_resumable is False
