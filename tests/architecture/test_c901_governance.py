"""Architecture checks for C901 complexity governance in CI."""

from __future__ import annotations

import pytest

import json
from pathlib import Path


pytestmark = pytest.mark.architecture


def test_c901_governance_job_is_declared_in_workflow() -> None:
    """CI workflow must declare dedicated blocking C901 governance job."""
    workflow = Path(".github/workflows/import-linter.yml").read_text(encoding="utf-8")

    assert "c901-governance:" in workflow
    assert "C901 Governance (blocking)" in workflow
    assert "ruff check src/bioetl --select C901" in workflow
    assert "python -m scripts.engineering.qa check-c901" in workflow
    assert "--mode" in workflow


def test_import_linter_contracts_are_declared_as_blocking_workflow_step() -> None:
    """CI must expose import-linter as an explicit blocking confidence signal."""
    workflow = Path(".github/workflows/import-linter.yml").read_text(encoding="utf-8")

    assert "arch-tests:" in workflow
    assert "Run import-linter architecture contracts" in workflow
    assert "uv run lint-imports --config .importlinter" in workflow


def test_c901_baseline_manifest_contains_expected_count() -> None:
    """C901 baseline manifest size is fixed to current approved debt budget."""
    baseline_path = Path("scripts/engineering/baselines/c901_baseline.json")
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))

    entries = payload.get("entries", [])
    assert isinstance(entries, list)
    assert len(entries) == 0, (
        "C901 baseline must track exactly 0 approved violations. "
        "If debt is reduced, remove entries; if increased, refactor code instead."
    )


def test_c901_baseline_entries_are_unique() -> None:
    """Baseline entries must be unique by file/function identity."""
    baseline_path = Path("scripts/engineering/baselines/c901_baseline.json")
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))

    entries = payload.get("entries", [])
    keys = [f"{item.get('file')}::{item.get('function')}" for item in entries]
    assert len(keys) == len(set(keys)), "Duplicate file/function keys in C901 baseline"
