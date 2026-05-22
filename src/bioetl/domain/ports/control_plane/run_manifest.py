"""Port for run-manifest persistence."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bioetl.domain.control_plane.run_manifest import RunManifest
from bioetl.domain.types import RunID

__all__ = ["RunManifestPort"]


@runtime_checkable
class RunManifestPort(Protocol):
    """Persist and retrieve immutable run-manifest records."""

    def save(self, manifest: RunManifest) -> None:
        """Persist one immutable run manifest."""
        ...

    def get(self, manifest_id: str) -> RunManifest | None:
        """Load a manifest by manifest identifier."""
        ...

    def get_by_run_id(self, run_id: RunID) -> RunManifest | None:
        """Load the manifest linked to a run identifier."""
        ...

    def list_all(self) -> tuple[RunManifest, ...]:
        """Return every persisted manifest in deterministic enumeration order."""
        ...
