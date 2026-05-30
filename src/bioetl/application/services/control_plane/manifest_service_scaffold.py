"""Shared manifest creation service scaffold for control-plane services."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from bioetl.application.services.control_plane.manifest_time_support import (
    ManifestClockProtocol,
    resolve_manifest_created_at,
)

__all__ = ["ManifestServiceScaffoldMixin"]


@dataclass(kw_only=True)
class ManifestServiceScaffoldMixin:
    """Shared clock/id/schema fields for immutable manifest services."""

    clock: ManifestClockProtocol | None = None
    created_at_factory: Callable[[], datetime] | None = None
    schema_version: str = "1.0"
    _manifest_id_factory: Callable[[], str] = field(
        default_factory=lambda: lambda: str(uuid4())
    )

    def _resolve_created_at(self) -> datetime:
        """Resolve manifest creation time through the configured seam."""
        return resolve_manifest_created_at(
            clock=self.clock,
            created_at_factory=self.created_at_factory,
        )
