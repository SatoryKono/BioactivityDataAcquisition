"""Built-in workflow transform for deterministic A/B row reconciliation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from bioetl.application.workflow.transforms import WorkflowTransformRuntimeContext
from bioetl.domain.ports import (
    RowReconciliationConfig,
    RowReconciliationPort,
    RowReconciliationResult,
)
from bioetl.domain.workflow import WorkflowTransformSpec

__all__ = ["build_reconcile_rows_executor"]


def build_reconcile_rows_executor(reconciliation_port: RowReconciliationPort):
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
        return _build_report_payload(spec, result)

    return _executor


def _build_config(
    spec: WorkflowTransformSpec,
    *,
    workflow_name: str | None = None,
) -> RowReconciliationConfig:
    config = spec.config or {}
    return RowReconciliationConfig(
        layer=_required_str(config, "layer"),
        left_table=_required_str(config, "left_table"),
        right_table=_required_str(config, "right_table"),
        left_columns=_required_str_tuple(config, "left_columns"),
        right_columns=_required_str_tuple(config, "right_columns"),
        left_primary_keys=_required_str_tuple(config, "left_primary_keys"),
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
    names = tuple(str(item).strip() for item in value if str(item).strip())
    if not names:
        raise ValueError(f"reconcile_rows requires config.{key} as a non-empty list")
    return names
