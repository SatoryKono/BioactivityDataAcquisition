"""Base exception classes for BioETL.

Defines the base exception hierarchy that all BioETL exceptions inherit from.
Each category defines a default error type for classification.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from bioetl.domain.types import ErrorType

from bioetl.domain.exceptions._redaction import _redact

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
    reason_code: str | None = None

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
    _RESERVED_CONTEXT_KEYS: ClassVar[frozenset[str]] = _CONTEXT_EXCLUDE | frozenset(
        {
            "add_note",
            "context",
            "get_error_type",
            "get_reason_code",
            "to_structured_context",
            "with_context",
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
            self._assign_context_attr(key, value)

    @classmethod
    def get_error_type(cls) -> ErrorType:
        """Get the error type for this exception class.

        Returns:
            ErrorType for this exception.
        """
        from bioetl.domain.types import ErrorType

        return getattr(cls, "error_type", ErrorType.INVALID_DATA)

    def get_reason_code(self) -> str | None:
        """Get the optional semantic reason code for this error."""
        reason_code = getattr(self, "reason_code", None)
        return None if reason_code is None else str(reason_code)

    @property
    def context(self) -> dict[str, object]:
        """Collect all public instance attributes for diagnostics.

        Returns:
            Dictionary of all public instance attributes excluding internal fields.
        """
        result: dict[str, object] = {}
        for key, value in vars(self).items():
            if key.startswith("_"):
                continue
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
        """Build a structured and redacted error payload for diagnostics."""
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
        """Attach additional context and return this exception instance.

        Args:
            **extra: Additional context fields to include.

        Returns:
            This exception instance with the supplied context attached.
        """
        for key, value in extra.items():
            self._assign_context_attr(key, value)
        return self

    def _is_reserved_context_key(self, key: str) -> bool:
        if not key or key.startswith("_") or key in self._RESERVED_CONTEXT_KEYS:
            return True
        existing = getattr(type(self), key, None)
        return isinstance(existing, property) or callable(existing)

    def _assign_context_attr(self, key: str, value: object) -> None:
        """Attach one diagnostic field, rejecting reserved or read-only names."""
        if self._is_reserved_context_key(key):
            raise ValueError(
                f"reserved or read-only context key cannot be assigned: {key!r}"
            )
        setattr(self, key, value)


class CriticalError(BioETLError):
    """Critical errors that prevent pipeline execution.

    Use for unrecoverable errors that require immediate pipeline termination.
    """

    @classmethod
    def get_error_type(cls) -> ErrorType:
        """Return the explicit type or the critical fallback."""
        from bioetl.domain.types import ErrorType

        return getattr(cls, "error_type", ErrorType.DB_UNAVAILABLE)


class DataQualityError(BioETLError):
    """Data quality violations that may allow partial recovery.

    Use for data validation failures that may be quarantined rather than
    failing the entire pipeline.
    """

    @classmethod
    def get_error_type(cls) -> ErrorType:
        """Return the explicit type or the data-quality fallback."""
        from bioetl.domain.types import ErrorType

        return getattr(cls, "error_type", ErrorType.INVALID_DATA)


class RecoverableError(BioETLError):
    """Transient errors that may be retried.

    Use for temporary failures like network timeouts or rate limits.
    """

    @classmethod
    def get_error_type(cls) -> ErrorType:
        """Return the explicit type or the recoverable fallback."""
        from bioetl.domain.types import ErrorType

        return getattr(cls, "error_type", ErrorType.NETWORK_ERROR)
