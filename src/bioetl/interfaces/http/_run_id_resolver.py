"""Unique run UUID resolution for sources that cannot embed one.

Dashboard variables and row links that already carry a catalog UUID stay on
that UUID. This helper is only for Prometheus, alert and action-scope rows
that have workflow / pipeline / run_type and no run id.

A compact clock stamp is not a run id. An explicit token is never replaced
by another catalog row. More than one match is ambiguous and is not reduced
to the newest run.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import SimpleNamespace
from typing import cast
from uuid import UUID

from bioetl.domain.control_plane.manifest_selection import current_run_manifests
from bioetl.domain.control_plane.run_manifest import RunManifest
from bioetl.interfaces.http._selected_run_a2_resolve import _declared_workflows

_ALL_SCOPE = frozenset({"", "All", "all", ".*", "$__all", "__all", "*", "—"})


@dataclass(frozen=True, slots=True)
class UniqueScopeResolution:
    """One non-guessing scope resolution."""

    status: str
    run_id: str | None
    manifest: object | None
    reason: str


def concrete_scope_values(values: Sequence[str]) -> tuple[str, ...]:
    """Drop Grafana All tokens so they do not filter as literal names."""
    return tuple(value.strip() for value in values if value.strip() not in _ALL_SCOPE)


def is_catalog_uuid(token: str) -> bool:
    """True when ``token`` is a UUID string, not a clock stamp or label."""
    try:
        UUID(token)
    except ValueError:
        return False
    return True


def resolve_unique_scope(
    manifests: Sequence[object],
    *,
    pipelines: Sequence[str] = (),
    run_types: Sequence[str] = (),
    workflows: Sequence[str] = (),
) -> UniqueScopeResolution:
    """Return the only in-scope run, or refuse to choose.

    ``status`` is ``resolved``, ``not_found`` or ``ambiguous``. ``run_id`` is
    set only for ``resolved``.
    """
    pipeline_filter = concrete_scope_values(pipelines)
    run_type_filter = concrete_scope_values(run_types)
    workflow_filter = concrete_scope_values(workflows)
    matched: dict[str, list[object]] = {}
    for manifest in _current_catalog(manifests):
        if not _manifest_in_scope(
            manifest,
            pipelines=pipeline_filter,
            run_types=run_type_filter,
            workflows=workflow_filter,
        ):
            continue
        run_id = str(getattr(manifest, "run_id", "") or "")
        if not run_id or not is_catalog_uuid(run_id):
            continue
        matched.setdefault(run_id, []).append(manifest)
    if len(matched) == 1:
        run_id, rows = next(iter(matched.items()))
        if len(rows) == 1:
            return UniqueScopeResolution(
                status="resolved",
                run_id=run_id,
                manifest=rows[0],
                reason="unique_scope",
            )
        return UniqueScopeResolution(
            status="ambiguous",
            run_id=None,
            manifest=None,
            reason="ambiguous_scope",
        )
    if not matched:
        return UniqueScopeResolution(
            status="not_found",
            run_id=None,
            manifest=None,
            reason="unique_scope_not_found",
        )
    return UniqueScopeResolution(
        status="ambiguous",
        run_id=None,
        manifest=None,
        reason="ambiguous_scope",
    )


def _manifest_in_scope(
    manifest: object,
    *,
    pipelines: tuple[str, ...],
    run_types: tuple[str, ...],
    workflows: tuple[str, ...],
) -> bool:
    pipeline = str(getattr(manifest, "pipeline_name", "") or "")
    if pipelines and pipeline not in pipelines:
        return False
    if run_types and _run_type_token(manifest) not in run_types:
        return False
    if not workflows:
        return True
    return bool(set(_workflow_names(manifest)).intersection(workflows))


def _current_catalog(manifests: Sequence[object]) -> tuple[object, ...]:
    """Drop predecessor manifests before a run is counted.

    ``list_all`` keeps both the predecessor and the successor for one run id.
    ``current_run_manifests`` keeps the chain tip, which is the manifest
    ``get_by_run_id`` indexes. Two current manifests for one run id are left
    intact so the caller can refuse to choose.
    """
    typed = tuple(item for item in manifests if isinstance(item, RunManifest))
    if typed and len(typed) == len(manifests):
        return current_run_manifests(typed)
    return tuple(manifests)


def _workflow_names(manifest: object) -> tuple[str, ...]:
    """Workflows recorded on the run, including nested config payloads.

    ``_declared_workflows`` is the existing catalog semantics. A top-level
    ``workflow_name`` and the same name under launch, runtime or resolved
    config are both matches. Neither is preferred.
    """
    if isinstance(manifest, RunManifest):
        return _declared_workflows(manifest)
    workflow_name = getattr(manifest, "workflow_name", None)
    view = SimpleNamespace(
        workflow_name=workflow_name if isinstance(workflow_name, str) else None,
        launch_context=_config_mapping(getattr(manifest, "launch_context", None)),
        runtime_config=_config_mapping(getattr(manifest, "runtime_config", None)),
        resolved_config=_config_mapping(getattr(manifest, "resolved_config", None)),
    )
    return _declared_workflows(cast(RunManifest, view))


def _config_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): item for key, item in value.items()}


def _run_type_token(manifest: object) -> str:
    run_type = getattr(manifest, "run_type", "")
    value = getattr(run_type, "value", run_type)
    return str(value)
