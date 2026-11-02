"""Evidence-location resolve seam (RF-003).

Owns bounded lookup-to-data-root resolution and legacy standard-root policy.
Registration of new runs is RF-004; Ops/Run Explorer wiring is RF-005.
"""

from __future__ import annotations

from bioetl.application.services.control_plane.evidence_location.resolver import (
    EvidenceLocationLegacyRootPolicy,
    EvidenceLocationResolver,
    EvidenceLocationResolveResult,
    EvidenceReadContext,
    EvidenceReadContextOpener,
)

__all__ = [
    "EvidenceLocationLegacyRootPolicy",
    "EvidenceLocationResolver",
    "EvidenceLocationResolveResult",
    "EvidenceReadContext",
    "EvidenceReadContextOpener",
]
