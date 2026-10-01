"""The retired dashboard must not reappear through generation or handoffs."""

import json
from pathlib import Path

import pytest

from scripts.ops.observability.grafana.dashboard_context_links import (
    retire_runtime_links,
)
from scripts.ops.observability.grafana.render_nav_bus import BUS, FILE_BY_UID

pytestmark = pytest.mark.integration


def test_retired_dashboard_is_absent_from_both_profiles_and_navigation():
    assert "bioetl-runtime" not in FILE_BY_UID
    assert all(item["uid"] != "bioetl-runtime" for item in BUS)
    for directory in ("dashboards", "dashboards-prometheus-only"):
        root = Path("grafana") / directory
        assert not (root / "bioetl-runtime.json").exists()
        for path in root.glob("*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            assert "bioetl-runtime" not in json.dumps(payload), path


def test_legacy_handoff_preserves_run_and_time_without_stage_scope():
    link = {
        "title": "Open Pipeline Diagnostics",
        "url": "/d/bioetl-runtime/3-pipeline-diagnostics?var-workflow=w"
        "&var-pipeline=p&var-run_type=backfill&var-run_id=exact-run"
        "&var-stage=silver&var-provider_hint=chembl&from=100&to=200",
    }
    retire_runtime_links(link)
    assert link == {
        "title": "Open Run Overview",
        "url": "/d/bioetl-overview-v2/2-overview?var-workflow=w"
        "&var-pipeline=p&var-run_type=backfill&var-run_id=exact-run"
        "&from=100&to=200",
    }
