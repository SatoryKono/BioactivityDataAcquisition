"""Pipeline run state enums."""

from __future__ import annotations

from enum import StrEnum


class StageStatus(StrEnum):
    """Status of a pipeline stage."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineRunState(StrEnum):
    """Lifecycle state of a pipeline run (PENDING -> RUNNING -> terminal).

    Unlike application.services.PipelineRunResult (completion result),
    this enum tracks the *current state* during execution.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SHUTDOWN = "shutdown"

    def is_terminal(self) -> bool:
        """Check if terminal (no more transitions).

        Returns:
            True if the condition is met, False otherwise.
        """
        return self in {
            PipelineRunState.COMPLETED,
            PipelineRunState.FAILED,
            PipelineRunState.SHUTDOWN,
        }


__all__ = ["PipelineRunState", "StageStatus"]
