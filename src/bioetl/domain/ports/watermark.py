"""Watermark strategy port for incremental data loading.

This module defines the interface for watermark-based incremental loading.
Currently a placeholder for future implementation (ADR-031).

IMPORTANT: Watermark-based loading requires:
1. Confirmed watermark field availability in source API
2. Reliable timestamp/version tracking on the source side
3. Proper handling of late-arriving data

Do NOT implement without confirming API support for watermark fields.
"""

from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class WatermarkStrategyPort(Protocol):
    """Port for watermark-based incremental loading strategy.

    Defines the interface for managing watermarks that track the progress
    of incremental data extraction. Watermarks are typically timestamps
    or version numbers that identify the last successfully processed record.

    This is a PLACEHOLDER interface for future implementation.
    Current status: NOT IMPLEMENTED.

    Requirements for implementation:
    1. Source API must provide a reliable watermark field (e.g., updated_at)
    2. Watermark field must be monotonically increasing
    3. Source must support filtering by watermark (e.g., WHERE updated_at > watermark)

    Example usage (future):
        >>> strategy = WatermarkStrategy(checkpoint_port, "updated_at")
        >>> last_watermark = await strategy.get_watermark("chembl_activity")
        >>> # Fetch records WHERE updated_at > last_watermark
        >>> await strategy.update_watermark("chembl_activity", new_watermark)

    See Also:
        ADR-030: Publication pagination strategy (full_scan_only)
        ADR-031: Loading strategy formalization
        LoadingStrategy: Enum controlling which strategy is used
    """

    @abstractmethod
    async def get_watermark(self, pipeline_name: str) -> datetime | int | str | None:
        """Get the current watermark for a pipeline.

        Args:
            pipeline_name: Name of the pipeline to get watermark for.

        Returns:
            The current watermark value (timestamp, version number, or ID),
            or None if no watermark exists (first run).
        """
        ...

    @abstractmethod
    async def update_watermark(
        self,
        pipeline_name: str,
        watermark: datetime | int | str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update the watermark after successful processing.

        Args:
            pipeline_name: Name of the pipeline to update watermark for.
            watermark: New watermark value to store.
            metadata: Optional metadata about the processing run.
        """
        ...

    @abstractmethod
    async def clear_watermark(self, pipeline_name: str) -> None:
        """Clear the watermark for a pipeline (triggers full reload).

        Args:
            pipeline_name: Name of the pipeline to clear watermark for.
        """
        ...


class NoOpWatermarkStrategy:
    """No-operation implementation of WatermarkStrategyPort.

    Used as a placeholder when watermark-based loading is not available.
    Always returns None for watermark and does nothing on update.

    This is the DEFAULT implementation until watermark support is added.
    """

    async def get_watermark(self, _pipeline_name: str) -> None:
        """Always returns None (no watermark available).

        Args:
            _pipeline_name: Ignored (intentionally unused in no-op).

        Returns:
            None, indicating no watermark support.
        """
        return None

    async def update_watermark(
        self,
        _pipeline_name: str,
        _watermark: datetime | int | str,
        _metadata: dict[str, Any] | None = None,
    ) -> None:
        """No-op: does nothing.

        Args:
            _pipeline_name: Ignored (intentionally unused in no-op).
            _watermark: Ignored (intentionally unused in no-op).
            _metadata: Ignored (intentionally unused in no-op).
        """
        pass

    async def clear_watermark(self, _pipeline_name: str) -> None:
        """No-op: does nothing.

        Args:
            _pipeline_name: Ignored (intentionally unused in no-op).
        """
        pass
