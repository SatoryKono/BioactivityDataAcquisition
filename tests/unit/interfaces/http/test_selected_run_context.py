"""Selection provenance cannot turn missing evidence into a successful run."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from bioetl.interfaces.http._selected_run_context import with_selection_context
from bioetl.interfaces.http._selected_run_status_cache import SelectedRunStatusCache

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("requested", ["-", "", "All", "$__all", "__all", "*"])
def test_auto_context_shows_resolved_run_and_unfinished_state(requested):
    payload = {
        "run_id": "newest",
        "execution_state": "UNFINISHED",
        "verdict": "INCOMPLETE",
    }
    result = with_selection_context(payload, requested)
    row = result["selection_context"][0]
    assert row["context"] == "AUTO · latest run in scope"
    assert row["run_id"] == "newest"
    assert row["execution_state"] == "UNFINISHED"
    assert row["verdict"] == "INCOMPLETE"
    assert row["resolved_at"].endswith("+00:00")
    assert "selection_context" not in payload


def test_explicit_context_preserves_requested_unknown_run():
    result = with_selection_context(
        {"run_id": "missing", "verdict": "UNKNOWN"}, "missing"
    )
    row = result["selection_context"][0]
    assert row["context"] == "EXPLICIT · requested Run ID"
    assert row["run_id"] == "missing"
    assert row["execution_state"] == "UNKNOWN"


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("no_runs_in_scope", "NO RUN · empty scope"),
        ("request_failed", "Context unavailable"),
    ],
)
def test_no_resolved_run_never_claims_latest_is_displayed(reason, expected):
    result = with_selection_context({"run_id": "-", "reason": reason}, "-")
    assert result["selection_context"][0]["context"] == expected


@pytest.mark.asyncio
async def test_cache_hit_retains_resolution_time_and_explicit_run_has_own_key():
    cache = SelectedRunStatusCache()
    loader = AsyncMock(
        side_effect=lambda: with_selection_context({"run_id": "latest"}, "-")
    )
    automatic = {"pipeline": "p", "run_id": "-"}
    first = await cache.read(automatic, loader)
    second = await cache.read(automatic, loader)
    assert first["selection_context"] == second["selection_context"]
    assert loader.await_count == 1
    explicit = AsyncMock(
        return_value=with_selection_context({"run_id": "finished"}, "finished")
    )
    chosen = await cache.read({"pipeline": "p", "run_id": "finished"}, explicit)
    assert chosen["selection_context"][0]["run_id"] == "finished"
    assert chosen["selection_context"][0]["context"].startswith("EXPLICIT")
    await cache.close()
