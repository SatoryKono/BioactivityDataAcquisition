"""Enrichment result models for composite pipelines."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class EnrichmentStatus(StrEnum):
    """Status of enrichment pipeline execution."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"
    NOT_RUN = "not_run"
    TIMEOUT = "timeout"


@dataclass(frozen=True, slots=True)
class EnrichmentResult:
    """Result of a single enrichment pipeline execution."""

    enricher_name: str
    status: EnrichmentStatus
    records_input: int = 0
    records_enriched: int = 0
    records_not_found: int = 0
    records_errored: int = 0
    dq_error_rate: float = 0.0
    duration_seconds: float = 0.0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Validate result invariants."""
        for name, value in (
            ("records_input", self.records_input),
            ("records_enriched", self.records_enriched),
            ("records_not_found", self.records_not_found),
            ("records_errored", self.records_errored),
        ):
            if value < 0:
                raise ValueError(f"{name} must be >= 0, got {value}")
        if self.records_enriched > self.records_input:
            raise ValueError(
                "records_enriched cannot exceed records_input: "
                f"{self.records_enriched} > {self.records_input}"
            )
        if self.records_not_found > self.records_input:
            raise ValueError(
                "records_not_found cannot exceed records_input: "
                f"{self.records_not_found} > {self.records_input}"
            )
        if not 0.0 <= self.dq_error_rate <= 1.0:
            raise ValueError(f"dq_error_rate must be 0.0-1.0, got {self.dq_error_rate}")
        if self.duration_seconds < 0.0:
            raise ValueError(
                f"duration_seconds must be >= 0, got {self.duration_seconds}"
            )

    @property
    def is_success(self) -> bool:
        """Check if enrichment succeeded, partially succeeded, or was skipped."""
        return self.status in (
            EnrichmentStatus.SUCCESS,
            EnrichmentStatus.PARTIAL,
            EnrichmentStatus.SKIPPED,
        )

    @property
    def enrichment_rate(self) -> float:
        """Calculate enrichment success rate (0.0-1.0)."""
        return self.records_enriched / self.records_input if self.records_input else 0.0

    @property
    def not_found_rate(self) -> float:
        """Calculate not-found rate (0.0-1.0)."""
        return (
            self.records_not_found / self.records_input if self.records_input else 0.0
        )

    @classmethod
    def success(
        cls,
        enricher_name: str,
        records_input: int,
        records_enriched: int,
        records_not_found: int = 0,
        duration_seconds: float = 0.0,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> EnrichmentResult:
        """Factory for successful enrichment result.

        Args:
            enricher_name: Enricher pipeline name.
            records_input: Records input.
            records_enriched: Records enriched.
            records_not_found: Records not found.
            duration_seconds: Duration seconds.
            started_at: Started at.
            completed_at: Completed at.

        Returns:
            The EnrichmentResult result.
        """
        return cls(
            enricher_name=enricher_name,
            status=EnrichmentStatus.SUCCESS,
            records_input=records_input,
            records_enriched=records_enriched,
            records_not_found=records_not_found,
            duration_seconds=duration_seconds,
            started_at=started_at,
            completed_at=completed_at,
        )

    @classmethod
    def failed(
        cls,
        enricher_name: str,
        error_message: str,
        records_input: int = 0,
        duration_seconds: float = 0.0,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> EnrichmentResult:
        """Factory for failed enrichment result.

        Args:
            enricher_name: Enricher pipeline name.
            error_message: Error message.
            records_input: Records input.
            duration_seconds: Duration seconds.
            started_at: Started at.
            completed_at: Completed at.

        Returns:
            The EnrichmentResult result.
        """
        return cls(
            enricher_name=enricher_name,
            status=EnrichmentStatus.FAILED,
            records_input=records_input,
            error_message=error_message,
            duration_seconds=duration_seconds,
            started_at=started_at,
            completed_at=completed_at,
        )

    @classmethod
    def skipped(
        cls,
        enricher_name: str,
        reason: str = "Filter excluded all records",
    ) -> EnrichmentResult:
        """Factory for skipped enrichment result.

        Args:
            enricher_name: Enricher pipeline name.
            reason: Reason description.

        Returns:
            The EnrichmentResult result.
        """
        return cls(
            enricher_name=enricher_name,
            status=EnrichmentStatus.SKIPPED,
            error_message=reason,
        )

    @classmethod
    def timeout(
        cls,
        enricher_name: str,
        timeout_seconds: float,
        records_input: int = 0,
        duration_seconds: float | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> EnrichmentResult:
        """Factory for timeout enrichment result.

        Args:
            enricher_name: Enricher pipeline name.
            timeout_seconds: Timeout seconds.
            records_input: Records input.
            duration_seconds: Observed duration before timeout. Defaults to timeout_seconds.
            started_at: Started at.
            completed_at: Completed at.

        Returns:
            The EnrichmentResult result.
        """
        if not math.isfinite(timeout_seconds) or timeout_seconds < 0.0:
            raise ValueError(
                f"timeout_seconds must be finite and >= 0, got {timeout_seconds}"
            )
        resolved_duration = (
            timeout_seconds if duration_seconds is None else duration_seconds
        )
        return cls(
            enricher_name=enricher_name,
            status=EnrichmentStatus.TIMEOUT,
            records_input=records_input,
            error_message=f"Timeout after {timeout_seconds}s",
            duration_seconds=resolved_duration,
            started_at=started_at,
            completed_at=completed_at,
        )

    @classmethod
    def not_run(
        cls,
        enricher_name: str,
        reason: str = "Pipeline not executed (required_only mode)",
    ) -> EnrichmentResult:
        """Factory for not-run enrichment result.

        Args:
            enricher_name: Enricher pipeline name.
            reason: Reason description.

        Returns:
            The EnrichmentResult result.
        """
        return cls(
            enricher_name=enricher_name,
            status=EnrichmentStatus.NOT_RUN,
            error_message=reason,
        )


__all__ = ["EnrichmentResult", "EnrichmentStatus"]
