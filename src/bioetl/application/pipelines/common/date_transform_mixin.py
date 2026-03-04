"""Date normalization mixin for publication transformers.

Extracts the common date handling patterns shared by CrossRef,
OpenAlex, PubMed, and SemanticScholar transformers:
- Publication year validation via PublicationYear Value Object
- Partial date normalization via DataNormalizationPort
- Date preference (choosing best date from multiple candidates)
"""

from __future__ import annotations

__all__ = ["DateTransformMixin"]


from typing import TYPE_CHECKING, Any

from bioetl.domain.value_objects import PublicationYear

if TYPE_CHECKING:
    from bioetl.domain.ports import DataNormalizationPort


class DateTransformMixin:
    """Shared date normalization methods for publication transformers.

    Requires host class to provide ``_data_normalizer`` attribute and
    ``validate_value_object`` method (both from ``BaseTransformer``).

    Naming: ``*Mixin`` suffix per NAME-001.
    """

    _data_normalizer: DataNormalizationPort

    def _validate_publication_year(
        self,
        raw_year: Any,  # Any: raw API value (int | str | None)
    ) -> int | None:
        """Validate and return publication year as integer.

        Delegates to ``PublicationYear`` Value Object.  Used identically
        in CrossRef, OpenAlex, SemanticScholar, and PubMed transformers.

        Args:
            raw_year: Raw year value from provider API.

        Returns:
            Validated year as int, or None if invalid.

        """
        from bioetl.application.core.base_transformer import BaseTransformer

        return BaseTransformer.validate_value_object(
            PublicationYear, raw_year, as_string=False
        )

    def _normalize_publication_date(
        self,
        raw_date: str | None,
    ) -> str | None:
        """Normalize a date string to YYYY-MM-DD format.

        Delegates to ``DataNormalizationPort.normalize_partial_date``.
        Used identically in OpenAlex and SemanticScholar transformers.

        Args:
            raw_date: Raw date string from provider API.

        Returns:
            Normalized ISO date string, or None.

        """
        return self._data_normalizer.normalize_partial_date(raw_date)

    @staticmethod
    def _prefer_date(*dates: str | None) -> str | None:
        """Return the first non-None date from priority-ordered candidates.

        Replaces provider-specific ``_compute_publication_date`` methods
        that simply choose among multiple date candidates.

        Example:
            >>> DateTransformMixin._prefer_date(published_print, published_online)
            '2024-01-15'

        Args:
            *dates: Date strings in priority order (most preferred first).

        Returns:
            First non-None date, or None if all are None.

        """
        for d in dates:
            if d:
                return d
        return None
