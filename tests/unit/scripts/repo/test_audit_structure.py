"""Unit tests for structure-audit governance alignment."""

from __future__ import annotations

from pathlib import Path

import yaml

from scripts.engineering.diagnostics import audit_structure as module


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
                "test_support_roots": {
                    "approved_roots": [{"path": "testing_support"}],
                },
                "docs_code_zones": {
                    "approved_roots": [
                        {"path": "docs/plugins/link_checker"},
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


def test_run_audit_allows_cataloged_test_support(tmp_path: Path) -> None:
    _write_governance_files(tmp_path)
    _write_minimal_repo_tree(tmp_path)
    (tmp_path / "testing_support").mkdir()
    (tmp_path / "testing_support" / "__init__.py").write_text("", encoding="utf-8")

    result = module.run_audit(tmp_path)

    assert not result.must_violations
    assert not result.should_violations


def test_run_audit_allows_cataloged_docs_code_zones_and_tolerated_hidden_roots(
    tmp_path: Path,
) -> None:
    _write_governance_files(tmp_path)
    _write_minimal_repo_tree(tmp_path)
    (tmp_path / "docs" / "plugins" / "link_checker").mkdir(parents=True)
    (tmp_path / "docs" / "plugins" / "link_checker" / "plugin.py").write_text(
        "print('ok')\n", encoding="utf-8"
    )
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


def test_run_audit_rejects_unapproved_root_directory(tmp_path: Path) -> None:
    _write_governance_files(tmp_path)
    _write_minimal_repo_tree(tmp_path)
    (tmp_path / "rogue").mkdir()

    result = module.run_audit(tmp_path)

    assert any(
        violation.category == "ROOT_DIR" and violation.path == "rogue"
        for violation in result.must_violations
    )
