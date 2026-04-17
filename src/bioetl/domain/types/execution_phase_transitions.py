"""Transition-table builder for composite execution FSM."""

from __future__ import annotations

from bioetl.domain.types._execution_phase_transition_support import (
    PhaseT,
    PolicyT,
    RuleT,
    TransitionT,
    _build_cross_validation_transitions,
    _build_dependency_execution_transitions,
    _build_enrichment_transitions,
    _build_merge_transitions,
    _build_not_started_transitions,
    _build_preflight_transitions,
    _build_write_finalize_transitions,
    _ExecutionPhaseNamespace,
    _get_terminal_phases,
    _PhaseTransitionNamespace,
    _PhaseTransitionRuleBuilder,
    _TransitionPolicyNamespace,
)


def build_transition_table(
    *,
    execution_phase: _ExecutionPhaseNamespace[PhaseT],
    phase_transition: _PhaseTransitionNamespace[TransitionT],
    transition_policy: _TransitionPolicyNamespace[PolicyT],
    phase_transition_rule: _PhaseTransitionRuleBuilder[
        PhaseT, TransitionT, PolicyT, RuleT
    ],
) -> dict[PhaseT, list[RuleT]]:
    """Build transition table for ``CompositeFSM`` without coupling to class names."""
    return {
        execution_phase.NOT_STARTED: _build_not_started_transitions(
            execution_phase, phase_transition, transition_policy, phase_transition_rule
        ),
        execution_phase.PREFLIGHT: _build_preflight_transitions(
            execution_phase, phase_transition, transition_policy, phase_transition_rule
        ),
        execution_phase.DEPENDENCY_EXECUTION: _build_dependency_execution_transitions(
            execution_phase, phase_transition, transition_policy, phase_transition_rule
        ),
        execution_phase.ENRICHMENT: _build_enrichment_transitions(
            execution_phase, phase_transition, transition_policy, phase_transition_rule
        ),
        execution_phase.MERGE: _build_merge_transitions(
            execution_phase, phase_transition, transition_policy, phase_transition_rule
        ),
        execution_phase.CROSS_VALIDATION: _build_cross_validation_transitions(
            execution_phase, phase_transition, transition_policy, phase_transition_rule
        ),
        execution_phase.WRITE_FINALIZE: _build_write_finalize_transitions(
            execution_phase, phase_transition, transition_policy, phase_transition_rule
        ),
        # Terminal states have no outgoing transitions
        **{phase: [] for phase in _get_terminal_phases(execution_phase)},
    }
