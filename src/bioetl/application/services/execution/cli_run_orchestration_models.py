"""Models for CLI run orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.services.execution.pipeline_runner_models import RunOptions

__all__ = [
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
class RunExecutionRequest:
    """Prepared run request passed across CLI orchestration boundaries."""

    pipeline: str
    options: RunOptions
    health_server: bool
    health_port: int


@dataclass(frozen=True, slots=True)
class RunPreparationResult:
    """Result of translating raw CLI inputs into a prepared run request."""

    request: RunExecutionRequest | None = None
    error_message: str | None = None

    @property
    def is_valid(self) -> bool:
        """Whether CLI inputs were valid enough to build a run request."""
        return self.request is not None
