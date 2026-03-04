"""Compatibility shim for OpenAlex adapter helper mixin.

Canonical implementation lives in ``client_helpers_adapter_mixin.py``.
"""

from __future__ import annotations

from bioetl.infrastructure.adapters.openalex.client_helpers_adapter_mixin import (
    OpenAlexAdapterHelpersMixin,
)

# Backward-compatible alias for existing imports.
_OpenAlexAdapterHelpersMixin = OpenAlexAdapterHelpersMixin

__all__ = ["OpenAlexAdapterHelpersMixin", "_OpenAlexAdapterHelpersMixin"]
