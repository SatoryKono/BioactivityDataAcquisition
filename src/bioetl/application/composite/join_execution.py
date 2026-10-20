"""Join execution helpers for Polars DataFrames."""

from __future__ import annotations

__all__ = [
    "JoinCardinalityError",
    "JoinExecutorService",
    "JoinHow",
    "RequiredJoinKeyError",
]


from collections.abc import Callable
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.ports import LoggerPort


JoinHow = Literal["inner", "left", "right", "full", "semi", "anti", "cross"]


class RequiredJoinKeyError(ValueError):
    """Required join failed closed: a key column is missing or seed rows are unmatched."""


class JoinCardinalityError(ValueError):
    """Optional left join changed the seed row count."""


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

    def _resolve_how(
        self,
        *,
        required: bool,
        join_how: JoinHow | None,
    ) -> JoinHow:
        """Resolve Polars ``how`` for one join.

        An explicit ``join_how`` wins. Otherwise ADR-026 maps a required source
        to ``inner`` and leaves optional sources on the configured strategy.
        """
        if join_how is not None:
            return join_how
        if required:
            return "inner"
        return self.get_polars_join_type()

    def _reject_missing_keys(
        self,
        *,
        required: bool,
        pipeline_name: str,
        missing_left: list[str],
        missing_right: list[str],
        left_df: pl.DataFrame,
    ) -> pl.DataFrame | None:
        """Return ``left_df`` when an optional join skips missing keys.

        Required joins fail closed instead of returning the unjoined frame.
        """
        if not missing_left and not missing_right:
            return None
        if required:
            raise RequiredJoinKeyError(
                "Required join key columns are missing for "
                f"{pipeline_name}: left={missing_left}, right={missing_right}"
            )
        self._logger.warning(
            "Join skipped: key not found in columns",
            pipeline=pipeline_name,
            missing_left=missing_left,
            missing_right=missing_right,
            left_rows=left_df.height,
        )
        return left_df

    def _reject_required_cardinality(
        self,
        *,
        required: bool,
        join_how: JoinHow | None,
        pipeline_name: str,
        left_height: int,
        result_height: int,
    ) -> None:
        """Fail a required join whose row count differs from the seed frame."""
        if not required or join_how is not None or result_height == left_height:
            return
        raise RequiredJoinKeyError(
            f"Required join for {pipeline_name} changed cardinality "
            f"from {left_height} to {result_height}"
        )

    def execute_polars_join(
        self,
        left_df: pl.DataFrame,
        right_df: pl.DataFrame,
        left_key: str,
        right_key: str,
        pipeline_name: str,
        required: bool = False,
        join_how: JoinHow | None = None,
    ) -> pl.DataFrame:
        """Execute single-key join while preserving right join key as data column.

        Args:
            left_df: Left-side DataFrame (typically the merged seed output).
            right_df: Right-side DataFrame (typically the enricher or dependency output).
            left_key: Column name to join on from left_df.
            right_key: Column name to join on from right_df.
            pipeline_name: Pipeline name used for column suffixing and log context.
            required: When true, missing keys and unmatched seed rows fail closed
                and the join uses INNER semantics (ADR-026).
            join_how: Optional explicit Polars join type. Used by fallback steps
                that must stay LEFT even when the source is required.

        Returns:
            Joined DataFrame. Optional joins with a missing key return ``left_df``.
        """
        import polars as pl

        how = self._resolve_how(required=required, join_how=join_how)
        missing_left = [] if left_key in left_df.columns else [left_key]
        missing_right = [] if right_key in right_df.columns else [right_key]
        skipped = self._reject_missing_keys(
            required=required,
            pipeline_name=pipeline_name,
            missing_left=missing_left,
            missing_right=missing_right,
            left_df=left_df,
        )
        if skipped is not None:
            return skipped

        if left_df[left_key].dtype != right_df[right_key].dtype:
            self._logger.debug(
                "Coercing join keys to String due to type mismatch",
                pipeline=pipeline_name,
                left_key=left_key,
                left_type=str(left_df[left_key].dtype),
                right_key=right_key,
                right_type=str(right_df[right_key].dtype),
            )
            left_cast = pl.col(left_key).cast(pl.String)
            if left_df[left_key].dtype.is_float():
                left_cast = left_cast.str.replace(r"\.0$", "", literal=False)
            left_df = left_df.with_columns(left_cast)

            right_cast = pl.col(right_key).cast(pl.String)
            if right_df[right_key].dtype.is_float():
                right_cast = right_cast.str.replace(r"\.0$", "", literal=False)
            right_df = right_df.with_columns(right_cast)

        if left_key != right_key:
            temp_join_col = f"__temp_join_{pipeline_name}"
            right_df = right_df.with_columns(pl.col(right_key).alias(temp_join_col))
            result = left_df.join(
                right_df,
                left_on=left_key,
                right_on=temp_join_col,
                how=how,
                suffix=f"_{pipeline_name}",
            )
        else:
            result = left_df.join(
                right_df,
                left_on=left_key,
                right_on=right_key,
                how=how,
                suffix=f"_{pipeline_name}",
            )
        self._reject_required_cardinality(
            required=required,
            join_how=join_how,
            pipeline_name=pipeline_name,
            left_height=left_df.height,
            result_height=result.height,
        )
        return result

    def execute_composite_key_join(
        self,
        left_df: pl.DataFrame,
        right_df: pl.DataFrame,
        left_keys: list[str],
        right_keys: list[str],
        pipeline_name: str,
        required: bool = False,
        join_how: JoinHow | None = None,
    ) -> pl.DataFrame:
        """Execute multi-key join preserving right-side key columns.

        Args:
            left_df: Left-side DataFrame (typically the merged seed output).
            right_df: Right-side DataFrame (typically the dependency output).
            left_keys: List of column names to join on from left_df.
            right_keys: List of column names to join on from right_df.
            pipeline_name: Pipeline name used for column suffixing and log context.
            required: When true, missing composite keys and unmatched seed rows
                fail closed with INNER semantics (ADR-026).
            join_how: Optional explicit Polars join type.

        Returns:
            Joined DataFrame using all provided composite key columns.
        """
        import polars as pl

        how = self._resolve_how(required=required, join_how=join_how)
        skipped = self._reject_missing_keys(
            required=required,
            pipeline_name=pipeline_name,
            missing_left=[key for key in left_keys if key not in left_df.columns],
            missing_right=[key for key in right_keys if key not in right_df.columns],
            left_df=left_df,
        )
        if skipped is not None:
            return skipped
        if left_keys == right_keys:
            result = left_df.join(
                right_df,
                on=left_keys,
                how=how,
                suffix=f"_{pipeline_name}",
            )
        else:
            temp_cols: list[str] = []
            for left_key, right_key in zip(left_keys, right_keys, strict=True):
                if left_key != right_key:
                    temp_col = f"__temp_join_{pipeline_name}_{right_key}"
                    right_df = right_df.with_columns(pl.col(right_key).alias(temp_col))
                    temp_cols.append(temp_col)
                else:
                    temp_cols.append(right_key)

            result = left_df.join(
                right_df,
                left_on=left_keys,
                right_on=temp_cols,
                how=how,
                suffix=f"_{pipeline_name}",
            )
        self._reject_required_cardinality(
            required=required,
            join_how=join_how,
            pipeline_name=pipeline_name,
            left_height=left_df.height,
            result_height=result.height,
        )
        return result
