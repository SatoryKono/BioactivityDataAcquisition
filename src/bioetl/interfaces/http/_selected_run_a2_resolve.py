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
from bioetl.interfaces.http._control_plane_selector_filters import filter_records
from bioetl.interfaces.http._control_plane_selector_payloads import RUN_ID_NO_SELECTION
from bioetl.interfaces.http._control_plane_selector_records import (
    SelectorRecord,
    build_selector_records,
    build_workflow_aliases,
    narrow_manifest_catalog,
    selected_pipeline_scope,
)
from bioetl.interfaces.http.run_report_index import _normalize_list_owner

_UNRESOLVED_RUN_IDS = frozenset(
    {"", RUN_ID_NO_SELECTION, "All", "$__all", "__all", "*"}
)
_ALL_SCOPE_TOKENS = frozenset(
    {"", "All", "all", ".*", "$__all", "__all", "*", "—", "-"}
)

NO_RUNS_STATUS = "НЕТ ЗАПУСКОВ"
NO_RUNS_REASON = "no_runs_in_scope"
CATALOG_UNAVAILABLE_REASON = "run_manifest_catalog_unavailable"


class _A2ManifestPort(Protocol):
    def list_all(self) -> tuple[RunManifest, ...]: ...


class _A2WorkflowManifestPort(Protocol):
    def list_all(self) -> tuple[WorkflowManifest, ...]: ...


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
    """Return newest-by-started_at run_id for the query scope, or None if empty.

    Ordering matches filter-options ``run_id`` (started_at desc), not
    selector-context ``latest_record`` (completed_at).

    Workflow filter prefers the run's declared membership
    (launch/runtime/resolved ``workflow`` / ``workflow_name``). Catalog
    aliases are used only as fallback when a run has no declared workflow.
    """
    selected_workflows = _scope_values(query.get("workflow"))
    selected_run_types = _scope_values(query.get("run_type"))
    selected_run_statuses = _scope_values(query.get("run_status"))
    selected_pipelines = selected_pipeline_scope(
        _scope_values(query.get("pipeline")),
        None if _is_all_pipeline(pipeline) else pipeline,
    )
    workflow_aliases = build_workflow_aliases(workflow_manifests)
    # Narrow without workflow aliases so cross-workflow pipeline aliases do not
    # pull foreign runs into the catalog before membership is evaluated.
    records = build_selector_records(
        narrow_manifest_catalog(
            manifests,
            selected_workflows=(),
            selected_pipelines=selected_pipelines,
            selected_run_types=selected_run_types,
            selected_run_id=None,
            workflow_aliases=None,
            fail_open_when_empty=False,
        ),
        ledger_port,
        workflow_aliases=workflow_aliases,
    )
    base = filter_records(
        records,
        selected_workflows=(),
        selected_pipelines=selected_pipelines,
        selected_run_types=selected_run_types,
        selected_run_statuses=selected_run_statuses,
        selected_run_id=None,
    )
    candidates = _apply_workflow_preference(base, selected_workflows)
    selected = _newest_started_record(candidates)
    return None if selected is None else selected.run_id


def _apply_workflow_preference(
    records: tuple[SelectorRecord, ...],
    selected_workflows: tuple[str, ...],
) -> tuple[SelectorRecord, ...]:
    if not selected_workflows:
        return records
    declared_hits: list[SelectorRecord] = []
    alias_fallback: list[SelectorRecord] = []
    selected = set(selected_workflows)
    for record in records:
        declared = _declared_workflows(record.manifest)
        if declared:
            if selected & set(declared):
                declared_hits.append(record)
            continue
        if selected & set(record.workflow_candidates):
            alias_fallback.append(record)
    if declared_hits:
        return tuple(declared_hits)
    return tuple(alias_fallback)


def _declared_workflows(manifest: RunManifest) -> tuple[str, ...]:
    """Workflow names recorded on the run itself (not pipeline-wide aliases)."""
    values: list[str] = []
    for payload in (
        manifest.launch_context,
        manifest.runtime_config,
        manifest.resolved_config,
    ):
        for key in ("workflow_name", "workflow"):
            raw = payload.get(key)
            if isinstance(raw, str):
                text = raw.strip()
                if text and text not in values:
                    values.append(text)
    return tuple(values)


def _newest_started_record(
    records: tuple[SelectorRecord, ...],
) -> SelectorRecord | None:
    """Pick the same head run as filter-options run_id list (started_at desc)."""
    if not records:
        return None
    return max(
        records,
        key=lambda record: (record.started_at, record.manifest_id, record.run_id),
    )


def list_a2_catalog(
    manifest_port: _A2ManifestPort,
    workflow_manifest_port: _A2WorkflowManifestPort | None,
) -> tuple[tuple[RunManifest, ...], tuple[WorkflowManifest, ...]]:
    """Read run/workflow manifests for A2 resolution.

    Callers must ensure ``manifest_port`` is present; a missing port is a
    QUERY ERROR, not an empty catalog.
    """
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
    return (
        pipeline.strip() in _ALL_SCOPE_TOKENS or _normalize_list_owner(pipeline) is None
    )
