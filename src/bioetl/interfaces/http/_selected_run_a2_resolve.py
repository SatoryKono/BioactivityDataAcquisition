"""A2 run_id resolution for selected-run-status (plan 3.2).

Unresolved selectors (``-`` / All / empty) auto-pick the latest run in the
current pipeline/run_type/workflow scope. An explicit URL ``run_id`` wins and
is never silently replaced by latest. Empty catalog yields ``None`` so the
caller can emit the canonical empty state «НЕТ ЗАПУСКОВ».
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from bioetl.domain.control_plane import RunManifest, WorkflowManifest
from bioetl.interfaces.http._control_plane_selector_filters import (
    filter_records,
    latest_record,
)
from bioetl.interfaces.http._control_plane_selector_payloads import RUN_ID_NO_SELECTION
from bioetl.interfaces.http._control_plane_selector_records import (
    build_selector_records,
    build_workflow_aliases,
    narrow_manifest_catalog,
    selected_pipeline_scope,
)
from bioetl.interfaces.http.run_report_index import _normalize_list_owner

_UNRESOLVED_RUN_IDS = frozenset({"", RUN_ID_NO_SELECTION, "All", "$__all", "__all", "*"})
_ALL_SCOPE_TOKENS = frozenset(
    {"", "All", "all", ".*", "$__all", "__all", "*", "—", "-"}
)

NO_RUNS_STATUS = "НЕТ ЗАПУСКОВ"
NO_RUNS_REASON = "no_runs_in_scope"


class _A2ManifestPort(Protocol):
    def list_all(self) -> tuple[RunManifest, ...]: ...


class _A2WorkflowManifestPort(Protocol):
    def list_all(self) -> tuple[WorkflowManifest, ...]: ...


class _A2LedgerPort(Protocol):
    pass


def is_unresolved_run_id(run_id: str | None) -> bool:
    """True when the client asked for auto-select / no concrete run."""
    if run_id is None:
        return True
    return run_id.strip() in _UNRESOLVED_RUN_IDS


def resolve_a2_latest_run_id(
    *,
    manifests: tuple[RunManifest, ...],
    ledger_port: object | None,
    workflow_manifests: tuple[WorkflowManifest, ...] = (),
    pipeline: str,
    query: Mapping[str, str],
) -> str | None:
    """Return latest concrete run_id for the query scope, or None if empty."""
    selected_workflows = _scope_values(query.get("workflow"))
    selected_run_types = _scope_values(query.get("run_type"))
    selected_run_statuses = _scope_values(query.get("run_status"))
    selected_pipelines = selected_pipeline_scope(
        _scope_values(query.get("pipeline")),
        None if _is_all_pipeline(pipeline) else pipeline,
    )
    workflow_aliases = build_workflow_aliases(workflow_manifests)
    records = build_selector_records(
        narrow_manifest_catalog(
            manifests,
            selected_workflows=selected_workflows,
            selected_pipelines=selected_pipelines,
            selected_run_types=selected_run_types,
            selected_run_id=None,
            workflow_aliases=workflow_aliases,
            fail_open_when_empty=False,
        ),
        ledger_port,
        workflow_aliases=workflow_aliases,
    )
    candidates = filter_records(
        records,
        selected_workflows=selected_workflows,
        selected_pipelines=selected_pipelines,
        selected_run_types=selected_run_types,
        selected_run_statuses=selected_run_statuses,
        selected_run_id=None,
    )
    selected = latest_record(candidates)
    return None if selected is None else selected.run_id


def list_a2_catalog(
    manifest_port: _A2ManifestPort | None,
    workflow_manifest_port: _A2WorkflowManifestPort | None,
) -> tuple[tuple[RunManifest, ...], tuple[WorkflowManifest, ...]]:
    """Read run/workflow manifests for A2 resolution; empty when ports missing."""
    if manifest_port is None:
        return (), ()
    manifests = tuple(manifest_port.list_all())
    if workflow_manifest_port is None:
        return manifests, ()
    return manifests, tuple(workflow_manifest_port.list_all())


def _scope_values(raw: str | None) -> tuple[str, ...]:
    if raw is None or raw.strip() in _ALL_SCOPE_TOKENS:
        return ()
    if _normalize_list_owner(raw) is None:
        return ()
    value = raw.strip()
    if value.startswith("{") and value.endswith("}"):
        value = value[1:-1]
    items: list[str] = []
    for part in value.split(","):
        normalized = part.strip()
        if not normalized or normalized in _ALL_SCOPE_TOKENS:
            continue
        if normalized not in items:
            items.append(normalized)
    return tuple(items)


def _is_all_pipeline(pipeline: str) -> bool:
    return pipeline.strip() in _ALL_SCOPE_TOKENS or _normalize_list_owner(pipeline) is None
