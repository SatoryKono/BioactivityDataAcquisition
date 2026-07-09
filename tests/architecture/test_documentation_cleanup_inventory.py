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


def test_documentation_cleanup_inventory_has_no_duplicate_surfaces() -> None:
    """Published duplicate documentation surfaces must be merged or redirected."""
    payload = _inventory_payload()
    files = payload["files"]
    assert isinstance(files, list)
    duplicate_paths = [
        str(row["path"])
        for row in files
        if isinstance(row, dict) and row.get("status") == "Duplicate"
    ]
    assert not duplicate_paths, duplicate_paths[:10]


def test_ai_skill_reference_redirects_are_active_compatibility_surfaces() -> None:
    """Legacy local skill-reference URLs stay active after duplicate body removal."""
    payload = _inventory_payload()
    files = payload["files"]
    assert isinstance(files, list)
    rows = {
        str(row["path"]): row
        for row in files
        if isinstance(row, dict) and isinstance(row.get("path"), str)
    }

    redirect_paths = {
        "docs/00-project/ai/skills/local/deep-research/references/critique-framework.md",
        "docs/00-project/ai/skills/local/deep-research/references/report-templates.md",
        "docs/00-project/ai/skills/local/deep-research/references/search-patterns.md",
        "docs/00-project/ai/skills/local/deep-research/references/source-evaluation.md",
        "docs/00-project/ai/skills/local/documentation-audit/references/audit-checklist.md",
        "docs/00-project/ai/skills/local/documentation-audit/references/report-template.md",
        "docs/00-project/ai/skills/local/py-test-swarm/references/l1-playbook.md",
        "docs/00-project/ai/skills/local/py-test-swarm/references/l2-l3-task-brief.md",
        "docs/00-project/ai/skills/local/py-test-swarm/references/report-templates.md",
        "docs/00-project/ai/skills/local/technical-designer-mermaid/references/patterns.md",
    }
    missing = sorted(path for path in redirect_paths if path not in rows)
    assert not missing
    for path in sorted(redirect_paths):
        assert rows[path]["status"] == "Active"
        assert rows[path]["declared_class"] == "published-redirect"
        assert rows[path]["recommended_action"] == "keep"


def test_documentation_cleanup_inventory_routes_diagram_artifacts() -> None:
    """Generated diagram support artifacts must have explicit route ownership."""
    payload = _inventory_payload()
    files = payload["files"]
    assert isinstance(files, list)
    rows = {
        str(row["path"]): row
        for row in files
        if isinstance(row, dict) and isinstance(row.get("path"), str)
    }

    expected_routes = {
        "docs/02-architecture/diagrams/class-diagrams/90-pkg-application-composite-checkpoint.mmd": "architecture-diagram-package-family-sources",
        "docs/02-architecture/diagrams/bundles/class.bundle.md": "architecture-diagram-bundles",
        "docs/02-architecture/diagrams/architecture/png/INDEX.md": "architecture-diagram-render-artifacts",
    }
    missing = sorted(path for path in expected_routes if path not in rows)
    assert not missing
    for path, route_id in expected_routes.items():
        assert rows[path]["status"] == "Generated"
        assert rows[path]["generated_route"] == route_id


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
