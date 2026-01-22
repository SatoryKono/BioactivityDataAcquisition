"""Data quality exceptions.

These errors signal data quality issues (business rules, anomalies).
Usually processed by skipping the record, unless a threshold is exceeded.
"""

from __future__ import annotations

from bioetl.domain.exceptions.base import BioETLError
from bioetl.domain.types import ErrorType


class DataQualityError(BioETLError):
    """Base class for data quality issues that do not halt the pipeline (record-level errors)."""

    error_type = ErrorType.DATA_QUALITY


class DataQualityThresholdError(DataQualityError):
    """Raised when the data quality error rate exceeds the allowed threshold.

    Indicates the batch is too corrupted to continue.
    """

    error_type = ErrorType.DATA_QUALITY

    def __init__(self, error_rate: float, threshold: float) -> None:
        self.error_rate = error_rate
        self.threshold = threshold
        super().__init__(
            f"DQ Hard Threshold exceeded: {error_rate:.2%} errors (limit: {threshold:.2%})"
        )
