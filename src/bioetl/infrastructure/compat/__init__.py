"""Infrastructure compatibility seams for third-party runtime quirks."""

from __future__ import annotations

from bioetl.infrastructure.compat.pandera_compat import (
    PANDERA_RUNTIME_SUPPORT_POLICY,
    UnsupportedPanderaRuntimeError,
    validate_supported_pandera_runtime,
)

__all__ = [
    "PANDERA_RUNTIME_SUPPORT_POLICY",
    "UnsupportedPanderaRuntimeError",
    "validate_supported_pandera_runtime",
]
