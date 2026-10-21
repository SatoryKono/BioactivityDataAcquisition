"""Selector caches retain bounded identity-checked snapshots without fabricating data."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from bioetl.interfaces.http import _health_server_routing_support as routing
from bioetl.interfaces.http import _report_selector_options as options
from bioetl.interfaces.http import _run_explorer_snapshot as snapshots
from bioetl.interfaces.http._selector_catalog import SelectorCatalog
from bioetl.interfaces.http._forensic_request_budget import ForensicEndpointUnavailable

pytestmark = pytest.mark.unit


def test_report_entry_from_another_pipeline_does_not_enter_selector(tmp_path):
    entry = SimpleNamespace(
        owner="chembl_assay",
        run_id="run",
        schema_version="pipeline_run_report_v2",
        identity_snapshot={
            "pipeline_name": "chembl_assay",
            "run_id": "run",
            "provider": "chembl",
        },
    )
    assert not options._entry_matches_catalog(entry, {"pipeline": ("chembl_activity",)})
    assert (
        options._maybe_report_option(
            entry=entry,
            dimension="provider",
            response_shape="options",
            scopes={"provider": ("pubmed",)},
            root=tmp_path,
            timezone="UTC",
            seen=set(),
        )
        is None
    )


@pytest.mark.asyncio
async def test_report_catalog_evicts_oldest_owner_scope_at_capacity():
    catalog = SelectorCatalog()
    for number in range(33):
        pipeline = f"provider_entity_{number}"
        assert (
            await catalog.read_reports({"pipeline": (pipeline,)}, lambda scopes: [])
            == []
        )
    assert len(catalog._report_snapshots) == 32
    assert ("provider_entity_0",) not in catalog._report_snapshots
    assert ("provider_entity_32",) in catalog._report_snapshots


def test_non_recent_or_unstructured_snapshot_is_returned_without_reinterpretation():
    cache = snapshots.RunExplorerSnapshotCache()
    cache._stored = {"order_by": "other", "items": None}
    assert cache.materialize() == {"order_by": "other", "items": None}
    assert snapshots._without_timing({"items": None}) == {"items": None}


@pytest.mark.asyncio
async def test_snapshot_refresh_without_manifest_catalog_preserves_last_good_page():
    cache = snapshots.RunExplorerSnapshotCache()
    cache._stored = {"items": ["accepted"]}
    await cache.refresh_once(SimpleNamespace(_run_manifest_port=None))
    assert cache.materialize()["items"] == ["accepted"]


@pytest.mark.parametrize(
    "changes",
    [
        {"view": "selected"},
        {"limit": 20},
        {"run_id": "concrete"},
        {"lookup_run_id": "concrete"},
    ],
)
def test_selected_or_nondefault_query_cannot_reuse_default_recent_snapshot(changes):
    query = {
        "view": "recent",
        "limit": 10,
        "pipeline": "All",
        "workflow": "All",
        "run_type": "All",
        "run_id": "-",
        "lookup_run_id": None,
    }
    query.update(changes)
    assert not snapshots.is_default_recent_browse(**query)


@pytest.mark.asyncio
async def test_completed_snapshot_failure_is_not_suppressed_during_shutdown():
    error = RuntimeError("snapshot failed")

    async def fail():
        raise error

    task = asyncio.create_task(fail())
    await asyncio.gather(task, return_exceptions=True)
    with pytest.raises(RuntimeError) as caught:
        await snapshots.stop_run_explorer_snapshot(task)
    assert caught.value is error


@pytest.mark.asyncio
async def test_prewarm_failure_does_not_prevent_health_server_startup():
    host = SimpleNamespace(
        _selector_catalog=SimpleNamespace(
            options=SimpleNamespace(
                read=AsyncMock(
                    side_effect=ForensicEndpointUnavailable(
                        reason="catalog_unavailable", status_code=503
                    )
                )
            )
        ),
        _selector_endpoint_limiter=Mock(),
    )
    await routing.prewarm_selector_options(host)
    host._selector_catalog.options.read.assert_awaited_once()
