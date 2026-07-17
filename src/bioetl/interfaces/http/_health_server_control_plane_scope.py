"""Control-plane selector scope helpers for health-server routing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.types import RunID, RunType
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


class _RunManifestLookupPort(Protocol):
    def get_by_run_id(self, run_id: RunID) -> RunManifest | None: ...

    def get_latest_for_scope(
        self,
        pipeline_name: str,
        run_types: tuple[RunType, ...] = (),
    ) -> RunManifest | None: ...


class _ControlPlaneScopeHost(Protocol):
    @property
    def _run_manifest_port(self) -> _RunManifestLookupPort | None: ...

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

    if len(selected_pipelines) != 1:
        return _IdentityScope(
            requested_pipeline=requested_pipeline,
            selected_pipelines=selected_pipelines,
            selected_run_types=selected_run_types,
            selected_run_id=selected_run_id,
            resolved_manifest=None,
            resolved_via="aggregate_scope_requires_exact_run_id",
        )

    try:
        run_types = tuple(RunType(value) for value in selected_run_types)
    except ValueError:
        run_types = ()
        invalid_run_type_scope = True
    else:
        invalid_run_type_scope = False
    resolved_manifest = (
        None
        if invalid_run_type_scope
        else host._run_manifest_port.get_latest_for_scope(
            selected_pipelines[0],
            run_types,
        )
    )
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
    manifest_port: _RunManifestLookupPort,
    selected_run_id: str,
) -> RunManifest | None:
    try:
        run_id = RunID(UUID(selected_run_id))
    except ValueError:
        return None
    return manifest_port.get_by_run_id(run_id)


def _is_unknown_pipeline_scope(
    *,
    requested_pipeline: str,
    selected_pipelines: tuple[str, ...],
) -> bool:
    return requested_pipeline.strip() == UNKNOWN_SCOPE and selected_pipelines in {
        (UNKNOWN_SCOPE,),
        (),
    }
