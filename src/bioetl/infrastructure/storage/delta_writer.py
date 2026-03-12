"""Compatibility-only wrapper for legacy ``DeltaWriter`` imports.

New first-party code must use ``SilverWriter`` from the canonical storage module.
This shim remains only to preserve import stability for compatibility coverage.
"""

from __future__ import annotations

from bioetl.domain.medallion import SilverWriteMode
from bioetl.infrastructure.storage.silver_writer import SilverWriter as DeltaWriter

__all__ = ["DeltaWriter", "SilverWriteMode"]
