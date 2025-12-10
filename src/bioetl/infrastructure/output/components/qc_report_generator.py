"""QC report generator component implementation."""

from __future__ import annotations

import pandas as pd

from bioetl.domain.ports.output import QcReportGeneratorPort


class QcReportGenerator(QcReportGeneratorPort):
    """Generator for quality control reports.

    This component builds quality and correlation reports
    without knowledge of file writing or metadata concerns.
    """

    def build_quality_report(
        self, df: pd.DataFrame, *, min_coverage: float
    ) -> pd.DataFrame:
        """Compute null/coverage metrics per column with coverage threshold.

        Args:
            df: Source DataFrame to analyze.
            min_coverage: Minimum required coverage (0.0 to 1.0).

        Returns:
            DataFrame with columns: column, null_count, non_null_count,
            unique_count, dtype, coverage, coverage_ok.
        """
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
                "coverage": (
                    coverage.values if hasattr(coverage, "values") else coverage
                ),
                "coverage_ok": (
                    (coverage >= min_coverage).values
                    if hasattr(coverage, "values")
                    else False
                ),
            }
        )

        return report.sort_values(by="column", ignore_index=True)

    def build_correlation_report(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate numeric correlation matrix with stable ordering.

        Args:
            df: Source DataFrame.

        Returns:
            DataFrame with correlation matrix. First column is 'column'
            containing row labels, remaining columns are correlations.
        """
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


__all__ = ["QcReportGenerator"]
