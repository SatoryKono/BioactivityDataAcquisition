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
"""Closeout evidence guards for tech-debt issues #5253-#5264."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT_PATH = (
    ROOT / "reports" / "quality" / "tech-debt-issues-5253-5264-closeout.json"
)
EXPECTED_ISSUES = {f"#{issue_number}" for issue_number in range(5253, 5265)}
REPLAY_DESCRIPTOR_SPLIT_BUDGETS = {
    "src/bioetl/application/services/control_plane/replay/bundle_descriptor_service.py": 250,
    "src/bioetl/application/services/control_plane/replay/_bundle_descriptor_payloads.py": 250,
}


def _load_closeout() -> dict[str, Any]:
    payload = json.loads(CLOSEOUT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _evidence_path(raw_evidence: str) -> str:
    return raw_evidence.split("::", maxsplit=1)[0]


def test_replay_bundle_descriptor_split_stays_below_hotspot_budget() -> None:
    """The replay descriptor split must not recreate a >=250 LOC hotspot."""
    violations: list[str] = []
    for relative_path, max_lines in REPLAY_DESCRIPTOR_SPLIT_BUDGETS.items():
        path = ROOT / relative_path
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        if line_count > max_lines:
            violations.append(f"{relative_path}: {line_count} > {max_lines}")

    assert not violations, (
        "Replay bundle descriptor split exceeded hotspot budgets:\n"
        + "\n".join(violations)
    )
