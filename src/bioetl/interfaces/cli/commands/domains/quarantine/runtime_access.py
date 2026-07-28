# pyright: reportInvalidCast=false
# Host/cast bridge residual; prefer Protocol self when rewriting module.
"""Quarantine-owned composition accessors for CLI command wiring."""

from __future__ import annotations

from typing import cast

from bioetl.interfaces.cli.commands.domains.quarantine.support import (
    _QuarantineRuntimeService,
    _QuarantineService,
)

__all__ = [
    "get_quarantine_runtime_service",
    "get_quarantine_service",
]


def get_quarantine_runtime_service(pipeline: str) -> _QuarantineRuntimeService:
    """Load one pipeline-scoped quarantine runtime service through composition."""
    from bioetl.composition.health_service_access import (
        get_quarantine_runtime_service as _impl,
    )

    return cast("_QuarantineRuntimeService", _impl(pipeline))


def get_quarantine_service() -> _QuarantineService:
    """Load the quarantine admin service through the canonical services seam."""
    from bioetl.composition.health_service_access import get_quarantine_service as _impl

    return cast("_QuarantineService", _impl())
