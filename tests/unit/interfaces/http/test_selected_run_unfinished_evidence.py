"""A persisted start event is not a probe of a live worker."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.interfaces.http._selected_run_live import active_run_diagnostics


@pytest.mark.parametrize("age_seconds", [0, 60, 3600, 86400])
def test_nonterminal_ledger_does_not_prove_running(monkeypatch, age_seconds):
    now = datetime(2026, 9, 23, tzinfo=UTC)
    monkeypatch.setattr(
        "bioetl.interfaces.http._selected_run_live.current_utc_time", lambda: now
    )
    host = MagicMock()
    host._run_manifest_port.get_by_run_id.return_value = SimpleNamespace(
        pipeline_name="chembl_activity",
        manifest_id="m",
        workflow_name=None,
        run_type=SimpleNamespace(value="incremental"),
    )
    host._run_ledger_port.list_entries_by_run_id.return_value = [
        SimpleNamespace(
            manifest_id="m",
            event_type="run_started",
            occurred_at=now - timedelta(seconds=age_seconds),
        )
    ]
    result = active_run_diagnostics(
        host, "chembl_activity", "00000000-0000-0000-0000-000000000001"
    )
    assert result["execution_state"] == "UNFINISHED"
    assert result["verdict"] == "INCOMPLETE"
    assert result["reason"] == "terminal_event_missing"
    assert result["heartbeat_age_seconds"] == age_seconds
