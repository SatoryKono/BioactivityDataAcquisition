"""Architecture guard for documentation cleanup inventory."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
INVENTORY_JSON = ROOT / "docs/reports/generated/documentation-cleanup-inventory.json"
INVENTORY_MD = ROOT / "docs/reports/generated/documentation-cleanup-inventory.md"
ROUTING_PATH = ROOT / "configs/quality/generated_artifact_routing.yaml"


def _inventory_payload() -> dict[str, object]:
    payload = json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_documentation_cleanup_inventory_artifacts_exist() -> None:
    """Tracked cleanup inventory outputs must be present for drift checks."""
    assert INVENTORY_JSON.exists(), (
        "run: python -m scripts.docs generate-cleanup-inventory --update"
    )
    assert INVENTORY_MD.exists()


def test_documentation_cleanup_inventory_has_no_unknown_published_docs() -> None:
    """Published docs surfaces must not remain in the Unknown bucket."""
    payload = _inventory_payload()
    files = payload["files"]
    assert isinstance(files, list)
    unknown_published = [
        str(row["path"])
        for row in files
        if isinstance(row, dict)
        and row.get("status") == "Unknown"
        and str(row.get("path", "")).startswith("docs/")
    ]
    assert not unknown_published, unknown_published[:10]


def test_documentation_cleanup_inventory_surface_families_present() -> None:
    """Inventory summary must separate canonical/generated/working/archive surfaces."""
    payload = _inventory_payload()
    summary = payload["summary"]
    assert isinstance(summary, dict)
    by_surface = summary.get("by_surface_family")
    assert isinstance(by_surface, dict)
    families = set(by_surface)
    expected = {"canonical", "active", "generated", "working", "archive"}
    assert expected <= families


def test_documentation_cleanup_inventory_check_passes() -> None:
    """Generator --check must stay synchronized with committed inventory artifacts."""
    result = subprocess.run(
        [sys.executable, "-m", "scripts.docs", "generate-cleanup-inventory", "--check"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_documentation_cleanup_inventory_routed_in_registry() -> None:
    """Cleanup inventory generator must remain in generated artifact routing."""
    payload = yaml.safe_load(ROUTING_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    routes = payload.get("routes")
    assert isinstance(routes, list)
    route = next(
        item for item in routes if item.get("id") == "documentation-cleanup-inventory"
    )
    assert route["generator"] == "scripts/docs/checks/documentation_cleanup_inventory.py"
    outputs = {str(output) for output in route.get("outputs", [])}
    assert "docs/reports/generated/documentation-cleanup-inventory.json" in outputs
    assert "docs/reports/generated/documentation-cleanup-inventory.md" in outputs
