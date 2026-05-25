"""Runtime bootstrap compatibility patches with explicit call sites."""

from __future__ import annotations

from bioetl.infrastructure.compat.pandera_compat import (
    apply_pandera_typing_compat_if_needed,
)

__all__ = ["apply_runtime_compatibility_patches"]


def apply_runtime_compatibility_patches() -> bool:
    """Apply idempotent third-party runtime compatibility patches."""
    return apply_pandera_typing_compat_if_needed()
