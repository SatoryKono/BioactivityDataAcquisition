"""Extraction filtering domain models.

Provides immutable value objects for API-level extraction filtering.
Part of ADR-028 §3: Extraction-Level Filtering.

Domain layer — no infrastructure or application imports allowed.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

__all__ = [
    "ExtractionParams",
    "SourceProfile",
    "SourceProfileStatus",
    "compute_extraction_params_sha256",
]

SourceProfileStatus = Literal["baseline", "candidate", "widened"]


def compute_extraction_params_sha256(
    params: Mapping[str, str | int | bool],
) -> str:
    """Return a deterministic hash for provider source-profile query policy."""
    payload = json.dumps(
        {str(key): value for key, value in sorted(params.items())},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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


@dataclass(frozen=True, slots=True)
class SourceProfile:
    """Versioned source-side extraction policy metadata.

    Source profiles describe provider request narrowing such as
    ``extraction_params``. They are not Silver filters and do not change adapter
    query behavior by themselves.
    """

    profile_id: str = "default"
    version: str = "1.0.0"
    status: SourceProfileStatus = "baseline"
    extraction_params_sha256: str | None = None
    description: str | None = None
