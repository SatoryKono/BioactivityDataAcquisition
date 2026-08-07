"""Seed and dependency result models for composite pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

__all__ = [
    "DependencyResult",
    "DependencyStatus",
    "SeedResult",
]


@dataclass(frozen=True, slots=True)
class SeedResult:
    """Result of seed pipeline execution."""

    pipeline_name: str
    records_extracted: int = 0
    records_silver: int = 0
    keys_generated: int = 0
    duration_seconds: float = 0.0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    resumed: bool = False

    @property
    def is_success(self) -> bool:
        """Check if seed was successful."""
        return self.records_silver > 0 or self.resumed


class DependencyStatus(StrEnum):
    """Status of dependency pipeline execution."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


@dataclass(frozen=True, slots=True)
class DependencyResult:
    """Result of a dependency pipeline execution."""

    pipeline_name: str
    status: DependencyStatus = DependencyStatus.SUCCESS
    records_extracted: int = 0
    records_silver: int = 0
    duration_seconds: float = 0.0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    resumed: bool = False

    @property
    def is_success(self) -> bool:
        """Check if dependency succeeded or was skipped (resume mode)."""
        return self.status in (DependencyStatus.SUCCESS, DependencyStatus.SKIPPED)

    @classmethod
    def success(
        cls,
        pipeline_name: str,
        records_extracted: int,
        records_silver: int,
        duration_seconds: float = 0.0,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> DependencyResult:
        """Factory for successful dependency result.

        Args:
            pipeline_name: Name of the dependency pipeline.
            records_extracted: Number of records extracted from the source.
            records_silver: Number of records written to the Silver layer.
            duration_seconds: Execution duration in seconds. Defaults to 0.0.
            started_at: UTC timestamp when execution started. Defaults to None.
            completed_at: UTC timestamp when execution completed. Defaults to None.

        Returns:
            DependencyResult with SUCCESS status.
        """
        return cls(
            pipeline_name=pipeline_name,
            status=DependencyStatus.SUCCESS,
            records_extracted=records_extracted,
            records_silver=records_silver,
            duration_seconds=duration_seconds,
            started_at=started_at,
            completed_at=completed_at,
        )

    @classmethod
    def failed(
        cls,
        pipeline_name: str,
        error_message: str,
        duration_seconds: float = 0.0,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> DependencyResult:
        """Factory for failed dependency result.

        Args:
            pipeline_name: Name of the dependency pipeline.
            error_message: Human-readable description of the failure.
            duration_seconds: Execution duration before failure. Defaults to 0.0.
            started_at: UTC timestamp when execution started. Defaults to None.
            completed_at: UTC timestamp when execution completed. Defaults to None.

        Returns:
            DependencyResult with FAILED status and error_message set.
        """
        return cls(
            pipeline_name=pipeline_name,
            status=DependencyStatus.FAILED,
            error_message=error_message,
            duration_seconds=duration_seconds,
            started_at=started_at,
            completed_at=completed_at,
        )

    @classmethod
    def skipped(
        cls,
        pipeline_name: str,
        reason: str = "Already completed",
    ) -> DependencyResult:
        """Factory for skipped dependency result.

        Args:
            pipeline_name: Name of the dependency pipeline.
            reason: Human-readable reason why execution was skipped. Defaults to 'Already completed'.

        Returns:
            DependencyResult with SKIPPED status.

        Note:
            ``reason`` is accepted for caller diagnostics only. A successful skip is
            not an error, so ``error_message`` stays ``None``.
        """
        _ = reason  # caller-facing diagnostic only; not an error payload
        return cls(
            pipeline_name=pipeline_name,
            status=DependencyStatus.SKIPPED,
            error_message=None,
        )

    @classmethod
    def timeout(
        cls,
        pipeline_name: str,
        timeout_seconds: float,
        duration_seconds: float | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> DependencyResult:
        """Factory for timeout dependency result.

        Args:
            pipeline_name: Name of the dependency pipeline.
            timeout_seconds: Timeout threshold in seconds that was exceeded.
            duration_seconds: Observed duration before timeout. Defaults to timeout_seconds.
            started_at: UTC timestamp when execution started. Defaults to None.
            completed_at: UTC timestamp when execution completed. Defaults to None.

        Returns:
            DependencyResult with TIMEOUT status. ``duration_seconds`` uses the
            supplied value when provided; otherwise defaults to ``timeout_seconds``.
        """
        return cls(
            pipeline_name=pipeline_name,
            status=DependencyStatus.TIMEOUT,
            error_message=f"Timeout after {timeout_seconds}s",
            duration_seconds=timeout_seconds
            if duration_seconds is None
            else duration_seconds,
            started_at=started_at,
            completed_at=completed_at,
        )
