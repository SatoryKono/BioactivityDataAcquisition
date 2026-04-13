"""Result model for checkpoint resume validation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CheckpointCompatibilityResult:
    """Result of checkpoint compatibility validation."""

    compatible: bool
    dq_compatible: bool
    pipeline_compatible: bool
    messages: list[str]
    execution_identity_compatible: bool = True

    @staticmethod
    def compatible_result() -> CheckpointCompatibilityResult:
        """Create a fully compatible result."""
        return CheckpointCompatibilityResult(
            compatible=True,
            dq_compatible=True,
            pipeline_compatible=True,
            execution_identity_compatible=True,
            messages=["Checkpoint is compatible for resume"],
        )

    @staticmethod
    def incompatible_result(
        dq_compatible: bool = False,
        pipeline_compatible: bool = False,
        execution_identity_compatible: bool = False,
        messages: list[str] | None = None,
    ) -> CheckpointCompatibilityResult:
        """Create an incompatible result with optional reason messages."""
        return CheckpointCompatibilityResult(
            compatible=False,
            dq_compatible=dq_compatible,
            pipeline_compatible=pipeline_compatible,
            execution_identity_compatible=execution_identity_compatible,
            messages=messages or [],
        )


__all__ = ["CheckpointCompatibilityResult"]
