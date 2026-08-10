"""Port for run-manifest persistence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from bioetl.domain.control_plane.run_manifest import RunManifest
from bioetl.domain.types import RunID, RunType

__all__ = [
    "RawManifestInspection",
    "RawRunManifestInspectionPort",
    "RunManifestPort",
]


@dataclass(frozen=True, slots=True)
class RawManifestInspection:
    """Bounded diagnostics from the persisted JSON before typed coercion."""

    parse_ok: bool
    schema_errors: tuple[str, ...] = ()

    @property
    def schema_ok(self) -> bool:
        """Return whether parsing and raw schema validation both succeeded."""
        return self.parse_ok and not self.schema_errors


@runtime_checkable
class RawRunManifestInspectionPort(Protocol):
    """Optional raw-manifest diagnostics without widening ``RunManifestPort``."""

    def inspect_raw_manifest(self, manifest_id: str) -> RawManifestInspection:
        """Inspect one persisted manifest without hydrating typed values."""
        ...


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

    def get_latest_for_scope(
        self,
        pipeline_name: str,
        run_types: tuple[RunType, ...] = (),
    ) -> RunManifest | None:
        """Load the latest manifest for one pipeline and optional run types."""
        ...

    def list_all(self) -> tuple[RunManifest, ...]:
        """Return every persisted manifest in deterministic enumeration order."""
        ...
