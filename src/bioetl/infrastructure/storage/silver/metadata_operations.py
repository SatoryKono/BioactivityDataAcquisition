"""Canonical Silver metadata operations."""

from __future__ import annotations

from bioetl.infrastructure.storage.silver.metadata_operation_protocols import (
    _SilverMetadataWriteHostProtocol,
    _SilverWriteFinalizationHostProtocol,
)
from bioetl.infrastructure.storage.silver.metadata_request_models import (
    _coerce_silver_metadata_write_request,
    _PreparedSilverMetadataWriteOperation,
    _PreparedSilverWriteFinalizationContext,
    _ResolvedSilverMetadataContext,
    _SilverMergedMetadataWriteRequest,
    _SilverMetadataWriteRequest,
    _SilverWriteFinalizationPreparationRequest,
)
from bioetl.infrastructure.storage.silver.metadata_result_finalization import (
    _build_silver_write_result,
    _prepare_silver_write_finalization_context,
    _read_delta_version,
)
from bioetl.infrastructure.storage.silver.metadata_write_execution import (
    _execute_prepared_silver_metadata_write_operation,
    _execute_silver_metadata_write,
)
from bioetl.infrastructure.storage.silver.metadata_write_preparation import (
    _emit_prepared_silver_metadata_metrics,
    _prepare_silver_merged_metadata_write,
    _prepare_silver_metadata_write,
    _raise_missing_silver_metadata_bundle,
    _resolve_silver_metadata_bundle,
    _resolve_silver_metadata_context,
)

__all__ = [
    "_PreparedSilverMetadataWriteOperation",
    "_PreparedSilverWriteFinalizationContext",
    "_ResolvedSilverMetadataContext",
    "_SilverMergedMetadataWriteRequest",
    "_SilverMetadataWriteHostProtocol",
    "_SilverMetadataWriteRequest",
    "_SilverWriteFinalizationHostProtocol",
    "_SilverWriteFinalizationPreparationRequest",
    "_build_silver_write_result",
    "_coerce_silver_metadata_write_request",
    "_emit_prepared_silver_metadata_metrics",
    "_execute_prepared_silver_metadata_write_operation",
    "_execute_silver_metadata_write",
    "_prepare_silver_merged_metadata_write",
    "_prepare_silver_metadata_write",
    "_prepare_silver_write_finalization_context",
    "_raise_missing_silver_metadata_bundle",
    "_read_delta_version",
    "_resolve_silver_metadata_bundle",
    "_resolve_silver_metadata_context",
]
