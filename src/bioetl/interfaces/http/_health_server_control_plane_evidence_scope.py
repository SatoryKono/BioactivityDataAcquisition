"""Selector and unavailable-state helpers for validation evidence routes."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Protocol
from uuid import UUID

from bioetl.application.observability.control_plane_evidence import (
    ControlPlaneEvidenceService,
    EvidenceCheckResult,
    EvidenceScopeContext,
)
from bioetl.application.observability.control_plane_evidence.service_support import (
    service_payload,
    source_error_payload,
)
from bioetl.application.observability.control_plane_evidence.timing import (
    evidence_stage,
)
from bioetl.application.services.evidence_location.resolver import (
    EvidenceLocationResolver,
    EvidenceReadContext,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.ports import RunManifestPort, RunReportStorePort
from bioetl.interfaces.http._health_server_control_plane_scope import (
    _IdentityScope,
    read_selected_run_id,
    resolve_control_plane_identity_scope,
)
from bioetl.interfaces.http._processed_records_value_support import _is_all_scope
from bioetl.interfaces.http._report_selector_options import (
    verified_report_identity_for_run,
)

SOURCE_READ_ERRORS = (BioETLError, OSError, TypeError, ValueError)


class EvidenceScopeHost(Protocol):
    """Minimal routing host required to resolve control-plane identity."""

    @property
    def _run_manifest_port(self) -> RunManifestPort | None: ...

    def _read_required_param(self, query: dict[str, str], name: str) -> str: ...

    @staticmethod
    def _read_optional_param(query: dict[str, str], name: str) -> str | None: ...

    @classmethod
    def _read_scope_csv_param(
        cls,
        query: dict[str, str],
        name: str,
    ) -> tuple[str, ...]: ...


async def resolve_evidence_scope(
    host: EvidenceScopeHost,
    query: dict[str, str],
    *,
    endpoint: str,
    check: str,
    reason: str,
) -> tuple[_IdentityScope | None, dict[str, object] | None]:
    """Resolve one selector scope, mapping source failures to stable evidence."""
    requested_pipeline = _safe_required_param(host, query, "pipeline")
    try:
        with evidence_stage("manifest_resolution"):
            scope = await asyncio.to_thread(
                resolve_control_plane_identity_scope,
                host,
                query,
            )
    except SOURCE_READ_ERRORS:
        fallback = _unresolved_evidence_scope(
            host,
            query,
            resolved_via="control_plane_source_read_failed",
            requested_pipeline=requested_pipeline,
        )
        return None, source_error_payload(
            endpoint=endpoint,
            scope=fallback,
            reason=reason,
            check=check,
        )
    return scope, None


def to_evidence_scope(scope: _IdentityScope) -> EvidenceScopeContext:
    """Project the shared HTTP identity scope to the application DTO."""
    return EvidenceScopeContext(
        requested_pipeline=scope.requested_pipeline,
        selected_run_id=scope.selected_run_id,
        selected_run_types=scope.selected_run_types,
        resolved_via=scope.resolved_via,
        manifest=scope.resolved_manifest,
    )


def evidence_service_unavailable_payload(
    host: EvidenceScopeHost,
    query: dict[str, str],
    *,
    endpoint: str,
) -> dict[str, object]:
    """Return the table contract even when its optional service is absent."""
    return service_payload(
        endpoint=endpoint,
        scope=_unresolved_evidence_scope(
            host,
            query,
            resolved_via="evidence_service_unavailable",
        ),
        checks=(
            EvidenceCheckResult(
                "evidence_service",
                "UNKNOWN",
                "control_plane_evidence_service_unavailable",
                "The optional control-plane evidence service is not configured.",
            ),
        ),
    )


def _safe_required_param(
    host: EvidenceScopeHost,
    query: dict[str, str],
    name: str,
) -> str:
    """Read a required query param without raising outside a caller handler."""
    try:
        return host._read_required_param(query, name)
    except SOURCE_READ_ERRORS:
        return ""


def _unresolved_evidence_scope(
    host: EvidenceScopeHost,
    query: dict[str, str],
    *,
    resolved_via: str,
    requested_pipeline: str | None = None,
) -> EvidenceScopeContext:
    pipeline = (
        requested_pipeline
        if requested_pipeline is not None
        else _safe_required_param(host, query, "pipeline")
    )
    return EvidenceScopeContext(
        requested_pipeline=pipeline,
        selected_run_id=read_selected_run_id(host, query),
        selected_run_types=host._read_scope_csv_param(query, "run_type"),
        resolved_via=resolved_via,
        manifest=None,
    )


__all__ = [
    "SOURCE_READ_ERRORS",
    "EvidenceScopeHost",
    "evidence_service_unavailable_payload",
    "resolve_evidence_scope",
    "to_evidence_scope",
]


def _same_run_id(left: object, right: object) -> bool:
    """Compare run ids as UUID values when both parse; else compare as text."""
    try:
        return UUID(str(left)) == UUID(str(right))
    except (TypeError, ValueError, AttributeError):
        return str(left) == str(right)


def _selected_validation_pipeline(
    host: EvidenceScopeHost, scope: _IdentityScope
) -> str:
    """Resolve one owner while rejecting a conflicting concrete request."""
    requested = scope.requested_pipeline
    is_all_scope = getattr(host, "_is_all_scope_token", _is_all_scope)
    concrete_requested = bool(requested) and not is_all_scope(requested)
    if concrete_requested:
        if (
            scope.resolved_manifest is not None
            and scope.resolved_manifest.pipeline_name != requested
        ):
            raise ValueError("Selected validation manifest identity does not match")
        return requested
    return (
        scope.resolved_manifest.pipeline_name if scope.resolved_manifest else requested
    )


def _validate_bound_manifest(
    manifest: object, *, scope: _IdentityScope, pipeline: str
) -> RunManifest:
    """Require a manifest matching the selected run, pipeline and run types."""
    if (
        not isinstance(manifest, RunManifest)
        or not _same_run_id(manifest.run_id, scope.selected_run_id)
        or manifest.pipeline_name != pipeline
        or (
            scope.selected_run_types
            and manifest.run_type.value not in scope.selected_run_types
        )
    ):
        raise ValueError("Selected validation manifest identity does not match")
    return manifest


def _resolve_validation_context(
    host: EvidenceScopeHost,
    scope: _IdentityScope,
    resolver: EvidenceLocationResolver,
    pipeline: str,
    run_id: str,
) -> EvidenceReadContext | None:
    """Resolve the selected root while retaining report-only diagnostics."""
    try:
        resolved = resolver.resolve(
            kind="pipeline",
            owner=pipeline,
            run_id=run_id,
            expected_runtime_source_id=getattr(host, "_runtime_source_id", None),
        )
    except (*SOURCE_READ_ERRORS, AttributeError):
        if scope.resolved_via == "resolved_without_manifest":
            return None
        raise
    if resolved.context is None or resolved.code.value in {
        "identity_conflict",
        "location_invalid",
    }:
        if scope.resolved_via == "resolved_without_manifest":
            return None
        raise ValueError("Selected validation evidence location is unavailable")
    return resolved.context


def _bind_selected_validation(
    host: EvidenceScopeHost,
    scope: _IdentityScope,
    service: ControlPlaneEvidenceService,
) -> tuple[_IdentityScope, ControlPlaneEvidenceService]:
    """Keep validation, lifecycle and ledger ports on the selected locator root."""
    resolver = getattr(host, "_evidence_location_resolver", None)
    if (
        not isinstance(resolver, EvidenceLocationResolver)
        or scope.selected_run_id is None
    ):
        return scope, service
    pipeline = _selected_validation_pipeline(host, scope)
    context = _resolve_validation_context(
        host, scope, resolver, pipeline, scope.selected_run_id
    )
    if context is None:
        return scope, service
    manifest = context.get_manifest_by_run_id(scope.selected_run_id)
    if manifest is None and scope.resolved_via in {
        "selected_run_id_not_found",
        "resolved_without_manifest",
    }:
        # The selected root was checked; no evidence ports exist for this UUID.
        return scope, service
    manifest = _validate_bound_manifest(manifest, scope=scope, pipeline=pipeline)
    getter = getattr(context, "get_validation_service", None)
    bound = getter() if callable(getter) else None
    if not isinstance(bound, ControlPlaneEvidenceService):
        raise ValueError("Selected validation ports are unavailable")
    return replace(scope, resolved_manifest=manifest), bound


_CATALOG_MEMBERSHIP_SCOPES: dict[str, tuple[str, ...]] = {
    "workflow": (),
    "pipeline": (),
    "run_type": (),
    "run_status": (),
}


def reconcile_manifest_validation_scope(
    scope: _IdentityScope,
    *,
    report_store: RunReportStorePort | None,
) -> _IdentityScope:
    """Map a report-catalog run that has no manifest off ``selected_run_id_not_found``.

    ``selected_run_id_not_found`` stays only when the run id is absent from the
    manifest catalog and from the report catalog. A manifest-catalog hit is
    unchanged. Other validation routes do not call this helper.
    """
    if scope.resolved_via != "selected_run_id_not_found":
        return scope
    run_id = scope.selected_run_id
    if run_id is None or report_store is None:
        return scope
    identity = verified_report_identity_for_run(
        run_id,
        _CATALOG_MEMBERSHIP_SCOPES,
        store=report_store,
    )
    if identity is None:
        return scope
    return _IdentityScope(
        requested_pipeline=scope.requested_pipeline,
        selected_pipelines=scope.selected_pipelines,
        selected_run_types=scope.selected_run_types,
        selected_run_id=scope.selected_run_id,
        resolved_manifest=scope.resolved_manifest,
        resolved_via="resolved_without_manifest",
    )


async def _reconcile_validation_scope(
    host: EvidenceScopeHost,
    scope: _IdentityScope,
    *,
    endpoint: str,
) -> _IdentityScope:
    """Reconcile manifest catalog selection before binding its validation ports."""
    if endpoint == "manifest-validation":
        return await asyncio.to_thread(
            reconcile_manifest_validation_scope,
            scope,
            report_store=getattr(host, "_run_report_store", None),
        )
    return scope
