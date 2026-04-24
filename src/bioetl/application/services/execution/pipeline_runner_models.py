"""Models and exceptions for PipelineRunnerService."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from bioetl.domain.context import MISSING_RUNTIME_TIMESTAMP


class PipelineRunResult(StrEnum):
    """Pipeline run completion status."""

    SUCCESS = "success"
    SHUTDOWN = "shutdown"
    FAILED = "failed"
    DRY_RUN = "dry_run"


@dataclass(frozen=True)
class RunResult:
    """Result of pipeline execution."""

    status: PipelineRunResult
    pipeline_name: str
    run_id: str
    run_type: str
    manifest_id: str | None = None
    records_fetched: int = 0
    records_bronze: int = 0
    records_silver: int = 0
    records_gold: int = 0
    records_quarantined: int = 0
    records_filtered_out: int = 0
    started_at: datetime = MISSING_RUNTIME_TIMESTAMP
    completed_at: datetime = MISSING_RUNTIME_TIMESTAMP
    error_message: str | None = None
    error_type: str | None = None

    @property
    def duration_seconds(self) -> float:
        """Calculate execution duration in seconds."""
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def success_rate(self) -> float:
        """Calculate success rate (non-quarantined / fetched)."""
        if self.records_fetched == 0:
            return 1.0
        return (self.records_fetched - self.records_quarantined) / self.records_fetched

    @property
    def is_success(self) -> bool:
        """Check if run was successful (or dry_run)."""
        return self.status in (PipelineRunResult.SUCCESS, PipelineRunResult.DRY_RUN)


@dataclass(frozen=True)
class RunOptions:
    """Options for running a pipeline."""

    run_type: str = "incremental"
    resume: bool = False
    start_offset: int | None = None
    limit: int | None = None
    dry_run: bool = False
    input_csv: str | None = None
    filter_column: str | None = None
    filter_field: str | None = None
    filter_ids: tuple[str, ...] | None = None
    multi_filter_ids: dict[str, tuple[str, ...]] | None = None
    fallback_column: str | None = None
    fallback_mapping: dict[str, str] | None = None
    vacuum_after_run: bool | None = None
    vacuum_retention_days: int | None = None
    log_level: str = "INFO"
    ignore_yaml_filter: bool = False
    skip_gold: bool = False
    execution_context: str = "isolated"
    use_cached_bronze: bool = False
    cached_bronze_path: str | None = None
    cached_bronze_date: str | None = None
    replay_of_run_id: str | None = None
    replay_of_manifest_id: str | None = None
    exact_replay: bool = False
    enable_tracing: bool | None = None


class PipelineNotFoundError(ValueError):
    """Raised when a pipeline is not found in the registry."""

    def __init__(self, pipeline_name: str, available: list[str]) -> None:
        self.pipeline_name = pipeline_name
        self.available = available
        super().__init__(f"Unknown pipeline: {pipeline_name}. Available: {available}")
