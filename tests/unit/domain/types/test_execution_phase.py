# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Unit tests for execution phase and FSM."""

import pytest

from bioetl.domain.types.execution_phase import (
    CompositeFSM,
    ExecutionFSMConfig,
    ExecutionOutcome,
    ExecutionPhase,
    PhaseTransition,
    TransitionPolicy,
    create_composite_fsm,
)


pytestmark = pytest.mark.unit


def test_fsm_creation():
    """Test that FSM can be created."""
    fsm = CompositeFSM()
    assert fsm.get_current_phase() == ExecutionPhase.NOT_STARTED
    assert len(fsm.get_transition_history()) == 0


def test_types_execution_phase__factory_function__e11e895c():
    """Test factory function."""
    fsm = create_composite_fsm()
    assert isinstance(fsm, CompositeFSM)


def test_types_execution_phase__custom_config__97623568():
    """Test FSM with custom configuration."""
    config = ExecutionFSMConfig(
        strict_validation=False,
        allow_degraded_mode=True,
        max_retry_attempts=3,
        timeout_seconds=300,
    )
    fsm = CompositeFSM(config)
    assert fsm.config.strict_validation is False
    assert fsm.config.allow_degraded_mode is True
    assert fsm.config.max_retry_attempts == 3
    assert fsm.config.timeout_seconds == 300


def test_types_execution_phase__initial_state__331e5a1c():
    """Test initial FSM state."""
    fsm = CompositeFSM()
    assert fsm.get_current_phase() == ExecutionPhase.NOT_STARTED
    assert not fsm.is_terminal_state()
    assert fsm.get_execution_outcome() is None


def test_valid_transitions_from_not_started():
    """Test valid transitions from NOT_STARTED phase."""
    fsm = CompositeFSM()
    valid_transitions = fsm.get_valid_transitions()
    assert len(valid_transitions) == 1
    assert PhaseTransition.START_PREFLIGHT in valid_transitions


def test_start_preflight_transition():
    """Test transition from NOT_STARTED to PREFLIGHT."""
    fsm = CompositeFSM()

    # Should be able to transition
    assert fsm.can_transition(PhaseTransition.START_PREFLIGHT)

    # Perform transition
    new_phase = fsm.transition(PhaseTransition.START_PREFLIGHT)
    assert new_phase == ExecutionPhase.PREFLIGHT
    assert fsm.get_current_phase() == ExecutionPhase.PREFLIGHT
    assert len(fsm.get_transition_history()) == 1
    assert fsm.get_transition_history()[0] == PhaseTransition.START_PREFLIGHT


def test_invalid_transition():
    """Test that invalid transitions are rejected."""
    fsm = CompositeFSM()

    # Try to transition directly to DEPENDENCY_EXECUTION (should fail)
    assert not fsm.can_transition(PhaseTransition.PREFLIGHT_TO_DEPENDENCIES)

    with pytest.raises(ValueError, match="Invalid transition"):
        fsm.transition(PhaseTransition.PREFLIGHT_TO_DEPENDENCIES)


def test_preflight_to_dependencies_transition():
    """Test transition from PREFLIGHT to DEPENDENCY_EXECUTION."""
    fsm = CompositeFSM()

    # Start preflight
    fsm.transition(PhaseTransition.START_PREFLIGHT)

    # Should be able to transition to dependencies
    assert fsm.can_transition(
        PhaseTransition.PREFLIGHT_TO_DEPENDENCIES, validation_passed=True
    )

    # Perform transition
    new_phase = fsm.transition(
        PhaseTransition.PREFLIGHT_TO_DEPENDENCIES, validation_passed=True
    )
    assert new_phase == ExecutionPhase.DEPENDENCY_EXECUTION


def test_validation_required_transition():
    """Test transition that requires validation."""
    fsm = CompositeFSM()
    fsm.transition(PhaseTransition.START_PREFLIGHT)

    # Should not allow transition if validation fails
    assert not fsm.can_transition(
        PhaseTransition.PREFLIGHT_TO_DEPENDENCIES, validation_passed=False
    )

    with pytest.raises(ValueError):
        fsm.transition(
            PhaseTransition.PREFLIGHT_TO_DEPENDENCIES, validation_passed=False
        )


def test_preflight_failure_transition():
    """Test failure transition from PREFLIGHT."""
    fsm = CompositeFSM()
    fsm.transition(PhaseTransition.START_PREFLIGHT)

    # Should be able to transition to failed state
    assert fsm.can_transition(PhaseTransition.ANY_TO_FAILED)

    new_phase = fsm.transition(PhaseTransition.ANY_TO_FAILED)
    assert new_phase == ExecutionPhase.FAILED_VALIDATION
    assert fsm.is_terminal_state()


def test_complete_execution_path():
    """Test a complete successful execution path."""
    fsm = CompositeFSM()

    # NOT_STARTED -> PREFLIGHT
    fsm.transition(PhaseTransition.START_PREFLIGHT)
    assert fsm.get_current_phase() == ExecutionPhase.PREFLIGHT

    # PREFLIGHT -> DEPENDENCY_EXECUTION
    fsm.transition(PhaseTransition.PREFLIGHT_TO_DEPENDENCIES, validation_passed=True)
    assert fsm.get_current_phase() == ExecutionPhase.DEPENDENCY_EXECUTION

    # DEPENDENCY_EXECUTION -> ENRICHMENT
    fsm.transition(PhaseTransition.DEPENDENCIES_TO_ENRICHMENT, validation_passed=True)
    assert fsm.get_current_phase() == ExecutionPhase.ENRICHMENT

    # ENRICHMENT -> MERGE
    fsm.transition(PhaseTransition.ENRICHMENT_TO_MERGE, validation_passed=True)
    assert fsm.get_current_phase() == ExecutionPhase.MERGE

    # MERGE -> CROSS_VALIDATION
    fsm.transition(PhaseTransition.MERGE_TO_CROSS_VALIDATION, validation_passed=True)
    assert fsm.get_current_phase() == ExecutionPhase.CROSS_VALIDATION

    # CROSS_VALIDATION -> WRITE_FINALIZE
    fsm.transition(PhaseTransition.CROSS_VALIDATION_TO_WRITE, validation_passed=True)
    assert fsm.get_current_phase() == ExecutionPhase.WRITE_FINALIZE

    # WRITE_FINALIZE -> COMPLETED_SUCCESS
    fsm.transition(PhaseTransition.WRITE_TO_SUCCESS, validation_passed=True)
    assert fsm.get_current_phase() == ExecutionPhase.COMPLETED_SUCCESS
    assert fsm.is_terminal_state()


def test_terminal_state_no_transitions():
    """Test that terminal states cannot transition."""
    fsm = CompositeFSM()

    # Complete execution to success
    for transition in [
        PhaseTransition.START_PREFLIGHT,
        PhaseTransition.PREFLIGHT_TO_DEPENDENCIES,
        PhaseTransition.DEPENDENCIES_TO_ENRICHMENT,
        PhaseTransition.ENRICHMENT_TO_MERGE,
        PhaseTransition.MERGE_TO_CROSS_VALIDATION,
        PhaseTransition.CROSS_VALIDATION_TO_WRITE,
        PhaseTransition.WRITE_TO_SUCCESS,
    ]:
        fsm.transition(transition, validation_passed=True)

    # Should be in terminal state
    assert fsm.is_terminal_state()
    assert len(fsm.get_valid_transitions()) == 0

    # Should not allow any transitions
    for transition in PhaseTransition:
        assert not fsm.can_transition(transition)


def test_execution_outcome():
    """Test execution outcome determination."""
    # Test success outcome
    fsm = CompositeFSM()
    for transition in [
        PhaseTransition.START_PREFLIGHT,
        PhaseTransition.PREFLIGHT_TO_DEPENDENCIES,
        PhaseTransition.DEPENDENCIES_TO_ENRICHMENT,
        PhaseTransition.ENRICHMENT_TO_MERGE,
        PhaseTransition.MERGE_TO_CROSS_VALIDATION,
        PhaseTransition.CROSS_VALIDATION_TO_WRITE,
        PhaseTransition.WRITE_TO_SUCCESS,
    ]:
        fsm.transition(transition, validation_passed=True)

    assert fsm.get_execution_outcome() == ExecutionOutcome.SUCCESS

    # Test failure outcome
    fsm2 = CompositeFSM()
    fsm2.transition(PhaseTransition.START_PREFLIGHT)
    fsm2.transition(PhaseTransition.ANY_TO_FAILED)

    assert fsm2.get_execution_outcome() == ExecutionOutcome.FAILED_VALIDATION


def test_fsm_reset():
    """Test FSM reset functionality."""
    fsm = CompositeFSM()

    # Progress through some phases
    fsm.transition(PhaseTransition.START_PREFLIGHT)
    fsm.transition(PhaseTransition.PREFLIGHT_TO_DEPENDENCIES, validation_passed=True)

    assert fsm.get_current_phase() == ExecutionPhase.DEPENDENCY_EXECUTION
    assert len(fsm.get_transition_history()) == 2

    # Reset
    fsm.reset()

    assert fsm.get_current_phase() == ExecutionPhase.NOT_STARTED
    assert len(fsm.get_transition_history()) == 0
    assert not fsm.is_terminal_state()


def test_degraded_mode_transition():
    """Test transition that allows degraded mode."""
    fsm = CompositeFSM()

    # Progress to enrichment phase
    fsm.transition(PhaseTransition.START_PREFLIGHT)
    fsm.transition(PhaseTransition.PREFLIGHT_TO_DEPENDENCIES, validation_passed=True)
    fsm.transition(PhaseTransition.DEPENDENCIES_TO_ENRICHMENT, validation_passed=True)

    # Get the transition rule
    valid_transitions = fsm.get_valid_transitions()
    enrichment_to_merge = PhaseTransition.ENRICHMENT_TO_MERGE
    assert enrichment_to_merge in valid_transitions

    # Check that this transition allows degraded mode
    transition_rules = fsm.transition_table[ExecutionPhase.ENRICHMENT]
    rule = next(
        rule for rule in transition_rules if rule.transition == enrichment_to_merge
    )
    assert rule.degraded_mode_allowed is True


def test_retry_allowed_transition():
    """Test transition that allows retry."""
    fsm = CompositeFSM()

    # Progress to dependency execution phase
    fsm.transition(PhaseTransition.START_PREFLIGHT)
    fsm.transition(PhaseTransition.PREFLIGHT_TO_DEPENDENCIES, validation_passed=True)

    # Get the transition rule
    transition_rules = fsm.transition_table[ExecutionPhase.DEPENDENCY_EXECUTION]
    dependencies_to_enrichment = PhaseTransition.DEPENDENCIES_TO_ENRICHMENT
    rule = next(
        rule
        for rule in transition_rules
        if rule.transition == dependencies_to_enrichment
    )

    assert rule.allows_retry is True


def test_transition_history():
    """Test transition history tracking."""
    fsm = CompositeFSM()

    # Perform several transitions
    transitions = [
        PhaseTransition.START_PREFLIGHT,
        PhaseTransition.PREFLIGHT_TO_DEPENDENCIES,
        PhaseTransition.DEPENDENCIES_TO_ENRICHMENT,
    ]

    for transition in transitions:
        fsm.transition(transition, validation_passed=True)

    # Check history
    history = fsm.get_transition_history()
    assert len(history) == 3
    for i, expected_transition in enumerate(transitions):
        assert history[i] == expected_transition


def test_phase_transition_policies():
    """Test different transition policies."""
    fsm = CompositeFSM()

    # Test BLOCK_CONTINUATION policy (most transitions)
    fsm.transition(PhaseTransition.START_PREFLIGHT)
    transition_rules = fsm.transition_table[ExecutionPhase.PREFLIGHT]

    block_transitions = [
        rule
        for rule in transition_rules
        if rule.policy == TransitionPolicy.BLOCK_CONTINUATION
    ]
    assert len(block_transitions) == 2  # PREFLIGHT_TO_DEPENDENCIES and ANY_TO_FAILED

    # Test ALLOW_RETRY policy
    fsm.transition(PhaseTransition.PREFLIGHT_TO_DEPENDENCIES, validation_passed=True)
    transition_rules = fsm.transition_table[ExecutionPhase.DEPENDENCY_EXECUTION]

    retry_transitions = [
        rule for rule in transition_rules if rule.policy == TransitionPolicy.ALLOW_RETRY
    ]
    assert len(retry_transitions) == 1  # DEPENDENCIES_TO_ENRICHMENT

    # Test CONTINUE_DEGRADED policy
    fsm.transition(PhaseTransition.DEPENDENCIES_TO_ENRICHMENT, validation_passed=True)
    transition_rules = fsm.transition_table[ExecutionPhase.ENRICHMENT]

    degraded_transitions = [
        rule
        for rule in transition_rules
        if rule.policy == TransitionPolicy.CONTINUE_DEGRADED
    ]
    assert len(degraded_transitions) == 1  # ENRICHMENT_TO_MERGE
