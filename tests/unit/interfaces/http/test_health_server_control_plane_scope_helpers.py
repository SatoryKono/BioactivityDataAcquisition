"""Focused coverage for control-plane identity scope resolution helpers."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest

from bioetl.domain.types import RunID, RunType
from bioetl.interfaces.http import _health_server_control_plane_scope as scope


pytestmark = pytest.mark.unit


_RUN_ID = "00000000-0000-0000-0000-000000000123"


class _ManifestPort:
    def __init__(
        self,
        manifests: tuple[object, ...],
        by_run_id: dict[str, object] | None = None,
    ) -> None:
        self._manifests = manifests
        self._by_run_id = by_run_id or {}

    def list_all(self) -> tuple[object, ...]:
        return self._manifests

    def get_by_run_id(self, run_id: RunID) -> object | None:
        return self._by_run_id.get(str(run_id))

    def get_latest_for_scope(
        self,
        pipeline_name: str,
        run_types: tuple[RunType, ...] = (),
    ) -> object | None:
        candidates = tuple(
            manifest
            for manifest in self._manifests
            if manifest.pipeline_name == pipeline_name
            and (not run_types or manifest.run_type in run_types)
        )
        return candidates[-1] if candidates else None


class _Host:
    def __init__(self, manifest_port: _ManifestPort) -> None:
        self._run_manifest_port = manifest_port

    def _read_required_param(self, query: dict[str, str], name: str) -> str:
        value = query.get(name)
        if value is None:
            raise ValueError(name)
        return value

    @staticmethod
    def _read_optional_param(query: dict[str, str], name: str) -> str | None:
        return query.get(name)

    @classmethod
    def _read_scope_csv_param(
        cls,
        query: dict[str, str],
        name: str,
    ) -> tuple[str, ...]:
        value = query.get(name)
        if value in {None, "$__all", "All", "*"}:
            return ()
        return tuple(item.strip() for item in value.split(",") if item.strip())


def _manifest(
    *,
    pipeline_name: str,
    run_id: str,
    run_type: RunType = RunType.INCREMENTAL,
) -> object:
    return SimpleNamespace(
        pipeline_name=pipeline_name,
        run_id=RunID(UUID(run_id)),
        run_type=run_type,
    )


def test_control_plane_scope_resolves_unknown_exact_and_latest_paths() -> None:
    selected = _manifest(pipeline_name="chembl_activity", run_id=_RUN_ID)
    later = _manifest(
        pipeline_name="chembl_activity",
        run_id="00000000-0000-0000-0000-000000000124",
    )
    host = _Host(_ManifestPort((selected, later), by_run_id={_RUN_ID: selected}))

    assert scope.read_selected_run_id(host, {"run_id": "-"}) is None
    assert scope.read_selected_run_id(host, {"run_id": _RUN_ID}) == _RUN_ID
    assert scope._is_unknown_pipeline_scope(
        requested_pipeline="unknown",
        selected_pipelines=(),
    )
    assert scope._is_unknown_pipeline_scope(
        requested_pipeline="unknown",
        selected_pipelines=("unknown",),
    )
    assert not scope._is_unknown_pipeline_scope(
        requested_pipeline="chembl_activity",
        selected_pipelines=("chembl_activity",),
    )

    unknown_scope = scope.resolve_control_plane_identity_scope(
        host,
        {"pipeline": "unknown"},
    )
    assert unknown_scope.resolved_via == "no_manifest_for_scope"
    assert unknown_scope.resolved_manifest is None

    exact_scope = scope.resolve_control_plane_identity_scope(
        host,
        {"pipeline": "chembl_activity", "run_id": _RUN_ID},
    )
    assert exact_scope.resolved_via == "selected_run_id"
    assert exact_scope.resolved_manifest is selected

    latest_scope = scope.resolve_control_plane_identity_scope(
        host,
        {"pipeline": "chembl_activity", "run_id": "not-a-uuid"},
    )
    assert latest_scope.resolved_via == "latest_manifest_for_scope"
    assert latest_scope.resolved_manifest is later
    assert latest_scope.selected_run_id == "not-a-uuid"

    fallback_scope = scope.resolve_control_plane_identity_scope(
        host,
        {"pipeline": "chembl_activity"},
    )
    assert fallback_scope.resolved_via == "latest_manifest_for_scope"
    assert fallback_scope.resolved_manifest is later

    aggregate_scope = scope.resolve_control_plane_identity_scope(
        host,
        {"pipeline": "$__all"},
    )
    assert aggregate_scope.resolved_via == "aggregate_scope_requires_exact_run_id"

    missing_scope = scope.resolve_control_plane_identity_scope(
        host,
        {"pipeline": "missing"},
    )
    assert missing_scope.resolved_via == "no_manifest_for_scope"


def test_control_plane_scope_uses_bounded_latest_lookup() -> None:
    selected = _manifest(pipeline_name="chembl_activity", run_id=_RUN_ID)
    manifest_port = _ManifestPort((selected,), by_run_id={_RUN_ID: selected})
    host = _Host(manifest_port)

    assert scope._ControlPlaneScopeHost._read_required_param(object(), {}, "x") is None
    assert scope._ControlPlaneScopeHost._read_optional_param({}, "x") is None
    assert scope._ControlPlaneScopeHost._read_scope_csv_param({}, "x") is None
    exact_from_catalog = scope.resolve_control_plane_identity_scope(
        host,
        {"pipeline": "chembl_activity", "run_id": _RUN_ID},
    )
    assert exact_from_catalog.resolved_via == "selected_run_id"
    assert exact_from_catalog.resolved_manifest is selected
    resolved = scope.resolve_control_plane_identity_scope(
        host,
        {"pipeline": "chembl_activity", "run_type": "incremental"},
    )
    assert resolved.resolved_via == "latest_manifest_for_scope"
    assert resolved.resolved_manifest is selected


def test_control_plane_scope_does_not_scan_catalog_for_latest_lookup() -> None:
    selected = _manifest(pipeline_name="chembl_activity", run_id=_RUN_ID)
    manifest_port = _ManifestPort((selected,))
    manifest_port.list_all = lambda: (_ for _ in ()).throw(  # type: ignore[attr-defined]
        AssertionError("latest scope must not scan the manifest catalog")
    )

    resolved = scope.resolve_control_plane_identity_scope(
        _Host(manifest_port),
        {"pipeline": "chembl_activity"},
    )

    assert resolved.resolved_manifest is selected
    assert resolved.resolved_via == "latest_manifest_for_scope"
