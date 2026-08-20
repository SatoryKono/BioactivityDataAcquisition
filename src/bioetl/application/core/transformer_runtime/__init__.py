"""Canonical grouping for batch-transformer runtime helpers."""
from __future__ import annotations
# ruff: noqa: I001

from bioetl.application.core.transformer_runtime.attempts import (
    TRANSFORM_PROCESSING_ERRORS as TRANSFORM_PROCESSING_ERRORS,
    bind_record_context as bind_record_context,
    transform_record_attempt as transform_record_attempt,
)
from bioetl.application.core.transformer_runtime.finalization import *  # noqa: F403
from bioetl.application.core.transformer_runtime.finalization import __all__ as _FINAL
from bioetl.application.core.transformer_runtime.orchestration import *  # noqa: F403
from bioetl.application.core.transformer_runtime.orchestration import __all__ as _ORCH
from bioetl.application.core.transformer_runtime.quarantine import (
    QUARANTINE_WRITE_WARN_ONLY_ERRORS as QUARANTINE_WRITE_WARN_ONLY_ERRORS,
    flush_dq_records as flush_dq_records,
    flush_filtered_records as flush_filtered_records,
    route_single_transform_attempt as route_single_transform_attempt,
)
from bioetl.application.core.transformer_runtime.state import *  # noqa: F403
from bioetl.application.core.transformer_runtime.state import __all__ as _STATE
from bioetl.application.core.transformer_runtime.streaming import (
    StreamingBatchProcessor as StreamingBatchProcessor,
)

__all__ = [
    "QUARANTINE_WRITE_WARN_ONLY_ERRORS",
    "TRANSFORM_PROCESSING_ERRORS",
    "StreamingBatchProcessor",
    "bind_record_context",
    "flush_dq_records",
    "flush_filtered_records",
    "route_single_transform_attempt",
    "transform_record_attempt",
    *_FINAL,
    *_ORCH,
    *_STATE,
]
