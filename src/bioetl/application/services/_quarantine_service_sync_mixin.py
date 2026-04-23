"""Synchronous quarantine admin timing helpers for QuarantineService."""

from __future__ import annotations

from datetime import datetime

from bioetl.application.runtime_timestamps import (
    capture_runtime_timing_anchor,
    derive_completion_timestamp,
)
from bioetl.application.services._quarantine_service_sync_operations import (
    QuarantineServiceReplayPurgeSyncMixin,
    QuarantineServiceStatusSyncMixin,
)


class QuarantineServiceSyncMixin(
    QuarantineServiceReplayPurgeSyncMixin,
    QuarantineServiceStatusSyncMixin,
):
    """Sync quarantine timing helpers plus delegated admin operations."""

    @staticmethod
    def _capture_operator_timing_anchor() -> tuple[datetime, float]:
        """Capture the canonical operator timing anchor for one sync admin flow."""
        return capture_runtime_timing_anchor()

    @staticmethod
    def _derive_operator_completion(
        *,
        started_at: datetime,
        started_monotonic: float,
    ) -> tuple[datetime, float]:
        """Derive completion timestamp/duration from the captured operator anchor."""
        return derive_completion_timestamp(
            started_at=started_at,
            started_monotonic=started_monotonic,
        )
