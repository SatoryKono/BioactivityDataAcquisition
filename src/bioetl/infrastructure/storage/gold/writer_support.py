"""Support helpers for the public ``gold_writer`` facade.

This module re-exports from split modules for backward compatibility.
"""

from __future__ import annotations


def _build_gold_write_request(*args: object, **kwargs: object) -> object:
    """Lazy compatibility wrapper for request construction."""
    from bioetl.infrastructure.storage.gold.writer_request import (
        _build_gold_write_request as _impl,
    )

    return _impl(*args, **kwargs)


def _project_records_for_gold_schema(*args: object, **kwargs: object) -> object:
    """Lazy compatibility wrapper for schema projection."""
    from bioetl.infrastructure.storage.gold.writer_schema_helpers import (
        _project_records_for_gold_schema as _impl,
    )

    return _impl(*args, **kwargs)


def _resolve_active_gold_schema(*args: object, **kwargs: object) -> object:
    """Lazy compatibility wrapper for active schema resolution."""
    from bioetl.infrastructure.storage.gold.writer_schema_helpers import (
        _resolve_active_gold_schema as _impl,
    )

    return _impl(*args, **kwargs)


def _resolve_runtime_services(*args: object, **kwargs: object) -> object:
    """Lazy compatibility wrapper for runtime service resolution."""
    from bioetl.infrastructure.storage.gold.writer_runtime import (
        _resolve_runtime_services as _impl,
    )

    return _impl(*args, **kwargs)


async def _write_dual_targets_impl(*args: object, **kwargs: object) -> object:
    """Lazy compatibility wrapper for dual-target writes."""
    from bioetl.infrastructure.storage.gold.writer_implementation import (
        _write_dual_targets_impl as _impl,
    )

    return await _impl(*args, **kwargs)


async def _write_single_target_impl(*args: object, **kwargs: object) -> object:
    """Lazy compatibility wrapper for single-target writes."""
    from bioetl.infrastructure.storage.gold.writer_implementation import (
        _write_single_target_impl as _impl,
    )

    return await _impl(*args, **kwargs)


__all__ = [
    "_build_gold_write_request",
    "_project_records_for_gold_schema",
    "_resolve_active_gold_schema",
    "_resolve_runtime_services",
    "_write_dual_targets_impl",
    "_write_single_target_impl",
]
