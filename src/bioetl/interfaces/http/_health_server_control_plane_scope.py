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


class _RunManifestLookupPort(Protocol):
    def get_by_run_id(self, run_id: RunID) -> RunManifest | None: ...


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


def _identity_scope(
    *,
    requested_pipeline: str,
    selected_pipelines: tuple[str, ...],
    selected_run_types: tuple[str, ...],
    selected_run_id: str | None,
    resolved_manifest: RunManifest | None,
    resolved_via: str,
) -> _IdentityScope:
    return _IdentityScope(
        requested_pipeline=requested_pipeline,
        selected_pipelines=selected_pipelines,
        selected_run_types=selected_run_types,
        selected_run_id=selected_run_id,
        resolved_manifest=resolved_manifest,
        resolved_via=resolved_via,
    )


def resolve_control_plane_identity_scope(
    host: _ControlPlaneScopeHost,
    query: dict[str, str],
) -> _IdentityScope:
    if host._run_manifest_port is None:
        raise RuntimeError(
            "run_manifest_port is required for control-plane identity scope resolution"
        )
    requested_pipeline = host._read_required_param(query, "pipeline")
    selected_pipelines = host._read_scope_csv_param(query, "pipeline")
    selected_run_types = host._read_scope_csv_param(query, "run_type")
    selected_run_id = read_selected_run_id(host, query)

    if selected_run_id is None and _is_unknown_pipeline_scope(
        requested_pipeline=requested_pipeline,
        selected_pipelines=selected_pipelines,
    ):
        return _identity_scope(
            requested_pipeline=requested_pipeline,
            selected_pipelines=selected_pipelines,
            selected_run_types=selected_run_types,
            selected_run_id=None,
            resolved_manifest=None,
            resolved_via="no_manifest_for_scope",
        )

    if selected_run_id is None and len(selected_pipelines) != 1:
        return _identity_scope(
            requested_pipeline=requested_pipeline,
            selected_pipelines=selected_pipelines,
            selected_run_types=selected_run_types,
            selected_run_id=None,
            resolved_manifest=None,
            resolved_via="aggregate_scope_requires_exact_run_id",
        )

    if selected_run_id is not None:
        resolved_manifest = _get_manifest_by_selected_run_id(
            host._run_manifest_port,
            selected_run_id,
        )
        if resolved_manifest is not None:
            return _identity_scope(
                requested_pipeline=requested_pipeline,
                selected_pipelines=selected_pipelines,
                selected_run_types=selected_run_types,
                selected_run_id=selected_run_id,
                resolved_manifest=resolved_manifest,
                resolved_via="selected_run_id",
            )
        # Explicit unresolved scope when a concrete run_id was selected but no
        # matching manifest exists (do not silently fall through to latest).
        return _identity_scope(
            requested_pipeline=requested_pipeline,
            selected_pipelines=selected_pipelines,
            selected_run_types=selected_run_types,
            selected_run_id=selected_run_id,
            resolved_manifest=None,
            resolved_via="selected_run_id_not_found",
        )

    # Grafana identity panels must not resolve "latest run" when Run ID is
    # unset / "-". That bleed looks like a selected run (#8758).
    return _identity_scope(
        requested_pipeline=requested_pipeline,
        selected_pipelines=selected_pipelines,
        selected_run_types=selected_run_types,
        selected_run_id=None,
        resolved_manifest=None,
        resolved_via="selection_required",
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
