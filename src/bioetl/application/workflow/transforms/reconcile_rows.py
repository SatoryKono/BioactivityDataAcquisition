# Boundary object/payload typing residual at this module.
"""Built-in workflow transform for deterministic A/B row reconciliation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from bioetl.application.services.workflow.workflow_transform_artifacts import (
    WorkflowTransformArtifactContext,
    artifact_refs_as_dicts,
)
from bioetl.application.workflow.transforms import (
    WorkflowTransformCallable,
    WorkflowTransformRuntimeContext,
)
from bioetl.domain.ports import (
    RowReconciliationConfig,
    RowReconciliationPort,
    RowReconciliationResult,
)
from bioetl.domain.workflow import WorkflowTransformSpec

__all__ = ["build_reconcile_rows_executor"]


def build_reconcile_rows_executor(
    reconciliation_port: RowReconciliationPort,
) -> WorkflowTransformCallable:
    """Build a storage-backed executor for `reconcile_rows`."""

    async def _executor(
        spec: WorkflowTransformSpec,
        upstream_outputs: Mapping[str, object],
        runtime_context: WorkflowTransformRuntimeContext | None = None,
    ) -> dict[str, object]:
        del upstream_outputs
        workflow_name = (
            getattr(runtime_context, "workflow_name", None)
            if runtime_context is not None
            else None
        )
        config = _build_config(spec, workflow_name=workflow_name)
        result = await reconciliation_port.reconcile_rows(config)
        payload = _build_report_payload(spec, result)
        artifact_refs = await _persist_reconcile_rows_artifact(
            runtime_context,
            spec=spec,
            payload=payload,
        )
        if artifact_refs:
            payload["artifact_refs"] = list(artifact_refs)
        return payload

    return _executor


def _build_config(
    spec: WorkflowTransformSpec,
    *,
    workflow_name: str | None = None,
) -> RowReconciliationConfig:
    config = spec.config or {}
    left_columns = _required_str_tuple(config, "left_columns")
    right_columns = _required_str_tuple(config, "right_columns")
    left_primary_keys = _required_str_tuple(config, "left_primary_keys")
    if len(left_columns) != len(right_columns):
        raise ValueError(
            "reconcile_rows requires left_columns and right_columns "
            "to have matching lengths"
        )
    if len(left_primary_keys) > len(left_columns):
        raise ValueError(
            "reconcile_rows requires left_primary_keys length "
            "to be <= left_columns length"
        )
    return RowReconciliationConfig(
        layer=_required_str(config, "layer"),
        left_table=_required_str(config, "left_table"),
        right_table=_required_str(config, "right_table"),
        left_columns=left_columns,
        right_columns=right_columns,
        left_primary_keys=left_primary_keys,
        nulls_equal=bool(config.get("nulls_equal", False)),
        type_policy=str(config.get("type_policy", "strict")),
        preserve_order=bool(config.get("preserve_order", True)),
        report_only=bool(config.get("report_only", True)),
        workflow_name=workflow_name,
    )


def _build_report_payload(
    spec: WorkflowTransformSpec,
    result: RowReconciliationResult,
) -> dict[str, object]:
    return {
        "transform_name": spec.transform_name,
        "fingerprint": spec.fingerprint,
        "implementation": result.implementation,
        "layer": result.layer.value,
        "left_table": result.left_table,
        "right_table": result.right_table,
        "left_columns": list(result.left_columns),
        "right_columns": list(result.right_columns),
        "left_primary_keys": list(result.left_primary_keys),
        "input_left_rows": result.input_left_rows,
        "input_right_rows": result.input_right_rows,
        "kept_rows": result.kept_rows,
        "excluded_rows": result.excluded_rows,
        "null_key_rows_left": result.null_key_rows_left,
        "null_key_rows_right": result.null_key_rows_right,
        "distinct_right_keys": result.distinct_right_keys,
        "nulls_equal": result.nulls_equal,
        "type_policy": result.type_policy.value,
        "preserve_order": result.preserve_order,
        "report_only": result.report_only,
        "mutated": result.mutated,
    }


def _required_str(config: Mapping[str, object], key: str) -> str:
    value = config.get(key)
    if value is None or not str(value).strip():
        raise ValueError(f"reconcile_rows requires config.{key}")
    return str(value).strip()


def _required_str_tuple(
    config: Mapping[str, object],
    key: str,
) -> tuple[str, ...]:
    value = config.get(key)
    if not isinstance(value, Sequence) or isinstance(
        value,
        str | bytes | bytearray,
    ):
        raise ValueError(f"reconcile_rows requires config.{key} as a non-empty list")
    names: list[str] = []
    for index, item in enumerate(value):
        text = str(item).strip()
        if not text:
            raise ValueError(
                f"reconcile_rows config.{key}[{index}] cannot be empty or whitespace"
            )
        names.append(text)
    if not names:
        raise ValueError(f"reconcile_rows requires config.{key} as a non-empty list")
    return tuple(names)


async def _persist_reconcile_rows_artifact(
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
                "Skipping reconcile_rows artifact persistence: missing identifiers",
                workflow_name=workflow_name,
                workflow_run_id=workflow_run_id,
                manifest_id=manifest_id,
                step_id=spec.step_id,
            )
        return ()
    writer = getattr(sink, "write_reconcile_result_artifact", None)
    if not callable(writer):
        return ()
    import asyncio

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


def _optional_runtime_str(
    runtime_context: WorkflowTransformRuntimeContext | None,
    attribute_name: str,
) -> str | None:
    if runtime_context is None:
        return None
    value = getattr(runtime_context, attribute_name, None)
    return None if value is None else str(value)
