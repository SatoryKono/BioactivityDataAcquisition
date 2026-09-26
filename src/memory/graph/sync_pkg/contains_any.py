"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Callable

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_secret_requirements import _add_workflow_outputs
from memory.graph.sync_pkg.default_batch_size import (
    GATE_CONFIG_VALIDATION,
    GATE_DOCS_VERIFICATION,
    GATE_MYPY_STRICT,
    GATE_NEO4J_ONTOLOGY_INVARIANTS,
)
from memory.graph.sync_pkg.graph_contexts import WorkflowContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.workflow_environment_mapping_name import (
    _workflow_matrix_axes,
    _workflow_matrix_variants,
)
from memory.graph.sync_pkg.workflow_family_rules import (
    _WORKFLOW_FAMILY_RULES,
    _workflow_environment_name,
    _workflow_on_payload,
    _workflow_trigger_names,
)
from memory.graph.sync_pkg.workflow_matrix_axis_values import _workflow_secret_refs
from memory.graph.sync_pkg.workflow_output_expression import (
    _job_step_counts,
    _workflow_concurrency_group,
)

__all__ = [
    "_WORKFLOW_GATE_RULES",
    "_add_workflow_call_entrypoint",
    "_contains_any",
    "_enrich_workflow_surface",
    "_workflow_family",
    "_workflow_job_surface_metadata",
]


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


_WORKFLOW_GATE_RULES: tuple[tuple[Callable[[str], bool], str], ...] = (
    (lambda text: "pytest" in text, "pytest"),
    (lambda text: "mypy" in text, GATE_MYPY_STRICT),
    (
        lambda text: _contains_any(
            text, ("scripts.docs", "check-links", "build_docs_site.sh")
        ),
        GATE_DOCS_VERIFICATION,
    ),
    (
        lambda text: _contains_any(
            text,
            ("validate_pipeline_configs", "scripts.schema", "check_config_invariants"),
        ),
        GATE_CONFIG_VALIDATION,
    ),
    (lambda text: "neo4j-memory" in text, GATE_NEO4J_ONTOLOGY_INVARIANTS),
)


def _workflow_family(workflow_name: str, title: str) -> str:
    lowered = f"{workflow_name} {title}".lower()
    for family_name, needles in _WORKFLOW_FAMILY_RULES:
        if _contains_any(lowered, needles):
            return family_name
    return "test"


def _enrich_workflow_surface(
    snapshot: GraphSnapshot,
    context: WorkflowContext,
    payload: dict[str, object],
) -> None:
    snapshot.add_node(
        "workflow_surface",
        context.workflow_name,
        workflow_family=_workflow_family(context.workflow_name, context.title),
        trigger_names=list(_workflow_trigger_names(payload)) or None,
        concurrency_group=_workflow_concurrency_group(payload),
    )


def _add_workflow_call_entrypoint(
    snapshot: GraphSnapshot,
    context: WorkflowContext,
    payload: dict[str, object],
) -> NodeKey | None:
    workflow_call_payload = _workflow_on_payload(payload)
    if not isinstance(workflow_call_payload, dict):
        return None
    reusable_workflow_payload = workflow_call_payload.get("workflow_call")
    if not isinstance(reusable_workflow_payload, dict):
        return None
    workflow_call_entrypoint = snapshot.add_node(
        "workflow_call_surface",
        f"{context.workflow_name}::workflow_call",
        summary=f"Reusable workflow entrypoint for `{context.workflow_name}`.",
        source_path=context.relative_path,
        source_kind="workflow_call_surface",
        workflow=context.workflow_name,
        reusable_kind="workflow_call_trigger",
        last_verified=context.today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(
        context.workflow,
        "CALLS_WORKFLOW",
        workflow_call_entrypoint,
        provenance="workflow_graph",
    )
    snapshot.add_relation(
        workflow_call_entrypoint,
        "DEPENDS_ON",
        context.workflow,
        provenance="workflow_graph",
    )
    _add_workflow_outputs(
        snapshot,
        owner=context.workflow,
        workflow_name=context.workflow_name,
        relative_path=context.relative_path,
        today=context.today,
        owner_id=context.workflow_name,
        output_payload=reusable_workflow_payload.get("outputs"),
        scope="workflow_call_output",
        output_scope="workflow_call",
        summary_template="Reusable workflow output `{output_name}`.",
    )
    return workflow_call_entrypoint


def _workflow_job_surface_metadata(
    job_payload: dict[str, object],
) -> tuple[
    int,
    int,
    tuple[str, ...],
    tuple[dict[str, str], ...],
    str | None,
    str | None,
    tuple[str, ...],
]:
    steps = job_payload.get("steps")
    inline_run_step_count, uses_step_count = _job_step_counts(steps)
    secret_usage_hints = _workflow_secret_refs(job_payload)
    matrix_axes = _workflow_matrix_axes(job_payload)
    matrix_variants = _workflow_matrix_variants(job_payload)
    environment_name = _workflow_environment_name(job_payload)
    concurrency_group = _workflow_concurrency_group(job_payload)
    return (
        inline_run_step_count,
        uses_step_count,
        matrix_axes,
        matrix_variants,
        environment_name,
        concurrency_group,
        secret_usage_hints,
    )
