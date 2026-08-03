"""Join execution helpers for Polars DataFrames."""

from __future__ import annotations

__all__ = ["JoinExecutorService", "JoinHow"]


from collections.abc import Callable
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.ports import LoggerPort


JoinHow = Literal["inner", "left", "right", "full", "semi", "anti", "cross", "outer"]


class JoinExecutorService:
    """Execute single-key and composite-key joins with safety checks."""

    def __init__(
        self,
        *,
        logger: LoggerPort,
        join_type_resolver: Callable[[], JoinHow],
    ) -> None:
        self._logger = logger
        self._join_type_resolver = join_type_resolver

    def get_polars_join_type(self) -> JoinHow:
        """Resolve current join type from strategy resolver.

        Returns:
            Polars join type literal (e.g. ``"left"``, ``"inner"``, ``"full"``).
        """
        return self._join_type_resolver()

    def execute_polars_join(
        self,
        left_df: pl.DataFrame,
        right_df: pl.DataFrame,
        left_key: str,
        right_key: str,
        pipeline_name: str,
    ) -> pl.DataFrame:
        """Execute single-key join while preserving right join key as data column.

        Args:
            left_df: Left-side DataFrame (typically the merged seed output).
            right_df: Right-side DataFrame (typically the enricher or dependency output).
            left_key: Column name to join on from left_df.
            right_key: Column name to join on from right_df.
            pipeline_name: Pipeline name used for column suffixing and log context.

        Returns:
            Joined DataFrame; returns left_df unchanged if a required join key is missing.
        """
        import polars as pl

        how = self.get_polars_join_type()

        if left_key not in left_df.columns or right_key not in right_df.columns:
            self._logger.warning(
                "Join skipped: key not found in columns",
                pipeline=pipeline_name,
                left_key=left_key,
                right_key=right_key,
                left_columns=left_df.columns
                if left_key not in left_df.columns
                else None,
                right_columns=right_df.columns
                if right_key not in right_df.columns
                else None,
            )
            return left_df

        if left_df[left_key].dtype != right_df[right_key].dtype:
            self._logger.debug(
                "Coercing join keys to String due to type mismatch",
                pipeline=pipeline_name,
                left_key=left_key,
                left_type=str(left_df[left_key].dtype),
                right_key=right_key,
                right_type=str(right_df[right_key].dtype),
            )
            left_df = left_df.with_columns(
                pl.col(left_key)
                .cast(pl.String)
                .str.replace(r"\\.0$", "", literal=False)
            )
            right_df = right_df.with_columns(
                pl.col(right_key)
                .cast(pl.String)
                .str.replace(r"\\.0$", "", literal=False)
            )

        if left_key != right_key:
            temp_join_col = f"__temp_join_{pipeline_name}"
            right_df = right_df.with_columns(pl.col(right_key).alias(temp_join_col))
            return left_df.join(
                right_df,
                left_on=left_key,
                right_on=temp_join_col,
                how=how,
                suffix=f"_{pipeline_name}",
            )

        return left_df.join(
            right_df,
            left_on=left_key,
            right_on=right_key,
            how=how,
            suffix=f"_{pipeline_name}",
        )

    def execute_composite_key_join(
        self,
        left_df: pl.DataFrame,
        right_df: pl.DataFrame,
        left_keys: list[str],
        right_keys: list[str],
        pipeline_name: str,
    ) -> pl.DataFrame:
        """Execute multi-key join preserving right-side key columns.

        Args:
            left_df: Left-side DataFrame (typically the merged seed output).
            right_df: Right-side DataFrame (typically the dependency output).
            left_keys: List of column names to join on from left_df.
            right_keys: List of column names to join on from right_df.
            pipeline_name: Pipeline name used for column suffixing and log context.

        Returns:
            Joined DataFrame using all provided composite key columns.
        """
        import polars as pl

        how = self.get_polars_join_type()
        if left_keys == right_keys:
            return left_df.join(
                right_df,
                on=left_keys,
                how=how,
                suffix=f"_{pipeline_name}",
            )

        temp_cols: list[str] = []
        for left_key, right_key in zip(left_keys, right_keys, strict=True):
            if left_key != right_key:
                temp_col = f"__temp_join_{pipeline_name}_{right_key}"
                right_df = right_df.with_columns(pl.col(right_key).alias(temp_col))
                temp_cols.append(temp_col)
            else:
                temp_cols.append(right_key)

        return left_df.join(
            right_df,
            left_on=left_keys,
            right_on=temp_cols,
            how=how,
            suffix=f"_{pipeline_name}",
        )
