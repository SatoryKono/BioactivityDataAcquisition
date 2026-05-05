#!/usr/bin/env python3
"""Build and optionally sync a deterministic BioETL knowledge graph into Neo4j."""

from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timezone
from pathlib import Path
from typing import TypeAlias, TypeVar
from urllib import error, parse, request

import yaml

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
T = TypeVar("T")
BIOETL_TEST_SURFACE_UNIT = "unit tests"
BIOETL_TEST_SURFACE_INTEGRATION = "integration tests"
BIOETL_TEST_SURFACE_E2E = "e2e tests"
BIOETL_TEST_SURFACE_ARCHITECTURE = "architecture tests"
BIOETL_TEST_SURFACE_CONTRACT = "contract tests"
BIOETL_TEST_SURFACE_BENCHMARKS = "benchmarks"
DOC_PATH_RULES = "docs/00-project/RULES.md"
DOC_PATH_MEMORY_ENTRY = "docs/00-project/ai/memory/agent-memory.md"
DOC_PATH_MEMORY_USAGE_GUIDE = "docs/00-project/ai/agents/guides/MEMORY_USAGE.md"
DOC_PATH_POST_CHANGE_VALIDATION = "docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md"
DOC_PATH_TESTING_GUIDE = "docs/03-guides/testing.md"
DOC_PATH_DOCS_VERIFICATION = "docs/03-guides/docs-verification.md"
DOC_PATH_CLAUDE_EXCLUSION = ".claude/"
DOC_PATH_ARCHITECTURE_DECISION_ADR040 = "docs/02-architecture/decisions/ADR-040-diagram-governance.md"
DOC_PATH_DOCS_REPORTS_MAP = "docs/02-architecture/diagrams/governance/DIAGRAM-WORKFLOW-GUIDE.md"
DOC_PATH_DIAGRAMS_README = "docs/02-architecture/diagrams/README.md"
DOC_PATH_DASHBOARDS_GUIDE = "docs/03-guides/dashboards/dashboard-extension-llm.md"
DOC_PATH_UNIPROT_PROVIDER_CONFIG = "configs/providers/uniprot.yaml"
DOC_PATH_MAP = "docs/00-project/00-map.md"
DOC_PATH_TEST_MATRIX = "configs/quality/test_matrix.yaml"
DOC_PATH_INTEGRATION_VCR_POLICY = "configs/quality/integration_vcr_policy.yaml"
DOC_PATH_HARDCODED_GRAFANA_DASHBOARDS = "grafana/dashboards"
DOC_PATH_DOCS_VERIFICATION_GUIDE = DOC_PATH_DOCS_VERIFICATION
DOC_PATH_GRAFANA_DASHBOARDS_SURFACE = "grafana dashboards json"
DOC_PATH_DIAGRAMS_HUB = "architecture diagrams hub"
DOC_PATH_DIAGRAM_TOOLING_README = "diagram tooling readme"
QUALITY_GATE_PYTEST = "pytest"
QUALITY_GATE_MYPY_STRICT = "mypy --strict"
QUALITY_GATE_DOCS_VERIFICATION = "docs verification"
QUALITY_GATE_CONFIG_VALIDATION = "config validation"
QUALITY_GATE_PRETEST_GUARDRAILS = "pretest guardrails"
QUALITY_GATE_DIAGRAM_QUALITY = "diagram quality gates"
PATH_PYTHON_INIT_FILE = "__init__.py"
PATH_PYTHON_INIT_SUFFIX = "/__init__.py"
PY_YAML_GLOB = "*.yaml"
PORT_MODULE_PREFIX = "bioetl.domain.ports"
BIOETL_METRIC_PATTERN = re.compile(r"\bbioetl_[a-zA-Z0-9_:]+")

DEFAULT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BATCH_SIZE = 20
DEFAULT_INGEST_WAVE = "repo_sync_v1"
DEFAULT_MANAGED_BY = "neo4j_memory_sync"
DEFAULT_MEMORY_MAPPING_PATH = "configs/quality/neo4j_memory_mapping.yaml"
CRITICAL_ANALYSIS_NODE_LABELS: tuple[str, ...] = (
    "retirement_candidate",
    "development_cycle_surface",
    "complexity_candidate",
)
CRITICAL_ANALYSIS_RELATION_TYPES: tuple[str, ...] = (
    "CANDIDATE_FOR_REMOVAL",
    "OWNED_BY_CYCLE",
    "BLOCKED_FROM_DELETION_BY",
    "HAS_COMPLEXITY_SIGNAL",
    "CANDIDATE_FOR_SIMPLIFICATION",
    "JUSTIFIED_BY_RUNTIME",
    "BLOCKED_BY_VARIANCE",
)
ANALYSIS_NODE_LABELS: tuple[str, ...] = (
    "retirement_candidate",
    "development_cycle_surface",
    "complexity_candidate",
)
ANALYSIS_RELATION_TYPES: tuple[str, ...] = (
    "CANDIDATE_FOR_REMOVAL",
    "OWNED_BY_CYCLE",
    "BLOCKED_FROM_DELETION_BY",
    "HAS_COMPLEXITY_SIGNAL",
    "CANDIDATE_FOR_SIMPLIFICATION",
    "JUSTIFIED_BY_RUNTIME",
    "BLOCKED_BY_VARIANCE",
)
DEFAULT_LEGACY_PRUNE_LABELS: tuple[str, ...] = (
    "project",
    "repo_zone",
    "directory_surface",
    "file_surface",
    "doc_source_surface",
    "doc_artifact",
    "decision",
    "risk",
    "policy_surface",
    "layer_family",
    "package_family",
    "module_surface",
    "class_surface",
    "function_surface",
    "method_surface",
    "duplication_cluster",
    "retirement_candidate",
    "development_cycle_surface",
    "complexity_candidate",
    "port_surface",
    "adapter_surface",
    "adapter_impl_surface",
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
DEFAULT_FILE_STRUCTURE_REPO_ZONES: dict[str, tuple[str, ...]] = {
    "src": ("src",),
    "configs": ("configs",),
    "tests": ("tests",),
    "docs": ("docs",),
    "scripts": ("scripts",),
    "grafana": ("grafana",),
}
DEFAULT_FILE_STRUCTURE_EXCLUDED_PREFIXES: tuple[str, ...] = (
    "docs/99-archive",
    "docs/exports",
    "docs/reports/generated",
    "docs/02-architecture/generated",
    "docs/02-architecture/diagrams/bundles",
    "docs/02-architecture/diagrams/architecture/png",
    "docs/02-architecture/diagrams/architecture/svg",
    "docs/02-architecture/diagrams/class-diagrams/png",
    "docs/02-architecture/diagrams/class-diagrams/svg",
    "docs/02-architecture/diagrams/foundation/png",
    "docs/02-architecture/diagrams/foundation/svg",
    "docs/02-architecture/diagrams/views/png",
    "docs/02-architecture/diagrams/views/svg",
    "docs/02-architecture/diagrams/descriptions/legacy",
    "scripts/archive",
)
DEFAULT_FILE_STRUCTURE_EXCLUDED_DIR_NAMES: tuple[str, ...] = ("__pycache__",)
KNOWN_LAYERS = ("domain", "application", "infrastructure", "composition", "interfaces")
TEST_SURFACES: dict[str, str] = {
    "unit": BIOETL_TEST_SURFACE_UNIT,
    "integration": BIOETL_TEST_SURFACE_INTEGRATION,
    "e2e": BIOETL_TEST_SURFACE_E2E,
    "architecture": BIOETL_TEST_SURFACE_ARCHITECTURE,
    "contract": BIOETL_TEST_SURFACE_CONTRACT,
    "benchmarks": BIOETL_TEST_SURFACE_BENCHMARKS,
}
CURATED_DOC_SOURCES: tuple[dict[str, str], ...] = (
    {
        "name": "Project Navigator",
        "path": DOC_PATH_MAP,
        "summary": "Primary project navigator and active entrypoint map.",
    },
    {
        "name": "RULES.md",
        "path": DOC_PATH_RULES,
        "summary": "Canonical governance and requirements surface for the project.",
    },
    {
        "name": "agent memory entry point",
        "path": DOC_PATH_MEMORY_ENTRY,
        "summary": "Human-oriented project memory entry point for AI runtimes.",
    },
    {
        "name": "testing guide",
        "path": DOC_PATH_TESTING_GUIDE,
        "summary": "Published testing strategy guide.",
    },
    {
        "name": "dashboard extension guide",
        "path": DOC_PATH_DASHBOARDS_GUIDE,
        "summary": "Canonical LLM playbook for shipped Grafana dashboards.",
    },
    {
        "name": DOC_PATH_DIAGRAMS_HUB,
        "path": DOC_PATH_DIAGRAMS_README,
        "summary": "Canonical hub for architecture, class, foundation, and view diagram sources and publication artifacts.",
    },
    {
        "name": "diagram governance ADR",
        "path": DOC_PATH_ARCHITECTURE_DECISION_ADR040,
        "summary": "Accepted ADR defining diagram governance, palette, decomposition rules, and CI validation expectations.",
    },
    {
        "name": "diagram governance workflow",
        "path": "docs/02-architecture/diagrams/governance/DIAGRAM-WORKFLOW-GUIDE.md",
        "summary": "Operator workflow for maintaining canonical diagram trees, derived views, and publication bundles.",
    },
    {
        "name": "diagram measured inventory",
        "path": "docs/02-architecture/diagrams/governance/diagrams-index.md",
        "summary": "Measured inventory of tracked diagram families and canonical source coverage.",
    },
    {
        "name": "diagram views inventory",
        "path": "docs/02-architecture/diagrams/governance/diagram-views-inventory.md",
        "summary": "Measured inventory of derived Mermaid review views and decomposition coverage.",
    },
    {
        "name": DOC_PATH_DIAGRAM_TOOLING_README,
        "path": "scripts/diagrams/README.md",
        "summary": "Repository entrypoint for diagram lint, render, bundle, and regression tooling.",
    },
    {
        "name": "docs verification guide",
        "path": DOC_PATH_DOCS_VERIFICATION,
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
        "name": DOC_PATH_GRAFANA_DASHBOARDS_SURFACE,
        "path": DOC_PATH_HARDCODED_GRAFANA_DASHBOARDS,
        "summary": "Factual source of truth for shipped dashboard behavior.",
    },
)
CURATED_QUALITY_GATES: tuple[dict[str, object], ...] = (
    {
        "name": QUALITY_GATE_PYTEST,
        "summary": "Primary test runner for local and CI feedback.",
    },
    {
        "name": QUALITY_GATE_MYPY_STRICT,
        "summary": "Static typing gate for public surfaces and repo strictness.",
    },
    {
        "name": QUALITY_GATE_DOCS_VERIFICATION,
        "summary": "Published docs verification chain via scripts.docs verify and strict MkDocs build.",
    },
    {
        "name": QUALITY_GATE_CONFIG_VALIDATION,
        "summary": "Schema/config validation path for supported configs and invariants.",
    },
    {
        "name": QUALITY_GATE_PRETEST_GUARDRAILS,
        "summary": "Broad preflight for cleanup, docs, inventory, and architecture drift.",
    },
    {
        "name": QUALITY_GATE_DIAGRAM_QUALITY,
        "summary": "Diagram lint, syntax validation, artifact checks, visual smoke, and nightly regression gates for Mermaid publication surfaces.",
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
        "source_path": DOC_PATH_RULES,
        "artifact_label": "doc_artifact",
        "governs_layers": KNOWN_LAYERS,
    },
    {
        "name": "medallion storage contract",
        "summary": (
            "BioETL follows Bronze to Silver to Gold medallion flow. Silver must use Delta Lake rather than raw "
            "Parquet, and Pandera remains the schema validation standard across dataframe boundaries."
        ),
        "source_path": DOC_PATH_RULES,
        "artifact_label": "doc_artifact",
    },
    {
        "name": "provider support matrix",
        "summary": (
            "Primary provider set includes ChEMBL, PubChem, PubMed, Semantic Scholar, CrossRef, OpenAlex, "
            "and UniProt for bioactivity acquisition and enrichment workflows."
        ),
        "source_path": DOC_PATH_RULES,
        "artifact_label": "doc_artifact",
    },
    {
        "name": "hexagonal package layout",
        "summary": (
            "Source layout is organized into domain, application, infrastructure, composition, and interfaces. "
            "Domain stays pure, composition owns wiring, interfaces expose CLI entrypoints, and architecture tests "
            "enforce cross-layer boundaries."
        ),
        "source_path": DOC_PATH_RULES,
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
        "source_path": DOC_PATH_RULES,
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
        "source_path": DOC_PATH_DASHBOARDS_GUIDE,
        "artifact_label": "doc_artifact",
            "governs_docs": (DOC_PATH_GRAFANA_DASHBOARDS_SURFACE,),
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
        "governs_test_surfaces": (
            BIOETL_TEST_SURFACE_UNIT,
            BIOETL_TEST_SURFACE_INTEGRATION,
            BIOETL_TEST_SURFACE_E2E,
            BIOETL_TEST_SURFACE_ARCHITECTURE,
            BIOETL_TEST_SURFACE_CONTRACT,
        ),
    },
    {
        "name": "quality gate stack",
        "summary": (
            f"The main repository gate stack combines {QUALITY_GATE_PYTEST}, "
            f"{QUALITY_GATE_MYPY_STRICT}, VCR execution policy, {QUALITY_GATE_DOCS_VERIFICATION}, "
            f"{QUALITY_GATE_CONFIG_VALIDATION}, and {QUALITY_GATE_PRETEST_GUARDRAILS}."
        ),
        "source_path": DOC_PATH_TESTING_GUIDE,
        "artifact_label": "doc_artifact",
        "governs_quality_gates": (
            QUALITY_GATE_PYTEST,
            QUALITY_GATE_MYPY_STRICT,
            QUALITY_GATE_DOCS_VERIFICATION,
            QUALITY_GATE_CONFIG_VALIDATION,
            QUALITY_GATE_PRETEST_GUARDRAILS,
        ),
    },
    {
        "name": "VCR replay discipline",
        "summary": (
            "Integration and e2e work is replay-first. VCR cassettes are refreshed in a targeted way rather than "
            "broad uncontrolled rewrites, and machine-readable policy keeps the replay contract synchronized with the test matrix."
        ),
        "source_path": DOC_PATH_TESTING_GUIDE,
        "artifact_label": "doc_artifact",
        "governs_test_surfaces": (BIOETL_TEST_SURFACE_INTEGRATION, BIOETL_TEST_SURFACE_E2E),
    },
    {
        "name": "target enrichment bridge",
        "summary": (
            "Target enrichment crosses provider boundaries: ChEMBL supplies target-centric seed records while UniProt "
            "contributes reviewed protein metadata and an idmapping surface that translates ChEMBL target identifiers into UniProt accessions."
        ),
        "source_path": DOC_PATH_UNIPROT_PROVIDER_CONFIG,
        "artifact_label": "config_artifact",
    },
    {
        "name": "publication enrichment mesh",
        "summary": (
            "Publication enrichment is intentionally multi-provider. ChEMBL contributes source publication references, "
            "while PubMed, CrossRef, OpenAlex, and Semantic Scholar enrich publication metadata through PMID, DOI, title, "
            "and citation-oriented resolution paths."
        ),
        "source_path": DOC_PATH_TEST_MATRIX,
        "artifact_label": "config_artifact",
    },
    {
        "name": "integration and VCR execution policy",
        "summary": "Tracked machine-readable policy for integration and VCR execution scope, replay modes, and suite inventory.",
        "source_path": DOC_PATH_INTEGRATION_VCR_POLICY,
        "artifact_label": "config_artifact",
        "governs_test_surfaces": (
            BIOETL_TEST_SURFACE_INTEGRATION,
            BIOETL_TEST_SURFACE_E2E,
        ),
        "governs_quality_gates": (QUALITY_GATE_PYTEST,),
    },
    {
        "name": "docs verification guide",
        "summary": "Published workflow defining the verification path for docs surface and repo-only supporting material boundaries.",
        "source_path": DOC_PATH_DOCS_VERIFICATION,
        "artifact_label": "doc_artifact",
        "governs_quality_gates": (QUALITY_GATE_DOCS_VERIFICATION,),
    },
    {
        "name": "diagram governance policy",
        "summary": (
            "Canonical architecture diagrams live under docs/02-architecture/diagrams with ADR-040, canonical policy, "
            "measured inventories, and scripted lint/render/publication checks defining the supported workflow."
        ),
        "source_path": "docs/02-architecture/diagrams/governance/policy.md",
        "artifact_label": "doc_artifact",
        "governs_quality_gates": (QUALITY_GATE_DIAGRAM_QUALITY,),
        "governs_test_surfaces": (BIOETL_TEST_SURFACE_ARCHITECTURE,),
        "governs_docs": (
            DOC_PATH_DIAGRAMS_HUB,
            "diagram governance ADR",
            "diagram governance workflow",
            "diagram measured inventory",
            "diagram views inventory",
            DOC_PATH_DIAGRAM_TOOLING_README,
        ),
    },
    {
        "name": "diagram publication boundary",
        "summary": (
            "Canonical .mmd trees and derived Mermaid views are source of truth for diagrams; svg, png, bundles, "
            "descriptions, and index files are publication artifacts regenerated from those sources."
        ),
        "source_path": "docs/02-architecture/diagrams/README.md",
        "artifact_label": "doc_artifact",
        "governs_docs": (DOC_PATH_DIAGRAMS_HUB, DOC_PATH_DIAGRAM_TOOLING_README),
    },
    {
        "name": "published docs boundary",
        "summary": "Published docs in docs/00-05 and README define active supported behavior; repo-only material must not override them.",
        "source_path": DOC_PATH_DOCS_VERIFICATION,
        "artifact_label": "doc_artifact",
    },
    {
        "name": "default VCR record mode",
        "summary": "CI defaults to none; local defaults to once unless explicitly overridden.",
        "source_path": DOC_PATH_INTEGRATION_VCR_POLICY,
        "artifact_label": "config_artifact",
        "governs_test_surfaces": (BIOETL_TEST_SURFACE_INTEGRATION, BIOETL_TEST_SURFACE_E2E),
    },
    {
        "name": "targeted cassette refresh",
        "summary": "Targeted VCR refresh uses new_episodes; broad rewrites are not the supported default path.",
        "source_path": DOC_PATH_INTEGRATION_VCR_POLICY,
        "artifact_label": "config_artifact",
        "governs_test_surfaces": (BIOETL_TEST_SURFACE_INTEGRATION, BIOETL_TEST_SURFACE_E2E),
    },
)
CURATED_EXECUTION_PATHS: tuple[dict[str, object], ...] = (
    {
        "name": "uv run python -m bioetl run --pipeline",
        "platform": "ci_uv",
        "summary": "Canonical CI and single-OS pipeline runtime path.",
    },
    {
        "name": "\"${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python\" -m bioetl run --pipeline",
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
        "gate": QUALITY_GATE_PYTEST,
    },
    {
        "name": "bash scripts/dev/run_pytest.sh",
        "platform": "wsl",
        "summary": "WSL/Linux wrapper with default coverage flags and plugin bootstrap.",
        "gate": QUALITY_GATE_PYTEST,
        "script_path": "scripts/dev/run_pytest.sh",
    },
    {
        "name": ".\\scripts\\dev\\run_pytest.ps1",
        "platform": "windows",
        "summary": "PowerShell wrapper with default coverage flags for .venv-win.",
        "gate": QUALITY_GATE_PYTEST,
        "script_path": "scripts/dev/run_pytest.ps1",
    },
    {
        "name": "uv run python -m mypy --strict src/bioetl/",
        "platform": "ci_uv",
        "summary": "Canonical CI and single-OS strict typing path.",
        "gate": QUALITY_GATE_MYPY_STRICT,
    },
    {
        "name": "bash scripts/dev/run_mypy.sh",
        "platform": "wsl",
        "summary": "WSL/Linux mypy wrapper for the stable WSL virtualenv.",
        "gate": QUALITY_GATE_MYPY_STRICT,
        "script_path": "scripts/dev/run_mypy.sh",
    },
    {
        "name": ".\\scripts\\dev\\run_mypy.ps1",
        "platform": "windows",
        "summary": "PowerShell mypy wrapper for .venv-win.",
        "gate": QUALITY_GATE_MYPY_STRICT,
        "script_path": "scripts/dev/run_mypy.ps1",
    },
    {
        "name": "uv run python -m scripts.docs verify",
        "platform": "ci_uv",
        "summary": "Canonical end-to-end published docs verification path.",
        "gate": QUALITY_GATE_DOCS_VERIFICATION,
        "script_path": "scripts/docs/verify_docs.py",
    },
    {
        "name": "uv run python -m scripts.schema validate-configs",
        "platform": "ci_uv",
        "summary": "Canonical config validation path for supported configs.",
        "gate": QUALITY_GATE_CONFIG_VALIDATION,
        "script_path": "scripts/schema/validate_configs.py",
    },
    {
        "name": "bash scripts/dev/pretest_guardrails.sh",
        "platform": "wsl",
        "summary": "WSL pretest guardrail runner before broad pytest waves.",
        "gate": QUALITY_GATE_PRETEST_GUARDRAILS,
        "script_path": "scripts/dev/pretest_guardrails.sh",
    },
)
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
                "gate": QUALITY_GATE_DIAGRAM_QUALITY,
            },
            {
                "name": "uv run python -m scripts.diagrams check-quality-gates",
                "platform": "ci_uv",
                "summary": "Canonical diagram regression gate for tracked Mermaid and publication invariants.",
                "gate": QUALITY_GATE_DIAGRAM_QUALITY,
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
                "gate": QUALITY_GATE_DOCS_VERIFICATION,
            },
            {
                "name": "uv run python -m scripts.docs check-links --links --specs --configs",
                "platform": "ci_uv",
                "summary": "Canonical docs link/spec/config verification path.",
                "gate": QUALITY_GATE_DOCS_VERIFICATION,
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
                "gate": QUALITY_GATE_CONFIG_VALIDATION,
            },
            {
                "name": "uv run python -m scripts.schema check-invariants",
                "platform": "ci_uv",
                "summary": "Canonical config invariant check for naming, auth, keys, and config CI policy.",
                "gate": QUALITY_GATE_CONFIG_VALIDATION,
            },
        ),
    },
    {
        "readme_path": "scripts/ops/README.md",
        "readme_summary": "Operations tooling notes covering Codex/WSL setup and the scripts.ops command surface.",
        "entrypoint_path": "scripts/ops/__main__.py",
        "entrypoint_summary": "Unified Python entrypoint for operational helpers such as Neo4j memory sync, Grafana fixes, and shell-based ops tasks.",
        "execution_paths": (
            {
                "name": "python -m scripts.ops",
                "platform": "cross_platform",
                "summary": "Unified local entrypoint for operational helper commands.",
            },
            {
                "name": "python -m scripts.ops sync-neo4j-memory --report /tmp/neo4j-memory-audit.json",
                "platform": "cross_platform",
                "summary": "Canonical audit/report path for the deterministic Neo4j repo graph.",
            },
            {
                "name": "python -m scripts.ops sync-neo4j-memory --apply",
                "platform": "cross_platform",
                "summary": "Canonical apply path for syncing the deterministic Neo4j repo graph.",
            },
        ),
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


def _filtered_snapshot(
    snapshot: GraphSnapshot,
    only_labels: tuple[str, ...] = (),
    only_analysis_layer: bool = False,
) -> GraphSnapshot:
    allowed_labels = set(only_labels)
    if only_analysis_layer:
        allowed_labels |= set(ANALYSIS_NODE_LABELS)
    if not allowed_labels:
        return snapshot

    filtered = GraphSnapshot()
    for key, node in snapshot.nodes.items():
        if key.label in allowed_labels:
            filtered.nodes[key] = node
    for rel_key, relation in snapshot.relations.items():
        if relation.relation_type in ANALYSIS_RELATION_TYPES:
            if only_analysis_layer or relation.source.label in allowed_labels or relation.target.label in allowed_labels:
                filtered.relations[rel_key] = relation
            continue
        if relation.source.label in allowed_labels and relation.target.label in allowed_labels:
            filtered.relations[rel_key] = relation
    return filtered


@dataclass(frozen=True)
class PortSurfaceDescriptor:
    surface_name: str
    class_name: str
    module_name: str
    source_path: str


@dataclass(frozen=True)
class DuplicateFamilyConfig:
    name: str
    roots: tuple[str, ...]
    package_family: str
    promotion_targets: tuple[NodeKey, ...]


@dataclass
class CallableDescriptor:
    node_key: NodeKey
    family_name: str
    package_family: str
    source_path: str
    callable_name: str
    parent_class: str | None
    surface_kind: str
    ast_shape_hash: str
    signature_hash: str
    ast_node_count: int
    semantic_tags: tuple[str, ...]


@dataclass
class ClassDescriptor:
    node_key: NodeKey
    family_name: str
    package_family: str
    source_path: str
    class_name: str
    base_names: tuple[str, ...]
    method_names: tuple[str, ...]


@dataclass(frozen=True)
class RetirementAnalysisConfig:
    enabled: bool
    family_names: tuple[str, ...]
    current_cycle_age_days: int
    stale_age_days: int
    dead_score_threshold: int
    wip_markers: tuple[str, ...]
    deprecation_markers: tuple[str, ...]


@dataclass(frozen=True)
class ComplexityAnalysisConfig:
    enabled: bool
    family_names: tuple[str, ...]
    complexity_score_threshold: int
    removable_score_threshold: int
    indirection_markers: tuple[str, ...]
    stateful_markers: tuple[str, ...]
    deprecation_markers: tuple[str, ...]
    blocker_anchor_limit: int


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
    parser.add_argument(
        "--only-label",
        action="append",
        default=[],
        help=(
            "Limit apply/export/report snapshot operations to one or more node labels. "
            "Useful for targeted sync debugging, e.g. --only-label complexity_candidate."
        ),
    )
    parser.add_argument(
        "--only-analysis-layer",
        action="store_true",
        help=(
            "Limit apply/export/report snapshot operations to the analysis layer "
            "(retirement/development-cycle/complexity nodes and their relations)."
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


def _load_memory_mapping(root: Path) -> dict[str, object]:
    mapping_path = root / DEFAULT_MEMORY_MAPPING_PATH
    if not mapping_path.is_file():
        return {}
    return _read_yaml(mapping_path)


def _file_structure_config(memory_mapping: dict[str, object]) -> dict[str, object]:
    payload = memory_mapping.get("file_structure", {})
    if not isinstance(payload, dict):
        payload = {}

    raw_repo_zones = payload.get("repo_zones", {})
    repo_zones: dict[str, tuple[str, ...]] = {}
    if isinstance(raw_repo_zones, dict):
        for zone_name, zone_paths in raw_repo_zones.items():
            repo_zones[str(zone_name)] = tuple(_as_string_list(zone_paths))
    if not repo_zones:
        repo_zones = DEFAULT_FILE_STRUCTURE_REPO_ZONES

    excluded_prefixes = tuple(
        sorted(set(_as_string_list(payload.get("excluded_prefixes")) or list(DEFAULT_FILE_STRUCTURE_EXCLUDED_PREFIXES)))
    )
    excluded_dir_names = tuple(
        sorted(set(_as_string_list(payload.get("excluded_dir_names")) or list(DEFAULT_FILE_STRUCTURE_EXCLUDED_DIR_NAMES)))
    )
    promoted_hubs = tuple(sorted(set(_as_string_list(payload.get("promoted_hubs")))))
    return {
        "repo_zones": repo_zones,
        "excluded_prefixes": excluded_prefixes,
        "excluded_dir_names": excluded_dir_names,
        "promoted_hubs": promoted_hubs,
    }


def _duplication_analysis_config(memory_mapping: dict[str, object]) -> dict[str, object]:  # NOSONAR
    payload = memory_mapping.get("duplication_analysis", {})
    if not isinstance(payload, dict):
        payload = {}

    raw_families = payload.get("families", {})
    families: list[DuplicateFamilyConfig] = []
    if isinstance(raw_families, dict):
        for family_name, family_payload in raw_families.items():
            if not isinstance(family_payload, dict):
                continue
            roots = tuple(_as_string_list(family_payload.get("roots")))
            package_family = str(family_payload.get("package_family", "")).strip()
            if not roots or not package_family:
                continue
            promotion_targets: list[NodeKey] = []
            raw_targets = family_payload.get("promotion_targets", [])
            if isinstance(raw_targets, list):
                for raw_target in raw_targets:
                    if not isinstance(raw_target, dict):
                        continue
                    label = str(raw_target.get("label", "")).strip()
                    name = str(raw_target.get("name", "")).strip()
                    if label and name:
                        promotion_targets.append(NodeKey(label, name))
            families.append(
                DuplicateFamilyConfig(
                    name=str(family_name),
                    roots=roots,
                    package_family=package_family,
                    promotion_targets=tuple(promotion_targets),
                )
            )

    return {
        "enabled": bool(payload.get("enabled", True)),
        "min_cluster_size": int(payload.get("min_cluster_size", 2) or 2),
        "min_ast_nodes": int(payload.get("min_ast_nodes", 12) or 12),
        "families": tuple(families),
    }


def _retirement_analysis_config(
    memory_mapping: dict[str, object],
    duplication_config: dict[str, object],
) -> RetirementAnalysisConfig:
    payload = memory_mapping.get("retirement_analysis", {})
    if not isinstance(payload, dict):
        payload = {}

    duplication_families = tuple(
        family.name
        for family in duplication_config.get("families", ())
        if isinstance(family, DuplicateFamilyConfig)
    )
    configured_families = tuple(
        family_name
        for family_name in _as_string_list(payload.get("families"))
        if family_name in duplication_families
    )

    return RetirementAnalysisConfig(
        enabled=bool(payload.get("enabled", True)),
        family_names=configured_families or duplication_families,
        current_cycle_age_days=int(payload.get("current_cycle_age_days", 45) or 45),
        stale_age_days=int(payload.get("stale_age_days", 180) or 180),
        dead_score_threshold=int(payload.get("dead_score_threshold", 6) or 6),
        wip_markers=tuple(
            marker.casefold()
            for marker in (
                _as_string_list(payload.get("wip_markers"))
                or ["todo", "wip", "follow-up", "phase 2", "spike", "temporary"]
            )
        ),
        deprecation_markers=tuple(
            marker.casefold()
            for marker in (
                _as_string_list(payload.get("deprecation_markers"))
                or ["deprecated", "legacy", "obsolete", "compat", "remove after", "migration shim"]
            )
        ),
    )


def _complexity_analysis_config(
    memory_mapping: dict[str, object],
    duplication_config: dict[str, object],
    retirement_config: RetirementAnalysisConfig,
) -> ComplexityAnalysisConfig:
    payload = memory_mapping.get("complexity_analysis", {})
    if not isinstance(payload, dict):
        payload = {}

    duplication_families = tuple(
        family.name
        for family in duplication_config.get("families", ())
        if isinstance(family, DuplicateFamilyConfig)
    )
    configured_families = tuple(
        family_name
        for family_name in _as_string_list(payload.get("families"))
        if family_name in duplication_families
    )

    return ComplexityAnalysisConfig(
        enabled=bool(payload.get("enabled", True)),
        family_names=configured_families or retirement_config.family_names or duplication_families,
        complexity_score_threshold=int(payload.get("complexity_score_threshold", 4) or 4),
        removable_score_threshold=int(payload.get("removable_score_threshold", 7) or 7),
        indirection_markers=tuple(
            marker.casefold()
            for marker in (
                _as_string_list(payload.get("indirection_markers"))
                or ["helper", "helpers", "mixin", "policy", "codec", "compat", "legacy", "wrapper", "shim"]
            )
        ),
        stateful_markers=tuple(
            marker.casefold()
            for marker in (
                _as_string_list(payload.get("stateful_markers"))
                or ["checkpoint", "resume", "state", "fsm", "transition", "runner"]
            )
        ),
        deprecation_markers=retirement_config.deprecation_markers,
        blocker_anchor_limit=int(payload.get("blocker_anchor_limit", 3) or 3),
    )


def _as_string_list(value: object) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _rel_path(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _module_dotted_name(relative_path: str) -> str:
    without_suffix = relative_path.removesuffix(".py")
    return without_suffix.replace("/", ".")


def _python_surface_name(relative_path: str) -> str:
    if relative_path.endswith(PATH_PYTHON_INIT_SUFFIX):
        dotted = relative_path.removesuffix(PATH_PYTHON_INIT_SUFFIX).replace("/", ".")
    else:
        dotted = _module_dotted_name(relative_path)
    return dotted.removeprefix("src.")


def _is_ignored_repo_path(path: Path) -> bool:
    return "__pycache__" in path.parts


def _is_excluded_file_structure_path(relative_path: str, config: dict[str, object]) -> bool:
    path = Path(relative_path)
    excluded_dir_names = {
        name for name in _as_string_list(config.get("excluded_dir_names")) if name
    }
    if any(part in excluded_dir_names for part in path.parts):
        return True

    normalized = relative_path.strip("/")
    excluded_prefixes = [prefix.strip("/") for prefix in _as_string_list(config.get("excluded_prefixes")) if prefix]
    return any(normalized == prefix or normalized.startswith(f"{prefix}/") for prefix in excluded_prefixes)


def _promoted_directory_hubs(relative_path: str, config: dict[str, object]) -> list[str]:
    promoted = {entry.strip("/") for entry in _as_string_list(config.get("promoted_hubs")) if entry}
    path = Path(relative_path)
    matches: list[str] = []
    for index in range(1, len(path.parts) + 1):
        candidate = Path(*path.parts[:index]).as_posix()
        if candidate in promoted:
            matches.append(candidate)
    return matches


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
    return None  # NOSONAR


def _git_last_commit_age_days(
    root: Path,
    relative_path: str,
    today: date,
    cache: dict[str, int | None],
) -> int | None:
    if relative_path in cache:
        return cache[relative_path]
    result = subprocess.run(
        ["git", "-C", str(root), "log", "-1", "--format=%ct", "--", relative_path],
        check=False,
        capture_output=True,
        text=True,
    )
    timestamp = result.stdout.strip()
    if result.returncode != 0 or not timestamp.isdigit():
        cache[relative_path] = None
        return None
    committed_at = datetime.fromtimestamp(int(timestamp), tz=UTC).date()
    age = max(0, (today - committed_at).days)
    cache[relative_path] = age
    return age


def _path_contains_any_token(path: Path, tokens: list[str]) -> bool:
    normalized = _read_text(path).lower()
    return any(token.lower() in normalized for token in tokens)


def _extract_bioetl_metrics(text: str) -> set[str]:
    return set(BIOETL_METRIC_PATTERN.findall(text))


def _dashboard_metric_index(root: Path) -> dict[NodeKey, set[str]]:  # NOSONAR
    dashboards_root = root / "grafana" / "dashboards"
    if not dashboards_root.is_dir():
        return {}
    metric_index: dict[NodeKey, set[str]] = {}
    for dashboard_path in sorted(dashboards_root.glob("*.json")):
        payload = _read_json(dashboard_path)
        metrics: set[str] = set()
        stack = list(payload.get("panels", [])) if isinstance(payload.get("panels"), list) else []
        while stack:
            panel = stack.pop()
            if not isinstance(panel, dict):
                continue
            nested = panel.get("panels")
            if isinstance(nested, list):
                stack.extend(nested)
            targets = panel.get("targets")
            if not isinstance(targets, list):
                continue
            for target in targets:
                if not isinstance(target, dict):
                    continue
                expr = target.get("expr")
                if isinstance(expr, str):
                    metrics.update(_extract_bioetl_metrics(expr))
        metric_index[NodeKey("dashboard_surface", dashboard_path.stem)] = metrics
    return metric_index


def _parse_python_ast(path: Path) -> ast.AST | None:
    if not path.is_file() or path.suffix != ".py":
        return None
    try:
        return ast.parse(_read_text(path), filename=str(path))
    except SyntaxError:
        return None


def _base_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return _base_name(node.value)
    if isinstance(node, ast.Call):
        return _base_name(node.func)
    return ""


def _signature_hash(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = node.args
    payload = {
        "async": isinstance(node, ast.AsyncFunctionDef),
        "posonly": len(args.posonlyargs),
        "args": len(args.args),
        "kwonly": len(args.kwonlyargs),
        "vararg": args.vararg is not None,
        "kwarg": args.kwarg is not None,
        "decorators": len(node.decorator_list),
    }
    encoded = json.dumps(payload, sort_keys=True)
    return hashlib.sha1(encoded.encode("utf-8")).hexdigest()


class _ShapeNormalizer(ast.NodeTransformer):
    def visit_arg(self, node: ast.arg) -> ast.AST:  # noqa: N802
        node.arg = "ARG"
        node.annotation = None
        return node

    def visit_Name(self, node: ast.Name) -> ast.AST:  # noqa: N802
        return ast.copy_location(ast.Name(id="VAR", ctx=node.ctx), node)

    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:  # noqa: N802
        value = self.visit(node.value)
        return ast.copy_location(ast.Attribute(value=value, attr="ATTR", ctx=node.ctx), node)

    def visit_Constant(self, node: ast.Constant) -> ast.AST:  # noqa: N802
        value = node.value
        if value is None or isinstance(value, bool):
            return node
        if isinstance(value, str):
            node.value = "STR"
        elif isinstance(value, (int, float, complex)):
            node.value = 0
        elif isinstance(value, bytes):
            node.value = b"BYTES"
        else:
            node.value = "CONST"
        return node


def _normalized_callable_hash(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    module = ast.Module(body=node.body, type_ignores=[])
    normalized = _ShapeNormalizer().visit(module)
    ast.fix_missing_locations(normalized)
    dumped = ast.dump(normalized, annotate_fields=True, include_attributes=False)
    return hashlib.sha1(dumped.encode("utf-8")).hexdigest()


def _callable_ast_node_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    return sum(1 for _ in ast.walk(node))


_CONTROL_FLOW_NODES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.Match,
    ast.IfExp,
    ast.With,
    ast.AsyncWith,
)


def _callable_branch_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    count = 0
    for child in ast.walk(node):
        if isinstance(child, _CONTROL_FLOW_NODES):
            count += 1
        elif isinstance(child, ast.BoolOp):
            count += max(0, len(child.values) - 1)
        elif isinstance(child, ast.comprehension):
            count += len(child.ifs)
    return count


def _callable_max_nesting_depth(node: ast.AST) -> int:
    def visit(current: ast.AST, depth: int) -> int:
        max_depth = depth
        for child in ast.iter_child_nodes(current):
            next_depth = depth + 1 if isinstance(child, _CONTROL_FLOW_NODES) else depth
            max_depth = max(max_depth, visit(child, next_depth))
        return max_depth

    return visit(node, 0)


def _callable_call_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    return sum(1 for child in ast.walk(node) if isinstance(child, ast.Call))


def _callable_helper_call_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    tokens = ("_", "helper", "policy", "codec", "mixin", "fsm", "compat")
    count = 0
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func_name = _base_name(child.func).casefold()
        if func_name and any(token in func_name for token in tokens):
            count += 1
    return count


def _semantic_tags(relative_path: str, symbol_name: str) -> tuple[str, ...]:
    normalized = f"{relative_path} {symbol_name}".lower()
    tags = []
    for tag in (
        "normalize",
        "health",
        "retry",
        "fallback",
        "merge",
        "join",
        "request",
        "response",
        "contract",
        "schema",
        "manifest",
        "lineage",
        "metadata",
        "pipeline",
    ):
        if tag in normalized:
            tags.append(tag)
    return tuple(sorted(set(tags)))


def _family_for_path(relative_path: str, config: dict[str, object]) -> DuplicateFamilyConfig | None:
    families = config.get("families", ())
    if not isinstance(families, tuple):
        return None
    best: DuplicateFamilyConfig | None = None
    for family in families:
        if not isinstance(family, DuplicateFamilyConfig):
            continue
        if any(relative_path == root or relative_path.startswith(f"{root}/") for root in family.roots):
            if best is None or max(len(root) for root in family.roots) > max(len(root) for root in best.roots):
                best = family
    return best


def _is_protocol_base(node: ast.expr) -> bool:
    if isinstance(node, ast.Name):
        return node.id == "Protocol"
    if isinstance(node, ast.Attribute):
        return node.attr == "Protocol"
    if isinstance(node, ast.Subscript):
        return _is_protocol_base(node.value)
    return False


def _is_dataframe_model_base(node: ast.expr) -> bool:
    if isinstance(node, ast.Name):
        return node.id == "DataFrameModel"
    if isinstance(node, ast.Attribute):
        return node.attr == "DataFrameModel"
    if isinstance(node, ast.Subscript):
        return _is_dataframe_model_base(node.value)
    return False


def _protocol_class_names(path: Path) -> list[str]:
    tree = _parse_python_ast(path)
    if tree is None:
        return []

    protocol_names: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if any(_is_protocol_base(base) for base in node.bases):
            protocol_names.append(node.name)
    return protocol_names


def _dataframe_model_class_names(path: Path) -> list[str]:
    tree = _parse_python_ast(path)
    if tree is None:
        return []

    class_names: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if any(_is_dataframe_model_base(base) for base in node.bases):
            class_names.append(node.name)
    return class_names


def _imported_symbols(path: Path) -> list[tuple[str, str, str]]:
    tree = _parse_python_ast(path)
    if tree is None:
        return []

    imports: list[tuple[str, str, str]] = []
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        for alias in node.names:
            imports.append((node.module, alias.name, alias.asname or alias.name))
    return imports

def _build_port_surface_catalog(  # NOSONAR
    root: Path,
) -> tuple[list[PortSurfaceDescriptor], dict[str, set[str]], dict[str, dict[str, str]]]:
    ports_root = root / "src" / "bioetl" / "domain" / "ports"
    if not ports_root.is_dir():
        return [], {}, {}

    descriptors: list[PortSurfaceDescriptor] = []
    module_surfaces: dict[str, set[str]] = {}
    symbol_index: dict[str, dict[str, str]] = {}
    init_paths: list[tuple[str, Path]] = []

    for port_path in sorted(ports_root.rglob("*.py")):
        if _is_ignored_repo_path(port_path) or "noop" in port_path.parts:
            continue
        relative_path = _rel_path(root, port_path)
        module_name = _python_surface_name(relative_path)
        init_paths.append((module_name, port_path)) if port_path.name == PATH_PYTHON_INIT_FILE else None
        for class_name in _protocol_class_names(port_path):
            surface_name = f"{module_name}.{class_name}"
            descriptors.append(
                PortSurfaceDescriptor(
                    surface_name=surface_name,
                    class_name=class_name,
                    module_name=module_name,
                    source_path=relative_path,
                )
            )
            module_surfaces.setdefault(module_name, set()).add(surface_name)
            symbol_index.setdefault(module_name, {})[class_name] = surface_name

    changed = True
    while changed:
        changed = False
        for module_name, init_path in init_paths:
            exported_surfaces = module_surfaces.setdefault(module_name, set())
            exported_symbols = symbol_index.setdefault(module_name, {})
            for imported_module, imported_name, alias_name in _imported_symbols(init_path):
                if not imported_module.startswith(PORT_MODULE_PREFIX):
                    continue
                target = symbol_index.get(imported_module, {}).get(imported_name)
                if target is None:
                    continue
                if exported_symbols.get(alias_name) != target:
                    exported_symbols[alias_name] = target
                    changed = True
                if target not in exported_surfaces:
                    exported_surfaces.add(target)
                    changed = True

    return descriptors, module_surfaces, symbol_index  # NOSONAR
    # NOSONAR

def _imported_port_surfaces(  # NOSONAR
    path: Path,
    port_module_surfaces: dict[str, set[str]],
    port_symbol_index: dict[str, dict[str, str]],
) -> set[str]:
    tree = _parse_python_ast(path)
    if tree is None:
        return set()

    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(PORT_MODULE_PREFIX):
                    imported.update(port_module_surfaces.get(alias.name, set()))
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.module.startswith(PORT_MODULE_PREFIX):
                if any(alias.name == "*" for alias in node.names):
                    imported.update(port_module_surfaces.get(node.module, set()))
                    continue
                for alias in node.names:
                    target = port_symbol_index.get(node.module, {}).get(alias.name)
                    if target is not None:
                        imported.add(target)
    return imported


def _resolve_python_module_surface(root: Path, module_name: str) -> NodeKey | None:
    relative_py = Path("src") / Path(*module_name.split("."))
    file_candidate = root / relative_py.with_suffix(".py")
    if file_candidate.is_file():
        return NodeKey("module_surface", _rel_path(root, file_candidate))
    init_candidate = root / relative_py / PATH_PYTHON_INIT_FILE
    if init_candidate.is_file():
        return NodeKey("module_surface", _rel_path(root, init_candidate))
    return None  # NOSONAR

def _imported_repo_modules(path: Path, prefixes: tuple[str, ...]) -> set[str]:  # NOSONAR
    tree = _parse_python_ast(path)
    if tree is None:
        return set()

    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(prefixes):
                    imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.module.startswith(prefixes):
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
            dimensions.add(dim)  # NOSONAR
    return dimensions

def _select_alert_targets(  # NOSONAR
    snapshot: GraphSnapshot,
    alert_name: str,
    group_name: str,
    expr: str,
    dimensions: set[str],
    pipeline_nodes: dict[str, NodeKey],
    provider_nodes: list[NodeKey],
    contract_nodes: dict[str, NodeKey],
    memory_mapping: dict[str, object],
) -> tuple[list[NodeKey], list[NodeKey], list[NodeKey]]:
    normalized = f"{group_name} {expr}".lower()
    alerts_config = memory_mapping.get("alerts")
    groups = alerts_config.get("groups") if isinstance(alerts_config, dict) else {}
    rules = alerts_config.get("rules") if isinstance(alerts_config, dict) else {}
    group_rule = groups.get(group_name) if isinstance(groups, dict) and isinstance(groups.get(group_name), dict) else {}
    alert_rule = rules.get(alert_name) if isinstance(rules, dict) and isinstance(rules.get(alert_name), dict) else {}

    pipeline_mode = str(alert_rule.get("pipelines", group_rule.get("pipelines", "auto")))
    pipeline_kind = str(alert_rule.get("pipeline_kind", group_rule.get("pipeline_kind", "any")))
    provider_mode = str(alert_rule.get("providers", group_rule.get("providers", "auto")))
    contract_mode = str(alert_rule.get("contracts", group_rule.get("contracts", "none")))

    pipeline_targets: list[NodeKey] = []
    if pipeline_mode == "all":
        pipeline_targets = list(pipeline_nodes.values())
    elif pipeline_mode == "entity":
        pipeline_targets = [
            node
            for node in pipeline_nodes.values()
            if snapshot.nodes[node].properties.get("pipeline_kind") == "entity"
        ]
    elif pipeline_mode == "composite":
        pipeline_targets = [
            node
            for node in pipeline_nodes.values()
            if snapshot.nodes[node].properties.get("pipeline_kind") == "composite"
        ]
    elif pipeline_mode == "auto" and "pipeline" in dimensions:
        pipeline_targets = list(pipeline_nodes.values())
        if (
            "entity" in dimensions
            or "bioetl_dq_" in normalized
            or "bioetl_silver_" in normalized
            or 'stage="bronze"' in normalized
            or "bioetl_data_freshness_seconds" in normalized
        ):
            pipeline_kind = "entity"

    if pipeline_kind in {"entity", "composite"}:
        pipeline_targets = [
            node
            for node in pipeline_targets
            if snapshot.nodes[node].properties.get("pipeline_kind") == pipeline_kind
        ]

    provider_targets: list[NodeKey] = []
    provider_mode_is_auto = provider_mode == "auto"
    provider_matches_dimensions = (
        "provider" in dimensions
        or "provider_health" in normalized
        or "bioetl_health_check_" in normalized
    )
    include_all_providers = provider_mode == "all" or (
        provider_mode_is_auto and provider_matches_dimensions
    )
    if include_all_providers:
        provider_targets = provider_nodes

    contract_targets: list[NodeKey] = []
    if contract_mode == "all":
        contract_targets = list(contract_nodes.values())
    elif contract_mode == "mapped":
        mapped_contracts = {
            relation.target
            for relation in snapshot.relations.values()
            if relation.source in pipeline_targets
            and relation.relation_type == "DEPENDS_ON"
            and relation.target.label == "contract_surface"
        }
        contract_targets = sorted(mapped_contracts, key=lambda node: node.name)

    return (
        sorted(set(pipeline_targets), key=lambda node: node.name),
        sorted(set(provider_targets), key=lambda node: node.name),
        sorted(set(contract_targets), key=lambda node: node.name),
    )


def _select_alert_dashboards(
    alert_name: str,
    group_name: str,
    expr: str,
    dashboard_metrics: dict[NodeKey, set[str]],
    memory_mapping: dict[str, object],
) -> list[NodeKey]:
    alerts_config = memory_mapping.get("alerts")
    rules = alerts_config.get("rules") if isinstance(alerts_config, dict) else {}
    dashboard_fallbacks = (
        alerts_config.get("dashboard_fallbacks")
        if isinstance(alerts_config, dict) and isinstance(alerts_config.get("dashboard_fallbacks"), dict)
        else {}
    )
    alert_rule = rules.get(alert_name) if isinstance(rules, dict) and isinstance(rules.get(alert_name), dict) else {}
    fallback_groups = dashboard_fallbacks.get("groups") if isinstance(dashboard_fallbacks, dict) else {}

    explicit_dashboards = {
        NodeKey("dashboard_surface", name)
        for name in _as_string_list(alert_rule.get("dashboards"))
    }
    common_dashboards = {
        NodeKey("dashboard_surface", name)
        for name in _as_string_list(dashboard_fallbacks.get("common"))
    }
    group_dashboards = {
        NodeKey("dashboard_surface", name)
        for name in _as_string_list(
            fallback_groups.get(group_name) if isinstance(fallback_groups, dict) else None
        )
    }

    metrics = _extract_bioetl_metrics(expr)
    metric_dashboards = {
        dashboard
        for dashboard, dashboard_metric_names in dashboard_metrics.items()
        if metrics & dashboard_metric_names
    }

    selected = set(explicit_dashboards)
    selected.update(metric_dashboards)
    if not metric_dashboards:
        selected.update(group_dashboards)
    selected.update(common_dashboards)
    return sorted(selected, key=lambda node: node.name)


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
        confidence="high",  # NOSONAR
    )
    _add_curated_docs(snapshot, root, project, today)
    _add_decisions_and_risks(snapshot, root, project, today)
    _add_layer_topology(snapshot, root, project, today)
    _add_provider_and_config_graph(snapshot, root, project, today)
    _add_dashboard_graph(snapshot, root, project, today)
    _add_quality_and_scripts(snapshot, project, today)
    _add_test_graph(snapshot, root, project, today)
    _add_policy_surfaces(snapshot, project, today)
    _add_impact_analysis_surfaces(snapshot, root, project, today)
    _add_file_structure_surfaces(snapshot, root, project, today)
    _add_retirement_analysis_surfaces(snapshot, root, project, today, _load_memory_mapping(root))
    _add_complexity_analysis_surfaces(snapshot, root, project, today, _load_memory_mapping(root))
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
            ingest_wave="repo_sync_v1",  # NOSONAR
            confidence="high",  # NOSONAR
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
                ingest_wave="repo_sync_v1",  # NOSONAR
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
        confidence="high",  # NOSONAR
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
            source_kind="evidence_decision_summary",  # NOSONAR
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="medium",  # NOSONAR
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
            confidence="medium",  # NOSONAR
        )  # NOSONAR
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
            source_path=_rel_path(root, governance_summary),  # NOSONAR
            source_kind="evidence_decision_summary",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )  # NOSONAR
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
        )  # NOSONAR
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
                ingest_wave="repo_sync_v1",  # NOSONAR
                confidence="high",  # NOSONAR
            )
            snapshot.add_relation(layer, "CONTAINS", family, provenance="source_tree")
        for module_path in sorted(layer_path.rglob("*.py")):
            if module_path.name in {PATH_PYTHON_INIT_FILE, "__main__.py"}:
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
                module_name=module_path.stem,  # NOSONAR
                dotted_path=_module_dotted_name(relative_path),
                last_verified=today,
                ingest_wave="repo_sync_v1",  # NOSONAR
                confidence="high",  # NOSONAR
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
    for provider_path in sorted(providers_root.glob(PY_YAML_GLOB)):
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
    for entity_path in sorted(entities_root.rglob(PY_YAML_GLOB)):
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
    for composite_path in sorted(composites_root.glob(PY_YAML_GLOB)):
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
    source_surface = NodeKey("doc_source_surface", DOC_PATH_GRAFANA_DASHBOARDS_SURFACE)
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


def _add_quality_and_scripts(snapshot: GraphSnapshot, project: NodeKey, today: str) -> None:
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
                ingest_wave="repo_sync_v1",  # NOSONAR
                confidence="high",
            )
            snapshot.add_relation(script, "PROVIDES", execution, provenance="curated_execution")
            if script_path.startswith("scripts/dev/"):
                snapshot.add_relation(dev_readme, "DESCRIBES", execution, provenance="scripts_dev_readme")

    for cluster in CURATED_SCRIPT_CLUSTERS:
        readme_path = str(cluster["readme_path"])
        readme = snapshot.add_node(
            "doc_artifact",
            readme_path,
            summary=str(cluster["readme_summary"]),
            source_path=readme_path,
            source_kind="ops_doc",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(project, "HAS_DOC_ARTIFACT", readme, provenance="curated_scripts")

        entrypoint_path = str(cluster["entrypoint_path"])
        entrypoint = snapshot.add_node(
            "script_surface",
            entrypoint_path,
            summary=str(cluster["entrypoint_summary"]),
            source_path=entrypoint_path,
            source_kind="script_surface",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )

        for execution_payload in cluster["execution_paths"]:
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
            snapshot.add_relation(entrypoint, "PROVIDES", execution, provenance="curated_script_clusters")
            snapshot.add_relation(readme, "DESCRIBES", execution, provenance="curated_script_clusters")
            gate_name = execution_payload.get("gate")
            if isinstance(gate_name, str):  # NOSONAR
                snapshot.add_relation(
                    execution,
                    "EXECUTES_GATE",
                    NodeKey("quality_gate", gate_name),  # NOSONAR
                    provenance="curated_script_clusters",
                )


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


def _add_policy_surfaces(snapshot: GraphSnapshot, project: NodeKey, today: str) -> None:
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
    memory_mapping = _load_memory_mapping(root)
    port_nodes = _add_port_surfaces(snapshot, root, project, today)  # NOSONAR
    adapter_nodes = _add_adapter_surfaces(snapshot, root, project, today, port_nodes, memory_mapping)
    contract_nodes = _add_contract_surfaces(snapshot, root, project, today, memory_mapping)
    pipeline_nodes = _add_pipeline_surfaces(snapshot, root, project, today, contract_nodes, adapter_nodes)  # NOSONAR
    _add_pipeline_normalization_edges(snapshot, pipeline_nodes, memory_mapping)
    _add_pipeline_test_edges(snapshot, root, memory_mapping)
    _add_alert_surfaces(snapshot, root, project, today, pipeline_nodes, contract_nodes, memory_mapping)
    _add_governance_edges(snapshot, port_nodes, adapter_nodes, pipeline_nodes, contract_nodes)  # NOSONAR
    _add_pipeline_operational_edges(snapshot, pipeline_nodes, memory_mapping)
    _extract_code_duplication_surfaces(snapshot, root, project, today, memory_mapping)


def _add_file_structure_surfaces(snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str) -> None:
    memory_mapping = _load_memory_mapping(root)
    config = _file_structure_config(memory_mapping)
    zone_roots = config["repo_zones"]

    for zone_name, relative_roots in zone_roots.items():
        zone = snapshot.add_node(
            "repo_zone",
            zone_name,
            summary=f"Primary repository zone `{zone_name}`.",
            source_kind="file_structure_zone",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(project, "HAS_REPO_ZONE", zone, provenance="file_structure")

        for relative_root in relative_roots:
            zone_root = root / relative_root
            if not zone_root.is_dir():
                continue
            for current_dir, dirnames, _ in os.walk(zone_root):
                current_path = Path(current_dir)
                relative_dir = _rel_path(root, current_path)
                if _is_excluded_file_structure_path(relative_dir, config):
                    dirnames[:] = []
                    continue

                dirnames[:] = sorted(
                    name
                    for name in dirnames
                    if not _is_excluded_file_structure_path(_rel_path(root, current_path / name), config)
                )
                directory = snapshot.add_node(
                    "directory_surface",
                    relative_dir,
                    summary=f"Primary repository directory `{relative_dir}`.",
                    source_path=relative_dir,
                    source_kind="file_structure_directory",
                    repo_zone=zone_name,
                    depth=len(Path(relative_dir).parts),
                    is_primary=True,
                    last_verified=today,
                    ingest_wave="repo_sync_v1",
                    confidence="high",
                )
                if relative_dir == relative_root:
                    snapshot.add_relation(zone, "CONTAINS", directory, provenance="file_structure")
                else:
                    parent_key = NodeKey("directory_surface", _rel_path(root, current_path.parent))
                    snapshot.add_relation(parent_key, "CONTAINS", directory, provenance="file_structure")

    source_backed_labels = {
        "layer_family",
        "package_family",
        "module_surface",
        "class_surface",
        "function_surface",
        "method_surface",
        "doc_source_surface",
        "doc_artifact",
        "policy_surface",
        "provider_surface",
        "entity_config",
        "composite_config",
        "config_artifact",
        "dashboard_surface",
        "script_surface",
        "test_surface",
        "test_artifact",
        "pipeline_surface",
        "contract_surface",
        "alert_surface",
    }
    for node in tuple(snapshot.nodes.values()):
        if node.key.label not in source_backed_labels:
            continue
        source_path_value = node.properties.get("source_path")
        if not isinstance(source_path_value, str) or not source_path_value:
            continue
        if _is_excluded_file_structure_path(source_path_value, config):
            continue

        source_path = root / source_path_value
        if source_path.is_dir():
            directory_key = NodeKey("directory_surface", source_path_value)
            if directory_key in snapshot.nodes:
                snapshot.add_relation(directory_key, "HOUSES", node.key, provenance="file_structure")
            for promoted_hub in _promoted_directory_hubs(source_path_value, config):
                hub_key = NodeKey("directory_surface", promoted_hub)
                if hub_key in snapshot.nodes:
                    snapshot.add_relation(hub_key, "HOUSES", node.key, provenance="file_structure")
            continue
        if not source_path.is_file():
            continue

        parent_relative = _rel_path(root, source_path.parent)
        file_surface = snapshot.add_node(
            "file_surface",
            source_path_value,
            summary=f"Primary repository file `{source_path_value}`.",
            source_path=source_path_value,
            source_kind="file_structure_file",
            repo_zone=next(
                (
                    zone_name
                    for zone_name, relative_roots in zone_roots.items()
                    if any(
                        source_path_value == zone_root or source_path_value.startswith(f"{zone_root}/")
                        for zone_root in relative_roots
                    )
                ),
                None,
            ),
            suffix=source_path.suffix,
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        directory_key = NodeKey("directory_surface", parent_relative)
        if directory_key in snapshot.nodes:
            snapshot.add_relation(directory_key, "CONTAINS", file_surface, provenance="file_structure")
            snapshot.add_relation(directory_key, "HOUSES", node.key, provenance="file_structure")
        for promoted_hub in _promoted_directory_hubs(parent_relative, config):
            hub_key = NodeKey("directory_surface", promoted_hub)
            if hub_key in snapshot.nodes:
                snapshot.add_relation(hub_key, "HOUSES", node.key, provenance="file_structure")
        snapshot.add_relation(file_surface, "BACKS", node.key, provenance="file_structure")

    relation_backed_types = {"BACKED_BY", "DESCRIBED_IN", "DEFINED_BY"}
    file_backed_labels = {"doc_artifact", "config_artifact", "module_surface", "script_surface", "test_artifact"}
    for relation in tuple(snapshot.relations.values()):
        if relation.relation_type not in relation_backed_types:
            continue
        if relation.target.label not in file_backed_labels:
            continue
        target_node = snapshot.nodes.get(relation.target)
        if target_node is None:
            continue
        source_path_value = target_node.properties.get("source_path")
        if not isinstance(source_path_value, str) or not source_path_value:
            continue
        if _is_excluded_file_structure_path(source_path_value, config):
            continue

        target_path = root / source_path_value
        if target_path.is_dir():
            parent_relative = source_path_value
        elif target_path.is_file():
            parent_relative = _rel_path(root, target_path.parent)
        else:
            continue

        directory_key = NodeKey("directory_surface", parent_relative)
        if directory_key in snapshot.nodes:
            snapshot.add_relation(directory_key, "HOUSES", relation.source, provenance="file_structure_inferred")
        for promoted_hub in _promoted_directory_hubs(parent_relative, config):
            hub_key = NodeKey("directory_surface", promoted_hub)
            if hub_key in snapshot.nodes:
                snapshot.add_relation(hub_key, "HOUSES", relation.source, provenance="file_structure_inferred")


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
    facade = snapshot.add_node(
        "port_surface",
        PORT_MODULE_PREFIX,
        summary="Canonical facade exporting stable domain port protocols.",
        source_path=f"src/bioetl/domain/ports/{PATH_PYTHON_INIT_FILE}",
        source_kind="domain_port_facade",
        granularity="facade",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    port_nodes.add(facade)
    snapshot.add_relation(project, "HAS_PORT", facade, provenance="impact_ports")
    if family in snapshot.nodes:
        snapshot.add_relation(family, "CONTAINS", facade, provenance="impact_ports")
    facade_module = NodeKey("module_surface", f"src/bioetl/domain/ports/{PATH_PYTHON_INIT_FILE}")
    if facade_module in snapshot.nodes:
        snapshot.add_relation(facade, "BACKED_BY", facade_module, provenance="impact_ports")

    descriptors, _, _ = _build_port_surface_catalog(root)
    for descriptor in descriptors:
        port = snapshot.add_node(
            "port_surface",
            descriptor.surface_name,
            summary=f"Domain port protocol `{descriptor.class_name}`.",
            source_path=descriptor.source_path,
            source_kind="domain_port_protocol",
            port_name=descriptor.class_name,
            port_module=descriptor.module_name,
            granularity="protocol_class",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        port_nodes.add(port)
        snapshot.add_relation(project, "HAS_PORT", port, provenance="impact_ports")
        snapshot.add_relation(facade, "CONTAINS", port, provenance="impact_ports")  # NOSONAR
        if family in snapshot.nodes:
            snapshot.add_relation(family, "CONTAINS", port, provenance="impact_ports")
        module_key = NodeKey("module_surface", descriptor.source_path)
        if module_key in snapshot.nodes:  # NOSONAR
            snapshot.add_relation(port, "BACKED_BY", module_key, provenance="impact_ports")
    return port_nodes


def _add_adapter_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    port_nodes: set[NodeKey],
    memory_mapping: dict[str, object],
) -> dict[str, NodeKey]:
    adapters_root = root / "src" / "bioetl" / "infrastructure" / "adapters"
    if not adapters_root.is_dir():
        return {}

    adapter_family = NodeKey("package_family", "infrastructure/adapters")
    port_names = {node.name for node in port_nodes}
    _, port_module_surfaces, port_symbol_index = _build_port_surface_catalog(root)
    adapter_nodes: dict[str, NodeKey] = {}
    adapter_mapping = memory_mapping.get("adapters")
    fine_grained_enabled = bool(
        adapter_mapping.get("fine_grained_enabled", True)
    ) if isinstance(adapter_mapping, dict) else True

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
                if fine_grained_enabled and module_path.name != PATH_PYTHON_INIT_FILE:
                    impl_relative_path = _rel_path(root, module_path)
                    impl_surface_name = _python_surface_name(impl_relative_path)
                    impl_node = snapshot.add_node(
                        "adapter_impl_surface",
                        impl_surface_name,
                        summary=f"Concrete adapter implementation `{impl_surface_name}`.",
                        source_path=impl_relative_path,
                        source_kind="adapter_impl_module",
                        adapter_kind="implementation_module",
                        granularity="concrete_module",
                        last_verified=today,
                        ingest_wave="repo_sync_v1",
                        confidence="high",
                    )
                    snapshot.add_relation(adapter, "CONTAINS", impl_node, provenance="impact_adapter_impls")
                    impl_module_key = NodeKey("module_surface", impl_relative_path)
                    if impl_module_key in snapshot.nodes:
                        snapshot.add_relation(impl_node, "BACKED_BY", impl_module_key, provenance="impact_adapter_impls")
                    for port_name in sorted(
                        _imported_port_surfaces(module_path, port_module_surfaces, port_symbol_index)
                    ):
                        if port_name in port_names:
                            snapshot.add_relation(
                                impl_node,
                                "DEPENDS_ON",
                                NodeKey("port_surface", port_name),
                                provenance="impact_adapter_impls",
                            )
                imported_ports.update(
                    _imported_port_surfaces(module_path, port_module_surfaces, port_symbol_index)
                )
            for port_name in sorted(imported_ports):
                if port_name in port_names:
                    snapshot.add_relation(
                        adapter,
                        "DEPENDS_ON",
                NodeKey("port_surface", port_name),  # NOSONAR
                provenance="impact_adapters",
            )
            continue

        if child.suffix != ".py" or child.name == PATH_PYTHON_INIT_FILE:
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
        for port_name in sorted(_imported_port_surfaces(child, port_module_surfaces, port_symbol_index)):
            if port_name in port_names:
                snapshot.add_relation(
                    adapter,  # NOSONAR
                    "DEPENDS_ON",
                    NodeKey("port_surface", port_name),
                    provenance="impact_adapters",
                )  # NOSONAR

    return adapter_nodes


def _add_contract_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    memory_mapping: dict[str, object],
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

    contracts_mapping = memory_mapping.get("contracts")
    source_prefixes = tuple(
        _as_string_list(
            contracts_mapping.get("registry_source_prefixes")
            if isinstance(contracts_mapping, dict)
            else None
        )
        or [
            "bioetl.domain.contracts.gold",
            "bioetl.domain.schemas",
        ]
    )
    control_plane_modules = _as_string_list(
        contracts_mapping.get("control_plane_modules") if isinstance(contracts_mapping, dict) else None
    )
    control_plane_runtime_modules = _as_string_list(
        contracts_mapping.get("control_plane_runtime_modules") if isinstance(contracts_mapping, dict) else None
    )
    lineage_modules = _as_string_list(
        contracts_mapping.get("lineage_modules") if isinstance(contracts_mapping, dict) else None
    )
    lineage_runtime_modules = _as_string_list(
        contracts_mapping.get("lineage_runtime_modules") if isinstance(contracts_mapping, dict) else None
    )
    control_plane_docs = _as_string_list(
        contracts_mapping.get("control_plane_docs") if isinstance(contracts_mapping, dict) else None
    )
    lineage_docs = _as_string_list(
        contracts_mapping.get("lineage_docs") if isinstance(contracts_mapping, dict) else None
    )
    control_plane_anchor_fields = _as_string_list(
        contracts_mapping.get("control_plane_anchor_fields") if isinstance(contracts_mapping, dict) else None
    )
    lineage_anchor_fields = _as_string_list(
        contracts_mapping.get("lineage_anchor_fields") if isinstance(contracts_mapping, dict) else None
    )

    contract_nodes: dict[str, NodeKey] = {}
    for contract_ref, raw_entry in sorted(entries.items()):
        if not isinstance(contract_ref, str) or not isinstance(raw_entry, dict):
            continue
        identity = raw_entry.get("identity") if isinstance(raw_entry.get("identity"), dict) else {}
        contract = snapshot.add_node(
            "contract_surface",
            contract_ref,
            summary=f"Published contract surface `{contract_ref}`.",
            source_path=_rel_path(root, registry_path),
            source_kind="contract_registry",
            status=raw_entry.get("status"),
            contract_version=identity.get("contract_version"),
            compatibility_level=identity.get("compatibility_level"),
            schema_hash=identity.get("schema_hash"),
            dq_policy_ref=raw_entry.get("dq_policy_ref") or identity.get("dq_policy_ref"),
            rule_bundle_version=raw_entry.get("rule_bundle_version") or identity.get("rule_bundle_version"),
            owners=raw_entry.get("owners"),
            supported_versions=raw_entry.get("supported_versions"),
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
                for imported_module in sorted(
                    _imported_repo_modules(
                        resolved,
                        source_prefixes,
                    )
                ):
                    dependency_key = _resolve_python_module_surface(root, imported_module)
                    if dependency_key is not None and dependency_key in snapshot.nodes:
                        snapshot.add_relation(contract, "DEPENDS_ON", dependency_key, provenance="impact_contracts")
                schema_classes = _dataframe_model_class_names(resolved)
                if schema_classes:
                    snapshot.add_node(
                        "contract_surface",
                        contract_ref,
                        schema_classes=schema_classes,
                    )

        contract_config_path = (root / "configs" / "contracts" / contract_ref.replace(".", "/")).with_suffix(".yaml")
        if contract_config_path.is_file():
            contract_config = _read_yaml(contract_config_path)
            snapshot.add_node(
                "contract_surface",
                contract_ref,
                contract_config_version=contract_config.get("contract_version"),
                contract_config_ref=contract_config.get("contract_ref"),
                soft_fail_threshold=contract_config.get("soft_fail_threshold"),
                hard_fail_threshold=contract_config.get("hard_fail_threshold"),
                strict_validation=contract_config.get("strict_validation"),
                invalid_record_policy=contract_config.get("invalid_record_policy"),
                default_disposition_policy=contract_config.get("default_disposition_policy"),
            )
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

        for module_path in control_plane_modules:
            resolved_module = root / module_path
            if not resolved_module.is_file() or not _path_contains_any_token(resolved_module, control_plane_anchor_fields):
                continue
            module_key = NodeKey("module_surface", _rel_path(root, resolved_module))
            if module_key in snapshot.nodes:
                snapshot.add_relation(contract, "DEPENDS_ON", module_key, provenance="impact_contracts_control_plane")

        for module_path in control_plane_runtime_modules:
            resolved_module = root / module_path
            if not resolved_module.is_file():
                continue
            module_key = NodeKey("module_surface", _rel_path(root, resolved_module))
            if module_key in snapshot.nodes:
                snapshot.add_relation(contract, "DEPENDS_ON", module_key, provenance="impact_contracts_runtime")

        for module_path in lineage_modules:
            resolved_module = root / module_path
            if not resolved_module.is_file() or not _path_contains_any_token(resolved_module, lineage_anchor_fields):
                continue
            module_key = NodeKey("module_surface", _rel_path(root, resolved_module))
            if module_key in snapshot.nodes:
                snapshot.add_relation(contract, "DEPENDS_ON", module_key, provenance="impact_contracts_lineage")

        for module_path in lineage_runtime_modules:
            resolved_module = root / module_path
            if not resolved_module.is_file():
                continue
            module_key = NodeKey("module_surface", _rel_path(root, resolved_module))
            if module_key in snapshot.nodes:
                snapshot.add_relation(contract, "DEPENDS_ON", module_key, provenance="impact_contracts_lineage_runtime")

        for doc_path in control_plane_docs:
            resolved_doc = root / doc_path
            if not resolved_doc.is_file() or not _path_contains_any_token(resolved_doc, control_plane_anchor_fields):
                continue
            artifact = snapshot.add_node(
                "doc_artifact",
                doc_path,
                summary=f"Control-plane contract reference for `{contract_ref}`.",
                source_path=doc_path,
                source_kind="control_plane_contract_doc",
                last_verified=today,
                ingest_wave="repo_sync_v1",
                confidence="high",
            )
            snapshot.add_relation(contract, "DESCRIBED_IN", artifact, provenance="impact_contracts_control_plane")

        for doc_path in lineage_docs:
            resolved_doc = root / doc_path
            if not resolved_doc.is_file() or not _path_contains_any_token(resolved_doc, lineage_anchor_fields):
                continue
            artifact = snapshot.add_node(
                "doc_artifact",
                doc_path,
                summary=f"Lineage/traceability contract reference for `{contract_ref}`.",
                source_path=doc_path,
                source_kind="lineage_contract_doc",
                last_verified=today,  # NOSONAR
                ingest_wave="repo_sync_v1",
                confidence="high",
            )
            snapshot.add_relation(contract, "DESCRIBED_IN", artifact, provenance="impact_contracts_lineage")  # NOSONAR

    return contract_nodes


def _extract_code_duplication_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    memory_mapping: dict[str, object],
) -> None:
    config = _duplication_analysis_config(memory_mapping)
    if not bool(config.get("enabled", True)):
        return

    min_cluster_size = int(config.get("min_cluster_size", 2))
    min_ast_nodes = int(config.get("min_ast_nodes", 12))

    class_descriptors: dict[NodeKey, ClassDescriptor] = {}
    callable_descriptors: dict[NodeKey, CallableDescriptor] = {}
    class_name_index: dict[str, list[NodeKey]] = {}

    for module in tuple(snapshot.nodes.values()):
        if module.key.label != "module_surface":
            continue
        relative_path = module.key.name
        family = _family_for_path(relative_path, config)
        if family is None:
            continue

        module_path = root / relative_path
        tree = _parse_python_ast(module_path)
        if tree is None:
            continue
        dotted_path = str(module.properties.get("dotted_path") or _module_dotted_name(relative_path))

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_key = snapshot.add_node(
                    "class_surface",
                    f"{dotted_path}.{node.name}",
                    summary=f"Class surface `{node.name}` from `{dotted_path}`.",
                    source_path=relative_path,
                    source_kind="python_class_surface",
                    family_name=family.name,
                    package_family=family.package_family,
                    class_name=node.name,
                    base_names=sorted(filter(None, (_base_name(base) for base in node.bases))),
                    method_count=sum(
                        1 for child in node.body if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                    ),
                    is_mixin=node.name.endswith("Mixin"),
                    semantic_tags=list(_semantic_tags(relative_path, node.name)),
                    last_verified=today,
                    ingest_wave="repo_sync_v1",
                    confidence="medium",
                )
                snapshot.add_relation(module.key, "DECLARES", class_key, provenance="code_duplication")
                class_descriptor = ClassDescriptor(
                    node_key=class_key,
                    family_name=family.name,
                    package_family=family.package_family,
                    source_path=relative_path,
                    class_name=node.name,
                    base_names=tuple(sorted(filter(None, (_base_name(base) for base in node.bases)))),
                    method_names=tuple(
                        child.name
                        for child in node.body
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                    ),
                )
                class_descriptors[class_key] = class_descriptor
                class_name_index.setdefault(node.name, []).append(class_key)

                for child in node.body:
                    if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    method_key = snapshot.add_node(
                        "method_surface",
                        f"{dotted_path}.{node.name}.{child.name}",
                        summary=f"Method surface `{node.name}.{child.name}` from `{dotted_path}`.",
                        source_path=relative_path,
                        source_kind="python_method_surface",
                        family_name=family.name,
                        package_family=family.package_family,
                        callable_name=child.name,
                        parent_class=node.name,
                        signature_hash=_signature_hash(child),
                        ast_shape_hash=_normalized_callable_hash(child),
                        ast_node_count=_callable_ast_node_count(child),
                        branch_count=_callable_branch_count(child),
                        nesting_depth=_callable_max_nesting_depth(child),
                        call_count=_callable_call_count(child),
                        helper_call_count=_callable_helper_call_count(child),
                        semantic_tags=list(_semantic_tags(relative_path, child.name)),
                        last_verified=today,
                        ingest_wave="repo_sync_v1",
                        confidence="medium",
                    )
                    snapshot.add_relation(class_key, "DECLARES", method_key, provenance="code_duplication")
                    callable_descriptors[method_key] = CallableDescriptor(
                        node_key=method_key,
                        family_name=family.name,
                        package_family=family.package_family,
                        source_path=relative_path,
                        callable_name=child.name,
                        parent_class=node.name,
                        surface_kind="method_surface",
                        ast_shape_hash=str(snapshot.nodes[method_key].properties["ast_shape_hash"]),
                        signature_hash=str(snapshot.nodes[method_key].properties["signature_hash"]),
                        ast_node_count=int(snapshot.nodes[method_key].properties["ast_node_count"]),
                        semantic_tags=tuple(_semantic_tags(relative_path, child.name)),
                    )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_key = snapshot.add_node(
                    "function_surface",
                    f"{dotted_path}.{node.name}",
                    summary=f"Function surface `{node.name}` from `{dotted_path}`.",
                    source_path=relative_path,
                    source_kind="python_function_surface",
                    family_name=family.name,
                    package_family=family.package_family,
                    callable_name=node.name,
                    signature_hash=_signature_hash(node),
                    ast_shape_hash=_normalized_callable_hash(node),
                    ast_node_count=_callable_ast_node_count(node),
                    branch_count=_callable_branch_count(node),
                    nesting_depth=_callable_max_nesting_depth(node),
                    call_count=_callable_call_count(node),
                    helper_call_count=_callable_helper_call_count(node),
                    semantic_tags=list(_semantic_tags(relative_path, node.name)),
                    last_verified=today,
                    ingest_wave="repo_sync_v1",
                    confidence="medium",
                )
                snapshot.add_relation(module.key, "DECLARES", function_key, provenance="code_duplication")
                callable_descriptors[function_key] = CallableDescriptor(
                    node_key=function_key,
                    family_name=family.name,
                    package_family=family.package_family,
                    source_path=relative_path,
                    callable_name=node.name,
                    parent_class=None,
                    surface_kind="function_surface",
                    ast_shape_hash=str(snapshot.nodes[function_key].properties["ast_shape_hash"]),
                    signature_hash=str(snapshot.nodes[function_key].properties["signature_hash"]),
                    ast_node_count=int(snapshot.nodes[function_key].properties["ast_node_count"]),
                    semantic_tags=tuple(_semantic_tags(relative_path, node.name)),
                )

    class_method_index: dict[tuple[NodeKey, str], NodeKey] = {}
    for callable_descriptor in callable_descriptors.values():
        if callable_descriptor.surface_kind != "method_surface" or callable_descriptor.parent_class is None:
            continue
        owner_name = callable_descriptor.node_key.name.rsplit(".", 1)[0]
        owner_key = NodeKey("class_surface", owner_name)
        class_method_index[(owner_key, callable_descriptor.callable_name)] = callable_descriptor.node_key

    for class_descriptor in class_descriptors.values():
        class_node = snapshot.nodes[class_descriptor.node_key]
        base_names = class_node.properties.get("base_names")
        if not isinstance(base_names, list):
            continue
        for base_name in base_names:
            if not isinstance(base_name, str) or not base_name:
                continue
            base_candidates = class_name_index.get(base_name, [])
            if len(base_candidates) != 1:
                continue
            base_class = base_candidates[0]
            snapshot.add_relation(class_descriptor.node_key, "DEPENDS_ON", base_class, provenance="code_duplication")
            for method_name in class_descriptor.method_names:
                base_method = class_method_index.get((base_class, method_name))
                current_method = class_method_index.get((class_descriptor.node_key, method_name))
                if base_method is not None and current_method is not None:
                    snapshot.add_relation(current_method, "OVERRIDES", base_method, provenance="code_duplication")

    grouped: dict[tuple[str, str, str], list[CallableDescriptor]] = {}
    for descriptor in callable_descriptors.values():
        if descriptor.ast_node_count < min_ast_nodes:
            continue
        grouped.setdefault(
            (descriptor.family_name, descriptor.surface_kind, descriptor.ast_shape_hash),
            [],
        ).append(descriptor)

    for (family_name, surface_kind, shape_hash), members in sorted(grouped.items()):
        if len(members) < min_cluster_size:
            continue
        unique_members = sorted(members, key=lambda item: item.node_key.name)
        cluster = snapshot.add_node(
            "duplication_cluster",
            f"{family_name}:{surface_kind}:{shape_hash[:12]}",
            summary=f"Potential duplicate logic cluster for `{family_name}` {surface_kind}.",
            source_kind="semantic_duplication_cluster",
            family_name=family_name,
            surface_kind=surface_kind,
            duplicate_count=len(unique_members),
            ast_shape_hash=shape_hash,
            semantic_tags=sorted({tag for member in unique_members for tag in member.semantic_tags}),
            promotion_score=round(min(0.99, 0.35 + (0.1 * len(unique_members))), 2),
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="medium",  # NOSONAR
        )
        snapshot.add_relation(project, "CONTAINS", cluster, provenance="code_duplication")
        for member in unique_members:
            snapshot.add_relation(cluster, "CONTAINS", member.node_key, provenance="code_duplication")
        for index, left in enumerate(unique_members):
            for right in unique_members[index + 1 :]:
                snapshot.add_relation(left.node_key, "SAME_SHAPE_AS", right.node_key, provenance="code_duplication")
                snapshot.add_relation(right.node_key, "SAME_SHAPE_AS", left.node_key, provenance="code_duplication")

        family = next(
            (
                item
                for item in config.get("families", ())
                if isinstance(item, DuplicateFamilyConfig) and item.name == family_name
            ),
            None,
        )
        promotion_target: NodeKey | None = None
        if surface_kind == "method_surface":
            common_base_candidates: set[NodeKey] | None = None
            method_name = unique_members[0].callable_name
            if all(member.callable_name == method_name and member.parent_class for member in unique_members):
                for member in unique_members:
                    candidate_set = {
                        relation.target
                        for relation in snapshot.relations.values()
                        if relation.source == member.node_key
                        and relation.relation_type == "OVERRIDES"
                        and relation.target.label == "method_surface"
                    }
                    class_targets = {
                        NodeKey("class_surface", target.name.rsplit(".", 1)[0]) for target in candidate_set
                    }
                    common_base_candidates = (
                        class_targets
                        if common_base_candidates is None
                        else common_base_candidates & class_targets
                    )
                if common_base_candidates:
                    promotion_target = sorted(common_base_candidates, key=lambda item: item.name)[0]

        if promotion_target is None and isinstance(family, DuplicateFamilyConfig):
            for candidate in family.promotion_targets:
                if candidate in snapshot.nodes:
                    promotion_target = candidate
                    break
        if promotion_target is not None:
            snapshot.add_relation(cluster, "CAN_PROMOTE_TO", promotion_target, provenance="code_duplication")  # NOSONAR

        package_family = NodeKey("package_family", unique_members[0].package_family)
        for relation in tuple(snapshot.relations.values()):
            if relation.relation_type != "TESTS_PACKAGE_FAMILY" or relation.target != package_family:  # NOSONAR
                continue
            snapshot.add_relation(cluster, "COVERED_BY_TEST", relation.source, provenance="code_duplication")


def _add_retirement_analysis_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    memory_mapping: dict[str, object],
) -> None:
    duplication_config = _duplication_analysis_config(memory_mapping)
    config = _retirement_analysis_config(memory_mapping, duplication_config)
    if not config.enabled or not config.family_names:
        return

    analysis_labels = {"module_surface", "class_surface", "function_surface", "method_surface"}
    runtime_labels = {"pipeline_surface", "execution_path", "alert_surface", "adapter_surface", "adapter_impl_surface"}
    config_labels = {"entity_config", "composite_config", "provider_surface", "contract_surface", "port_surface"}
    doc_labels = {"policy_surface", "doc_source_surface", "doc_artifact", "dashboard_surface", "quality_gate"}
    test_labels = {"test_surface", "test_artifact"}
    ignored_relation_types = {
        "DECLARES",
        "OVERRIDES",
        "SAME_SHAPE_AS",
        "CONTAINS",
        "BACKS",
        "HOUSES",
        "CANDIDATE_FOR_REMOVAL",
        "OWNED_BY_CYCLE",
        "BLOCKED_FROM_DELETION_BY",
    }

    incoming: dict[NodeKey, list[GraphRelation]] = {}
    outgoing: dict[NodeKey, list[GraphRelation]] = {}
    for relation in snapshot.relations.values():
        incoming.setdefault(relation.target, []).append(relation)
        outgoing.setdefault(relation.source, []).append(relation)

    today_date = date.fromisoformat(today)
    text_cache: dict[str, str] = {}
    age_cache: dict[str, int | None] = {}

    def read_source_text(relative_path: str) -> str:
        if relative_path not in text_cache:
            path = root / relative_path
            try:
                text_cache[relative_path] = _read_text(path).casefold()
            except OSError:
                text_cache[relative_path] = ""
        return text_cache[relative_path]

    def collect_anchor_names(
        surface_key: NodeKey,
        module_key: NodeKey,
    ) -> dict[str, set[str]]:
        buckets = {
            "runtime": set(),
            "config": set(),
            "docs": set(),
            "tests": set(),
        }
        package_name: str | None = None
        module_node = snapshot.nodes.get(module_key)
        if module_node is not None:
            package_raw = module_node.properties.get("family_name")
            if isinstance(package_raw, str) and package_raw:
                package_name = package_raw

        keys_to_scan = {surface_key, module_key}
        if package_name is not None:
            keys_to_scan.add(NodeKey("package_family", package_name))

        for key in keys_to_scan:
            for relation in [*incoming.get(key, ()), *outgoing.get(key, ())]:
                if relation.relation_type in ignored_relation_types:
                    continue
                other = relation.source if relation.target == key else relation.target
                if other.label in runtime_labels:
                    buckets["runtime"].add(other.name)
                elif other.label in config_labels:
                    buckets["config"].add(other.name)
                elif other.label in doc_labels:
                    buckets["docs"].add(other.name)
                elif other.label in test_labels:
                    buckets["tests"].add(other.name)
        return buckets

    for node in sorted(snapshot.nodes.values(), key=lambda item: (item.key.label, item.key.name)):
        if node.key.label not in analysis_labels:
            continue
        source_path = node.properties.get("source_path")
        if not isinstance(source_path, str) or not source_path.endswith(".py"):
            continue
        family = _family_for_path(source_path, duplication_config)
        if family is None or family.name not in config.family_names:
            continue

        module_key = node.key if node.key.label == "module_surface" else NodeKey("module_surface", source_path)
        if module_key not in snapshot.nodes:
            continue

        anchor_names = collect_anchor_names(node.key, module_key)
        runtime_count = len(anchor_names["runtime"])
        config_count = len(anchor_names["config"])
        doc_count = len(anchor_names["docs"])
        test_count = len(anchor_names["tests"])
        only_test_referenced = test_count > 0 and runtime_count == 0 and config_count == 0 and doc_count == 0

        source_text = read_source_text(source_path)
        wip_markers = sorted({marker for marker in config.wip_markers if marker in source_text})
        deprecation_markers = sorted({marker for marker in config.deprecation_markers if marker in source_text})
        recent_age_days = _git_last_commit_age_days(root, source_path, today_date, age_cache)

        cycle_score = 0
        if recent_age_days is not None and recent_age_days <= config.current_cycle_age_days:
            cycle_score += 2
        if wip_markers:
            cycle_score += 3
        if doc_count > 0 and runtime_count == 0:
            cycle_score += 1

        deletion_score = 0
        if runtime_count == 0:
            deletion_score += 3
        if config_count == 0:
            deletion_score += 2
        if doc_count == 0:
            deletion_score += 1
        if only_test_referenced:
            deletion_score += 2
        if deprecation_markers:
            deletion_score += 2
        if recent_age_days is not None and recent_age_days >= config.stale_age_days:
            deletion_score += 2
        deletion_score -= cycle_score

        development_cycle: NodeKey | None = None
        if cycle_score >= 3:
            development_cycle = snapshot.add_node(
                "development_cycle_surface",
                f"{node.key.label}:{node.key.name}",
                summary=f"Current-cycle code surface `{node.key.name}` in `{family.name}`.",
                source_path=source_path,
                source_kind="development_cycle_surface",
                family_name=family.name,
                target_label=node.key.label,
                target_name=node.key.name,
                cycle_status="current_cycle",
                cycle_score=cycle_score,
                recent_age_days=recent_age_days,
                wip_markers=wip_markers,
                runtime_anchor_count=runtime_count,
                config_anchor_count=config_count,
                doc_anchor_count=doc_count,
                test_anchor_count=test_count,
                last_verified=today,
                ingest_wave="repo_sync_v1",
                confidence="medium",
            )
            snapshot.add_relation(project, "CONTAINS", development_cycle, provenance="retirement_analysis")
            snapshot.add_relation(node.key, "OWNED_BY_CYCLE", development_cycle, provenance="retirement_analysis")

        if deletion_score < config.dead_score_threshold:
            continue

        confidence = "high" if deletion_score >= config.dead_score_threshold + 2 else "medium"
        candidate = snapshot.add_node(
            "retirement_candidate",
            f"{node.key.label}:{node.key.name}",
            summary=f"Potential dead/stale code candidate `{node.key.name}` in `{family.name}`.",
            source_path=source_path,
            source_kind="retirement_candidate",
            family_name=family.name,
            target_label=node.key.label,
            target_name=node.key.name,
            deletion_score=deletion_score,
            deletion_confidence=confidence,
            recent_age_days=recent_age_days,
            only_test_referenced=only_test_referenced,
            deprecation_markers=deprecation_markers,
            runtime_anchor_count=runtime_count,
            config_anchor_count=config_count,
            doc_anchor_count=doc_count,
            test_anchor_count=test_count,
            runtime_anchors=sorted(anchor_names["runtime"]),
            config_anchors=sorted(anchor_names["config"]),
            doc_anchors=sorted(anchor_names["docs"]),
            test_anchors=sorted(anchor_names["tests"]),
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence=confidence,
        )
        snapshot.add_relation(project, "CONTAINS", candidate, provenance="retirement_analysis")
        snapshot.add_relation(candidate, "CANDIDATE_FOR_REMOVAL", node.key, provenance="retirement_analysis")  # NOSONAR
        if development_cycle is not None:
            snapshot.add_relation(candidate, "BLOCKED_FROM_DELETION_BY", development_cycle, provenance="retirement_analysis")


def _add_complexity_analysis_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    memory_mapping: dict[str, object],
) -> None:
    duplication_config = _duplication_analysis_config(memory_mapping)
    retirement_config = _retirement_analysis_config(memory_mapping, duplication_config)
    config = _complexity_analysis_config(memory_mapping, duplication_config, retirement_config)
    if not config.enabled or not config.family_names:
        return

    analysis_labels = {"module_surface", "class_surface", "function_surface", "method_surface"}
    runtime_labels = {"pipeline_surface", "execution_path", "alert_surface", "adapter_surface", "adapter_impl_surface"}
    config_labels = {"entity_config", "composite_config", "provider_surface", "contract_surface", "port_surface"}
    doc_labels = {"policy_surface", "doc_source_surface", "doc_artifact", "dashboard_surface", "quality_gate"}
    test_labels = {"test_surface", "test_artifact"}
    ignored_relation_types = {
        "DECLARES",
        "OVERRIDES",
        "SAME_SHAPE_AS",
        "CONTAINS",
        "BACKS",
        "HOUSES",
        "CANDIDATE_FOR_REMOVAL",
        "OWNED_BY_CYCLE",
        "BLOCKED_FROM_DELETION_BY",
        "HAS_COMPLEXITY_SIGNAL",
        "CANDIDATE_FOR_SIMPLIFICATION",
        "JUSTIFIED_BY_RUNTIME",
        "BLOCKED_BY_VARIANCE",
    }

    incoming: dict[NodeKey, list[GraphRelation]] = {}
    outgoing: dict[NodeKey, list[GraphRelation]] = {}
    for relation in snapshot.relations.values():
        incoming.setdefault(relation.target, []).append(relation)
        outgoing.setdefault(relation.source, []).append(relation)

    text_cache: dict[str, str] = {}
    module_ast_cache: dict[str, ast.AST | None] = {}

    def read_source_text(relative_path: str) -> str:
        if relative_path not in text_cache:
            path = root / relative_path
            try:
                text_cache[relative_path] = _read_text(path).casefold()
            except OSError:
                text_cache[relative_path] = ""
        return text_cache[relative_path]

    def parse_module_ast(relative_path: str) -> ast.AST | None:
        if relative_path not in module_ast_cache:
            module_ast_cache[relative_path] = _parse_python_ast(root / relative_path)
        return module_ast_cache[relative_path]

    def collect_anchor_nodes(surface_key: NodeKey, module_key: NodeKey) -> dict[str, list[NodeKey]]:
        buckets: dict[str, set[NodeKey]] = {
            "runtime": set(),
            "config": set(),
            "docs": set(),
            "tests": set(),
        }

        def _relation_bucket_label(label: str) -> str | None:
            if label in runtime_labels:
                return "runtime"
            if label in config_labels:
                return "config"
            if label in doc_labels:
                return "docs"
            if label in test_labels:
                return "tests"
            return None

        package_name: str | None = None
        module_node = snapshot.nodes.get(module_key)
        if module_node is not None:
            package_raw = module_node.properties.get("family_name")
            if isinstance(package_raw, str) and package_raw:
                package_name = package_raw

        keys_to_scan = {surface_key, module_key}
        if package_name is not None:
            keys_to_scan.add(NodeKey("package_family", package_name))

        for key in keys_to_scan:
            for relation in [*incoming.get(key, ()), *outgoing.get(key, ())]:
                if relation.relation_type in ignored_relation_types:
                    continue
                other = relation.source if relation.target == key else relation.target
                bucket_name = _relation_bucket_label(other.label)
                if bucket_name is not None:
                    buckets[bucket_name].add(other)
        return {
            name: sorted(values, key=lambda item: (item.label, item.name))  # NOSONAR
            for name, values in buckets.items()
        }

    def resolve_ast_surface(node: GraphNode, tree: ast.AST) -> ast.AST | None:
        if node.key.label == "module_surface":
            return tree if isinstance(tree, ast.Module) else None
        if node.key.label == "class_surface":
            class_name = str(node.properties.get("class_name") or node.key.name.rsplit(".", 1)[-1])
            for child in getattr(tree, "body", ()):
                if isinstance(child, ast.ClassDef) and child.name == class_name:
                    return child
            return None
        if node.key.label == "function_surface":
            function_name = str(node.properties.get("callable_name") or node.key.name.rsplit(".", 1)[-1])
            for child in getattr(tree, "body", ()):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == function_name:
                    return child
            return None
        if node.key.label == "method_surface":
            class_name = str(node.properties.get("parent_class") or "")
            method_name = str(node.properties.get("callable_name") or node.key.name.rsplit(".", 1)[-1])
            for child in getattr(tree, "body", ()):
                if not isinstance(child, ast.ClassDef) or child.name != class_name:
                    continue
                for method in child.body:
                    if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)) and method.name == method_name:
                        return method
            return None
        return None

    def complexity_marker_buckets(
        relative_path: str,
        symbol_name: str,
        source_text: str,
    ) -> tuple[list[str], list[str], list[str]]:
        normalized = f"{relative_path} {symbol_name}".casefold()
        indirection = sorted({marker for marker in config.indirection_markers if marker in normalized or marker in source_text})
        stateful = sorted({marker for marker in config.stateful_markers if marker in normalized or marker in source_text})
        deprecation = sorted({marker for marker in config.deprecation_markers if marker in normalized or marker in source_text})
        return indirection, stateful, deprecation

    def score_from_threshold(value: int, *, low: int, high: int) -> int:
        if value >= high:
            return 2
        if value >= low:
            return 1
        return 0

    for node in sorted(snapshot.nodes.values(), key=lambda item: (item.key.label, item.key.name)):
        if node.key.label not in analysis_labels:
            continue
        source_path = node.properties.get("source_path")
        if not isinstance(source_path, str) or not source_path.endswith(".py"):
            continue
        family = _family_for_path(source_path, duplication_config)
        if family is None or family.name not in config.family_names:
            continue

        module_key = node.key if node.key.label == "module_surface" else NodeKey("module_surface", source_path)
        if module_key not in snapshot.nodes:
            continue

        tree = parse_module_ast(source_path)
        if tree is None:
            continue
        ast_surface = resolve_ast_surface(node, tree)
        if ast_surface is None:
            continue

        source_text = read_source_text(source_path)
        anchor_nodes = collect_anchor_nodes(node.key, module_key)
        runtime_anchors = anchor_nodes["runtime"]
        config_anchors = anchor_nodes["config"]
        doc_anchors = anchor_nodes["docs"]
        test_anchors = anchor_nodes["tests"]
        runtime_count = len(runtime_anchors)
        config_count = len(config_anchors)
        doc_count = len(doc_anchors)
        test_count = len(test_anchors)

        symbol_name = node.key.name.removeprefix(f"{_module_dotted_name(source_path)}.")
        indirection_markers, stateful_markers, deprecation_markers = complexity_marker_buckets(
            source_path,
            symbol_name,
            source_text,
        )

        branch_count = 0
        nesting_depth = 0
        call_count = 0
        helper_call_count = 0
        abstraction_fanout = 0
        api_surface_to_logic_ratio = 0.0

        if node.key.label in {"function_surface", "method_surface"} and isinstance(
            ast_surface, (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            branch_count = _callable_branch_count(ast_surface)
            nesting_depth = _callable_max_nesting_depth(ast_surface)
            call_count = _callable_call_count(ast_surface)
            helper_call_count = _callable_helper_call_count(ast_surface)
            abstraction_fanout = max(1, call_count)
            api_surface_to_logic_ratio = round(call_count / max(1, branch_count + nesting_depth), 2)
        elif node.key.label == "class_surface" and isinstance(ast_surface, ast.ClassDef):
            methods = [child for child in ast_surface.body if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))]
            abstraction_fanout = len(methods)
            branch_count = sum(_callable_branch_count(method) for method in methods)
            nesting_depth = max((_callable_max_nesting_depth(method) for method in methods), default=0)
            call_count = sum(_callable_call_count(method) for method in methods)
            helper_call_count = sum(_callable_helper_call_count(method) for method in methods)
            api_surface_to_logic_ratio = round(abstraction_fanout / max(1, branch_count + 1), 2)
        elif node.key.label == "module_surface" and isinstance(ast_surface, ast.Module):
            functions = [child for child in ast_surface.body if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))]
            classes = [child for child in ast_surface.body if isinstance(child, ast.ClassDef)]
            module_methods = [
                method
                for class_node in classes
                for method in class_node.body
                if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            abstraction_fanout = len(functions) + len(classes)
            branch_count = sum(_callable_branch_count(function) for function in functions)
            branch_count += sum(
                _callable_branch_count(method)
                for class_node in classes  # NOSONAR
                for method in class_node.body
                if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))  # NOSONAR
            )
            module_callables = [
                *functions,
                *module_methods,
            ]
            nesting_depth = max(
                (_callable_max_nesting_depth(function) for function in module_callables),
                default=0,  # NOSONAR
            )  # NOSONAR
            call_count = sum(_callable_call_count(function) for function in functions)  # NOSONAR
            call_count += sum(
                _callable_call_count(method)  # NOSONAR
                for method in module_methods  # NOSONAR
            )  # NOSONAR
            helper_call_count = sum(_callable_helper_call_count(function) for function in functions)  # NOSONAR
            helper_call_count += sum(
                _callable_helper_call_count(method)  # NOSONAR
                for method in module_methods  # NOSONAR
            )
            api_surface_to_logic_ratio = round(abstraction_fanout / max(1, branch_count + 1), 2)

        complexity_score = 0
        branch_count_score = score_from_threshold(branch_count, low=3, high=6)
        nesting_depth_score = score_from_threshold(nesting_depth, low=3, high=4)
        helper_call_score = score_from_threshold(helper_call_count, low=2, high=4)
        indirection_score = 2 if len(indirection_markers) >= 2 else 1 if indirection_markers else 0
        stateful_score = 2 if len(stateful_markers) >= 2 else 1 if stateful_markers else 0
        fanout_score = score_from_threshold(abstraction_fanout, low=3, high=6)
        complexity_score += (
            branch_count_score
            + nesting_depth_score
            + helper_call_score
            + indirection_score
            + stateful_score
            + fanout_score
        )

        simplification_score = complexity_score
        removable_score = complexity_score
        if runtime_count == 0:
            removable_score += 2
        if config_count == 0:
            removable_score += 2
        if doc_count == 0:
            removable_score += 1
        if test_count == 0:
            removable_score += 1
        if deprecation_markers:
            removable_score += 2

        blocked_cycles = sorted(
            {
                relation.target
                for relation in outgoing.get(node.key, ())
                if relation.relation_type == "OWNED_BY_CYCLE" and relation.target.label == "development_cycle_surface"
            },
            key=lambda item: item.name,
        )
        if blocked_cycles:
            removable_score -= 3

        if complexity_score < config.complexity_score_threshold and removable_score < config.removable_score_threshold:
            continue

        classification = "overengineered_active"
        removal_confidence = "low"
        if removable_score >= config.removable_score_threshold and not blocked_cycles:
            classification = "removable_complexity"
            removal_confidence = "high" if removable_score >= config.removable_score_threshold + 2 else "medium"
        elif runtime_count == 0 and config_count == 0 and doc_count == 0:
            classification = "overengineered_stale"
            removal_confidence = "medium"

        candidate = snapshot.add_node(
            "complexity_candidate",
            f"{node.key.label}:{node.key.name}",
            summary=f"Complexity analysis candidate for `{node.key.name}` in `{family.name}`.",
            source_path=source_path,
            source_kind="complexity_candidate",
            family_name=family.name,
            target_label=node.key.label,
            target_name=node.key.name,
            classification=classification,
            complexity_score=complexity_score,
            simplification_score=simplification_score,
            removable_score=removable_score,
            simplification_confidence="high" if simplification_score >= config.complexity_score_threshold + 2 else "medium",
            removal_confidence=removal_confidence,
            branch_count=branch_count,
            nesting_depth=nesting_depth,
            call_count=call_count,
            helper_call_count=helper_call_count,
            abstraction_fanout=abstraction_fanout,
            api_surface_to_logic_ratio=api_surface_to_logic_ratio,
            runtime_anchor_count=runtime_count,
            config_anchor_count=config_count,
            doc_anchor_count=doc_count,
            test_anchor_count=test_count,
            indirection_markers=indirection_markers,
            stateful_markers=stateful_markers,
            deprecation_markers=deprecation_markers,
            blocked_by_cycle=bool(blocked_cycles),
            runtime_anchors=[anchor.name for anchor in runtime_anchors[: config.blocker_anchor_limit]],
            config_anchors=[anchor.name for anchor in config_anchors[: config.blocker_anchor_limit]],
            doc_anchors=[anchor.name for anchor in doc_anchors[: config.blocker_anchor_limit]],  # NOSONAR
            test_anchors=[anchor.name for anchor in test_anchors[: config.blocker_anchor_limit]],
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="medium",  # NOSONAR
        )
        snapshot.add_relation(project, "CONTAINS", candidate, provenance="complexity_analysis")
        snapshot.add_relation(node.key, "HAS_COMPLEXITY_SIGNAL", candidate, provenance="complexity_analysis")
        snapshot.add_relation(candidate, "CANDIDATE_FOR_SIMPLIFICATION", node.key, provenance="complexity_analysis")
        if classification == "removable_complexity":
            snapshot.add_relation(candidate, "CANDIDATE_FOR_REMOVAL", node.key, provenance="complexity_analysis")
        for cycle in blocked_cycles:
            snapshot.add_relation(candidate, "BLOCKED_FROM_DELETION_BY", cycle, provenance="complexity_analysis")
        for anchor in runtime_anchors[: config.blocker_anchor_limit]:
            snapshot.add_relation(candidate, "JUSTIFIED_BY_RUNTIME", anchor, provenance="complexity_analysis")
        for anchor in [*config_anchors[: config.blocker_anchor_limit], *doc_anchors[: config.blocker_anchor_limit]]:
            snapshot.add_relation(candidate, "BLOCKED_BY_VARIANCE", anchor, provenance="complexity_analysis")


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
    for entity_path in sorted(entities_root.rglob(PY_YAML_GLOB)):
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
            pipeline_kind="entity",
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
    for composite_path in sorted(composites_root.glob(PY_YAML_GLOB)):
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
            pipeline_kind="composite",
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
                        provenance="impact_pipelines",  # NOSONAR
                    )
            dependencies = composite.get("dependencies")
            if isinstance(dependencies, list):
                for dependency in dependencies:  # NOSONAR
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


def _add_pipeline_normalization_edges(  # NOSONAR
    snapshot: GraphSnapshot,
    pipeline_nodes: dict[str, NodeKey],
    memory_mapping: dict[str, object],
) -> None:
    normalization_mapping = memory_mapping.get("normalization")
    if not isinstance(normalization_mapping, dict):
        return

    relation_type = str(normalization_mapping.get("relation_type", "DEPENDS_ON"))
    entity_relation_type = str(normalization_mapping.get("entity_relation_type", relation_type))
    defaults = normalization_mapping.get("defaults")
    default_entity_modules: list[str] = []
    default_composite_modules: list[str] = []
    if isinstance(defaults, dict):
        entity_defaults = defaults.get("entity")
        composite_defaults = defaults.get("composite")
        if isinstance(entity_defaults, dict):
            default_entity_modules = _as_string_list(entity_defaults.get("modules"))
        if isinstance(composite_defaults, dict):
            default_composite_modules = _as_string_list(composite_defaults.get("modules"))

    pipeline_entries = normalization_mapping.get("pipelines")
    pipeline_overrides = pipeline_entries if isinstance(pipeline_entries, dict) else {}

    for pipeline_name, pipeline_key in pipeline_nodes.items():
        pipeline_node = snapshot.nodes.get(pipeline_key)
        if pipeline_node is None:
            continue
        pipeline_kind = str(pipeline_node.properties.get("pipeline_kind", "entity"))
        modules = list(default_entity_modules if pipeline_kind == "entity" else default_composite_modules)  # NOSONAR
        pipeline_payload = pipeline_overrides.get(pipeline_name)
        if isinstance(pipeline_payload, dict):
            modules.extend(_as_string_list(pipeline_payload.get("modules")))
    # NOSONAR
    seen_modules: set[str] = set()
    entity_key = NodeKey("entity_config", pipeline_name)
    for module_path in modules:
            if module_path in seen_modules:
                continue
            seen_modules.add(module_path)
            module_key = NodeKey("module_surface", module_path)
            if module_key not in snapshot.nodes:
                continue
            snapshot.add_relation(pipeline_key, relation_type, module_key, provenance="impact_normalization")
            if pipeline_kind == "entity" and entity_key in snapshot.nodes:
                snapshot.add_relation(entity_key, entity_relation_type, module_key, provenance="impact_normalization")


def _add_pipeline_test_edges(
    snapshot: GraphSnapshot,
    root: Path,
    memory_mapping: dict[str, object],
) -> None:
    tests_mapping = memory_mapping.get("pipeline_tests")
    relation_type = str(tests_mapping.get("relation_type", "TESTED_BY")) if isinstance(tests_mapping, dict) else "TESTED_BY"
    ownership_config = (
        str(tests_mapping.get("ownership_config", DOC_PATH_TEST_MATRIX))
        if isinstance(tests_mapping, dict)
        else DOC_PATH_TEST_MATRIX
    )
    ownership_path = root / ownership_config
    if not ownership_path.is_file():
        return

    payload = _read_yaml(ownership_path)
    ownership = payload.get("entity_test_ownership")
    if not isinstance(ownership, dict):
        return
    include_provider_regression_suites = bool(
        tests_mapping.get("provider_regression_suites", True)
    ) if isinstance(tests_mapping, dict) else True

    entity_pipeline_index = {
        (str(node.properties.get("provider")), str(node.properties.get("entity"))): node.key
        for node in snapshot.nodes.values()
        if node.key.label == "pipeline_surface" and node.properties.get("pipeline_kind") == "entity"
    }
    provider_pipeline_index: dict[str, list[NodeKey]] = {}
    for node in snapshot.nodes.values():
        if node.key.label != "pipeline_surface":
            continue
        provider = node.properties.get("provider")
        if isinstance(provider, str):
            provider_pipeline_index.setdefault(provider, []).append(node.key)

    def link_test_target(pipeline_key: NodeKey, test_path: str, provenance: str) -> None:
        artifact_key = NodeKey("test_artifact", test_path)
        if artifact_key not in snapshot.nodes:
            return
        snapshot.add_relation(pipeline_key, relation_type, artifact_key, provenance=provenance)
        suite_name = TEST_SURFACES.get(str(snapshot.nodes[artifact_key].properties.get("suite", "")))
        if suite_name is not None:
            snapshot.add_relation(
                pipeline_key,
                relation_type,
                NodeKey("test_surface", suite_name),
                provenance=provenance,
            )

    for contract_ref, raw_tests in ownership.items():
        if not isinstance(contract_ref, str):
            continue
        if "." not in contract_ref:
            continue
        provider_name, entity_name = contract_ref.split(".", 1)
        pipeline_key = entity_pipeline_index.get((provider_name, entity_name))
        if pipeline_key is None:
            continue
        for test_path in _as_string_list(raw_tests):
            link_test_target(pipeline_key, test_path, "impact_pipeline_tests")

    suites = payload.get("provider_regression_suites")
    if not include_provider_regression_suites or not isinstance(suites, dict):  # NOSONAR
        return
    for suite_name, suite_payload in suites.items():
        if not isinstance(suite_payload, dict):
            continue  # NOSONAR
        providers = suite_payload.get("providers")
        if not isinstance(providers, dict):
            continue
        for provider_name, raw_test_path in providers.items():
            if not isinstance(provider_name, str) or not isinstance(raw_test_path, str):
                continue
            for pipeline_key in provider_pipeline_index.get(provider_name, []):
                link_test_target(
                    pipeline_key,
                    raw_test_path,
                    f"impact_pipeline_regression_suite:{suite_name}",
                )


def _add_alert_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    pipeline_nodes: dict[str, NodeKey],
    contract_nodes: dict[str, NodeKey],
    memory_mapping: dict[str, object],
) -> None:
    rules_root = root / "grafana" / "prometheus-rules"
    if not rules_root.is_dir():
        return

    dashboard_metrics = _dashboard_metric_index(root)
    provider_nodes = sorted(
        (key for key in snapshot.nodes if key.label == "provider_surface"),
        key=lambda node: node.name,
    )
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
                selected_pipelines, selected_providers, selected_contracts = _select_alert_targets(
                    snapshot,
                    alert_name,
                    group_name,
                    expr,
                    dimensions,
                    pipeline_nodes,
                    provider_nodes,
                    contract_nodes,
                    memory_mapping,
                )
                for pipeline in selected_pipelines:
                    snapshot.add_relation(alert, "DEPENDS_ON", pipeline, provenance="impact_alerts")
                for provider in selected_providers:
                    snapshot.add_relation(alert, "DEPENDS_ON", provider, provenance="impact_alerts")
                for contract in selected_contracts:
                    snapshot.add_relation(alert, "DEPENDS_ON", contract, provenance="impact_alerts")
                for dashboard in _select_alert_dashboards(
                    alert_name,
                    group_name,
                    expr,
                    dashboard_metrics,
                    memory_mapping,
                ):
                    if dashboard in snapshot.nodes:
                        snapshot.add_relation(alert, "OBSERVED_BY", dashboard, provenance="impact_alerts")  # NOSONAR

                runbook = annotations.get("runbook")
                if isinstance(runbook, str):
                    runbook_path = root / runbook  # NOSONAR
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


def _add_governance_edges(  # NOSONAR
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

    pipeline_policy = NodeKey("policy_surface", "pipeline assembly model")  # NOSONAR
    if pipeline_policy in snapshot.nodes:
        for pipeline in sorted(pipeline_nodes.values(), key=lambda node: node.name):
            snapshot.add_relation(pipeline_policy, "GOVERNS", pipeline, provenance="impact_governance")
    # NOSONAR

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


def _add_pipeline_operational_edges(
    snapshot: GraphSnapshot,
    pipeline_nodes: dict[str, NodeKey],
    memory_mapping: dict[str, object],
) -> None:
    pipeline_ops = memory_mapping.get("pipeline_operational")
    runtime_paths = [
        NodeKey("execution_path", name)
        for name in _as_string_list(
            pipeline_ops.get("runtime_paths") if isinstance(pipeline_ops, dict) else None
        )
    ] or [
        NodeKey("execution_path", "uv run python -m bioetl run --pipeline"),
        NodeKey(
            "execution_path",
            "\"${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python\" -m bioetl run --pipeline",
        ),
        NodeKey("execution_path", ".\\.venv-win\\Scripts\\python.exe -m bioetl run --pipeline"),
    ]
    validation_gates = [
        NodeKey("quality_gate", name)
        for name in _as_string_list(
            pipeline_ops.get("validation_gates") if isinstance(pipeline_ops, dict) else None
        )
    ] or [
        NodeKey("quality_gate", QUALITY_GATE_PYTEST),
        NodeKey("quality_gate", QUALITY_GATE_CONFIG_VALIDATION),
    ]
    dashboards_cfg = pipeline_ops.get("dashboards") if isinstance(pipeline_ops, dict) else {}
    common_dashboards = [
        NodeKey("dashboard_surface", name)
        for name in _as_string_list(dashboards_cfg.get("common") if isinstance(dashboards_cfg, dict) else None)
    ] or [
        NodeKey("dashboard_surface", "bioetl-overview-v2"),
        NodeKey("dashboard_surface", "bioetl-runtime"),
    ]
    kind_dashboards = dashboards_cfg.get("by_kind") if isinstance(dashboards_cfg, dict) else {}
    entity_dashboards = [
        NodeKey("dashboard_surface", name)
        for name in _as_string_list(kind_dashboards.get("entity") if isinstance(kind_dashboards, dict) else None)
    ] or [
        NodeKey("dashboard_surface", "bioetl-dq-v2"),
        NodeKey("dashboard_surface", "bioetl-silver-reject-explorer"),
    ]
    composite_dashboards = [
        NodeKey("dashboard_surface", name)
        for name in _as_string_list(kind_dashboards.get("composite") if isinstance(kind_dashboards, dict) else None)
    ] or [
        NodeKey("dashboard_surface", "bioetl-control-plane-v1"),
    ]

    for pipeline in sorted(pipeline_nodes.values(), key=lambda node: node.name):
        pipeline_props = snapshot.nodes[pipeline].properties
        pipeline_kind = pipeline_props.get("pipeline_kind")
        for execution_path in runtime_paths:
            if execution_path in snapshot.nodes:
                snapshot.add_relation(pipeline, "RUNS_VIA", execution_path, provenance="impact_pipeline_ops")
        for gate in validation_gates:
            if gate in snapshot.nodes:
                snapshot.add_relation(pipeline, "VALIDATED_BY", gate, provenance="impact_pipeline_ops")
        for dashboard in common_dashboards:
            if dashboard in snapshot.nodes:
                snapshot.add_relation(pipeline, "OBSERVED_BY", dashboard, provenance="impact_pipeline_ops")
        if pipeline_kind == "entity":
            for dashboard in entity_dashboards:
                if dashboard in snapshot.nodes:
                    snapshot.add_relation(pipeline, "OBSERVED_BY", dashboard, provenance="impact_pipeline_ops")
        elif pipeline_kind == "composite":
            for dashboard in composite_dashboards:
                if dashboard in snapshot.nodes:
                    snapshot.add_relation(pipeline, "OBSERVED_BY", dashboard, provenance="impact_pipeline_ops")


class Neo4jHttpClient:
    def __init__(self, base_uri: str, username: str, password: str, database: str) -> None:
        self._endpoint = f"{base_uri}/db/{database}/tx/commit"
        auth_token = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
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
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def _delete_managed_wave_nodes_statement(label: str, limit: int) -> dict[str, JsonValue]:
    return {
        "statement": (
            f"MATCH (n:`{label}`) "
            "WHERE n.ingest_wave = $ingest_wave "
            "AND coalesce(n.managed_by, $managed_by) = $managed_by "
            "WITH n LIMIT $limit "
            "DETACH DELETE n "
            "RETURN count(*) AS deleted"
        ),
        "parameters": {
            "ingest_wave": DEFAULT_INGEST_WAVE,
            "managed_by": DEFAULT_MANAGED_BY,
            "limit": limit,  # NOSONAR
        },
    }  # NOSONAR


def _prune_legacy_unmanaged_nodes_statement(managed_labels: list[str]) -> dict[str, JsonValue]:  # NOSONAR
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
    only_labels: tuple[str, ...] = (),
    only_analysis_layer: bool = False,
) -> None:
    base_uri, username, password, database = resolve_neo4j_connection(root, http_uri)
    client = Neo4jHttpClient(base_uri, username, password, database)
    sync_run = _sync_run_id()
    snapshot = _filtered_snapshot(snapshot, only_labels=only_labels, only_analysis_layer=only_analysis_layer)
    managed_labels = sorted({node.key.label for node in snapshot.nodes.values()} | set(DEFAULT_LEGACY_PRUNE_LABELS))
    node_groups: dict[str, list[dict[str, JsonValue]]] = {}
    for node in snapshot.nodes.values():
        node_groups.setdefault(node.key.label, []).append(_node_statement(node, sync_run))
    relation_groups: dict[str, list[dict[str, JsonValue]]] = {}
    for relation in snapshot.relations.values():
        relation_groups.setdefault(relation.relation_type, []).append(_relation_statement(relation, sync_run))
    core_node_groups, analysis_node_groups, core_relation_groups, analysis_relation_groups = _partition_groups(
        node_groups,
        relation_groups,
    )
    if full_reset_managed_wave:
        delete_batch_size = max(1, min(batch_size, 50))
        for label in managed_labels:
            while True:
                delete_statement = _delete_managed_wave_nodes_statement(label, delete_batch_size)
                rows = client.query(
                    delete_statement["statement"],
                    delete_statement["parameters"],
                )
                deleted = int(rows[0]["deleted"]) if rows else 0
                if deleted == 0:
                    break
    _execute_grouped_statements(client, core_node_groups, batch_size, "core node")
    analysis_node_batch_size = 1 if "complexity_candidate" in analysis_node_groups else max(1, min(batch_size, 10))
    _execute_grouped_statements(client, analysis_node_groups, analysis_node_batch_size, "analysis node")
    if prune_stale and relation_groups:
        relation_types = sorted({relation.relation_type for relation in snapshot.relations.values()})
        client.execute([_reset_managed_relations_statement(relation_types)])
    _execute_grouped_statements(client, core_relation_groups, batch_size, "core relation")
    _execute_grouped_statements(
        client,
        analysis_relation_groups,
        max(1, min(batch_size, 5)),
        "analysis relation",
    )
    _retry_critical_analysis_groups(client, analysis_node_groups, analysis_relation_groups, batch_size)
    _verify_expected_group_counts(
        client,
        analysis_node_groups if only_analysis_layer or only_labels else {},
        analysis_relation_groups if only_analysis_layer or only_labels else {},
        strict_analysis=not (only_analysis_layer or only_labels),
    )
    if only_analysis_layer or only_labels:
        _verify_expected_group_counts(  # NOSONAR
            client,
            node_groups,  # NOSONAR
            relation_groups,
            strict_analysis=False,
        )
    if prune_stale:
        client.execute([_prune_stale_relations_statement(sync_run)])
        client.execute([_prune_stale_nodes_statement(sync_run)])
    if prune_legacy_unmanaged:
        client.execute([_prune_legacy_unmanaged_nodes_statement(managed_labels)])


def _batched(items: list[T], size: int) -> list[list[T]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _execute_grouped_statements(
    client: Neo4jHttpClient,
    grouped_statements: dict[str, list[dict[str, JsonValue]]],
    batch_size: int,
    kind: str,
) -> None:
    for group_name in sorted(grouped_statements):
        statements = grouped_statements[group_name]
        grouped_batches = _batched(statements, batch_size)
        for batch_index, batch in enumerate(grouped_batches, start=1):
            try:
                client.execute(batch)
            except Exception as exc:  # pragma: no cover - depends on live backend state
                if len(batch) > 1:
                    for statement_index, statement in enumerate(batch, start=1):
                        try:
                            client.execute([statement])
                        except Exception as statement_exc:  # pragma: no cover - live backend dependent
                            parameters = statement.get("parameters", {})
                            node_name = parameters.get("name")
                            source_name = parameters.get("source_name")
                            target_name = parameters.get("target_name")
                            context = (
                                f"name={node_name!r}" if node_name is not None else
                                f"source={source_name!r}, target={target_name!r}"
                            )
                            raise RuntimeError(
                                f"Neo4j sync failed while applying {kind} group `{group_name}` "
                                f"(batch {batch_index}/{len(grouped_batches)}, "
                                f"statement {statement_index}/{len(batch)}, {context})"
                            ) from statement_exc
                    continue
                parameters = batch[0].get("parameters", {})
                node_name = parameters.get("name")
                source_name = parameters.get("source_name")
                target_name = parameters.get("target_name")
                context = (
                    f"name={node_name!r}" if node_name is not None else
                    f"source={source_name!r}, target={target_name!r}"
                )
                raise RuntimeError(
                    f"Neo4j sync failed while applying {kind} group `{group_name}` "
                    f"(batch {batch_index}/{len(grouped_batches)}, 1 statement, {context})"
                ) from exc


def _live_managed_node_count(client: Neo4jHttpClient, label: str) -> int:
    rows = client.query(
        f"MATCH (n:`{label}`) "
        "WHERE n.managed_by = $managed_by "
        "RETURN count(n) AS count",
        {"managed_by": DEFAULT_MANAGED_BY},
    )
    return int(rows[0]["count"]) if rows else 0


def _live_managed_relation_count(client: Neo4jHttpClient, relation_type: str) -> int:
    rows = client.query(
        f"MATCH ()-[r:`{relation_type}`]->() "
        "WHERE r.managed_by = $managed_by "
        "RETURN count(r) AS count",
        {"managed_by": DEFAULT_MANAGED_BY},
    )
    return int(rows[0]["count"]) if rows else 0


def _retry_critical_analysis_groups(
    client: Neo4jHttpClient,
    node_groups: dict[str, list[dict[str, JsonValue]]],
    relation_groups: dict[str, list[dict[str, JsonValue]]],
    batch_size: int,
) -> None:
    retry_batch_size = max(1, min(batch_size, 5))

    missing_node_labels = [
        label
        for label in CRITICAL_ANALYSIS_NODE_LABELS
        if label in node_groups and _live_managed_node_count(client, label) != len(node_groups[label])
    ]
    if missing_node_labels:
        _execute_grouped_statements(
            client,
            {label: node_groups[label] for label in missing_node_labels},
            retry_batch_size,
            "critical node retry",
        )

    missing_relation_types = [
        relation_type
        for relation_type in CRITICAL_ANALYSIS_RELATION_TYPES
        if relation_type in relation_groups
        and _live_managed_relation_count(client, relation_type) != len(relation_groups[relation_type])
    ]
    if missing_relation_types:
        _execute_grouped_statements(
            client,
            {relation_type: relation_groups[relation_type] for relation_type in missing_relation_types},
            retry_batch_size,
            "critical relation retry",
        )

    missing_after_retry: list[str] = []
    for label in CRITICAL_ANALYSIS_NODE_LABELS:
        if label not in node_groups:
            continue
        live_count = _live_managed_node_count(client, label)
        expected = len(node_groups[label])
        if live_count != expected:
            missing_after_retry.append(
                f"label `{label}` expected {expected}, live managed {live_count}"
            )
    for relation_type in CRITICAL_ANALYSIS_RELATION_TYPES:
        if relation_type not in relation_groups:
            continue
        live_count = _live_managed_relation_count(client, relation_type)
        expected = len(relation_groups[relation_type])
        if live_count != expected:
            missing_after_retry.append(
                f"relation `{relation_type}` expected {expected}, live managed {live_count}"
            )
    if missing_after_retry:
        raise RuntimeError(
            "Post-apply verification failed for critical analysis groups: "
            + "; ".join(missing_after_retry)
        )


def _partition_groups(
    node_groups: dict[str, list[dict[str, JsonValue]]],
    relation_groups: dict[str, list[dict[str, JsonValue]]],
) -> tuple[
    dict[str, list[dict[str, JsonValue]]],
    dict[str, list[dict[str, JsonValue]]],
    dict[str, list[dict[str, JsonValue]]],
    dict[str, list[dict[str, JsonValue]]],
]:
    analysis_node_groups = {
        label: statements for label, statements in node_groups.items() if label in ANALYSIS_NODE_LABELS
    }
    core_node_groups = {
        label: statements for label, statements in node_groups.items() if label not in ANALYSIS_NODE_LABELS
    }
    analysis_relation_groups = {
        relation_type: statements
        for relation_type, statements in relation_groups.items()
        if relation_type in ANALYSIS_RELATION_TYPES
    }
    core_relation_groups = {
        relation_type: statements
        for relation_type, statements in relation_groups.items()
        if relation_type not in ANALYSIS_RELATION_TYPES
    }
    return core_node_groups, analysis_node_groups, core_relation_groups, analysis_relation_groups


def _verify_expected_group_counts(
    client: Neo4jHttpClient,
    node_groups: dict[str, list[dict[str, JsonValue]]],
    relation_groups: dict[str, list[dict[str, JsonValue]]],
    *,
    strict_analysis: bool,
) -> None:
    mismatches: list[str] = []
    for label, statements in sorted(node_groups.items()):
        expected = len(statements)
        live_count = _live_managed_node_count(client, label)
        if live_count != expected:
            mismatches.append(f"label `{label}` expected {expected}, live managed {live_count}")
    for relation_type, statements in sorted(relation_groups.items()):
        expected = len(statements)
        live_count = _live_managed_relation_count(client, relation_type)
        if live_count != expected:
            mismatches.append(f"relation `{relation_type}` expected {expected}, live managed {live_count}")

    if strict_analysis:
        critical_mismatches = [
            mismatch
            for mismatch in mismatches
            if any(token in mismatch for token in (*CRITICAL_ANALYSIS_NODE_LABELS, *CRITICAL_ANALYSIS_RELATION_TYPES))
        ]
        if critical_mismatches:
            raise RuntimeError(
                "Post-apply verification failed for critical analysis groups: "
                + "; ".join(critical_mismatches)
            )
    elif mismatches:
        raise RuntimeError(
            "Post-apply verification failed for targeted sync groups: " + "; ".join(mismatches)
        )


def _write_export(path: Path, snapshot: GraphSnapshot) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot.to_dict(), indent=2) + "\n", encoding="utf-8")  # NOSONAR


def _write_json(path: Path, payload: JsonValue) -> None:  # NOSONAR
    path.parent.mkdir(parents=True, exist_ok=True)  # NOSONAR
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def snapshot_orphans(snapshot: GraphSnapshot) -> list[NodeKey]:
    degrees = dict.fromkeys(snapshot.nodes, 0)
    for relation in snapshot.relations.values():
        degrees[relation.source] = degrees.get(relation.source, 0) + 1
        degrees[relation.target] = degrees.get(relation.target, 0) + 1
    return sorted(
        (key for key, degree in degrees.items() if degree == 0),
        key=lambda key: (key.label, key.name),
    )


def snapshot_invariant_issues(snapshot: GraphSnapshot) -> list[str]:
    stats = snapshot.stats()
    issues: list[str] = []
    required_labels = (
        "repo_zone",
        "directory_surface",
        "file_surface",
        "class_surface",
        "function_surface",
        "method_surface",
        "duplication_cluster",
        "complexity_candidate",
        "port_surface",
        "adapter_surface",
        "adapter_impl_surface",
        "pipeline_surface",
        "contract_surface",
        "alert_surface",
        "execution_path",
        "quality_gate",
        "dashboard_surface",
    )
    required_relation_types = (
        "BACKS",
        "HOUSES",
        "DECLARES",
        "DEPENDS_ON",
        "GOVERNS",
        "RUNS_VIA",
        "VALIDATED_BY",
        "OBSERVED_BY",
        "TESTED_BY",
        "SAME_SHAPE_AS",
        "CAN_PROMOTE_TO",
        "COVERED_BY_TEST",
        "HAS_COMPLEXITY_SIGNAL",
        "CANDIDATE_FOR_SIMPLIFICATION",
    )
    for label in required_labels:
        if int(stats["labels"].get(label, 0)) <= 0:
            issues.append(f"missing required label population: {label}")
    for relation_type in required_relation_types:
        if int(stats["relation_types"].get(relation_type, 0)) <= 0:
            issues.append(f"missing required relation population: {relation_type}")

    if NodeKey("port_surface", PORT_MODULE_PREFIX) not in snapshot.nodes:
        issues.append("missing bioetl.domain.ports facade port surface")

    protocol_ports = [
        node
        for node in snapshot.nodes.values()
        if node.key.label == "port_surface" and node.properties.get("granularity") == "protocol_class"
    ]
    if not protocol_ports:
        issues.append("missing protocol-class port surfaces")

    rich_contracts = [
        node
        for node in snapshot.nodes.values()
        if node.key.label == "contract_surface"
        and node.properties.get("dq_policy_ref")
        and node.properties.get("schema_classes")
    ]
    if not rich_contracts:
        issues.append("missing rich contract metadata on contract surfaces")

    relation_keys = {
        (rel.source.label, rel.source.name, rel.relation_type, rel.target.label)
        for rel in snapshot.relations.values()
    }
    if not any(
        source_label == "project" and relation_type == "HAS_REPO_ZONE" and target_label == "repo_zone"
        for source_label, _, relation_type, target_label in relation_keys
    ):
        issues.append("missing project -> HAS_REPO_ZONE -> repo_zone links")

    if not any(
        source_label == "directory_surface" and relation_type == "CONTAINS" and target_label == "file_surface"
        for source_label, _, relation_type, target_label in relation_keys
    ):
        issues.append("missing directory_surface -> CONTAINS -> file_surface links")

    if not any(
        source_label == "file_surface" and relation_type == "BACKS" and target_label == "module_surface"
        for source_label, _, relation_type, target_label in relation_keys
    ):
        issues.append("missing file_surface -> BACKS -> module_surface links")

    if not any(
        source_label == "directory_surface" and relation_type == "HOUSES" and target_label == "package_family"
        for source_label, _, relation_type, target_label in relation_keys
    ):
        issues.append("missing directory_surface -> HOUSES -> package_family links")

    if not any(
        source_label == "directory_surface" and relation_type == "HOUSES" and target_label == "entity_config"
        for source_label, _, relation_type, target_label in relation_keys
    ):
        issues.append("missing directory_surface -> HOUSES -> entity_config links")

    if not any(
        source_label == "directory_surface" and relation_type == "HOUSES" and target_label == "doc_source_surface"
        for source_label, _, relation_type, target_label in relation_keys
    ):
        issues.append("missing directory_surface -> HOUSES -> doc_source_surface links")

    if not any(
        source_label == "directory_surface" and relation_type == "HOUSES" and target_label == "test_artifact"
        for source_label, _, relation_type, target_label in relation_keys
    ):
        issues.append("missing directory_surface -> HOUSES -> test_artifact links")

    if not any(
        source_label == "module_surface" and relation_type == "DECLARES" and target_label == "class_surface"
        for source_label, _, relation_type, target_label in relation_keys
    ):
        issues.append("missing module_surface -> DECLARES -> class_surface links")

    if not any(
        source_label == "class_surface" and relation_type == "DECLARES" and target_label == "method_surface"
        for source_label, _, relation_type, target_label in relation_keys
    ):
        issues.append("missing class_surface -> DECLARES -> method_surface links")

    if not any(
        source_label == "module_surface" and relation_type == "DECLARES" and target_label == "function_surface"
        for source_label, _, relation_type, target_label in relation_keys
    ):
        issues.append("missing module_surface -> DECLARES -> function_surface links")

    if not any(
        source_label == "duplication_cluster" and relation_type == "CAN_PROMOTE_TO"
        for source_label, _, relation_type, _ in relation_keys
    ):
        issues.append("missing duplication_cluster promotion targets")

    if not any(
        source_label in {"method_surface", "function_surface"} and relation_type == "SAME_SHAPE_AS"
        for source_label, _, relation_type, _ in relation_keys
    ):
        issues.append("missing callable duplication links")

    if not any(
        source_label in {"module_surface", "class_surface", "function_surface", "method_surface"}
        and relation_type == "HAS_COMPLEXITY_SIGNAL"
        and target_label == "complexity_candidate"
        for source_label, _, relation_type, target_label in relation_keys
    ):
        issues.append("missing code surface -> HAS_COMPLEXITY_SIGNAL -> complexity_candidate links")

    if not any(
        source_label == "complexity_candidate" and relation_type == "CANDIDATE_FOR_SIMPLIFICATION"
        for source_label, _, relation_type, _ in relation_keys
    ):
        issues.append("missing complexity simplification candidates")

    if not any(
        source_label == "contract_surface" and relation_type == "DEPENDS_ON" and target_label == "module_surface"
        for source_label, _, relation_type, target_label in relation_keys
    ):
        issues.append("missing contract_surface -> DEPENDS_ON -> module_surface relations")

    if not any(
        source_label == "contract_surface" and relation_type == "DESCRIBED_IN" and target_label == "doc_artifact"
        for source_label, _, relation_type, target_label in relation_keys
    ):
        issues.append("missing contract_surface -> DESCRIBED_IN -> doc_artifact relations")

    if not any(
        source_label == "pipeline_surface" and relation_type == "RUNS_VIA" and target_label == "execution_path"
        for source_label, _, relation_type, target_label in relation_keys
    ):
        issues.append("missing pipeline_surface operational runtime links")

    if not any(
        source_label == "pipeline_surface" and relation_type == "TESTED_BY" and target_label == "test_artifact"
        for source_label, _, relation_type, target_label in relation_keys
    ):
        issues.append("missing pipeline_surface direct test coverage links")

    if not any(
        source_label == "pipeline_surface" and relation_type == "DEPENDS_ON" and target_label == "module_surface"
        for source_label, _, relation_type, target_label in relation_keys
    ):
        issues.append("missing pipeline_surface -> DEPENDS_ON -> module_surface links")

    if not any(
        source_label == "entity_config" and relation_type == "DEPENDS_ON" and target_label == "module_surface"
        for source_label, _, relation_type, target_label in relation_keys
    ):
        issues.append("missing entity_config -> DEPENDS_ON -> module_surface links")

    if not any(
        source_label == "alert_surface" and relation_type == "DEPENDS_ON" and target_label in {"pipeline_surface", "provider_surface"}
        for source_label, _, relation_type, target_label in relation_keys
    ):
        issues.append("missing alert_surface dependency links")

    if not any(
        source_label == "alert_surface" and relation_type == "DEPENDS_ON" and target_label == "contract_surface"
        for source_label, _, relation_type, target_label in relation_keys
    ):
        issues.append("missing alert_surface -> DEPENDS_ON -> contract_surface links")

    if not any(
        source_label == "alert_surface" and relation_type == "OBSERVED_BY" and target_label == "dashboard_surface"
        for source_label, _, relation_type, target_label in relation_keys
    ):
        issues.append("missing alert_surface -> OBSERVED_BY -> dashboard_surface links")

    if not any(
        source_label == "adapter_surface" and relation_type == "CONTAINS" and target_label == "adapter_impl_surface"
        for source_label, _, relation_type, target_label in relation_keys
    ):
        issues.append("missing adapter_surface -> CONTAINS -> adapter_impl_surface links")

    ignored_paths = [
        node.key.name
        for node in snapshot.nodes.values()
        if "__pycache__" in node.key.name
            or "__pycache__" in str(node.properties.get("source_path", ""))
    ]
    if ignored_paths:
        issues.append(f"ignored runtime paths leaked into snapshot: {sorted(set(ignored_paths))[:5]}")

    excluded_file_structure_paths = [
        node.key.name
        for node in snapshot.nodes.values()
        if node.key.label in {"directory_surface", "file_surface"}
        and (
            node.key.name.startswith("docs/99-archive")
            or node.key.name.startswith("docs/exports")
            or node.key.name.startswith("docs/reports/generated")
            or node.key.name.startswith("docs/02-architecture/generated")
            or node.key.name.startswith("docs/02-architecture/diagrams/bundles")
            or node.key.name.startswith("scripts/archive")
            or "/png" in node.key.name
            or "/svg" in node.key.name
        )
    ]
    if excluded_file_structure_paths:
        issues.append(
            "excluded file-structure paths leaked into snapshot: "
            + ", ".join(sorted(set(excluded_file_structure_paths))[:10])
        )

    orphan_nodes = snapshot_orphans(snapshot)
    if orphan_nodes:
        issues.append(
            "snapshot contains orphan nodes: "
            + ", ".join(f"{node.label}:{node.name}" for node in orphan_nodes[:10])
        )

    return issues


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
    rows: list[dict[str, JsonValue]] = []
    for label in managed_labels:
        result = client.query(
            (
                f"MATCH (n:`{label}`) "
                "RETURN $label AS label, "
                "count(n) AS total, "
                "sum(CASE WHEN coalesce(n.managed_by, '') = $managed_by THEN 1 ELSE 0 END) AS managed, "
                "sum(CASE WHEN coalesce(n.managed_by, '') = '' THEN 1 ELSE 0 END) AS unmanaged"
            ),
            {
                "label": label,
                "managed_by": DEFAULT_MANAGED_BY,
            },
        )
        if result:
            rows.extend(result)
    return rows


def _live_managed_relation_rows(
    client: Neo4jHttpClient,
    relation_types: list[str],
) -> list[dict[str, JsonValue]]:
    rows: list[dict[str, JsonValue]] = []
    for relation_type in relation_types:
        result = client.query(
            (
                f"MATCH ()-[r:`{relation_type}`]->() "
                "WHERE coalesce(r.managed_by, '') = $managed_by "
                "AND coalesce(r.ingest_wave, '') = $ingest_wave "
                "RETURN $relation_type AS relation_type, count(r) AS total"
            ),
            {
                "relation_type": relation_type,
                "managed_by": DEFAULT_MANAGED_BY,
                "ingest_wave": DEFAULT_INGEST_WAVE,
            },
        )
        if result:
            rows.extend(result)
    return rows


def _live_orphan_rows(client: Neo4jHttpClient, managed_labels: list[str]) -> list[dict[str, JsonValue]]:
    rows: list[dict[str, JsonValue]] = []
    for label in managed_labels:
        result = client.query(
            (
                f"MATCH (n:`{label}`) "
                "WHERE coalesce(n.managed_by, '') = $managed_by "
                "AND coalesce(n.ingest_wave, '') = $ingest_wave "
                "AND NOT (n)--() "
                "RETURN $label AS label, count(n) AS count, collect(n.name)[0..10] AS samples"
            ),
            {
                "label": label,
                "managed_by": DEFAULT_MANAGED_BY,
                "ingest_wave": DEFAULT_INGEST_WAVE,
            },
        )
        if result and int(result[0].get("count", 0)):
            rows.extend(result)
    return rows


def _live_unmanaged_repo_rows(client: Neo4jHttpClient, managed_labels: list[str]) -> list[dict[str, JsonValue]]:
    rows: list[dict[str, JsonValue]] = []
    for label in managed_labels:
        result = client.query(
            (
                f"MATCH (n:`{label}`) "
                "WHERE coalesce(n.managed_by, '') = '' "
                "RETURN $label AS label, count(n) AS count, collect(n.name)[0..10] AS samples"
            ),
            {
                "label": label,
            },
        )
        if result and int(result[0].get("count", 0)):
            rows.extend(result)
    return rows


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
    snapshot_relation_types = sorted({relation.relation_type for relation in snapshot.relations.values()})
    snapshot_stats = snapshot.stats()
    live_label_rows = _live_repo_label_rows(client, managed_labels)
    live_relation_rows = _live_managed_relation_rows(client, snapshot_relation_types)
    orphan_rows = _live_orphan_rows(client, managed_labels)
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


def _critical_analysis_audit_issues(report: dict[str, JsonValue]) -> list[str]:
    issues: list[str] = []
    diff = report.get("diff", {})
    label_rows = diff.get("labels", []) if isinstance(diff, dict) else []
    relation_rows = diff.get("relation_types", []) if isinstance(diff, dict) else []

    for row in label_rows:
        if not isinstance(row, dict):
            continue
        name = row.get("name")
        delta = row.get("delta")
        if name in CRITICAL_ANALYSIS_NODE_LABELS and delta:
            issues.append(
                f"label `{name}` expected {row.get('snapshot')}, live managed {row.get('live_managed')}"
            )
    for row in relation_rows:
        if not isinstance(row, dict):
            continue
        name = row.get("name")
        delta = row.get("delta")
        if name in CRITICAL_ANALYSIS_RELATION_TYPES and delta:
            issues.append(
                f"relation `{name}` expected {row.get('snapshot')}, live managed {row.get('live_managed')}"
            )
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.prune_stale and args.full_reset_managed_wave:
        parser.error("--prune-stale and --full-reset-managed-wave cannot be used together")
    root = args.root.resolve()
    snapshot = _filtered_snapshot(
        build_snapshot(root),
        only_labels=tuple(args.only_label),
        only_analysis_layer=args.only_analysis_layer,
    )
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
            only_labels=tuple(args.only_label),
            only_analysis_layer=args.only_analysis_layer,
        )
        post_apply_report = build_audit_report(snapshot, root, args.http_uri)
        critical_issues = _critical_analysis_audit_issues(post_apply_report)
        if critical_issues:
            raise RuntimeError(
                "Post-apply audit failed for critical analysis groups: " + "; ".join(critical_issues)
            )
        print("Neo4j sync completed.")
    if args.report is not None:
        report = build_audit_report(snapshot, root, args.http_uri)
        _write_json(args.report, report)
        print(f"Exported audit report to {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
