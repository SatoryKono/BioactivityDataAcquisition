"""Unique run UUID resolution for sources that cannot embed one.

Dashboard variables and row links that already carry a catalog UUID stay on
that UUID. This helper is only for Prometheus, alert and action-scope rows
that have workflow / pipeline / run_type and no run id.

A compact clock stamp is not a run id. An explicit token is never replaced
by another catalog row. More than one match is ambiguous and is not reduced
to the newest run.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

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
    matched: dict[str, object] = {}
    for manifest in manifests:
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
        matched.setdefault(run_id, manifest)
    if len(matched) == 1:
        run_id, manifest = next(iter(matched.items()))
        return UniqueScopeResolution(
            status="resolved",
            run_id=run_id,
            manifest=manifest,
            reason="unique_scope",
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
    if workflows:
        workflow = getattr(manifest, "workflow_name", None)
        if not isinstance(workflow, str) or workflow not in workflows:
            return False
    return True


def _run_type_token(manifest: object) -> str:
    run_type = getattr(manifest, "run_type", "")
    value = getattr(run_type, "value", run_type)
    return str(value)
