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
"""Architecture tests for lightweight docs-only governance workflow coverage."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture


def test_tests_workflow_keeps_docs_only_changes_out_of_heavy_matrix() -> None:
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")

    assert "paths-ignore:" in workflow
    assert "'docs/**'" in workflow or '"docs/**"' in workflow


def test_docs_workflow_runs_lightweight_docs_governance_profile() -> None:
    workflow = Path(".github/workflows/docs.yml").read_text(encoding="utf-8")

    assert "docs-governance:" in workflow
    assert "fetch-depth: 0" in workflow
    assert "generate_package_family_class_diagrams.py --check" in workflow
    assert "Run docs-governance architecture tests" in workflow
    assert "validate-mkdocs:\n    needs: docs-governance" in workflow
    assert "'grafana/README.md'" in workflow
    assert "'.codex/agents/**'" in workflow
    assert "'.junie/agents/**'" in workflow


def test_docs_workflow_path_filters_include_github_workflows_glob() -> None:
    """The leaf is reusable; the coordinator owns PR path decisions (#9975)."""
    workflow = Path(".github/workflows/docs.yml").read_text(encoding="utf-8")
    trigger_block = workflow.split("jobs:", maxsplit=1)[0]

    assert "workflow_call:" in trigger_block
    assert "pull_request:" not in trigger_block
    assert "'.github/workflows/**'" in trigger_block

    catalog = Path("configs/quality/github_required_checks.yaml").read_text(
        encoding="utf-8"
    )
    docs_gate = catalog.rsplit("- id: docs-governance", maxsplit=1)[1]
    former_trigger_paths = (
        ".github/actions/setup-python-uv/**",
        "scripts/engineering/qa/check_xwalk_missing_backlog.py",
        "src/bioetl/application/pipelines/chembl/activity_transformer.py",
        "src/bioetl/composition/factories/pipeline/_registry_manifest_chembl.py",
        "tests/architecture/test_ai_runtime_governance_links.py",
        "tests/architecture/test_check_doc_links_guardrails.py",
        "tests/unit/scripts/qa/test_check_xwalk_missing_backlog.py",
        "tests/unit/repo_backed/scripts/diagrams/test_generate_pipeline_dataflows.py",
    )
    assert ".github/workflows/**" in docs_gate
    for path in former_trigger_paths:
        assert path in trigger_block
        assert path in docs_gate


def test_docs_workflow_scopes_pr_diagram_lint_to_changed_sources() -> None:
    """Unchanged full-corpus freshness remains owned by diagram-nightly."""
    workflow = Path(".github/workflows/docs.yml").read_text(encoding="utf-8")

    assert 'EVENT_NAME: ${{ github.event_name }}' in workflow
    assert '"${BASE_REF}" != "main" && "${BASE_REF}" != "develop"' in workflow
    assert 'git diff --name-only "origin/${BASE_REF}"...HEAD' in workflow
    assert "'*.mmd' '*.mermaid'" in workflow
    assert '"${lint_targets[@]}" --json' in workflow


def test_docs_governance_profile_covers_doc_sync_architecture_tests() -> None:
    workflow = Path(".github/workflows/docs.yml").read_text(encoding="utf-8")

    expected_targets = (
        "tests/architecture/test_architecture_dependency_docs_drift.py::test_dependency_map_drift_check_passes_current_repo",
        "tests/architecture/test_config_topology_docs_drift.py",
        "tests/architecture/test_control_plane_runtime_docs_alignment.py",
        "tests/architecture/test_diagram_narrative_docs_sync.py",
        "tests/architecture/test_documentation_audit_remediation.py",
        "tests/architecture/test_api_reference_public_facades.py",
        "tests/architecture/test_docs_governance_workflow.py",
        "tests/architecture/test_observability_docs_drift.py",
        "tests/architecture/test_observability_docs_sync.py",
        "tests/architecture/test_reproducibility_docs_contract_drift.py",
        "tests/architecture/test_docs_version_sync.py::TestDocsVersionSync::test_required_docs_synced",
        "tests/architecture/test_documentation_sync.py::test_mkdocs_nav_references_existing_markdown_files",
        "tests/architecture/test_internal_orchestration_docs.py",
        "tests/architecture/test_runtime_agent_docs_drift.py",
        "tests/architecture/test_workflow_cli_running_boundaries.py",
    )

    for target in expected_targets:
        assert target in workflow, f"Missing docs-governance target: {target}"
