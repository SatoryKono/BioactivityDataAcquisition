"""RF-003 evidence-location resolver protocols and result types."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol, runtime_checkable

from bioetl.domain.control_plane.run_evidence_location import (
    EvidenceLocationKind,
    EvidenceLocationLookupCode,
    EvidenceLocationLookupResult,
    RunEvidenceLocation,
)

__all__ = [
    "EvidenceLocationLegacyRootPolicy",
    "EvidenceLocationResolveResult",
    "EvidenceReadContext",
    "EvidenceReadContextFactoryProtocol",
]

class EvidenceLocationLegacyRootPolicy(StrEnum):
    """RF-003 policy for ``location_missing`` without inventing isolated roots.

    ``REQUIRE_EXPLICIT_RECORD`` — missing locator fails closed (no data root).
    ``ALLOW_STANDARD_ALIAS_BASE`` — open the trusted alias base (equivalent to
    explicit ``relative_data_root="."``). Never scans for foreign isolated
    workflow directories.
    """

    REQUIRE_EXPLICIT_RECORD = "require_explicit_record"
    ALLOW_STANDARD_ALIAS_BASE = "allow_standard_alias_base"


@runtime_checkable
class EvidenceReadContext(Protocol):
    """Read-only control-plane view bound to one data root."""

    @property
    def data_root(self) -> Path:
        """Absolute data root selected for this resolve."""
        ...

    def get_manifest_by_run_id(self, run_id: object) -> object | None:
        """Load a manifest by run id from the bound root, or ``None``."""
        ...

    def get_workflow_manifest_by_run_id(self, run_id: object) -> object | None:
        """Load a workflow manifest by run id from the bound root, or ``None``."""
        ...

    def verify_replay_objects(self, manifest: object) -> Mapping[str, bool]:
        """Re-validate saved config / lock / Bronze bytes for ``manifest``."""
        ...


@runtime_checkable
class EvidenceReadContextFactoryProtocol(Protocol):
    """Composition-injected factory that opens stores under a trusted base."""

    def open(
        self,
        data_root: Path,
        *,
        trusted_alias_base: Path,
    ) -> EvidenceReadContext:
        """Open read-only ports for ``data_root`` after containment checks."""
        ...


@dataclass(frozen=True, slots=True)
class EvidenceLocationResolveResult:
    """Resolver outcome; lookup codes stay distinct from replay verdicts."""

    lookup: EvidenceLocationLookupResult
    requested_run_id: str | None = None
    requested_kind: EvidenceLocationKind | str | None = None
    data_root: Path | None = None
    context: EvidenceReadContext | None = None
    used_legacy_standard_root: bool = False
    detail: str | None = None

    @property
    def code(self) -> EvidenceLocationLookupCode:
        return self.lookup.code

    @property
    def location(self) -> RunEvidenceLocation | None:
        return self.lookup.location

    @property
    def is_open(self) -> bool:
        return self.context is not None and self.data_root is not None

