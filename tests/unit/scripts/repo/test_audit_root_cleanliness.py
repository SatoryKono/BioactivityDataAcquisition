"""Unit tests for repository root cleanliness policy helpers."""

from __future__ import annotations

from pathlib import Path

import yaml

from scripts.engineering.repo import audit_root_cleanliness as module


def test_collect_tracked_policy_violations_rejects_root_status_markdown() -> None:
    violations = module._collect_tracked_policy_violations(
        ["README.md", "SYNC_COMPLETE.md"]
    )

    assert violations == [
        "SYNC_COMPLETE.md: root text files must be canonical entrypoints only"
    ]


def test_collect_tracked_policy_violations_rejects_root_python() -> None:
    violations = module._collect_tracked_policy_violations(["test_neo4j_memory.py"])

    assert violations == [
        "test_neo4j_memory.py: root-level Python files are not allowed"
    ]


def test_collect_tracked_policy_violations_rejects_generated_artifact_families() -> (
    None
):
    violations = module._collect_tracked_policy_violations(
        [
            "src/tools/reports/project_structure.md",
            "contract-identity-diagnostics.json",
            "contract-registry-diagnostics.json",
            "contract-results.xml",
            "coverage.xml",
            ".coverage-sharded/.coverage",
            "contract-registry-dq-diagnostics.json",
            "contract-schema-classifier-diagnostics.json",
            "hypothesis-contracts-results.xml",
            "port-contracts-results.xml",
            "provider-contract-drift-report.json",
            "reports/README.md",
            "tasks_architecture_metric_exemptions_2026-04-04-09-30.json",
            "trivy-results.sarif",
        ]
    )

    assert violations == [
        ".coverage-sharded/.coverage: generated/runtime artifact must not be tracked",
        "contract-identity-diagnostics.json: generated/runtime artifact must not be tracked",
        "contract-registry-diagnostics.json: generated/runtime artifact must not be tracked",
        "contract-registry-dq-diagnostics.json: generated/runtime artifact must not be tracked",
        "contract-results.xml: generated/runtime artifact must not be tracked",
        "contract-schema-classifier-diagnostics.json: generated/runtime artifact must not be tracked",
        "coverage.xml: generated/runtime artifact must not be tracked",
        "hypothesis-contracts-results.xml: generated/runtime artifact must not be tracked",
        "port-contracts-results.xml: generated/runtime artifact must not be tracked",
        "provider-contract-drift-report.json: generated/runtime artifact must not be tracked",
        "src/tools/reports/project_structure.md: generated/runtime artifact must not be tracked",
        "tasks_architecture_metric_exemptions_2026-04-04-09-30.json: generated/runtime artifact must not be tracked",
        "trivy-results.sarif: generated/runtime artifact must not be tracked",
    ]


def test_collect_tracked_policy_violations_allows_current_canonical_root_files() -> (
    None
):
    violations = module._collect_tracked_policy_violations(
        [
            "CHANGELOG.md",
            "GEMINI.md",
            "README.md",
            "pyproject.toml",
            "docs/plans/repository-file-structure-cleanup-plan-2026-04-20.md",
        ]
    )

    assert violations == []


def test_collect_structure_policy_violations_rejects_uncataloged_legacy_doc(
    tmp_path: Path,
) -> None:
    catalog = {
        "docs_drafts": {
            "allowed_files": [
                {
                    "path": "docs/D-01 Governance & Style Guide.md",
                    "disposition": "retained_repo_only_sync_note",
                }
            ]
        },
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
        "blocked_cleanup_zones": [{"path": "docs/99-archive"}],
    }
    (tmp_path / "docs/99-archive").mkdir(parents=True)
    tracked_paths = [
        "docs/D-01 Governance & Style Guide.md",
        "docs/D-02 Provider Integration Handbook.md",
        "docs/plans/README.md",
        "docs/plans/consolidated-open-tasks-plan-2026-03-21.md",
        "src/bioetl/__init__.py",
    ]

    violations = module._collect_structure_policy_violations(
        tmp_path, tracked_paths, catalog
    )

    assert violations == [
        "docs/D-02 Provider Integration Handbook.md: legacy flat doc must be cataloged in configs/quality/repo_structure_catalog.yaml"
    ]


def test_collect_structure_policy_violations_rejects_unapproved_src_root(
    tmp_path: Path,
) -> None:
    catalog = {
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
        "blocked_cleanup_zones": [{"path": "docs/99-archive"}],
    }
    (tmp_path / "docs/99-archive").mkdir(parents=True)
    tracked_paths = [
        "docs/plans/README.md",
        "docs/plans/consolidated-open-tasks-plan-2026-03-21.md",
        "src/bioetl/__init__.py",
        "src/rogue/__init__.py",
    ]

    violations = module._collect_structure_policy_violations(
        tmp_path, tracked_paths, catalog
    )

    assert violations == [
        "src/rogue: new src top-level family requires explicit structure catalog approval"
    ]


def test_approved_root_directories_include_cataloged_test_support_root() -> None:
    catalog = {
        "test_support_roots": {
            "approved_roots": [{"path": "testing_support"}],
        }
    }

    approved = module._approved_root_directories(catalog)

    assert "testing_support" in approved
    assert "tests" in approved


def test_load_structure_catalog_requires_sections(tmp_path: Path, monkeypatch) -> None:
    catalog_path = tmp_path / ".github" / "root-allowlist.txt"
    catalog_path.parent.mkdir(parents=True)
    catalog_path.write_text("README.md\n", encoding="utf-8")

    structure_catalog = tmp_path / "configs/quality/repo_structure_catalog.yaml"
    structure_catalog.parent.mkdir(parents=True)
    structure_catalog.write_text(
        yaml.safe_dump({"docs_drafts": {"allowed_files": []}}, sort_keys=False),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        module,
        "STRUCTURE_CATALOG_FILE",
        Path("configs/quality/repo_structure_catalog.yaml"),
    )

    try:
        module._load_structure_catalog(tmp_path)
    except RuntimeError as exc:
        assert (
            "Structure catalog missing required sections: blocked_cleanup_zones, plans, src_sidecars"
            == str(exc)
        )
    else:
        raise AssertionError("Expected RuntimeError for incomplete structure catalog")
