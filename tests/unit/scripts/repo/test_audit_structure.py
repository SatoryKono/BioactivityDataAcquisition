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
"""Unit tests for structure-audit governance alignment."""

from __future__ import annotations

import pytest

from pathlib import Path

import yaml

from scripts.engineering.diagnostics import audit_structure as module


pytestmark = pytest.mark.unit


def _write_governance_files(tmp_path: Path) -> None:
    allowlist_path = tmp_path / ".github" / "root-allowlist.txt"
    allowlist_path.parent.mkdir(parents=True)
    allowlist_path.write_text("README.md\npyproject.toml\n", encoding="utf-8")

    catalog_path = tmp_path / "configs" / "quality" / "repo_structure_catalog.yaml"
    catalog_path.parent.mkdir(parents=True)
    catalog_path.write_text(
        yaml.safe_dump(
            {
                "docs_drafts": {"allowed_files": []},
                "plans": {
                    "readme": "docs/plans/README.md",
                    "max_active_backlog": 1,
                    "allowed_files": [
                        {
                            "path": "docs/plans/consolidated-open-tasks-plan-2026-03-21.md",
                            "lifecycle": "active_backlog",
                        }
                    ],
                },
                "src_sidecars": {
                    "approved_roots": [
                        {"path": "src/bioetl"},
                        {"path": "src/tools"},
                        {"path": "src/memory"},
                    ]
                },
                "docs_code_zones": {
                    "approved_roots": [
                        {"path": "docs/00-project/ai/agents/scripts"},
                    ],
                },
                "local_tolerated_root_dirs": {
                    "approved_roots": [
                        {"path": ".agent-work"},
                        {"path": ".scannerwork"},
                    ],
                },
                "blocked_cleanup_zones": [{"path": "docs/99-archive"}],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _write_minimal_repo_tree(tmp_path: Path) -> None:
    (tmp_path / "docs" / "plans").mkdir(parents=True)
    (tmp_path / "docs" / "99-archive").mkdir(parents=True)
    (tmp_path / "src" / "bioetl").mkdir(parents=True)
    for layer in module.REQUIRED_BIOETL_LAYERS:
        (tmp_path / "src" / "bioetl" / layer).mkdir(parents=True, exist_ok=True)


def test_run_audit_allows_tests_tree_support_package(tmp_path: Path) -> None:
    _write_governance_files(tmp_path)
    _write_minimal_repo_tree(tmp_path)
    (tmp_path / "tests" / "testing_support").mkdir(parents=True)
    (tmp_path / "tests" / "testing_support" / "__init__.py").write_text(
        "", encoding="utf-8"
    )

    result = module.run_audit(tmp_path)

    assert not result.must_violations
    assert not result.should_violations


def test_run_audit_allows_cataloged_docs_code_zone_and_tolerated_hidden_roots(
    tmp_path: Path,
) -> None:
    _write_governance_files(tmp_path)
    _write_minimal_repo_tree(tmp_path)
    (tmp_path / "docs" / "00-project" / "ai" / "agents" / "scripts").mkdir(
        parents=True, exist_ok=True
    )
    (
        tmp_path / "docs" / "00-project" / "ai" / "agents" / "scripts" / "agent_tool.py"
    ).write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / ".agent-work").mkdir()
    (tmp_path / ".scannerwork").mkdir()

    result = module.run_audit(tmp_path)

    assert not result.must_violations
    assert not result.should_violations


def test_run_audit_allows_cataloged_archived_agents_scripts_zone(
    tmp_path: Path,
) -> None:
    _write_governance_files(tmp_path)
    catalog_path = tmp_path / "configs" / "quality" / "repo_structure_catalog.yaml"
    catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    catalog["docs_code_zones"]["approved_roots"] = [
        {"path": "docs/99-archive/agents-scripts-2026-09"},
    ]
    catalog_path.write_text(yaml.safe_dump(catalog, sort_keys=False), encoding="utf-8")
    _write_minimal_repo_tree(tmp_path)
    archive_dir = tmp_path / "docs" / "99-archive" / "agents-scripts-2026-09" / "diagrams"
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / "legacy_helper.py").write_text("print('archived')\n", encoding="utf-8")
    (
        tmp_path / "docs" / "99-archive" / "agents-scripts-2026-09" / "legacy_tool.py"
    ).write_text("print('archived')\n", encoding="utf-8")

    result = module.run_audit(tmp_path)

    assert not result.must_violations
    assert not result.should_violations


def test_live_catalog_ratifies_archived_agents_scripts_docs_code_zone() -> None:
    catalog = yaml.safe_load(
        (
            Path(__file__).resolve().parents[4]
            / "configs"
            / "quality"
            / "repo_structure_catalog.yaml"
        ).read_text(encoding="utf-8")
    )
    roots = [
        entry["path"]
        for entry in catalog["docs_code_zones"]["approved_roots"]
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    ]
    assert "docs/99-archive/agents-scripts-2026-09" in roots
    assert "docs/00-project/ai/agents/policy" in roots
    assert "docs/00-project/ai/agents/scripts" not in roots


def test_run_audit_allows_cataloged_visible_local_root_dirs(tmp_path: Path) -> None:
    _write_governance_files(tmp_path)
    _write_minimal_repo_tree(tmp_path)

    catalog_path = tmp_path / "configs" / "quality" / "repo_structure_catalog.yaml"
    catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    local_roots = catalog["local_tolerated_root_dirs"]["approved_roots"]
    local_roots.extend(
        [
            {"path": "tmp"},
            {"path": "~"},
            {"path": ".coverage-sharded-current-main"},
        ]
    )
    catalog_path.write_text(
        yaml.safe_dump(catalog, sort_keys=False),
        encoding="utf-8",
    )

    (tmp_path / "tmp").mkdir()
    (tmp_path / "~").mkdir()
    (tmp_path / ".coverage-sharded-current-main").mkdir()

    result = module.run_audit(tmp_path)

    assert not result.must_violations
    assert not result.should_violations


def test_run_audit_rejects_unapproved_root_directory(tmp_path: Path) -> None:
    _write_governance_files(tmp_path)
    _write_minimal_repo_tree(tmp_path)
    (tmp_path / "rogue").mkdir()

    result = module.run_audit(tmp_path)

    assert any(
        violation.category == "ROOT_DIR" and violation.path == "rogue"
        for violation in result.must_violations
    )


def test_run_audit_rejects_editor_metadata_inside_data(tmp_path: Path) -> None:
    _write_governance_files(tmp_path)
    _write_minimal_repo_tree(tmp_path)
    (tmp_path / "data" / ".idea").mkdir(parents=True)
    (tmp_path / "data" / ".idea" / "workspace.xml").write_text(
        "<project />\n", encoding="utf-8"
    )

    result = module.run_audit(tmp_path)

    assert any(
        violation.category == "DATA_EDITOR_STATE" and violation.path == "data/.idea"
        for violation in result.must_violations
    )
