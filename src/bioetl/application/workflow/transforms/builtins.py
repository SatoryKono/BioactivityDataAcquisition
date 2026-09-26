"""Built-in workflow transforms shipped with the baseline workflow runner."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.application.workflow.transforms import WorkflowTransformRegistry
from bioetl.application.workflow.transforms.reconcile_foreign_keys import (
    build_reconcile_foreign_keys_executor,
)
from bioetl.application.workflow.transforms.reconcile_rows import (
    build_reconcile_rows_executor,
)
from bioetl.domain.ports import ForeignKeyReconciliationPort, RowReconciliationPort
from bioetl.domain.workflow import WorkflowTransformSpec

__all__ = ["register_builtin_workflow_transforms"]


def register_builtin_workflow_transforms(
    registry: WorkflowTransformRegistry,
    *,
    foreign_key_reconciliation_port: ForeignKeyReconciliationPort | None = None,
    row_reconciliation_port: RowReconciliationPort | None = None,
) -> WorkflowTransformRegistry:
    """Register baseline built-in transforms on the provided registry."""
    registry.register("summarize_upstream_outputs", _summarize_upstream_outputs)
    if foreign_key_reconciliation_port is not None:
        registry.register(
            "reconcile_foreign_keys",
            build_reconcile_foreign_keys_executor(foreign_key_reconciliation_port),
        )
    if row_reconciliation_port is not None:
        registry.register(
            "reconcile_rows",
            build_reconcile_rows_executor(row_reconciliation_port),
        )
    return registry


def _summarize_upstream_outputs(
    spec: WorkflowTransformSpec,
    upstream_outputs: Mapping[str, object],
) -> dict[str, object]:
    """Emit a deterministic summary of upstream workflow step outputs.

    The baseline workflow example needs one transform step that is:
    - local-only;
    - deterministic;
    - safe for dry-run smoke tests;
    - representative enough to exercise transform-step orchestration.
    """

    upstream_steps = sorted(upstream_outputs)
    step_summaries = {
        step_id: {
            "payload_type": type(payload).__name__,
            "status": getattr(payload, "status", None),
        }
        for step_id, payload in sorted(upstream_outputs.items())
    }
    return {
        "transform_name": spec.transform_name,
        "fingerprint": spec.fingerprint,
        "upstream_steps": upstream_steps,
        "step_summaries": step_summaries,
    }
