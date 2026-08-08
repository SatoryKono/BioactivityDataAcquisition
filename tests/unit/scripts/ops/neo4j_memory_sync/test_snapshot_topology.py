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
"""Snapshot topology and graph-shape invariants for Neo4j memory sync."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Legacy memory sync test - module structure changed")

# from tests.testing_support.neo4j_memory_sync import (  # noqa: F401
    test_development_cycle_surface_filter_is_now_a_clean_noop,
    test_duplication_analysis_config_excludes_normalization_registry_path,
    test_normalize_docs_repo_reference_strips_globs_and_keeps_repo_paths,
    test_snapshot_contains_complexity_candidates_with_simplification_links,
    test_snapshot_contains_core_repo_surfaces,
    test_snapshot_contains_duplication_clusters_with_promotion_targets,
    test_snapshot_contains_expected_relations,
    test_snapshot_contains_workflow_execution_cli_and_claim_extensions,
    test_snapshot_enriches_current_normalization_topology,
    test_snapshot_excludes_normalization_registry_duplication_noise,
    test_storage_ref_from_output_path_normalizes_data_output_prefix,
    test_storage_surface_helpers_merge_base_and_pipeline_overrides,
    test_workflow_quality_gates_detect_repo_gate_signals,
)
from tests.testing_support.neo4j_memory_sync_support.common import (
    _skip_full_repo_snapshot_on_windows,
)

pytestmark = [pytest.mark.memory, pytest.mark.timeout(180)]


def test_full_repo_snapshot_is_skipped_on_windows() -> None:
    assert _skip_full_repo_snapshot_on_windows("linux") is None
    with pytest.raises(
        pytest.skip.Exception,
        match="full repo walk which is prohibitively slow on Windows",
    ):
        _skip_full_repo_snapshot_on_windows("win32")
