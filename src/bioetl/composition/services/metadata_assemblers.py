"""Composition-level compatibility facade for metadata assemblers.

Canonical implementations live in ``bioetl.application.services.metadata_assemblers``.
"""

from __future__ import annotations

from bioetl.application.services.metadata_assemblers import (
    GoldMetadataAssembler,
    SilverMetadataAssembler,
)

__all__ = ["GoldMetadataAssembler", "SilverMetadataAssembler"]
