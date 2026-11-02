"""Evidence-location registration and finalize consistency (RF-004).

Primary registration runs after durable manifest save. Report finalization
only verifies the locator and records a diagnostic observation — it never
mutates processing_status / identity.status and never invents READY.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from bioetl.application.services.run_reports.observations import record_run_observation
from bioetl.domain.control_plane.run_evidence_location import (
    DEFAULT_EVIDENCE_ROOT_ALIAS,
    EvidenceLocationConflictError,
    EvidenceLocationInvalidError,
    EvidenceLocationKind,
    EvidenceLocationLookupCode,
    EvidenceLocationRegisterOutcome,
    build_run_evidence_location,
)
from bioetl.domain.ports.control_plane.run_evidence_location import (
    RunEvidenceLocationReadPort,
    RunEvidenceLocationRegisterPort,
)

__all__ = [
    "EVIDENCE_LOCATION_OBSERVATION_DOMAIN",
    "EvidenceLocationRegisterRequest",
    "EvidenceLocationRegistrationOutcome",
    "EvidenceLocationRegistrationService",
    "EvidenceLocationVerifyOutcome",
    "record_registration_soft_failure_observation",
]

EVIDENCE_LOCATION_OBSERVATION_DOMAIN = "Evidence Location"

_REGISTRATION_SUCCESS_CODES = frozenset({"registered", "already_identical"})


def record_registration_soft_failure_observation(
    *,
    code: str,
    detail: str | None = None,
    facts: dict[str, object] | None = None,
) -> None:
    """Publish conflict/error/exception diagnostics without mutating status.

    Success and explicit skip codes stay silent. Soft-register callers use this
    so RF-004 failures remain visible on the Evidence Location observation
    channel while processing_status stays untouched.
    """
    if code in _REGISTRATION_SUCCESS_CODES or code.startswith("skipped_"):
        return
    payload = dict(facts or {})
    if detail is not None:
        payload.setdefault("detail", detail)
    record_run_observation(
        EVIDENCE_LOCATION_OBSERVATION_DOMAIN,
        verdict="ERROR",
        reason=code,
        facts=payload,
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


class _RegisterAndReadPort(
    RunEvidenceLocationRegisterPort, RunEvidenceLocationReadPort, Protocol
):
    """Store surface that supports both register and lookup."""


@dataclass(slots=True)
class EvidenceLocationRegistrationService:
    """Application publisher for run evidence-location locators."""

    locations: _RegisterAndReadPort

    def register(
        self, request: EvidenceLocationRegisterRequest
    ) -> EvidenceLocationRegistrationOutcome:
        """Create-if-absent / idempotent-identical register; soft conflict."""
        try:
            location = build_run_evidence_location(
                kind=request.kind,
                owner=request.owner,
                run_id=request.run_id,
                runtime_source_id=request.runtime_source_id,
                root_alias=request.root_alias,
                relative_data_root=request.relative_data_root,
                workflow_run_id=request.workflow_run_id,
            )
        except EvidenceLocationInvalidError as exc:
            return EvidenceLocationRegistrationOutcome(
                code="invalid",
                detail=str(exc),
            )
        try:
            result = self.locations.register(location)
        except EvidenceLocationConflictError as exc:
            return EvidenceLocationRegistrationOutcome(
                code="conflict",
                detail=str(exc),
            )
        except (OSError, ValueError) as exc:
            return EvidenceLocationRegistrationOutcome(
                code="error",
                detail=f"{type(exc).__name__}: {exc}",
            )
        if result.outcome is EvidenceLocationRegisterOutcome.REGISTERED:
            return EvidenceLocationRegistrationOutcome(
                code="registered",
                revision=location.revision,
            )
        if result.outcome is EvidenceLocationRegisterOutcome.ALREADY_IDENTICAL:
            return EvidenceLocationRegistrationOutcome(
                code="already_identical",
                revision=location.revision,
            )
        return EvidenceLocationRegistrationOutcome(
            code="conflict",
            detail=result.detail or "binding_conflict",
            revision=location.revision,
        )

    def register_pipeline_run(
        self,
        *,
        pipeline_name: str,
        run_id: str,
        runtime_source_id: str,
        relative_data_root: str,
        root_alias: str = DEFAULT_EVIDENCE_ROOT_ALIAS,
        workflow_run_id: str | None = None,
    ) -> EvidenceLocationRegistrationOutcome:
        """Register a pipeline (standalone or workflow child) locator."""
        return self.register(
            EvidenceLocationRegisterRequest(
                kind=EvidenceLocationKind.PIPELINE,
                owner=pipeline_name,
                run_id=run_id,
                runtime_source_id=runtime_source_id,
                relative_data_root=relative_data_root,
                root_alias=root_alias,
                workflow_run_id=workflow_run_id,
            )
        )

    def register_workflow_run(
        self,
        *,
        workflow_name: str,
        workflow_run_id: str,
        runtime_source_id: str,
        relative_data_root: str,
        root_alias: str = DEFAULT_EVIDENCE_ROOT_ALIAS,
    ) -> EvidenceLocationRegistrationOutcome:
        """Register a workflow-parent locator (``workflow_run_id`` field null)."""
        return self.register(
            EvidenceLocationRegisterRequest(
                kind=EvidenceLocationKind.WORKFLOW,
                owner=workflow_name,
                run_id=workflow_run_id,
                runtime_source_id=runtime_source_id,
                relative_data_root=relative_data_root,
                root_alias=root_alias,
                workflow_run_id=None,
            )
        )

    def verify(
        self, request: EvidenceLocationRegisterRequest
    ) -> EvidenceLocationVerifyOutcome:
        """Lookup + binding compare for report finalization diagnostics."""
        try:
            expected = build_run_evidence_location(
                kind=request.kind,
                owner=request.owner,
                run_id=request.run_id,
                runtime_source_id=request.runtime_source_id,
                root_alias=request.root_alias,
                relative_data_root=request.relative_data_root,
                workflow_run_id=request.workflow_run_id,
            )
        except EvidenceLocationInvalidError as exc:
            return EvidenceLocationVerifyOutcome(
                code="invalid",
                detail=str(exc),
                verdict="INCOMPLETE",
            )
        lookup = self.locations.lookup(
            kind=request.kind,
            owner=request.owner,
            run_id=request.run_id,
            expected_runtime_source_id=request.runtime_source_id,
        )
        if lookup.code is EvidenceLocationLookupCode.LOCATION_MISSING:
            return EvidenceLocationVerifyOutcome(
                code="location_missing",
                detail=lookup.detail,
                verdict="INCOMPLETE",
            )
        if lookup.code is EvidenceLocationLookupCode.LOCATION_INVALID:
            return EvidenceLocationVerifyOutcome(
                code="location_invalid",
                detail=lookup.detail,
                verdict="ERROR",
            )
        if lookup.code is EvidenceLocationLookupCode.IDENTITY_CONFLICT:
            return EvidenceLocationVerifyOutcome(
                code="identity_conflict",
                detail=lookup.detail,
                verdict="ERROR",
            )
        found = lookup.location
        if found is None:
            return EvidenceLocationVerifyOutcome(
                code="location_missing",
                verdict="INCOMPLETE",
            )
        if found.revision != expected.revision:
            return EvidenceLocationVerifyOutcome(
                code="binding_mismatch",
                detail=(
                    f"expected_revision={expected.revision} "
                    f"found_revision={found.revision}"
                ),
                verdict="ERROR",
            )
        return EvidenceLocationVerifyOutcome(code="ok", verdict="OK")

    def record_verify_observation(
        self, request: EvidenceLocationRegisterRequest
    ) -> EvidenceLocationVerifyOutcome:
        """Verify and publish an Evidence Location observation (soft)."""
        outcome = self.verify(request)
        record_run_observation(
            EVIDENCE_LOCATION_OBSERVATION_DOMAIN,
            verdict=outcome.verdict,
            reason=outcome.code,
            facts={
                "kind": str(
                    request.kind.value
                    if isinstance(request.kind, EvidenceLocationKind)
                    else request.kind
                ),
                "owner": request.owner,
                "run_id": request.run_id,
                "workflow_run_id": request.workflow_run_id,
                "root_alias": request.root_alias,
                "relative_data_root": request.relative_data_root,
                "detail": outcome.detail,
            },
        )
        return outcome
