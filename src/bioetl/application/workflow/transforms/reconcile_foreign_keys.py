# Boundary object/payload typing residual at this module.
"""Facade workflow transform for foreign-key reconciliation (AUD-005).

This module only orchestrates the canonical implementation
(``infrastructure/storage/workflow_foreign_key_reconciliation.py``) through
``ForeignKeyReconciliationPort``: it builds the request, shapes the result
payload, and persists artifacts. Storage/mutation logic must not be duplicated
here; parity with the canonical adapter is enforced by
``tests/unit/application/workflow/test_reconcile_fk_parity.py``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from bioetl.application.workflow.transforms import (
    WorkflowTransformCallable,
    WorkflowTransformRuntimeContext,
)
from bioetl.application.workflow.transforms.reconcile_foreign_keys_config import (
    _optional_layer,
    _optional_runtime_str,
    _persist_reconcile_result_artifact,
    _require_delete_orphans_action,
    _required_primary_keys,
    _required_str,
    _resolve_reference_completeness,
    _resolve_reference_keys,
    _run_ids_from_upstream,
    _source_scope,
)
from bioetl.domain.ports import (
    ForeignKeyReconciliationPort,
    ForeignKeyReconciliationRequest,
)
from bioetl.domain.workflow import WorkflowTransformSpec

__all__ = ["build_reconcile_foreign_keys_executor"]


def _runtime_flag(
    runtime_context: WorkflowTransformRuntimeContext | None, name: str, default: bool
) -> bool:
    if runtime_context is None:
        return default
    return bool(getattr(runtime_context, name, default))


def _build_reconcile_payload(
    *,
    spec: WorkflowTransformSpec,
    request: ForeignKeyReconciliationRequest,
    result: object,
    workflow_name: object,
) -> dict[str, object]:
    # Port result is structural; keep boundary free of concrete infra result types.
    r = cast(Any, result)  # Any: structural FK reconcile result port
    payload = {
        "transform_name": spec.transform_name,
        "fingerprint": spec.fingerprint,
        "workflow_name": workflow_name,
        "workflow_run_id": request.workflow_run_id,
        "manifest_id": request.manifest_id,
        "step_id": spec.step_id,
        "source_table": r.source_table,
        "reference_table": r.reference_table,
        "source_key": r.source_key,
        "reference_key": r.reference_key,
        "source_layer": r.source_layer,
        "reference_layer": r.reference_layer,
        "mutation_layer": r.mutation_layer,
        "source_keys": list(request.source_keys or (request.source_key,)),
        "source_run_ids": list(request.source_run_ids),
        "source_scope": request.source_scope,
        "reference_keys": list(request.reference_keys or (request.reference_key,)),
        "action": r.action,
        "nulls_equal": request.nulls_equal,
        "scanned_rows": r.scanned_rows,
        "retained_rows": r.retained_rows,
        "orphan_rows_deleted": r.orphan_rows_deleted,
        "mutated": r.mutated,
        "dry_run": r.dry_run,
        "would_mutate": r.would_mutate,
        "mutation_mode": r.mutation_mode,
        "quarantine_batch_id": r.quarantine_batch_id,
        "quarantine_rows_written": r.quarantine_rows_written,
        "quarantine_error_code": r.quarantine_error_code,
        "reference_completeness": request.reference_completeness,
        "unproven_unmatched_rows": getattr(r, "unproven_unmatched_rows", 0),
    }
    blocked_reason = getattr(r, "mutation_blocked_reason", None)
    if blocked_reason:
        payload["mutation_blocked_reason"] = blocked_reason
    if r.dry_run and r.would_mutate:
        payload["mutation_blocked_reason"] = "workflow_dry_run"
    if getattr(r, "source_snapshot", None) is not None:
        payload["source_snapshot"] = dict(r.source_snapshot)
    return payload


def _record_reconcile_destructive_commit(
    runtime_context: WorkflowTransformRuntimeContext | None,
    *,
    spec: WorkflowTransformSpec,
    result: object,
    payload: dict[str, object],
) -> None:
    r = cast(Any, result)  # Any: structural FK reconcile result port
    if not r.mutated or r.dry_run:
        return
    if runtime_context is None or not hasattr(
        runtime_context, "record_destructive_commit"
    ):
        return
    runtime_context.record_destructive_commit(
        step_id=spec.step_id,
        transform_name=spec.transform_name,
        fingerprint=spec.fingerprint,
        details=payload,
    )


def build_reconcile_foreign_keys_executor(
    reconciliation_port: ForeignKeyReconciliationPort,
) -> WorkflowTransformCallable:
    """Build a storage-backed executor for `reconcile_foreign_keys`."""

    async def _executor(
        spec: WorkflowTransformSpec,
        upstream_outputs: Mapping[str, object],
        runtime_context: WorkflowTransformRuntimeContext | None = None,
    ) -> dict[str, object]:
        workflow_name = (
            getattr(runtime_context, "workflow_name", None)
            if runtime_context is not None
            else None
        )
        request = _build_request(
            spec,
            dry_run=_runtime_flag(runtime_context, "dry_run", False),
            workflow_name=workflow_name,
            workflow_run_id=_optional_runtime_str(runtime_context, "workflow_run_id"),
            manifest_id=_optional_runtime_str(runtime_context, "manifest_id"),
            debug_export_enabled=_runtime_flag(
                runtime_context, "debug_export_enabled", False
            ),
            debug_export_dir=_optional_runtime_str(runtime_context, "debug_export_dir"),
            source_run_ids=_run_ids_from_upstream(
                upstream_outputs,
                workflow_run_id=_optional_runtime_str(
                    runtime_context, "workflow_run_id"
                ),
                depends_on=tuple(spec.depends_on),
            ),
            upstream_outputs=upstream_outputs,
        )
        result = await reconciliation_port.reconcile_foreign_keys(request)
        payload = _build_reconcile_payload(
            spec=spec,
            request=request,
            result=result,
            workflow_name=workflow_name,
        )
        _record_reconcile_destructive_commit(
            runtime_context, spec=spec, result=result, payload=payload
        )
        artifact_refs = await _persist_reconcile_result_artifact(
            runtime_context,
            spec=spec,
            payload=payload,
        )
        if artifact_refs:
            payload["artifact_refs"] = list(artifact_refs)
        return payload

    return _executor


def _build_request(
    spec: WorkflowTransformSpec,
    *,
    dry_run: bool = False,
    workflow_name: str | None = None,
    workflow_run_id: str | None = None,
    manifest_id: str | None = None,
    debug_export_enabled: bool = False,
    debug_export_dir: str | None = None,
    source_run_ids: tuple[str, ...] = (),
    upstream_outputs: Mapping[str, object] | None = None,
) -> ForeignKeyReconciliationRequest:
    config = spec.config or {}
    source_table = _required_str(config, "source_table")
    reference_table = _required_str(config, "reference_table")
    _require_delete_orphans_action(config)
    primary_keys = _required_primary_keys(config)
    source_key, reference_key, source_keys, reference_keys = _resolve_reference_keys(
        config
    )
    source_layer = _optional_layer(config, "source_layer", default="silver")
    reference_layer = _optional_layer(config, "reference_layer", default="silver")
    assert source_layer is not None and reference_layer is not None
    completeness, identity, snapshot_version, evidence_ref = (
        _resolve_reference_completeness(
            config,
            upstream_outputs or {},
            reference_table=reference_table,
        )
    )
    return ForeignKeyReconciliationRequest(
        source_table=source_table,
        reference_table=reference_table,
        source_key=source_key,
        reference_key=reference_key,
        primary_keys=primary_keys,
        action="delete_orphans",
        source_layer=source_layer,
        reference_layer=reference_layer,
        mutation_layer=_optional_layer(config, "mutation_layer", default=None),
        source_keys=source_keys,
        reference_keys=reference_keys,
        nulls_equal=bool(config.get("nulls_equal", False)),
        dry_run=dry_run,
        workflow_name=workflow_name,
        workflow_run_id=workflow_run_id,
        manifest_id=manifest_id,
        step_id=spec.step_id,
        transform_name=spec.transform_name,
        debug_export_enabled=debug_export_enabled,
        debug_export_dir=debug_export_dir,
        source_scope=_source_scope(config),
        source_run_ids=source_run_ids,
        reference_completeness=completeness,
        reference_identity=identity,
        reference_snapshot_version=snapshot_version,
        completeness_evidence_ref=evidence_ref,
    )
