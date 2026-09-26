"""Private transition-builder helpers for execution-phase FSM."""

from __future__ import annotations

from bioetl.domain.types._execution_phase_transition_support import (
    PhaseT,
    PolicyT,
    RuleT,
    TransitionT,
    _ExecutionPhaseNamespace,
    _PhaseTransitionNamespace,
    _PhaseTransitionRuleBuilder,
    _TransitionPolicyNamespace,
)


def _build_not_started_transitions(
    execution_phase: _ExecutionPhaseNamespace[PhaseT],
    phase_transition: _PhaseTransitionNamespace[TransitionT],
    transition_policy: _TransitionPolicyNamespace[PolicyT],
    phase_transition_rule: _PhaseTransitionRuleBuilder[
        PhaseT, TransitionT, PolicyT, RuleT
    ],
) -> list[RuleT]:
    return [
        phase_transition_rule(
            from_phase=execution_phase.NOT_STARTED,
            to_phase=execution_phase.PREFLIGHT,
            transition=phase_transition.START_PREFLIGHT,
            policy=transition_policy.BLOCK_CONTINUATION,
            requires_validation=False,
        )
    ]


def _build_preflight_transitions(
    execution_phase: _ExecutionPhaseNamespace[PhaseT],
    phase_transition: _PhaseTransitionNamespace[TransitionT],
    transition_policy: _TransitionPolicyNamespace[PolicyT],
    phase_transition_rule: _PhaseTransitionRuleBuilder[
        PhaseT, TransitionT, PolicyT, RuleT
    ],
) -> list[RuleT]:
    return [
        phase_transition_rule(
            from_phase=execution_phase.PREFLIGHT,
            to_phase=execution_phase.DEPENDENCY_EXECUTION,
            transition=phase_transition.PREFLIGHT_TO_DEPENDENCIES,
            policy=transition_policy.BLOCK_CONTINUATION,
            requires_validation=True,
        ),
        phase_transition_rule(
            from_phase=execution_phase.PREFLIGHT,
            to_phase=execution_phase.FAILED_VALIDATION,
            transition=phase_transition.ANY_TO_FAILED,
            policy=transition_policy.BLOCK_CONTINUATION,
            requires_validation=False,
        ),
    ]


def _build_dependency_execution_transitions(
    execution_phase: _ExecutionPhaseNamespace[PhaseT],
    phase_transition: _PhaseTransitionNamespace[TransitionT],
    transition_policy: _TransitionPolicyNamespace[PolicyT],
    phase_transition_rule: _PhaseTransitionRuleBuilder[
        PhaseT, TransitionT, PolicyT, RuleT
    ],
) -> list[RuleT]:
    return [
        phase_transition_rule(
            from_phase=execution_phase.DEPENDENCY_EXECUTION,
            to_phase=execution_phase.ENRICHMENT,
            transition=phase_transition.DEPENDENCIES_TO_ENRICHMENT,
            policy=transition_policy.ALLOW_RETRY,
            requires_validation=True,
            allows_retry=True,
        ),
        phase_transition_rule(
            from_phase=execution_phase.DEPENDENCY_EXECUTION,
            to_phase=execution_phase.FAILED_EXECUTION,
            transition=phase_transition.ANY_TO_FAILED,
            policy=transition_policy.BLOCK_CONTINUATION,
            requires_validation=False,
        ),
    ]


def _build_enrichment_transitions(
    execution_phase: _ExecutionPhaseNamespace[PhaseT],
    phase_transition: _PhaseTransitionNamespace[TransitionT],
    transition_policy: _TransitionPolicyNamespace[PolicyT],
    phase_transition_rule: _PhaseTransitionRuleBuilder[
        PhaseT, TransitionT, PolicyT, RuleT
    ],
) -> list[RuleT]:
    return [
        phase_transition_rule(
            from_phase=execution_phase.ENRICHMENT,
            to_phase=execution_phase.MERGE,
            transition=phase_transition.ENRICHMENT_TO_MERGE,
            policy=transition_policy.CONTINUE_DEGRADED,
            requires_validation=True,
            degraded_mode_allowed=True,
        ),
        phase_transition_rule(
            from_phase=execution_phase.ENRICHMENT,
            to_phase=execution_phase.FAILED_EXECUTION,
            transition=phase_transition.ANY_TO_FAILED,
            policy=transition_policy.BLOCK_CONTINUATION,
            requires_validation=False,
        ),
    ]


def _build_merge_transitions(
    execution_phase: _ExecutionPhaseNamespace[PhaseT],
    phase_transition: _PhaseTransitionNamespace[TransitionT],
    transition_policy: _TransitionPolicyNamespace[PolicyT],
    phase_transition_rule: _PhaseTransitionRuleBuilder[
        PhaseT, TransitionT, PolicyT, RuleT
    ],
) -> list[RuleT]:
    return [
        phase_transition_rule(
            from_phase=execution_phase.MERGE,
            to_phase=execution_phase.CROSS_VALIDATION,
            transition=phase_transition.MERGE_TO_CROSS_VALIDATION,
            policy=transition_policy.BLOCK_CONTINUATION,
            requires_validation=True,
        ),
        phase_transition_rule(
            from_phase=execution_phase.MERGE,
            to_phase=execution_phase.FAILED_EXECUTION,
            transition=phase_transition.ANY_TO_FAILED,
            policy=transition_policy.BLOCK_CONTINUATION,
            requires_validation=False,
        ),
    ]


def _build_cross_validation_transitions(
    execution_phase: _ExecutionPhaseNamespace[PhaseT],
    phase_transition: _PhaseTransitionNamespace[TransitionT],
    transition_policy: _TransitionPolicyNamespace[PolicyT],
    phase_transition_rule: _PhaseTransitionRuleBuilder[
        PhaseT, TransitionT, PolicyT, RuleT
    ],
) -> list[RuleT]:
    return [
        phase_transition_rule(
            from_phase=execution_phase.CROSS_VALIDATION,
            to_phase=execution_phase.WRITE_FINALIZE,
            transition=phase_transition.CROSS_VALIDATION_TO_WRITE,
            policy=transition_policy.BLOCK_CONTINUATION,
            requires_validation=True,
        ),
        phase_transition_rule(
            from_phase=execution_phase.CROSS_VALIDATION,
            to_phase=execution_phase.COMPLETED_WITH_WARNINGS,
            transition=phase_transition.WRITE_TO_SUCCESS,
            policy=transition_policy.CONTINUE_DEGRADED,
            requires_validation=True,
            degraded_mode_allowed=True,
        ),
        phase_transition_rule(
            from_phase=execution_phase.CROSS_VALIDATION,
            to_phase=execution_phase.FAILED_EXECUTION,
            transition=phase_transition.ANY_TO_FAILED,
            policy=transition_policy.BLOCK_CONTINUATION,
            requires_validation=False,
        ),
    ]


def _build_write_finalize_transitions(
    execution_phase: _ExecutionPhaseNamespace[PhaseT],
    phase_transition: _PhaseTransitionNamespace[TransitionT],
    transition_policy: _TransitionPolicyNamespace[PolicyT],
    phase_transition_rule: _PhaseTransitionRuleBuilder[
        PhaseT, TransitionT, PolicyT, RuleT
    ],
) -> list[RuleT]:
    return [
        phase_transition_rule(
            from_phase=execution_phase.WRITE_FINALIZE,
            to_phase=execution_phase.COMPLETED_SUCCESS,
            transition=phase_transition.WRITE_TO_SUCCESS,
            policy=transition_policy.BLOCK_CONTINUATION,
            requires_validation=True,
        ),
        phase_transition_rule(
            from_phase=execution_phase.WRITE_FINALIZE,
            to_phase=execution_phase.FAILED_EXECUTION,
            transition=phase_transition.ANY_TO_FAILED,
            policy=transition_policy.BLOCK_CONTINUATION,
            requires_validation=False,
        ),
    ]


def _get_terminal_phases(
    execution_phase: _ExecutionPhaseNamespace[PhaseT],
) -> list[PhaseT]:
    return [
        execution_phase.COMPLETED_SUCCESS,
        execution_phase.COMPLETED_WITH_WARNINGS,
        execution_phase.FAILED_VALIDATION,
        execution_phase.FAILED_EXECUTION,
        execution_phase.FAILED_RECOVERY,
        execution_phase.TERMINATED,
    ]
