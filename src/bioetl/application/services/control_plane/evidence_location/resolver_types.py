"""Policy and result values for evidence-location resolution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from bioetl.application.ports import EvidenceReadContext
from bioetl.domain.control_plane.run_evidence_location import (
    EvidenceLocationKind,
    EvidenceLocationLookupCode,
    EvidenceLocationLookupResult,
    RunEvidenceLocation,
)


class EvidenceLocationLegacyRootPolicy(StrEnum):
    """RF-003 policy for ``location_missing`` without inventing isolated roots.

    ``REQUIRE_EXPLICIT_RECORD`` — missing locator fails closed (no data root).
    ``ALLOW_STANDARD_ALIAS_BASE`` — open the trusted alias base (equivalent to
    explicit ``relative_data_root="."``). Never scans for foreign isolated
    workflow directories.
    """

    REQUIRE_EXPLICIT_RECORD = "require_explicit_record"
    ALLOW_STANDARD_ALIAS_BASE = "allow_standard_alias_base"


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
