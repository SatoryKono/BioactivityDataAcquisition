"""Keep the reviewed memory refactor and resource review impact routes fail closed."""

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
)


@pytest.mark.parametrize("path", MEMORY_PATHS)
def test_reviewed_memory_change_executes_the_memory_suite(path: str) -> None:
    expected = sorted(
        p.relative_to(ROOT).as_posix()
        for p in (ROOT / "tests/unit/memory").rglob("test_*.py")
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
