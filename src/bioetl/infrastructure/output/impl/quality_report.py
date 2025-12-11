"""Quality report generator implementation.

This module provides a concrete implementation of QualityReportABC
that delegates to QcReportGenerator to avoid code duplication.
"""

from __future__ import annotations

import pandas as pd

from bioetl.domain.clients.base.output.contracts import QualityReportABC
from bioetl.infrastructure.output.components.qc_report_generator import (
    QcReportGenerator,
)


class QualityReportImpl(QualityReportABC):
    """Pandas-based QC report generator.

    This class delegates to QcReportGenerator to avoid code duplication.
    It exists to maintain compatibility with QualityReportABC interface.
    """

    def __init__(self) -> None:
        self._generator = QcReportGenerator()

    def build_quality_report(
        self, df: pd.DataFrame, *, min_coverage: float
    ) -> pd.DataFrame:
        """Compute null/coverage metrics per column with coverage threshold."""
        return self._generator.build_quality_report(df, min_coverage=min_coverage)

    def build_correlation_report(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate numeric correlation matrix with stable ordering."""
        return self._generator.build_correlation_report(df)
