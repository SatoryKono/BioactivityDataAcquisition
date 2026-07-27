"""Closeout inventory governance (T-05 / #6600)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

_REPO_ROOT = Path(__file__).resolve().parents[2]
_INVENTORY = _REPO_ROOT / "configs/quality/architecture_closeout_inventory.yaml"
_ARCHITECTURE = _REPO_ROOT / "tests/architecture"


def _closeout_paths() -> list[str]:
    paths: list[str] = []
    for path in sorted(_ARCHITECTURE.glob("test_*.py")):
        name = path.name.lower()
        if "closeout" in name or name.startswith("test_tech_debt_issues_"):
            paths.append(path.relative_to(_REPO_ROOT).as_posix())
    return paths


def test_closeout_inventory_exists_and_classifies_policy() -> None:
    payload = yaml.safe_load(_INVENTORY.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["summary"]["minimum_fold_or_delete_fraction"] >= 0.25
    assert "default_unlisted_classification" in payload["summary"]
    classifications = set(payload["classification"])
    assert {"keep_as_is", "fold_into_generic", "delete_after_sunset"} <= classifications


def test_closeout_files_are_inventoried_or_default_fold() -> None:
    payload = yaml.safe_load(_INVENTORY.read_text(encoding="utf-8"))
    explicit = {entry["path"]: entry for entry in payload.get("entries", [])}
    closeouts = _closeout_paths()
    assert closeouts, "expected closeout architecture tests to exist"

    fold_or_delete = 0
    for path in closeouts:
        entry = explicit.get(path)
        classification = (
            entry["classification"]
            if entry is not None
            else payload["summary"]["default_unlisted_classification"]
        )
        assert classification in {
            "keep_as_is",
            "fold_into_generic",
            "delete_after_sunset",
        }
        if classification in {"fold_into_generic", "delete_after_sunset"}:
            fold_or_delete += 1

    fraction = fold_or_delete / len(closeouts)
    assert fraction >= float(payload["summary"]["minimum_fold_or_delete_fraction"]), (
        f"closeout fold/delete fraction {fraction:.2%} below minimum "
        f"{payload['summary']['minimum_fold_or_delete_fraction']}"
    )
