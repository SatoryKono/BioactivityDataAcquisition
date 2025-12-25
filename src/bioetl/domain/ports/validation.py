"""Validation port for Gold layer record validation.

This port abstracts the validation mechanism for Gold records,
allowing different validation strategies (Pandera, Great Expectations, etc.)
to be injected without coupling RecordProcessor to a specific implementation.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from bioetl.domain.types import ValidationResult


@runtime_checkable
class GoldValidatorPort(Protocol):
    """Port for Gold layer record validation.

    This interface abstracts the validation mechanism for Gold records,
    allowing different validation strategies (Pandera, Great Expectations, etc.)
    to be injected without coupling RecordProcessor to a specific implementation.

    Note: GoldValidatorPort uses synchronous methods as validation
    should be a CPU-bound operation without I/O.
    """

    def validate(self, records: list[dict[str, Any]]) -> ValidationResult:
        """Validate records for Gold layer.

        Args:
            records: List of record dictionaries to validate.

        Returns:
            ValidationResult with valid flag and any error messages.
        """
        ...
