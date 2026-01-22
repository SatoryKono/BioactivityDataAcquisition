"""Base utilities for Gold layer data contracts.

DEPRECATED: This module re-exports from bioetl.domain.contracts.gold._base for
backward compatibility. New code should import from bioetl.domain.contracts.gold._base.

Contains shared constants and utilities used across all Gold schemas.
"""

from __future__ import annotations

# Re-export from domain.contracts for backward compatibility
from bioetl.domain.contracts.gold._base import DATE_REGEX

__all__ = ["DATE_REGEX"]
