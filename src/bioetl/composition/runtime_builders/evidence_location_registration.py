"""Composition-edge wiring for RF-004 evidence-location registration.

Reads typed Settings at the composition boundary. Application services
receive absolute paths, alias bases, and runtime_source_id as parameters.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.evidence_location.registration import (
    EvidenceLocationRegisterRequest,
    EvidenceLocationRegistrationOutcome,
    EvidenceLocationRegistrationService,
    EvidenceLocationVerifyOutcome,
)
from bioetl.application.services.run_reports.evidence_location_paths import (
    default_evidence_root_alias_registry,
)
from bioetl.domain.control_plane.run_evidence_location import (
    EvidenceLocationKind,
)
from bioetl.infrastructure.control_plane.file_evidence_location_store import (
    FileEvidenceLocationStore,
)

if TYPE_CHECKING:
    from bioetl.domain.control_plane.run_manifest import RunManifest
    from bioetl.domain.control_plane.workflow_manifest import WorkflowManifest
    from bioetl.infrastructure.config.settings_api import Settings

from bioetl.composition.runtime_builders.evidence_location_binding import (
    EvidenceLocationBindingContext,
    build_evidence_location_binding_context,
    relative_data_root_under_alias,
    resolve_dashboard_data_alias_base,
    resolve_registration_runtime_source_id as _resolve_registration_runtime_source_id,
)

__all__ = [
    "EvidenceLocationBindingContext",
    "build_evidence_location_binding_context",
    "build_evidence_location_registration_service",
    "register_pipeline_manifest_location",
    "register_workflow_manifest_location",
    "relative_data_root_under_alias",
    "resolve_dashboard_data_alias_base",
    "resolve_registration_runtime_source_id",
]


def _repository_root() -> Path:
    """Return the repository root; kept as a test seam for env-file lookup."""
    return Path(__file__).resolve().parents[4]


def resolve_registration_runtime_source_id(settings: Settings) -> str | None:
    """Resolve runtime source identity using this builder's repository root."""
    return _resolve_registration_runtime_source_id(
        settings, repository_root=_repository_root()
    )


def build_evidence_location_registration_service(
    settings: Settings,
) -> tuple[EvidenceLocationRegistrationService, EvidenceLocationBindingContext]:
    """Construct file-backed registration service + binding context."""
    binding = build_evidence_location_binding_context(settings)
    # Alias registry always uses the trusted dashboard base (never remapped).
    default_evidence_root_alias_registry(dashboard_data_root=binding.alias_base)
    store = FileEvidenceLocationStore(
        report_root=binding.report_root
        if binding.report_root is not None
        else Path("reports") / "run-reports"
    )
    return EvidenceLocationRegistrationService(locations=store), binding


def _soft_skip(*, code: str, detail: str) -> EvidenceLocationRegistrationOutcome:
    return EvidenceLocationRegistrationOutcome(code=code, detail=detail)


def _guard_registration_binding(
    binding: EvidenceLocationBindingContext,
) -> EvidenceLocationRegistrationOutcome | None:
    if binding.skip_reason is not None:
        return _soft_skip(
            code="skipped_write_root_outside_alias",
            detail=binding.skip_reason,
        )
    if binding.runtime_source_id is None:
        return _soft_skip(
            code="skipped_missing_runtime_source_id",
            detail="runtime_source_id unresolved; locator not published",
        )
    return None


def register_pipeline_manifest_location(
    *,
    manifest: RunManifest,
    settings: Settings,
) -> EvidenceLocationRegistrationOutcome:
    """Best-effort register after a pipeline manifest was persisted."""
    service, binding = build_evidence_location_registration_service(settings)
    skipped = _guard_registration_binding(binding)
    if skipped is not None:
        return skipped
    assert binding.runtime_source_id is not None
    workflow_run_id = getattr(manifest, "workflow_run_id", None)
    return service.register_pipeline_run(
        pipeline_name=str(manifest.pipeline_name),
        run_id=str(manifest.run_id),
        runtime_source_id=binding.runtime_source_id,
        relative_data_root=binding.relative_data_root,
        root_alias=binding.root_alias,
        workflow_run_id=str(workflow_run_id) if workflow_run_id else None,
    )


def register_workflow_manifest_location(
    *,
    manifest: WorkflowManifest,
    settings: Settings,
) -> EvidenceLocationRegistrationOutcome:
    """Best-effort register after a workflow parent manifest was persisted."""
    service, binding = build_evidence_location_registration_service(settings)
    skipped = _guard_registration_binding(binding)
    if skipped is not None:
        return skipped
    assert binding.runtime_source_id is not None
    return service.register_workflow_run(
        workflow_name=str(manifest.workflow_name),
        workflow_run_id=str(manifest.workflow_run_id),
        runtime_source_id=binding.runtime_source_id,
        relative_data_root=binding.relative_data_root,
        root_alias=binding.root_alias,
    )


def build_evidence_location_binding_service(
    settings: Settings,
) -> tuple[EvidenceLocationRegistrationService, EvidenceLocationBindingContext]:
    """Alias for :func:`build_evidence_location_registration_service`."""
    return build_evidence_location_registration_service(settings)


def _verify_bound_location(
    *,
    settings: Settings,
    kind: EvidenceLocationKind,
    owner: str,
    run_id: str,
    workflow_run_id: str | None,
) -> EvidenceLocationVerifyOutcome | None:
    """Finalize-time verify shared by pipeline and workflow callers."""
    service, binding = build_evidence_location_registration_service(settings)
    if binding.skip_reason is not None or binding.runtime_source_id is None:
        return None
    return service.record_verify_observation(
        EvidenceLocationRegisterRequest(
            kind=kind,
            owner=owner,
            run_id=run_id,
            runtime_source_id=binding.runtime_source_id,
            relative_data_root=binding.relative_data_root,
            root_alias=binding.root_alias,
            workflow_run_id=workflow_run_id,
        )
    )


def verify_pipeline_run_location(
    *,
    pipeline_name: str,
    run_id: str,
    workflow_run_id: str | None,
    settings: Settings,
) -> EvidenceLocationVerifyOutcome | None:
    """Finalize-time verify; returns None when binding cannot be published."""
    return _verify_bound_location(
        settings=settings,
        kind=EvidenceLocationKind.PIPELINE,
        owner=pipeline_name,
        run_id=run_id,
        workflow_run_id=workflow_run_id,
    )


def verify_workflow_run_location(
    *,
    workflow_name: str,
    workflow_run_id: str,
    settings: Settings,
) -> EvidenceLocationVerifyOutcome | None:
    """Finalize-time verify for a workflow parent locator."""
    return _verify_bound_location(
        settings=settings,
        kind=EvidenceLocationKind.WORKFLOW,
        owner=workflow_name,
        run_id=workflow_run_id,
        workflow_run_id=None,
    )
