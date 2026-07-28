"""Helpers for live residual non-growth freezes (#6891 / epic #6890)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LIVE_RESIDUAL_SNAPSHOT = ROOT / "reports" / "quality" / "live-residual-snapshot.json"


def load_live_residual_snapshot() -> dict[str, Any]:
    payload = json.loads(LIVE_RESIDUAL_SNAPSHOT.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert payload.get("schema_version") == "live-residual-snapshot-v1"
    return payload


def assert_residual_not_grown(
    *,
    metric_name: str,
    live_value: int | float,
    baseline_value: int | float,
    epsilon: float = 0.0,
) -> None:
    """Residual metrics must only shrink or stay flat."""
    if isinstance(live_value, float) or isinstance(baseline_value, float):
        assert float(live_value) <= float(baseline_value) + epsilon, (
            f"{metric_name} grew: live={live_value} baseline={baseline_value}"
        )
        return
    assert int(live_value) <= int(baseline_value), (
        f"{metric_name} grew: live={live_value} baseline={baseline_value}"
    )


def hotspot_family(snapshot: dict[str, Any], name: str) -> dict[str, Any]:
    families = snapshot.get("hotspot_families", {})
    assert isinstance(families, dict)
    row = families.get(name)
    assert isinstance(row, dict), (
        f"missing hotspot family in live residual snapshot: {name}"
    )
    return row
