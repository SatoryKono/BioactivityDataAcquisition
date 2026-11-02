"""Unit coverage for the Phase-2 Grafana dashboard linter."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ops.observability.grafana import lint_dashboard_phase2 as lint


pytestmark = pytest.mark.unit


def test_phase2_linter_passes_on_provisioned_dashboards() -> None:
    assert lint.main([]) == 0


def test_phase2_linter_flags_missing_nav_and_index_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dash = {
        "uid": "bioetl-overview-v2",
        "panels": [
            {
                "id": 42,
                "type": "table",
                "transformations": [
                    {
                        "id": "organize",
                        "options": {"indexByName": {"a": 0, "b": 0}},
                    }
                ],
            }
        ],
    }
    path = tmp_path / "bioetl-overview-v2.json"
    path.write_text(__import__("json").dumps(dash), encoding="utf-8")
    monkeypatch.setattr(lint, "DASH_DIR", tmp_path)
    monkeypatch.setattr(lint, "FILES", ("bioetl-overview-v2.json",))
    findings = lint.lint_dashboard(path)
    assert any("missing navigation panel id=1000" in item for item in findings)
    assert any("indexByName collision" in item for item in findings)
