"""Control-plane selector scope helpers for health-server routing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.types import RunID
from bioetl.interfaces.http.control_plane_selector_context import (
    RUN_ID_NO_SELECTION,
    UNKNOWN_SCOPE,
)


@dataclass(frozen=True, slots=True)
class _IdentityScope:
    requested_pipeline: str
    selected_pipelines: tuple[str, ...]
    selected_run_types: tuple[str, ...]
    selected_run_id: str | None
    resolved_manifest: RunManifest | None
    resolved_via: str


class _ControlPlaneScopeHost(Protocol):
    _run_manifest_port: object | None

    def _read_required_param(self, query: dict[str, str], name: str) -> str: ...

    @staticmethod
    def _read_optional_param(query: dict[str, str], name: str) -> str | None: ...

    @classmethod
    def _read_scope_csv_param(
        cls,
        query: dict[str, str],
        name: str,
    ) -> tuple[str, ...]: ...


def read_selected_run_id(
    host: _ControlPlaneScopeHost,
    query: dict[str, str],
) -> str | None:
    selected_run_id = host._read_optional_param(query, "run_id")
    return None if selected_run_id in {None, RUN_ID_NO_SELECTION} else selected_run_id


def resolve_control_plane_identity_scope(
    host: _ControlPlaneScopeHost,
    query: dict[str, str],
) -> _IdentityScope:
    assert host._run_manifest_port is not None
    requested_pipeline = host._read_required_param(query, "pipeline")
    selected_pipelines = host._read_scope_csv_param(query, "pipeline")
    selected_run_types = host._read_scope_csv_param(query, "run_type")
    selected_run_id = read_selected_run_id(host, query)

    if selected_run_id is None and _is_unknown_pipeline_scope(
        requested_pipeline=requested_pipeline,
        selected_pipelines=selected_pipelines,
    ):
        return _IdentityScope(
            requested_pipeline=requested_pipeline,
            selected_pipelines=selected_pipelines,
            selected_run_types=selected_run_types,
            selected_run_id=None,
            resolved_manifest=None,
            resolved_via="no_manifest_for_scope",
        )

    if selected_run_id is not None:
        resolved_manifest = _get_manifest_by_selected_run_id(
            host._run_manifest_port,
            selected_run_id,
        )
        if resolved_manifest is not None:
            return _IdentityScope(
                requested_pipeline=requested_pipeline,
                selected_pipelines=selected_pipelines,
                selected_run_types=selected_run_types,
                selected_run_id=selected_run_id,
                resolved_manifest=resolved_manifest,
                resolved_via="selected_run_id",
            )

    manifests = tuple(
        manifest
        for manifest in host._run_manifest_port.list_all()
        if (not selected_pipelines or manifest.pipeline_name in selected_pipelines)
        and (not selected_run_types or str(manifest.run_type) in selected_run_types)
    )
    resolved_manifest = next(
        (
            manifest
            for manifest in manifests
            if selected_run_id is not None and str(manifest.run_id) == selected_run_id
        ),
        None,
    )
    resolved_via = "selected_run_id"
    if resolved_manifest is None:
        if len(selected_pipelines) != 1:
            resolved_via = "aggregate_scope_requires_exact_run_id"
        else:
            resolved_manifest = manifests[-1] if manifests else None
            resolved_via = (
                "latest_manifest_for_scope"
                if resolved_manifest is not None
                else "no_manifest_for_scope"
            )
    return _IdentityScope(
        requested_pipeline=requested_pipeline,
        selected_pipelines=selected_pipelines,
        selected_run_types=selected_run_types,
        selected_run_id=selected_run_id,
        resolved_manifest=resolved_manifest,
        resolved_via=resolved_via,
    )


def _get_manifest_by_selected_run_id(
    manifest_port: object,
    selected_run_id: str,
) -> RunManifest | None:
    get_by_run_id = getattr(manifest_port, "get_by_run_id", None)
    if not callable(get_by_run_id):
        return None
    try:
        run_id = RunID(UUID(selected_run_id))
    except ValueError:
        return None
    return get_by_run_id(run_id)


def _is_unknown_pipeline_scope(
    *,
    requested_pipeline: str,
    selected_pipelines: tuple[str, ...],
) -> bool:
    return requested_pipeline.strip() == UNKNOWN_SCOPE and selected_pipelines in {
        (UNKNOWN_SCOPE,),
        (),
    }
