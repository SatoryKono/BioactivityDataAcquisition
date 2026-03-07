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
        """Factory for successful dependency result."""
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
    ) -> DependencyResult:
        """Factory for failed dependency result."""
        return cls(
            pipeline_name=pipeline_name,
            status=DependencyStatus.FAILED,
            error_message=error_message,
            duration_seconds=duration_seconds,
        )

    @classmethod
    def skipped(
        cls,
        pipeline_name: str,
        reason: str = "Already completed",
    ) -> DependencyResult:
        """Factory for skipped dependency result."""
        return cls(
            pipeline_name=pipeline_name,
            status=DependencyStatus.SKIPPED,
            error_message=reason,
        )

    @classmethod
    def timeout(
        cls,
        pipeline_name: str,
        timeout_seconds: float,
    ) -> DependencyResult:
        """Factory for timeout dependency result."""
        return cls(
            pipeline_name=pipeline_name,
            status=DependencyStatus.TIMEOUT,
            error_message=f"Timeout after {timeout_seconds}s",
            duration_seconds=timeout_seconds,
        )
