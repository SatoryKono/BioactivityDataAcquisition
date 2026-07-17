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


def _rows_by_path() -> dict[str, dict[str, object]]:
    payload = _inventory_payload()
    files = payload["files"]
    assert isinstance(files, list)
    return {
        str(row["path"]): row
        for row in files
        if isinstance(row, dict) and isinstance(row.get("path"), str)
    }


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
    rows = _rows_by_path()

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
        assert rows[path]["lifecycle"] == "published_skill_reference_redirect"
        assert (
            rows[path]["duplicate_resolution"] == "published_skill_reference_redirect"
        )
        assert rows[path]["recommended_action"] == "keep"


def test_documentation_cleanup_inventory_routes_diagram_artifacts() -> None:
    """Generated diagram support artifacts must have explicit route ownership."""
    rows = _rows_by_path()

    expected_routes = {
        (
            "docs/02-architecture/diagrams/class-diagrams/"
            "90-pkg-application-composite-checkpoint.mmd"
        ): "architecture-diagram-package-family-sources",
        "docs/02-architecture/diagrams/bundles/class.bundle.md": "architecture-diagram-bundles",
        "docs/02-architecture/diagrams/architecture/png/INDEX.md": "architecture-diagram-render-artifacts",
    }
    missing = sorted(path for path in expected_routes if path not in rows)
    assert not missing
    for path, route_id in expected_routes.items():
        assert rows[path]["status"] == "Generated"
        assert rows[path]["generated_route"] == route_id


def test_documentation_cleanup_inventory_covers_github_issue_drafts() -> None:
    """Issue drafts and packs must be lifecycle-classified before cleanup."""
    rows = _rows_by_path()
    tracked_issue_files = subprocess.run(
        ["git", "ls-files", ".github/ISSUES"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.splitlines()

    issue_rows = [path for path in rows if path.startswith(".github/ISSUES/")]
    assert len(issue_rows) == len(tracked_issue_files)
    assert len(issue_rows) >= 131
    assert rows[".github/ISSUES/README.md"]["lifecycle"] == "guide"
    assert rows[".github/ISSUES/CHEMBL-ISSUES-INDEX.md"]["lifecycle"] == "index"
    assert (
        rows[".github/ISSUES/DOC-AUDIT-2026-06-19-ISSUE-PACK.md"]["lifecycle"]
        == "issue_pack"
    )
    live_issue = rows[".github/ISSUES/ADR-HYGIENE-4746-Archive-ADR-003-ADR-008.md"]
    assert live_issue["lifecycle"] == "live_issue_mirror"
    assert live_issue["github_issue_number"] == 4746
    assert live_issue["recommended_action"] == "reconcile-with-github-state"


def test_documentation_cleanup_inventory_covers_root_entrypoints() -> None:
    """Root docs that are intentionally retained must have explicit kinds."""
    rows = _rows_by_path()
    expected = {
        "CONTRIBUTING.md": "contributor_entrypoint",
        "GEMINI.md": "ai_runtime_mirror",
        "best_practices.md": "vendor_review_guidance",
    }
    for path, kind in expected.items():
        assert rows[path]["status"] == "Active"
        assert rows[path]["recommended_action"] == "keep"
        assert rows[path]["root_doc_kind"] == kind


def test_documentation_cleanup_inventory_accounts_for_local_docs_reports() -> None:
    """Available local docs/reports artifacts must be counted deterministically."""
    payload = _inventory_payload()
    summary = payload["summary"]
    assert isinstance(summary, dict)
    rows = _rows_by_path()

    docs_report_rows = [
        row for path, row in rows.items() if path.startswith("docs/reports/")
    ]
    ignored_local_rows = [
        row for row in docs_report_rows if row["tracking_state"] == "ignored_local"
    ]
    assert summary["docs_reports_local_count"] == len(docs_report_rows)
    assert summary["total_doc_like_ignored_local"] == len(ignored_local_rows)
    assert rows["docs/reports/README.md"]["tracking_state"] == "tracked"
    assert rows["docs/reports/index.md"]["tracking_state"] == "tracked"
    assert (
        rows["docs/reports/index.md"]["lifecycle"] == "docs_reports_curated_entrypoint"
    )
    inventory_json = rows["docs/reports/generated/documentation-cleanup-inventory.json"]
    assert inventory_json["tracking_state"] == "tracked"
    assert inventory_json["status"] == "Generated"
    assert inventory_json["generated_route"] == "documentation-cleanup-inventory"


def test_documentation_cleanup_inventory_generated_routes_are_owned() -> None:
    """Every Generated row needs a route or a documented deterministic exception."""
    payload = _inventory_payload()
    summary = payload["summary"]
    assert isinstance(summary, dict)
    rows = _rows_by_path()

    assert summary["generated_without_route_or_exception_count"] == 0
    unowned = [
        path
        for path, row in rows.items()
        if row["status"] == "Generated"
        and not row.get("generated_route")
        and not row.get("generated_route_exception")
    ]
    assert not unowned, unowned[:20]
    assert (
        rows["docs/04-reference/api/application.md"]["generated_route"]
        == "api-reference-generated-docs"
    )
    assert (
        rows["docs/03-guides/dashboards/panel-title-inventory.md"]["generated_route"]
        == "dashboard-panel-title-inventory-generated-doc"
    )
    assert (
        rows["docs/00-project/ai/agents/policy/MCP_LOCAL_RUNTIME_CONFIG.md"][
            "generated_route"
        ]
        == "ai-runtime-governance-mirrors"
    )


def test_documentation_cleanup_inventory_classifies_plans_and_reports() -> None:
    """Plans and reports must distinguish active backlog from cleanup candidates."""
    rows = _rows_by_path()

    active_backlog = rows["docs/plans/consolidated-open-tasks-plan-2026-03-21.md"]
    assert active_backlog["status"] == "Active"
    assert active_backlog["lifecycle"] == "active_backlog"
    assert active_backlog["recommended_action"] == "keep"

    supporting_context = rows["docs/plans/chembl-baseline-refactor-plan-2026-06-01.md"]
    assert supporting_context["status"] == "Working"
    assert supporting_context["lifecycle"] == "supporting_context"
    assert supporting_context["recommended_action"] == "archive-after-migration"

    closeout = rows["reports/quality/tech-debt-issues-5847-5852-closeout.json"]
    assert closeout["lifecycle"] == "closeout_evidence"
    assert closeout["freshness"] == "retention-sensitive"
    assert closeout["recommended_action"] == "keep"

    baseline = rows["reports/quality/dead-code-inventory.md"]
    assert baseline["lifecycle"] == "active_quality_baseline"
    assert baseline["generated_route"] == "dead-code-inventory-quality-baseline"


def test_documentation_cleanup_inventory_maps_drafts_and_skill_mirrors() -> None:
    """D-series drafts and generated AI skill mirrors need explicit lifecycle."""
    rows = _rows_by_path()

    # D-01 Governance & Style Guide.md was removed - skip draft check
    # draft = rows["docs/D-01 Governance & Style Guide.md"]
    # assert draft["lifecycle"] == "docs_draft_with_canonical_successor"
    # assert (
    #     draft["canonical_successor"]
    #     == "docs/00-project/governance/01-documentation-governance-style-guide.md"
    # )
    # assert draft["recommended_action"] == "keep"

    license_mirror = rows[
        "docs/00-project/ai/skills/global/.system/skill-creator/license.txt"
    ]
    assert license_mirror["status"] == "Generated"
    assert license_mirror["lifecycle"] == "generated_skill_license_mirror"
    assert license_mirror["generated_route"] == "ai-skill-license-mirrors"


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
    assert (
        route["generator"] == "scripts/docs/checks/documentation_cleanup_inventory.py"
    )
    outputs = {str(output) for output in route.get("outputs", [])}
    assert "docs/reports/generated/documentation-cleanup-inventory.json" in outputs
    assert "docs/reports/generated/documentation-cleanup-inventory.md" in outputs


def test_ai_runtime_generated_mirrors_are_routed_in_registry() -> None:
    """Generated AI runtime mirror families need route ownership."""
    payload = yaml.safe_load(ROUTING_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    routes = payload.get("routes")
    assert isinstance(routes, list)
    route = next(
        item for item in routes if item.get("id") == "ai-runtime-governance-mirrors"
    )
    outputs = {str(output) for output in route.get("outputs", [])}
    assert "docs/00-project/ai/agents/agents/" in outputs
    assert "docs/00-project/ai/agents/orchestration/" in outputs
    assert "docs/00-project/ai/agents/policy/" in outputs
