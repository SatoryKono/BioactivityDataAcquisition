"""Validate the shipped native incident banner and adaptive restoration."""

from copy import deepcopy

import pytest

from scripts.ops.observability.grafana._audit_presentation import (
    project_adaptive_dashboard as project,
)

pytestmark = pytest.mark.integration


def test_native_scope_banner_matches_period_end_queries_and_restores_live_profile():
    import json
    from pathlib import Path
    from scripts.ops.observability.grafana._audit_presentation import (
        mark_native_snapshot_clocks,
    )

    source = json.loads(
        Path("grafana/dashboards/bioetl-incident-v1.json").read_text(encoding="utf-8")
    )
    queries = deepcopy(next(p for p in source["panels"] if p["id"] == 9401)["targets"])
    mark_native_snapshot_clocks(source)
    banner = next(p for p in source["panels"] if p["id"] == 9400)
    assert "PERIOD END SNAPSHOT:" in banner["options"]["content"]
    assert "CURRENT:" not in banner["options"]["content"]
    assert "CURRENT" not in banner["description"]
    assert "PERIOD END SNAPSHOT" in banner["description"]
    before = deepcopy(source)
    mark_native_snapshot_clocks(source)
    assert source == before
    adaptive = project(source)
    live_banner = next(p for p in adaptive["panels"] if p["id"] == 9400)
    assert "CURRENT:" in live_banner["options"]["content"]
    assert "CURRENT" in live_banner["description"]
    assert "PERIOD END SNAPSHOT:" not in live_banner["options"]["content"]
    assert "bioetlCurrentPresentation" not in json.dumps(adaptive)
    live_status = next(p for p in adaptive["panels"] if p["id"] == 9401)
    assert live_status["options"]["viewMode"] == "current"
    assert live_status["options"]["currentView"]["queries"] == queries
