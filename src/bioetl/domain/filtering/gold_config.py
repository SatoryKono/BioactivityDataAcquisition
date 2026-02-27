"""Gold filter configuration."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.filtering._base_filter_config import BaseFilterConfig


@dataclass(frozen=True, slots=True)
class GoldFilterConfig(BaseFilterConfig):
    """Full filter configuration for the Gold layer."""
