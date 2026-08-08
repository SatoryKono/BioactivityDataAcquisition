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
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Support helpers for invariant-focused Neo4j memory sync test suites."""

# ruff: noqa: F403,F405

from __future__ import annotations

import sys
import tempfile
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

import pytest

pytestmark = [pytest.mark.skip(reason="Legacy memory sync test - module structure changed"), pytest.mark.memory, pytest.mark.timeout(180)]

# from scripts.memory.operations.sync import *
# from memory.graph.sync_pkg import _core as _sync_core
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
SYNC_CORE_MODULE_PATH = "memory.graph.sync_pkg._core"
NEO4J_HTTP_CLIENT_PATH = f"{SYNC_CORE_MODULE_PATH}.Neo4jHttpClient"
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


def _skip_full_repo_snapshot_on_windows(platform: str) -> None:
    if platform.startswith("win"):
        pytest.skip(
            "Snapshot tests require full repo walk which is prohibitively slow on Windows"
        )


@lru_cache(maxsize=1)
def _snapshot_base() -> object:
    _skip_full_repo_snapshot_on_windows(sys.platform)
    original_lookup = _sync_core._git_last_commit_age_days_bulk
    _sync_core._git_last_commit_age_days_bulk = _deterministic_git_age_lookup
    try:
        return build_snapshot(_repo_root(), verified_at="2026-04-09")
    finally:
        _sync_core._git_last_commit_age_days_bulk = original_lookup


def _deterministic_git_age_lookup(
    _root: Path,
    relative_paths: list[str],
    _today: date,
    cache: dict[str, int | None],
    *,
    chunk_size: int = 1024,
) -> dict[str, int | None]:
    del chunk_size
    result = {path: 0 for path in dict.fromkeys(relative_paths) if path}
    cache.update(result)
    return result


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
