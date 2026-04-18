"""Models for CLI run orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.services.execution.pipeline_runner_models import RunOptions

__all__ = [
    "CliRunOptionsSpec",
    "CliRunOptionsInput",
    "CliRunPreparationSpec",
    "CliRunPreparationInput",
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
class CliRunOptionsSpec:
    """Normalized raw CLI option values used to build RunOptions."""

    run_type: str
    resume: bool
    start_offset: int | None
    limit: int | None
    input_csv: str | None
    filter_column: str | None
    filter_field: str | None
    dry_run: bool
    vacuum_after_run: bool | None
    vacuum_retention_days: int | None
    debug: bool
    use_cached_bronze: bool
    cached_bronze_date: str | None
    cached_bronze_path: str | None
    replay_of_run_id: str | None = None
    replay_of_manifest_id: str | None = None
    exact_replay: bool = False
    enable_tracing: bool | None = None


@dataclass(frozen=True, slots=True)
class CliRunPreparationSpec:
    """Validated-or-not raw CLI inputs needed to prepare one execution request."""

    pipeline: str
    options: CliRunOptionsSpec
    health_server: bool
    health_port: int


@dataclass(frozen=True, slots=True)
class RunExecutionContext:
    """Prepared run request passed across CLI orchestration boundaries."""

    pipeline: str
    options: RunOptions
    health_server: bool
    health_port: int


@dataclass(frozen=True, slots=True)
class RunPreparationResult:
    """Result of translating raw CLI inputs into a prepared run request."""

    request: RunExecutionContext | None = None
    error_message: str | None = None

    @property
    def is_valid(self) -> bool:
        """Whether CLI inputs were valid enough to build a run request."""
        return self.request is not None


CliRunOptionsInput = CliRunOptionsSpec
CliRunPreparationInput = CliRunPreparationSpec
RunExecutionRequest = RunExecutionContext
