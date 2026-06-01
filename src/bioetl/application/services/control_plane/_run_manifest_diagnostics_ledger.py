"""Compatibility facade for manifest-owned diagnostics ledger processing."""

from __future__ import annotations

from bioetl.application.services.control_plane.manifest.diagnostics import (
    ledger_processing as _impl,
)

__all__ = [name for name in dir(_impl) if not name.startswith("__")]
globals().update({name: getattr(_impl, name) for name in __all__})
