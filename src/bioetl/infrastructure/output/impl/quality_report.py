"""Quality report generator implementation."""
from __future__ import annotations

import pandas as pd

from bioetl.infrastructure.output.contracts import QualityReportABC


class QualityReportImpl(QualityReportABC):
    """Генератор QC-отчетов на базе Pandas."""

    def build_quality_report(
        self, df: pd.DataFrame, *, min_coverage: float
    ) -> pd.DataFrame:
        row_count = len(df.index)
        nulls = df.isnull().sum()
        non_nulls = df.notnull().sum()
        unique_counts = df.nunique(dropna=True)
        coverage = non_nulls / row_count if row_count > 0 else 0.0

        report = pd.DataFrame(
            {
                "column": df.columns,
                "null_count": nulls.values,
                "non_null_count": non_nulls.values,
                "unique_count": unique_counts.values,
                "dtype": df.dtypes.values.astype(str),
                "coverage": coverage.values if hasattr(coverage, "values") else coverage,
                "coverage_ok": (coverage >= min_coverage).values
                if hasattr(coverage, "values")
                else False,
            }
        )

        return report.sort_values(by="column", ignore_index=True)

    def build_correlation_report(self, df: pd.DataFrame) -> pd.DataFrame:
        numeric_columns = sorted(
            c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])
        )
        if not numeric_columns:
            return pd.DataFrame(columns=["column"])

        numeric_df = df[numeric_columns].copy()
        for column in numeric_columns:
            if pd.api.types.is_bool_dtype(numeric_df[column]):
                numeric_df[column] = numeric_df[column].astype(int)

        correlation = numeric_df.corr(numeric_only=True)
        correlation = correlation.loc[numeric_columns, numeric_columns]
        correlation.insert(0, "column", correlation.index)
        return correlation.reset_index(drop=True)
