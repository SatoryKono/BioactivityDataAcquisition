# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Render blank-screen gate and deployed dashboard parity (#6686, #6690)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.engineering.qa import report_dashboard_inventory as inventory
from scripts.ops.observability.grafana import rerender_grafana_screenshots as rerender

pytestmark = pytest.mark.unit


def _png(width: int = 1024, height: int = 900, fill: bytes = b"\x00") -> bytes:
    header = (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
    )
    return header + (fill * 8000)


def test_materially_blank_png_detects_uniform_payload(tmp_path: Path) -> None:
    blank = tmp_path / "blank.png"
    blank.write_bytes(_png(fill=b"\xaa"))
    problem = rerender._materially_blank_png_problem(blank)
    assert problem is not None
    assert "blank" in problem


def test_materially_blank_png_accepts_diverse_payload(tmp_path: Path) -> None:
    diverse = tmp_path / "ok.png"
    filler = bytes((i * 37) % 256 for i in range(12000))
    diverse.write_bytes(_png()[:24] + filler)
    assert rerender._materially_blank_png_problem(diverse) is None


def test_normalize_dashboard_payload_strips_only_volatile_fields() -> None:
    payload = {
        "id": 99,
        "version": 7,
        "uid": "bioetl-runtime",
        "title": "Runtime",
        "panels": [
            {
                "id": 1,
                "title": "Status",
                "pluginVersion": "12.0.0",
                "targets": [{"expr": "up"}],
            }
        ],
    }
    normalized = inventory._normalize_dashboard_payload(payload)
    assert "id" not in normalized
    assert "version" not in normalized
    assert normalized["uid"] == "bioetl-runtime"
    assert normalized["panels"][0]["title"] == "Status"
    assert "pluginVersion" not in normalized["panels"][0]
    assert normalized["panels"][0]["targets"][0]["expr"] == "up"


def test_compare_deployed_dashboards_detects_query_drift(tmp_path: Path) -> None:
    dashboards = Path("grafana/dashboards")
    sample = next(dashboards.glob("bioetl-runtime.json"))
    payload = json.loads(sample.read_text(encoding="utf-8"))

    def _mutate(node: object) -> bool:
        if isinstance(node, dict):
            expr = node.get("expr")
            if isinstance(expr, str) and expr:
                node["expr"] = expr + " #drift"
                return True
            for value in node.values():
                if _mutate(value):
                    return True
        if isinstance(node, list):
            for item in node:
                if _mutate(item):
                    return True
        return False

    mutated = json.loads(json.dumps(payload))
    assert _mutate(mutated)
    deployed_dir = tmp_path / "deployed"
    deployed_dir.mkdir()
    (deployed_dir / "bioetl-runtime.json").write_text(
        json.dumps(mutated),
        encoding="utf-8",
    )
    for path in dashboards.glob("*.json"):
        if path.name == "bioetl-runtime.json":
            continue
        (deployed_dir / path.name).write_text(
            path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    inv = inventory._load_inventory()
    errors, by_uid = inventory._compare_deployed_dashboards(
        inv,
        deployed_dir=deployed_dir,
    )
    assert errors
    assert any("bioetl-runtime" in err for err in errors)
    assert by_uid.get("bioetl-runtime")
