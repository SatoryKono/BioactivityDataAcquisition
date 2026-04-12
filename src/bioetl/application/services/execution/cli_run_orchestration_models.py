"""Models for CLI run orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.services.pipeline_runner_models import RunOptions

__all__ = [
    "RunExecutionContext",
    "RunExecutionRequest",
    "RunPreparationResult",
    "StartOffsetValidationResult",
]


@dataclass(frozen=True, slots=True)
class StartOffsetValidationResult:
    """Validation result for start-offset related CLI options."""

    is_valid: bool
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class RunExecutionContext:
    """Prepared run context passed across CLI orchestration boundaries."""

    pipeline: str
    options: RunOptions
    health_server: bool
    health_port: int


RunExecutionRequest = RunExecutionContext


@dataclass(frozen=True, slots=True)
class RunPreparationResult:
    """Result of translating raw CLI inputs into a prepared run request."""

    request: RunExecutionRequest | None = None
    error_message: str | None = None

    @property
    def is_valid(self) -> bool:
        """Whether CLI inputs were valid enough to build a run request."""
        return self.request is not None
