"""Compatibility facade for manifest-owned diagnostics composite projection."""

from __future__ import annotations

from bioetl.application.services.control_plane.manifest.diagnostics import (
    composite_projection as _impl,
)

__all__ = [name for name in dir(_impl) if not name.startswith("__")]
globals().update({name: getattr(_impl, name) for name in __all__})
