"""Stage counter component for tracking records processed by stages."""

from datetime import datetime, timezone

from bioetl.domain.models import StageResult
from bioetl.domain.value_objects import StageName


class StageCounter:
    """Tracks record and chunk counts per pipeline stage."""

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}
        self._chunks: dict[str, int] = {}
        self._stage_starts: dict[str, datetime] = {}

    def increment(self, stage: str, count: int) -> None:
        """Increment record count for a stage."""
        self._counts[stage] = self._counts.get(stage, 0) + count

    def increment_chunks(self, stage: str, count: int = 1) -> None:
        """Increment chunk count for a stage."""
        self._chunks[stage] = self._chunks.get(stage, 0) + count

    def get_count(self, stage: str) -> int:
        """Return record count for a stage."""
        return self._counts.get(stage, 0)

    def get_chunks(self, stage: str) -> int:
        """Return chunk count for a stage."""
        return self._chunks.get(stage, 0)

    def get_counts(self) -> dict[str, int]:
        """Return all stage record counts."""
        return dict(self._counts)

    def get_all_chunks(self) -> dict[str, int]:
        """Return all stage chunk counts."""
        return dict(self._chunks)

    def mark_stage_start(self, stage: str) -> None:
        """Record start time for a stage."""
        self._stage_starts[stage] = datetime.now(timezone.utc)

    def get_stage_start(self, stage: str) -> datetime | None:
        """Return start time for a stage, if recorded."""
        return self._stage_starts.get(stage)

    def reset(self) -> None:
        """Clear all counts and timestamps."""
        self._counts.clear()
        self._chunks.clear()
        self._stage_starts.clear()

    def make_stage_result(
        self,
        stage: str,
        *,
        success: bool = True,
        errors: list[str] | None = None,
        override_count: int | None = None,
        override_chunks: int | None = None,
    ) -> StageResult:
        """Build a StageResult with duration and counters."""
        start_time = self.get_stage_start(stage)
        duration = 0.0
        if start_time:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        count = override_count if override_count is not None else self.get_count(stage)
        chunks = (
            override_chunks if override_chunks is not None else self.get_chunks(stage)
        )

        return StageResult(
            stage_name=StageName(stage),
            success=success,
            records_processed=count if success else 0,
            chunks_processed=chunks if success else 0,
            duration_sec=duration,
            errors=errors or [],
        )
