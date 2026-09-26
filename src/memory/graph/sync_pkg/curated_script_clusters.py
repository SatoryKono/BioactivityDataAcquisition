"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.default_batch_size import (
    DEFAULT_LEGACY_REPORT_PATH,
    GATE_CONFIG_VALIDATION,
    GATE_DIAGRAM_QUALITY,
    GATE_DOCS_VERIFICATION,
)
from memory.graph.sync_pkg.graph_contexts import DuplicateFamilyConfig
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.score_family import _family_for_path

__all__ = [
    "CURATED_SCRIPT_CLUSTERS",
    "_analysis_family_for_source_path",
    "_analysis_keys_to_scan",
    "_analysis_package_name",
]

CURATED_SCRIPT_CLUSTERS: tuple[dict[str, object], ...] = (
    {
        "readme_path": "scripts/diagrams/README.md",
        "readme_summary": "Diagram tooling catalog covering lint, render, publication, and nightly validation workflows.",
        "entrypoint_path": "scripts/diagrams/__main__.py",
        "entrypoint_summary": "Unified Python entrypoint for diagram lint, check, fix, render, and nightly suite commands.",
        "execution_paths": (
            {
                "name": "python -m scripts.diagrams",
                "platform": "cross_platform",
                "summary": "Unified local entrypoint for diagram tooling commands.",
            },
            {
                "name": "uv run python -m scripts.diagrams lint",
                "platform": "ci_uv",
                "summary": "Canonical diagram lint path for Mermaid source validation.",
                "gate": GATE_DIAGRAM_QUALITY,
            },
            {
                "name": "uv run python -m scripts.diagrams check-quality-gates",
                "platform": "ci_uv",
                "summary": "Canonical diagram regression gate for tracked Mermaid and publication invariants.",
                "gate": GATE_DIAGRAM_QUALITY,
            },
        ),
    },
    {
        "readme_path": "scripts/docs/README.md",
        "readme_summary": "Documentation tooling catalog covering verification, drift checks, matrix generation, and link maintenance.",
        "entrypoint_path": "scripts/docs/__main__.py",
        "entrypoint_summary": "Unified Python entrypoint for documentation verification, drift, and generated report workflows.",
        "execution_paths": (
            {
                "name": "python -m scripts.docs",
                "platform": "cross_platform",
                "summary": "Unified local entrypoint for documentation tooling commands.",
            },
            {
                "name": "uv run python -m scripts.docs verify",
                "platform": "ci_uv",
                "summary": "Canonical end-to-end docs verification chain.",
                "gate": GATE_DOCS_VERIFICATION,
            },
            {
                "name": "uv run python -m scripts.docs check-links --links --specs --configs",
                "platform": "ci_uv",
                "summary": "Canonical docs link/spec/config verification path.",
                "gate": GATE_DOCS_VERIFICATION,
            },
            {
                "name": "uv run python -m scripts.docs generate-pipeline-normalization-matrix --check",
                "platform": "ci_uv",
                "summary": "Canonical drift check for the published pipeline normalization matrix artifact.",
            },
        ),
    },
    {
        "readme_path": "scripts/engineering/qa/README.md",
        "readme_summary": "QA tooling catalog covering architecture checks, debt telemetry, and normalization inventory reporting.",
        "entrypoint_path": "scripts/engineering/qa/__main__.py",
        "entrypoint_summary": "Unified Python entrypoint for QA checks and normalization inventory reporting workflows.",
        "execution_paths": (
            {
                "name": "python -m scripts.engineering.qa",
                "platform": "cross_platform",
                "summary": "Unified local entrypoint for QA tooling commands.",
            },
            {
                "name": "python -m scripts.engineering.qa report-normalization-fallback-inventory --limit 20",
                "platform": "cross_platform",
                "summary": "Canonical report-only inventory path for current fallback normalization debt.",
            },
        ),
    },
    {
        "readme_path": "scripts/schema/README.md",
        "readme_summary": "Schema and config tooling catalog covering validation, invariants, and contract generation.",
        "entrypoint_path": "scripts/schema/__main__.py",
        "entrypoint_summary": "Unified Python entrypoint for config validation, schema artifact generation, and contract audits.",
        "execution_paths": (
            {
                "name": "python -m scripts.schema",
                "platform": "cross_platform",
                "summary": "Unified local entrypoint for schema and config tooling commands.",
            },
            {
                "name": "uv run python -m scripts.schema validate-configs",
                "platform": "ci_uv",
                "summary": "Maintained JSON Schema validation path for unified pipeline configs.",
                "gate": GATE_CONFIG_VALIDATION,
            },
            {
                "name": "uv run python -m scripts.schema check-invariants",
                "platform": "ci_uv",
                "summary": "Canonical config invariant check for naming, auth, keys, and config CI policy.",
                "gate": GATE_CONFIG_VALIDATION,
            },
        ),
    },
    {
        "readme_path": "scripts/memory/README.md",
        "readme_summary": "Neo4j project-memory tooling, MCP wrappers, and WSL bootstrap guidance.",
        "entrypoint_path": "scripts/memory/__main__.py",
        "entrypoint_summary": "Unified Python entrypoint for deterministic Neo4j memory sync, query, and smoke tooling.",
        "execution_paths": (
            {
                "name": "python -m scripts.memory",
                "platform": "cross_platform",
                "summary": "Unified local entrypoint for project-memory helper commands.",
            },
            {
                "name": f"python -m scripts.memory sync --report {DEFAULT_LEGACY_REPORT_PATH}",
                "platform": "cross_platform",
                "summary": "Canonical audit/report path for the deterministic Neo4j repo graph.",
            },
            {
                "name": "python -m scripts.memory sync --apply",
                "platform": "cross_platform",
                "summary": "Canonical apply path for syncing the deterministic Neo4j repo graph.",
            },
        ),
    },
)


def _analysis_family_for_source_path(
    relative_path: str,
    duplication_config: dict[str, object],
    family_cache: dict[str, DuplicateFamilyConfig | None],
) -> DuplicateFamilyConfig | None:
    if relative_path not in family_cache:
        family_cache[relative_path] = _family_for_path(
            relative_path, duplication_config
        )
    return family_cache[relative_path]


def _analysis_package_name(snapshot: GraphSnapshot, module_key: NodeKey) -> str | None:
    module_node = snapshot.nodes.get(module_key)
    if module_node is None:
        return None
    package_raw = module_node.properties.get("family_name")
    if isinstance(package_raw, str) and package_raw:
        return package_raw
    return None


def _analysis_keys_to_scan(
    snapshot: GraphSnapshot,
    surface_key: NodeKey,
    module_key: NodeKey,
) -> set[NodeKey]:
    keys_to_scan = {surface_key, module_key}
    package_name = _analysis_package_name(snapshot, module_key)
    if package_name is not None:
        keys_to_scan.add(NodeKey("package_family", package_name))
    return keys_to_scan
