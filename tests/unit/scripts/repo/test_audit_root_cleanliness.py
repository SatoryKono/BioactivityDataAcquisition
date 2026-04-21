"""Unit tests for repository root cleanliness policy helpers."""

from __future__ import annotations

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


def test_collect_tracked_policy_violations_rejects_generated_artifact_families() -> None:
    violations = module._collect_tracked_policy_violations(
        [
            "src/tools/reports/project_structure.md",
            "coverage.xml",
            ".coverage-sharded/.coverage",
            "reports/README.md",
        ]
    )

    assert violations == [
        ".coverage-sharded/.coverage: generated/runtime artifact must not be tracked",
        "coverage.xml: generated/runtime artifact must not be tracked",
        "src/tools/reports/project_structure.md: generated/runtime artifact must not be tracked",
    ]


def test_collect_tracked_policy_violations_allows_current_canonical_root_files() -> None:
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
