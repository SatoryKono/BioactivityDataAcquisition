"""Checkpoint debugging runbook keeps its observability workflow owner."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.engineering.ci.pr_lane_results import build_shadow_compare

pytestmark = pytest.mark.unit


def test_checkpoint_debugging_runbook_selects_workflow_diagnostics(
    tmp_path: Path,
) -> None:
    owner = "tests/unit/application/services/test_observability_workflow_service.py"
    path = tmp_path / owner
    path.parent.mkdir(parents=True)
    path.write_text("def test_owner():\n    assert True\n", encoding="utf-8")

    report = build_shadow_compare(
        ["docs/05-operations/runbooks/checkpoint-debugging.md"], repo_root=tmp_path
    )

    assert report["selected"] == [owner]
    assert report["covers_full_suite"] is False
