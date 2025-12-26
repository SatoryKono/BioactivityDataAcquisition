"""Base exception classes for BioETL.

Defines the base exception hierarchy that all BioETL exceptions inherit from.
Each category defines a default error type for classification.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from bioetl.domain.types import ErrorType


class BioETLError(Exception):
    """Base exception for all BioETL errors.

    All exceptions in the system should inherit from this class to enable
    consistent error handling and classification.

    Attributes:
        error_type: Explicit ErrorType for deterministic classification.
                   Subclasses MUST override this attribute.

    The `context` property automatically collects all public instance attributes
    for unified error diagnostics and logging.
    """

    error_type: ClassVar[ErrorType]

    # Private attributes that should be excluded from context
    _CONTEXT_EXCLUDE: ClassVar[frozenset[str]] = frozenset({
        "args",
        "with_traceback",
    })

    @classmethod
    def get_error_type(cls) -> ErrorType:
        """Get the error type for this exception class.

        Returns:
            ErrorType for this exception.

        Raises:
            AttributeError: If error_type is not defined (should not happen).
        """
        # Import here to avoid circular import at module load time
        from bioetl.domain.types import ErrorType

        return getattr(cls, "error_type", ErrorType.INVALID_DATA)


class ProcessingError(CriticalError):
    """Generic error during record processing."""

    @property
    def context(self) -> dict[str, object]:
        """Get unified error context from instance attributes.

        Automatically collects all public instance attributes set on the exception,
        enabling consistent logging and diagnostics across all BioETL errors.

        Returns:
            Dictionary of attribute names to values, excluding private attributes
            and standard Exception attributes.

        Example:
            >>> err = RateLimitError(provider="chembl", retry_after=60.0)
            >>> err.context
            {'provider': 'chembl', 'retry_after': 60.0}
        """
        result: dict[str, object] = {}
        for key, value in vars(self).items():
            # Skip private attributes
            if key.startswith("_"):
                continue
            # Skip excluded attributes
            if key in self._CONTEXT_EXCLUDE:
                continue
            result[key] = value
        return result

    def with_context(self, **extra: object) -> BioETLError:
        """Return self with additional context attributes.

        Allows adding extra context to an existing exception without
        creating a new instance.

        Args:
            **extra: Additional context key-value pairs to attach.

        Returns:
            Self with additional attributes set.

        Example:
            >>> err = ApiError("Connection failed", status_code=500)
            >>> err = err.with_context(endpoint="/api/v1/data", attempt=3)
            >>> err.context
            {'message': 'Connection failed', 'status_code': 500, ...}
        """
        for key, value in extra.items():
            setattr(self, key, value)
        return self


class CriticalError(BioETLError):
    """Errors that should stop the pipeline immediately.

    These errors indicate serious problems that cannot be recovered from
    and require immediate attention. Examples: lock lost, data corruption,
    system resource exhaustion.
    """

    # Default for CriticalError subclasses that don't override
    @classmethod
    def get_error_type(cls) -> ErrorType:
        from bioetl.domain.types import ErrorType

        return getattr(cls, "error_type", ErrorType.DB_UNAVAILABLE)


class RecoverableError(BioETLError):
    """Errors that can be retried.

    These errors are typically transient and may succeed on retry.
    Examples: network timeouts, rate limits, temporary service unavailability.
    """

    @classmethod
    def get_error_type(cls) -> ErrorType:
        from bioetl.domain.types import ErrorType

        return getattr(cls, "error_type", ErrorType.NETWORK_ERROR)


class DataQualityError(BioETLError):
    """Errors in data quality (skip record).

    These errors indicate problems with individual data records that should
    be logged and skipped, but should not stop the pipeline.
    Examples: schema violations, missing required fields, invalid data formats.
    """

    @classmethod
    def get_error_type(cls) -> ErrorType:
        from bioetl.domain.types import ErrorType

        return getattr(cls, "error_type", ErrorType.INVALID_DATA)
