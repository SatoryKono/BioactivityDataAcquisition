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
"""Helpers for live residual non-growth freezes (#6891 / epic #6890)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tests.architecture._module_coverage_inventory_support import (
    skip_if_artifact_is_not_authoritative,
)

ROOT = Path(__file__).resolve().parents[2]
LIVE_RESIDUAL_SNAPSHOT = ROOT / "reports" / "quality" / "live-residual-snapshot.json"


def load_live_residual_snapshot() -> dict[str, Any]:
    skip_if_artifact_is_not_authoritative(
        root=ROOT,
        artifact_path=LIVE_RESIDUAL_SNAPSHOT,
    )
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
