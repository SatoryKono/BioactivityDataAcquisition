"""Post-build invariant checks for Neo4j memory snapshots."""

from __future__ import annotations

import pytest

from tests.testing_support.neo4j_memory_sync import (  # noqa: F401
    test_snapshot_invariants_are_clean,
    test_snapshot_invariants_require_control_plane_artifact_links,
    test_snapshot_invariants_require_docs_to_code_drift_edges,
    test_snapshot_invariants_require_run_instance_artifact_links,
    test_snapshot_invariants_require_runtime_evidence_support_links,
    test_snapshot_invariants_require_runtime_state_links,
    test_snapshot_invariants_require_schema_field_links,
    test_snapshot_invariants_require_workflow_job_parent_links,
)

pytestmark = pytest.mark.memory
