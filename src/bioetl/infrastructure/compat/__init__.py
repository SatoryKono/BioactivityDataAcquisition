"""Infrastructure compatibility seams for third-party runtime quirks."""

from __future__ import annotations

from bioetl.infrastructure.compat.pandera_compat import (
    apply_pandera_typing_compat_if_needed,
)

__all__ = ["apply_pandera_typing_compat_if_needed"]
