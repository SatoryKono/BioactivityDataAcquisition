# Boundary object/payload typing residual at this module.
"""Built-in workflow transform for foreign-key reconciliation."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.application.workflow.transforms import (
    WorkflowTransformCallable,
    WorkflowTransformRuntimeContext,
)
from bioetl.application.workflow.transforms._reconcile_foreign_keys_support import (
    _build_reconcile_payload,
    _optional_layer,
    _optional_runtime_str,
    _payload_run_ids,
    _persist_reconcile_result_artifact,
    _record_reconcile_destructive_commit,
    _require_delete_orphans_action,
    _required_primary_keys,
    _required_str,
    _resolve_reference_completeness,
    _resolve_reference_keys,
    _source_scope,
)
from bioetl.application.workflow.transforms._reconcile_foreign_keys_support import (
    _optional_key_tuple as _optional_key_tuple,
)
from bioetl.application.workflow.transforms._reconcile_foreign_keys_support import (
    _upstream_completeness_evidence as _upstream_completeness_evidence,
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


def _run_ids_from_upstream(
    upstream_outputs: Mapping[str, object],
    *,
    workflow_run_id: str | None,
    depends_on: tuple[str, ...] = (),
) -> tuple[str, ...]:
    selected = upstream_outputs
    if depends_on:
        allowed = set(depends_on)
        selected = {
            step_id: payload
            for step_id, payload in upstream_outputs.items()
            if step_id in allowed
        }
    candidates: list[object] = [workflow_run_id]
    for payload in selected.values():
        candidates.extend(_payload_run_ids(payload))
    normalized = [str(value).strip() for value in candidates if value]
    return tuple(dict.fromkeys(value for value in normalized if value))
