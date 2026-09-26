"""Slow source-tree freshness guards for the module coverage inventory."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts.engineering.qa.report_module_coverage_inventory import (
    _iter_source_modules,
    compute_source_tree_sha256,
)

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "reports" / "quality" / "module-coverage-inventory.json"


def _skip_if_source_tree_is_dirty() -> None:
    """Committed inventory assertions require a clean production source tree."""
    try:
        result = subprocess.run(
            ["git", "status", "--short", "--", "src/bioetl"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip(
            "Committed module-coverage inventory dirty-tree guard is not "
            "authoritative on this checkout."
        )
    dirty_entries = [
        line.strip() for line in result.stdout.splitlines() if line.strip()
    ]
    if dirty_entries:
        pytest.skip(
            "Committed module-coverage inventory is only authoritative for a clean "
            "src/bioetl tree. Dirty entries: " + ", ".join(dirty_entries[:20])
        )


def test_module_coverage_inventory_covers_every_source_module() -> None:
    _skip_if_source_tree_is_dirty()
    committed = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    inventory_paths = {str(row["path"]) for row in committed["modules"]}
    expected_paths = {
        path.relative_to(ROOT).as_posix() for path in _iter_source_modules(ROOT)
    }

    assert inventory_paths == expected_paths


def test_module_coverage_inventory_source_tree_hash_is_current() -> None:
    _skip_if_source_tree_is_dirty()
    committed = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))

    assert committed["source_tree_sha256"] == compute_source_tree_sha256(repo_root=ROOT)
    assert "source_tree_sha256" not in committed["summary"]
