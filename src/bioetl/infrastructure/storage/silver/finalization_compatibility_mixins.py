"""Re-export facade for Silver finalization and metadata mixins."""

from __future__ import annotations

from bioetl.infrastructure.storage.silver.audit_metadata_compatibility_mixin import (
    SilverWriterAuditMetadataCompatibilityMixin,
)
from bioetl.infrastructure.storage.silver.finalization_pipeline_compatibility_mixin import (
    SilverWriterFinalizationCompatibilityMixin,
)

__all__ = [
    "SilverWriterAuditMetadataCompatibilityMixin",
    "SilverWriterFinalizationCompatibilityMixin",
]
