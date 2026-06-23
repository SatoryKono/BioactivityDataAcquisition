"""Finalizer callback builders for metadata writer public methods."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import cast

from bioetl.domain.models.metadata import GoldMetadata, SilverMetadata
from bioetl.infrastructure.storage.metadata_writer_helpers import (
    _apply_gold_metadata_finalization,
    _apply_silver_metadata_finalization,
)


def build_silver_metadata_finalizer(
    *,
    dq_report_path: str | None,
    completed_at: datetime | None,
    delta_version_after: int | None,
) -> Callable[[SilverMetadata | GoldMetadata], None]:
    """Build the Silver metadata finalization callback."""

    def apply_finalization(metadata: SilverMetadata | GoldMetadata) -> None:
        _apply_silver_metadata_finalization(
            metadata=cast("SilverMetadata", metadata),
            dq_report_path=dq_report_path,
            completed_at=completed_at,
            delta_version_after=delta_version_after,
        )

    return apply_finalization


def build_gold_metadata_finalizer(
    *,
    dq_report_path: str | None,
    completed_at: datetime | None,
) -> Callable[[SilverMetadata | GoldMetadata], None]:
    """Build the Gold metadata finalization callback."""

    def apply_finalization(metadata: SilverMetadata | GoldMetadata) -> None:
        _apply_gold_metadata_finalization(
            metadata=cast("GoldMetadata", metadata),
            dq_report_path=dq_report_path,
            completed_at=completed_at,
        )

    return apply_finalization


__all__ = ["build_gold_metadata_finalizer", "build_silver_metadata_finalizer"]
