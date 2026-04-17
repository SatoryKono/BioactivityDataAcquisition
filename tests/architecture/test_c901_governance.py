"""Architecture checks for C901 complexity governance in CI."""

from __future__ import annotations

import json
from pathlib import Path


def test_c901_governance_job_is_declared_in_workflow() -> None:
    """CI workflow must declare dedicated blocking C901 governance job."""
    workflow = Path(".github/workflows/import-linter.yml").read_text(encoding="utf-8")

    assert "c901-governance:" in workflow
    assert "C901 Governance (blocking)" in workflow
    assert "ruff check src/bioetl --select C901" in workflow
    assert "scripts/engineering/qa/check_c901_baseline.py" in workflow
    assert "--mode" in workflow


def test_c901_baseline_manifest_contains_expected_count() -> None:
    """C901 baseline manifest size is fixed to current approved debt budget."""
    baseline_path = Path("scripts/engineering/baselines/c901_baseline.json")
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))

    entries = payload.get("entries", [])
    assert isinstance(entries, list)
    assert len(entries) == 7, (
        "C901 baseline must track exactly 7 approved violations. "
        "If debt is reduced, remove entries; if increased, refactor code instead."
    )


def test_c901_baseline_entries_are_unique() -> None:
    """Baseline entries must be unique by file/function identity."""
    baseline_path = Path("scripts/engineering/baselines/c901_baseline.json")
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))

    entries = payload.get("entries", [])
    keys = [f"{item.get('file')}::{item.get('function')}" for item in entries]
    assert len(keys) == len(set(keys)), "Duplicate file/function keys in C901 baseline"
