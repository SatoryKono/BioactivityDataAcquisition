"""Unit tests for FileRunReportStoreAdapter (#9084)."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.domain.ports.storage.run_report_store import RunReportStorePort
from bioetl.infrastructure.storage.run_report_store_adapter import (
    FileRunReportStoreAdapter,
)

pytestmark = pytest.mark.unit


def test_adapter_satisfies_port_and_round_trips_text(tmp_path: Path) -> None:
    adapter = FileRunReportStoreAdapter()
    assert isinstance(adapter, RunReportStorePort)
    target = tmp_path / "nested" / "report.json"
    adapter.mkdir(target.parent)
    payload = '{"ok": true}' + chr(10)
    adapter.write_text(target, payload)
    assert adapter.read_text(target) == payload
