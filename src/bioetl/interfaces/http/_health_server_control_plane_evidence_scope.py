"""Selector and unavailable-state helpers for validation evidence routes."""

from __future__ import annotations

import asyncio
from typing import Protocol

from bioetl.application.observability.control_plane_evidence import (
    EvidenceCheckResult,
    EvidenceScopeContext,
)
from bioetl.application.observability.control_plane_evidence.service_support import (
    service_payload,
    source_error_payload,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.ports import RunManifestPort
from bioetl.interfaces.http._health_server_control_plane_scope import (
    _IdentityScope,
    read_selected_run_id,
    resolve_control_plane_identity_scope,
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
