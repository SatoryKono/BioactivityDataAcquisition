"""Result assembly helpers for checkpoint compatibility decisions."""

from __future__ import annotations

from collections.abc import Sequence

from bioetl.domain.types.checkpoint_metadata import CheckpointCompatibilityResult


def build_strict_checkpoint_compatibility_result(
    *,
    compatible: bool,
    dq_compatible: bool,
    pipeline_compatible: bool,
    execution_identity_compatible: bool,
    identity_continuity_proven: bool,
    required_anchor_compatible: bool,
    messages: Sequence[str],
) -> CheckpointCompatibilityResult:
    """Build the strict resume compatibility result payload."""
    overall_compatible = compatible and required_anchor_compatible
    identity_compatible = (
        execution_identity_compatible and required_anchor_compatible
    )
    continuity_proven = identity_continuity_proven and required_anchor_compatible
    if overall_compatible:
        return CheckpointCompatibilityResult(
            compatible=True,
            dq_compatible=dq_compatible,
            pipeline_compatible=pipeline_compatible,
            execution_identity_compatible=identity_compatible,
            identity_continuity_proven=continuity_proven,
            resume_verdict="resume_only",
            messages=tuple(messages)
            or ("Checkpoint is compatible for resume",),
        )
    return CheckpointCompatibilityResult.incompatible_result(
        dq_compatible=dq_compatible,
        pipeline_compatible=pipeline_compatible,
        execution_identity_compatible=identity_compatible,
        identity_continuity_proven=continuity_proven,
        messages=tuple(messages),
    )


def build_lenient_checkpoint_compatibility_result(
    *,
    compatible: bool,
    dq_compatible: bool,
    pipeline_compatible: bool,
    execution_identity_compatible: bool,
    identity_continuity_proven: bool,
    messages: Sequence[str],
    degraded_messages: tuple[str, ...],
) -> CheckpointCompatibilityResult:
    """Build the lenient resume compatibility result payload."""
    if not compatible:
        resume_verdict = "non_replayable"
    elif degraded_messages:
        resume_verdict = "resume_only_degraded"
    else:
        resume_verdict = "resume_only"
    return CheckpointCompatibilityResult(
        compatible=compatible,
        dq_compatible=dq_compatible,
        pipeline_compatible=pipeline_compatible,
        messages=tuple(messages),
        execution_identity_compatible=execution_identity_compatible,
        identity_continuity_proven=identity_continuity_proven,
        resume_verdict=resume_verdict,
        degraded_resume_reasons=degraded_messages,
    )


__all__ = [
    "build_lenient_checkpoint_compatibility_result",
    "build_strict_checkpoint_compatibility_result",
]
