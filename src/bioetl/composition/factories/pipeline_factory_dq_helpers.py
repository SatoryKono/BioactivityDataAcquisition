"""DQ config/path extraction helpers - backward-compatibility re-export facade.

All implementation has been moved to dq_context_resolver.py.
"""

from __future__ import annotations

from bioetl.composition.factories.dq_context_resolver import (
    extract_dq_configs,
    extract_dq_output_paths,
    extract_single_dq_config,
    get_layer_path,
    has_flat_structure,
)

__all__ = [
    "extract_dq_configs",
    "extract_dq_output_paths",
    "extract_single_dq_config",
    "get_layer_path",
    "has_flat_structure",
]
