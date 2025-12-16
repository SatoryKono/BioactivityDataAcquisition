"""Error classification logic.

Maps exceptions to ErrorType for handling strategy.
"""

import httpx
from bioetl.domain.types import ErrorType
from bioetl.domain.exceptions import BioETLError


class ErrorClassifier:
    """Classifies exceptions into error types."""

    def classify(self, error: Exception) -> ErrorType:
        """Classify an exception into an ErrorType.

        Args:
            error: The exception to classify.

        Returns:
            The appropriate ErrorType.
        """
        # First, check if it's a BioETL exception with explicit type
        if isinstance(error, BioETLError):
            return error.error_type

        # Fallback to type-based classification for external exceptions
        return self._classify_external(error)

    def _classify_external(self, error: Exception) -> ErrorType:
        """Classify external exceptions by type."""

        if isinstance(error, httpx.HTTPStatusError):
            status = error.response.status_code
            if status == 429:
                return ErrorType.RATE_LIMIT
            if status in (401, 403):
                return ErrorType.AUTH_FAILURE
            if status in (502, 503, 504):
                return ErrorType.TIMEOUT

        if isinstance(error, (httpx.ConnectError, httpx.ConnectTimeout)):
            return ErrorType.NETWORK_ERROR

        if isinstance(error, httpx.ReadTimeout):
            return ErrorType.TIMEOUT

        # Default to data quality issue
        return ErrorType.INVALID_DATA
