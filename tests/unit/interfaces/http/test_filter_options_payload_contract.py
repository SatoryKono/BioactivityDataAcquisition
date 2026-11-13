"""HTTP selector composition preserves scope and bounded supplemental lookups."""

from __future__ import annotations
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, sentinel
import pytest
from bioetl.interfaces.http import _health_server_filter_options_payload as subject

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
@pytest.mark.parametrize("dimension", ["run_type", "run_id"])
async def test_filter_options_supplement_only_unscoped_run_type(monkeypatch, dimension):
    catalog = SimpleNamespace(read=AsyncMock(return_value=([], [])))
    host = SimpleNamespace(
        _run_manifest_port=sentinel.manifests,
        _workflow_manifest_port=None,
        _run_ledger_port=None,
        _selector_catalog=catalog,
        _prometheus_base_url="http://local.invalid",
        _read_optional_param=lambda query, key: query.get(key),
        _read_required_param=lambda query, key: query[key],
        _read_scope_csv_param=lambda query, key: (),
    )
    supplement = Mock(return_value={"items": [{"text": "full", "value": "full"}]})
    monkeypatch.setattr(subject, "supplement_prometheus_run_type_options", supplement)
    builder = Mock(return_value={"items": []})
    add_items = Mock()
    result = await subject.build_filter_options_payload(
        host,
        {
            "dimension": dimension,
            "response_shape": "options",
            "pipeline": "test_pipeline",
        },
        options_builder=builder,
        add_run_id_items=add_items,
        include_reports=False,
        deadline=123.0,
    )
    if dimension == "run_type":
        assert result == supplement.return_value
        supplement.assert_called_once_with(
            builder.return_value,
            prometheus_base_url="http://local.invalid",
            deadline=123.0,
            response_shape="options",
            pipelines=(),
        )
    else:
        supplement.assert_not_called()
        assert result["items"]
    add_items.assert_called_once_with(
        result, response_shape="options", dimension=dimension
    )
