"""Support helpers for the public ``gold_writer`` facade.

This module re-exports from split modules for backward compatibility.
"""

from __future__ import annotations

# Re-export from split modules
from bioetl.infrastructure.storage.gold.writer_implementation import (
    _write_dual_targets_impl,
    _write_single_target_impl,
)
from bioetl.infrastructure.storage.gold.writer_request import (
    _build_gold_write_request,
)
from bioetl.infrastructure.storage.gold.writer_runtime import (
    _resolve_runtime_services,
)
from bioetl.infrastructure.storage.gold.writer_schema_helpers import (
    _project_records_for_gold_schema,
    _resolve_active_gold_schema,
)

__all__ = [
    "_build_gold_write_request",
    "_project_records_for_gold_schema",
    "_resolve_active_gold_schema",
    "_resolve_runtime_services",
    "_write_dual_targets_impl",
    "_write_single_target_impl",
]
