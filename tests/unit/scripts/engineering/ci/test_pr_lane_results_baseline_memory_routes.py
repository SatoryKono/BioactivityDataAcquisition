"""Keep the reviewed memory refactor and resource review impact routes fail closed."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.engineering.ci.pr_lane_results import (
    affected_pytest_targets,
    build_shadow_compare,
)

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[5]
RESOURCE_REVIEW = "configs/quality/external_resource_inventory_cc52_source_review.json"
MEMORY_PATHS = (
    "src/memory/artifact_readiness.py",
    "src/memory/graph/importers/expanded_json.py",
    "src/memory/graph/query.py",
    "src/memory/graph/sync_pkg/complexity_marker_buckets.py",
    "src/memory/graph/sync_pkg/git_history.py",
    "src/memory/graph/sync_pkg/int_node_property.py",
    "src/memory/graph/sync_pkg/merge_field_validation_item.py",
    "src/memory/graph/sync_pkg/neo4j_statements.py",
    "src/memory/graph/sync_pkg/python_paths.py",
    "src/memory/graph/sync_pkg/relation_requirement_keys.py",
    "src/memory/graph/sync_pkg/storage_surface_state.py",
    "src/memory/graph/sync_pkg/transport.py",
    "src/memory/graph/sync_pkg/workflow_output_expression.py",
    "src/memory/handoff.py",
    "src/memory/proof_ci.py",
    "src/memory/proof_cli.py",
    "src/memory/query.py",
    "src/memory/rag/_validation_checks.py",
    "src/memory/rag/_validation_model.py",
    "src/memory/rag/filters.py",
    "src/memory/rag/retrieval.py",
    "src/memory/tooling/promote_note.py",
    "src/memory/tooling/prune.py",
    "src/memory/tooling/workflow.py",
    "src/memory/validation.py",
    "src/memory/README.md",
    "src/memory/catalog/memory_registry.yaml",
    "src/memory/catalog/placement_rules.yaml",
    "src/memory/curated/archive/lessons/docker-desktop-wsl-stability-32gib.md",
    "src/memory/curated/archive/lessons/run-reports-and-governance-hash-refresh.md",
    "src/memory/curated/domain_knowledge/task-aware-retrieval-profiles.md",
    "src/memory/curated/incidents/sonar-nosonar.md",
    "src/memory/curated/lessons/promote-only-repeatable-knowledge.md",
    "src/memory/policy/exclusions.yaml",
    "src/memory/tooling/navigation_seed.py",
)


@pytest.mark.parametrize("path", MEMORY_PATHS)
def test_reviewed_memory_change_executes_the_memory_suite(path: str) -> None:
    expected = sorted(
        [
            p.relative_to(ROOT).as_posix()
            for p in (ROOT / "tests/unit/memory").rglob("test_*.py")
        ]
        + [
            "tests/architecture/test_ai_memory_program_contracts.py",
            "tests/integration/memory/test_workflow_partial_retrieval.py",
            "tests/integration/memory/test_workflow_tooling.py",
        ]
    )
    assert expected
    assert affected_pytest_targets([path], repo_root=ROOT) == expected
    shadow = build_shadow_compare([path], repo_root=ROOT)
    assert shadow["selected"] == expected
    assert shadow["activation"] == "not_applied"
    assert shadow["covers_full_suite"] is False


def test_baseline_resource_review_executes_both_qualification_checks() -> None:
    expected = {
        "tests/architecture/test_external_resource_inventory_catalog.py",
        "tests/unit/scripts/engineering/qa/test_requalify_external_resource_inventory.py",
    }
    assert set(affected_pytest_targets([RESOURCE_REVIEW], repo_root=ROOT)) == expected
    shadow = build_shadow_compare([RESOURCE_REVIEW], repo_root=ROOT)
    assert set(shadow["selected"]) == expected
    assert shadow["activation"] == "not_applied"
    assert shadow["covers_full_suite"] is False


@pytest.mark.parametrize(
    "unknown",
    (
        "src/memory/unreviewed.py",
        "src/memory/curated/incidents/unreviewed.md",
        "docs/plans/memory-recovery-unreviewed.md",
        "src/memory/graph/sync_pkg/unreviewed.py",
        "configs/quality/external_resource_inventory_unknown_review.json",
        "configs/quality/external_resource_inventory_baseline_cc52_review-copy.json",
    ),
)
def test_unreviewed_peers_still_fail_alone_and_beside_reviewed_paths(
    unknown: str,
) -> None:
    with pytest.raises(ValueError, match="unmapped paths"):
        build_shadow_compare([unknown], repo_root=ROOT)
    with pytest.raises(ValueError, match="unmapped paths"):
        build_shadow_compare([*MEMORY_PATHS, RESOURCE_REVIEW, unknown], repo_root=ROOT)


def test_memory_recovery_plan_executes_structural_and_documentation_checks() -> None:
    path = "docs/plans/memory-recovery-2026-11-17.md"
    targets = affected_pytest_targets([path], repo_root=ROOT)
    assert "tests/unit/scripts/repo/test_check_root_governance_docs.py" in targets
    assert "tests/architecture/test_documentation_cleanup_inventory.py" in targets
    shadow = build_shadow_compare([path], repo_root=ROOT)
    assert shadow["selected"] == targets
    assert shadow["covers_full_suite"] is False


@pytest.mark.parametrize(
    ("path", "owner"),
    (
        (
            "docs/00-project/ai/agents/guides/CODEX_TASK_ROUTING.md",
            "tests/architecture/test_ai_runtime_governance_links.py",
        ),
        (
            "docs/00-project/ai/memory/agent-memory.md",
            "tests/architecture/test_ai_memory_program_contracts.py",
        ),
    ),
)
def test_runtime_guidance_docs_have_explicit_routes(path: str, owner: str) -> None:
    expected = {
        owner,
        "tests/architecture/test_codex_task_routing.py",
        "tests/architecture/test_runtime_agent_docs_drift.py",
    }
    targets = affected_pytest_targets([path], repo_root=ROOT)
    assert set(targets) == expected
    shadow = build_shadow_compare([path], repo_root=ROOT)
    assert shadow["selected"] == targets
    assert shadow["activation"] == "not_applied"
    assert shadow["covers_full_suite"] is False


@pytest.mark.parametrize(
    "unknown",
    (
        "docs/00-project/ai/agents/guides/CODEX_TASK_ROUTING-unreviewed.md",
        "docs/00-project/ai/memory/agent-memory-unreviewed.md",
    ),
)
def test_runtime_guidance_doc_routes_stay_fail_closed(unknown: str) -> None:
    reviewed = (
        "docs/00-project/ai/agents/guides/CODEX_TASK_ROUTING.md",
        "docs/00-project/ai/memory/agent-memory.md",
    )
    with pytest.raises(ValueError, match="unmapped paths"):
        build_shadow_compare([unknown], repo_root=ROOT)
    with pytest.raises(ValueError, match="unmapped paths"):
        build_shadow_compare([*reviewed, unknown], repo_root=ROOT)
