"""Request models and coercion helpers for Silver metadata operations.

This module re-exports from split modules for backward compatibility.
"""

from __future__ import annotations

# Re-export from split modules
from bioetl.infrastructure.storage.silver.finalization_models import (
    _coerce_request_fields,
    _coerce_silver_write_finalization_preparation_request,
    _coerce_silver_write_result_finalization_request,
    _SilverWriteFinalizationPreparationRequest,
    _SilverWriteResultFinalizationRequest,
)
from bioetl.infrastructure.storage.silver.metadata_write_models import (
    _coerce_silver_metadata_write_request,
    _SilverMetadataWriteRequest,
)
from bioetl.infrastructure.storage.silver.prepared_operation_models import (
    _build_silver_merged_metadata_write_request,
    _PreparedSilverMetadataWriteOperation,
    _PreparedSilverWriteFinalizationContext,
    _ResolvedSilverMetadataContext,
    _SilverMergedMetadataWriteRequest,
)

__all__ = [
    "_PreparedSilverMetadataWriteOperation",
    "_PreparedSilverWriteFinalizationContext",
    "_ResolvedSilverMetadataContext",
    "_SilverMergedMetadataWriteRequest",
    "_SilverMetadataWriteRequest",
    "_SilverWriteFinalizationPreparationRequest",
    "_SilverWriteResultFinalizationRequest",
    "_build_silver_merged_metadata_write_request",
    "_coerce_request_fields",
    "_coerce_silver_metadata_write_request",
    "_coerce_silver_write_finalization_preparation_request",
    "_coerce_silver_write_result_finalization_request",
]
