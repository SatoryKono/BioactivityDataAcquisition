"""Support helpers for invariant-focused Neo4j memory sync test suites."""

from __future__ import annotations

import io
import tempfile
from copy import deepcopy
from datetime import date
from functools import lru_cache
from pathlib import Path
from urllib import error

import pytest
from scripts.memory.sync import (
    DEFAULT_INGEST_WAVE,
    DEFAULT_LEGACY_PRUNE_LABELS,
    DEFAULT_MANAGED_BY,
    GraphNode,
    GraphRelation,
    GraphSnapshot,
    Neo4jHttpClient,
    NodeKey,
    _add_complexity_analysis_surfaces,
    _build_diff_entries,
    _critical_analysis_audit_issues,
    _delete_managed_wave_nodes_statement,
    _docs_drift_sources,
    _duplication_analysis_config,
    _ensure_targeted_apply_prerequisites,
    _family_for_path,
    _filtered_snapshot,
    _git_last_commit_age_days_bulk,
    _live_managed_node_counts,
    _live_managed_relation_counts,
    _load_memory_mapping,
    _memory_mapping_path,
    _merge_storage_layer_config,
    _missing_managed_anchor_keys,
    _node_statement,
    _normalization_evidence_statements,
    _normalize_docs_repo_reference,
    _prune_legacy_unmanaged_nodes_statement,
    _prune_stale_nodes_statement,
    _prune_stale_relations_statement,
    _relation_statement,
    _reset_managed_relations_statement,
    _storage_ref_from_output_path,
    _targeted_apply_external_anchor_keys,
    _targeted_apply_required_anchor_labels,
    _verify_expected_group_counts,
    _workflow_quality_gates,
    apply_normalization_evidence_only,
    build_audit_report,
    build_fast_analysis_audit_report,
    build_snapshot,
    derive_http_uri,
    main,
    resolve_neo4j_connection,
    snapshot_invariant_issues,
    sync_snapshot,
)

pytestmark = [pytest.mark.memory, pytest.mark.timeout(180)]
LEGACY_REPORT_PATH = str(Path(tempfile.gettempdir()) / "neo4j-memory-audit.json")


def _test_internal_http_uri(host: str, port: int) -> str:
    """Test-only helper for explicitly required unencrypted HTTP connections."""
    return f"http://{host}:{port}"  # NOSONAR # nosec B108


LOCALHOST_HTTP_URI = _test_internal_http_uri("localhost", 7474)
LOCALHOST_AUDIT_HTTP_URI = _test_internal_http_uri("localhost", 7475)
HOST_DOCKER_INTERNAL_HTTP_URI = _test_internal_http_uri("host.docker.internal", 7474)
HOST_DOCKER_INTERNAL_AUDIT_HTTP_URI = _test_internal_http_uri(
    "host.docker.internal", 7475
)
CHEMBL_ACTIVITY_CONFIG_PATH = "configs/entities/chembl/activity.yaml"
RUN_MANIFEST_LEDGER_DOC_PATH = "docs/04-reference/contracts/run-manifest-ledger.md"
RUN_MANIFEST_MODULE_PATH = "src/bioetl/domain/control_plane/run_manifest.py"
APPLICATION_CORE_DIR = "src/bioetl/application/core"
CHEMBL_CONFIG_DIR = "configs/entities/chembl"
TESTS_ARCHITECTURE_DIR = "tests/architecture"
ARCHITECTURE_DIAGRAMS_DIR = "docs/02-architecture/diagrams"
SCRIPTS_OPS_DIR = "scripts/ops"
GRAFANA_DASHBOARDS_DIR = "grafana/dashboards"
GITHUB_WORKFLOWS_DIR = ".github/workflows"
RECORD_NORMALIZATION_PROCESSOR_PATH = (
    "src/bioetl/application/core/record_normalization_processor.py"
)
ARCHITECTURE_DIAGRAMS_README_PATH = "docs/02-architecture/diagrams/README.md"
SCRIPTS_MEMORY_MAIN_PATH = "scripts/memory/__main__.py"
DIAGRAM_QUALITY_GATES_TEST_PATH = "tests/architecture/test_diagram_quality_gates.py"
BIOETL_RUNTIME_DASHBOARD_PATH = "grafana/dashboards/bioetl-runtime.json"
TESTS_WORKFLOW_PATH = ".github/workflows/tests.yml"
SILVER_CHEMBL_ACTIVITY = "silver/chembl/activity"
SILVER_CHEMBL_ACTIVITY_FIELD = "silver/chembl/activity::activity_id"
SILVER_COMPOSITE_ACTIVITY = "silver/composite/activity"
SILVER_COMPOSITE_ACTIVITY_FIELD = "silver/composite/activity::compound_name"
RUN_MANIFEST_STORAGE_PATH = "control/run_manifest/{manifest_id}.json"
EFFECTIVE_CONFIG_STORAGE_PATH = "control/effective_config/{artifact_id}.json"
LINEAGE_FRAGMENT_STORAGE_PATH = "control/lineage/fragments/{fragment_hash}.json"
ARCHITECTURE_DIAGRAMS_HUB = "architecture diagrams hub"
INTEGRATION_VCR_POLICY = "integration and VCR execution policy"
DIAGRAM_GOVERNANCE_POLICY = "diagram governance policy"
CHEMBL_ADAPTER_SURFACE = "bioetl.infrastructure.adapters.chembl"
CHEMBL_ADAPTER_IMPL_SURFACE = "bioetl.infrastructure.adapters.chembl.client"


REPO_ZONE_GITHUB = ".github"
CONTRACT_CHEMBL_ACTIVITY = "chembl.activity"
ARTIFACT_RUN_MANIFEST = "run_manifest::json"
ARTIFACT_EFFECTIVE_CONFIG = "effective_config_artifact::json"
ARTIFACT_LINEAGE = "lineage::fragment"
STATE_MANIFEST_CHAIN_2 = "manifest-chain-2::retry-window"
JOB_GOVERNANCE_PREFLIGHT = "tests::governance-preflight"
ACTION_UPLOAD_ARTIFACT = "actions/upload-artifact"
ARTIFACT_COVERAGE_DATA = "tests::coverage-data-${{ matrix.test-group.name }}"
CMD_BIOETL_RUN = "bioetl run"
CMD_MEMORY_SYNC = "scripts.memory sync"
EXEC_BIOETL_RUN = "uv run python -m bioetl run --pipeline"
EXEC_DIAGRAMS_LINT = "uv run python -m scripts.diagrams lint"
EXEC_DOCS_VERIFY = "uv run python -m scripts.docs verify"
EXEC_SCHEMA_VALIDATE = "uv run python -m scripts.schema validate-configs"
QUALITY_GATE_DIAGRAMS = "diagram quality gates"
JOB_TEST_MATRIX = "tests::test-matrix"
PATH_CHEMBL_ACTIVITY_PROFILE = (
    "src/bioetl/domain/normalization/profiles/chembl_activity.py"
)
GATE_CONFIG_VALIDATION = "config validation"
ARTIFACT_RUN_LEDGER = "run_ledger::jsonl"
STMT_RETURN_1 = "RETURN 1 AS ok"
NEO4J_HTTP_CLIENT_PATH = "scripts.memory.sync.Neo4jHttpClient"
PATH_COMPOSITE_EXAMPLE = "src/bioetl/application/composite/example.py"
CLASS_PKG_EXAMPLE = "pkg.Example"
COMPLEXITY_PKG_EXAMPLE = "class_surface:pkg.Example"
CONTEXT_COMPLEXITY_PREREQ = (
    "complexity-layer targeted sync prerequisite anchor node check"
)
PATH_PKG_EXAMPLE = "src/pkg/example.py"
CONTEXT_FAST_AUDIT_LABEL = "fast audit label summary"
PATH_SRC_A = "src/a.py"
PATH_SRC_B = "src/b.py"
PATH_SRC_C = "src/c.py"
FAMILY_APP_COMPOSITE = "application/composite"


class _TargetedApplyPrereqStubClient:
    def query(
        self,
        _statement: str,
        parameters: dict[str, object] | None = None,
        *,
        context: str | None = None,
    ) -> list[dict[str, object]]:
        assert parameters is not None
        if context == "complexity-layer targeted sync prerequisite anchor check":
            labels = parameters["labels"]
            assert isinstance(labels, list)
            return [{"label": label, "count": 0} for label in labels]
        if context == CONTEXT_COMPLEXITY_PREREQ:
            anchors = parameters["anchors"]
            assert isinstance(anchors, list)
            return [
                {
                    "label": anchor["label"],
                    "name": anchor["name"],
                    "count": 0,
                }
                for anchor in anchors
            ]
        raise AssertionError(f"Unexpected context: {context}")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def _snapshot_base() -> object:
    return build_snapshot(_repo_root(), verified_at="2026-04-09")


def _clone_snapshot(snapshot: GraphSnapshot) -> GraphSnapshot:
    cloned = GraphSnapshot()
    cloned.nodes = {
        key: GraphNode(key=node.key, properties=deepcopy(node.properties))
        for key, node in snapshot.nodes.items()
    }
    cloned.relations = {
        key: GraphRelation(
            source=relation.source,
            relation_type=relation.relation_type,
            target=relation.target,
            properties=deepcopy(relation.properties),
        )
        for key, relation in snapshot.relations.items()
    }
    return cloned


def _snapshot() -> tuple[Path, object]:
    root = _repo_root()
    return root, _clone_snapshot(_snapshot_base())


__all__ = [name for name in globals() if not name.startswith("__")]
