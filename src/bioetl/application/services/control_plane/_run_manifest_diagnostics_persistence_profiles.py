"""Compatibility facade for manifest-owned persistence profile helpers."""

from __future__ import annotations

from bioetl.application.services.control_plane.manifest.diagnostics import (
    persistence_profiles as _impl,
)

__all__ = [name for name in dir(_impl) if not name.startswith("__")]
globals().update({name: getattr(_impl, name) for name in __all__})
