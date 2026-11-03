"""Registration request and result models for evidence locations."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.control_plane.run_evidence_location import (
    DEFAULT_EVIDENCE_ROOT_ALIAS,
    EvidenceLocationKind,
    RunEvidenceLocation,
    build_run_evidence_location,
)


@dataclass(frozen=True, slots=True)
class EvidenceLocationRegisterRequest:
    """DI-bound inputs for one ownership key registration."""

    kind: EvidenceLocationKind | str
    owner: str
    run_id: str
    runtime_source_id: str
    relative_data_root: str
    root_alias: str = DEFAULT_EVIDENCE_ROOT_ALIAS
    workflow_run_id: str | None = None


@dataclass(frozen=True, slots=True)
class EvidenceLocationRegistrationOutcome:
    """Bounded registration result for diagnostics (not a replay verdict)."""

    code: str
    detail: str | None = None
    revision: str | None = None


@dataclass(frozen=True, slots=True)
class EvidenceLocationVerifyOutcome:
    """Finalize-time consistency result; never implies READY."""

    code: str
    detail: str | None = None
    verdict: str = "UNKNOWN"


def _location_from_request(
    request: EvidenceLocationRegisterRequest,
) -> RunEvidenceLocation:
    """Build the immutable locator payload shared by register and verify."""
    return build_run_evidence_location(
        kind=request.kind,
        owner=request.owner,
        run_id=request.run_id,
        runtime_source_id=request.runtime_source_id,
        root_alias=request.root_alias,
        relative_data_root=request.relative_data_root,
        workflow_run_id=request.workflow_run_id,
    )
