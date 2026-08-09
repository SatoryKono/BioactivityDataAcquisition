"""Bounded routes for run-scoped control-plane validation evidence."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Protocol

from bioetl.application.runtime_clock import current_utc_time
from bioetl.application.services.control_plane.evidence import (
    ControlPlaneEvidenceService,
    EvidenceScope,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.http._forensic_request_budget import (
    ForensicEndpointUnavailable,
    forensic_unavailable_payload,
    run_bounded_forensic_operation,
)
from bioetl.interfaces.http._health_server_checkpoint_lookup import (
    load_checkpoint_freshness_evidence,
)
from bioetl.interfaces.http._health_server_control_plane_scope import (
    _IdentityScope,
    read_selected_run_id,
    resolve_control_plane_identity_scope,
)

_SOURCE_READ_ERRORS = (BioETLError, OSError, TypeError, ValueError)


class _EvidenceRoutingHost(Protocol):
    @property
    def _control_plane_evidence_service(
        self,
    ) -> ControlPlaneEvidenceService | None: ...

    @property
    def _forensic_endpoint_limiter(self) -> asyncio.Semaphore: ...

    def _read_required_param(self, query: dict[str, str], name: str) -> str: ...

    @staticmethod
    def _read_optional_param(query: dict[str, str], name: str) -> str | None: ...

    @classmethod
    def _read_scope_csv_param(
        cls,
        query: dict[str, str],
        name: str,
    ) -> tuple[str, ...]: ...

    async def _send_response(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        message: str,
    ) -> None: ...

    async def _send_payload_response(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        payload: dict[str, object],
    ) -> None: ...


async def dispatch_control_plane_evidence_request(
    host: _EvidenceRoutingHost,
    *,
    writer: asyncio.StreamWriter,
    path: str,
    query: dict[str, str],
) -> bool:
    """Handle one validation route and return whether the path was recognized."""
    operations: dict[
        str,
        Callable[[], Awaitable[dict[str, object]]],
    ] = {
        "/ops/control-plane/checkpoint-validation": lambda: _checkpoint_payload(
            host, query
        ),
        "/ops/control-plane/manifest-validation": lambda: _service_payload(
            host, query, endpoint="manifest-validation"
        ),
        "/ops/control-plane/lineage-validation": lambda: _service_payload(
            host, query, endpoint="lineage-validation"
        ),
        "/ops/control-plane/retention-compliance": lambda: _service_payload(
            host, query, endpoint="retention-compliance"
        ),
        "/ops/control-plane/failure-reasons": lambda: _service_payload(
            host, query, endpoint="failure-reasons"
        ),
    }
    operation_factory = operations.get(path)
    if operation_factory is None:
        return False
    if host._control_plane_evidence_service is None:
        await host._send_response(
            writer,
            503,
            "Control-plane validation evidence unavailable",
        )
        return True
    try:
        payload = await run_bounded_forensic_operation(
            limiter=host._forensic_endpoint_limiter,
            operation_factory=operation_factory,
        )
    except ForensicEndpointUnavailable as exc:
        await host._send_payload_response(
            writer,
            exc.status_code,
            forensic_unavailable_payload(endpoint=path, reason=exc.reason),
        )
        return True
    await host._send_payload_response(writer, 200, payload)
    return True


async def _checkpoint_payload(
    host: _EvidenceRoutingHost,
    query: dict[str, str],
) -> dict[str, object]:
    service = _require_service(host)
    scope, error_payload = await _resolve_scope(
        host,
        query,
        endpoint="checkpoint-validation",
        check="parse",
        reason="checkpoint_scope_manifest_parse_error",
    )
    if error_payload is not None:
        return error_payload
    assert scope is not None
    target_pipeline = (
        scope.resolved_manifest.pipeline_name
        if scope.resolved_manifest is not None
        else scope.requested_pipeline
    )
    try:
        (
            checkpoint,
            evidence_source,
            _,
            aggregate_scope_unknown,
        ) = await load_checkpoint_freshness_evidence(
            host,  # type: ignore[arg-type]
            scope=scope,
            target_pipeline=target_pipeline,
        )
    except _SOURCE_READ_ERRORS:
        return service.source_error(
            endpoint="checkpoint-validation",
            scope=_evidence_scope(scope),
            reason="checkpoint_parse_error",
            check="parse",
        )
    return await asyncio.to_thread(
        service.checkpoint_validation,
        scope=_evidence_scope(scope),
        checkpoint=checkpoint,
        evidence_source=evidence_source,
        aggregate_scope_unknown=aggregate_scope_unknown,
    )


async def _service_payload(
    host: _EvidenceRoutingHost,
    query: dict[str, str],
    *,
    endpoint: str,
) -> dict[str, object]:
    service = _require_service(host)
    source_reason, source_check = {
        "manifest-validation": ("manifest_parse_error", "parse"),
        "lineage-validation": ("lineage_source_read_error", "closure"),
        "retention-compliance": ("retention_plan_read_error", "retention_policy"),
        "failure-reasons": ("run_ledger_parse_error", "classification"),
    }[endpoint]
    scope, error_payload = await _resolve_scope(
        host,
        query,
        endpoint=endpoint,
        check=source_check,
        reason=source_reason,
    )
    if error_payload is not None:
        return error_payload
    assert scope is not None
    evidence_scope = _evidence_scope(scope)
    try:
        if endpoint == "retention-compliance":
            return await asyncio.to_thread(
                service.retention_compliance,
                scope=evidence_scope,
                now=current_utc_time(),
            )
        method = getattr(service, endpoint.replace("-", "_"))
        return await asyncio.to_thread(method, scope=evidence_scope)
    except _SOURCE_READ_ERRORS:
        return service.source_error(
            endpoint=endpoint,
            scope=evidence_scope,
            reason=source_reason,
            check=source_check,
        )


async def _resolve_scope(
    host: _EvidenceRoutingHost,
    query: dict[str, str],
    *,
    endpoint: str,
    check: str,
    reason: str,
) -> tuple[_IdentityScope | None, dict[str, object] | None]:
    service = _require_service(host)
    try:
        scope = await asyncio.to_thread(
            resolve_control_plane_identity_scope,
            host,  # type: ignore[arg-type]
            query,
        )
    except _SOURCE_READ_ERRORS:
        fallback = EvidenceScope(
            requested_pipeline=host._read_required_param(query, "pipeline"),
            selected_run_id=read_selected_run_id(host, query),  # type: ignore[arg-type]
            selected_run_types=host._read_scope_csv_param(query, "run_type"),
            resolved_via="control_plane_source_read_failed",
            manifest=None,
        )
        return None, service.source_error(
            endpoint=endpoint,
            scope=fallback,
            reason=reason,
            check=check,
        )
    return scope, None


def _evidence_scope(scope: _IdentityScope) -> EvidenceScope:
    return EvidenceScope(
        requested_pipeline=scope.requested_pipeline,
        selected_run_id=scope.selected_run_id,
        selected_run_types=scope.selected_run_types,
        resolved_via=scope.resolved_via,
        manifest=scope.resolved_manifest,
    )


def _require_service(host: _EvidenceRoutingHost) -> ControlPlaneEvidenceService:
    service = host._control_plane_evidence_service
    if service is None:
        raise RuntimeError("control-plane evidence service is unavailable")
    return service


__all__ = ["dispatch_control_plane_evidence_request"]
