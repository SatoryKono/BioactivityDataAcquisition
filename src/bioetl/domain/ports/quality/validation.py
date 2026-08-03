"""Validation ports for Medallion layer record validation.

This module provides port abstractions for validating records at different
Medallion layers (Silver, Gold), allowing different validation strategies
(Pandera, Great Expectations, etc.) to be injected without coupling
components to specific implementations.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bioetl.domain.types import JsonDict, ValidationResult

__all__ = [
    "GoldValidatorPort",
    "SilverValidatorPort",
]


@runtime_checkable
class SilverValidatorPort(Protocol):
    """Port for Silver layer record validation.

    This interface abstracts the validation mechanism for Silver records,
    allowing different validation strategies (Pandera, Great Expectations, etc.)
    to be injected without coupling SilverWriter to a specific implementation.

    Note: SilverValidatorPort uses synchronous methods as validation
    should be a CPU-bound operation without I/O.
    """

    def validate(
        self,
        records: list[JsonDict],
    ) -> ValidationResult:
        """Validate records for Silver layer.

        Args:
            records: List of record dictionaries to validate.

        Returns:
            ValidationResult with valid flag and any error messages.
        """
        ...


@runtime_checkable
class GoldValidatorPort(Protocol):
    """Port for Gold layer record validation.

    This interface abstracts the validation mechanism for Gold records,
    allowing different validation strategies (Pandera, Great Expectations, etc.)
    to be injected without coupling RecordProcessor to a specific implementation.

    Note: GoldValidatorPort uses synchronous methods as validation
    should be a CPU-bound operation without I/O.
    """

    def validate(
        self,
        records: list[JsonDict],
    ) -> ValidationResult:
        """Validate records for Gold layer.

        Args:
            records: List of record dictionaries to validate.

        Returns:
            ValidationResult with valid flag and any error messages.
        """
        ...
