"""Private support types for the execution-phase FSM."""

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
