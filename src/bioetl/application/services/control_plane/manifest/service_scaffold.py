"""Shared manifest creation service scaffold for control-plane services."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from bioetl.domain.context_time import resolve_manifest_created_at

__all__ = ["ManifestServiceScaffoldMixin"]


class ManifestClockProtocol(Protocol):
    """Clock protocol used by manifest creation services."""

    def now(self) -> datetime: ...


def _resolve_manifest_created_at(
    *,
    clock: ManifestClockProtocol | None,
    created_at_factory: Callable[[], datetime] | None,
) -> datetime:
    return resolve_manifest_created_at(
        clock=clock,
        created_at_factory=created_at_factory,
    )


def _missing_manifest_id_factory() -> str:
    raise RuntimeError("manifest_id_factory must be supplied by composition root")


@dataclass(kw_only=True)
class ManifestServiceScaffoldMixin:
    """Shared clock/id/schema fields for immutable manifest services."""

    clock: ManifestClockProtocol | None = None
    created_at_factory: Callable[[], datetime] | None = None
    schema_version: str = "1.0"
    _manifest_id_factory: Callable[[], str] = field(
        default_factory=lambda: _missing_manifest_id_factory
    )

    def _resolve_created_at(self) -> datetime:
        """Resolve manifest creation time through the configured seam."""
        return _resolve_manifest_created_at(
            clock=self.clock,
            created_at_factory=self.created_at_factory,
        )
