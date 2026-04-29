"""Composition-facing bridge for composite Polars join execution."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.composite.join_execution import JoinExecutorService

if TYPE_CHECKING:
    import polars as pl
    from polars._typing import JoinStrategy as JoinHow


class PolarsJoinBridge:
    """Bridge wrapper for JoinExecutorService in composition layer.

    This real adapter provides composition-specific interface and behavior
    while delegating to the underlying JoinExecutorService.
    """

    def __init__(self, join_service: JoinExecutorService) -> None:
        """Initialize adapter with underlying join service.

        Args:
            join_service: The JoinExecutorService to adapt
        """
        self._join_service = join_service

    def get_polars_join_type(self) -> JoinHow:
        """Get current join type from adapted service."""
        return self._join_service.get_polars_join_type()

    def execute_polars_join(
        self,
        left_df: pl.DataFrame,
        right_df: pl.DataFrame,
        left_key: str,
        right_key: str,
        pipeline_name: str,
    ) -> pl.DataFrame:
        """Execute join through adapted service."""
        return self._join_service.execute_polars_join(
            left_df,
            right_df,
            left_key,
            right_key,
            pipeline_name,
        )

    def execute_composite_key_join(
        self,
        left_df: pl.DataFrame,
        right_df: pl.DataFrame,
        left_keys: list[str],
        right_keys: list[str],
        pipeline_name: str,
    ) -> pl.DataFrame:
        """Execute composite-key join through adapted service."""
        return self._join_service.execute_composite_key_join(
            left_df,
            right_df,
            left_keys,
            right_keys,
            pipeline_name,
        )


__all__ = ["PolarsJoinBridge"]


# Backward-compatible alias retained while composition callers migrate to the
# Bridge suffix. New code should use PolarsJoinBridge directly.
PolarsJoinAdapter = PolarsJoinBridge
