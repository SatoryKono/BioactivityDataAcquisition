#!/usr/bin/env python3
"""Build and optionally sync a deterministic BioETL knowledge graph into Neo4j."""

from __future__ import annotations

import argparse
import ast
import base64
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import TypeAlias, TypeVar
from urllib import error, parse, request

import yaml

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
T = TypeVar("T")

DEFAULT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BATCH_SIZE = 100
DEFAULT_INGEST_WAVE = "repo_sync_v1"
DEFAULT_MANAGED_BY = "neo4j_memory_sync"
DEFAULT_LEGACY_PRUNE_LABELS: tuple[str, ...] = (
    "project",
    "doc_source_surface",
    "doc_artifact",
    "decision",
    "risk",
    "policy_surface",
    "layer_family",
    "package_family",
    "module_surface",
    "port_surface",
    "adapter_surface",
    "pipeline_surface",
    "contract_surface",
    "alert_surface",
    "provider_surface",
    "entity_config",
    "composite_config",
    "config_artifact",
    "dashboard_surface",
    "quality_gate",
    "script_surface",
    "execution_path",
    "test_surface",
    "test_artifact",
)
KNOWN_LAYERS = ("domain", "application", "infrastructure", "composition", "interfaces")
TEST_SURFACES: dict[str, str] = {
    "unit": "unit tests",
    "integration": "integration tests",
    "e2e": "e2e tests",
    "architecture": "architecture tests",
    "contract": "contract tests",
    "benchmarks": "benchmarks",
}
CURATED_DOC_SOURCES: tuple[dict[str, str], ...] = (
    {
        "name": "Project Navigator",
        "path": "docs/00-project/00-map.md",
        "summary": "Primary project navigator and active entrypoint map.",
    },
    {
        "name": "RULES.md",
        "path": "docs/00-project/RULES.md",
        "summary": "Canonical governance and requirements surface for the project.",
    },
    {
        "name": "agent memory entry point",
        "path": "docs/00-project/ai/memory/agent-memory.md",
        "summary": "Human-oriented project memory entry point for AI runtimes.",
    },
    {
        "name": "testing guide",
        "path": "docs/03-guides/testing.md",
        "summary": "Published testing strategy guide.",
    },
    {
        "name": "dashboard extension guide",
        "path": "docs/03-guides/dashboards/dashboard-extension-llm.md",
        "summary": "Canonical LLM playbook for shipped Grafana dashboards.",
    },
    {
        "name": "docs verification guide",
        "path": "docs/03-guides/docs-verification.md",
        "summary": "Published workflow for docs verification and drift control.",
    },
    {
        "name": "package topology evidence summary",
        "path": "docs/reports/evidence/project-package-topology/SUMMARY.md",
        "summary": "Repo-only topology calibration evidence for package families.",
    },
    {
        "name": "governance decisions summary",
        "path": "docs/reports/evidence/governance-signals/04-decisions/SUMMARY.md",
        "summary": "Accepted governance decisions and risks.",
    },
    {
        "name": "grafana dashboards json",
        "path": "grafana/dashboards",
        "summary": "Factual source of truth for shipped dashboard behavior.",
    },
)
CURATED_QUALITY_GATES: tuple[dict[str, object], ...] = (
    {
        "name": "pytest",
        "summary": "Primary test runner for local and CI feedback.",
    },
    {
        "name": "mypy --strict",
        "summary": "Static typing gate for public surfaces and repo strictness.",
    },
    {
        "name": "docs verification",
        "summary": "Published docs verification chain via scripts.docs verify and strict MkDocs build.",
    },
    {
        "name": "config validation",
        "summary": "Schema/config validation path for supported configs and invariants.",
    },
    {
        "name": "pretest guardrails",
        "summary": "Broad preflight for cleanup, docs, inventory, and architecture drift.",
    },
)
CURATED_POLICY_SURFACES: tuple[dict[str, object], ...] = (
    {
        "name": "hexagonal import matrix",
        "summary": (
            "Import boundaries are strict: domain imports only domain, application imports domain plus itself, "
            "infrastructure imports domain plus itself, composition can wire all layers except interfaces, "
            "and interfaces can depend on all layers."
        ),
        "source_path": "docs/00-project/RULES.md",
        "artifact_label": "doc_artifact",
        "governs_layers": KNOWN_LAYERS,
    },
    {
        "name": "medallion storage contract",
        "summary": (
            "BioETL follows Bronze to Silver to Gold medallion flow. Silver must use Delta Lake rather than raw "
            "Parquet, and Pandera remains the schema validation standard across dataframe boundaries."
        ),
        "source_path": "docs/00-project/RULES.md",
        "artifact_label": "doc_artifact",
    },
    {
        "name": "provider support matrix",
        "summary": (
            "Primary provider set includes ChEMBL, PubChem, PubMed, Semantic Scholar, CrossRef, OpenAlex, "
            "and UniProt for bioactivity acquisition and enrichment workflows."
        ),
        "source_path": "docs/00-project/RULES.md",
        "artifact_label": "doc_artifact",
    },
    {
        "name": "hexagonal package layout",
        "summary": (
            "Source layout is organized into domain, application, infrastructure, composition, and interfaces. "
            "Domain stays pure, composition owns wiring, interfaces expose CLI entrypoints, and architecture tests "
            "enforce cross-layer boundaries."
        ),
        "source_path": "docs/00-project/RULES.md",
        "artifact_label": "doc_artifact",
        "governs_layers": KNOWN_LAYERS,
    },
    {
        "name": "pipeline assembly model",
        "summary": (
            "BioETL assembles provider ingestion, transformation, schema validation, and medallion storage flow "
            "through composition-layer factories and config-driven pipeline definitions rather than hard-coded "
            "business wiring inside domain or application layers."
        ),
        "source_path": "docs/00-project/RULES.md",
        "artifact_label": "doc_artifact",
        "governs_layers": ("composition", "application"),
    },
    {
        "name": "observability surface model",
        "summary": (
            "Operational visibility is centered on Grafana dashboards backed primarily by Prometheus metrics, "
            "with dashboard JSON in grafana/dashboards as the factual source of shipped behavior and dedicated "
            "guides for dashboard extension work."
        ),
        "source_path": "docs/03-guides/dashboards/dashboard-extension-llm.md",
        "artifact_label": "doc_artifact",
        "governs_docs": ("grafana dashboards json",),
    },
    {
        "name": "testing strategy matrix",
        "summary": (
            "Testing is intentionally stratified across unit, integration, e2e, architecture, contract, "
            "and optional benchmark surfaces. ADR-042 and the published testing guide define when each "
            "surface is appropriate and keep scope explicit."
        ),
        "source_path": "docs/02-architecture/decisions/ADR-042-testing-strategy-matrix.md",
        "artifact_label": "doc_artifact",
        "governs_test_surfaces": ("unit tests", "integration tests", "e2e tests", "architecture tests", "contract tests"),
    },
    {
        "name": "quality gate stack",
        "summary": (
            "The main repository gate stack combines pytest, mypy --strict, VCR execution policy, docs verification, "
            "config validation, and pretest guardrails."
        ),
        "source_path": "docs/03-guides/testing.md",
        "artifact_label": "doc_artifact",
        "governs_quality_gates": ("pytest", "mypy --strict", "docs verification", "config validation", "pretest guardrails"),
    },
    {
        "name": "VCR replay discipline",
        "summary": (
            "Integration and e2e work is replay-first. VCR cassettes are refreshed in a targeted way rather than "
            "broad uncontrolled rewrites, and machine-readable policy keeps the replay contract synchronized with the test matrix."
        ),
        "source_path": "docs/03-guides/testing.md",
        "artifact_label": "doc_artifact",
        "governs_test_surfaces": ("integration tests", "e2e tests"),
    },
    {
        "name": "target enrichment bridge",
        "summary": (
            "Target enrichment crosses provider boundaries: ChEMBL supplies target-centric seed records while UniProt "
            "contributes reviewed protein metadata and an idmapping surface that translates ChEMBL target identifiers into UniProt accessions."
        ),
        "source_path": "configs/providers/uniprot.yaml",
        "artifact_label": "config_artifact",
    },
    {
        "name": "publication enrichment mesh",
        "summary": (
            "Publication enrichment is intentionally multi-provider. ChEMBL contributes source publication references, "
            "while PubMed, CrossRef, OpenAlex, and Semantic Scholar enrich publication metadata through PMID, DOI, title, "
            "and citation-oriented resolution paths."
        ),
        "source_path": "configs/quality/test_matrix.yaml",
        "artifact_label": "config_artifact",
    },
    {
        "name": "integration and VCR execution policy",
        "summary": "Tracked machine-readable policy for integration and VCR execution scope, replay modes, and suite inventory.",
        "source_path": "configs/quality/integration_vcr_policy.yaml",
        "artifact_label": "config_artifact",
        "governs_test_surfaces": ("integration tests", "e2e tests"),
        "governs_quality_gates": ("pytest",),
    },
    {
        "name": "docs verification guide",
        "summary": "Published workflow defining the verification path for docs surface and repo-only supporting material boundaries.",
        "source_path": "docs/03-guides/docs-verification.md",
        "artifact_label": "doc_artifact",
        "governs_quality_gates": ("docs verification",),
    },
    {
        "name": "published docs boundary",
        "summary": "Published docs in docs/00-05 and README define active supported behavior; repo-only material must not override them.",
        "source_path": "docs/03-guides/docs-verification.md",
        "artifact_label": "doc_artifact",
    },
    {
        "name": "default VCR record mode",
        "summary": "CI defaults to none; local defaults to once unless explicitly overridden.",
        "source_path": "configs/quality/integration_vcr_policy.yaml",
        "artifact_label": "config_artifact",
        "governs_test_surfaces": ("integration tests", "e2e tests"),
    },
    {
        "name": "targeted cassette refresh",
        "summary": "Targeted VCR refresh uses new_episodes; broad rewrites are not the supported default path.",
        "source_path": "configs/quality/integration_vcr_policy.yaml",
        "artifact_label": "config_artifact",
        "governs_test_surfaces": ("integration tests", "e2e tests"),
    },
)
CURATED_EXECUTION_PATHS: tuple[dict[str, object], ...] = (
    {
        "name": "uv run python -m pytest",
        "platform": "ci_uv",
        "summary": "Canonical CI and single-OS pytest execution path.",
        "gate": "pytest",
    },
    {
        "name": "bash scripts/dev/run_pytest.sh",
        "platform": "wsl",
        "summary": "WSL/Linux wrapper with default coverage flags and plugin bootstrap.",
        "gate": "pytest",
        "script_path": "scripts/dev/run_pytest.sh",
    },
    {
        "name": ".\\scripts\\dev\\run_pytest.ps1",
        "platform": "windows",
        "summary": "PowerShell wrapper with default coverage flags for .venv-win.",
        "gate": "pytest",
        "script_path": "scripts/dev/run_pytest.ps1",
    },
    {
        "name": "uv run python -m mypy --strict src/bioetl/",
        "platform": "ci_uv",
        "summary": "Canonical CI and single-OS strict typing path.",
        "gate": "mypy --strict",
    },
    {
        "name": "bash scripts/dev/run_mypy.sh",
        "platform": "wsl",
        "summary": "WSL/Linux mypy wrapper for the stable WSL virtualenv.",
        "gate": "mypy --strict",
        "script_path": "scripts/dev/run_mypy.sh",
    },
    {
        "name": ".\\scripts\\dev\\run_mypy.ps1",
        "platform": "windows",
        "summary": "PowerShell mypy wrapper for .venv-win.",
        "gate": "mypy --strict",
        "script_path": "scripts/dev/run_mypy.ps1",
    },
    {
        "name": "uv run python -m scripts.docs verify",
        "platform": "ci_uv",
        "summary": "Canonical end-to-end published docs verification path.",
        "gate": "docs verification",
        "script_path": "scripts/docs/verify_docs.py",
    },
    {
        "name": "uv run python -m scripts.schema validate-configs",
        "platform": "ci_uv",
        "summary": "Canonical config validation path for supported configs.",
        "gate": "config validation",
        "script_path": "scripts/schema/validate_configs.py",
    },
    {
        "name": "bash scripts/dev/pretest_guardrails.sh",
        "platform": "wsl",
        "summary": "WSL pretest guardrail runner before broad pytest waves.",
        "gate": "pretest guardrails",
        "script_path": "scripts/dev/pretest_guardrails.sh",
    },
)


@dataclass(frozen=True)
class NodeKey:
    label: str
    name: str


@dataclass
class GraphNode:
    key: NodeKey
    properties: dict[str, JsonValue] = field(default_factory=dict)


@dataclass
class GraphRelation:
    source: NodeKey
    relation_type: str
    target: NodeKey
    properties: dict[str, JsonValue] = field(default_factory=dict)


@dataclass
class GraphSnapshot:
    nodes: dict[NodeKey, GraphNode] = field(default_factory=dict)
    relations: dict[tuple[NodeKey, str, NodeKey], GraphRelation] = field(default_factory=dict)

    def add_node(self, label: str, name: str, **properties: JsonValue) -> NodeKey:
        key = NodeKey(label=label, name=name)
        if key not in self.nodes:
            self.nodes[key] = GraphNode(key=key, properties={})
        for prop_name, prop_value in properties.items():
            if prop_value is None:
                continue
            self.nodes[key].properties[prop_name] = prop_value
        return key

    def add_relation(
        self,
        source: NodeKey,
        relation_type: str,
        target: NodeKey,
        **properties: JsonValue,
    ) -> None:
        key = (source, relation_type, target)
        if key not in self.relations:
            self.relations[key] = GraphRelation(
                source=source,
                relation_type=relation_type,
                target=target,
                properties={},
            )
        for prop_name, prop_value in properties.items():
            if prop_value is None:
                continue
            self.relations[key].properties[prop_name] = prop_value

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "nodes": [
                {
                    "label": node.key.label,
                    "name": node.key.name,
                    "properties": node.properties,
                }
                for node in sorted(self.nodes.values(), key=lambda item: (item.key.label, item.key.name))
            ],
            "relations": [
                {
                    "source": {
                        "label": relation.source.label,
                        "name": relation.source.name,
                    },
                    "type": relation.relation_type,
                    "target": {
                        "label": relation.target.label,
                        "name": relation.target.name,
                    },
                    "properties": relation.properties,
                }
                for relation in sorted(
                    self.relations.values(),
                    key=lambda item: (
                        item.source.label,
                        item.source.name,
                        item.relation_type,
                        item.target.label,
                        item.target.name,
                    ),
                )
            ],
        }

    def stats(self) -> dict[str, object]:
        label_counts: dict[str, int] = {}
        relation_counts: dict[str, int] = {}
        for node in self.nodes.values():
            label_counts[node.key.label] = label_counts.get(node.key.label, 0) + 1
        for relation in self.relations.values():
            relation_counts[relation.relation_type] = relation_counts.get(relation.relation_type, 0) + 1
        return {
            "node_count": len(self.nodes),
            "relation_count": len(self.relations),
            "labels": label_counts,
            "relation_types": relation_counts,
        }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and optionally sync a deterministic BioETL graph into Neo4j.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="Project root directory.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the generated graph into Neo4j.",
    )
    parser.add_argument(
        "--export",
        type=Path,
        help="Write the generated graph snapshot as JSON.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help=(
            "Write an audit report as JSON. "
            "The report includes snapshot stats, live managed/unmanaged summaries, "
            "label and relation diffs, and orphan summaries."
        ),
    )
    parser.add_argument(
        "--http-uri",
        type=str,
        help="Explicit Neo4j HTTP endpoint, e.g. http://localhost:7474.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Maximum statements per Neo4j commit request.",
    )
    parser.add_argument(
        "--prune-stale",
        action="store_true",
        help=(
            "Delete stale repo-derived nodes after sync. "
            "This only targets the current ingest wave and resets managed relations "
            "between repo-managed nodes before recreating them."
        ),
    )
    parser.add_argument(
        "--full-reset-managed-wave",
        action="store_true",
        help=(
            "Delete the entire current managed ingest wave before rebuilding it. "
            "This removes all repo-managed nodes for the current wave and any relations "
            "attached to them, then recreates the wave from the current repository state."
        ),
    )
    parser.add_argument(
        "--prune-legacy-unmanaged",
        action="store_true",
        help=(
            "Delete unmanaged legacy nodes for repo-derived labels after sync. "
            "This is intended to converge the repo graph to managed-only state for "
            "labels now owned by deterministic sync, while leaving unrelated labels "
            "such as MemoryEntity untouched."
        ),
    )
    return parser


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_yaml(path: Path) -> dict[str, object]:
    loaded = yaml.safe_load(_read_text(path))
    if isinstance(loaded, dict):
        return loaded
    return {}


def _read_json(path: Path) -> dict[str, object]:
    loaded = json.loads(_read_text(path))
    if isinstance(loaded, dict):
        return loaded
    return {}


def _rel_path(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _module_dotted_name(relative_path: str) -> str:
    without_suffix = relative_path.removesuffix(".py")
    return without_suffix.replace("/", ".")


def _python_surface_name(relative_path: str) -> str:
    if relative_path.endswith("/__init__.py"):
        dotted = relative_path.removesuffix("/__init__.py").replace("/", ".")
    else:
        dotted = _module_dotted_name(relative_path)
    return dotted.removeprefix("src.")


def _is_ignored_repo_path(path: Path) -> bool:
    return "__pycache__" in path.parts


def _resolve_repo_path(root: Path, base_path: Path, raw_path: str) -> Path | None:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = (base_path.parent / candidate).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    if candidate.exists():
        return candidate
    return None


def _imported_port_surfaces(path: Path) -> set[str]:
    if not path.is_file() or path.suffix != ".py":
        return set()
    try:
        tree = ast.parse(_read_text(path), filename=str(path))
    except SyntaxError:
        return set()

    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("bioetl.domain.ports"):
                    imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.module.startswith("bioetl.domain.ports"):
                imported.add(node.module)
    return imported


def _runtime_dimensions(*parts: str) -> set[str]:
    combined = " ".join(parts)
    dimensions = set()
    for dim in (
        "pipeline",
        "provider",
        "entity",
        "layer",
        "run_type",
        "stage",
        "table",
        "metric",
        "anomaly_type",
        "event_type",
        "store",
        "operation",
        "ref_type",
    ):
        if re.search(rf"\b{dim}\b", combined):
            dimensions.add(dim)
    return dimensions


def _normalize_env_value(raw: str) -> str:
    return raw.strip().strip('"').strip("'")


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    loaded: dict[str, str] = {}
    for raw_line in _read_text(path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        loaded[name.strip()] = _normalize_env_value(value)
    return loaded


def load_repo_env(root: Path) -> dict[str, str]:
    env = _read_env_file(root / ".env")
    env.update(_read_env_file(root / ".env.local"))
    shell_env = {key: value for key, value in os.environ.items() if value}
    env.update(shell_env)
    return env


def _parse_auth_pair(raw_auth: str | None) -> tuple[str | None, str | None]:
    if not raw_auth or "/" not in raw_auth:
        return None, None
    username, password = raw_auth.split("/", 1)
    return username or None, password or None


def resolve_neo4j_connection(root: Path, explicit_http_uri: str | None) -> tuple[str, str, str, str]:
    env = load_repo_env(root)
    bolt_uri = env.get("NEO4J_URI", "bolt://localhost:7687")
    username = env.get("NEO4J_USERNAME") or env.get("NEO4J_AUTH_USERNAME")
    password = env.get("NEO4J_PASSWORD") or env.get("NEO4J_AUTH_PASSWORD")
    database = env.get("NEO4J_DATABASE", "neo4j")
    auth_username, auth_password = _parse_auth_pair(env.get("NEO4J_AUTH"))
    username = username or auth_username or "neo4j"
    password = password or auth_password or "bioetl_secure_password"
    http_uri = explicit_http_uri or env.get("NEO4J_HTTP_URI") or derive_http_uri(bolt_uri)
    return http_uri.rstrip("/"), username, password, database


def derive_http_uri(neo4j_uri: str) -> str:
    parsed = parse.urlparse(neo4j_uri)
    if parsed.scheme in {"http", "https"}:
        return f"{parsed.scheme}://{parsed.hostname}:{parsed.port or (443 if parsed.scheme == 'https' else 80)}"
    scheme = "https" if parsed.scheme in {"neo4j+s", "bolt+s"} else "http"
    host = parsed.hostname or "localhost"
    return f"{scheme}://{host}:7474"


def build_snapshot(root: Path, verified_at: str | None = None) -> GraphSnapshot:
    snapshot = GraphSnapshot()
    today = verified_at or date.today().isoformat()
    project = snapshot.add_node(
        "project",
        "BioETL",
        summary="Python ETL framework for bioactivity data acquisition.",
        source_path="docs/00-project/ai/memory/agent-memory.md",
        source_kind="memory_entrypoint",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    _add_curated_docs(snapshot, root, project, today)
    _add_decisions_and_risks(snapshot, root, project, today)
    _add_layer_topology(snapshot, root, project, today)
    _add_provider_and_config_graph(snapshot, root, project, today)
    _add_dashboard_graph(snapshot, root, project, today)
    _add_quality_and_scripts(snapshot, root, project, today)
    _add_test_graph(snapshot, root, project, today)
    _add_policy_surfaces(snapshot, root, project, today)
    _add_impact_analysis_surfaces(snapshot, root, project, today)
    return snapshot


def _add_curated_docs(snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str) -> None:
    for entry in CURATED_DOC_SOURCES:
        source_name = entry["name"]
        source_path = entry["path"]
        summary = entry["summary"]
        source_node = snapshot.add_node(
            "doc_source_surface",
            source_name,
            summary=summary,
            source_path=source_path,
            source_kind="doc_surface",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(project, "HAS_DOC_SOURCE_SURFACE", source_node, provenance="curated_docs")
        path = root / source_path
        if path.is_file():
            artifact = snapshot.add_node(
                "doc_artifact",
                source_path,
                summary=summary,
                source_path=source_path,
                source_kind="doc_artifact",
                last_verified=today,
                ingest_wave="repo_sync_v1",
                confidence="high",
            )
            snapshot.add_relation(source_node, "BACKED_BY", artifact, provenance="curated_docs")


def _add_decisions_and_risks(snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str) -> None:
    package_summary = root / "docs/reports/evidence/project-package-topology/04-decisions/SUMMARY.md"
    governance_summary = root / "docs/reports/evidence/governance-signals/04-decisions/SUMMARY.md"
    package_doc = snapshot.add_node(
        "doc_artifact",
        _rel_path(root, package_summary),
        summary="Accepted package topology decisions and risks.",
        source_path=_rel_path(root, package_summary),
        source_kind="evidence_decision_summary",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    governance_doc = snapshot.add_node(
        "doc_artifact",
        _rel_path(root, governance_summary),
        summary="Accepted governance decisions and associated risks.",
        source_path=_rel_path(root, governance_summary),
        source_kind="evidence_decision_summary",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    for decision_id in sorted(set(re.findall(r"DEC-[a-z0-9-]+", _read_text(package_summary)))):
        decision = snapshot.add_node(
            "decision",
            decision_id,
            summary="Accepted package-topology decision.",
            source_path=_rel_path(root, package_summary),
            source_kind="evidence_decision_summary",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="medium",
        )
        snapshot.add_relation(project, "HAS_DECISION", decision, provenance="package_topology_summary")
        snapshot.add_relation(decision, "DESCRIBED_IN", package_doc, provenance="package_topology_summary")
    for risk_id in sorted(set(re.findall(r"RISK-[a-z0-9-]+", _read_text(package_summary)))):
        risk = snapshot.add_node(
            "risk",
            risk_id,
            summary="Package-topology risk captured in evidence decisions.",
            source_path=_rel_path(root, package_summary),
            source_kind="evidence_decision_summary",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="medium",
        )
        snapshot.add_relation(project, "HAS_RISK", risk, provenance="package_topology_summary")
        snapshot.add_relation(risk, "DESCRIBED_IN", package_doc, provenance="package_topology_summary")

    governance_text = _read_text(governance_summary)
    table_pattern = re.compile(r"\|\s*`(DEC-[a-z0-9-]+)`\s*\|\s*([^|]+?)\s*\|", re.IGNORECASE)
    for match in table_pattern.finditer(governance_text):
        decision_id = match.group(1)
        summary = match.group(2).strip()
        decision = snapshot.add_node(
            "decision",
            decision_id,
            summary=summary,
            source_path=_rel_path(root, governance_summary),
            source_kind="evidence_decision_summary",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(project, "HAS_DECISION", decision, provenance="governance_summary")
        snapshot.add_relation(decision, "DESCRIBED_IN", governance_doc, provenance="governance_summary")
    risk_pattern = re.compile(r"\|\s*`(RISK-[a-z0-9-]+)`\s*\|\s*([^|]+?)\s*\|", re.IGNORECASE)
    for match in risk_pattern.finditer(governance_text):
        risk_id = match.group(1)
        summary = match.group(2).strip()
        risk = snapshot.add_node(
            "risk",
            risk_id,
            summary=summary,
            source_path=_rel_path(root, governance_summary),
            source_kind="evidence_decision_summary",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(project, "HAS_RISK", risk, provenance="governance_summary")
        snapshot.add_relation(risk, "DESCRIBED_IN", governance_doc, provenance="governance_summary")


def _add_layer_topology(snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str) -> None:
    src_root = root / "src" / "bioetl"
    for layer_name in KNOWN_LAYERS:
        layer_path = src_root / layer_name
        if not layer_path.is_dir():
            continue
        layer = snapshot.add_node(
            "layer_family",
            layer_name,
            summary=f"Top-level runtime layer `{layer_name}`.",
            source_path=_rel_path(root, layer_path),
            source_kind="source_tree",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(project, "CONTAINS", layer, provenance="source_tree")
        for family_path in sorted(
            path for path in layer_path.iterdir() if path.is_dir() and not _is_ignored_repo_path(path)
        ):
            family_name = f"{layer_name}/{family_path.name}"
            family = snapshot.add_node(
                "package_family",
                family_name,
                summary=f"Package family `{family_name}`.",
                source_path=_rel_path(root, family_path),
                source_kind="source_tree",
                layer=layer_name,
                last_verified=today,
                ingest_wave="repo_sync_v1",
                confidence="high",
            )
            snapshot.add_relation(layer, "CONTAINS", family, provenance="source_tree")
        for module_path in sorted(layer_path.rglob("*.py")):
            if module_path.name in {"__init__.py", "__main__.py"}:
                continue
            if _is_ignored_repo_path(module_path):
                continue
            relative_path = _rel_path(root, module_path)
            parts = Path(relative_path).parts
            family_key: NodeKey
            if len(parts) >= 5:
                family_name = f"{layer_name}/{parts[3]}"
                family_key = NodeKey("package_family", family_name)
            else:
                family_key = layer
            module = snapshot.add_node(
                "module_surface",
                relative_path,
                summary=f"Python module `{_module_dotted_name(relative_path)}`.",
                source_path=relative_path,
                source_kind="python_module",
                layer=layer_name,
                module_name=module_path.stem,
                dotted_path=_module_dotted_name(relative_path),
                last_verified=today,
                ingest_wave="repo_sync_v1",
                confidence="high",
            )
            snapshot.add_relation(family_key, "CONTAINS", module, provenance="source_tree")


def _add_provider_and_config_graph(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
) -> None:
    providers_root = root / "configs" / "providers"
    provider_nodes: dict[str, NodeKey] = {}
    entity_nodes: dict[str, NodeKey] = {}
    for provider_path in sorted(providers_root.glob("*.yaml")):
        payload = _read_yaml(provider_path)
        provider_name = str(payload.get("provider", provider_path.stem))
        provider_config = payload.get("source", {})
        auth_type = None
        pagination = None
        if isinstance(provider_config, dict):
            provider_config = provider_config.get("provider_config", provider_config)
            if isinstance(provider_config, dict):
                auth_type = provider_config.get("auth_type")
                pagination_data = provider_config.get("pagination")
                if isinstance(pagination_data, dict):
                    pagination = pagination_data.get("strategy")
        provider = snapshot.add_node(
            "provider_surface",
            provider_name,
            summary=f"Provider surface for `{provider_name}`.",
            source_path=_rel_path(root, provider_path),
            source_kind="provider_config",
            auth_type=auth_type,
            pagination_strategy=pagination,
            entity_count=len(payload.get("entities", [])) if isinstance(payload.get("entities"), list) else None,
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        provider_nodes[provider_name] = provider
        snapshot.add_relation(project, "HAS_PROVIDER", provider, provenance="provider_config")
        artifact = snapshot.add_node(
            "config_artifact",
            _rel_path(root, provider_path),
            summary=f"Provider config for `{provider_name}`.",
            source_path=_rel_path(root, provider_path),
            source_kind="provider_config",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(provider, "DEFINED_BY", artifact, provenance="provider_config")

    entities_root = root / "configs" / "entities"
    for entity_path in sorted(entities_root.rglob("*.yaml")):
        payload = _read_yaml(entity_path)
        provider_name = str(payload.get("provider", entity_path.parent.name))
        entity_name = str(payload.get("entity", entity_path.stem))
        pipeline = payload.get("pipeline", {})
        pipeline_name = None
        pipeline_description = None
        if isinstance(pipeline, dict):
            pipeline_name = pipeline.get("pipeline_name")
            pipeline_description = pipeline.get("description")
        node_name = str(pipeline_name or f"{provider_name}_{entity_name}")
        entity = snapshot.add_node(
            "entity_config",
            node_name,
            summary=str(pipeline_description or f"Entity pipeline config for `{provider_name}/{entity_name}`."),
            source_path=_rel_path(root, entity_path),
            source_kind="entity_config",
            provider=provider_name,
            entity=entity_name,
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        entity_nodes[node_name] = entity
        provider = provider_nodes.get(provider_name)
        if provider is not None:
            snapshot.add_relation(provider, "DEFINES", entity, provenance="entity_config")
        artifact = snapshot.add_node(
            "config_artifact",
            _rel_path(root, entity_path),
            summary=f"Entity config for `{provider_name}/{entity_name}`.",
            source_path=_rel_path(root, entity_path),
            source_kind="entity_config",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(entity, "DEFINED_BY", artifact, provenance="entity_config")

    composites_root = root / "configs" / "composites"
    for composite_path in sorted(composites_root.glob("*.yaml")):
        payload = _read_yaml(composite_path)
        composite = payload.get("composite", {})
        composite_name = composite_path.stem
        summary = f"Composite pipeline config `{composite_name}`."
        seed_pipeline = None
        if isinstance(composite, dict):
            composite_name = str(composite.get("name", composite_name))
            seed = composite.get("seed")
            if isinstance(seed, dict):
                seed_pipeline = seed.get("pipeline")
        composite_node = snapshot.add_node(
            "composite_config",
            composite_name,
            summary=summary,
            source_path=_rel_path(root, composite_path),
            source_kind="composite_config",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(project, "HAS_COMPOSITE", composite_node, provenance="composite_config")
        artifact = snapshot.add_node(
            "config_artifact",
            _rel_path(root, composite_path),
            summary=summary,
            source_path=_rel_path(root, composite_path),
            source_kind="composite_config",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(composite_node, "DEFINED_BY", artifact, provenance="composite_config")
        if isinstance(seed_pipeline, str) and seed_pipeline in entity_nodes:
            snapshot.add_relation(composite_node, "DEPENDS_ON", entity_nodes[seed_pipeline], provenance="composite_seed")
        dependencies = composite.get("dependencies") if isinstance(composite, dict) else None
        if isinstance(dependencies, list):
            for dependency in dependencies:
                if not isinstance(dependency, dict):
                    continue
                dependency_pipeline = dependency.get("pipeline")
                if isinstance(dependency_pipeline, str) and dependency_pipeline in entity_nodes:
                    snapshot.add_relation(
                        composite_node,
                        "DEPENDS_ON",
                        entity_nodes[dependency_pipeline],
                        provenance="composite_dependency",
                        required=bool(dependency.get("required", False)),
                    )


def _add_dashboard_graph(snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str) -> None:
    dashboards_root = root / "grafana" / "dashboards"
    source_surface = NodeKey("doc_source_surface", "grafana dashboards json")
    snapshot.add_relation(project, "HAS_DOC_SOURCE_SURFACE", source_surface, provenance="dashboard_graph")
    for dashboard_path in sorted(dashboards_root.glob("*.json")):
        name = dashboard_path.stem
        payload = _read_json(dashboard_path)
        title = payload.get("title") if isinstance(payload.get("title"), str) else None
        dashboard = snapshot.add_node(
            "dashboard_surface",
            name,
            summary=str(title or f"Grafana dashboard `{name}`."),
            source_path=_rel_path(root, dashboard_path),
            source_kind="dashboard_json",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(project, "HAS_DASHBOARD", dashboard, provenance="dashboard_graph")
        snapshot.add_relation(source_surface, "IS_FACTUAL_SOURCE_FOR", dashboard, provenance="dashboard_graph")


def _add_quality_and_scripts(snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str) -> None:
    for gate_payload in CURATED_QUALITY_GATES:
        gate = snapshot.add_node(
            "quality_gate",
            str(gate_payload["name"]),
            summary=str(gate_payload["summary"]),
            source_kind="curated_quality_gate",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(project, "HAS_QUALITY_GATE", gate, provenance="curated_quality")

    dev_readme = snapshot.add_node(
        "doc_artifact",
        "scripts/dev/README.md",
        summary="Developer workflow and wrapper entrypoint guide.",
        source_path="scripts/dev/README.md",
        source_kind="ops_doc",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(project, "HAS_DOC_ARTIFACT", dev_readme, provenance="curated_scripts")

    for execution_payload in CURATED_EXECUTION_PATHS:
        execution = snapshot.add_node(
            "execution_path",
            str(execution_payload["name"]),
            summary=str(execution_payload["summary"]),
            platform=str(execution_payload["platform"]),
            source_kind="execution_path",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        gate_name = execution_payload.get("gate")
        if isinstance(gate_name, str):
            gate = NodeKey("quality_gate", gate_name)
            snapshot.add_relation(execution, "EXECUTES_GATE", gate, provenance="curated_execution")
        script_path = execution_payload.get("script_path")
        if isinstance(script_path, str):
            script = snapshot.add_node(
                "script_surface",
                script_path,
                summary=f"Script surface for `{script_path}`.",
                source_path=script_path,
                source_kind="script_surface",
                last_verified=today,
                ingest_wave="repo_sync_v1",
                confidence="high",
            )
            snapshot.add_relation(script, "PROVIDES", execution, provenance="curated_execution")
            if script_path.startswith("scripts/dev/"):
                snapshot.add_relation(dev_readme, "DESCRIBES", execution, provenance="scripts_dev_readme")


def _add_test_graph(snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str) -> None:
    tests_root = root / "tests"
    for suite_dir, suite_name in TEST_SURFACES.items():
        suite = snapshot.add_node(
            "test_surface",
            suite_name,
            summary=f"`tests/{suite_dir}/` coverage surface.",
            source_path=f"tests/{suite_dir}",
            source_kind="test_surface",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(project, "HAS_TEST_SURFACE", suite, provenance="test_graph")

    for test_path in sorted(tests_root.rglob("test_*.py")):
        relative_path = _rel_path(root, test_path)
        parts = Path(relative_path).parts
        if len(parts) < 2:
            continue
        suite_dir = parts[1]
        suite_name = TEST_SURFACES.get(suite_dir)
        if suite_name is None:
            continue
        artifact = snapshot.add_node(
            "test_artifact",
            relative_path,
            summary=f"Test artifact `{relative_path}`.",
            source_path=relative_path,
            source_kind="test_artifact",
            suite=suite_dir,
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(NodeKey("test_surface", suite_name), "CONTAINS", artifact, provenance="test_graph")
        layer_name = parts[2] if len(parts) > 2 and parts[2] in KNOWN_LAYERS else None
        if layer_name is not None:
            snapshot.add_relation(artifact, "TESTS_LAYER", NodeKey("layer_family", layer_name), provenance="test_graph")
            if len(parts) > 4:
                family_name = f"{layer_name}/{parts[3]}"
                family_key = NodeKey("package_family", family_name)
                if family_key in snapshot.nodes:
                    snapshot.add_relation(
                        artifact,
                        "TESTS_PACKAGE_FAMILY",
                        family_key,
                        provenance="test_graph",
                    )


def _add_policy_surfaces(snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str) -> None:
    for policy_payload in CURATED_POLICY_SURFACES:
        policy = snapshot.add_node(
            "policy_surface",
            str(policy_payload["name"]),
            summary=str(policy_payload["summary"]),
            source_path=str(policy_payload["source_path"]),
            source_kind="repo_policy_surface",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(project, "HAS_POLICY_SURFACE", policy, provenance="curated_policy")

        source_path = str(policy_payload["source_path"])
        artifact_label = str(policy_payload["artifact_label"])
        artifact = snapshot.add_node(
            artifact_label,
            source_path,
            summary=str(policy_payload["summary"]),
            source_path=source_path,
            source_kind="policy_artifact",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(policy, "BACKED_BY", artifact, provenance="curated_policy")

        for layer_name in policy_payload.get("governs_layers", ()):
            snapshot.add_relation(policy, "GOVERNS", NodeKey("layer_family", str(layer_name)), provenance="curated_policy")
        for gate_name in policy_payload.get("governs_quality_gates", ()):
            snapshot.add_relation(policy, "GOVERNS", NodeKey("quality_gate", str(gate_name)), provenance="curated_policy")
        for test_surface_name in policy_payload.get("governs_test_surfaces", ()):
            snapshot.add_relation(
                policy,
                "GOVERNS",
                NodeKey("test_surface", str(test_surface_name)),
                provenance="curated_policy",
            )
        for doc_source_name in policy_payload.get("governs_docs", ()):
            snapshot.add_relation(
                policy,
                "GOVERNS",
                NodeKey("doc_source_surface", str(doc_source_name)),
                provenance="curated_policy",
            )


def _add_impact_analysis_surfaces(snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str) -> None:
    port_nodes = _add_port_surfaces(snapshot, root, project, today)
    adapter_nodes = _add_adapter_surfaces(snapshot, root, project, today, port_nodes)
    contract_nodes = _add_contract_surfaces(snapshot, root, project, today)
    pipeline_nodes = _add_pipeline_surfaces(snapshot, root, project, today, contract_nodes, adapter_nodes)
    _add_alert_surfaces(snapshot, root, project, today, pipeline_nodes)
    _add_governance_edges(snapshot, port_nodes, adapter_nodes, pipeline_nodes, contract_nodes)


def _add_port_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
) -> set[NodeKey]:
    ports_root = root / "src" / "bioetl" / "domain" / "ports"
    if not ports_root.is_dir():
        return set()

    family = NodeKey("package_family", "domain/ports")
    port_nodes: set[NodeKey] = set()
    for port_path in sorted(ports_root.rglob("*.py")):
        if _is_ignored_repo_path(port_path) or "noop" in port_path.parts:
            continue
        relative_path = _rel_path(root, port_path)
        surface_name = _python_surface_name(relative_path)
        port = snapshot.add_node(
            "port_surface",
            surface_name,
            summary=f"Domain port surface `{surface_name}`.",
            source_path=relative_path,
            source_kind="domain_port",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        port_nodes.add(port)
        snapshot.add_relation(project, "HAS_PORT", port, provenance="impact_ports")
        if family in snapshot.nodes:
            snapshot.add_relation(family, "CONTAINS", port, provenance="impact_ports")
        module_key = NodeKey("module_surface", relative_path)
        if module_key in snapshot.nodes:
            snapshot.add_relation(port, "BACKED_BY", module_key, provenance="impact_ports")
    return port_nodes


def _add_adapter_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    port_nodes: set[NodeKey],
) -> dict[str, NodeKey]:
    adapters_root = root / "src" / "bioetl" / "infrastructure" / "adapters"
    if not adapters_root.is_dir():
        return {}

    adapter_family = NodeKey("package_family", "infrastructure/adapters")
    port_names = {node.name for node in port_nodes}
    adapter_nodes: dict[str, NodeKey] = {}

    for child in sorted(adapters_root.iterdir()):
        if _is_ignored_repo_path(child) or child.name.startswith("_"):
            continue
        if child.is_dir():
            relative_path = _rel_path(root, child)
            surface_name = relative_path.replace("/", ".").removeprefix("src.")
            adapter = snapshot.add_node(
                "adapter_surface",
                surface_name,
                summary=f"Immediate adapter package surface `{surface_name}`.",
                source_path=relative_path,
                source_kind="adapter_package",
                adapter_kind="package",
                granularity="immediate_child",
                last_verified=today,
                ingest_wave="repo_sync_v1",
                confidence="high",
            )
            adapter_nodes[child.name] = adapter
            snapshot.add_relation(project, "HAS_ADAPTER", adapter, provenance="impact_adapters")
            if adapter_family in snapshot.nodes:
                snapshot.add_relation(adapter_family, "CONTAINS", adapter, provenance="impact_adapters")
            provider_key = NodeKey("provider_surface", child.name)
            if provider_key in snapshot.nodes:
                snapshot.add_relation(provider_key, "PROVIDES", adapter, provenance="impact_adapters")
            imported_ports: set[str] = set()
            for module_path in sorted(child.rglob("*.py")):
                if _is_ignored_repo_path(module_path):
                    continue
                imported_ports.update(_imported_port_surfaces(module_path))
            for port_name in sorted(imported_ports):
                if port_name in port_names:
                    snapshot.add_relation(
                        adapter,
                        "DEPENDS_ON",
                        NodeKey("port_surface", port_name),
                        provenance="impact_adapters",
                    )
            continue

        if child.suffix != ".py" or child.name == "__init__.py":
            continue
        relative_path = _rel_path(root, child)
        surface_name = _python_surface_name(relative_path)
        adapter = snapshot.add_node(
            "adapter_surface",
            surface_name,
            summary=f"Immediate adapter module surface `{surface_name}`.",
            source_path=relative_path,
            source_kind="adapter_module",
            adapter_kind="module",
            granularity="immediate_child",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        adapter_nodes[child.stem] = adapter
        snapshot.add_relation(project, "HAS_ADAPTER", adapter, provenance="impact_adapters")
        if adapter_family in snapshot.nodes:
            snapshot.add_relation(adapter_family, "CONTAINS", adapter, provenance="impact_adapters")
        module_key = NodeKey("module_surface", relative_path)
        if module_key in snapshot.nodes:
            snapshot.add_relation(adapter, "BACKED_BY", module_key, provenance="impact_adapters")
        for port_name in sorted(_imported_port_surfaces(child)):
            if port_name in port_names:
                snapshot.add_relation(
                    adapter,
                    "DEPENDS_ON",
                    NodeKey("port_surface", port_name),
                    provenance="impact_adapters",
                )

    return adapter_nodes


def _add_contract_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
) -> dict[str, NodeKey]:
    registry_path = root / "configs" / "base" / "contract_registry.yaml"
    if not registry_path.is_file():
        return {}

    registry_artifact = snapshot.add_node(
        "config_artifact",
        _rel_path(root, registry_path),
        summary="Contract registry for published data contracts.",
        source_path=_rel_path(root, registry_path),
        source_kind="contract_registry",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )

    payload = _read_yaml(registry_path)
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        return {}

    contract_nodes: dict[str, NodeKey] = {}
    for contract_ref, raw_entry in sorted(entries.items()):
        if not isinstance(contract_ref, str) or not isinstance(raw_entry, dict):
            continue
        contract = snapshot.add_node(
            "contract_surface",
            contract_ref,
            summary=f"Published contract surface `{contract_ref}`.",
            source_path=_rel_path(root, registry_path),
            source_kind="contract_registry",
            status=raw_entry.get("status"),
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        contract_nodes[contract_ref] = contract
        snapshot.add_relation(project, "HAS_CONTRACT", contract, provenance="impact_contracts")
        snapshot.add_relation(contract, "BACKED_BY", registry_artifact, provenance="impact_contracts")

        provider_name = contract_ref.split(".", 1)[0]
        provider_key = NodeKey("provider_surface", provider_name)
        if provider_key in snapshot.nodes:
            snapshot.add_relation(provider_key, "DEFINES", contract, provenance="impact_contracts")

        source_path = raw_entry.get("source_path")
        if isinstance(source_path, str):
            resolved = _resolve_repo_path(root, registry_path, source_path)
            if resolved is not None:
                module_key = NodeKey("module_surface", _rel_path(root, resolved))
                if module_key in snapshot.nodes:
                    snapshot.add_relation(contract, "BACKED_BY", module_key, provenance="impact_contracts")

        contract_config_path = (root / "configs" / "contracts" / contract_ref.replace(".", "/")).with_suffix(".yaml")
        if contract_config_path.is_file():
            artifact = snapshot.add_node(
                "config_artifact",
                _rel_path(root, contract_config_path),
                summary=f"Contract policy config for `{contract_ref}`.",
                source_path=_rel_path(root, contract_config_path),
                source_kind="contract_config",
                last_verified=today,
                ingest_wave="repo_sync_v1",
                confidence="high",
            )
            snapshot.add_relation(contract, "BACKED_BY", artifact, provenance="impact_contracts")

        published_artifacts = raw_entry.get("published_artifacts")
        if isinstance(published_artifacts, list):
            for published_path in published_artifacts:
                if not isinstance(published_path, str):
                    continue
                resolved = _resolve_repo_path(root, registry_path, published_path)
                if resolved is None:
                    continue
                artifact = snapshot.add_node(
                    "doc_artifact",
                    _rel_path(root, resolved),
                    summary=f"Published contract artifact for `{contract_ref}`.",
                    source_path=_rel_path(root, resolved),
                    source_kind="published_contract",
                    last_verified=today,
                    ingest_wave="repo_sync_v1",
                    confidence="high",
                )
                snapshot.add_relation(contract, "BACKED_BY", artifact, provenance="impact_contracts")

    return contract_nodes


def _add_pipeline_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    contract_nodes: dict[str, NodeKey],
    adapter_nodes: dict[str, NodeKey],
) -> dict[str, NodeKey]:
    pipeline_nodes: dict[str, NodeKey] = {}

    entities_root = root / "configs" / "entities"
    for entity_path in sorted(entities_root.rglob("*.yaml")):
        payload = _read_yaml(entity_path)
        provider_name = str(payload.get("provider", entity_path.parent.name))
        entity_name = str(payload.get("entity", entity_path.stem))
        pipeline_payload = payload.get("pipeline")
        pipeline_name = f"{provider_name}_{entity_name}"
        pipeline_summary = f"Entity pipeline `{pipeline_name}`."
        if isinstance(pipeline_payload, dict):
            pipeline_name = str(pipeline_payload.get("pipeline_name", pipeline_name))
            pipeline_summary = str(pipeline_payload.get("description", pipeline_summary))
        pipeline = snapshot.add_node(
            "pipeline_surface",
            pipeline_name,
            summary=pipeline_summary,
            source_path=_rel_path(root, entity_path),
            source_kind="entity_pipeline",
            provider=provider_name,
            entity=entity_name,
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        pipeline_nodes[pipeline_name] = pipeline
        snapshot.add_relation(project, "HAS_PIPELINE", pipeline, provenance="impact_pipelines")

        entity_key = NodeKey("entity_config", pipeline_name)
        if entity_key in snapshot.nodes:
            snapshot.add_relation(pipeline, "BACKED_BY", entity_key, provenance="impact_pipelines")
        provider_key = NodeKey("provider_surface", provider_name)
        if provider_key in snapshot.nodes:
            snapshot.add_relation(pipeline, "DEPENDS_ON", provider_key, provenance="impact_pipelines")
        adapter_key = adapter_nodes.get(provider_name)
        if adapter_key is not None:
            snapshot.add_relation(pipeline, "DEPENDS_ON", adapter_key, provenance="impact_pipelines")
        contract_key = contract_nodes.get(f"{provider_name}.{entity_name}")
        if contract_key is not None:
            snapshot.add_relation(pipeline, "DEPENDS_ON", contract_key, provenance="impact_pipelines")

    composites_root = root / "configs" / "composites"
    for composite_path in sorted(composites_root.glob("*.yaml")):
        payload = _read_yaml(composite_path)
        composite = payload.get("composite")
        composite_name = composite_path.stem
        if isinstance(composite, dict):
            composite_name = str(composite.get("name", composite_name))
        pipeline = snapshot.add_node(
            "pipeline_surface",
            composite_name,
            summary=f"Composite pipeline `{composite_name}`.",
            source_path=_rel_path(root, composite_path),
            source_kind="composite_pipeline",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        pipeline_nodes[composite_name] = pipeline
        snapshot.add_relation(project, "HAS_PIPELINE", pipeline, provenance="impact_pipelines")

        composite_key = NodeKey("composite_config", composite_name)
        if composite_key in snapshot.nodes:
            snapshot.add_relation(pipeline, "BACKED_BY", composite_key, provenance="impact_pipelines")

        if isinstance(composite, dict):
            seed = composite.get("seed")
            if isinstance(seed, dict):
                seed_pipeline = seed.get("pipeline")
                if isinstance(seed_pipeline, str) and seed_pipeline in pipeline_nodes:
                    snapshot.add_relation(
                        pipeline,
                        "DEPENDS_ON",
                        pipeline_nodes[seed_pipeline],
                        provenance="impact_pipelines",
                    )
            dependencies = composite.get("dependencies")
            if isinstance(dependencies, list):
                for dependency in dependencies:
                    if not isinstance(dependency, dict):
                        continue
                    dependency_pipeline = dependency.get("pipeline")
                    if isinstance(dependency_pipeline, str) and dependency_pipeline in pipeline_nodes:
                        snapshot.add_relation(
                            pipeline,
                            "DEPENDS_ON",
                            pipeline_nodes[dependency_pipeline],
                            provenance="impact_pipelines",
                        )

    return pipeline_nodes


def _add_alert_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    pipeline_nodes: dict[str, NodeKey],
) -> None:
    rules_root = root / "grafana" / "prometheus-rules"
    if not rules_root.is_dir():
        return

    provider_nodes = sorted(
        (key for key in snapshot.nodes if key.label == "provider_surface"),
        key=lambda node: node.name,
    )
    pipeline_targets = sorted(pipeline_nodes.values(), key=lambda node: node.name)

    for rules_path in sorted(rules_root.glob("*.y*ml")):
        payload = _read_yaml(rules_path)
        artifact = snapshot.add_node(
            "config_artifact",
            _rel_path(root, rules_path),
            summary=f"Prometheus alert rules file `{rules_path.name}`.",
            source_path=_rel_path(root, rules_path),
            source_kind="prometheus_rules",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        groups = payload.get("groups")
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            group_name = str(group.get("name", rules_path.stem))
            rules = group.get("rules")
            if not isinstance(rules, list):
                continue
            for rule in rules:
                if not isinstance(rule, dict):
                    continue
                alert_name = rule.get("alert")
                if not isinstance(alert_name, str):
                    continue
                annotations = rule.get("annotations") if isinstance(rule.get("annotations"), dict) else {}
                labels = rule.get("labels") if isinstance(rule.get("labels"), dict) else {}
                alert = snapshot.add_node(
                    "alert_surface",
                    alert_name,
                    summary=str(annotations.get("summary", f"Prometheus alert `{alert_name}`.")),
                    source_path=_rel_path(root, rules_path),
                    source_kind="prometheus_alert_rule",
                    group=group_name,
                    severity=labels.get("severity"),
                    last_verified=today,
                    ingest_wave="repo_sync_v1",
                    confidence="high",
                )
                snapshot.add_relation(project, "HAS_ALERT", alert, provenance="impact_alerts")
                snapshot.add_relation(alert, "BACKED_BY", artifact, provenance="impact_alerts")

                expr = str(rule.get("expr", ""))
                dimension_text = " ".join(str(value) for value in annotations.values())
                dimensions = _runtime_dimensions(expr, dimension_text)
                if "pipeline" in dimensions:
                    for pipeline in pipeline_targets:
                        snapshot.add_relation(alert, "DEPENDS_ON", pipeline, provenance="impact_alerts")
                if "provider" in dimensions:
                    for provider in provider_nodes:
                        snapshot.add_relation(alert, "DEPENDS_ON", provider, provenance="impact_alerts")

                runbook = annotations.get("runbook")
                if isinstance(runbook, str):
                    runbook_path = root / runbook
                    if runbook_path.is_file():
                        doc = snapshot.add_node(
                            "doc_artifact",
                            runbook,
                            summary=f"Runbook referenced by alert `{alert_name}`.",
                            source_path=runbook,
                            source_kind="alert_runbook",
                            last_verified=today,
                            ingest_wave="repo_sync_v1",
                            confidence="high",
                        )
                        snapshot.add_relation(alert, "DESCRIBED_IN", doc, provenance="impact_alerts")


def _add_governance_edges(
    snapshot: GraphSnapshot,
    port_nodes: set[NodeKey],
    adapter_nodes: dict[str, NodeKey],
    pipeline_nodes: dict[str, NodeKey],
    contract_nodes: dict[str, NodeKey],
) -> None:
    for policy_name in ("hexagonal import matrix", "hexagonal package layout"):
        policy = NodeKey("policy_surface", policy_name)
        if policy not in snapshot.nodes:
            continue
        for port in sorted(port_nodes, key=lambda node: node.name):
            snapshot.add_relation(policy, "GOVERNS", port, provenance="impact_governance")
        for adapter in sorted(adapter_nodes.values(), key=lambda node: node.name):
            snapshot.add_relation(policy, "GOVERNS", adapter, provenance="impact_governance")

    pipeline_policy = NodeKey("policy_surface", "pipeline assembly model")
    if pipeline_policy in snapshot.nodes:
        for pipeline in sorted(pipeline_nodes.values(), key=lambda node: node.name):
            snapshot.add_relation(pipeline_policy, "GOVERNS", pipeline, provenance="impact_governance")

    contract_policy = NodeKey("policy_surface", "medallion storage contract")
    if contract_policy in snapshot.nodes:
        for contract in sorted(contract_nodes.values(), key=lambda node: node.name):
            snapshot.add_relation(contract_policy, "GOVERNS", contract, provenance="impact_governance")
        for pipeline in sorted(pipeline_nodes.values(), key=lambda node: node.name):
            snapshot.add_relation(contract_policy, "GOVERNS", pipeline, provenance="impact_governance")

    observability_policy = NodeKey("policy_surface", "observability surface model")
    if observability_policy in snapshot.nodes:
        for node_key in sorted(snapshot.nodes, key=lambda node: (node.label, node.name)):
            if node_key.label == "alert_surface":
                snapshot.add_relation(observability_policy, "GOVERNS", node_key, provenance="impact_governance")


class Neo4jHttpClient:
    def __init__(self, base_uri: str, username: str, password: str, database: str) -> None:
        self._endpoint = f"{base_uri}/db/{database}/tx/commit"
        auth_token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        self._headers = {
            "Authorization": f"Basic {auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def execute(self, statements: list[dict[str, JsonValue]]) -> dict[str, object]:
        payload = json.dumps({"statements": statements}).encode("utf-8")
        req = request.Request(self._endpoint, data=payload, headers=self._headers, method="POST")
        try:
            with request.urlopen(req, timeout=30) as response:
                raw = response.read().decode("utf-8")
        except error.URLError as exc:  # pragma: no cover - network errors vary per environment
            raise RuntimeError(f"Failed to reach Neo4j HTTP endpoint {self._endpoint}: {exc}") from exc
        body = json.loads(raw)
        errors = body.get("errors", [])
        if errors:
            raise RuntimeError(f"Neo4j returned errors: {errors}")
        return body

    def query(self, statement: str, parameters: dict[str, JsonValue] | None = None) -> list[dict[str, JsonValue]]:
        body = self.execute(
            [
                {
                    "statement": statement,
                    "parameters": parameters or {},
                }
            ]
        )
        results = body.get("results", [])
        if not results:
            return []
        result = results[0]
        columns = result.get("columns", [])
        rows: list[dict[str, JsonValue]] = []
        for entry in result.get("data", []):
            raw_row = entry.get("row", [])
            row = {
                str(column): raw_row[index]
                for index, column in enumerate(columns)
            }
            rows.append(row)
        return rows


def _sync_run_id() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _managed_properties(properties: dict[str, JsonValue], sync_run: str) -> dict[str, JsonValue]:
    managed = dict(properties)
    managed["managed_by"] = DEFAULT_MANAGED_BY
    managed["sync_run"] = sync_run
    managed.setdefault("ingest_wave", DEFAULT_INGEST_WAVE)
    return managed


def _node_statement(node: GraphNode, sync_run: str) -> dict[str, JsonValue]:
    return {
        "statement": (
            f"MERGE (n:`{node.key.label}` {{name: $name}}) "
            "SET n += $properties"
        ),
        "parameters": {
            "name": node.key.name,
            "properties": _managed_properties(node.properties, sync_run),
        },
    }


def _relation_statement(relation: GraphRelation, sync_run: str) -> dict[str, JsonValue]:
    return {
        "statement": (
            f"MATCH (a:`{relation.source.label}` {{name: $source_name}}) "
            f"MATCH (b:`{relation.target.label}` {{name: $target_name}}) "
            f"MERGE (a)-[r:`{relation.relation_type}`]->(b) "
            "SET r += $properties"
        ),
        "parameters": {
            "source_name": relation.source.name,
            "target_name": relation.target.name,
            "properties": _managed_properties(relation.properties, sync_run),
        },
    }


def _reset_managed_relations_statement(relation_types: list[str]) -> dict[str, JsonValue]:
    return {
        "statement": (
            "MATCH (a)-[r]->(b) "
            "WHERE type(r) IN $relation_types "
            "AND (r.managed_by = $managed_by "
            "OR (a.ingest_wave = $ingest_wave AND b.ingest_wave = $ingest_wave)) "
            "DELETE r"
        ),
        "parameters": {
            "relation_types": relation_types,
            "managed_by": DEFAULT_MANAGED_BY,
            "ingest_wave": DEFAULT_INGEST_WAVE,
        },
    }


def _prune_stale_relations_statement(sync_run: str) -> dict[str, JsonValue]:
    return {
        "statement": (
            "MATCH ()-[r]->() "
            "WHERE (r.managed_by = $managed_by OR r.ingest_wave = $ingest_wave) "
            "AND coalesce(r.sync_run, '') <> $sync_run "
            "DELETE r"
        ),
        "parameters": {
            "managed_by": DEFAULT_MANAGED_BY,
            "ingest_wave": DEFAULT_INGEST_WAVE,
            "sync_run": sync_run,
        },
    }


def _prune_stale_nodes_statement(sync_run: str) -> dict[str, JsonValue]:
    return {
        "statement": (
            "MATCH (n) "
            "WHERE n.ingest_wave = $ingest_wave "
            "AND coalesce(n.sync_run, '') <> $sync_run "
            "DETACH DELETE n"
        ),
        "parameters": {
            "ingest_wave": DEFAULT_INGEST_WAVE,
            "sync_run": sync_run,
        },
    }


def _delete_managed_wave_nodes_statement() -> dict[str, JsonValue]:
    return {
        "statement": (
            "MATCH (n) "
            "WHERE n.ingest_wave = $ingest_wave "
            "AND coalesce(n.managed_by, $managed_by) = $managed_by "
            "DETACH DELETE n"
        ),
        "parameters": {
            "ingest_wave": DEFAULT_INGEST_WAVE,
            "managed_by": DEFAULT_MANAGED_BY,
        },
    }


def _prune_legacy_unmanaged_nodes_statement(managed_labels: list[str]) -> dict[str, JsonValue]:
    return {
        "statement": (
            "MATCH (n) "
            "WHERE any(label IN labels(n) WHERE label IN $managed_labels) "
            "AND coalesce(n.managed_by, '') = '' "
            "DETACH DELETE n"
        ),
        "parameters": {
            "managed_labels": managed_labels,
        },
    }


def sync_snapshot(
    snapshot: GraphSnapshot,
    root: Path,
    http_uri: str | None,
    batch_size: int,
    prune_stale: bool = False,
    full_reset_managed_wave: bool = False,
    prune_legacy_unmanaged: bool = False,
) -> None:
    base_uri, username, password, database = resolve_neo4j_connection(root, http_uri)
    client = Neo4jHttpClient(base_uri, username, password, database)
    sync_run = _sync_run_id()
    node_statements = [_node_statement(node, sync_run) for node in snapshot.nodes.values()]
    relation_statements = [_relation_statement(relation, sync_run) for relation in snapshot.relations.values()]
    if full_reset_managed_wave:
        client.execute([_delete_managed_wave_nodes_statement()])
    for statements in _batched(node_statements, batch_size):
        client.execute(statements)
    if prune_stale and relation_statements:
        relation_types = sorted({relation.relation_type for relation in snapshot.relations.values()})
        client.execute([_reset_managed_relations_statement(relation_types)])
    for statements in _batched(relation_statements, batch_size):
        client.execute(statements)
    if prune_stale:
        client.execute([_prune_stale_relations_statement(sync_run)])
        client.execute([_prune_stale_nodes_statement(sync_run)])
    if prune_legacy_unmanaged:
        managed_labels = sorted({node.key.label for node in snapshot.nodes.values()} | set(DEFAULT_LEGACY_PRUNE_LABELS))
        client.execute([_prune_legacy_unmanaged_nodes_statement(managed_labels)])


def _batched(items: list[T], size: int) -> list[list[T]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _write_export(path: Path, snapshot: GraphSnapshot) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot.to_dict(), indent=2) + "\n", encoding="utf-8")


def _write_json(path: Path, payload: JsonValue) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _build_diff_entries(snapshot_counts: dict[str, int], live_counts: dict[str, int]) -> list[dict[str, JsonValue]]:
    entries: list[dict[str, JsonValue]] = []
    for name in sorted(set(snapshot_counts) | set(live_counts)):
        snapshot_value = snapshot_counts.get(name, 0)
        live_value = live_counts.get(name, 0)
        entries.append(
            {
                "name": name,
                "snapshot": snapshot_value,
                "live_managed": live_value,
                "delta": live_value - snapshot_value,
            }
        )
    return entries


def _live_repo_label_rows(client: Neo4jHttpClient, managed_labels: list[str]) -> list[dict[str, JsonValue]]:
    return client.query(
        (
            "MATCH (n) "
            "UNWIND labels(n) AS label "
            "WITH label, n "
            "WHERE label IN $managed_labels "
            "RETURN label, "
            "count(n) AS total, "
            "sum(CASE WHEN coalesce(n.managed_by, '') = $managed_by THEN 1 ELSE 0 END) AS managed, "
            "sum(CASE WHEN coalesce(n.managed_by, '') = '' THEN 1 ELSE 0 END) AS unmanaged "
            "ORDER BY label"
        ),
        {
            "managed_labels": managed_labels,
            "managed_by": DEFAULT_MANAGED_BY,
        },
    )


def _live_managed_relation_rows(client: Neo4jHttpClient) -> list[dict[str, JsonValue]]:
    return client.query(
        (
            "MATCH ()-[r]->() "
            "WHERE coalesce(r.managed_by, '') = $managed_by "
            "AND coalesce(r.ingest_wave, '') = $ingest_wave "
            "RETURN type(r) AS relation_type, count(r) AS total "
            "ORDER BY relation_type"
        ),
        {
            "managed_by": DEFAULT_MANAGED_BY,
            "ingest_wave": DEFAULT_INGEST_WAVE,
        },
    )


def _live_orphan_rows(client: Neo4jHttpClient) -> list[dict[str, JsonValue]]:
    return client.query(
        (
            "MATCH (n) "
            "WHERE coalesce(n.managed_by, '') = $managed_by "
            "AND coalesce(n.ingest_wave, '') = $ingest_wave "
            "AND NOT (n)--() "
            "UNWIND labels(n) AS label "
            "RETURN label, count(n) AS count, collect(n.name)[0..10] AS samples "
            "ORDER BY count DESC, label"
        ),
        {
            "managed_by": DEFAULT_MANAGED_BY,
            "ingest_wave": DEFAULT_INGEST_WAVE,
        },
    )


def _live_unmanaged_repo_rows(client: Neo4jHttpClient, managed_labels: list[str]) -> list[dict[str, JsonValue]]:
    return client.query(
        (
            "MATCH (n) "
            "UNWIND labels(n) AS label "
            "WITH label, n "
            "WHERE label IN $managed_labels "
            "AND coalesce(n.managed_by, '') = '' "
            "RETURN label, count(n) AS count, collect(n.name)[0..10] AS samples "
            "ORDER BY count DESC, label"
        ),
        {
            "managed_labels": managed_labels,
        },
    )


def _live_scalar(client: Neo4jHttpClient, statement: str, parameters: dict[str, JsonValue]) -> int:
    rows = client.query(statement, parameters)
    if not rows:
        return 0
    value = next(iter(rows[0].values()), 0)
    return int(value) if isinstance(value, (int, float)) else 0


def build_audit_report(
    snapshot: GraphSnapshot,
    root: Path,
    http_uri: str | None,
) -> dict[str, JsonValue]:
    base_uri, username, password, database = resolve_neo4j_connection(root, http_uri)
    client = Neo4jHttpClient(base_uri, username, password, database)
    managed_labels = sorted({node.key.label for node in snapshot.nodes.values()} | set(DEFAULT_LEGACY_PRUNE_LABELS))
    snapshot_stats = snapshot.stats()
    live_label_rows = _live_repo_label_rows(client, managed_labels)
    live_relation_rows = _live_managed_relation_rows(client)
    orphan_rows = _live_orphan_rows(client)
    unmanaged_rows = _live_unmanaged_repo_rows(client, managed_labels)

    live_managed_label_counts = {
        str(row["label"]): int(row["managed"])
        for row in live_label_rows
        if isinstance(row.get("label"), str)
    }
    live_managed_relation_counts = {
        str(row["relation_type"]): int(row["total"])
        for row in live_relation_rows
        if isinstance(row.get("relation_type"), str)
    }
    managed_node_total = _live_scalar(
        client,
        (
            "MATCH (n) "
            "WHERE coalesce(n.managed_by, '') = $managed_by "
            "AND coalesce(n.ingest_wave, '') = $ingest_wave "
            "RETURN count(n) AS value"
        ),
        {
            "managed_by": DEFAULT_MANAGED_BY,
            "ingest_wave": DEFAULT_INGEST_WAVE,
        },
    )
    unmanaged_repo_node_total = _live_scalar(
        client,
        (
            "MATCH (n) "
            "WHERE any(label IN labels(n) WHERE label IN $managed_labels) "
            "AND coalesce(n.managed_by, '') = '' "
            "RETURN count(n) AS value"
        ),
        {
            "managed_labels": managed_labels,
        },
    )
    managed_relation_total = sum(live_managed_relation_counts.values())
    orphan_total = sum(int(row["count"]) for row in orphan_rows if isinstance(row.get("count"), (int, float)))

    return {
        "generated_at": _sync_run_id(),
        "managed_by": DEFAULT_MANAGED_BY,
        "ingest_wave": DEFAULT_INGEST_WAVE,
        "snapshot": snapshot_stats,
        "managed_labels": managed_labels,
        "live": {
            "managed_node_total": managed_node_total,
            "managed_relation_total": managed_relation_total,
            "unmanaged_repo_node_total": unmanaged_repo_node_total,
            "label_summary": live_label_rows,
            "managed_relation_summary": live_relation_rows,
            "orphan_summary": {
                "total": orphan_total,
                "by_label": orphan_rows,
            },
            "unmanaged_summary": {
                "total": unmanaged_repo_node_total,
                "by_label": unmanaged_rows,
            },
        },
        "diff": {
            "labels": _build_diff_entries(
                {str(name): int(count) for name, count in snapshot_stats["labels"].items()},
                live_managed_label_counts,
            ),
            "relation_types": _build_diff_entries(
                {str(name): int(count) for name, count in snapshot_stats["relation_types"].items()},
                live_managed_relation_counts,
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.prune_stale and args.full_reset_managed_wave:
        parser.error("--prune-stale and --full-reset-managed-wave cannot be used together")
    root = args.root.resolve()
    snapshot = build_snapshot(root)
    stats = snapshot.stats()
    print(json.dumps(stats, indent=2))
    if args.export is not None:
        _write_export(args.export, snapshot)
        print(f"Exported graph snapshot to {args.export}")
    if args.apply:
        sync_snapshot(
            snapshot,
            root,
            args.http_uri,
            args.batch_size,
            prune_stale=args.prune_stale,
            full_reset_managed_wave=args.full_reset_managed_wave,
            prune_legacy_unmanaged=args.prune_legacy_unmanaged,
        )
        print("Neo4j sync completed.")
    if args.report is not None:
        report = build_audit_report(snapshot, root, args.http_uri)
        _write_json(args.report, report)
        print(f"Exported audit report to {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
