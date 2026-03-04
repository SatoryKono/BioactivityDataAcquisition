"""Silver filter configuration."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.filtering._base_filter_config import BaseFilterConfig

__all__ = [
    "SilverFilterConfig",
]


@dataclass(frozen=True, slots=True)
class SilverFilterConfig(BaseFilterConfig):
    """Filter configuration for the Silver layer."""
