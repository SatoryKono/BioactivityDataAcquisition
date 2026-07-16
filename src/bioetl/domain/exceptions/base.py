"""Base exception classes for BioETL.

Defines the base exception hierarchy that all BioETL exceptions inherit from.
Each category defines a default error type for classification.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, ClassVar
from urllib.parse import urlsplit, urlunsplit

if TYPE_CHECKING:
    from bioetl.domain.types import ErrorType

_SECRET_MARKERS = (
    "password",
    "passwd",
    "token",
    "secret",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "credential",
)
_INLINE_SECRET = re.compile(
    r"(?i)\b(password|passwd|token|secret|api[_-]?key|authorization)\b"
    r"\s*[:=]\s*([^\s,;&]+)"
)


def _redact_string(value: str) -> str:
    redacted = _INLINE_SECRET.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)
    if "://" not in redacted:
        return redacted
    try:
        parsed = urlsplit(redacted)
        port = parsed.port
    except ValueError:
        return "[REDACTED URL]"
    if not parsed.scheme or not parsed.netloc:
        return redacted
    hostname = parsed.hostname or ""
    if port is not None:
        hostname = f"{hostname}:{port}"
    query = "[REDACTED]" if parsed.query else ""
    return urlunsplit((parsed.scheme, hostname, parsed.path, query, ""))


def _redact(value: object, key: str = "") -> object:
    if any(marker in key.lower() for marker in _SECRET_MARKERS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): _redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(_redact(v, key) for v in value)
    if isinstance(value, set):
        return {_redact(item, key) for item in value}
    if isinstance(value, BaseException):
        return {
            "error_type": type(value).__name__,
            "message": _redact_string(str(value)),
        }
    if isinstance(value, str):
        return _redact_string(value)
    return value


__all__ = [
    "BioETLError",
    "CriticalError",
    "DataQualityError",
    "RecoverableError",
]


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
    reason_code: ClassVar[str | None] = None

    # Private attributes that should be excluded from context
    _CONTEXT_EXCLUDE: ClassVar[frozenset[str]] = frozenset(
        {
            "args",
            "error_type",
            "error_type_override",
            "reason_code",
            "with_traceback",
        }
    )

    def __init__(
        self,
        message: str = "",
        *,
        reason_code: str | None = None,
        **context: object,
    ) -> None:
        """Initialize a BioETL error with optional semantic reason code."""
        super().__init__(message)
        if reason_code is not None:
            self.reason_code = reason_code
        for key, value in context.items():
            setattr(self, key, value)

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

    def get_reason_code(self) -> str | None:
        """Get semantic reason code for this error instance/class.

        Returns:
            Optional reason code for policy-based handling and diagnostics.
        """
        reason_code = getattr(self, "reason_code", None)
        if reason_code is None:
            return None
        return str(reason_code)

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
            result[key] = _redact(value, key)
        return result

    def to_structured_context(
        self,
        *,
        reason_code: str | None = None,
        **extra: object,
    ) -> dict[str, object]:
        """Build a structured error payload for logging/triage.

        Args:
            reason_code: Optional policy reason code override.
            **extra: Additional context fields.

        Returns:
            Structured context with class/category identity and public attrs.
        """
        resolved_reason_code = reason_code or self.get_reason_code()
        structured: dict[str, object] = {
            "message": str(self),
            "error_type": type(self).__name__,
            "error_category": self.get_error_type().value,
        }
        if resolved_reason_code is not None:
            structured["reason_code"] = resolved_reason_code
        structured.update(self.context)
        structured.update({key: _redact(value, key) for key, value in extra.items()})
        return {key: _redact(value, key) for key, value in structured.items()}

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

    @classmethod
    def get_error_type(cls) -> ErrorType:
        """Get the default error type for critical errors.

        Returns:
            ErrorType.DB_UNAVAILABLE as the default for CriticalError subclasses
            that don't define their own error_type. This signals that the error
            is fatal and the pipeline should stop immediately.

        Note:
            Subclasses may override by defining a class-level error_type attribute.
        """
        from bioetl.domain.types import ErrorType

        return getattr(cls, "error_type", ErrorType.DB_UNAVAILABLE)


class RecoverableError(BioETLError):
    """Errors that can be retried.

    These errors are typically transient and may succeed on retry.
    Examples: network timeouts, rate limits, temporary service unavailability.
    """

    @classmethod
    def get_error_type(cls) -> ErrorType:
        """Get the default error type for recoverable errors.

        Returns:
            ErrorType.NETWORK_ERROR as the default for RecoverableError subclasses
            that don't define their own error_type. This signals that the error
            is transient and retry with exponential backoff is appropriate (§3.1.3).

        Note:
            Subclasses may override by defining a class-level error_type attribute.
        """
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
        """Get the default error type for data quality errors.

        Returns:
            ErrorType.INVALID_DATA as the default for DataQualityError subclasses
            that don't define their own error_type. This signals that the record
            should be quarantined (§2.6) and processing should continue.

        Note:
            Subclasses may override by defining a class-level error_type attribute.
        """
        from bioetl.domain.types import ErrorType

        return getattr(cls, "error_type", ErrorType.INVALID_DATA)
