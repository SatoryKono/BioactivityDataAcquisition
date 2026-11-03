"""Evidence-location registration and finalize consistency (RF-004).

Primary registration runs after durable manifest save. Report finalization
only verifies the locator and records a diagnostic observation — it never
mutates processing_status / identity.status and never invents READY.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from bioetl.application.services.control_plane.evidence_location.registration_models import (
    EvidenceLocationRegisterRequest,
    EvidenceLocationRegistrationOutcome,
    EvidenceLocationVerifyOutcome,
)
from bioetl.application.services.control_plane.evidence_location.registration_observations import (
    EVIDENCE_LOCATION_OBSERVATION_DOMAIN,
    EVIDENCE_LOCATION_SOFT_FAILURE_EXCEPTIONS,
    record_registration_exception_observation,
    record_registration_outcome_observation,
    record_registration_soft_failure_observation,
    record_verify_exception_observation,
    soft_failure_exception_detail,
    soft_invoke_evidence_location_verify,
)
from bioetl.application.services.run_reports.observations import record_run_observation
from bioetl.domain.control_plane.run_evidence_location import (
    DEFAULT_EVIDENCE_ROOT_ALIAS,
    EvidenceLocationConflictError,
    EvidenceLocationInvalidError,
    EvidenceLocationKind,
    EvidenceLocationLookupCode,
    EvidenceLocationRegisterOutcome,
    RunEvidenceLocation,
    build_run_evidence_location,
)
from bioetl.domain.ports import (
    RunEvidenceLocationReadPort,
    RunEvidenceLocationRegisterPort,
)

__all__ = [
    "EVIDENCE_LOCATION_OBSERVATION_DOMAIN",
    "EVIDENCE_LOCATION_SOFT_FAILURE_EXCEPTIONS",
    "EvidenceLocationRegisterRequest",
    "EvidenceLocationRegistrationOutcome",
    "EvidenceLocationRegistrationService",
    "EvidenceLocationVerifyOutcome",
    "record_registration_exception_observation",
    "record_registration_outcome_observation",
    "record_registration_soft_failure_observation",
    "record_verify_exception_observation",
    "soft_failure_exception_detail",
    "soft_invoke_evidence_location_verify",
]


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
            location = _location_from_request(request)
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
                detail=soft_failure_exception_detail(exc),
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
            expected = _location_from_request(request)
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
