"""Exact selectors must not enumerate the filesystem run catalogs."""

from typing import Any
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from bioetl.interfaces.http import _health_server_routing_support as routing

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.mark.parametrize("run_id", ["-", "ca60c80e-1be4-5001-8e5c-de0f3df507e2"])
async def test_exact_context_uses_index_and_auto_keeps_catalog(
    run_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifests = MagicMock()
    manifests.list_all.return_value = ()
    manifests.get_by_run_id.return_value = None
    workflows = MagicMock()
    workflows.list_all.return_value = ()
    host = SimpleNamespace(
        _run_manifest_port=manifests,
        _workflow_manifest_port=workflows,
        _read_optional_param=lambda query, key: query.get(key),
    )
    captured: dict[str, Any] = {}

    def build(_host: object, **kwargs: Any) -> dict[str, object]:
        captured.update(kwargs)
        return {"selected": {"run_id": run_id}}

    monkeypatch.setattr(routing, "_selector_context_payload_with_a2", build)
    result = await routing._selector_context_bounded_payload(host, {"run_id": run_id})
    assert result["selected"]["run_id"] == run_id
    if run_id == "-":
        manifests.list_all.assert_called_once()
        workflows.list_all.assert_called_once()
        manifests.get_by_run_id.assert_not_called()
    else:
        manifests.get_by_run_id.assert_called_once()
        manifests.list_all.assert_not_called()
        workflows.list_all.assert_not_called()
    assert captured["manifests"] == ()


async def test_exact_context_loads_only_the_selected_manifest_and_its_parent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = "ca60c80e-1be4-5001-8e5c-de0f3df507e2"
    parent_id = UUID("b2fd1006-33f3-5adf-bafb-204899485521")
    manifest = SimpleNamespace(workflow_run_id=parent_id)
    parent = object()
    manifests = MagicMock()
    manifests.get_by_run_id.return_value = manifest
    workflows = MagicMock()
    workflows.get_by_run_id.return_value = parent
    host = SimpleNamespace(
        _run_manifest_port=manifests,
        _workflow_manifest_port=workflows,
        _read_optional_param=lambda query, key: query.get(key),
    )
    build = MagicMock(return_value={"selected": {"run_id": run_id}})
    monkeypatch.setattr(routing, "_selector_context_payload_with_a2", build)

    result = await routing._selector_context_bounded_payload(host, {"run_id": run_id})

    assert result == {"selected": {"run_id": run_id}}
    manifests.get_by_run_id.assert_called_once_with(UUID(run_id))
    workflows.get_by_run_id.assert_called_once_with(parent_id)
    manifests.list_all.assert_not_called()
    workflows.list_all.assert_not_called()
    assert build.call_args.kwargs["manifests"] == (manifest,)
    assert build.call_args.kwargs["workflow_manifests"] == (parent,)
