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
"""Unit tests for repository root cleanliness policy helpers."""

from __future__ import annotations

import pytest

from pathlib import Path

import yaml

from scripts.engineering.repo import audit_root_cleanliness as module


pytestmark = pytest.mark.unit


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
            ".codex_tmp/session.md",
            "src/tools/reports/project_structure.md",
            "contract-identity-diagnostics.json",
            "contract-registry-diagnostics.json",
            "contract-results.xml",
            "coverage.html",
            "coverage.xml",
            "coverage_20260616.xml",
            ".coverage-sharded/.coverage",
            "contract-registry-dq-diagnostics.json",
            "contract-schema-classifier-diagnostics.json",
            "hypothesis-contracts-results.xml",
            "port-contracts-results.xml",
            "provider-contract-drift-report.json",
            "reports/README.md",
            "Test Results - Pytest_All.html",
            "tasks_architecture_metric_exemptions_2026-04-04-09-30.json",
            "trivy-results.sarif",
        ]
    )

    assert violations == [
        ".codex_tmp/session.md: generated/runtime artifact must not be tracked",
        ".coverage-sharded/.coverage: generated/runtime artifact must not be tracked",
        "Test Results - Pytest_All.html: generated/runtime artifact must not be tracked",
        "contract-identity-diagnostics.json: generated/runtime artifact must not be tracked",
        "contract-registry-diagnostics.json: generated/runtime artifact must not be tracked",
        "contract-registry-dq-diagnostics.json: generated/runtime artifact must not be tracked",
        "contract-results.xml: generated/runtime artifact must not be tracked",
        "contract-schema-classifier-diagnostics.json: generated/runtime artifact must not be tracked",
        "coverage.html: generated/runtime artifact must not be tracked",
        "coverage.xml: generated/runtime artifact must not be tracked",
        "coverage_20260616.xml: generated/runtime artifact must not be tracked",
        "hypothesis-contracts-results.xml: generated/runtime artifact must not be tracked",
        "port-contracts-results.xml: generated/runtime artifact must not be tracked",
        "provider-contract-drift-report.json: generated/runtime artifact must not be tracked",
        "src/tools/reports/project_structure.md: generated/runtime artifact must not be tracked",
        "tasks_architecture_metric_exemptions_2026-04-04-09-30.json: generated/runtime artifact must not be tracked",
        "trivy-results.sarif: generated/runtime artifact must not be tracked",
    ]


def test_collect_forbidden_local_output_roots_detects_ignored_root_outputs() -> None:
    violations = module._collect_forbidden_local_output_roots(
        [
            "logs/",
            "test-output/results.xml",
            "output/run/result.json",
            "reports/logs/bioetl.log",
            "data/output/control/run_manifest/manifest.json",
        ],
        forbidden_roots=("logs", "test-output", "output"),
        blocked_cleanup_paths=frozenset({"data", "reports"}),
        tolerated_local_root_dirs=frozenset({"logs", "test-output"}),
    )

    assert violations == ["output"]


def test_collect_forbidden_local_output_roots_allows_routed_reports_logs() -> None:
    violations = module._collect_forbidden_local_output_roots(
        ["reports/logs/bioetl.log"],
        forbidden_roots=("logs", "test-output"),
        blocked_cleanup_paths=frozenset({"reports"}),
        tolerated_local_root_dirs=frozenset({"logs", "test-output"}),
    )

    assert violations == []


def test_collect_forbidden_local_output_roots_rejects_root_silver_output() -> None:
    violations = module._collect_forbidden_local_output_roots(
        ["silver/test/part-0001.parquet", "data/output/silver/chembl/activity"],
        forbidden_roots=("silver",),
        blocked_cleanup_paths=frozenset({"data"}),
        tolerated_local_root_dirs=frozenset(),
    )

    assert violations == ["silver"]


def test_unexpected_local_root_dirs_on_disk_reject_uncataloged_root_dirs(
    tmp_path: Path,
) -> None:
    (tmp_path / "configs").mkdir()
    (tmp_path / ".benchmarks").mkdir()
    (tmp_path / ".mypy_cache").mkdir()
    (tmp_path / ".qodo").mkdir()
    (tmp_path / "logs").mkdir()

    violations = module._unexpected_local_root_dirs_on_disk(
        tmp_path,
        tracked_root_dirs={"configs"},
        allowed_root_dirs=frozenset({"configs"}),
        tolerated_local_root_dirs=frozenset({".benchmarks", ".mypy_cache", ".qodo"}),
    )

    assert violations == ["logs"]


def test_unexpected_local_root_dirs_on_disk_preserves_nonempty_worktrees(
    tmp_path: Path,
) -> None:
    worktrees = tmp_path / ".worktrees"
    (worktrees / "active-checkout").mkdir(parents=True)

    violations = module._unexpected_local_root_dirs_on_disk(
        tmp_path,
        tracked_root_dirs=set(),
        allowed_root_dirs=frozenset(),
        tolerated_local_root_dirs=frozenset(),
    )

    assert violations == []


def test_unexpected_local_root_dirs_on_disk_rejects_empty_worktrees(
    tmp_path: Path,
) -> None:
    (tmp_path / ".worktrees").mkdir()

    violations = module._unexpected_local_root_dirs_on_disk(
        tmp_path,
        tracked_root_dirs=set(),
        allowed_root_dirs=frozenset(),
        tolerated_local_root_dirs=frozenset(),
    )

    assert violations == [".worktrees"]


def test_unexpected_local_root_python_files_reject_untracked_root_python(
    tmp_path: Path,
) -> None:
    (tmp_path / "test_print.py").write_text("print('x')\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("ok\n", encoding="utf-8")

    violations = module._unexpected_local_root_python_files(
        tmp_path,
        tracked_root_files={"README.md"},
    )

    assert violations == ["test_print.py"]


def test_unexpected_local_root_temp_files_reject_panel_inventory_artifacts(
    tmp_path: Path,
) -> None:
    (tmp_path / ".xml").write_text("<testsuite />\n", encoding="utf-8")
    (tmp_path / "_tmp_panel_inventory.mjs").write_text("{}", encoding="utf-8")
    (tmp_path / "_tmp_panel_inventory.ps1").write_text("{}", encoding="utf-8")
    (tmp_path / "coverage.xml").write_text("<coverage />\n", encoding="utf-8")
    (tmp_path / "mcp-shell.log").write_text("local log\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("ok\n", encoding="utf-8")
    # HTML reports are tracked by cleanup-root-local-clutter, but are not a
    # strict blocker because Windows viewers can keep them locked on WSL drives.
    (tmp_path / "Test Results - Pytest_All.html").write_text(
        "<html></html>\n",
        encoding="utf-8",
    )
    (tmp_path / "Test Results - Pytest_All.xml").write_text(
        "<testsuite />\n",
        encoding="utf-8",
    )

    violations = module._unexpected_local_root_temp_files(
        tmp_path,
        tracked_root_files={"README.md"},
    )

    assert violations == [
        ".xml",
        "Test Results - Pytest_All.xml",
        "_tmp_panel_inventory.mjs",
        "_tmp_panel_inventory.ps1",
        "coverage.xml",
        "mcp-shell.log",
    ]


def test_unexpected_local_root_temp_files_detects_reserved_name_without_is_file() -> (
    None
):
    """Win32 reserved basenames may list without is_file()==True (RH7-C3)."""

    class _ReservedNameEntry:
        def __init__(self, name: str) -> None:
            self.name = name

        def is_dir(self) -> bool:
            return False

        def is_file(self) -> bool:
            return False

    class _FakeRoot:
        def iterdir(self):
            return iter([_ReservedNameEntry("nul")])

    violations = module._unexpected_local_root_temp_files(
        _FakeRoot(),  # type: ignore[arg-type]
        tracked_root_files=set(),
    )

    assert violations == ["nul"]


def test_collect_tracked_policy_violations_allows_current_canonical_root_files() -> (
    None
):
    violations = module._collect_tracked_policy_violations(
        [
            "CHANGELOG.md",
            "GEMINI.md",
            "README.md",
            "best_practices.md",
            "pyproject.toml",
            "docs/plans/repository-file-structure-remediation-plan-2026-04-28.md",
        ]
    )

    assert violations == []


def test_collect_root_layout_state_splits_root_file_and_dir_policy_violations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        module,
        "_load_allowed_root_files",
        lambda _repo_root: frozenset({"README.md"}),
    )
    monkeypatch.setattr(module, "_load_structure_catalog", lambda _repo_root: {})
    monkeypatch.setattr(
        module,
        "_approved_root_directories",
        lambda _catalog: frozenset({"docs"}),
    )
    monkeypatch.setattr(
        module,
        "_get_tracked_paths",
        lambda _repo_root: [
            "README.md",
            "SYNC_COMPLETE.md",
            "docs/index.md",
            "scratch/output.txt",
        ],
    )
    monkeypatch.setattr(module, "_get_untracked_paths", lambda _repo_root: [])

    state = module.collect_root_layout_state(tmp_path)

    assert state["root_file_allowlist_violations"] == ["SYNC_COMPLETE.md"]
    assert state["root_directory_approval_violations"] == ["scratch"]
    assert state["unexpected_root_files"] == ["SYNC_COMPLETE.md"]
    assert state["unexpected_root_dirs"] == ["scratch"]


def test_report_root_layout_violations_uses_separate_file_and_dir_headers(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        module._report_root_layout_violations(
            unexpected_root_files=["SYNC_COMPLETE.md"],
            unexpected_root_dirs=["scratch"],
        )
        == 1
    )

    captured = capsys.readouterr()

    assert "ERROR: root file allowlist violation detected." in captured.err
    assert "Unexpected tracked root files:" in captured.err
    assert "ERROR: root directory approval violation detected." in captured.err
    assert "Unexpected tracked root directories:" in captured.err


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
        "docs/D-02 Provider Integration Handbook.md: legacy flat doc must be"
        " cataloged in configs/quality/repo_structure_catalog.yaml"
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


def test_collect_structure_policy_violations_rejects_ide_metadata_inside_data(
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
        "blocked_cleanup_zones": [{"path": "data"}],
    }
    (tmp_path / "data").mkdir(parents=True)
    tracked_paths = [
        "docs/plans/README.md",
        "docs/plans/consolidated-open-tasks-plan-2026-03-21.md",
        "src/bioetl/__init__.py",
        "data/.idea/workspace.xml",
    ]

    violations = module._collect_structure_policy_violations(
        tmp_path, tracked_paths, catalog
    )

    assert violations == [
        "data/.idea/workspace.xml: IDE metadata must not live inside governed data/ surfaces"
    ]


def test_approved_root_directories_include_tests_without_extra_catalog_root() -> None:
    catalog = {}

    approved = module._approved_root_directories(catalog)

    assert "tests" in approved


def test_approved_root_directories_include_cataloged_root_tooling_root() -> None:
    catalog = {
        "root_tooling_roots": {
            "approved_roots": [{"path": "tools"}],
        }
    }

    approved = module._approved_root_directories(catalog)

    assert "tools" in approved
    assert "scripts" in approved


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
