"""Built-in workflow transform for foreign-key reconciliation."""

from __future__ import annotations

from collections.abc import Mapping

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
        request = _build_request(spec)
        result = await reconciliation_port.reconcile_foreign_keys(request)
        payload = {
            "transform_name": spec.transform_name,
            "fingerprint": spec.fingerprint,
            "source_table": result.source_table,
            "reference_table": result.reference_table,
            "source_key": result.source_key,
            "reference_key": result.reference_key,
            "action": result.action,
            "scanned_rows": result.scanned_rows,
            "retained_rows": result.retained_rows,
            "orphan_rows_deleted": result.orphan_rows_deleted,
            "mutated": result.mutated,
        }
        if result.mutated and runtime_context is not None:
            runtime_context.record_destructive_commit(
                step_id=spec.step_id,
                transform_name=spec.transform_name,
                fingerprint=spec.fingerprint,
                details=payload,
            )
        return payload

    return _executor


def _build_request(spec: WorkflowTransformSpec) -> ForeignKeyReconciliationRequest:
    config = spec.config or {}
    source_table = _required_str(config, "source_table")
    reference_table = _required_str(config, "reference_table")
    source_key = _required_str(config, "source_key")
    reference_key = _required_str(config, "reference_key")
    action = _required_str(config, "action")
    if action != "delete_orphans":
        raise ValueError("reconcile_foreign_keys supports only action=delete_orphans")
    raw_primary_keys = config.get("primary_keys")
    if not isinstance(raw_primary_keys, list) or not raw_primary_keys:
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
    return ForeignKeyReconciliationRequest(
        source_table=source_table,
        reference_table=reference_table,
        source_key=source_key,
        reference_key=reference_key,
        primary_keys=primary_keys,
        action="delete_orphans",
    )


def _required_str(config: Mapping[str, object], key: str) -> str:
    value = config.get(key)
    if value is None or not str(value).strip():
        raise ValueError(f"reconcile_foreign_keys requires config.{key}")
    return str(value).strip()
