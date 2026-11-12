"""Only unscoped run-type options may use the bounded Prometheus supplement."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, sentinel
import pytest
from bioetl.interfaces.http import _health_server_filter_options_payload as subject

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_unscoped_run_type_options_supplement_existing_payload_without_network(
    monkeypatch,
):
    initial, supplemented = {"items": []}, {"items": ["backfill"]}
    supplement = Mock(return_value=supplemented)
    monkeypatch.setattr(subject, "supplement_prometheus_run_type_options", supplement)
    catalog = SimpleNamespace(read=AsyncMock(return_value=([], [])))
    host = SimpleNamespace(
        _run_manifest_port=sentinel.manifests,
        _workflow_manifest_port=None,
        _run_ledger_port=None,
        _selector_catalog=catalog,
        _prometheus_base_url="http://fixture.invalid",
        _read_optional_param=lambda query, name: query.get(name),
        _read_scope_csv_param=lambda query, name: (),
    )
    added = Mock()
    result = await subject.build_filter_options_payload(
        host,
        {"dimension": "run_type"},
        options_builder=lambda **kwargs: initial,
        add_run_id_items=added,
        include_reports=False,
        deadline=5.0,
    )
    assert result is supplemented
    supplement.assert_called_once_with(
        initial,
        prometheus_base_url="http://fixture.invalid",
        deadline=5.0,
        response_shape="object",
        pipelines=(),
    )
    added.assert_called_once_with(
        supplemented, response_shape="object", dimension="run_type"
    )


def test_options_run_id_label_is_finalized_in_its_own_response_shape(monkeypatch):
    finalize = Mock(return_value=sentinel.empty_catalog)
    monkeypatch.setattr(subject, "finalize_run_id_empty_catalog_label", finalize)
    payload = {"items": []}
    assert (
        subject._finalize_run_id_options_label(
            payload, dimension="run_id", response_shape="options"
        )
        is sentinel.empty_catalog
    )
    finalize.assert_called_once_with(payload)


def test_workflow_scope_disables_universe_supplement():
    host = SimpleNamespace(_prometheus_base_url="http://fixture.invalid")
    assert (
        subject._prometheus_base_url_for_run_type_options(
            host, dimension="run_type", selected_workflows=("workflow",)
        )
        == ""
    )
