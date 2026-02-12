"""Compatibility wrapper for legacy DeltaWriter imports."""

from __future__ import annotations

from bioetl.domain.medallion import SilverWriteMode
from bioetl.infrastructure.storage.silver_writer import SilverWriter as DeltaWriter

__all__ = ["DeltaWriter", "SilverWriteMode"]
