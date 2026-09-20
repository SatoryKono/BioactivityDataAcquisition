"""Config readers and runtime support for the reconcile_foreign_keys transform."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import cast

from bioetl.application.services.workflow.workflow_transform_artifacts import (
    WorkflowTransformArtifactContext,
    artifact_refs_as_dicts,
)
from bioetl.application.workflow.transforms import WorkflowTransformRuntimeContext
from bioetl.domain.ports import (
    ForeignKeyReconciliationLayer,
    ReferenceCompletenessStatus,
)
from bioetl.domain.workflow import WorkflowTransformSpec

__all__ = [
    "_optional_key_tuple",
    "_optional_layer",
    "_optional_runtime_str",
    "_payload_run_ids",
    "_persist_reconcile_result_artifact",
    "_require_delete_orphans_action",
    "_required_primary_keys",
    "_required_str",
    "_resolve_reference_completeness",
    "_resolve_reference_keys",
    "_run_ids_from_upstream",
    "_source_scope",
    "_upstream_completeness_evidence",
]


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


def _clean_evidence_str(value: object, default: str | None) -> str | None:
    """Strip string-like evidence, falling back to default for missing entries."""
    if value in (None, ""):
        return default or None
    return str(value).strip() or None


def _resolve_reference_completeness(
    config: Mapping[str, object],
    upstream_outputs: Mapping[str, object],
    *,
    reference_table: str,
) -> tuple[ReferenceCompletenessStatus, str | None, str | None, str | None]:
    """Return completeness only from typed evidence bound to the reference table."""
    evidence = config.get("reference_completeness_evidence")
    if not isinstance(evidence, Mapping):
        evidence = _upstream_completeness_evidence(upstream_outputs, reference_table)
    if not isinstance(evidence, Mapping):
        return "unproven", None, None, None
    status = str(evidence.get("status") or "unproven").strip().lower()
    identity = _clean_evidence_str(evidence.get("reference_identity"), reference_table)
    snapshot_version = _clean_evidence_str(evidence.get("snapshot_version"), None)
    evidence_ref = _clean_evidence_str(evidence.get("evidence_ref"), None)
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
