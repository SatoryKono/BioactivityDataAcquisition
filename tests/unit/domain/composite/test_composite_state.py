"""Unit tests for CompositePipelineState FSM.

Tests for state transitions, properties, and metric values.
"""

from __future__ import annotations

import pytest

from bioetl.domain.composite.state import CompositePipelineState


class TestCompositePipelineState:
    """Tests for CompositePipelineState enum."""

    def test_all_states_exist(self):
        """All expected states should be defined."""
        expected_states = {
            "NOT_STARTED",
            "SEED_RUNNING",
            "SEED_COMPLETED",
            "ENRICHING",
            "ENRICHMENT_COMPLETED",
            "MERGING",
            "COMPLETED",
            "FAILED",
        }
        actual_states = {s.value for s in CompositePipelineState}
        assert actual_states == expected_states

    def test_state_from_string(self):
        """States should be constructible from string values."""
        assert (
            CompositePipelineState("NOT_STARTED") == CompositePipelineState.NOT_STARTED
        )
        assert CompositePipelineState("COMPLETED") == CompositePipelineState.COMPLETED
        assert CompositePipelineState("FAILED") == CompositePipelineState.FAILED

    def test_invalid_state_raises(self):
        """Invalid state string should raise ValueError."""
        with pytest.raises(ValueError):
            CompositePipelineState("INVALID_STATE")


class TestIsTerminal:
    """Tests for is_terminal property."""

    def test_completed_is_terminal(self):
        """COMPLETED should be terminal."""
        assert CompositePipelineState.COMPLETED.is_terminal is True

    def test_failed_is_terminal(self):
        """FAILED should be terminal."""
        assert CompositePipelineState.FAILED.is_terminal is True

    @pytest.mark.parametrize(
        "state",
        [
            CompositePipelineState.NOT_STARTED,
            CompositePipelineState.SEED_RUNNING,
            CompositePipelineState.SEED_COMPLETED,
            CompositePipelineState.ENRICHING,
            CompositePipelineState.ENRICHMENT_COMPLETED,
            CompositePipelineState.MERGING,
        ],
    )
    def test_non_terminal_states(self, state: CompositePipelineState):
        """Non-terminal states should return False."""
        assert state.is_terminal is False


class TestIsResumable:
    """Tests for is_resumable property."""

    @pytest.mark.parametrize(
        "state",
        [
            CompositePipelineState.SEED_COMPLETED,
            CompositePipelineState.ENRICHING,
            CompositePipelineState.ENRICHMENT_COMPLETED,
        ],
    )
    def test_resumable_states(self, state: CompositePipelineState):
        """Resumable states should return True."""
        assert state.is_resumable is True

    @pytest.mark.parametrize(
        "state",
        [
            CompositePipelineState.NOT_STARTED,
            CompositePipelineState.SEED_RUNNING,
            CompositePipelineState.MERGING,
            CompositePipelineState.COMPLETED,
            CompositePipelineState.FAILED,
        ],
    )
    def test_non_resumable_states(self, state: CompositePipelineState):
        """Non-resumable states should return False."""
        assert state.is_resumable is False


class TestToMetricValue:
    """Tests for to_metric_value method."""

    def test_metric_values_increase_with_progress(self):
        """Metric values should increase as pipeline progresses."""
        progress_order = [
            CompositePipelineState.NOT_STARTED,
            CompositePipelineState.SEED_RUNNING,
            CompositePipelineState.SEED_COMPLETED,
            CompositePipelineState.ENRICHING,
            CompositePipelineState.ENRICHMENT_COMPLETED,
            CompositePipelineState.MERGING,
            CompositePipelineState.COMPLETED,
        ]
        metric_values = [s.to_metric_value() for s in progress_order]
        assert metric_values == sorted(metric_values)

    def test_failed_has_negative_value(self):
        """FAILED should have -1 to distinguish from NOT_STARTED."""
        assert CompositePipelineState.FAILED.to_metric_value() == -1

    def test_not_started_has_zero(self):
        """NOT_STARTED should have 0."""
        assert CompositePipelineState.NOT_STARTED.to_metric_value() == 0

    def test_completed_has_highest_positive(self):
        """COMPLETED should have the highest positive value."""
        completed_value = CompositePipelineState.COMPLETED.to_metric_value()
        for state in CompositePipelineState:
            if state not in (
                CompositePipelineState.COMPLETED,
                CompositePipelineState.FAILED,
            ):
                assert state.to_metric_value() < completed_value


class TestCanTransitionTo:
    """Tests for can_transition_to method."""

    def test_any_state_can_transition_to_failed(self):
        """Any state should be able to transition to FAILED."""
        for state in CompositePipelineState:
            if state != CompositePipelineState.FAILED:
                assert state.can_transition_to(CompositePipelineState.FAILED) is True

    def test_failed_cannot_transition_except_to_failed(self):
        """FAILED is terminal and cannot transition."""
        for target in CompositePipelineState:
            if target == CompositePipelineState.FAILED:
                assert CompositePipelineState.FAILED.can_transition_to(target) is True
            else:
                assert CompositePipelineState.FAILED.can_transition_to(target) is False

    def test_completed_cannot_transition_except_to_failed(self):
        """COMPLETED is terminal and cannot transition."""
        for target in CompositePipelineState:
            if target == CompositePipelineState.FAILED:
                assert (
                    CompositePipelineState.COMPLETED.can_transition_to(target) is True
                )
            else:
                assert (
                    CompositePipelineState.COMPLETED.can_transition_to(target) is False
                )

    def test_valid_forward_transitions(self):
        """Valid forward transitions should be allowed."""
        valid_transitions = [
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
        ]
        for from_state, to_state in valid_transitions:
            assert from_state.can_transition_to(to_state) is True, (
                f"{from_state} -> {to_state} should be valid"
            )

    def test_invalid_backward_transitions(self):
        """Backward transitions should not be allowed."""
        invalid_transitions = [
            (CompositePipelineState.SEED_COMPLETED, CompositePipelineState.NOT_STARTED),
            (CompositePipelineState.ENRICHING, CompositePipelineState.SEED_RUNNING),
            (CompositePipelineState.MERGING, CompositePipelineState.ENRICHING),
        ]
        for from_state, to_state in invalid_transitions:
            assert from_state.can_transition_to(to_state) is False, (
                f"{from_state} -> {to_state} should be invalid"
            )

    def test_invalid_skip_transitions(self):
        """Skipping states should not be allowed."""
        invalid_transitions = [
            (CompositePipelineState.NOT_STARTED, CompositePipelineState.ENRICHING),
            (CompositePipelineState.SEED_RUNNING, CompositePipelineState.MERGING),
            (CompositePipelineState.SEED_COMPLETED, CompositePipelineState.COMPLETED),
        ]
        for from_state, to_state in invalid_transitions:
            assert from_state.can_transition_to(to_state) is False, (
                f"{from_state} -> {to_state} should be invalid (skip)"
            )


class TestStateStringRepresentation:
    """Tests for string representation."""

    def test_value_is_string(self):
        """State value should be a string."""
        for state in CompositePipelineState:
            assert isinstance(state.value, str)

    def test_inherits_from_str(self):
        """State should inherit from str for easy serialization."""
        assert isinstance(CompositePipelineState.NOT_STARTED, str)
        assert CompositePipelineState.NOT_STARTED == "NOT_STARTED"
