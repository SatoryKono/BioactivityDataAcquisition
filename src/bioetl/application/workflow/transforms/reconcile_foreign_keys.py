"""Built-in workflow transform for foreign-key reconciliation."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping

from bioetl.application.services.workflow_transform_artifacts import (
    WorkflowTransformArtifactContext,
    artifact_refs_as_dicts,
)
from bioetl.application.workflow.transforms import WorkflowTransformRuntimeContext
from bioetl.domain.ports import (
    ForeignKeyReconciliationPort,
    ForeignKeyReconciliationRequest,
)
from bioetl.domain.workflow import WorkflowTransformSpec

__all__ = ["build_reconcile_foreign_keys_executor"]


def build_reconcile_foreign_keys_executor(
    reconciliation_port: ForeignKeyReconciliationPort,
):
    """Build a storage-backed executor for `reconcile_foreign_keys`."""

    async def _executor(
        spec: WorkflowTransformSpec,
        upstream_outputs: Mapping[str, object],
        runtime_context: WorkflowTransformRuntimeContext | None = None,
    ) -> dict[str, object]:
        del upstream_outputs
        context_dry_run = (
            False
            if runtime_context is None
            else getattr(runtime_context, "dry_run", False)
        )
        workflow_name = (
            getattr(runtime_context, "workflow_name", None)
            if runtime_context is not None
            else None
        )
        request = _build_request(
            spec,
            dry_run=context_dry_run,
            workflow_name=workflow_name,
            workflow_run_id=_optional_runtime_str(runtime_context, "workflow_run_id"),
            manifest_id=_optional_runtime_str(runtime_context, "manifest_id"),
            debug_export_enabled=(
                bool(getattr(runtime_context, "debug_export_enabled", False))
                if runtime_context is not None
                else False
            ),
            debug_export_dir=_optional_runtime_str(runtime_context, "debug_export_dir"),
        )
        result = await reconciliation_port.reconcile_foreign_keys(request)
        payload = {
            "transform_name": spec.transform_name,
            "fingerprint": spec.fingerprint,
            "workflow_name": workflow_name,
            "workflow_run_id": request.workflow_run_id,
            "manifest_id": request.manifest_id,
            "step_id": spec.step_id,
            "source_table": result.source_table,
            "reference_table": result.reference_table,
            "source_key": result.source_key,
            "reference_key": result.reference_key,
            "source_layer": result.source_layer,
            "reference_layer": result.reference_layer,
            "mutation_layer": result.mutation_layer,
            "source_keys": list(request.source_keys or (request.source_key,)),
            "reference_keys": list(request.reference_keys or (request.reference_key,)),
            "action": result.action,
            "nulls_equal": request.nulls_equal,
            "scanned_rows": result.scanned_rows,
            "retained_rows": result.retained_rows,
            "orphan_rows_deleted": result.orphan_rows_deleted,
            "mutated": result.mutated,
            "dry_run": result.dry_run,
            "would_mutate": result.would_mutate,
            "mutation_mode": result.mutation_mode,
            "quarantine_batch_id": result.quarantine_batch_id,
            "quarantine_rows_written": result.quarantine_rows_written,
            "quarantine_error_code": result.quarantine_error_code,
        }
        if result.dry_run and result.would_mutate:
            payload["mutation_blocked_reason"] = "workflow_dry_run"
        if (
            result.mutated
            and not result.dry_run
            and runtime_context is not None
            and hasattr(runtime_context, "record_destructive_commit")
        ):
            runtime_context.record_destructive_commit(
                step_id=spec.step_id,
                transform_name=spec.transform_name,
                fingerprint=spec.fingerprint,
                details=payload,
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
) -> ForeignKeyReconciliationRequest:
    config = spec.config or {}
    source_table = _required_str(config, "source_table")
    reference_table = _required_str(config, "reference_table")
    _require_delete_orphans_action(config)
    primary_keys = _required_primary_keys(config)
    source_key, reference_key, source_keys, reference_keys = _resolve_reference_keys(
        config
    )
    return ForeignKeyReconciliationRequest(
        source_table=source_table,
        reference_table=reference_table,
        source_key=source_key,
        reference_key=reference_key,
        primary_keys=primary_keys,
        action="delete_orphans",
        source_layer=_optional_layer(config, "source_layer", default="silver"),
        reference_layer=_optional_layer(config, "reference_layer", default="silver"),
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
    )


def _optional_runtime_str(
    runtime_context: WorkflowTransformRuntimeContext | None,
    attribute_name: str,
) -> str | None:
    if runtime_context is None:
        return None
    value = getattr(runtime_context, attribute_name, None)
    return None if value is None else str(value)


async def _persist_reconcile_result_artifact(
    runtime_context: WorkflowTransformRuntimeContext | None,
    *,
    spec: WorkflowTransformSpec,
    payload: Mapping[str, object],
) -> tuple[dict[str, object], ...]:
    if runtime_context is None:
        return ()
    sink = getattr(runtime_context, "artifact_sink", None)
    if sink is None:
        return ()
    workflow_name = getattr(runtime_context, "workflow_name", None)
    workflow_run_id = getattr(runtime_context, "workflow_run_id", None)
    manifest_id = getattr(runtime_context, "manifest_id", None)
    if workflow_name is None or workflow_run_id is None or manifest_id is None:
        logger = getattr(runtime_context, "logger", None)
        if logger is not None:
            logger.debug(
                "Skipping reconcile_foreign_keys artifact persistence: missing identifiers",
                workflow_name=workflow_name,
                workflow_run_id=workflow_run_id,
                manifest_id=manifest_id,
                step_id=spec.step_id,
            )
        return ()
    writer = getattr(sink, "write_reconcile_result_artifact", None)
    if not callable(writer):
        return ()
    refs = await asyncio.to_thread(
        writer,
        context=WorkflowTransformArtifactContext(
            workflow_name=str(workflow_name),
            workflow_run_id=str(workflow_run_id),
            manifest_id=str(manifest_id),
            step_id=spec.step_id,
            transform_name=spec.transform_name,
            debug_export_enabled=bool(
                getattr(runtime_context, "debug_export_enabled", False)
            ),
            debug_export_dir=_optional_runtime_str(
                runtime_context,
                "debug_export_dir",
            ),
            created_at=getattr(runtime_context, "created_at", None),
        ),
        payload=payload,
    )
    return artifact_refs_as_dicts(tuple(refs))


def _require_delete_orphans_action(config: Mapping[str, object]) -> None:
    action = _required_str(config, "action")
    if action != "delete_orphans":
        raise ValueError("reconcile_foreign_keys supports only action=delete_orphans")


def _required_primary_keys(config: Mapping[str, object]) -> tuple[str, ...]:
    from collections.abc import Sequence

    raw_primary_keys = config.get("primary_keys")
    if (
        not isinstance(raw_primary_keys, Sequence)
        or isinstance(raw_primary_keys, (str, bytes, bytearray))
        or not raw_primary_keys
    ):
        raise ValueError(
            "reconcile_foreign_keys requires config.primary_keys as a non-empty list"
        )
    primary_keys = tuple(
        str(item).strip() for item in raw_primary_keys if str(item).strip()
    )
    if not primary_keys:
        raise ValueError(
            "reconcile_foreign_keys requires at least one non-empty primary key"
        )
    return primary_keys


def _resolve_reference_keys(
    config: Mapping[str, object],
) -> tuple[str, str, tuple[str, ...] | None, tuple[str, ...] | None]:
    source_keys = _optional_key_tuple(config, "source_keys")
    reference_keys = _optional_key_tuple(config, "reference_keys")
    if source_keys is None and reference_keys is None:
        return (
            _required_str(config, "source_key"),
            _required_str(config, "reference_key"),
            None,
            None,
        )
    if source_keys is None or reference_keys is None:
        raise ValueError(
            "reconcile_foreign_keys requires source_keys and reference_keys together"
        )
    if len(source_keys) != len(reference_keys):
        raise ValueError(
            "reconcile_foreign_keys requires source_keys and reference_keys "
            "to have the same length"
        )
    return source_keys[0], reference_keys[0], source_keys, reference_keys


def _required_str(config: Mapping[str, object], key: str) -> str:
    value = config.get(key)
    if value is None or not str(value).strip():
        raise ValueError(f"reconcile_foreign_keys requires config.{key}")
    return str(value).strip()


def _optional_layer(
    config: Mapping[str, object],
    key: str,
    *,
    default: str | None,
) -> str | None:
    value = config.get(key, default)
    if value is None:
        return None
    rendered = str(value).strip().lower()
    if rendered not in {"silver", "gold"}:
        raise ValueError(
            f"reconcile_foreign_keys requires config.{key} as 'silver' or 'gold'"
        )
    return rendered


def _optional_key_tuple(
    config: Mapping[str, object],
    key: str,
) -> tuple[str, ...] | None:
    from collections.abc import Sequence

    value = config.get(key)
    if value is None:
        return None
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or not value
    ):
        raise ValueError(
            f"reconcile_foreign_keys requires config.{key} as a non-empty list"
        )
    keys = tuple(str(item).strip() for item in value if str(item).strip())
    if not keys:
        raise ValueError(
            f"reconcile_foreign_keys requires at least one non-empty entry in "
            f"config.{key}"
        )
    return keys
