"""Silver DQ statistics service.

Encapsulates statistical profiling and distribution formatting for Silver DQ.
"""

from __future__ import annotations

import polars as pl

from bioetl.domain.services.dq_serializer import to_dict
from bioetl.domain.value_objects.dq_report import (
    CategoricalDistribution,
    DQCheckStatus,
    NumericDistribution,
    ValueDistributionResult,
)

_SILVER_PROFILE_ERRORS = (
    pl.exceptions.PolarsError,
    ValueError,
    TypeError,
    RuntimeError,
)


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


class SilverDQStatisticsService:
    """Calculate Silver data quality statistical distributions."""

    def check_value_distribution(self, df: pl.DataFrame) -> ValueDistributionResult:
        """Calculate value distributions for a limited subset of columns."""
        numeric_cols: dict[str, NumericDistribution] = {}
        categorical_cols: dict[str, CategoricalDistribution] = {}

        for col in df.columns[:20]:
            dtype = df[col].dtype

            if dtype in (pl.Float64, pl.Float32, pl.Int64, pl.Int32, pl.Int16, pl.Int8):
                try:
                    stats = df[col].drop_nulls().cast(pl.Float64)
                    if len(stats) > 0:
                        numeric_cols[col] = NumericDistribution(
                            min=_to_float(stats.min()),
                            max=_to_float(stats.max()),
                            mean=_to_float(stats.mean()),
                            std=_to_float(stats.std()),
                            median=_to_float(stats.median()),
                        )
                except _SILVER_PROFILE_ERRORS:
                    pass

            elif dtype in (pl.Utf8, pl.Categorical):
                try:
                    value_counts = df[col].value_counts().head(5)
                    cardinality = df[col].n_unique()
                    top_values: list[dict[str, object]] = []
                    for row in value_counts.iter_rows(named=True):
                        val = row.get(col) or row.get("value")
                        count = row.get("count") or row.get("counts", 0)
                        top_values.append(
                            {
                                "value": str(val) if val is not None else None,
                                "count": count,
                                "pct": round(count / len(df), 4) if len(df) > 0 else 0,
                            }
                        )
                    categorical_cols[col] = CategoricalDistribution(
                        top_values=tuple(top_values),
                        cardinality=cardinality,
                    )
                except _SILVER_PROFILE_ERRORS:
                    pass

        return ValueDistributionResult(
            numeric_columns=numeric_cols,
            categorical_columns=categorical_cols,
            status=DQCheckStatus.PASS,
        )

    def distribution_to_dict(
        self, result: ValueDistributionResult
    ) -> dict[str, object]:
        """Convert distribution result to transport-friendly dict."""
        numeric_columns: dict[str, object] = {}
        categorical_columns: dict[str, object] = {}

        for col, numeric_dist in result.numeric_columns.items():
            numeric_columns[col] = to_dict(numeric_dist)

        for col, categorical_dist in result.categorical_columns.items():
            categorical_columns[col] = {
                "top_values": list(categorical_dist.top_values),
                "cardinality": categorical_dist.cardinality,
            }

        return {
            "numeric_columns": numeric_columns,
            "categorical_columns": categorical_columns,
            "status": result.status.value,
        }


__all__ = ["SilverDQStatisticsService"]
