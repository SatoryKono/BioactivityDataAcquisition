"""Shipped dashboards keep catalog UUIDs and do not filter panel 9701 by run id."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[5]
_DASHBOARDS = _ROOT / "grafana" / "dashboards"
_UIDS = (
    "bioetl-control-plane-v1",
    "bioetl-overview-v2",
    "bioetl-dq-v2",
    "bioetl-incident-v1",
    "bioetl-run-explorer-v1",
)
_COMPACT_STAMP = re.compile(r"\d{8}T\d{6}")


def _load(uid: str) -> dict[str, object]:
    payload = json.loads((_DASHBOARDS / f"{uid}.json").read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _panels(payload: dict[str, object]) -> list[dict[str, object]]:
    found: list[dict[str, object]] = []

    def walk(items: object) -> None:
        if not isinstance(items, list):
            return
        for panel in items:
            if not isinstance(panel, dict):
                continue
            found.append(panel)
            walk(panel.get("panels"))

    walk(payload.get("panels"))
    return found


def test_shipped_dashboards_do_not_embed_a_compact_stamp() -> None:
    for uid in _UIDS:
        text = (_DASHBOARDS / f"{uid}.json").read_text(encoding="utf-8")
        assert _COMPACT_STAMP.search(text) is None, uid


def test_panel_9701_does_not_read_run_id() -> None:
    incident = _load("bioetl-incident-v1")
    panel = next(item for item in _panels(incident) if item.get("id") == 9701)
    targets = panel["targets"]
    assert isinstance(targets, list)
    for target in targets:
        assert isinstance(target, dict)
        expr = str(target.get("expr", ""))
        assert "$run_id" not in expr
        assert "run_id" not in expr


def test_run_explorer_row_links_use_the_uuid_field() -> None:
    explorer = _load("bioetl-run-explorer-v1")
    text = json.dumps(explorer)
    assert "${__data.fields.run_id" in text
    assert "${__data.fields.Run:" not in text
    assert "${__data.fields.Started" not in text
