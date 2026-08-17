"""Result model for checkpoint resume validation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CheckpointCompatibilityResult:
    """Result of checkpoint compatibility validation."""

    compatible: bool
    dq_compatible: bool
    pipeline_compatible: bool
    messages: tuple[str, ...]
    execution_identity_compatible: bool = True
    identity_continuity_proven: bool = True
    resume_verdict: str = "resume_only"
    degraded_resume_reasons: tuple[str, ...] = ()

    @staticmethod
    def compatible_result() -> CheckpointCompatibilityResult:
        """Create a fully compatible result."""
        return CheckpointCompatibilityResult(
            compatible=True,
            dq_compatible=True,
            pipeline_compatible=True,
            execution_identity_compatible=True,
            identity_continuity_proven=True,
            resume_verdict="resume_only",
            degraded_resume_reasons=(),
            messages=("Checkpoint is compatible for resume",),
        )

    @staticmethod
    def incompatible_result(
        dq_compatible: bool = False,
        pipeline_compatible: bool = False,
        execution_identity_compatible: bool = False,
        identity_continuity_proven: bool = False,
        resume_verdict: str = "non_replayable",
        degraded_resume_reasons: tuple[str, ...] = (),
        messages: tuple[str, ...] | list[str] | None = None,
    ) -> CheckpointCompatibilityResult:
        """Create an incompatible result with optional reason messages."""
        return CheckpointCompatibilityResult(
            compatible=False,
            dq_compatible=dq_compatible,
            pipeline_compatible=pipeline_compatible,
            execution_identity_compatible=execution_identity_compatible,
            identity_continuity_proven=identity_continuity_proven,
            resume_verdict=resume_verdict,
            degraded_resume_reasons=degraded_resume_reasons,
            messages=tuple(messages or ()),
        )


__all__ = ["CheckpointCompatibilityResult"]
