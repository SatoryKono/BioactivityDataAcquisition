"""Unit tests for explicit Grafana renderer recovery (no Grafana restart)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts.ops.observability.grafana import recover_renderer as rr

pytestmark = pytest.mark.unit


def test_monitoring_compose_does_not_health_gate_grafana_on_renderer() -> None:
    compose = yaml.safe_load(
        Path("docker-compose.monitoring.yml").read_text(encoding="utf-8")
    )
    grafana = compose["services"]["grafana"]
    renderer = compose["services"]["renderer"]
    depends = grafana.get("depends_on") or {}
    assert "renderer" not in depends
    assert renderer.get("restart") == "on-failure:3"
    assert renderer.get("mem_limit") == "3g"
    assert renderer.get("oom_score_adj") == 800


def test_recover_renderer_never_recreates_grafana(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[list[str]] = []

    def fake_run(args: list[str], *, timeout: float = 120.0, cwd=None):
        del timeout, cwd
        calls.append(list(args))
        if args[:3] == ["docker", "compose", "-p"] and "ps" in args:
            return 0, "abc123", ""
        if args[:2] == ["docker", "inspect"]:
            payload = {
                "Name": "/bioetl-monitoring-renderer-1",
                "State": {
                    "Status": "running",
                    "Health": {"Status": "healthy"},
                    "OOMKilled": False,
                    "RestartCount": 0,
                },
                "HostConfig": {"Memory": 3 * 1024**3},
            }
            return 0, json.dumps(payload), ""
        if "up" in args and "renderer" in args:
            assert "--no-deps" in args
            assert "grafana" not in args
            return 0, "", ""
        return 0, "", ""

    monkeypatch.setattr(rr, "_run", fake_run)
    monkeypatch.setattr(rr, "probe_grafana_ui", lambda **_k: True)
    monkeypatch.setattr(rr.shutil, "which", lambda _n: "/usr/bin/docker")

    compose = tmp_path / "docker-compose.monitoring.yml"
    compose.write_text("services: {}\n", encoding="utf-8")
    report = rr.recover_renderer(
        project="bioetl-monitoring",
        compose_file=compose,
        wait_seconds=5.0,
    )
    assert report.ok is True
    assert report.healthy is True
    up_calls = [c for c in calls if "up" in c and "renderer" in c]
    assert up_calls
    assert all("grafana" not in c for c in up_calls)
    assert all("--no-deps" in c for c in up_calls)


def test_check_only_suggests_recover(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        rr,
        "list_renderer_snapshots",
        lambda *_a, **_k: [],
    )
    monkeypatch.setattr(rr, "probe_grafana_ui", lambda **_k: True)
    monkeypatch.setattr(rr.shutil, "which", lambda _n: "/usr/bin/docker")
    code = rr.main(["--check-only", "--json"])
    assert code == 1
