"""Data quality exceptions for batch-level quality issues.

These errors indicate problems with data quality at the batch or pipeline level,
as opposed to individual record validation errors. DataQualityErrors typically
affect processing decisions for entire batches or trigger quarantine mechanisms.

Category: DataQualityErrors - data quality errors at the content integrity level
(invariant violations, data anomalies, threshold exceedances,
data quarantine cases).

Note:
    Individual record validation errors (for example `SchemaViolationError` or
    `ValidationError` instances classified as missing-field / invalid-format
    cases) are in the `validation` module.
"""

from __future__ import annotations

from bioetl.domain.exceptions.base import BioETLError
from bioetl.domain.types import ErrorType

__all__ = [
    "DataQualityThresholdError",
]


class DataQualityThresholdError(BioETLError):
    """Raised when Data Quality error rate exceeds the hard threshold.

    This error indicates that the quality of the batch is too low to proceed,
    requiring the pipeline or batch to stop. Per RULES.md §4.1:
    - Soft threshold (>5%): Warning, continue processing
    - Hard threshold (>20%): Fail batch with this error

    Attributes:
        error_rate: Actual error rate observed (0.0-1.0).
        threshold: Configured threshold that was exceeded (0.0-1.0).

    Example:
        >>> # 25% of records failed validation
        >>> raise DataQualityThresholdError(error_rate=0.25, threshold=0.20)
        # Raises: DQ Hard Threshold exceeded: 25.00% errors (limit: 20.00%)
    """

    error_type = ErrorType.DATA_QUALITY

    def __init__(self, error_rate: float, threshold: float) -> None:
        """Initialize DataQualityThresholdError.

        Args:
            error_rate: Actual error rate observed (0.0-1.0).
            threshold: Configured threshold that was exceeded (0.0-1.0).
        """
        self.error_rate = error_rate
        self.threshold = threshold
        super().__init__(
            f"DQ Hard Threshold exceeded: {error_rate:.2%} errors (limit: {threshold:.2%})"
        )
