"""Fail-closed scope fallbacks for control-plane evidence routes."""

from __future__ import annotations

from typing import cast

import pytest

from bioetl.interfaces.http import (
    _health_server_control_plane_evidence_scope as evidence_scope,
)


pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_latest_complete_uses_both_pipeline_and_workflow_catalogs(monkeypatch):
    from unittest.mock import MagicMock
    from bioetl.interfaces.http import (
        _health_server_control_plane_evidence_routing as module,
    )

    host = MagicMock()
    host._read_required_param.return_value = "chembl_activity"
    host._read_scope_csv_param.side_effect = lambda _query, key: (
        ("backfill",) if key == "run_type" else ()
    )
    host._is_all_scope_token.return_value = False
    host._run_manifest_port.list_all.return_value = ("pipeline-manifest",)
    host._workflow_manifest_port.list_all.return_value = ("workflow-manifest",)
    monkeypatch.setattr(module, "read_selected_run_id", lambda *a: None)
    monkeypatch.setattr(module, "_require_service", lambda _host: "service")
    build = MagicMock(return_value={"status": "OK"})
    monkeypatch.setattr(module, "build_latest_complete_run_payload", build)
    assert await module._latest_complete_payload(host, {}) == {"status": "OK"}
    assert build.call_args.kwargs["manifests"] == ("pipeline-manifest",)
    assert build.call_args.kwargs["workflow_manifests"] == ("workflow-manifest",)
    host._run_manifest_port.list_all.assert_called_once_with()
    host._workflow_manifest_port.list_all.assert_called_once_with()


class _Host:
    def __init__(self, *, pipeline_error: Exception | None = None) -> None:
        self._run_manifest_port = object()
        self._pipeline_error = pipeline_error
        self.pipeline_reads = 0

    def _read_required_param(self, query: dict[str, str], name: str) -> str:
        self.pipeline_reads += 1
        if self._pipeline_error is not None:
            raise self._pipeline_error
        value = query.get(name, "").strip()
        if not value:
            raise ValueError(f"Missing required query parameter: {name}")
        return value

    @staticmethod
    def _read_optional_param(query: dict[str, str], name: str) -> str | None:
        value = query.get(name)
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @classmethod
    def _read_scope_csv_param(
        cls,
        query: dict[str, str],
        name: str,
    ) -> tuple[str, ...]:
        value = cls._read_optional_param(query, name)
        if value is None:
            return ()
        return tuple(item.strip() for item in value.split(",") if item.strip())


@pytest.mark.asyncio
async def test_resolve_evidence_scope_does_not_reread_failed_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _Host(pipeline_error=OSError("pipeline store unavailable"))

    def fail_resolve(*_args: object, **_kwargs: object) -> object:
        raise OSError("pipeline store unavailable")

    monkeypatch.setattr(
        evidence_scope,
        "resolve_control_plane_identity_scope",
        fail_resolve,
    )

    scope, payload = await evidence_scope.resolve_evidence_scope(
        cast(evidence_scope.EvidenceScopeHost, host),
        {"pipeline": "chembl_activity"},
        endpoint="manifest-validation",
        check="parse",
        reason="source_read_failed",
    )

    assert scope is None
    assert payload is not None
    assert payload["status"] == "UNKNOWN"
    assert host.pipeline_reads == 1
    assert payload["pipeline"] == ""
    assert payload["resolved_via"] == "control_plane_source_read_failed"


@pytest.mark.asyncio
async def test_unresolved_evidence_scope_uses_safe_placeholder_on_reread() -> None:
    host = _Host(pipeline_error=ValueError("missing pipeline"))

    fallback = evidence_scope._unresolved_evidence_scope(
        cast(evidence_scope.EvidenceScopeHost, host),
        {},
        resolved_via="control_plane_source_read_failed",
    )

    assert fallback.requested_pipeline == ""
    assert fallback.resolved_via == "control_plane_source_read_failed"
    assert fallback.manifest is None
