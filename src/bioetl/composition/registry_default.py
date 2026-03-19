"""Shared default registry state used by compatibility re-exports."""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = ["get_default_registry"]

if TYPE_CHECKING:
    from bioetl.composition.registry import PipelineRegistry

_compat_default_registry: PipelineRegistry | None = None


def get_default_registry() -> PipelineRegistry:
    """Return the compatibility-only shared default registry instance."""
    global _compat_default_registry
    if _compat_default_registry is None:
        from bioetl.composition.registry import PipelineRegistry

        _compat_default_registry = PipelineRegistry()
    return _compat_default_registry
