"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import AnalysisLabelSets, NodeKey
from memory.graph.sync_pkg.curated_script_clusters import _analysis_keys_to_scan
from memory.graph.sync_pkg.default_batch_size import (
    GATE_CONFIG_VALIDATION,
    GATE_DIAGRAM_QUALITY,
    GATE_DOCS_VERIFICATION,
    GATE_MYPY_STRICT,
    GATE_NEO4J_ONTOLOGY_INVARIANTS,
    GATE_PRETEST_GUARDRAILS,
)
from memory.graph.sync_pkg.graph_contexts import AnalysisAnchors, SurfaceRelationIndexes
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "CURATED_EXECUTION_PATHS",
    "CURATED_QUALITY_GATES",
    "_anchor_bucket_for_label",
    "_collect_analysis_anchor_nodes",
]

CURATED_QUALITY_GATES: tuple[dict[str, object], ...] = (
    {
        "name": "pytest",
        "summary": "Primary test runner for local and CI feedback.",
    },
    {
        "name": GATE_MYPY_STRICT,
        "summary": "Static typing gate for public surfaces and repo strictness.",
    },
    {
        "name": GATE_DOCS_VERIFICATION,
        "summary": "Published docs verification chain via scripts.docs verify and strict MkDocs build.",
    },
    {
        "name": GATE_CONFIG_VALIDATION,
        "summary": "Schema/config validation path for supported configs and invariants.",
    },
    {
        "name": GATE_PRETEST_GUARDRAILS,
        "summary": "Broad preflight for cleanup, docs, inventory, and architecture drift.",
    },
    {
        "name": GATE_NEO4J_ONTOLOGY_INVARIANTS,
        "summary": "Repo-backed ontology validation for deterministic Neo4j memory graph structure and invariants.",
    },
    {
        "name": GATE_DIAGRAM_QUALITY,
        "summary": "Diagram lint, syntax validation, artifact checks, visual smoke, and nightly regression gates for Mermaid publication surfaces.",
    },
)
CURATED_EXECUTION_PATHS: tuple[dict[str, object], ...] = (
    {
        "name": "uv run python -m bioetl run --pipeline",
        "platform": "ci_uv",
        "summary": "Canonical CI and single-OS pipeline runtime path.",
    },
    {
        "name": '"${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python" -m bioetl run --pipeline',
        "platform": "wsl",
        "summary": "WSL/Linux pipeline runtime path for the stable WSL virtualenv.",
    },
    {
        "name": ".\\.venv-win\\Scripts\\python.exe -m bioetl run --pipeline",
        "platform": "windows",
        "summary": "PowerShell pipeline runtime path for .venv-win.",
    },
    {
        "name": "uv run python -m pytest",
        "platform": "ci_uv",
        "summary": "Canonical CI and single-OS pytest execution path.",
        "gate": "pytest",
    },
    {
        "name": "bash scripts/engineering/dev/run_pytest.sh",
        "platform": "wsl",
        "summary": "WSL/Linux wrapper with default coverage flags and plugin bootstrap.",
        "gate": "pytest",
        "script_path": "scripts/engineering/dev/run_pytest.sh",
    },
    {
        "name": ".\\scripts\\dev\\run_pytest.ps1",
        "platform": "windows",
        "summary": "PowerShell wrapper with default coverage flags for .venv-win.",
        "gate": "pytest",
        "script_path": "scripts/engineering/dev/run_pytest.ps1",
    },
    {
        "name": "uv run python -m mypy --strict src/bioetl/",
        "platform": "ci_uv",
        "summary": "Canonical CI and single-OS strict typing path.",
        "gate": GATE_MYPY_STRICT,
    },
    {
        "name": "bash scripts/engineering/dev/run_mypy.sh",
        "platform": "wsl",
        "summary": "WSL/Linux mypy wrapper for the stable WSL virtualenv.",
        "gate": GATE_MYPY_STRICT,
        "script_path": "scripts/engineering/dev/run_mypy.sh",
    },
    {
        "name": ".\\scripts\\dev\\run_mypy.ps1",
        "platform": "windows",
        "summary": "PowerShell mypy wrapper for .venv-win.",
        "gate": GATE_MYPY_STRICT,
        "script_path": "scripts/engineering/dev/run_mypy.ps1",
    },
    {
        "name": "uv run python -m scripts.docs verify",
        "platform": "ci_uv",
        "summary": "Canonical end-to-end published docs verification path.",
        "gate": GATE_DOCS_VERIFICATION,
        "script_path": "scripts/docs/checks/verify.py",
    },
    {
        "name": "uv run python -m scripts.schema validate-configs",
        "platform": "ci_uv",
        "summary": "Canonical config validation path for supported configs.",
        "gate": GATE_CONFIG_VALIDATION,
        "script_path": "scripts/schema/validation/validate_pipeline_configs.py",
    },
    {
        "name": "bash scripts/engineering/dev/pretest_guardrails.sh",
        "platform": "wsl",
        "summary": "WSL pretest guardrail runner before broad pytest waves.",
        "gate": GATE_PRETEST_GUARDRAILS,
        "script_path": "scripts/engineering/dev/pretest_guardrails.sh",
    },
)


def _anchor_bucket_for_label(label: str, label_sets: AnalysisLabelSets) -> str | None:
    if label in label_sets.runtime_labels:
        return "runtime"
    if label in label_sets.config_labels:
        return "config"
    if label in label_sets.doc_labels:
        return "docs"
    if label in label_sets.test_labels:
        return "tests"
    return None


def _collect_analysis_anchor_nodes(
    snapshot: GraphSnapshot,
    indexes: SurfaceRelationIndexes,
    surface_key: NodeKey,
    module_key: NodeKey,
    label_sets: AnalysisLabelSets,
) -> AnalysisAnchors:
    buckets: dict[str, set[NodeKey]] = {
        "runtime": set(),
        "config": set(),
        "docs": set(),
        "tests": set(),
    }
    for key in _analysis_keys_to_scan(snapshot, surface_key, module_key):
        for relation in [
            *indexes.incoming.get(key, ()),
            *indexes.outgoing.get(key, ()),
        ]:
            if relation.relation_type in label_sets.ignored_relation_types:
                continue
            other = relation.source if relation.target == key else relation.target
            bucket = _anchor_bucket_for_label(other.label, label_sets)
            if bucket is not None:
                buckets[bucket].add(other)
    return AnalysisAnchors(
        runtime=tuple(
            sorted(buckets["runtime"], key=lambda item: (item.label, item.name))
        ),
        config=tuple(
            sorted(buckets["config"], key=lambda item: (item.label, item.name))
        ),
        docs=tuple(sorted(buckets["docs"], key=lambda item: (item.label, item.name))),
        tests=tuple(sorted(buckets["tests"], key=lambda item: (item.label, item.name))),
    )
