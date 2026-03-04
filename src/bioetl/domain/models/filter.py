"""Extraction filtering domain models.

Provides immutable value objects for API-level extraction filtering.
Part of ADR-028 §3: Extraction-Level Filtering.

Domain layer — no infrastructure or application imports allowed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

__all__ = [
    "ExtractionParams",
]


@dataclass(frozen=True, slots=True)
class ExtractionParams:
    """Server-side query parameters for API extraction filtering.

    Immutable value object. Provider-agnostic container —
    concrete syntax (__in, __isnull) is defined in YAML config.

    Attributes:
        params: Mapping of query parameter names to values.
                Keys are provider-specific (e.g., 'standard_type__in').
                Values are primitives only.

    Example:
        >>> ep = ExtractionParams(params={
        ...     "standard_type__in": "IC50,Ki",
        ...     "standard_units": "nM",
        ...     "pchembl_value__isnull": False,
        ... })
        >>> ep.to_query_dict()
        {'standard_type__in': 'IC50,Ki', 'standard_units': 'nM', ...}
    """

    params: Mapping[str, str | int | bool]

    def to_query_dict(self) -> dict[str, str | int | bool]:
        """Return params as mutable dict for adapter consumption.

        Returns:
            Result dictionary.
        """
        return dict(self.params)

    def to_query_string(self) -> str:
        """Serialize for SourceMetadata.query_string audit field.

        Returns:
            URL-encoded-like string with sorted keys for determinism.
        """
        parts = [f"{k}={v}" for k, v in sorted(self.params.items())]
        return "&".join(parts)

    @property
    def is_empty(self) -> bool:
        """Check if no extraction params are configured."""
        return len(self.params) == 0

    @classmethod
    def empty(cls) -> ExtractionParams:
        """Create an empty ExtractionParams instance.

        Returns:
            The ExtractionParams result.
        """
        return cls(params={})
