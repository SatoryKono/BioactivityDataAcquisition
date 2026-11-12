"""Service dashboard migration preserves identity and the meaning of samples."""

from __future__ import annotations

import pytest

from scripts.ops.observability.grafana.repair_legacy_prometheus_dashboard import (
    repair_dashboard,
)


def test_legacy_migration_preserves_queries_and_explains_absence():
    source = {
        "uid": "rpfmFFz7z",
        "title": "Prometheus Stats",
        "panels": [
            {"id": 6, "targets": [{"expr": "prometheus_local_storage_memory_series"}]},
            {
                "id": 14,
                "title": "Scrape Duration",
                "targets": [{"expr": "prometheus_target_interval_length_seconds"}],
            },
        ],
    }
    result = repair_dashboard(source)
    assert result["uid"] == source["uid"]
    assert result["panels"][1]["targets"] == source["panels"][1]["targets"]
    assert result["panels"][1]["title"] == "Scrape Interval"
    assert result["panels"][1]["fieldConfig"]["defaults"]["unit"] == "s"
    assert result["panels"][0]["fieldConfig"]["defaults"]["noValue"].startswith(
        "UNSUPPORTED"
    )
    assert source["title"] == "Prometheus Stats"
    assert repair_dashboard(result) == result


def test_migration_rejects_an_unrelated_dashboard():
    with pytest.raises(ValueError):
        repair_dashboard({"uid": "bioetl-overview-v2"})
