"""Architecture tests for lightweight docs-only governance workflow coverage."""

from __future__ import annotations

from pathlib import Path


def test_tests_workflow_keeps_docs_only_changes_out_of_heavy_matrix() -> None:
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")

    assert "paths-ignore:" in workflow
    assert "'docs/**'" in workflow


def test_docs_workflow_runs_lightweight_docs_governance_profile() -> None:
    workflow = Path(".github/workflows/docs.yml").read_text(encoding="utf-8")

    assert "docs-governance:" in workflow
    assert "Run docs-governance architecture tests" in workflow
    assert "validate-mkdocs:\n    needs: docs-governance" in workflow


def test_docs_governance_profile_covers_doc_sync_architecture_tests() -> None:
    workflow = Path(".github/workflows/docs.yml").read_text(encoding="utf-8")

    expected_targets = (
        "tests/architecture/test_architecture_dependency_docs_drift.py::test_dependency_map_drift_check_passes_current_repo",
        "tests/architecture/test_config_topology_docs_drift.py",
        "tests/architecture/test_diagram_narrative_docs_sync.py",
        "tests/architecture/test_documentation_audit_remediation.py",
        "tests/architecture/test_docs_governance_workflow.py",
        "tests/architecture/test_docs_version_sync.py::TestDocsVersionSync::test_required_docs_synced",
        "tests/architecture/test_documentation_sync.py::test_mkdocs_nav_references_existing_markdown_files",
        "tests/architecture/test_internal_orchestration_docs.py",
        "tests/architecture/test_runtime_agent_docs_drift.py",
    )

    for target in expected_targets:
        assert target in workflow, f"Missing docs-governance target: {target}"
