"""ADR (Architecture Decision Records) domain port and DTOs.

Defines a minimal read-only interface for working with ADR documents
stored in the repository (see docs/02-architecture/decisions).

Layering rules: This module belongs to the Domain layer and MUST NOT
import infrastructure. Implementations live in the Infrastructure layer
and are wired in the Composition layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class AdrInfo:
    """Brief ADR info for listings."""

    number: int
    title: str
    path: str


@dataclass(frozen=True, slots=True)
class AdrDocument:
    """Full ADR document payload."""

    number: int
    title: str
    content: str
    path: str
    status: str | None = None
    date: str | None = None


class AdrIssueSeverity(StrEnum):
    """Severity levels for ADR validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True, slots=True)
class AdrValidationIssue:
    """Single validation issue for an ADR document."""

    number: int | None
    path: str
    message: str
    severity: AdrIssueSeverity = AdrIssueSeverity.ERROR


@dataclass(frozen=True, slots=True)
class AdrValidationReport:
    """Validation summary for ADR documents in the repository."""

    valid: bool
    total: int
    errors: int
    warnings: int
    issues: tuple[AdrValidationIssue, ...]


@runtime_checkable
class AdrServicePort(Protocol):
    """Port for accessing and validating ADR documents."""

    def list_adrs(self) -> list[AdrInfo]:
        """List ADRs available in the repository sorted by number.

        Returns:
            Collection of adrs.
        """
        ...

    def get_adr(self, number: int) -> AdrDocument:
        """Get full ADR document by number.

        Raises:
            FileNotFoundError: if ADR with the given number does not exist.
            ValueError: if the ADR file is malformed.

        Args:
            number: Number.

        Returns:
            Adr.
        """
        ...

    def validate(self) -> AdrValidationReport:
        """Validate ADR repository and return a summary report.

        Returns:
            Validated AdrValidationReport.
        """
        ...


__all__ = [
    "AdrDocument",
    "AdrInfo",
    "AdrServicePort",
    "AdrValidationIssue",
    "AdrValidationReport",
]
