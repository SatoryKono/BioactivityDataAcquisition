"""Transition-table builder for composite execution FSM."""

from __future__ import annotations


def build_transition_table(
    *,
    execution_phase: type,
    phase_transition: type,
    transition_policy: type,
    phase_transition_rule: type,
) -> dict[object, list[object]]:
    """Build transition table for ``CompositeFSM`` without coupling to class names."""
    return {
        execution_phase.NOT_STARTED: [
            phase_transition_rule(
                from_phase=execution_phase.NOT_STARTED,
                to_phase=execution_phase.PREFLIGHT,
                transition=phase_transition.START_PREFLIGHT,
                policy=transition_policy.BLOCK_CONTINUATION,
                requires_validation=False,
            )
        ],
        execution_phase.PREFLIGHT: [
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
        ],
        execution_phase.DEPENDENCY_EXECUTION: [
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
        ],
        execution_phase.ENRICHMENT: [
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
        ],
        execution_phase.MERGE: [
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
        ],
        execution_phase.CROSS_VALIDATION: [
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
        ],
        execution_phase.WRITE_FINALIZE: [
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
        ],
        # Terminal states have no outgoing transitions
        execution_phase.COMPLETED_SUCCESS: [],
        execution_phase.COMPLETED_WITH_WARNINGS: [],
        execution_phase.FAILED_VALIDATION: [],
        execution_phase.FAILED_EXECUTION: [],
        execution_phase.FAILED_RECOVERY: [],
        execution_phase.TERMINATED: [],
    }

