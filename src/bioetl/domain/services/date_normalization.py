"""Date normalization service.

Pure domain service (no I/O) per RULES.md §1.1.
Handles year validation and partial date normalization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.domain.services._date_helpers import (
    format_date_parts as _format_date_parts,
)
from bioetl.domain.services._date_helpers import (
    normalize_partial_date as _normalize_partial_date,
)
from bioetl.domain.services.data_normalization_config import DataNormalizationConfig

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "DateNormalizationService",
]


@dataclass(frozen=True, slots=True)
class DateNormalizationService:
    """Normalize dates and validate publication years.

    Delegates partial date normalization and date-parts formatting
    to pure helper functions in ``_date_helpers``.
    """

    config: DataNormalizationConfig = field(default_factory=DataNormalizationConfig)

    def normalize_year(self, year: int | None) -> tuple[int | None, bool]:
        """Validate publication year against configured range.

        Returns (year, is_warning). Warning is True if year is outside valid range.

        Args:
            year: Publication year.

        Returns:
            Tuple of (year, is_warning).
        """
        if year is None:
            return None, False
        if self.config.min_publication_year <= year <= self.config.max_publication_year:
            return year, False
        return year, True

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
