"""Private support helpers for the reconcile_foreign_keys transform.

Keeps the facade module within the application-layer size budget while
preserving exact payload, artifact, and evidence semantics.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any, cast

from bioetl.application.services.workflow.workflow_transform_artifacts import (
    WorkflowTransformArtifactContext,
    artifact_refs_as_dicts,
)
from bioetl.application.workflow.transforms import WorkflowTransformRuntimeContext
from bioetl.domain.ports import (
    ForeignKeyReconciliationLayer,
    ForeignKeyReconciliationRequest,
)
from bioetl.domain.workflow import WorkflowTransformSpec


def _optional_runtime_str(
    runtime_context: WorkflowTransformRuntimeContext | None,
    attribute_name: str,
) -> str | None:
    if runtime_context is None:
        return None
    value = getattr(runtime_context, attribute_name, None)
    return None if value is None else str(value)


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
    return artifact_refs_as_dicts(tuple(refs))  # pyright: ignore[reportArgumentType]


def _source_scope(config: Mapping[str, object]) -> str:
    raw = config.get("source_scope", "all_current")
    if raw in {"all_current", "current_run"}:
        return str(raw)
    raise ValueError(
        "reconcile_foreign_keys source_scope must be all_current or current_run"
    )


def _payload_run_ids(payload: object) -> tuple[object, ...]:
    payload = getattr(payload, "output", payload)
    if isinstance(payload, Mapping):
        inherited = payload.get("source_run_ids", ())
        refs = tuple(inherited) if isinstance(inherited, (tuple, list)) else ()
        return (*refs, payload.get("run_id"))
    return (getattr(payload, "run_id", None),)


def _evidence_field_text(value: object, *, default: str | None) -> str | None:
    """Return stripped evidence text (``default`` for missing fields).

    Whitespace-only values strip to ``""`` exactly like the inline version
    this helper replaces; callers apply their own empty fallback.
    """
    if value in (None, ""):
        return default
    return str(value).strip()


def _resolve_reference_completeness(
    config: Mapping[str, object],
    upstream_outputs: Mapping[str, object],
    *,
    reference_table: str,
) -> tuple[str, str | None, str | None, str | None]:
    """Return completeness only from typed evidence bound to the reference table."""
    evidence = config.get("reference_completeness_evidence")
    if not isinstance(evidence, Mapping):
        evidence = _upstream_completeness_evidence(upstream_outputs, reference_table)
    if not isinstance(evidence, Mapping):
        return "unproven", None, None, None
    status = str(evidence.get("status") or "unproven").strip().lower()
    identity = (
        _evidence_field_text(
            evidence.get("reference_identity"), default=reference_table
        )
        or None
    )
    snapshot_version = _evidence_field_text(
        evidence.get("snapshot_version"), default=None
    )
    evidence_ref = _evidence_field_text(evidence.get("evidence_ref"), default=None)
    if status != "complete" or identity != reference_table or not evidence_ref:
        return "unproven", identity, snapshot_version, evidence_ref
    return "complete", identity, snapshot_version, evidence_ref


def _upstream_completeness_evidence(
    upstream_outputs: Mapping[str, object],
    reference_table: str,
) -> Mapping[str, object] | None:
    for payload in upstream_outputs.values():
        mapping = getattr(payload, "output", payload)
        if not isinstance(mapping, Mapping):
            continue
        evidence = mapping.get("reference_completeness_evidence")
        if not isinstance(evidence, Mapping):
            continue
        identity = str(evidence.get("reference_identity") or "").strip()
        if identity in {"", reference_table}:
            return evidence
    return None


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
    primary_keys = tuple(str(item).strip() for item in raw_primary_keys)
    if any(not key for key in primary_keys):
        raise ValueError(
            "reconcile_foreign_keys primary_keys cannot contain blank entries"
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
    keys = tuple(str(item).strip() for item in value)
    if any(not item for item in keys):
        raise ValueError(f"reconcile_foreign_keys {key} cannot contain blank entries")
    return keys


def _optional_layer(
    config: Mapping[str, object],
    key: str,
    *,
    default: ForeignKeyReconciliationLayer | None,
) -> ForeignKeyReconciliationLayer | None:
    value = config.get(key, default)
    if value is None:
        return None
    rendered = str(value).strip().lower()
    if rendered not in {"silver", "gold"}:
        raise ValueError(
            f"reconcile_foreign_keys requires config.{key} as 'silver' or 'gold'"
        )
    return cast("ForeignKeyReconciliationLayer", rendered)
