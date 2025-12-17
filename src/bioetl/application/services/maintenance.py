"""Maintenance service for pipeline administration.

Handles non-pipeline-execution tasks like inspecting quarantine,
managing checkpoints, and other administrative functions.
"""

from dataclasses import dataclass
from typing import Any

from bioetl.domain.ports import CheckpointPort, QuarantinePort


@dataclass(frozen=True)
class QuarantineStats:
    """Statistics for quarantined records."""

    total_records: int
    by_error_type: dict[str, int]


class MaintenanceService:
    """Application-level service for pipeline maintenance."""

    def __init__(
        self,
        quarantine: QuarantinePort,
        checkpoint: CheckpointPort,
    ) -> None:
        self._quarantine = quarantine
        self._checkpoint = checkpoint

    async def get_quarantine_stats(self) -> QuarantineStats:
        """Get statistics about quarantined records."""
        # Note: This assumes QuarantinePort has get_stats().
        # If not, we might need to cast or expand the port definition.
        # Based on previous context, we use the port directly.
        raw_stats: dict[str, Any] = await self._quarantine.get_stats()

        return QuarantineStats(
            total_records=raw_stats.get("total", 0),
            by_error_type=raw_stats.get("by_error_type", {}),
        )

    async def list_checkpoints(self) -> list[str]:
        """List all available checkpoints."""
        return await self._checkpoint.list_all()
