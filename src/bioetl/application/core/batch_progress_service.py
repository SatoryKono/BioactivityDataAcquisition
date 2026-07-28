"""Progress tracking service for BatchExecutor runtime."""

from __future__ import annotations

__all__ = ["BatchProgressService"]

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort

class BatchProgressService:
    """Tracks and emits pipeline progress during batch execution."""

    def __init__(self, *, logger: LoggerPort, data_source: object) -> None:
        self._logger = logger
        self._data_source = data_source
        self._total_records: int | None = None
        self._progress_interval: int | None = None
        self._next_progress_threshold: int = 0

    async def initialize_tracking(self, limit: int | None) -> None:
        """Estimate total records and initialize progress thresholds.

        Args:
            limit: Optional upper bound on records to process. If provided, used
                directly as the total. If None, attempts to query the data source
                for an estimated total.
        """
        self._total_records = limit
        if self._total_records:
            self._set_progress_thresholds()
            return

        get_total = getattr(self._data_source, "get_total_records", None)
        if get_total and callable(get_total):
            from collections.abc import Awaitable, Callable
            from typing import cast

            get_total_fn = cast(Callable[[], Awaitable[object]], get_total)
            result = await get_total_fn()
            if isinstance(result, int) and result > 0:
                self._total_records = result
                self._set_progress_thresholds()

    def report_progress(
        self,
        *,
        records_fetched: int,
        records_bronze: int,
        records_silver: int,
        records_filtered_out: int,
    ) -> None:
        """Emit progress log when next reporting threshold is reached.

        Args:
            records_fetched: Total records received from the data source so far.
            records_bronze: Total records written to Bronze layer so far.
            records_silver: Total records written to Silver layer so far.
            records_filtered_out: Total records discarded by filters so far.
        """
        if (
            self._progress_interval
            and self._total_records
            and records_fetched >= self._next_progress_threshold
        ):
            pct = min(100, (records_fetched / self._total_records) * 100)
            self._logger.info(
                "Pipeline progress",
                progress=f"{pct:.0f}%",
                bronze=records_bronze,
                silver=records_silver,
                filtered_out=records_filtered_out,
                fetched=records_fetched,
            )
            self._next_progress_threshold += self._progress_interval

    def _set_progress_thresholds(self) -> None:
        """Initialize interval and first threshold from total-record estimate."""
        total_records = self._total_records
        if total_records is None:
            return
        self._progress_interval = max(1, total_records // 10)
        self._next_progress_threshold = self._progress_interval
        self._logger.info(
            "Starting pipeline with total records estimate",
            total_records=total_records,
            progress_interval=self._progress_interval,
        )
