"""Bounded run-scoped control-plane validation evidence service."""

from __future__ import annotations

from bioetl.application.observability.control_plane_evidence.checks import (
    EvidenceCheckResult,
    EvidenceStatus,
)
from bioetl.application.observability.control_plane_evidence.failure_reasons import (
    FAILURE_REASON_CATEGORIES,
    build_unknown_failure_reason_rows,
)
from bioetl.application.observability.control_plane_evidence.models import (
    CONTROL_PLANE_EVIDENCE_CONTRACT,
)
from bioetl.application.observability.control_plane_evidence.service import (
    DEFAULT_CONTROL_PLANE_RETENTION_DAYS,
    ControlPlaneEvidenceService,
)
from bioetl.application.observability.control_plane_evidence.service_support import (
    EvidenceScopeContext,
)

__all__ = [
    "CONTROL_PLANE_EVIDENCE_CONTRACT",
    "DEFAULT_CONTROL_PLANE_RETENTION_DAYS",
    "FAILURE_REASON_CATEGORIES",
    "ControlPlaneEvidenceService",
    "EvidenceCheckResult",
    "EvidenceScopeContext",
    "EvidenceStatus",
    "build_unknown_failure_reason_rows",
]
