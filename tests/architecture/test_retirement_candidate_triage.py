"""Architecture guardrails for zero-anchor retirement triage decisions."""

from __future__ import annotations

import ast
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRIAGE_PATH = PROJECT_ROOT / "configs/quality/retirement_candidate_triage.yaml"
SRC_ROOT = PROJECT_ROOT / "src" / "bioetl"


def _load_triage() -> dict[str, object]:
    payload = yaml.safe_load(TRIAGE_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _iter_src_python_files() -> list[Path]:
    return sorted(SRC_ROOT.rglob("*.py"))


def _count_src_importers(module_name: str) -> int:
    count = 0
    for path in _iter_src_python_files():
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(alias.name == module_name for alias in node.names):
                    count += 1
                    break
            if isinstance(node, ast.ImportFrom) and node.level == 0:
                if node.module == module_name:
                    count += 1
                    break
                if node.module is not None and any(
                    f"{node.module}.{alias.name}" == module_name
                    for alias in node.names
                    if alias.name != "*"
                ):
                    count += 1
                    break
    return count


def test_retirement_triage_entries_are_explicit_and_actionable() -> None:
    """Each tracked retirement tranche should declare a concrete decision."""
    triage = _load_triage()
    assert triage.get("schema_version") == 1
    policy = triage.get("policy", {})
    assert isinstance(policy, dict)
    assert policy.get("review_cycle_days") == 90

    families = triage.get("families", [])
    assert isinstance(families, list) and families
    entries = [
        entry
        for family in families
        if isinstance(family, dict)
        for entry in family.get("entries", [])
        if isinstance(entry, dict)
    ]
    assert entries, "Expected at least one retirement-triage entry"

    for entry in entries:
        disposition = entry.get("disposition")
        assert disposition in {"removed", "retain_active"}
        assert isinstance(entry.get("rationale"), str) and entry["rationale"].strip()
        assert isinstance(entry.get("reviewed_on"), str) and entry["reviewed_on"]
        assert isinstance(entry.get("linked_issue"), str) and entry["linked_issue"]

        target = entry.get("target", {})
        assert isinstance(target, dict)
        module_path = target.get("module_path")
        assert isinstance(module_path, str) and module_path

        if disposition == "retain_active":
            assert isinstance(entry.get("review_by"), str) and entry["review_by"]
            verification = entry.get("verification", {})
            assert isinstance(verification, dict)
            min_src_importers = verification.get("min_src_importers")
            assert isinstance(min_src_importers, int) and min_src_importers >= 1


def test_removed_retirement_tranches_stay_absent() -> None:
    """Removed retirement tranches should not reappear in the source tree."""
    triage = _load_triage()
    entries = [
        entry
        for family in triage.get("families", [])
        if isinstance(family, dict)
        for entry in family.get("entries", [])
        if isinstance(entry, dict) and entry.get("disposition") == "removed"
    ]
    assert entries, "Expected at least one removed retirement tranche"

    for entry in entries:
        target = entry["target"]
        assert isinstance(target, dict)
        module_path = target["module_path"]
        assert isinstance(module_path, str)
        assert not (PROJECT_ROOT / module_path).exists(), (
            f"Removed retirement tranche unexpectedly exists again: {module_path}"
        )


def test_retained_zero_anchor_tranches_have_live_src_importers() -> None:
    """Retained candidates must stay justified by first-party source imports."""
    triage = _load_triage()
    retained = [
        entry
        for family in triage.get("families", [])
        if isinstance(family, dict)
        for entry in family.get("entries", [])
        if isinstance(entry, dict) and entry.get("disposition") == "retain_active"
    ]
    assert retained, "Expected at least one retained retirement tranche"

    for entry in retained:
        target = entry["target"]
        assert isinstance(target, dict)
        module_path = target["module_path"]
        module_name = target["module_name"]
        assert isinstance(module_path, str)
        assert isinstance(module_name, str)
        assert (PROJECT_ROOT / module_path).exists(), (
            f"Retained active tranche is missing its module: {module_path}"
        )

        verification = entry["verification"]
        assert isinstance(verification, dict)
        min_src_importers = verification["min_src_importers"]
        assert isinstance(min_src_importers, int)
        actual_importers = _count_src_importers(module_name)
        assert actual_importers >= min_src_importers, (
            f"{module_name} only has {actual_importers} src importers, below the "
            f"triaged minimum {min_src_importers}. Remove it or refresh the triage ledger intentionally."
        )
