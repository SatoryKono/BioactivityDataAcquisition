"""Shared time resolution helpers for control-plane manifest creation."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from bioetl.domain.context import MISSING_RUNTIME_TIMESTAMP

__all__ = ["ManifestClockProtocol", "resolve_manifest_created_at"]


class ManifestClockProtocol(Protocol):
    """Clock protocol used by manifest creation services."""

    def now(self) -> datetime:
        """Return the current timestamp."""
        ...


def resolve_manifest_created_at(
    *,
    clock: ManifestClockProtocol | None,
    created_at_factory: Callable[[], datetime] | None,
) -> datetime:
    """Resolve manifest creation time through the configured seam."""
    if clock is not None:
        return clock.now()
    if created_at_factory is not None:
        return created_at_factory()
    return MISSING_RUNTIME_TIMESTAMP
