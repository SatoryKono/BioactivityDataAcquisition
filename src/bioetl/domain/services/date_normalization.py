"""Deprecated date normalization compatibility service.

Deprecated: import pure helpers from ``bioetl.domain.normalization.dates``
instead.
Sunset target: 2026-06-30.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.domain.normalization.dates import (
    format_date_parts as _format_date_parts,
)
from bioetl.domain.normalization.dates import (
    normalize_partial_date as _normalize_partial_date,
)
from bioetl.domain.normalization.dates import (
    validate_publication_year as _validate_publication_year,
)
from bioetl.domain.services.data_normalization_config import DataNormalizationConfig

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "DateNormalizationService",
]

DEPRECATED_IN_FAVOR_OF = "bioetl.domain.normalization.dates"
SUNSET_DATE = "2026-06-30"


@dataclass(frozen=True, slots=True)
class DateNormalizationService:
    """Compatibility façade over pure date normalization helpers."""

    config: DataNormalizationConfig = field(default_factory=DataNormalizationConfig)

    def normalize_year(self, year: int | None) -> tuple[int | None, bool]:
        """Validate publication year against configured bounds."""
        return _validate_publication_year(
            year,
            min_year=self.config.min_publication_year,
            max_year=self.config.max_publication_year,
        )

    def normalize_partial_date(self, date_str: str | None) -> str | None:
        """Normalize partial date to full YYYY-MM-DD format (end of period).

        Args:
            date_str: Date string in partial or full ISO format.

        Returns:
            Full ISO date string (YYYY-MM-DD), or None if invalid.
        """
        return _normalize_partial_date(date_str)

    def format_date_parts(
        self, date_parts: Sequence[Sequence[int]] | None
    ) -> str | None:
        """Format CrossRef date-parts [[year, month?, day?]] to ISO YYYY-MM-DD string.

        Args:
            date_parts: Date parts array from CrossRef API.

        Returns:
            ISO date string, or None if invalid.
        """
        return _format_date_parts(date_parts)
