"""Private support types and transition builders for execution-phase FSM."""

from __future__ import annotations

from typing import Protocol, TypeVar

PhaseT = TypeVar("PhaseT")
TransitionT = TypeVar("TransitionT")
PolicyT = TypeVar("PolicyT")
RuleT = TypeVar("RuleT")
PhaseCoT = TypeVar("PhaseCoT", covariant=True)
TransitionCoT = TypeVar("TransitionCoT", covariant=True)
PolicyCoT = TypeVar("PolicyCoT", covariant=True)
PhaseContraT = TypeVar("PhaseContraT", contravariant=True)
TransitionContraT = TypeVar("TransitionContraT", contravariant=True)
PolicyContraT = TypeVar("PolicyContraT", contravariant=True)
RuleCoT = TypeVar("RuleCoT", covariant=True)


class _ExecutionPhaseNamespace(Protocol[PhaseCoT]):
    @property
    def NOT_STARTED(self) -> PhaseCoT: ...

    @property
    def PREFLIGHT(self) -> PhaseCoT: ...

    @property
    def DEPENDENCY_EXECUTION(self) -> PhaseCoT: ...

    @property
    def ENRICHMENT(self) -> PhaseCoT: ...

    @property
    def MERGE(self) -> PhaseCoT: ...

    @property
    def CROSS_VALIDATION(self) -> PhaseCoT: ...

    @property
    def WRITE_FINALIZE(self) -> PhaseCoT: ...

    @property
    def COMPLETED_SUCCESS(self) -> PhaseCoT: ...

    @property
    def COMPLETED_WITH_WARNINGS(self) -> PhaseCoT: ...

    @property
    def FAILED_VALIDATION(self) -> PhaseCoT: ...

    @property
    def FAILED_EXECUTION(self) -> PhaseCoT: ...

    @property
    def FAILED_RECOVERY(self) -> PhaseCoT: ...

    @property
    def TERMINATED(self) -> PhaseCoT: ...


class _PhaseTransitionNamespace(Protocol[TransitionCoT]):
    @property
    def START_PREFLIGHT(self) -> TransitionCoT: ...

    @property
    def PREFLIGHT_TO_DEPENDENCIES(self) -> TransitionCoT: ...

    @property
    def DEPENDENCIES_TO_ENRICHMENT(self) -> TransitionCoT: ...

    @property
    def ENRICHMENT_TO_MERGE(self) -> TransitionCoT: ...

    @property
    def MERGE_TO_CROSS_VALIDATION(self) -> TransitionCoT: ...

    @property
    def CROSS_VALIDATION_TO_WRITE(self) -> TransitionCoT: ...

    @property
    def WRITE_TO_SUCCESS(self) -> TransitionCoT: ...

    @property
    def ANY_TO_FAILED(self) -> TransitionCoT: ...


class _TransitionPolicyNamespace(Protocol[PolicyCoT]):
    @property
    def ALLOW_RETRY(self) -> PolicyCoT: ...

    @property
    def CONTINUE_DEGRADED(self) -> PolicyCoT: ...

    @property
    def BLOCK_CONTINUATION(self) -> PolicyCoT: ...


class _PhaseTransitionRuleBuilder(
    Protocol[PhaseContraT, TransitionContraT, PolicyContraT, RuleCoT]
):
    def __call__(
        self,
        *,
        from_phase: PhaseContraT,
        to_phase: PhaseContraT,
        transition: TransitionContraT,
        policy: PolicyContraT,
        requires_validation: bool = True,
        allows_retry: bool = False,
        compensation_required: bool = False,
        degraded_mode_allowed: bool = False,
    ) -> RuleCoT: ...


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
