#!/usr/bin/env python3
"""Build and optionally sync a deterministic BioETL knowledge graph into Neo4j."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import TypeAlias
from urllib import error, parse, request

import yaml

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]

DEFAULT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BATCH_SIZE = 100
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
        for family_path in sorted(path for path in layer_path.iterdir() if path.is_dir()):
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
            relative_path = _rel_path(root, module_path)
            parts = Path(relative_path).parts
            family_key: NodeKey
            if len(parts) >= 4:
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
            if len(parts) > 3:
                family_name = f"{layer_name}/{parts[3]}"
                snapshot.add_relation(
                    artifact,
                    "TESTS_PACKAGE_FAMILY",
                    NodeKey("package_family", family_name),
                    provenance="test_graph",
                )


class Neo4jHttpClient:
    def __init__(self, base_uri: str, username: str, password: str, database: str) -> None:
        self._endpoint = f"{base_uri}/db/{database}/tx/commit"
        auth_token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        self._headers = {
            "Authorization": f"Basic {auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def execute(self, statements: list[dict[str, JsonValue]]) -> None:
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


def _node_statement(node: GraphNode) -> dict[str, JsonValue]:
    return {
        "statement": (
            f"MERGE (n:`{node.key.label}` {{name: $name}}) "
            "SET n += $properties"
        ),
        "parameters": {
            "name": node.key.name,
            "properties": node.properties,
        },
    }


def _relation_statement(relation: GraphRelation) -> dict[str, JsonValue]:
    return {
        "statement": (
            f"MERGE (a:`{relation.source.label}` {{name: $source_name}}) "
            f"MERGE (b:`{relation.target.label}` {{name: $target_name}}) "
            f"MERGE (a)-[r:`{relation.relation_type}`]->(b) "
            "SET r += $properties"
        ),
        "parameters": {
            "source_name": relation.source.name,
            "target_name": relation.target.name,
            "properties": relation.properties,
        },
    }


def sync_snapshot(
    snapshot: GraphSnapshot,
    root: Path,
    http_uri: str | None,
    batch_size: int,
) -> None:
    base_uri, username, password, database = resolve_neo4j_connection(root, http_uri)
    client = Neo4jHttpClient(base_uri, username, password, database)
    node_statements = [_node_statement(node) for node in snapshot.nodes.values()]
    relation_statements = [_relation_statement(relation) for relation in snapshot.relations.values()]
    for statements in _batched(node_statements + relation_statements, batch_size):
        client.execute(statements)


def _batched[T](items: list[T], size: int) -> list[list[T]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _write_export(path: Path, snapshot: GraphSnapshot) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot.to_dict(), indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    snapshot = build_snapshot(root)
    stats = snapshot.stats()
    print(json.dumps(stats, indent=2))
    if args.export is not None:
        _write_export(args.export, snapshot)
        print(f"Exported graph snapshot to {args.export}")
    if args.apply:
        sync_snapshot(snapshot, root, args.http_uri, args.batch_size)
        print("Neo4j sync completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
