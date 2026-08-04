#!/usr/bin/env python3
"""Build and optionally sync the canonical deterministic BioETL graph into Neo4j."""

from __future__ import annotations

import argparse
import ast
import base64
import fnmatch
import hashlib
import http.client
import itertools
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TypeVar, cast
from urllib import error, parse, request

import yaml

from bioetl.infrastructure.config.contract_registry_loader import (
    DEFAULT_CONTRACT_REGISTRY_PATH,
    load_contract_registry_payload,
)

type JsonScalar = str | int | float | bool | None
# Graph assembly ingests heterogeneous YAML/JSON and AST-derived values. Keep
# that pre-serialization boundary explicit; serializers below narrow values to
# the scalar/list shapes accepted by Neo4j and JSON.
type JsonValue = object
type RelationSpec = tuple[str, frozenset[str], frozenset[str]]
type ShardFilterSpec = tuple[frozenset[str], tuple[RelationSpec, ...]]
# Relation / shard filter keys used by snapshot filtering helpers.
# NodeKey is defined later; PEP 695 type aliases evaluate lazily.
type RelationKey = tuple[NodeKey, str, NodeKey]
type ShardFilter = ShardFilterSpec
T = TypeVar("T")
BIOETL_METRIC_PATTERN = re.compile(r"\bbioetl_[a-zA-Z0-9_:]+")


def _as_mapping(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return {str(k): v for k, v in value.items()}
    return {}


def _as_iterable(value: object) -> list[object]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, set):
        return list(value)
    return []


def _coerce_int(value: object, default: int = 0) -> int:
    """Coerce mapping/JSON payload values to int for static checkers and runtime."""
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


SRC_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ROOT = Path(__file__).resolve().parents[4]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(DEFAULT_ROOT) not in sys.path:
    sys.path.insert(0, str(DEFAULT_ROOT))
DEFAULT_BATCH_SIZE = 20
DEFAULT_INGEST_WAVE = "repo_sync_v1"
DEFAULT_MANAGED_BY = "neo4j_memory_sync"
DEFAULT_MEMORY_MAPPING_PATH = "src/memory/graph/mappings.yaml"
LEGACY_MEMORY_MAPPING_PATH = "configs/quality/neo4j_memory_mapping.yaml"
ANALYSIS_SOURCE_READ_TIMEOUT_SECONDS = 2.0
INIT_PY = "__init__.py"
MAIN_PY = "__main__.py"
YAML_SUFFIX = ".yaml"
GITHUB_DIR = ".github"
GITHUB_PATH_PREFIX = f"{GITHUB_DIR}/"
GITHUB_WORKFLOWS_PREFIX = f"{GITHUB_DIR}/workflows/"
PORTS_MODULE_PREFIX = "bioetl.domain.ports"
PORTS_FACADE_SOURCE_PATH = f"src/bioetl/domain/ports/{INIT_PY}"
RULES_DOC_PATH = "docs/00-project/RULES.md"
TESTING_GUIDE_PATH = "docs/03-guides/testing.md"
DOCS_VERIFICATION_GUIDE_PATH = "docs/03-guides/docs-verification.md"
INTEGRATION_VCR_POLICY_PATH = "configs/quality/integration_vcr_policy.yaml"
TEST_MATRIX_CONFIG_PATH = "configs/quality/test_matrix.yaml"
RUN_MANIFEST_LEDGER_DOC_PATH = "docs/04-reference/contracts/run-manifest-ledger.md"
GOVERNANCE_DECISIONS_SUMMARY_PATH = (
    "docs/reports/evidence/governance-signals/04-decisions/SUMMARY.md"
)
RUN_MANIFEST_INSPECTION_DOC_PATH = (
    "docs/05-operations/runbooks/run-manifest-inspection.md"
)
TRACEABILITY_SIGNAL_OWNERSHIP_DOC_PATH = (
    "docs/05-operations/runbooks/traceability-signal-ownership.md"
)
CONTRACT_REGISTRY_RELATIVE_PATH = DEFAULT_CONTRACT_REGISTRY_PATH.as_posix()
CHEMBL_ACTIVITY_CONTRACT_REF = "chembl.activity"
RUN_MANIFEST_ARTIFACT_REF = "run_manifest::json"
EFFECTIVE_CONFIG_ARTIFACT_REF = "effective_config_artifact::json"
RUN_LEDGER_ARTIFACT_REF = "run_ledger::jsonl"
DOC_GRAFANA_DASHBOARDS_JSON = "grafana dashboards json"
DOC_ARCHITECTURE_DIAGRAMS_HUB = "architecture diagrams hub"
DOC_DIAGRAM_TOOLING_README = "diagram tooling readme"
TEST_SURFACE_INTEGRATION = "integration tests"
TEST_SURFACE_E2E = "e2e tests"
TEST_SURFACE_ARCHITECTURE = "architecture tests"
GATE_MYPY_STRICT = "mypy --strict"
GATE_DOCS_VERIFICATION = "docs verification"
GATE_CONFIG_VALIDATION = "config validation"
GATE_PRETEST_GUARDRAILS = "pretest guardrails"
GATE_DIAGRAM_QUALITY = "diagram quality gates"
GATE_NEO4J_ONTOLOGY_INVARIANTS = "deterministic neo4j memory ontology invariants"
DEFAULT_LEGACY_REPORT_PATH = str(
    Path(tempfile.gettempdir()) / "neo4j-memory-audit.json"
)
YAML_FILE_GLOB = "*.yaml"
MANIFEST_ID_TEMPLATE = "{manifest_id}"
RUN_ID_TEMPLATE = "{run_id}"
CRITICAL_ANALYSIS_NODE_LABELS: tuple[str, ...] = (
    "retirement_candidate",
    "complexity_candidate",
)
CRITICAL_ANALYSIS_RELATION_TYPES: tuple[str, ...] = (
    "CANDIDATE_FOR_REMOVAL",
    "HAS_COMPLEXITY_SIGNAL",
    "CANDIDATE_FOR_SIMPLIFICATION",
    "JUSTIFIED_BY_RUNTIME",
    "BLOCKED_BY_VARIANCE",
)
ANALYSIS_NODE_LABELS: tuple[str, ...] = (
    "retirement_candidate",
    "complexity_candidate",
)
ANALYSIS_RELATION_TYPES: tuple[str, ...] = (
    "CANDIDATE_FOR_REMOVAL",
    "HAS_COMPLEXITY_SIGNAL",
    "CANDIDATE_FOR_SIMPLIFICATION",
    "JUSTIFIED_BY_RUNTIME",
    "BLOCKED_BY_VARIANCE",
)
RETIREMENT_NODE_LABELS: tuple[str, ...] = ("retirement_candidate",)
RETIREMENT_RELATION_TYPES: tuple[str, ...] = ("CANDIDATE_FOR_REMOVAL",)
COMPLEXITY_NODE_LABELS: tuple[str, ...] = ("complexity_candidate",)
COMPLEXITY_RELATION_TYPES: tuple[str, ...] = (
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
    "storage_surface",
    "runtime_evidence_surface",
    "control_plane_artifact_surface",
    "run_instance_surface",
    "runtime_state_surface",
    "schema_field_surface",
    "workflow_surface",
    "workflow_job_surface",
    "workflow_call_surface",
    "workflow_matrix_variant_surface",
    "workflow_output_surface",
    "workflow_action_surface",
    "workflow_artifact_surface",
    "workflow_secret_surface",
    "cli_command_surface",
    "cli_option_surface",
    "doc_claim_surface",
)
DEFAULT_FILE_STRUCTURE_REPO_ZONES: dict[str, tuple[str, ...]] = {
    "src": ("src",),
    "configs": ("configs",),
    "tests": ("tests",),
    "docs": ("docs",),
    "scripts": ("scripts",),
    "grafana": ("grafana",),
    GITHUB_DIR: (GITHUB_DIR,),
}
DEFAULT_FILE_STRUCTURE_EXCLUDED_PREFIXES: tuple[str, ...] = (
    "docs/site",
    "docs/99-archive",
    "docs/exports",
    "docs/reports",
    "docs/reports/generated",
    "docs/00-project/ai/agents/agents",
    "docs/00-project/ai/agents/runtime",
    "docs/00-project/ai/prompts",
    "docs/00-project/ai/rules",
    "docs/00-project/ai/skills",
    "docs/02-architecture/generated",
    "docs/02-architecture/diagrams/bundles",
    "docs/02-architecture/diagrams/descriptions",
    "docs/02-architecture/diagrams/manifests",
    "docs/02-architecture/diagrams/png",
    "docs/02-architecture/diagrams/tooling",
    "docs/02-architecture/diagrams/architecture/png",
    "docs/02-architecture/diagrams/architecture/svg",
    "docs/02-architecture/diagrams/class-diagrams/png",
    "docs/02-architecture/diagrams/class-diagrams/svg",
    "docs/02-architecture/diagrams/foundation/png",
    "docs/02-architecture/diagrams/foundation/svg",
    "docs/02-architecture/diagrams/views/png",
    "docs/02-architecture/diagrams/views/svg",
    "scripts/diagrams/svg2png.mjs",
    "scripts/archive",
)
DEFAULT_FILE_STRUCTURE_EXCLUDED_DIR_NAMES: tuple[str, ...] = ("__pycache__",)
ADR_DECISIONS_DIR = "docs/02-architecture/decisions"
OPS_SCRIPT_HUB_PREFIXES: tuple[str, ...] = (
    "scripts/diagrams/",
    "scripts/docs/",
    "scripts/engineering/qa/",
    "scripts/schema/",
    "scripts/memory/",
)
DEFAULT_PIPELINE_RUNTIME_PATHS: tuple[str, ...] = (
    "uv run python -m bioetl run --pipeline",
    '"${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python" -m bioetl run --pipeline',
    ".\\.venv-win\\Scripts\\python.exe -m bioetl run --pipeline",
)
DEFAULT_PIPELINE_VALIDATION_GATES: tuple[str, ...] = ("pytest", GATE_CONFIG_VALIDATION)
DEFAULT_COMMON_PIPELINE_DASHBOARDS: tuple[str, ...] = (
    "bioetl-overview-v2",
    "bioetl-runtime",
)
DEFAULT_ENTITY_PIPELINE_DASHBOARDS: tuple[str, ...] = (
    "bioetl-dq-v2",
    "bioetl-silver-reject-explorer",
)
DEFAULT_COMPOSITE_PIPELINE_DASHBOARDS: tuple[str, ...] = ("bioetl-control-plane-v1",)
KNOWN_LAYERS = ("domain", "application", "infrastructure", "composition", "interfaces")
TEST_SURFACES: dict[str, str] = {
    "unit": "unit tests",
    "integration": TEST_SURFACE_INTEGRATION,
    "e2e": TEST_SURFACE_E2E,
    "architecture": TEST_SURFACE_ARCHITECTURE,
    "contract": "contract tests",
    "benchmarks": "benchmarks",
}
STORAGE_LAYER_FILTER: ShardFilterSpec = (
    frozenset(
        {
            "project",
            "pipeline_surface",
            "entity_config",
            "composite_config",
            "config_artifact",
            "storage_surface",
            "runtime_evidence_surface",
            "control_plane_artifact_surface",
            "run_instance_surface",
            "runtime_state_surface",
            "schema_field_surface",
        }
    ),
    (
        ("HAS_STORAGE_SURFACE", frozenset({"project"}), frozenset({"storage_surface"})),
        (
            "HAS_RUNTIME_EVIDENCE",
            frozenset({"project"}),
            frozenset({"runtime_evidence_surface"}),
        ),
        (
            "HAS_CONTROL_PLANE_ARTIFACT",
            frozenset({"project"}),
            frozenset({"control_plane_artifact_surface"}),
        ),
        (
            "HAS_RUN_INSTANCE",
            frozenset({"project"}),
            frozenset({"run_instance_surface"}),
        ),
        (
            "WRITES_TO",
            frozenset(
                {
                    "pipeline_surface",
                    "entity_config",
                    "composite_config",
                    "runtime_evidence_surface",
                }
            ),
            frozenset({"storage_surface"}),
        ),
        (
            "DEFINED_BY",
            frozenset({"pipeline_surface", "entity_config", "composite_config"}),
            frozenset({"config_artifact"}),
        ),
        ("PROMOTES_TO", frozenset({"storage_surface"}), frozenset({"storage_surface"})),
        (
            "EMITS_ARTIFACT",
            frozenset({"runtime_evidence_surface"}),
            frozenset({"control_plane_artifact_surface"}),
        ),
        (
            "MATERIALIZED_AS",
            frozenset({"control_plane_artifact_surface"}),
            frozenset({"storage_surface"}),
        ),
        (
            "REFERENCES_ARTIFACT",
            frozenset({"run_instance_surface"}),
            frozenset({"control_plane_artifact_surface"}),
        ),
        (
            "HAS_SCHEMA_FIELD",
            frozenset({"project", "storage_surface", "contract_surface"}),
            frozenset({"schema_field_surface"}),
        ),
        (
            "PROMOTES_FIELD_TO",
            frozenset({"schema_field_surface"}),
            frozenset({"schema_field_surface"}),
        ),
        (
            "DERIVES_FIELD_FROM",
            frozenset({"schema_field_surface"}),
            frozenset({"schema_field_surface"}),
        ),
        (
            "HAS_RUNTIME_STATE",
            frozenset({"project", "run_instance_surface"}),
            frozenset({"runtime_state_surface"}),
        ),
        (
            "REFERENCES_ARTIFACT",
            frozenset({"runtime_state_surface"}),
            frozenset({"control_plane_artifact_surface"}),
        ),
    ),
)
RUNTIME_EVIDENCE_LAYER_FILTER: ShardFilterSpec = (
    frozenset(
        {
            "project",
            "runtime_evidence_surface",
            "control_plane_artifact_surface",
            "run_instance_surface",
            "runtime_state_surface",
            "storage_surface",
            "module_surface",
            "doc_artifact",
            "test_artifact",
            "pipeline_surface",
            "contract_surface",
            "workflow_surface",
        }
    ),
    (
        (
            "HAS_RUNTIME_EVIDENCE",
            frozenset({"project"}),
            frozenset({"runtime_evidence_surface"}),
        ),
        (
            "HAS_CONTROL_PLANE_ARTIFACT",
            frozenset({"project"}),
            frozenset({"control_plane_artifact_surface"}),
        ),
        (
            "HAS_RUN_INSTANCE",
            frozenset({"project"}),
            frozenset({"run_instance_surface"}),
        ),
        (
            "BACKED_BY",
            frozenset({"runtime_evidence_surface"}),
            frozenset({"module_surface"}),
        ),
        (
            "DESCRIBED_IN",
            frozenset({"runtime_evidence_surface"}),
            frozenset({"doc_artifact"}),
        ),
        (
            "DESCRIBED_IN",
            frozenset({"run_instance_surface"}),
            frozenset({"doc_artifact", "test_artifact"}),
        ),
        (
            "DEPENDS_ON",
            frozenset({"run_instance_surface"}),
            frozenset({"pipeline_surface", "contract_surface"}),
        ),
        (
            "WRITES_TO",
            frozenset({"runtime_evidence_surface"}),
            frozenset({"storage_surface"}),
        ),
        (
            "EMITS_ARTIFACT",
            frozenset({"runtime_evidence_surface"}),
            frozenset({"control_plane_artifact_surface"}),
        ),
        (
            "MATERIALIZED_AS",
            frozenset({"control_plane_artifact_surface"}),
            frozenset({"storage_surface"}),
        ),
        (
            "REFERENCES_ARTIFACT",
            frozenset({"run_instance_surface"}),
            frozenset({"control_plane_artifact_surface"}),
        ),
        (
            "HAS_RUNTIME_STATE",
            frozenset({"project", "run_instance_surface"}),
            frozenset({"runtime_state_surface"}),
        ),
        (
            "DEPENDS_ON",
            frozenset({"runtime_state_surface"}),
            frozenset(
                {
                    "pipeline_surface",
                    "workflow_surface",
                    "runtime_evidence_surface",
                    "contract_surface",
                }
            ),
        ),
        (
            "REFERENCES_ARTIFACT",
            frozenset({"runtime_state_surface"}),
            frozenset({"control_plane_artifact_surface"}),
        ),
        (
            "DESCRIBED_IN",
            frozenset({"runtime_state_surface"}),
            frozenset({"doc_artifact"}),
        ),
    ),
)
WORKFLOW_GRAPH_FILTER: ShardFilterSpec = (
    frozenset(
        {
            "project",
            "workflow_surface",
            "workflow_job_surface",
            "workflow_call_surface",
            "workflow_matrix_variant_surface",
            "workflow_output_surface",
            "workflow_action_surface",
            "workflow_artifact_surface",
            "workflow_secret_surface",
            "script_surface",
            "file_surface",
            "directory_surface",
            "quality_gate",
        }
    ),
    (
        ("HAS_WORKFLOW", frozenset({"project"}), frozenset({"workflow_surface"})),
        (
            "CONTAINS",
            frozenset({"workflow_surface"}),
            frozenset({"workflow_job_surface"}),
        ),
        (
            "CALLS_WORKFLOW",
            frozenset({"workflow_surface", "workflow_job_surface"}),
            frozenset({"workflow_call_surface"}),
        ),
        (
            "HAS_MATRIX_VARIANT",
            frozenset({"workflow_job_surface"}),
            frozenset({"workflow_matrix_variant_surface"}),
        ),
        (
            "EMITS_OUTPUT",
            frozenset({"workflow_surface", "workflow_job_surface"}),
            frozenset({"workflow_output_surface"}),
        ),
        (
            "RUNS_VIA",
            frozenset({"workflow_job_surface"}),
            frozenset({"script_surface", "file_surface", "directory_surface"}),
        ),
        (
            "EXECUTES_GATE",
            frozenset({"workflow_job_surface"}),
            frozenset({"quality_gate"}),
        ),
        (
            "DEPENDS_ON",
            frozenset({"workflow_job_surface", "workflow_call_surface"}),
            frozenset(
                {
                    "workflow_job_surface",
                    "workflow_artifact_surface",
                    "workflow_surface",
                }
            ),
        ),
        (
            "USES_ACTION",
            frozenset({"workflow_job_surface"}),
            frozenset({"workflow_action_surface"}),
        ),
        (
            "PUBLISHES_ARTIFACT",
            frozenset({"workflow_job_surface"}),
            frozenset({"workflow_artifact_surface"}),
        ),
        (
            "REQUIRES_SECRET",
            frozenset({"workflow_job_surface"}),
            frozenset({"workflow_secret_surface"}),
        ),
    ),
)
DOCS_DRIFT_FILTER: ShardFilterSpec = (
    frozenset(
        {
            "doc_source_surface",
            "doc_artifact",
            "policy_surface",
            "doc_claim_surface",
            "module_surface",
            "script_surface",
            "config_artifact",
            "workflow_surface",
            "cli_command_surface",
            "file_surface",
            "directory_surface",
            "execution_path",
        }
    ),
    (
        (
            "DESCRIBES",
            frozenset({"doc_source_surface", "doc_artifact", "policy_surface"}),
            frozenset(
                {
                    "module_surface",
                    "script_surface",
                    "config_artifact",
                    "workflow_surface",
                    "cli_command_surface",
                    "file_surface",
                    "directory_surface",
                    "execution_path",
                }
            ),
        ),
        (
            "ASSERTS",
            frozenset({"doc_source_surface", "doc_artifact", "policy_surface"}),
            frozenset({"doc_claim_surface"}),
        ),
        (
            "DESCRIBED_IN",
            frozenset({"module_surface"}),
            frozenset({"doc_source_surface", "doc_artifact"}),
        ),
        (
            "ASSERTS_ABOUT",
            frozenset({"doc_claim_surface"}),
            frozenset(
                {
                    "module_surface",
                    "script_surface",
                    "config_artifact",
                    "workflow_surface",
                    "cli_command_surface",
                    "file_surface",
                    "directory_surface",
                    "execution_path",
                }
            ),
        ),
    ),
)
CURATED_DOC_SOURCES: tuple[dict[str, str], ...] = (
    {
        "name": "Project Navigator",
        "path": "docs/00-project/00-map.md",
        "summary": "Primary project navigator and active entrypoint map.",
    },
    {
        "name": "RULES.md",
        "path": RULES_DOC_PATH,
        "summary": "Canonical governance and requirements surface for the project.",
    },
    {
        "name": "agent memory entry point",
        "path": "docs/00-project/ai/memory/agent-memory.md",
        "summary": "Human-oriented project memory entry point for AI runtimes.",
    },
    {
        "name": "testing guide",
        "path": TESTING_GUIDE_PATH,
        "summary": "Published testing strategy guide.",
    },
    {
        "name": "normalization plan",
        "path": "docs/05-engineering/normalization_plan_P0_P6.md",
        "summary": "Canonical normalization architecture, evidence governance, and rollout plan.",
    },
    {
        "name": "pipeline normalization matrix",
        "path": "docs/reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.md",
        "summary": "Generated field-level normalization evidence for entity and composite pipelines.",
    },
    {
        "name": "dashboard extension guide",
        "path": "docs/03-guides/dashboards/dashboard-extension-llm.md",
        "summary": "Canonical LLM playbook for shipped Grafana dashboards.",
    },
    {
        "name": "architecture diagrams hub",
        "path": "docs/02-architecture/diagrams/README.md",
        "summary": "Canonical hub for architecture, class, foundation, and view diagram sources and publication artifacts.",
    },
    {
        "name": "diagram governance ADR",
        "path": "docs/02-architecture/decisions/ADR-040-diagram-governance.md",
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
        "name": "diagram tooling readme",
        "path": "scripts/diagrams/README.md",
        "summary": "Repository entrypoint for diagram lint, render, bundle, and regression tooling.",
    },
    {
        "name": "docs verification guide",
        "path": DOCS_VERIFICATION_GUIDE_PATH,
        "summary": "Published workflow for docs verification and drift control.",
    },
    {
        "name": RUN_MANIFEST_LEDGER_DOC_PATH,
        "path": RUN_MANIFEST_LEDGER_DOC_PATH,
        "summary": "Published control-plane contract for immutable run manifests, append-only run ledgers, and replay inspection surfaces.",
    },
    {
        "name": "package topology evidence summary",
        "path": "docs/reports/evidence/project-package-topology/SUMMARY.md",
        "summary": "Repo-only topology calibration evidence for package families.",
    },
    {
        "name": "governance decisions summary",
        "path": GOVERNANCE_DECISIONS_SUMMARY_PATH,
        "summary": "Accepted governance decisions and risks.",
    },
    {
        "name": DOC_GRAFANA_DASHBOARDS_JSON,
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
CURATED_POLICY_SURFACES: tuple[dict[str, object], ...] = (
    {
        "name": "hexagonal import matrix",
        "summary": (
            "Import boundaries are strict: domain imports only domain, application imports domain plus itself, "
            "infrastructure imports domain plus itself, composition can wire all layers except interfaces, "
            "and interfaces can depend on all layers."
        ),
        "source_path": RULES_DOC_PATH,
        "artifact_label": "doc_artifact",
        "governs_layers": KNOWN_LAYERS,
    },
    {
        "name": "medallion storage contract",
        "summary": (
            "BioETL follows Bronze to Silver to Gold medallion flow. Silver must use Delta Lake rather than raw "
            "Parquet, and Pandera remains the schema validation standard across dataframe boundaries."
        ),
        "source_path": RULES_DOC_PATH,
        "artifact_label": "doc_artifact",
    },
    {
        "name": "provider support matrix",
        "summary": (
            "Primary provider set includes ChEMBL, PubChem, PubMed, Semantic Scholar, CrossRef, OpenAlex, "
            "and UniProt for bioactivity acquisition and enrichment workflows."
        ),
        "source_path": RULES_DOC_PATH,
        "artifact_label": "doc_artifact",
    },
    {
        "name": "hexagonal package layout",
        "summary": (
            "Source layout is organized into domain, application, infrastructure, composition, and interfaces. "
            "Domain stays pure, composition owns wiring, interfaces expose CLI entrypoints, and architecture tests "
            "enforce cross-layer boundaries."
        ),
        "source_path": RULES_DOC_PATH,
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
        "source_path": RULES_DOC_PATH,
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
        "governs_docs": (DOC_GRAFANA_DASHBOARDS_JSON,),
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
            "unit tests",
            TEST_SURFACE_INTEGRATION,
            TEST_SURFACE_E2E,
            TEST_SURFACE_ARCHITECTURE,
            "contract tests",
        ),
    },
    {
        "name": "quality gate stack",
        "summary": (
            f"The main repository gate stack combines pytest, {GATE_MYPY_STRICT}, VCR execution policy, "
            f"{GATE_DOCS_VERIFICATION}, {GATE_CONFIG_VALIDATION}, and {GATE_PRETEST_GUARDRAILS}."
        ),
        "source_path": TESTING_GUIDE_PATH,
        "artifact_label": "doc_artifact",
        "governs_quality_gates": (
            "pytest",
            GATE_MYPY_STRICT,
            GATE_DOCS_VERIFICATION,
            GATE_CONFIG_VALIDATION,
            GATE_PRETEST_GUARDRAILS,
        ),
    },
    {
        "name": "VCR replay discipline",
        "summary": (
            "Integration and e2e work is replay-first. VCR cassettes are refreshed in a targeted way rather than "
            "broad uncontrolled rewrites, and machine-readable policy keeps the replay contract synchronized with the test matrix."
        ),
        "source_path": TESTING_GUIDE_PATH,
        "artifact_label": "doc_artifact",
        "governs_test_surfaces": (TEST_SURFACE_INTEGRATION, TEST_SURFACE_E2E),
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
        "source_path": TEST_MATRIX_CONFIG_PATH,
        "artifact_label": "config_artifact",
    },
    {
        "name": "integration and VCR execution policy",
        "summary": "Tracked machine-readable policy for integration and VCR execution scope, replay modes, and suite inventory.",
        "source_path": INTEGRATION_VCR_POLICY_PATH,
        "artifact_label": "config_artifact",
        "governs_test_surfaces": (TEST_SURFACE_INTEGRATION, TEST_SURFACE_E2E),
        "governs_quality_gates": ("pytest",),
    },
    {
        "name": "docs verification guide",
        "summary": "Published workflow defining the verification path for docs surface and repo-only supporting material boundaries.",
        "source_path": DOCS_VERIFICATION_GUIDE_PATH,
        "artifact_label": "doc_artifact",
        "governs_quality_gates": (GATE_DOCS_VERIFICATION,),
    },
    {
        "name": "diagram governance policy",
        "summary": (
            "Canonical architecture diagrams live under docs/02-architecture/diagrams with ADR-040, canonical policy, "
            "measured inventories, and scripted lint/render/publication checks defining the supported workflow."
        ),
        "source_path": "docs/02-architecture/diagrams/governance/policy.md",
        "artifact_label": "doc_artifact",
        "governs_quality_gates": (GATE_DIAGRAM_QUALITY,),
        "governs_test_surfaces": (TEST_SURFACE_ARCHITECTURE,),
        "governs_docs": (
            DOC_ARCHITECTURE_DIAGRAMS_HUB,
            "diagram governance ADR",
            "diagram governance workflow",
            "diagram measured inventory",
            "diagram views inventory",
            DOC_DIAGRAM_TOOLING_README,
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
        "governs_docs": (DOC_ARCHITECTURE_DIAGRAMS_HUB, DOC_DIAGRAM_TOOLING_README),
    },
    {
        "name": "published docs boundary",
        "summary": "Published docs in docs/00-05 and README define active supported behavior; repo-only material must not override them.",
        "source_path": DOCS_VERIFICATION_GUIDE_PATH,
        "artifact_label": "doc_artifact",
    },
    {
        "name": "default VCR record mode",
        "summary": "CI defaults to none; local defaults to once unless explicitly overridden.",
        "source_path": INTEGRATION_VCR_POLICY_PATH,
        "artifact_label": "config_artifact",
        "governs_test_surfaces": (TEST_SURFACE_INTEGRATION, TEST_SURFACE_E2E),
    },
    {
        "name": "targeted cassette refresh",
        "summary": "Targeted VCR refresh uses new_episodes; broad rewrites are not the supported default path.",
        "source_path": INTEGRATION_VCR_POLICY_PATH,
        "artifact_label": "config_artifact",
        "governs_test_surfaces": (TEST_SURFACE_INTEGRATION, TEST_SURFACE_E2E),
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
        "script_path": "scripts/docs/verify_docs.py",
    },
    {
        "name": "uv run python -m scripts.schema validate-configs",
        "platform": "ci_uv",
        "summary": "Canonical config validation path for supported configs.",
        "gate": GATE_CONFIG_VALIDATION,
        "script_path": "scripts/schema/validate_configs.py",
    },
    {
        "name": "bash scripts/engineering/dev/pretest_guardrails.sh",
        "platform": "wsl",
        "summary": "WSL pretest guardrail runner before broad pytest waves.",
        "gate": GATE_PRETEST_GUARDRAILS,
        "script_path": "scripts/engineering/dev/pretest_guardrails.sh",
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
    relations: dict[tuple[NodeKey, str, NodeKey], GraphRelation] = field(
        default_factory=dict
    )

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
                for node in sorted(
                    self.nodes.values(),
                    key=lambda item: (item.key.label, item.key.name),
                )
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
            relation_counts[relation.relation_type] = (
                relation_counts.get(relation.relation_type, 0) + 1
            )
        return {
            "node_count": len(self.nodes),
            "relation_count": len(self.relations),
            "labels": label_counts,
            "relation_types": relation_counts,
        }


def _selected_shard_filters(
    selection: SnapshotSelection,
) -> tuple[ShardFilterSpec, ...]:
    selected: list[ShardFilterSpec] = []
    if selection.only_storage_layer:
        selected.append(STORAGE_LAYER_FILTER)
    if selection.only_runtime_evidence_layer:
        selected.append(RUNTIME_EVIDENCE_LAYER_FILTER)
    if selection.only_workflow_graph:
        selected.append(WORKFLOW_GRAPH_FILTER)
    if selection.only_docs_drift:
        selected.append(DOCS_DRIFT_FILTER)
    return tuple(selected)


def _allowed_analysis_relation_types(
    selection: SnapshotSelection,
) -> set[str]:
    allowed = set()
    if selection.only_analysis_layer:
        allowed.update(ANALYSIS_RELATION_TYPES)
    if selection.only_retirement_layer:
        allowed.update(RETIREMENT_RELATION_TYPES)
    if selection.only_complexity_layer:
        allowed.update(COMPLEXITY_RELATION_TYPES)
    return allowed or set(ANALYSIS_RELATION_TYPES)


def _build_allowed_labels(
    selection: SnapshotSelection,
    shard_filters: tuple[ShardFilterSpec, ...],
) -> set[str]:
    allowed_labels = set(selection.only_labels)
    for shard_labels, _ in shard_filters:
        allowed_labels.update(shard_labels)
    if selection.only_analysis_layer:
        allowed_labels.update(ANALYSIS_NODE_LABELS)
    if selection.only_retirement_layer:
        allowed_labels.update(RETIREMENT_NODE_LABELS)
    if selection.only_complexity_layer:
        allowed_labels.update(COMPLEXITY_NODE_LABELS)
    return allowed_labels


def _relation_matches_shard_filters(
    relation: GraphRelation, shard_filters: tuple[ShardFilterSpec, ...]
) -> bool:
    for _, relation_specs in shard_filters:
        for relation_type, source_labels, target_labels in relation_specs:
            if (
                relation.relation_type == relation_type
                and relation.source.label in source_labels
                and relation.target.label in target_labels
            ):
                return True
    return False


def _include_analysis_relation(
    filtered: GraphSnapshot,
    rel_key: tuple[NodeKey, str, NodeKey],
    relation: GraphRelation,
    *,
    allowed_labels: set[str],
    allowed_analysis_relation_types: set[str],
    label_scoped_only: bool,
    selection: SnapshotSelection,
) -> bool:
    if relation.relation_type not in ANALYSIS_RELATION_TYPES:
        return False
    if relation.relation_type not in allowed_analysis_relation_types:
        return True
    if label_scoped_only:
        if (
            relation.source.label in allowed_labels
            and relation.target.label in allowed_labels
        ):
            filtered.relations[rel_key] = relation
        return True
    if (
        selection.only_analysis_layer
        or relation.source.label in allowed_labels
        or relation.target.label in allowed_labels
    ):
        filtered.relations[rel_key] = relation
    return True


def _seed_filtered_nodes(
    filtered: GraphSnapshot,
    snapshot: GraphSnapshot,
    allowed_labels: set[str],
    *,
    has_shard_filters: bool,
) -> None:
    if has_shard_filters:
        return
    for key, node in snapshot.nodes.items():
        if key.label in allowed_labels:
            filtered.nodes[key] = node


def _include_shard_relation_nodes(
    filtered: GraphSnapshot, snapshot: GraphSnapshot, relation: GraphRelation
) -> None:
    if relation.source in snapshot.nodes:
        filtered.nodes.setdefault(relation.source, snapshot.nodes[relation.source])
    if relation.target in snapshot.nodes:
        filtered.nodes.setdefault(relation.target, snapshot.nodes[relation.target])


def _filtered_snapshot(
    snapshot: GraphSnapshot,
    selection: SnapshotSelection | None = None,
    **legacy_selection: object,
) -> GraphSnapshot:
    selection = _resolved_snapshot_selection(selection, legacy_selection)
    shard_filters = _selected_shard_filters(selection)
    allowed_labels = _build_allowed_labels(
        selection,
        shard_filters,
    )
    if not allowed_labels:
        return snapshot

    label_scoped_only = (
        bool(selection.only_labels) and not selection.has_targeted_filters()
    )
    filtered = GraphSnapshot()
    allowed_analysis_relation_types = _allowed_analysis_relation_types(selection)
    has_shard_filters = bool(shard_filters)
    _seed_filtered_nodes(
        filtered, snapshot, allowed_labels, has_shard_filters=has_shard_filters
    )

    for rel_key, relation in snapshot.relations.items():
        _include_filtered_relation(
            filtered,
            snapshot,
            rel_key,
            relation,
            allowed_labels=allowed_labels,
            allowed_analysis_relation_types=allowed_analysis_relation_types,
            label_scoped_only=label_scoped_only,
            selection=selection,
            has_shard_filters=has_shard_filters,
            shard_filters=shard_filters,
        )
    return filtered


def _resolved_snapshot_selection(
    selection: SnapshotSelection | None,
    legacy_selection: dict[str, object],
) -> SnapshotSelection:
    if selection is not None:
        return selection
    return SnapshotSelection(
        only_labels=tuple(str(item) for item in _as_iterable(legacy_selection.get("only_labels"))),
        only_analysis_layer=bool(legacy_selection.get("only_analysis_layer", False)),
        only_retirement_layer=bool(
            legacy_selection.get("only_retirement_layer", False)
        ),
        only_complexity_layer=bool(
            legacy_selection.get("only_complexity_layer", False)
        ),
        only_storage_layer=bool(legacy_selection.get("only_storage_layer", False)),
        only_runtime_evidence_layer=bool(
            legacy_selection.get("only_runtime_evidence_layer", False)
        ),
        only_workflow_graph=bool(legacy_selection.get("only_workflow_graph", False)),
        only_docs_drift=bool(legacy_selection.get("only_docs_drift", False)),
    )


def _include_filtered_relation(
    filtered: GraphSnapshot,
    snapshot: GraphSnapshot,
    rel_key: RelationKey,
    relation: GraphRelation,
    *,
    allowed_labels: set[str],
    allowed_analysis_relation_types: set[str],
    label_scoped_only: bool,
    selection: SnapshotSelection,
    has_shard_filters: bool,
    shard_filters: tuple[ShardFilter, ...],
) -> None:
    if _include_analysis_relation(
        filtered,
        rel_key,
        relation,
        allowed_labels=allowed_labels,
        allowed_analysis_relation_types=allowed_analysis_relation_types,
        label_scoped_only=label_scoped_only,
        selection=selection,
    ):
        return
    if has_shard_filters:
        _include_shard_filtered_relation(
            filtered, snapshot, rel_key, relation, shard_filters
        )
        return
    if (
        relation.source.label in allowed_labels
        and relation.target.label in allowed_labels
    ):
        filtered.relations[rel_key] = relation


def _include_shard_filtered_relation(
    filtered: GraphSnapshot,
    snapshot: GraphSnapshot,
    rel_key: RelationKey,
    relation: GraphRelation,
    shard_filters: tuple[ShardFilter, ...],
) -> None:
    if _relation_matches_shard_filters(relation, shard_filters):
        _include_shard_relation_nodes(filtered, snapshot, relation)
        filtered.relations[rel_key] = relation


@dataclass(frozen=True)
class PortSurfaceDescriptor:
    surface_name: str
    class_name: str
    module_name: str
    source_path: str


@dataclass(frozen=True)
class EntityScope:
    provider: str | None = None
    entity: str | None = None
    pipeline_name: str | None = None


@dataclass(frozen=True)
class SnapshotSelection:
    only_labels: tuple[str, ...] = ()
    only_analysis_layer: bool = False
    only_retirement_layer: bool = False
    only_complexity_layer: bool = False
    only_storage_layer: bool = False
    only_runtime_evidence_layer: bool = False
    only_workflow_graph: bool = False
    only_docs_drift: bool = False

    def has_targeted_filters(self) -> bool:
        return any(
            (
                self.only_analysis_layer,
                self.only_retirement_layer,
                self.only_complexity_layer,
                self.only_storage_layer,
                self.only_runtime_evidence_layer,
                self.only_workflow_graph,
                self.only_docs_drift,
            )
        )

    def targeted_mode(self) -> bool:
        return self.has_targeted_filters() or bool(self.only_labels)

    def mode_description(self) -> str:
        if self.only_complexity_layer:
            return "complexity-layer targeted sync"
        if self.only_retirement_layer:
            return "retirement-layer targeted sync"
        if self.only_analysis_layer:
            return "analysis-layer targeted sync"
        if self.only_storage_layer:
            return "storage-layer targeted sync"
        if self.only_runtime_evidence_layer:
            return "runtime-evidence targeted sync"
        if self.only_workflow_graph:
            return "workflow-graph targeted sync"
        if self.only_docs_drift:
            return "docs-drift targeted sync"
        return "targeted sync"


@dataclass(frozen=True)
class SyncApplyOptions:
    batch_size: int
    prune_stale: bool = False
    full_reset_managed_wave: bool = False
    prune_legacy_unmanaged: bool = False


@dataclass(frozen=True)
class WorkflowContext:
    workflow_name: str
    title: str
    relative_path: str
    today: str
    workflow: NodeKey


@dataclass(frozen=True)
class WorkflowJobContext:
    workflow_name: str
    job_id: str
    job_name: str
    relative_path: str
    today: str
    job: NodeKey


@dataclass(frozen=True)
class EntityPipelineContext:
    provider_name: str
    entity_name: str
    pipeline_name: str
    pipeline_key: NodeKey
    entity_key: NodeKey
    config_artifact: NodeKey
    today: str
    contract_ref: str
    retention_days: int | None
    config_version: str | None
    quality_version: str | None


@dataclass(frozen=True)
class CompositePipelineContext:
    composite_name: str
    pipeline_key: NodeKey
    config_artifact: NodeKey
    today: str
    composite_version: str | None


@dataclass(frozen=True)
class SchemaFieldSpec:
    contract_ref: str | None = None
    scope: EntityScope = EntityScope()
    required_in_quality: bool | None = None
    validation_types: list[str] | None = None
    drift_classification: str | None = None
    source_storage_refs: list[str] | None = None


@dataclass(frozen=True)
class StorageSurfaceSpec:
    ref: str
    summary: str
    layer: str
    today: str
    storage_kind: str
    scope: EntityScope = EntityScope()
    format_name: str | None = None
    mode: str | None = None
    enabled: bool | None = None
    retention_days: int | None = None
    config_version: str | None = None
    quality_version: str | None = None
    partition_by: list[str] | None = None
    sort_by: list[str] | None = None
    on_schema_mismatch: str | None = None
    versioning_mode: str | None = None
    version_column: str | None = None
    current_flag_column: str | None = None
    valid_from_column: str | None = None
    valid_to_column: str | None = None
    merge_strategy: str | None = None
    semantic_properties: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True)
class ControlPlaneArtifactSpec:
    artifact_name: str
    summary: str
    today: str
    artifact_family: str
    artifact_kind: str
    storage_ref: str
    artifact_format: str | None = None
    key_template: str | None = None


@dataclass(frozen=True)
class GroupedStatementFailureContext:
    kind: str
    group_name: str
    batch_index: int
    batch_count: int
    statement_index: int
    statement_count: int


@dataclass(frozen=True)
class AlertTargetContext:
    snapshot: GraphSnapshot
    pipeline_nodes: dict[str, NodeKey]
    provider_nodes: list[NodeKey]
    contract_nodes: dict[str, NodeKey]
    memory_mapping: dict[str, object]


@dataclass(frozen=True)
class EntityLayerFieldContext:
    payload: dict[str, object]
    surface: NodeKey
    layer_name: str
    quality_index: dict[str, dict[str, JsonValue]]
    layer_config: dict[str, object]


@dataclass(frozen=True)
class CompositeOutputConfig:
    merge_payload: dict[str, object]
    output_payload: dict[str, object]
    group_fields: list[tuple[str, str]]
    source_storage_refs: list[str]
    schema_fields_by_storage: dict[str, dict[str, NodeKey]]


@dataclass(frozen=True)
class ContractMappingConfig:
    source_prefixes: tuple[str, ...]
    control_plane_modules: list[str]
    control_plane_runtime_modules: list[str]
    lineage_modules: list[str]
    lineage_runtime_modules: list[str]
    control_plane_docs: list[str]
    lineage_docs: list[str]
    control_plane_anchor_fields: list[str]
    lineage_anchor_fields: list[str]


@dataclass(frozen=True)
class ContractEntryContext:
    root: Path
    registry_path: Path
    today: str
    contract_ref: str
    contract: NodeKey
    raw_entry: dict[str, object]


@dataclass
class DuplicationExtractionContext:
    snapshot: GraphSnapshot
    root: Path
    today: str
    config: dict[str, object]
    class_descriptors: dict[NodeKey, ClassDescriptor] = field(default_factory=dict)
    callable_descriptors: dict[NodeKey, CallableDescriptor] = field(
        default_factory=dict
    )
    class_name_index: dict[str, list[NodeKey]] = field(default_factory=dict)


@dataclass(frozen=True)
class DuplicateFamilyConfig:
    name: str
    roots: tuple[str, ...]
    package_family: str
    promotion_targets: tuple[NodeKey, ...]
    excluded_paths: tuple[str, ...] = ()


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


@dataclass(frozen=True)
class SurfaceRelationIndexes:
    incoming: dict[NodeKey, list[GraphRelation]]
    outgoing: dict[NodeKey, list[GraphRelation]]
    declared_children: dict[NodeKey, list[NodeKey]]


@dataclass(frozen=True)
class AnalysisAnchors:
    runtime: tuple[NodeKey, ...]
    config: tuple[NodeKey, ...]
    docs: tuple[NodeKey, ...]
    tests: tuple[NodeKey, ...]


@dataclass(frozen=True)
class ComplexityMetrics:
    branch_count: int
    nesting_depth: int
    call_count: int
    helper_call_count: int
    abstraction_fanout: int
    api_surface_to_logic_ratio: float


# Canonical names used by complexity/retirement analysis surfaces (PD-C01).
type SurfaceAnchorSets = AnalysisAnchors
type SurfaceComplexityMetrics = ComplexityMetrics


@dataclass(frozen=True)
class AnalysisLabelSets:
    ignored_relation_types: set[str]
    runtime_labels: set[str]
    config_labels: set[str]
    doc_labels: set[str]
    test_labels: set[str]


@dataclass(frozen=True)
class RetirementScoreInputs:
    runtime_count: int
    config_count: int
    doc_count: int
    test_count: int
    recent_age_days: int | None
    wip_markers: list[str]
    deprecation_markers: list[str]


@dataclass(frozen=True)
class ComplexityScoreInputs:
    indirection_markers: list[str]
    stateful_markers: list[str]
    deprecation_markers: list[str]
    runtime_count: int
    config_count: int
    doc_count: int
    test_count: int
    blocked_by_current_cycle: bool


def _build_surface_relation_indexes(snapshot: GraphSnapshot) -> SurfaceRelationIndexes:
    incoming: dict[NodeKey, list[GraphRelation]] = {}
    outgoing: dict[NodeKey, list[GraphRelation]] = {}
    declared_children: dict[NodeKey, list[NodeKey]] = {}
    for relation in snapshot.relations.values():
        incoming.setdefault(relation.target, []).append(relation)
        outgoing.setdefault(relation.source, []).append(relation)
        if relation.relation_type == "DECLARES":
            declared_children.setdefault(relation.source, []).append(relation.target)
    return SurfaceRelationIndexes(
        incoming=incoming,
        outgoing=outgoing,
        declared_children=declared_children,
    )


def _analysis_read_source_text(
    root: Path, relative_path: str, text_cache: dict[str, str]
) -> str:
    if relative_path not in text_cache:
        path = root / relative_path
        try:
            text_cache[relative_path] = _read_analysis_source_text(path).casefold()
        except (OSError, TimeoutError):
            text_cache[relative_path] = ""
    return text_cache[relative_path]


def _read_analysis_source_text(
    path: Path,
    *,
    timeout_seconds: float = ANALYSIS_SOURCE_READ_TIMEOUT_SECONDS,
    os_name: str = os.name,
) -> str:
    """Read optional source text for marker analysis without blocking Windows runs."""
    if os_name != "nt":
        return _read_text(path)

    result: queue.Queue[tuple[str, str | BaseException]] = queue.Queue(maxsize=1)

    def _read() -> None:
        try:
            result.put(("ok", _read_text(path)))
        except (OSError, UnicodeError, ValueError) as exc:  # pragma: no cover
            result.put(("error", exc))

    thread = threading.Thread(
        target=_read,
        name=f"memory-analysis-read:{path.name}",
        daemon=True,
    )
    thread.start()
    thread.join(timeout_seconds)
    if thread.is_alive():
        raise TimeoutError(f"Timed out reading analysis source text: {path}")

    status, payload = result.get_nowait()
    if status == "error":
        if isinstance(payload, BaseException):
            raise payload
        raise RuntimeError(str(payload))
    return str(payload)


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


def _int_node_property(
    snapshot: GraphSnapshot, node_key: NodeKey, property_name: str
) -> int:
    node = snapshot.nodes.get(node_key)
    if node is None:
        return 0
    raw_value = node.properties.get(property_name)
    return _coerce_int(raw_value, 0) if isinstance(raw_value, (int, float, str)) else 0


def _aggregate_callable_metrics(
    snapshot: GraphSnapshot, node_key: NodeKey
) -> tuple[int, int, int, int]:
    return (
        _int_node_property(snapshot, node_key, "branch_count"),
        _int_node_property(snapshot, node_key, "nesting_depth"),
        _int_node_property(snapshot, node_key, "call_count"),
        _int_node_property(snapshot, node_key, "helper_call_count"),
    )


def _callable_surface_complexity_metrics(
    snapshot: GraphSnapshot, surface_key: NodeKey
) -> ComplexityMetrics:
    branch_count, nesting_depth, call_count, helper_call_count = (
        _aggregate_callable_metrics(snapshot, surface_key)
    )
    abstraction_fanout = max(1, call_count)
    return ComplexityMetrics(
        branch_count=branch_count,
        nesting_depth=nesting_depth,
        call_count=call_count,
        helper_call_count=helper_call_count,
        abstraction_fanout=abstraction_fanout,
        api_surface_to_logic_ratio=round(
            call_count / max(1, branch_count + nesting_depth), 2
        ),
    )


def _class_surface_complexity_metrics(
    snapshot: GraphSnapshot,
    indexes: SurfaceRelationIndexes,
    surface_key: NodeKey,
) -> ComplexityMetrics:
    methods = [
        child
        for child in indexes.declared_children.get(surface_key, ())
        if child.label == "method_surface"
    ]
    method_metrics = [
        _aggregate_callable_metrics(snapshot, method_key) for method_key in methods
    ]
    branch_count = sum(metric[0] for metric in method_metrics)
    return ComplexityMetrics(
        branch_count=branch_count,
        nesting_depth=max((metric[1] for metric in method_metrics), default=0),
        call_count=sum(metric[2] for metric in method_metrics),
        helper_call_count=sum(metric[3] for metric in method_metrics),
        abstraction_fanout=len(methods),
        api_surface_to_logic_ratio=round(len(methods) / max(1, branch_count + 1), 2),
    )


def _module_surface_complexity_metrics(
    snapshot: GraphSnapshot,
    indexes: SurfaceRelationIndexes,
    surface_key: NodeKey,
) -> ComplexityMetrics:
    children = indexes.declared_children.get(surface_key, ())
    functions = [child for child in children if child.label == "function_surface"]
    classes = [child for child in children if child.label == "class_surface"]
    methods = [
        method_key
        for class_key in classes
        for method_key in indexes.declared_children.get(class_key, ())
        if method_key.label == "method_surface"
    ]
    callable_metrics = [
        *[
            _aggregate_callable_metrics(snapshot, function_key)
            for function_key in functions
        ],
        *[_aggregate_callable_metrics(snapshot, method_key) for method_key in methods],
    ]
    branch_count = sum(metric[0] for metric in callable_metrics)
    abstraction_fanout = len(functions) + len(classes)
    return ComplexityMetrics(
        branch_count=branch_count,
        nesting_depth=max((metric[1] for metric in callable_metrics), default=0),
        call_count=sum(metric[2] for metric in callable_metrics),
        helper_call_count=sum(metric[3] for metric in callable_metrics),
        abstraction_fanout=abstraction_fanout,
        api_surface_to_logic_ratio=round(
            abstraction_fanout / max(1, branch_count + 1), 2
        ),
    )


def _aggregate_surface_complexity_metrics(
    snapshot: GraphSnapshot,
    indexes: SurfaceRelationIndexes,
    surface_key: NodeKey,
) -> ComplexityMetrics:
    if surface_key.label in {"function_surface", "method_surface"}:
        return _callable_surface_complexity_metrics(snapshot, surface_key)

    if surface_key.label == "class_surface":
        return _class_surface_complexity_metrics(snapshot, indexes, surface_key)

    if surface_key.label == "module_surface":
        return _module_surface_complexity_metrics(snapshot, indexes, surface_key)

    return ComplexityMetrics(0, 0, 0, 0, 0, 0.0)


def _complexity_marker_buckets(
    config: ComplexityAnalysisConfig,
    relative_path: str,
    symbol_name: str,
    source_text: str,
) -> tuple[list[str], list[str], list[str]]:
    normalized = f"{relative_path} {symbol_name}".casefold()
    indirection = sorted(
        {
            marker
            for marker in config.indirection_markers
            if marker in normalized or marker in source_text
        }
    )
    stateful = sorted(
        {
            marker
            for marker in config.stateful_markers
            if marker in normalized or marker in source_text
        }
    )
    deprecation = sorted(
        {
            marker
            for marker in config.deprecation_markers
            if marker in normalized or marker in source_text
        }
    )
    return indirection, stateful, deprecation


def _retirement_scores(
    config: RetirementAnalysisConfig,
    inputs: RetirementScoreInputs,
) -> tuple[int, int, bool]:
    only_test_referenced = (
        inputs.test_count > 0
        and inputs.runtime_count == 0
        and inputs.config_count == 0
        and inputs.doc_count == 0
    )
    cycle_score = 0
    if (
        inputs.recent_age_days is not None
        and inputs.recent_age_days <= config.current_cycle_age_days
    ):
        cycle_score += 2
    if inputs.wip_markers:
        cycle_score += 3
    if inputs.doc_count > 0 and inputs.runtime_count == 0:
        cycle_score += 1

    deletion_score = 0
    if inputs.runtime_count == 0:
        deletion_score += 3
    if inputs.config_count == 0:
        deletion_score += 2
    if inputs.doc_count == 0:
        deletion_score += 1
    if only_test_referenced:
        deletion_score += 2
    if inputs.deprecation_markers:
        deletion_score += 2
    if (
        inputs.recent_age_days is not None
        and inputs.recent_age_days >= config.stale_age_days
    ):
        deletion_score += 2
    return cycle_score, deletion_score - cycle_score, only_test_referenced


def _complexity_scores(
    metrics: ComplexityMetrics,
    inputs: ComplexityScoreInputs,
) -> tuple[int, int, int]:
    complexity_score = 0
    complexity_score += _threshold_score(metrics.branch_count, medium=3, high=6)
    complexity_score += _threshold_score(metrics.nesting_depth, medium=3, high=4)
    complexity_score += _threshold_score(metrics.helper_call_count, medium=2, high=4)
    complexity_score += _presence_score(len(inputs.indirection_markers))
    complexity_score += _presence_score(len(inputs.stateful_markers))
    complexity_score += _threshold_score(metrics.abstraction_fanout, medium=3, high=6)

    removable_score = complexity_score
    if inputs.runtime_count == 0:
        removable_score += 2
    if inputs.config_count == 0:
        removable_score += 2
    if inputs.doc_count == 0:
        removable_score += 1
    if inputs.test_count == 0:
        removable_score += 1
    if inputs.deprecation_markers:
        removable_score += 2
    if inputs.blocked_by_current_cycle:
        removable_score -= 3
    return complexity_score, complexity_score, removable_score


def _classify_complexity_candidate(
    config: ComplexityAnalysisConfig,
    *,
    removable_score: int,
    runtime_count: int,
    config_count: int,
    doc_count: int,
    blocked_by_current_cycle: bool,
) -> tuple[str, str]:
    if (
        removable_score >= config.removable_score_threshold
        and not blocked_by_current_cycle
    ):
        removal_confidence = (
            "high"
            if removable_score >= config.removable_score_threshold + 2
            else "medium"
        )
        return "removable_complexity", removal_confidence
    if runtime_count == 0 and config_count == 0 and doc_count == 0:
        return "overengineered_stale", "medium"
    return "overengineered_active", "low"


def _configured_node_keys(
    label: str,
    values: object,
    default_names: tuple[str, ...],
) -> list[NodeKey]:
    names = _as_string_list(values) or list(default_names)
    return [NodeKey(label, name) for name in names]


def _link_existing_targets(
    snapshot: GraphSnapshot,
    source: NodeKey,
    relation_type: str,
    targets: list[NodeKey],
    *,
    provenance: str,
) -> None:
    for target in targets:
        if target in snapshot.nodes:
            snapshot.add_relation(source, relation_type, target, provenance=provenance)


def _parser() -> argparse.ArgumentParser:
    from memory.graph.sync_pkg import cli as _cli

    return _cli._parser()


def _read_text(path: Path) -> str:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=REPO_ROOT)
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
    mapping_path = _memory_mapping_path(root)
    if not mapping_path.is_file():
        return {}
    return _read_yaml(mapping_path)


def _mapping_section(
    memory_mapping: dict[str, object], section: str
) -> dict[str, object]:
    return _mapping_dict_or_empty(memory_mapping.get(section, {}))


def _memory_mapping_path(root: Path) -> Path:
    preferred = root / DEFAULT_MEMORY_MAPPING_PATH
    if preferred.is_file():
        return preferred
    legacy = root / LEGACY_MEMORY_MAPPING_PATH
    if legacy.is_file():
        return legacy
    return preferred


def _mapping_dict_or_empty(payload: object) -> dict[str, object]:
    if isinstance(payload, dict):
        return payload
    return {}


def _configured_duplicate_families(
    payload: dict[str, object],
    duplication_config: dict[str, object],
) -> tuple[str, ...]:
    duplication_families = tuple(
        family.name
        for family in _as_iterable(duplication_config.get("families"))
        if isinstance(family, DuplicateFamilyConfig)
    )
    configured_families = tuple(
        family_name
        for family_name in _as_string_list(payload.get("families"))
        if family_name in duplication_families
    )
    return configured_families or duplication_families


def _casefolded_markers(
    payload: dict[str, object],
    key: str,
    defaults: list[str],
) -> tuple[str, ...]:
    return tuple(
        marker.casefold() for marker in (_as_string_list(payload.get(key)) or defaults)
    )


def _file_structure_config(memory_mapping: dict[str, object]) -> dict[str, object]:
    payload = _mapping_section(memory_mapping, "file_structure")

    raw_repo_zones = payload.get("repo_zones", {})
    repo_zones: dict[str, tuple[str, ...]] = {}
    if isinstance(raw_repo_zones, dict):
        for zone_name, zone_paths in raw_repo_zones.items():
            repo_zones[str(zone_name)] = tuple(_as_string_list(zone_paths))
    if not repo_zones:
        repo_zones = DEFAULT_FILE_STRUCTURE_REPO_ZONES

    excluded_prefixes = tuple(
        sorted(
            set(
                _as_string_list(payload.get("excluded_prefixes"))
                or list(DEFAULT_FILE_STRUCTURE_EXCLUDED_PREFIXES)
            )
        )
    )
    excluded_dir_names = tuple(
        sorted(
            set(
                _as_string_list(payload.get("excluded_dir_names"))
                or list(DEFAULT_FILE_STRUCTURE_EXCLUDED_DIR_NAMES)
            )
        )
    )
    promoted_hubs = tuple(sorted(set(_as_string_list(payload.get("promoted_hubs")))))
    return {
        "repo_zones": repo_zones,
        "excluded_prefixes": excluded_prefixes,
        "excluded_dir_names": excluded_dir_names,
        "promoted_hubs": promoted_hubs,
    }


def _duplication_analysis_config(
    memory_mapping: dict[str, object],
) -> dict[str, object]:
    payload = _mapping_section(memory_mapping, "duplication_analysis")
    families = _configured_duplication_families(payload.get("families", {}))
    return {
        "enabled": bool(payload.get("enabled", True)),
        "min_cluster_size": _coerce_int(payload.get("min_cluster_size", 2), 2),
        "min_ast_nodes": _coerce_int(payload.get("min_ast_nodes", 12), 12),
        "families": tuple(families),
    }


def _promotion_targets_from_payload(raw_targets: object) -> tuple[NodeKey, ...]:
    if not isinstance(raw_targets, list):
        return ()
    promotion_targets: list[NodeKey] = []
    for raw_target in raw_targets:
        if not isinstance(raw_target, dict):
            continue
        label = str(raw_target.get("label", "")).strip()
        name = str(raw_target.get("name", "")).strip()
        if label and name:
            promotion_targets.append(NodeKey(label, name))
    return tuple(promotion_targets)


def _duplicate_family_config(
    name: object, payload: object
) -> DuplicateFamilyConfig | None:
    if not isinstance(payload, dict):
        return None
    roots = tuple(_as_string_list(payload.get("roots")))
    package_family = str(payload.get("package_family", "")).strip()
    if not roots or not package_family:
        return None
    excluded_paths = tuple(sorted(set(_as_string_list(payload.get("excluded_paths")))))
    return DuplicateFamilyConfig(
        name=str(name),
        roots=roots,
        package_family=package_family,
        promotion_targets=_promotion_targets_from_payload(
            payload.get("promotion_targets", [])
        ),
        excluded_paths=excluded_paths,
    )


def _configured_duplication_families(
    raw_families: object,
) -> list[DuplicateFamilyConfig]:
    if not isinstance(raw_families, dict):
        return []
    families: list[DuplicateFamilyConfig] = []
    for family_name, family_payload in raw_families.items():
        family = _duplicate_family_config(family_name, family_payload)
        if family is not None:
            families.append(family)
    return families


def _retirement_analysis_config(
    memory_mapping: dict[str, object],
    duplication_config: dict[str, object],
) -> RetirementAnalysisConfig:
    payload = _mapping_section(memory_mapping, "retirement_analysis")
    family_names = _configured_duplicate_families(payload, duplication_config)

    return RetirementAnalysisConfig(
        enabled=bool(payload.get("enabled", True)),
        family_names=family_names,
        current_cycle_age_days=_coerce_int(
            payload.get("current_cycle_age_days", 45), 45
        ),
        stale_age_days=_coerce_int(payload.get("stale_age_days", 180), 180),
        dead_score_threshold=_coerce_int(payload.get("dead_score_threshold", 6), 6),
        wip_markers=_casefolded_markers(
            payload,
            "wip_markers",
            ["todo", "wip", "follow-up", "phase 2", "spike", "temporary"],
        ),
        deprecation_markers=_casefolded_markers(
            payload,
            "deprecation_markers",
            [
                "deprecated",
                "legacy",
                "obsolete",
                "compat",
                "remove after",
                "migration shim",
            ],
        ),
    )


def _complexity_analysis_config(
    memory_mapping: dict[str, object],
    duplication_config: dict[str, object],
    retirement_config: RetirementAnalysisConfig,
) -> ComplexityAnalysisConfig:
    payload = _mapping_section(memory_mapping, "complexity_analysis")
    family_names = _configured_duplicate_families(payload, duplication_config)

    return ComplexityAnalysisConfig(
        enabled=bool(payload.get("enabled", True)),
        family_names=family_names or retirement_config.family_names,
        complexity_score_threshold=_coerce_int(
            payload.get("complexity_score_threshold", 4), 4
        ),
        removable_score_threshold=_coerce_int(
            payload.get("removable_score_threshold", 7), 7
        ),
        indirection_markers=_casefolded_markers(
            payload,
            "indirection_markers",
            [
                "helper",
                "helpers",
                "mixin",
                "policy",
                "codec",
                "compat",
                "legacy",
                "wrapper",
                "shim",
            ],
        ),
        stateful_markers=_casefolded_markers(
            payload,
            "stateful_markers",
            ["checkpoint", "resume", "state", "fsm", "transition", "runner"],
        ),
        deprecation_markers=retirement_config.deprecation_markers,
        blocker_anchor_limit=_coerce_int(payload.get("blocker_anchor_limit", 3), 3),
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
    init_suffix = f"/{INIT_PY}"
    if relative_path.endswith(init_suffix):
        dotted = relative_path.removesuffix(init_suffix).replace("/", ".")
    else:
        dotted = _module_dotted_name(relative_path)
    return dotted.removeprefix("src.")


def _is_ignored_repo_path(path: Path) -> bool:
    return "__pycache__" in path.parts


def _normalize_repo_relative_path(relative_path: str) -> str:
    return relative_path.replace("\\", "/").strip().strip("/")


def _coerce_repo_relative_path(root: Path, raw_path: str) -> str:
    normalized = _normalize_repo_relative_path(raw_path)
    if not normalized:
        return ""

    root_normalized = _normalize_repo_relative_path(root.resolve().as_posix())
    normalized_lower = normalized.casefold()
    root_lower = root_normalized.casefold()
    if normalized_lower == root_lower:
        return ""
    if normalized_lower.startswith(f"{root_lower}/"):
        return normalized[len(root_normalized) + 1 :]

    root_anchor = root.resolve().name.casefold()
    parts = [part for part in normalized.split("/") if part]
    parts_lower = [part.casefold() for part in parts]
    if root_anchor in parts_lower:
        anchor_index = parts_lower.index(root_anchor)
        return "/".join(parts[anchor_index + 1 :])

    return normalized


def _is_excluded_file_structure_path(
    relative_path: str, config: dict[str, object]
) -> bool:
    normalized = _normalize_repo_relative_path(relative_path)
    path = Path(normalized)
    excluded_dir_names = {
        name for name in _as_string_list(config.get("excluded_dir_names")) if name
    }
    if any(part in excluded_dir_names for part in path.parts):
        return True

    excluded_prefixes = [
        prefix.strip("/")
        for prefix in _as_string_list(config.get("excluded_prefixes"))
        if prefix
    ]
    return any(
        normalized == prefix or normalized.startswith(f"{prefix}/")
        for prefix in excluded_prefixes
    )


def _promoted_directory_hubs(
    relative_path: str, config: dict[str, object]
) -> list[str]:
    promoted = {
        entry.strip("/")
        for entry in _as_string_list(config.get("promoted_hubs"))
        if entry
    }
    path = Path(relative_path)
    matches: list[str] = []
    for index in range(1, len(path.parts) + 1):
        candidate = Path(*path.parts[:index]).as_posix()
        if candidate in promoted:
            matches.append(candidate)
    return matches


def _supplemental_directory_hubs_for_node(
    node_key: NodeKey, source_path_value: str
) -> tuple[str, ...]:
    if node_key.label == "script_surface" and any(
        source_path_value.startswith(prefix) for prefix in OPS_SCRIPT_HUB_PREFIXES
    ):
        return ("scripts/ops",)
    return ()


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


def _git_last_commit_age_days(
    root: Path,
    relative_path: str,
    today: date,
    cache: dict[str, int | None],
) -> int | None:
    if relative_path in cache:
        return cache[relative_path]
    try:
        result = _run_git_history_subprocess(
            [
                _resolve_git_executable(),
                "-C",
                str(root),
                "log",
                "-1",
                "--format=%ct",
                "--",
                relative_path,
            ],
            timeout_seconds=10.0,
        )
    except subprocess.TimeoutExpired:
        cache[relative_path] = None
        return None
    timestamp = result.stdout.strip()
    if result.returncode != 0 or not timestamp.isdigit():
        cache[relative_path] = None
        return None
    committed_at = datetime.fromtimestamp(_coerce_int(timestamp), tz=UTC).date()
    age = max(0, (today - committed_at).days)
    cache[relative_path] = age
    return age


def _git_last_commit_age_days_bulk(
    root: Path,
    relative_paths: list[str],
    today: date,
    cache: dict[str, int | None],
    *,
    chunk_size: int = 1024,
) -> dict[str, int | None]:
    unique_paths = [path for path in dict.fromkeys(relative_paths) if path]
    if not unique_paths:
        return {}

    git_executable = _resolve_git_executable()
    resolved = _git_cached_commit_ages(unique_paths, cache)
    pending_paths = [path for path in unique_paths if path not in resolved]
    for start_index in range(0, len(pending_paths), chunk_size):
        chunk = pending_paths[start_index : start_index + chunk_size]
        if not chunk:
            continue
        tracked_chunk = _git_chunk_tracked_paths(
            git_executable=git_executable,
            root=root,
            chunk=chunk,
        )
        untracked_paths = sorted(set(chunk) - set(tracked_chunk))
        for path in untracked_paths:
            cache[path] = None
            resolved[path] = None
        if not tracked_chunk:
            continue
        chunk_results = _git_chunk_commit_ages(
            git_executable=git_executable,
            root=root,
            chunk=tracked_chunk,
            today=today,
        )
        cache.update(chunk_results)
        resolved.update(chunk_results)
    return {path: resolved.get(path) for path in unique_paths}


def _git_cached_commit_ages(
    unique_paths: list[str],
    cache: dict[str, int | None],
) -> dict[str, int | None]:
    return {path: cache[path] for path in unique_paths if path in cache}


def _run_git_history_subprocess(
    command: list[str], *, timeout_seconds: float | None = None
) -> subprocess.CompletedProcess[str]:
    """Run Git history probes with compatibility fallbacks for test doubles."""
    try:
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        raise
    except TypeError:
        # Some lightweight test doubles still implement the historical
        # positional-only signature (cmd, check, capture_output, text).
        legacy_run = cast(
            Callable[..., subprocess.CompletedProcess[str]],
            subprocess.run,
        )
        return legacy_run(command, False, True, True)


def _git_chunk_commit_ages(
    *,
    git_executable: str,
    root: Path,
    chunk: list[str],
    today: date,
) -> dict[str, int | None]:
    try:
        result = _run_git_history_subprocess(
            [
                git_executable,
                "-C",
                str(root),
                "log",
                "--format=__TS__%ct",
                "--name-only",
                "--",
                *chunk,
            ],
            timeout_seconds=10.0,
        )
    except subprocess.TimeoutExpired:
        if len(chunk) <= 1:
            return {
                path: _git_last_commit_age_days(root, path, today, {}) for path in chunk
            }
        middle = len(chunk) // 2
        first_half = _git_chunk_commit_ages(
            git_executable=git_executable,
            root=root,
            chunk=chunk[:middle],
            today=today,
        )
        second_half = _git_chunk_commit_ages(
            git_executable=git_executable,
            root=root,
            chunk=chunk[middle:],
            today=today,
        )
        first_half.update(second_half)
        return first_half
    chunk_results = dict.fromkeys(chunk)
    if result.returncode != 0:
        return chunk_results
    return _parse_git_chunk_age_output(result.stdout, chunk, today)


def _git_chunk_tracked_paths(
    *,
    git_executable: str,
    root: Path,
    chunk: list[str],
) -> list[str]:
    result = _run_git_history_subprocess(
        [
            git_executable,
            "-C",
            str(root),
            "ls-files",
            "--cached",
            "--",
            *chunk,
        ]
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _parse_git_chunk_age_output(
    output: str,
    chunk: list[str],
    today: date,
) -> dict[str, int | None]:
    chunk_results = dict.fromkeys(chunk)
    current_timestamp: int | None = None
    unresolved = set(chunk)
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("__TS__"):
            timestamp = line.removeprefix("__TS__")
            current_timestamp = _coerce_int(timestamp) if timestamp.isdigit() else None
            continue
        if current_timestamp is None or line not in unresolved:
            continue
        committed_at = datetime.fromtimestamp(current_timestamp, tz=UTC).date()
        chunk_results[line] = max(0, (today - committed_at).days)
        unresolved.remove(line)
        if not unresolved:
            break
    return chunk_results


def _resolve_git_executable() -> str:
    git_path = shutil.which("git")
    if git_path:
        return git_path
    windows_candidates = (
        "/mnt/c/Program Files/Git/cmd/git.exe",
        "/mnt/c/Program Files/Git/bin/git.exe",
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files\Git\bin\git.exe",
    )
    for candidate in windows_candidates:
        if Path(candidate).exists():
            return candidate
    return "git"


def _path_contains_any_token(path: Path, tokens: list[str]) -> bool:
    normalized = _read_text(path).lower()
    return any(token.lower() in normalized for token in tokens)


def _extract_bioetl_metrics(text: str) -> set[str]:
    return set(BIOETL_METRIC_PATTERN.findall(text))


def _dashboard_metric_index(root: Path) -> dict[NodeKey, set[str]]:
    dashboards_root = root / "grafana" / "dashboards"
    if not dashboards_root.is_dir():
        return {}
    metric_index: dict[NodeKey, set[str]] = {}
    for dashboard_path in sorted(dashboards_root.glob("*.json")):
        try:
            payload = _read_json(dashboard_path)
        except Exception:
            # Snapshot building should stay resilient to malformed or
            # partially edited dashboard files.
            payload = {}
        metrics = _dashboard_metrics_from_payload(payload)
        metric_index[NodeKey("dashboard_surface", dashboard_path.stem)] = metrics
    return metric_index


def _dashboard_metrics_from_payload(payload: dict[str, object]) -> set[str]:
    metrics: set[str] = set()
    stack = _dashboard_panel_stack(payload)
    while stack:
        panel = stack.pop()
        if not isinstance(panel, dict):
            continue
        stack.extend(_nested_dashboard_panels(panel))
        metrics.update(_dashboard_panel_target_metrics(panel))
    return metrics


def _dashboard_panel_stack(payload: dict[str, object]) -> list[object]:
    panels = payload.get("panels")
    return list(panels) if isinstance(panels, list) else []


def _nested_dashboard_panels(panel: dict[str, object]) -> list[object]:
    nested = panel.get("panels")
    return list(nested) if isinstance(nested, list) else []


def _dashboard_panel_target_metrics(panel: dict[str, object]) -> set[str]:
    targets = panel.get("targets")
    if not isinstance(targets, list):
        return set()
    metrics: set[str] = set()
    for target in targets:
        if not isinstance(target, dict):
            continue
        expr = target.get("expr")
        if isinstance(expr, str):
            metrics.update(_extract_bioetl_metrics(expr))
    return metrics


def _parse_python_ast(path: Path) -> ast.Module | None:
    if path.suffix != ".py":
        return None
    try:
        return ast.parse(_read_text(path), filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError):
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
        "decorator_count": len(node.decorator_list),
    }
    encoded = json.dumps(payload, sort_keys=True)
    # Deterministic structural fingerprint used for clustering, not for secrets.
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class _ShapeNormalizer(ast.NodeTransformer):
    def visit_arg(self, node: ast.arg) -> ast.arg:
        replacement = ast.arg(arg="ARG", annotation=None, type_comment=None)
        replacement.lineno = node.lineno
        replacement.col_offset = node.col_offset
        replacement.end_lineno = node.end_lineno
        replacement.end_col_offset = node.end_col_offset
        return replacement

    def visit_Name(self, node: ast.Name) -> ast.AST:
        return ast.copy_location(ast.Name(id="VAR", ctx=node.ctx), node)

    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
        value = self.visit(node.value)
        return ast.copy_location(
            ast.Attribute(value=value, attr="ATTR", ctx=node.ctx), node
        )

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        value = node.value
        if value is None or isinstance(value, bool):
            return node
        replacement: JsonScalar
        if isinstance(value, str):
            replacement = "STR"
        elif isinstance(value, (int, float, complex)):
            replacement = 0
        elif isinstance(value, bytes):
            replacement = "BYTES"
        else:
            replacement = "CONST"
        return ast.copy_location(ast.Constant(value=replacement), node)


def _normalized_callable_hash(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    module = ast.Module(body=node.body, type_ignores=[])
    normalized = _ShapeNormalizer().visit(module)
    ast.fix_missing_locations(normalized)
    dumped = ast.dump(normalized, annotate_fields=True, include_attributes=False)
    # Deterministic structural fingerprint used for clustering, not for secrets.
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


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


def _threshold_score(value: int, *, medium: int, high: int) -> int:
    if value >= high:
        return 2
    if value >= medium:
        return 1
    return 0


def _presence_score(size: int) -> int:
    return _threshold_score(size, medium=1, high=2)


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


def _family_for_path(
    relative_path: str, config: dict[str, object]
) -> DuplicateFamilyConfig | None:
    families = config.get("families", ())
    if not isinstance(families, tuple):
        return None
    best: DuplicateFamilyConfig | None = None
    for family in families:
        if not isinstance(family, DuplicateFamilyConfig):
            continue
        if not _family_matches_relative_path(relative_path, family):
            continue
        if best is None or _family_root_priority(family) > _family_root_priority(best):
            best = family
    return best


def _family_matches_relative_path(
    relative_path: str, family: DuplicateFamilyConfig
) -> bool:
    if relative_path in family.excluded_paths:
        return False
    return any(
        relative_path == root or relative_path.startswith(f"{root}/")
        for root in family.roots
    )


def _family_root_priority(family: DuplicateFamilyConfig) -> int:
    return max(len(root) for root in family.roots)


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
        if _looks_like_dataframe_model_class(node):
            class_names.append(node.name)
    return class_names


def _looks_like_dataframe_model_class(node: ast.ClassDef) -> bool:
    """Return True when a class likely represents a Pandera DataFrameModel schema."""
    if any(_is_dataframe_model_base(base) for base in node.bases):
        return True
    if not node.name.endswith("Schema"):
        return False
    return any(isinstance(child, ast.AnnAssign) for child in node.body)


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


def _build_port_surface_catalog(
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
        _seed_port_surface_catalog(
            root,
            port_path,
            descriptors,
            module_surfaces,
            symbol_index,
            init_paths,
        )

    _propagate_port_init_exports(init_paths, module_surfaces, symbol_index)

    return descriptors, module_surfaces, symbol_index


def _seed_port_surface_catalog(
    root: Path,
    port_path: Path,
    descriptors: list[PortSurfaceDescriptor],
    module_surfaces: dict[str, set[str]],
    symbol_index: dict[str, dict[str, str]],
    init_paths: list[tuple[str, Path]],
) -> None:
    if _is_ignored_repo_path(port_path) or "noop" in port_path.parts:
        return
    relative_path = _rel_path(root, port_path)
    module_name = _python_surface_name(relative_path)
    if port_path.name == INIT_PY:
        init_paths.append((module_name, port_path))
    _register_port_protocol_descriptors(
        port_path,
        relative_path,
        module_name,
        descriptors,
        module_surfaces,
        symbol_index,
    )


def _register_port_protocol_descriptors(
    port_path: Path,
    relative_path: str,
    module_name: str,
    descriptors: list[PortSurfaceDescriptor],
    module_surfaces: dict[str, set[str]],
    symbol_index: dict[str, dict[str, str]],
) -> None:
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


def _propagate_port_init_exports(
    init_paths: list[tuple[str, Path]],
    module_surfaces: dict[str, set[str]],
    symbol_index: dict[str, dict[str, str]],
) -> None:
    changed = True
    while changed:
        changed = False
        for module_name, init_path in init_paths:
            if _merge_port_init_exports(
                module_name, init_path, module_surfaces, symbol_index
            ):
                changed = True


def _merge_port_init_exports(
    module_name: str,
    init_path: Path,
    module_surfaces: dict[str, set[str]],
    symbol_index: dict[str, dict[str, str]],
) -> bool:
    changed = False
    exported_surfaces = module_surfaces.setdefault(module_name, set())
    exported_symbols = symbol_index.setdefault(module_name, {})
    for imported_module, imported_name, alias_name in _imported_symbols(init_path):
        if not imported_module.startswith(PORTS_MODULE_PREFIX):
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
    return changed


def _imported_port_surfaces(
    path: Path,
    port_module_surfaces: dict[str, set[str]],
    port_symbol_index: dict[str, dict[str, str]],
) -> set[str]:
    tree = _parse_python_ast(path)
    if tree is None:
        return set()

    imported: set[str] = set()
    for node in ast.walk(tree):
        imported.update(
            _imported_port_surfaces_for_node(
                node,
                port_module_surfaces=port_module_surfaces,
                port_symbol_index=port_symbol_index,
            )
        )
    return imported


def _imported_port_surfaces_for_node(
    node: ast.AST,
    *,
    port_module_surfaces: dict[str, set[str]],
    port_symbol_index: dict[str, dict[str, str]],
) -> set[str]:
    if isinstance(node, ast.Import):
        return _imported_port_surfaces_from_import(node, port_module_surfaces)
    if isinstance(node, ast.ImportFrom) and node.module is not None:
        return _imported_port_surfaces_from_import_from(
            node,
            port_module_surfaces=port_module_surfaces,
            port_symbol_index=port_symbol_index,
        )
    return set()


def _imported_port_surfaces_from_import(
    node: ast.Import,
    port_module_surfaces: dict[str, set[str]],
) -> set[str]:
    imported: set[str] = set()
    for alias in node.names:
        if alias.name.startswith(PORTS_MODULE_PREFIX):
            imported.update(port_module_surfaces.get(alias.name, set()))
    return imported


def _imported_port_surfaces_from_import_from(
    node: ast.ImportFrom,
    *,
    port_module_surfaces: dict[str, set[str]],
    port_symbol_index: dict[str, dict[str, str]],
) -> set[str]:
    if node.module is None or not node.module.startswith(PORTS_MODULE_PREFIX):
        return set()
    if any(alias.name == "*" for alias in node.names):
        return set(port_module_surfaces.get(node.module, set()))
    imported: set[str] = set()
    symbol_targets = port_symbol_index.get(node.module, {})
    for alias in node.names:
        target = symbol_targets.get(alias.name)
        if target is not None:
            imported.add(target)
    return imported


def _resolve_python_module_surface(root: Path, module_name: str) -> NodeKey | None:
    relative_py = Path("src") / Path(*module_name.split("."))
    file_candidate = root / relative_py.with_suffix(".py")
    if file_candidate.is_file():
        return NodeKey("module_surface", _rel_path(root, file_candidate))
    init_candidate = root / relative_py / INIT_PY
    if init_candidate.is_file():
        return NodeKey("module_surface", _rel_path(root, init_candidate))
    return None


def _matching_imported_module_names(
    node: ast.AST, prefixes: tuple[str, ...]
) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(
            alias.name for alias in node.names if alias.name.startswith(prefixes)
        )
    if (
        isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith(prefixes)
    ):
        return (node.module,)
    return ()


def _imported_repo_modules(path: Path, prefixes: tuple[str, ...]) -> set[str]:
    tree = _parse_python_ast(path)
    if tree is None:
        return set()

    imported: set[str] = set()
    for node in ast.walk(tree):
        imported.update(_matching_imported_module_names(node, prefixes))
    return imported


def _runtime_dimensions(*parts: str) -> set[str]:
    combined = " ".join(parts)
    dimensions = set()
    for dim in _RUNTIME_DIMENSIONS:
        if re.search(rf"\b{dim}\b", combined):
            dimensions.add(dim)
    return dimensions


_RUNTIME_DIMENSIONS = (
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
)


@dataclass(frozen=True)
class AlertRuleSettings:
    pipeline_mode: str
    pipeline_kind: str
    provider_mode: str
    contract_mode: str


def _alert_rule_settings(
    memory_mapping: dict[str, object],
    *,
    alert_name: str,
    group_name: str,
) -> AlertRuleSettings:
    group_rule, alert_rule = _alert_rule_overrides(
        memory_mapping,
        alert_name=alert_name,
        group_name=group_name,
    )
    return AlertRuleSettings(
        pipeline_mode=str(
            alert_rule.get("pipelines", group_rule.get("pipelines", "auto"))
        ),
        pipeline_kind=str(
            alert_rule.get("pipeline_kind", group_rule.get("pipeline_kind", "any"))
        ),
        provider_mode=str(
            alert_rule.get("providers", group_rule.get("providers", "auto"))
        ),
        contract_mode=str(
            alert_rule.get("contracts", group_rule.get("contracts", "none"))
        ),
    )


def _alert_rule_overrides(
    memory_mapping: dict[str, object],
    *,
    alert_name: str,
    group_name: str,
) -> tuple[dict[str, object], dict[str, object]]:
    alerts_config = _alerts_config_section(memory_mapping)
    groups, rules = _alert_override_maps(alerts_config)
    group_rule = _as_mapping(groups.get(group_name)) if isinstance(groups, dict) else {}
    alert_rule = _as_mapping(rules.get(alert_name)) if isinstance(rules, dict) else {}
    return group_rule, alert_rule


def _alerts_config_section(memory_mapping: dict[str, object]) -> dict[str, object]:
    alerts_config = memory_mapping.get("alerts")
    return alerts_config if isinstance(alerts_config, dict) else {}


def _alert_override_maps(
    alerts_config: dict[str, object],
) -> tuple[object, object]:
    return alerts_config.get("groups"), alerts_config.get("rules")


def _pipeline_targets_for_alert(
    context: AlertTargetContext,
    *,
    pipeline_mode: str,
    pipeline_kind: str,
    normalized: str,
    dimensions: set[str],
) -> list[NodeKey]:
    pipeline_targets = _pipeline_targets_for_alert_mode(
        context, pipeline_mode, dimensions
    )
    effective_kind = _alert_pipeline_kind_override(
        pipeline_kind, normalized, dimensions
    )
    if effective_kind in {"entity", "composite"}:
        return _pipeline_targets_matching_kind(
            context, pipeline_targets, effective_kind
        )
    return pipeline_targets


def _pipeline_targets_for_alert_mode(
    context: AlertTargetContext,
    pipeline_mode: str,
    dimensions: set[str],
) -> list[NodeKey]:
    all_pipelines = _all_pipeline_targets(context)
    if pipeline_mode == "all":
        return all_pipelines
    if pipeline_mode == "entity":
        return _pipeline_targets_matching_kind(context, all_pipelines, "entity")
    if pipeline_mode == "composite":
        return _pipeline_targets_matching_kind(context, all_pipelines, "composite")
    if pipeline_mode == "auto" and "pipeline" in dimensions:
        return all_pipelines
    return []


def _all_pipeline_targets(context: AlertTargetContext) -> list[NodeKey]:
    return list(context.pipeline_nodes.values())


def _alert_pipeline_kind_override(
    pipeline_kind: str,
    normalized: str,
    dimensions: set[str],
) -> str:
    if pipeline_kind in {"entity", "composite"}:
        return pipeline_kind
    if _entity_alert_signal_detected(normalized, dimensions):
        return "entity"
    return pipeline_kind


def _entity_alert_signal_detected(normalized: str, dimensions: set[str]) -> bool:
    return "entity" in dimensions or any(
        marker in normalized
        for marker in (
            "bioetl_dq_",
            "bioetl_silver_",
            'stage="bronze"',
            "bioetl_data_freshness_seconds",
        )
    )


def _pipeline_targets_matching_kind(
    context: AlertTargetContext,
    pipeline_targets: Iterable[NodeKey],
    pipeline_kind: str,
) -> list[NodeKey]:
    return [
        node
        for node in pipeline_targets
        if context.snapshot.nodes[node].properties.get("pipeline_kind") == pipeline_kind
    ]


def _provider_targets_for_alert(
    context: AlertTargetContext,
    *,
    provider_mode: str,
    normalized: str,
    dimensions: set[str],
) -> list[NodeKey]:
    provider_targets_requested = _provider_targets_requested(
        provider_mode,
        normalized=normalized,
        dimensions=dimensions,
    )
    return context.provider_nodes if provider_targets_requested else []


def _provider_targets_requested(
    provider_mode: str,
    *,
    normalized: str,
    dimensions: set[str],
) -> bool:
    return provider_mode == "all" or (
        provider_mode == "auto"
        and _provider_alert_signal_detected(normalized, dimensions)
    )


def _provider_alert_signal_detected(normalized: str, dimensions: set[str]) -> bool:
    return (
        "provider" in dimensions
        or "provider_health" in normalized
        or "bioetl_health_check_" in normalized
    )


def _contract_targets_for_alert(
    context: AlertTargetContext,
    *,
    contract_mode: str,
    pipeline_targets: list[NodeKey],
) -> list[NodeKey]:
    if contract_mode == "all":
        return _all_contract_targets(context)
    if contract_mode != "mapped":
        return []
    return sorted(
        _mapped_contract_targets(context, pipeline_targets), key=lambda node: node.name
    )


def _all_contract_targets(context: AlertTargetContext) -> list[NodeKey]:
    return list(context.contract_nodes.values())


def _mapped_contract_targets(
    context: AlertTargetContext,
    pipeline_targets: Iterable[NodeKey],
) -> set[NodeKey]:
    pipeline_target_set = set(pipeline_targets)
    return {
        relation.target
        for relation in context.snapshot.relations.values()
        if relation.source in pipeline_target_set
        and relation.relation_type == "DEPENDS_ON"
        and relation.target.label == "contract_surface"
    }


def _select_alert_targets(
    context: AlertTargetContext,
    alert_name: str,
    group_name: str,
    expr: str,
    dimensions: set[str],
) -> AlertTargetSelection:
    pipeline_targets, provider_targets, contract_targets = _raw_alert_targets(
        context,
        alert_name=alert_name,
        group_name=group_name,
        expr=expr,
        dimensions=dimensions,
    )
    return _sorted_alert_targets(pipeline_targets, provider_targets, contract_targets)


def _sorted_unique_node_keys(nodes: Iterable[NodeKey]) -> tuple[NodeKey, ...]:
    return tuple(sorted(set(nodes), key=lambda node: node.name))


def _raw_alert_targets(
    context: AlertTargetContext,
    *,
    alert_name: str,
    group_name: str,
    expr: str,
    dimensions: set[str],
) -> tuple[list[NodeKey], list[NodeKey], list[NodeKey]]:
    normalized = _normalized_alert_selector(group_name, expr)
    settings = _alert_rule_settings(
        context.memory_mapping,
        alert_name=alert_name,
        group_name=group_name,
    )
    pipeline_targets = _pipeline_targets_for_alert(
        context,
        pipeline_mode=settings.pipeline_mode,
        pipeline_kind=settings.pipeline_kind,
        normalized=normalized,
        dimensions=dimensions,
    )
    provider_targets = _provider_targets_for_alert(
        context,
        provider_mode=settings.provider_mode,
        normalized=normalized,
        dimensions=dimensions,
    )
    contract_targets = _contract_targets_for_alert(
        context,
        contract_mode=settings.contract_mode,
        pipeline_targets=pipeline_targets,
    )
    return pipeline_targets, provider_targets, contract_targets


def _normalized_alert_selector(group_name: str, expr: str) -> str:
    return f"{group_name} {expr}".lower()


def _sorted_alert_targets(
    pipeline_targets: list[NodeKey],
    provider_targets: list[NodeKey],
    contract_targets: list[NodeKey],
) -> AlertTargetSelection:
    return AlertTargetSelection(
        selected_pipelines=_sorted_unique_node_keys(pipeline_targets),
        selected_providers=_sorted_unique_node_keys(provider_targets),
        selected_contracts=_sorted_unique_node_keys(contract_targets),
    )


def _select_alert_dashboards(
    alert_name: str,
    group_name: str,
    expr: str,
    dashboard_metrics: dict[NodeKey, set[str]],
    memory_mapping: dict[str, object],
) -> list[NodeKey]:
    config = _alert_dashboard_config(
        memory_mapping,
        alert_name=alert_name,
    )
    explicit_dashboards = _configured_dashboard_targets(
        config.alert_rule.get("dashboards")
    )
    common_dashboards = _configured_dashboard_targets(
        config.dashboard_fallbacks.get("common")
    )
    group_dashboards = _configured_dashboard_targets(
        config.fallback_groups.get(group_name)
    )
    metric_dashboards = _metric_dashboard_targets(expr, dashboard_metrics)
    return _merged_alert_dashboard_targets(
        explicit_dashboards=explicit_dashboards,
        metric_dashboards=metric_dashboards,
        group_dashboards=group_dashboards,
        common_dashboards=common_dashboards,
    )


def _merged_alert_dashboard_targets(
    *,
    explicit_dashboards: set[NodeKey],
    metric_dashboards: set[NodeKey],
    group_dashboards: set[NodeKey],
    common_dashboards: set[NodeKey],
) -> list[NodeKey]:
    selected = set(explicit_dashboards)
    selected.update(metric_dashboards)
    if not metric_dashboards:
        selected.update(group_dashboards)
    selected.update(common_dashboards)
    return _sorted_node_keys(selected)


def _sorted_node_keys(nodes: Iterable[NodeKey]) -> list[NodeKey]:
    return sorted(nodes, key=lambda node: node.name)


@dataclass(frozen=True)
class AlertDashboardConfig:
    alert_rule: dict[str, object]
    dashboard_fallbacks: dict[str, object]
    fallback_groups: dict[str, object]


def _alert_dashboard_config(
    memory_mapping: dict[str, object],
    *,
    alert_name: str,
) -> AlertDashboardConfig:
    alerts_config = _alerts_config_section(memory_mapping)
    dashboard_fallbacks = _alert_dashboard_fallbacks(alerts_config)
    return AlertDashboardConfig(
        alert_rule=_configured_alert_rule(alerts_config, alert_name),
        dashboard_fallbacks=dashboard_fallbacks,
        fallback_groups=_alert_dashboard_fallback_groups(dashboard_fallbacks),
    )


def _configured_alert_rule(
    alerts_config: dict[str, object],
    alert_name: str,
) -> dict[str, object]:
    rules = alerts_config.get("rules")
    if not isinstance(rules, dict):
        return {}
    alert_rule = rules.get(alert_name)
    return alert_rule if isinstance(alert_rule, dict) else {}


def _alert_dashboard_fallbacks(
    alerts_config: dict[str, object],
) -> dict[str, object]:
    dashboard_fallbacks = alerts_config.get("dashboard_fallbacks")
    return dashboard_fallbacks if isinstance(dashboard_fallbacks, dict) else {}


def _alert_dashboard_fallback_groups(
    dashboard_fallbacks: dict[str, object],
) -> dict[str, object]:
    fallback_groups = dashboard_fallbacks.get("groups")
    return fallback_groups if isinstance(fallback_groups, dict) else {}


def _configured_dashboard_targets(values: object) -> set[NodeKey]:
    return _dashboard_target_keys(_as_string_list(values))


def _dashboard_target_keys(names: Iterable[str]) -> set[NodeKey]:
    return {NodeKey("dashboard_surface", name) for name in names}


def _metric_dashboard_targets(
    expr: str,
    dashboard_metrics: dict[NodeKey, set[str]],
) -> set[NodeKey]:
    metrics = _extract_bioetl_metrics(expr)
    return {
        dashboard
        for dashboard, dashboard_metric_names in dashboard_metrics.items()
        if metrics & dashboard_metric_names
    }


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


def _env_flag_is_enabled(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().casefold() not in {"", "0", "false", "no", "off"}


def _default_neo4j_host(env: dict[str, str]) -> str:
    if env.get("WSL_INTEROP") or env.get("WSL_DISTRO_NAME"):
        return "host.docker.internal"
    return "localhost"


_DEFAULT_NEO4J_AUDIT_USERNAME = "neo4j"
_DEFAULT_NEO4J_AUDIT_PASSWORD = "audit_secure_password"
_DEFAULT_NEO4J_AUDIT_DATABASE = "neo4j"


def resolve_neo4j_connection(
    root: Path, explicit_http_uri: str | None
) -> tuple[str, str, str, str]:
    env = load_repo_env(root)
    audit_mode = _env_flag_is_enabled(env.get("LIVE_AUDIT_MODE"))
    default_host = _default_neo4j_host(env)

    if audit_mode:
        username = env.get("NEO4J_AUDIT_USERNAME")
        password = env.get("NEO4J_AUDIT_PASSWORD")
        database = (
            env.get("NEO4J_AUDIT_DATABASE")
            or env.get("NEO4J_DATABASE")
            or _DEFAULT_NEO4J_AUDIT_DATABASE
        )
        auth_username, auth_password = _parse_auth_pair(env.get("NEO4J_AUDIT_AUTH"))
        username = username or auth_username or _DEFAULT_NEO4J_AUDIT_USERNAME
        password = password or auth_password or _DEFAULT_NEO4J_AUDIT_PASSWORD
        http_uri = (
            explicit_http_uri
            or env.get("NEO4J_AUDIT_HTTP_URI")
            or f"http://{default_host}:7475"  # NOSONAR - local Neo4j browser port
        )
    else:
        bolt_uri = env.get("NEO4J_URI", "bolt://localhost:7687")
        username = env.get("NEO4J_USERNAME") or env.get("NEO4J_AUTH_USERNAME")
        password = env.get("NEO4J_PASSWORD") or env.get("NEO4J_AUTH_PASSWORD")
        database = env.get("NEO4J_DATABASE", "neo4j")
        auth_username, auth_password = _parse_auth_pair(env.get("NEO4J_AUTH"))
        username = username or auth_username or "neo4j"
        password = password or auth_password
        if not password:
            raise RuntimeError(
                "Neo4j password not found in NEO4J_PASSWORD, NEO4J_AUTH_PASSWORD, or NEO4J_AUTH"
            )
        http_uri = (
            explicit_http_uri or env.get("NEO4J_HTTP_URI") or derive_http_uri(bolt_uri)
        )
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
    memory_mapping = _load_memory_mapping(root)
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
    _add_file_structure_surfaces(snapshot, root, project, today)
    _add_storage_data_surfaces(snapshot, root, project, today)
    _add_control_plane_runtime_evidence(snapshot, root, project, today)
    _add_ci_workflow_graph(snapshot, root, project, today)
    _add_cli_command_graph(snapshot, root, project, today)
    _add_docs_to_code_drift_edges(snapshot, root)
    _add_pipeline_doc_edges(snapshot)
    _add_reverse_module_doc_edges(snapshot)
    _add_adr_constraint_edges(snapshot, root, project, today)
    _add_retirement_analysis_surfaces(snapshot, root, project, today, memory_mapping)
    _add_complexity_analysis_surfaces(snapshot, root, project, today, memory_mapping)
    return snapshot


def _add_curated_docs(
    snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str
) -> None:
    for entry in CURATED_DOC_SOURCES:
        _add_curated_doc_source(snapshot, root, project, today, entry)


def _add_curated_doc_source(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    entry: dict[str, str],
) -> None:
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
    snapshot.add_relation(
        project, "HAS_DOC_SOURCE_SURFACE", source_node, provenance="curated_docs"
    )
    _link_curated_doc_artifact(
        snapshot,
        root,
        source_node,
        source_path=source_path,
        summary=summary,
        today=today,
    )


def _link_curated_doc_artifact(
    snapshot: GraphSnapshot,
    root: Path,
    source_node: NodeKey,
    *,
    source_path: str,
    summary: str,
    today: str,
) -> None:
    path = root / source_path
    if not path.is_file():
        return
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


def _evidence_summary_doc(
    snapshot: GraphSnapshot,
    root: Path,
    today: str,
    *,
    path: str,
    summary: str,
) -> tuple[Path, NodeKey]:
    doc_path = root / path
    relative_path = _rel_path(root, doc_path)
    doc = snapshot.add_node(
        "doc_artifact",
        relative_path,
        summary=summary,
        source_path=relative_path,
        source_kind="evidence_decision_summary",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    return doc_path, doc


def _summary_identifier_matches(path: Path, pattern: str) -> tuple[str, ...]:
    return tuple(sorted(set(re.findall(pattern, _read_text(path)))))


def _summary_table_rows(
    text: str, identifier_prefix: str
) -> tuple[tuple[str, str], ...]:
    pattern = re.compile(
        rf"\|\s*`({identifier_prefix}-[a-z0-9-]+)`\s*\|\s*([^|]+?)\s*\|",
        re.IGNORECASE,
    )
    return tuple(
        (match.group(1), match.group(2).strip()) for match in pattern.finditer(text)
    )


def _add_summary_identifiers(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
    *,
    doc: NodeKey,
    provenance: str,
    identifier_kind: str,
    matches: tuple[str, ...],
    summary: str,
    source_path: str,
) -> None:
    relation_type = "HAS_DECISION" if identifier_kind == "decision" else "HAS_RISK"
    for identifier in matches:
        node = snapshot.add_node(
            identifier_kind,
            identifier,
            summary=summary,
            source_path=source_path,
            source_kind="evidence_decision_summary",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="medium",
        )
        snapshot.add_relation(project, relation_type, node, provenance=provenance)
        snapshot.add_relation(node, "DESCRIBED_IN", doc, provenance=provenance)


def _add_summary_table_identifiers(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
    *,
    doc: NodeKey,
    provenance: str,
    identifier_kind: str,
    rows: tuple[tuple[str, str], ...],
    source_path: str,
) -> None:
    relation_type = "HAS_DECISION" if identifier_kind == "decision" else "HAS_RISK"
    for identifier, summary in rows:
        node = snapshot.add_node(
            identifier_kind,
            identifier,
            summary=summary,
            source_path=source_path,
            source_kind="evidence_decision_summary",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(project, relation_type, node, provenance=provenance)
        snapshot.add_relation(node, "DESCRIBED_IN", doc, provenance=provenance)


def _add_decisions_and_risks(
    snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str
) -> None:
    _add_package_topology_decisions_and_risks(snapshot, root, project, today)
    _add_governance_decisions_and_risks(snapshot, root, project, today)


def _add_package_topology_decisions_and_risks(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
) -> None:
    summary_path = (
        root / "docs/reports/evidence/project-package-topology/04-decisions/SUMMARY.md"
    )
    if not summary_path.is_file():
        return
    package_summary, package_doc = _evidence_summary_doc(
        snapshot,
        root,
        today,
        path="docs/reports/evidence/project-package-topology/04-decisions/SUMMARY.md",
        summary="Accepted package topology decisions and risks.",
    )
    source_path = _rel_path(root, package_summary)
    for identifier_kind, pattern, summary in _package_topology_summary_specs():
        _add_summary_identifiers(
            snapshot,
            project,
            today,
            doc=package_doc,
            provenance="package_topology_summary",
            identifier_kind=identifier_kind,
            matches=_summary_identifier_matches(package_summary, pattern),
            summary=summary,
            source_path=source_path,
        )


def _package_topology_summary_specs() -> tuple[tuple[str, str, str], ...]:
    return (
        ("decision", r"DEC-[a-z0-9-]+", "Accepted package-topology decision."),
        (
            "risk",
            r"RISK-[a-z0-9-]+",
            "Package-topology risk captured in evidence decisions.",
        ),
    )


def _add_governance_decisions_and_risks(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
) -> None:
    summary_path = root / GOVERNANCE_DECISIONS_SUMMARY_PATH
    if not summary_path.is_file():
        return
    governance_summary, governance_doc = _evidence_summary_doc(
        snapshot,
        root,
        today,
        path=GOVERNANCE_DECISIONS_SUMMARY_PATH,
        summary="Accepted governance decisions and associated risks.",
    )
    governance_text = _read_text(governance_summary)
    source_path = _rel_path(root, governance_summary)
    for identifier_kind, prefix in _governance_summary_table_specs():
        _add_summary_table_identifiers(
            snapshot,
            project,
            today,
            doc=governance_doc,
            provenance="governance_summary",
            identifier_kind=identifier_kind,
            rows=_summary_table_rows(governance_text, prefix),
            source_path=source_path,
        )


def _governance_summary_table_specs() -> tuple[tuple[str, str], ...]:
    return (
        ("decision", "DEC"),
        ("risk", "RISK"),
    )


def _add_runtime_layer_surface(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    *,
    layer_name: str,
    layer_path: Path,
    today: str,
) -> NodeKey:
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
    return layer


def _add_runtime_layer_families(
    snapshot: GraphSnapshot,
    root: Path,
    layer: NodeKey,
    *,
    layer_name: str,
    layer_path: Path,
    today: str,
) -> None:
    for family_path in sorted(
        path
        for path in layer_path.iterdir()
        if path.is_dir() and not _is_ignored_repo_path(path)
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


def _runtime_module_family_key(
    layer: NodeKey, *, layer_name: str, relative_path: str
) -> NodeKey:
    parts = Path(relative_path).parts
    if len(parts) >= 5:
        return NodeKey("package_family", f"{layer_name}/{parts[3]}")
    return layer


def _add_runtime_layer_modules(
    snapshot: GraphSnapshot,
    root: Path,
    layer: NodeKey,
    *,
    layer_name: str,
    layer_path: Path,
    today: str,
) -> None:
    for module_path in sorted(layer_path.rglob("*.py")):
        if module_path.name in {INIT_PY, MAIN_PY}:
            continue
        if _is_ignored_repo_path(module_path):
            continue
        relative_path = _rel_path(root, module_path)
        family_key = _runtime_module_family_key(
            layer, layer_name=layer_name, relative_path=relative_path
        )
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


def _add_layer_topology(
    snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str
) -> None:
    src_root = root / "src" / "bioetl"
    for layer_name in KNOWN_LAYERS:
        layer_path = src_root / layer_name
        if not layer_path.is_dir():
            continue
        layer = _add_runtime_layer_surface(
            snapshot,
            root,
            project,
            layer_name=layer_name,
            layer_path=layer_path,
            today=today,
        )
        _add_runtime_layer_families(
            snapshot,
            root,
            layer,
            layer_name=layer_name,
            layer_path=layer_path,
            today=today,
        )
        _add_runtime_layer_modules(
            snapshot,
            root,
            layer,
            layer_name=layer_name,
            layer_path=layer_path,
            today=today,
        )


def _add_provider_and_config_graph(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
) -> None:
    provider_nodes = _add_provider_surfaces(snapshot, root, project, today)
    entity_nodes = _add_entity_config_surfaces(snapshot, root, today, provider_nodes)
    _add_composite_config_surfaces(snapshot, root, project, today, entity_nodes)


def _add_provider_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
) -> dict[str, NodeKey]:
    providers_root = root / "configs" / "providers"
    provider_nodes: dict[str, NodeKey] = {}
    for provider_path in _provider_config_paths(providers_root):
        _add_provider_surface(
            snapshot,
            root,
            project,
            today,
            provider_path,
            provider_nodes=provider_nodes,
        )
    return provider_nodes


def _provider_config_paths(providers_root: Path) -> tuple[Path, ...]:
    return tuple(sorted(providers_root.glob(YAML_FILE_GLOB)))


def _add_provider_surface(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    provider_path: Path,
    *,
    provider_nodes: dict[str, NodeKey],
) -> None:
    payload = _read_yaml(provider_path)
    provider_name = str(payload.get("provider", provider_path.stem))
    auth_type, pagination = _provider_config_properties(payload.get("source", {}))
    provider = snapshot.add_node(
        "provider_surface",
        provider_name,
        summary=f"Provider surface for `{provider_name}`.",
        source_path=_rel_path(root, provider_path),
        source_kind="provider_config",
        auth_type=auth_type,
        pagination_strategy=pagination,
        entity_count=len(_as_iterable(payload.get("entities"))) or None,
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    provider_nodes[provider_name] = provider
    snapshot.add_relation(
        project, "HAS_PROVIDER", provider, provenance="provider_config"
    )
    _link_config_artifact(
        snapshot,
        provider,
        path=_rel_path(root, provider_path),
        summary=f"Provider config for `{provider_name}`.",
        source_kind="provider_config",
        today=today,
        provenance="provider_config",
    )


def _provider_config_properties(source_payload: object) -> tuple[str | None, str | None]:
    auth_type = None
    pagination = None
    provider_config = source_payload
    if isinstance(provider_config, dict):
        provider_config = provider_config.get("provider_config", provider_config)
        if isinstance(provider_config, dict):
            auth_type = _optional_text(provider_config.get("auth_type"))
            pagination_data = provider_config.get("pagination")
            if isinstance(pagination_data, dict):
                pagination = _optional_text(pagination_data.get("strategy"))
    return auth_type, pagination


def _add_entity_config_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    today: str,
    provider_nodes: dict[str, NodeKey],
) -> dict[str, NodeKey]:
    entities_root = root / "configs" / "entities"
    entity_nodes: dict[str, NodeKey] = {}
    for entity_path in _entity_config_paths(entities_root):
        _add_entity_config_surface(
            snapshot,
            root,
            today,
            entity_path,
            provider_nodes=provider_nodes,
            entity_nodes=entity_nodes,
        )
    return entity_nodes


def _entity_config_paths(entities_root: Path) -> tuple[Path, ...]:
    return tuple(sorted(entities_root.rglob(YAML_FILE_GLOB)))


def _add_entity_config_surface(
    snapshot: GraphSnapshot,
    root: Path,
    today: str,
    entity_path: Path,
    *,
    provider_nodes: dict[str, NodeKey],
    entity_nodes: dict[str, NodeKey],
) -> None:
    payload = _read_yaml(entity_path)
    provider_name, entity_name, node_name, summary = _entity_config_identity(
        entity_path, payload
    )
    entity = snapshot.add_node(
        "entity_config",
        node_name,
        summary=summary,
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
    _link_config_artifact(
        snapshot,
        entity,
        path=_rel_path(root, entity_path),
        summary=f"Entity config for `{provider_name}/{entity_name}`.",
        source_kind="entity_config",
        today=today,
        provenance="entity_config",
    )


def _entity_config_identity(
    entity_path: Path,
    payload: dict[str, object],
) -> tuple[str, str, str, str]:
    provider_name = str(payload.get("provider", entity_path.parent.name))
    entity_name = str(payload.get("entity", entity_path.stem))
    pipeline = payload.get("pipeline", {})
    pipeline_name = None
    pipeline_description = None
    if isinstance(pipeline, dict):
        pipeline_name = pipeline.get("pipeline_name")
        pipeline_description = pipeline.get("description")
    node_name = str(pipeline_name or f"{provider_name}_{entity_name}")
    summary = str(
        pipeline_description
        or f"Entity pipeline config for `{provider_name}/{entity_name}`."
    )
    return provider_name, entity_name, node_name, summary


def _add_composite_config_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    entity_nodes: dict[str, NodeKey],
) -> None:
    composites_root = root / "configs" / "composites"
    for composite_path in _composite_config_paths(composites_root):
        _add_composite_config_surface(
            snapshot,
            root,
            project,
            today,
            composite_path,
            entity_nodes=entity_nodes,
        )


def _composite_config_paths(composites_root: Path) -> tuple[Path, ...]:
    return tuple(sorted(composites_root.glob(YAML_FILE_GLOB)))


def _composite_config_identity(
    composite_path: Path,
    payload: dict[str, object],
) -> tuple[str, str, object, str | None]:
    composite_payload = payload.get("composite", {})
    composite_name = composite_path.stem
    summary = f"Composite pipeline config `{composite_name}`."
    seed_pipeline = None
    if isinstance(composite_payload, dict):
        composite_name = str(composite_payload.get("name", composite_name))
        summary = f"Composite pipeline config `{composite_name}`."
        seed = composite_payload.get("seed")
        if isinstance(seed, dict):
            seed_pipeline = seed.get("pipeline")
    return composite_name, summary, composite_payload, seed_pipeline


def _add_composite_config_surface(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    composite_path: Path,
    *,
    entity_nodes: dict[str, NodeKey],
) -> None:
    payload = _read_yaml(composite_path)
    composite_name, summary, composite_payload, seed_pipeline = (
        _composite_config_identity(
            composite_path,
            payload,
        )
    )
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
    snapshot.add_relation(
        project, "HAS_COMPOSITE", composite_node, provenance="composite_config"
    )
    _link_config_artifact(
        snapshot,
        composite_node,
        path=_rel_path(root, composite_path),
        summary=summary,
        source_kind="composite_config",
        today=today,
        provenance="composite_config",
    )
    _link_composite_config_dependencies(
        snapshot,
        composite_node,
        composite_payload,
        seed_pipeline=seed_pipeline,
        entity_nodes=entity_nodes,
    )


def _link_composite_config_dependencies(
    snapshot: GraphSnapshot,
    composite_node: NodeKey,
    composite_payload: object,
    *,
    seed_pipeline: str | None,
    entity_nodes: dict[str, NodeKey],
) -> None:
    _link_composite_seed_dependency(
        snapshot, composite_node, seed_pipeline=seed_pipeline, entity_nodes=entity_nodes
    )
    for dependency in _composite_config_dependency_entries(composite_payload):
        _link_composite_dependency(snapshot, composite_node, dependency, entity_nodes)


def _composite_config_dependency_entries(
    composite_payload: object,
) -> tuple[object, ...]:
    dependencies = (
        composite_payload.get("dependencies")
        if isinstance(composite_payload, dict)
        else None
    )
    if not isinstance(dependencies, list):
        return ()
    return tuple(dependencies)


def _link_composite_seed_dependency(
    snapshot: GraphSnapshot,
    composite_node: NodeKey,
    *,
    seed_pipeline: str | None,
    entity_nodes: dict[str, NodeKey],
) -> None:
    target = _composite_dependency_target(seed_pipeline, entity_nodes)
    if target is not None:
        snapshot.add_relation(
            composite_node, "DEPENDS_ON", target, provenance="composite_seed"
        )


def _link_composite_dependency(
    snapshot: GraphSnapshot,
    composite_node: NodeKey,
    dependency: object,
    entity_nodes: dict[str, NodeKey],
) -> None:
    if not isinstance(dependency, dict):
        return
    target = _composite_dependency_target(dependency.get("pipeline"), entity_nodes)
    if target is not None:
        snapshot.add_relation(
            composite_node,
            "DEPENDS_ON",
            target,
            provenance="composite_dependency",
            required=bool(dependency.get("required", False)),
        )


def _composite_dependency_target(
    dependency_pipeline: object,
    entity_nodes: dict[str, NodeKey],
) -> NodeKey | None:
    if isinstance(dependency_pipeline, str) and dependency_pipeline in entity_nodes:
        return entity_nodes[dependency_pipeline]
    return None


def _link_config_artifact(
    snapshot: GraphSnapshot,
    target: NodeKey,
    *,
    path: str,
    summary: str,
    source_kind: str,
    today: str,
    provenance: str,
) -> None:
    artifact = snapshot.add_node(
        "config_artifact",
        path,
        summary=summary,
        source_path=path,
        source_kind=source_kind,
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(target, "DEFINED_BY", artifact, provenance=provenance)


def _add_dashboard_graph(
    snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str
) -> None:
    dashboards_root = root / "grafana" / "dashboards"
    source_surface = NodeKey("doc_source_surface", DOC_GRAFANA_DASHBOARDS_JSON)
    snapshot.add_relation(
        project, "HAS_DOC_SOURCE_SURFACE", source_surface, provenance="dashboard_graph"
    )
    for dashboard_path in sorted(dashboards_root.glob("*.json")):
        dashboard = _add_dashboard_surface(snapshot, root, dashboard_path, today)
        snapshot.add_relation(
            project, "HAS_DASHBOARD", dashboard, provenance="dashboard_graph"
        )
        snapshot.add_relation(
            source_surface,
            "IS_FACTUAL_SOURCE_FOR",
            dashboard,
            provenance="dashboard_graph",
        )


def _add_dashboard_surface(
    snapshot: GraphSnapshot,
    root: Path,
    dashboard_path: Path,
    today: str,
) -> NodeKey:
    name = dashboard_path.stem
    try:
        payload = _read_json(dashboard_path)
    except (OSError, json.JSONDecodeError):
        payload = {}
    title = payload.get("title") if isinstance(payload.get("title"), str) else None
    return snapshot.add_node(
        "dashboard_surface",
        name,
        summary=str(title or f"Grafana dashboard `{name}`."),
        source_path=_rel_path(root, dashboard_path),
        source_kind="dashboard_json",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )


def _add_curated_quality_gates(
    snapshot: GraphSnapshot, project: NodeKey, today: str
) -> None:
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
        snapshot.add_relation(
            project, "HAS_QUALITY_GATE", gate, provenance="curated_quality"
        )


def _developer_workflow_readme(
    snapshot: GraphSnapshot, project: NodeKey, today: str
) -> NodeKey:
    dev_readme = snapshot.add_node(
        "doc_artifact",
        "scripts/engineering/dev/README.md",
        summary="Developer workflow and wrapper entrypoint guide.",
        source_path="scripts/engineering/dev/README.md",
        source_kind="ops_doc",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(
        project, "HAS_DOC_ARTIFACT", dev_readme, provenance="curated_scripts"
    )
    return dev_readme


def _add_execution_path_node(
    snapshot: GraphSnapshot,
    today: str,
    execution_payload: dict[str, object],
) -> NodeKey:
    return snapshot.add_node(
        "execution_path",
        str(execution_payload["name"]),
        summary=str(execution_payload["summary"]),
        platform=str(execution_payload["platform"]),
        source_kind="execution_path",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )


def _link_execution_gate(
    snapshot: GraphSnapshot,
    execution: NodeKey,
    execution_payload: dict[str, object],
    *,
    provenance: str,
) -> None:
    gate_name = execution_payload.get("gate")
    if isinstance(gate_name, str):
        snapshot.add_relation(
            execution,
            "EXECUTES_GATE",
            NodeKey("quality_gate", gate_name),
            provenance=provenance,
        )


def _add_curated_execution_paths(
    snapshot: GraphSnapshot, today: str, dev_readme: NodeKey
) -> None:
    for execution_payload in CURATED_EXECUTION_PATHS:
        execution = _add_execution_path_node(snapshot, today, execution_payload)
        _link_execution_gate(
            snapshot, execution, execution_payload, provenance="curated_execution"
        )
        _link_curated_execution_script(
            snapshot, execution, execution_payload, today=today, dev_readme=dev_readme
        )


def _link_curated_execution_script(
    snapshot: GraphSnapshot,
    execution: NodeKey,
    execution_payload: dict[str, object],
    *,
    today: str,
    dev_readme: NodeKey,
) -> None:
    script_path = execution_payload.get("script_path")
    if not isinstance(script_path, str):
        return
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
    if script_path.startswith("scripts/engineering/dev/"):
        snapshot.add_relation(
            dev_readme, "DESCRIBES", execution, provenance="scripts_dev_readme"
        )


def _add_curated_script_clusters(
    snapshot: GraphSnapshot, project: NodeKey, today: str
) -> None:
    for cluster in CURATED_SCRIPT_CLUSTERS:
        readme = _add_curated_cluster_readme(snapshot, cluster, today)
        snapshot.add_relation(
            project, "HAS_DOC_ARTIFACT", readme, provenance="curated_scripts"
        )
        entrypoint = _add_curated_cluster_entrypoint(snapshot, cluster, today)

        for execution_payload in _as_iterable(cluster.get("execution_paths")):
            if not isinstance(execution_payload, dict):
                continue
            _add_curated_cluster_execution(
                snapshot,
                today,
                entrypoint,
                readme,
                execution_payload,
            )


def _add_curated_cluster_readme(
    snapshot: GraphSnapshot,
    cluster: dict[str, object],
    today: str,
) -> NodeKey:
    readme_path = str(cluster["readme_path"])
    return snapshot.add_node(
        "doc_artifact",
        readme_path,
        summary=str(cluster["readme_summary"]),
        source_path=readme_path,
        source_kind="ops_doc",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )


def _add_curated_cluster_entrypoint(
    snapshot: GraphSnapshot,
    cluster: dict[str, object],
    today: str,
) -> NodeKey:
    entrypoint_path = str(cluster["entrypoint_path"])
    return snapshot.add_node(
        "script_surface",
        entrypoint_path,
        summary=str(cluster["entrypoint_summary"]),
        source_path=entrypoint_path,
        source_kind="script_surface",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )


def _add_curated_cluster_execution(
    snapshot: GraphSnapshot,
    today: str,
    entrypoint: NodeKey,
    readme: NodeKey,
    execution_payload: dict[str, object],
) -> None:
    execution = _add_execution_path_node(snapshot, today, execution_payload)
    snapshot.add_relation(
        entrypoint, "PROVIDES", execution, provenance="curated_script_clusters"
    )
    snapshot.add_relation(
        readme, "DESCRIBES", execution, provenance="curated_script_clusters"
    )
    _link_execution_gate(
        snapshot,
        execution,
        execution_payload,
        provenance="curated_script_clusters",
    )


def _add_quality_and_scripts(
    snapshot: GraphSnapshot, _root: Path, project: NodeKey, today: str
) -> None:
    _add_curated_quality_gates(snapshot, project, today)
    dev_readme = _developer_workflow_readme(snapshot, project, today)
    _add_curated_execution_paths(snapshot, today, dev_readme)
    _add_curated_script_clusters(snapshot, project, today)


def _add_cli_command_graph(
    snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str
) -> None:
    execution_to_gates, execution_to_scripts = _cli_execution_indexes(snapshot)
    for execution in tuple(snapshot.nodes.values()):
        if execution.key.label != "execution_path":
            continue
        command_name = _normalize_cli_command_name(execution.key.name)
        if command_name is None:
            continue
        backing_scripts = execution_to_scripts.get(execution.key, [])
        source_path = _cli_command_source_path(root, command_name, backing_scripts)
        command_options = _extract_cli_options(execution.key.name)
        command = _add_cli_command_surface(
            snapshot,
            execution,
            command_name=command_name,
            source_path=source_path,
            command_options=command_options,
            today=today,
        )
        snapshot.add_relation(
            project, "HAS_CLI_COMMAND", command, provenance="cli_command_graph"
        )
        _link_cli_command_execution(
            snapshot,
            command,
            execution.key,
            execution_to_gates.get(execution.key, []),
            backing_scripts,
        )
        _add_cli_option_surfaces(
            snapshot,
            command,
            command_name=command_name,
            source_path=source_path,
            command_options=command_options,
            today=today,
        )
        _link_cli_command_side_effects(snapshot, command, command_name)


def _add_cli_command_surface(
    snapshot: GraphSnapshot,
    execution: GraphNode,
    *,
    command_name: str,
    source_path: str | None,
    command_options: tuple[str, ...],
    today: str,
) -> NodeKey:
    return snapshot.add_node(
        "cli_command_surface",
        command_name,
        summary=f"CLI command surface `{command_name}`.",
        source_path=source_path,
        source_kind="cli_command_surface",
        platform=str(execution.properties.get("platform") or ""),
        side_effect_class=_cli_side_effect_class(command_name),
        command_options=list(command_options) if command_options else None,
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )


def _link_cli_command_execution(
    snapshot: GraphSnapshot,
    command: NodeKey,
    execution_key: NodeKey,
    gates: list[NodeKey],
    scripts: list[NodeKey],
) -> None:
    snapshot.add_relation(
        command, "RUNS_VIA", execution_key, provenance="cli_command_graph"
    )
    for gate in gates:
        snapshot.add_relation(
            command, "EXECUTES_GATE", gate, provenance="cli_command_graph"
        )
    for script in scripts:
        snapshot.add_relation(
            command, "DEPENDS_ON", script, provenance="cli_command_graph"
        )


def _cli_execution_indexes(
    snapshot: GraphSnapshot,
) -> tuple[dict[NodeKey, list[NodeKey]], dict[NodeKey, list[NodeKey]]]:
    execution_to_gates: dict[NodeKey, list[NodeKey]] = {}
    execution_to_scripts: dict[NodeKey, list[NodeKey]] = {}
    for relation in snapshot.relations.values():
        if (
            relation.source.label == "execution_path"
            and relation.relation_type == "EXECUTES_GATE"
        ):
            execution_to_gates.setdefault(relation.source, []).append(relation.target)
        if (
            relation.target.label == "execution_path"
            and relation.relation_type == "PROVIDES"
        ):
            execution_to_scripts.setdefault(relation.target, []).append(relation.source)
    return execution_to_gates, execution_to_scripts


def _cli_command_source_path(
    root: Path,
    command_name: str,
    backing_scripts: list[NodeKey],
) -> str | None:
    if backing_scripts:
        return backing_scripts[0].name
    if command_name.startswith("bioetl "):
        command_suffix = command_name.split(" ", 1)[1]
        source_candidate = (
            root
            / "src/bioetl/interfaces/cli/commands"
            / f"{command_suffix.replace('-', '_')}.py"
        )
        if source_candidate.is_file():
            return _rel_path(root, source_candidate)
    return None


def _add_cli_option_surfaces(
    snapshot: GraphSnapshot,
    command: NodeKey,
    *,
    command_name: str,
    source_path: str | None,
    command_options: tuple[str, ...],
    today: str,
) -> None:
    for option_name in command_options:
        option = snapshot.add_node(
            "cli_option_surface",
            f"{command_name} {option_name}",
            summary=f"Observed CLI option `{option_name}` for command `{command_name}`.",
            source_path=source_path,
            source_kind="cli_option_surface",
            command=command_name,
            option_name=option_name,
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="medium",
        )
        snapshot.add_relation(
            command, "ACCEPTS_OPTION", option, provenance="cli_command_graph"
        )


def _link_cli_command_side_effects(
    snapshot: GraphSnapshot,
    command: NodeKey,
    command_name: str,
) -> None:
    if command_name == "bioetl run":
        for target in sorted(
            (key for key in snapshot.nodes if key.label == "pipeline_surface"),
            key=lambda key: key.name,
        )[:5]:
            snapshot.add_relation(
                command, "SIDE_EFFECTS_ON", target, provenance="cli_command_graph"
            )
        return
    if command_name == "scripts.memory sync":
        gate_key = NodeKey("quality_gate", GATE_NEO4J_ONTOLOGY_INVARIANTS)
        if gate_key in snapshot.nodes:
            snapshot.add_relation(
                command, "SIDE_EFFECTS_ON", gate_key, provenance="cli_command_graph"
            )


def _add_test_graph(
    snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str
) -> None:
    tests_root = root / "tests"
    for suite_dir, suite_name in TEST_SURFACES.items():
        _add_test_suite_surface(
            snapshot, project, today, suite_dir=suite_dir, suite_name=suite_name
        )

    for test_path in sorted(tests_root.rglob("test_*.py")):
        _add_test_artifact_surface(snapshot, root, today, test_path)


def _add_test_suite_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
    *,
    suite_dir: str,
    suite_name: str,
) -> None:
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


def _add_test_artifact_surface(
    snapshot: GraphSnapshot,
    root: Path,
    today: str,
    test_path: Path,
) -> None:
    relative_path = _rel_path(root, test_path)
    parts = Path(relative_path).parts
    suite_name = _test_suite_name(parts)
    if suite_name is None:
        return
    suite_dir = parts[1]
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
    snapshot.add_relation(
        NodeKey("test_surface", suite_name),
        "CONTAINS",
        artifact,
        provenance="test_graph",
    )
    _link_test_artifact_scope(snapshot, artifact, parts)


def _test_suite_name(parts: tuple[str, ...]) -> str | None:
    if len(parts) < 2:
        return None
    suite_dir = parts[1]
    return TEST_SURFACES.get(suite_dir)


def _link_test_artifact_scope(
    snapshot: GraphSnapshot, artifact: NodeKey, parts: tuple[str, ...]
) -> None:
    layer_name = parts[2] if len(parts) > 2 and parts[2] in KNOWN_LAYERS else None
    if layer_name is None:
        return
    snapshot.add_relation(
        artifact,
        "TESTS_LAYER",
        NodeKey("layer_family", layer_name),
        provenance="test_graph",
    )
    if len(parts) <= 4:
        return
    family_key = NodeKey("package_family", f"{layer_name}/{parts[3]}")
    if family_key in snapshot.nodes:
        snapshot.add_relation(
            artifact,
            "TESTS_PACKAGE_FAMILY",
            family_key,
            provenance="test_graph",
        )


def _add_policy_surfaces(
    snapshot: GraphSnapshot, _root: Path, project: NodeKey, today: str
) -> None:
    for policy_payload in _curated_policy_surfaces():
        _add_policy_surface_entry(snapshot, project, today, policy_payload)


def _curated_policy_surfaces() -> tuple[dict[str, object], ...]:
    return tuple(CURATED_POLICY_SURFACES)


def _add_policy_surface_entry(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
    policy_payload: dict[str, object],
) -> None:
    policy_context = _policy_surface_context(snapshot, policy_payload, today)
    policy = policy_context.policy
    snapshot.add_relation(
        project, "HAS_POLICY_SURFACE", policy, provenance="curated_policy"
    )
    snapshot.add_relation(
        policy, "BACKED_BY", policy_context.artifact, provenance="curated_policy"
    )
    _link_policy_governance_targets(snapshot, policy, policy_payload)


@dataclass(frozen=True)
class PolicySurfaceContext:
    policy: NodeKey
    artifact: NodeKey


def _policy_surface_context(
    snapshot: GraphSnapshot,
    policy_payload: dict[str, object],
    today: str,
) -> PolicySurfaceContext:
    return PolicySurfaceContext(
        policy=_add_policy_surface(snapshot, policy_payload, today),
        artifact=_add_policy_artifact(snapshot, policy_payload, today),
    )


def _add_policy_surface(
    snapshot: GraphSnapshot,
    policy_payload: dict[str, object],
    today: str,
) -> NodeKey:
    return snapshot.add_node(
        "policy_surface",
        str(policy_payload["name"]),
        summary=str(policy_payload["summary"]),
        source_path=str(policy_payload["source_path"]),
        source_kind="repo_policy_surface",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )


def _add_policy_artifact(
    snapshot: GraphSnapshot,
    policy_payload: dict[str, object],
    today: str,
) -> NodeKey:
    source_path = str(policy_payload["source_path"])
    return snapshot.add_node(
        str(policy_payload["artifact_label"]),
        source_path,
        summary=str(policy_payload["summary"]),
        source_path=source_path,
        source_kind="policy_artifact",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )


def _link_policy_governance_targets(
    snapshot: GraphSnapshot,
    policy: NodeKey,
    policy_payload: dict[str, object],
) -> None:
    for target in _policy_governance_targets(policy_payload):
        snapshot.add_relation(policy, "GOVERNS", target, provenance="curated_policy")


def _policy_governance_targets(
    policy_payload: dict[str, object],
) -> tuple[NodeKey, ...]:
    targets: list[NodeKey] = []
    targets.extend(
        NodeKey("layer_family", str(name))
        for name in _as_iterable(policy_payload.get("governs_layers"))
    )
    targets.extend(
        NodeKey("quality_gate", str(name))
        for name in _as_iterable(policy_payload.get("governs_quality_gates"))
    )
    targets.extend(
        NodeKey("test_surface", str(name))
        for name in _as_iterable(policy_payload.get("governs_test_surfaces"))
    )
    targets.extend(
        NodeKey("doc_source_surface", str(name))
        for name in _as_iterable(policy_payload.get("governs_docs"))
    )
    return tuple(targets)


def _add_impact_analysis_surfaces(
    snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str
) -> None:
    memory_mapping = _load_memory_mapping(root)
    port_nodes, adapter_nodes, contract_nodes, pipeline_nodes = (
        _impact_analysis_context(
            snapshot,
            root,
            project,
            today,
            memory_mapping,
        )
    )
    _run_impact_analysis_passes(
        snapshot,
        root,
        project,
        today,
        memory_mapping=memory_mapping,
        port_nodes=port_nodes,
        adapter_nodes=adapter_nodes,
        contract_nodes=contract_nodes,
        pipeline_nodes=pipeline_nodes,
    )


def _run_impact_analysis_passes(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    *,
    memory_mapping: dict[str, object],
    port_nodes: set[NodeKey],
    adapter_nodes: dict[str, NodeKey],
    contract_nodes: dict[str, NodeKey],
    pipeline_nodes: dict[str, NodeKey],
) -> None:
    _add_pipeline_normalization_edges(snapshot, pipeline_nodes, memory_mapping)
    _add_pipeline_normalization_evidence(snapshot, pipeline_nodes)
    _add_pipeline_test_edges(snapshot, root, pipeline_nodes, memory_mapping)
    _add_alert_surfaces(
        snapshot, root, project, today, pipeline_nodes, contract_nodes, memory_mapping
    )
    _add_governance_edges(
        snapshot, port_nodes, adapter_nodes, pipeline_nodes, contract_nodes
    )
    _add_pipeline_operational_edges(snapshot, pipeline_nodes, memory_mapping)
    _extract_code_duplication_surfaces(snapshot, root, project, today, memory_mapping)


def _impact_analysis_context(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    memory_mapping: dict[str, object],
) -> tuple[set[NodeKey], dict[str, NodeKey], dict[str, NodeKey], dict[str, NodeKey]]:
    port_nodes = _add_port_surfaces(snapshot, root, project, today)
    adapter_nodes = _add_adapter_surfaces(
        snapshot, root, project, today, port_nodes, memory_mapping
    )
    contract_nodes = _add_contract_surfaces(
        snapshot, root, project, today, memory_mapping
    )
    pipeline_nodes = _add_pipeline_surfaces(
        snapshot, root, project, today, contract_nodes, adapter_nodes
    )
    return port_nodes, adapter_nodes, contract_nodes, pipeline_nodes


def _is_doc_artifact_file(relative_file: str, file_extension: str) -> bool:
    return file_extension in {".md", ".yml", YAML_SUFFIX} and (
        relative_file in {"README.md", "mkdocs.yml"}
        or relative_file.startswith("docs/")
        or relative_file.startswith(GITHUB_PATH_PREFIX)
    )


def _repo_zone_for_path(
    source_path_value: str, zone_roots: dict[str, tuple[str, ...]]
) -> str | None:
    return next(
        (
            zone_name
            for zone_name, relative_roots in zone_roots.items()
            if any(
                source_path_value == zone_root
                or source_path_value.startswith(f"{zone_root}/")
                for zone_root in relative_roots
            )
        ),
        None,
    )


def _add_repo_zone_file_structure(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    zone_name: str,
    relative_roots: tuple[str, ...],
    config: dict[str, object],
) -> None:
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
        _walk_repo_zone_root(
            snapshot,
            root,
            project,
            zone,
            today,
            zone_name=zone_name,
            relative_root=relative_root,
            config=config,
        )


def _walk_repo_zone_root(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    zone: NodeKey,
    today: str,
    *,
    zone_name: str,
    relative_root: str,
    config: dict[str, object],
) -> None:
    zone_root = root / relative_root
    if not zone_root.is_dir():
        return
    _walk_repo_zone_file_structure(
        snapshot,
        root,
        project,
        zone,
        today,
        zone_name=zone_name,
        relative_root=relative_root,
        zone_root=zone_root,
        config=config,
    )


def _walk_repo_zone_file_structure(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    zone: NodeKey,
    today: str,
    *,
    zone_name: str,
    relative_root: str,
    zone_root: Path,
    config: dict[str, object],
) -> None:
    for current_dir, dirnames, filenames in os.walk(zone_root):
        current_path = Path(current_dir)
        relative_dir = _rel_path(root, current_path)
        if _is_excluded_file_structure_path(relative_dir, config):
            dirnames[:] = []
            filenames[:] = []
            continue
        dirnames[:] = _included_file_structure_dirs(
            root, current_path, dirnames, config
        )
        directory = _add_repo_zone_directory_surface(
            snapshot,
            root,
            zone,
            today,
            zone_name=zone_name,
            relative_root=relative_root,
            current_path=current_path,
            relative_dir=relative_dir,
        )
        _add_repo_zone_directory_files(
            snapshot,
            root,
            project,
            directory,
            current_path,
            filenames,
            today,
            zone_name=zone_name,
            config=config,
        )


def _included_file_structure_dirs(
    root: Path,
    current_path: Path,
    dirnames: list[str],
    config: dict[str, object],
) -> list[str]:
    return sorted(
        name
        for name in dirnames
        if not _is_excluded_file_structure_path(
            _rel_path(root, current_path / name), config
        )
    )


def _add_repo_zone_directory_surface(
    snapshot: GraphSnapshot,
    root: Path,
    zone: NodeKey,
    today: str,
    *,
    zone_name: str,
    relative_root: str,
    current_path: Path,
    relative_dir: str,
) -> NodeKey:
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
        snapshot.add_relation(
            parent_key, "CONTAINS", directory, provenance="file_structure"
        )
    return directory


def _add_repo_zone_directory_files(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    directory: NodeKey,
    current_path: Path,
    filenames: list[str],
    today: str,
    *,
    zone_name: str,
    config: dict[str, object],
) -> None:
    for filename in sorted(filenames):
        _add_repo_zone_directory_file(
            snapshot,
            root,
            project,
            directory,
            current_path,
            filename,
            today,
            zone_name=zone_name,
            config=config,
        )


def _add_repo_zone_directory_file(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    directory: NodeKey,
    current_path: Path,
    filename: str,
    today: str,
    *,
    zone_name: str,
    config: dict[str, object],
) -> None:
    file_path = current_path / filename
    relative_file = _rel_path(root, file_path)
    if _is_excluded_file_structure_path(relative_file, config):
        return
    file_surface = _add_repo_zone_file_surface(
        snapshot,
        directory,
        relative_file,
        today,
        zone_name=zone_name,
        filename=filename,
    )
    _add_repo_zone_doc_artifact(
        snapshot,
        project,
        file_surface,
        relative_file,
        today,
        zone_name=zone_name,
    )


def _add_repo_zone_file_surface(
    snapshot: GraphSnapshot,
    directory: NodeKey,
    relative_file: str,
    today: str,
    *,
    zone_name: str,
    filename: str,
) -> NodeKey:
    file_surface = snapshot.add_node(
        "file_surface",
        relative_file,
        summary=f"Repository file `{relative_file}`.",
        source_path=relative_file,
        source_kind="file_structure_file",
        repo_zone=zone_name,
        file_extension=Path(filename).suffix[1:] if Path(filename).suffix else None,
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(
        directory, "CONTAINS", file_surface, provenance="file_structure"
    )
    return file_surface


def _add_repo_zone_doc_artifact(
    snapshot: GraphSnapshot,
    project: NodeKey,
    file_surface: NodeKey,
    relative_file: str,
    today: str,
    *,
    zone_name: str,
) -> None:
    file_extension = Path(relative_file).suffix.lower()
    if not _is_doc_artifact_file(relative_file, file_extension):
        return
    doc_artifact = snapshot.add_node(
        "doc_artifact",
        relative_file,
        summary=f"Documentation artifact `{relative_file}`.",
        source_path=relative_file,
        source_kind="doc_artifact",
        repo_zone=zone_name,
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="medium",
    )
    snapshot.add_relation(
        project, "HAS_DOC_ARTIFACT", doc_artifact, provenance="file_structure"
    )
    snapshot.add_relation(
        doc_artifact, "BACKED_BY", file_surface, provenance="file_structure"
    )


def _link_source_backed_file_structure(
    snapshot: GraphSnapshot,
    root: Path,
    today: str,
    zone_roots: dict[str, tuple[str, ...]],
    config: dict[str, object],
) -> None:
    source_backed_labels = _source_backed_file_structure_labels()
    path_kind_cache: dict[str, str | None] = {}
    for node in tuple(snapshot.nodes.values()):
        _link_source_backed_node_structure(
            snapshot,
            root,
            node,
            source_backed_labels=source_backed_labels,
            path_kind_cache=path_kind_cache,
            today=today,
            zone_roots=zone_roots,
            config=config,
        )


def _link_source_backed_node_structure(
    snapshot: GraphSnapshot,
    root: Path,
    node: GraphNode,
    *,
    source_backed_labels: set[str],
    path_kind_cache: dict[str, str | None],
    today: str,
    zone_roots: dict[str, tuple[str, ...]],
    config: dict[str, object],
) -> None:
    if node.key.label not in source_backed_labels:
        return
    source_path_value = node.properties.get("source_path")
    if not isinstance(source_path_value, str) or not source_path_value:
        return
    if _is_excluded_file_structure_path(source_path_value, config):
        return

    path_kind = _source_backed_path_kind(snapshot, source_path_value, path_kind_cache)
    if path_kind == "directory":
        _link_source_backed_directory_structure(
            snapshot,
            node.key,
            source_path_value=source_path_value,
            config=config,
        )
        return
    if path_kind != "file":
        return
    _link_source_backed_file_node(
        snapshot,
        root,
        node.key,
        root / source_path_value,
        source_path_value=source_path_value,
        today=today,
        zone_roots=zone_roots,
        config=config,
    )


def _source_backed_path_kind(
    snapshot: GraphSnapshot,
    source_path_value: str,
    path_kind_cache: dict[str, str | None],
) -> str | None:
    if source_path_value in path_kind_cache:
        return path_kind_cache[source_path_value]

    if NodeKey("directory_surface", source_path_value) in snapshot.nodes:
        path_kind_cache[source_path_value] = "directory"
    elif NodeKey("file_surface", source_path_value) in snapshot.nodes:
        path_kind_cache[source_path_value] = "file"
    else:
        path_kind_cache[source_path_value] = None
    return path_kind_cache[source_path_value]


def _source_backed_file_structure_labels() -> set[str]:
    return {
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
        "runtime_evidence_surface",
        "workflow_surface",
        "workflow_job_surface",
    }


def _link_source_backed_directory_structure(
    snapshot: GraphSnapshot,
    node_key: NodeKey,
    *,
    source_path_value: str,
    config: dict[str, object],
) -> None:
    directory_key = NodeKey("directory_surface", source_path_value)
    if directory_key in snapshot.nodes:
        snapshot.add_relation(
            directory_key, "HOUSES", node_key, provenance="file_structure"
        )
    for promoted_hub in _promoted_directory_hubs(source_path_value, config):
        hub_key = NodeKey("directory_surface", promoted_hub)
        if hub_key in snapshot.nodes:
            snapshot.add_relation(
                hub_key, "HOUSES", node_key, provenance="file_structure"
            )


def _link_source_backed_file_node(
    snapshot: GraphSnapshot,
    root: Path,
    node_key: NodeKey,
    source_path: Path,
    *,
    source_path_value: str,
    today: str,
    zone_roots: dict[str, tuple[str, ...]],
    config: dict[str, object],
) -> None:
    parent_relative = _rel_path(root, source_path.parent)
    file_surface = snapshot.add_node(
        "file_surface",
        source_path_value,
        summary=f"Primary repository file `{source_path_value}`.",
        source_path=source_path_value,
        source_kind="file_structure_file",
        repo_zone=_repo_zone_for_path(source_path_value, zone_roots),
        suffix=source_path.suffix,
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    directory_key = NodeKey("directory_surface", parent_relative)
    if directory_key in snapshot.nodes:
        snapshot.add_relation(
            directory_key, "CONTAINS", file_surface, provenance="file_structure"
        )
        snapshot.add_relation(
            directory_key, "HOUSES", node_key, provenance="file_structure"
        )
    for promoted_hub in _promoted_directory_hubs(parent_relative, config):
        hub_key = NodeKey("directory_surface", promoted_hub)
        if hub_key in snapshot.nodes:
            snapshot.add_relation(
                hub_key, "HOUSES", node_key, provenance="file_structure"
            )
    for supplemental_hub in _supplemental_directory_hubs_for_node(
        node_key, source_path_value
    ):
        hub_key = NodeKey("directory_surface", supplemental_hub)
        snapshot.add_relation(
            hub_key, "CONTAINS", file_surface, provenance="file_structure_promoted"
        )
        snapshot.add_relation(
            hub_key, "HOUSES", node_key, provenance="file_structure_promoted"
        )
    snapshot.add_relation(file_surface, "BACKS", node_key, provenance="file_structure")


def _link_relation_backed_file_structure(
    snapshot: GraphSnapshot,
    root: Path,
    config: dict[str, object],
) -> None:
    relation_backed_types = _relation_backed_file_structure_types()
    file_backed_labels = _relation_backed_file_structure_labels()
    for relation in tuple(snapshot.relations.values()):
        _link_relation_backed_structure_for_relation(
            snapshot,
            root,
            relation,
            relation_backed_types=relation_backed_types,
            file_backed_labels=file_backed_labels,
            config=config,
        )


def _link_relation_backed_structure_for_relation(
    snapshot: GraphSnapshot,
    root: Path,
    relation: GraphRelation,
    *,
    relation_backed_types: set[str],
    file_backed_labels: set[str],
    config: dict[str, object],
) -> None:
    if (
        relation.relation_type not in relation_backed_types
        or relation.target.label not in file_backed_labels
    ):
        return
    target_node = snapshot.nodes.get(relation.target)
    if target_node is None:
        return
    source_path_value = target_node.properties.get("source_path")
    if not isinstance(source_path_value, str) or not source_path_value:
        return
    if _is_excluded_file_structure_path(source_path_value, config):
        return

    parent_relative = _relation_backed_parent_relative(root, source_path_value)
    if parent_relative is None:
        return
    _link_relation_backed_directory_housing(
        snapshot,
        relation.source,
        parent_relative=parent_relative,
        config=config,
    )


def _relation_backed_file_structure_types() -> set[str]:
    return {"BACKED_BY", "DESCRIBED_IN", "DEFINED_BY"}


def _relation_backed_file_structure_labels() -> set[str]:
    return {
        "doc_artifact",
        "config_artifact",
        "module_surface",
        "script_surface",
        "test_artifact",
    }


def _relation_backed_parent_relative(root: Path, source_path_value: str) -> str | None:
    normalized_path = _normalize_repo_relative_path(source_path_value)
    if not normalized_path:
        return None
    target_path = root / normalized_path
    if target_path.is_dir():
        return normalized_path
    # Relation-backed labels here are file-oriented. Prefer the lexical parent
    # after the directory check to avoid expensive repeated file stats during
    # snapshot assembly on large or partially materialized trees.
    return str(Path(normalized_path).parent)


def _link_relation_backed_directory_housing(
    snapshot: GraphSnapshot,
    source: NodeKey,
    *,
    parent_relative: str,
    config: dict[str, object],
) -> None:
    directory_key = NodeKey("directory_surface", parent_relative)
    if directory_key in snapshot.nodes:
        snapshot.add_relation(
            directory_key, "HOUSES", source, provenance="file_structure_inferred"
        )
    for promoted_hub in _promoted_directory_hubs(parent_relative, config):
        hub_key = NodeKey("directory_surface", promoted_hub)
        if hub_key in snapshot.nodes:
            snapshot.add_relation(
                hub_key, "HOUSES", source, provenance="file_structure_inferred"
            )


def _add_file_structure_surfaces(
    snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str
) -> None:
    memory_mapping = _load_memory_mapping(root)
    config = _file_structure_config(memory_mapping)
    zone_roots = _file_structure_zone_roots(config)
    _materialize_file_structure(snapshot, root, project, today, zone_roots, config)


def _materialize_file_structure(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    zone_roots: dict[str, tuple[str, ...]],
    config: dict[str, object],
) -> None:
    _add_file_structure_zones(snapshot, root, project, today, zone_roots, config)
    _link_source_backed_file_structure(snapshot, root, today, zone_roots, config)
    _link_relation_backed_file_structure(snapshot, root, config)


def _file_structure_zone_roots(config: dict[str, object]) -> dict[str, tuple[str, ...]]:
    raw_zones = config.get("repo_zones")
    if not isinstance(raw_zones, dict):
        return {}
    return {
        str(name): tuple(_as_string_list(paths))
        for name, paths in raw_zones.items()
    }


def _add_file_structure_zones(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    zone_roots: dict[str, tuple[str, ...]],
    config: dict[str, object],
) -> None:
    for zone_name, relative_roots in zone_roots.items():
        _add_file_structure_zone(
            snapshot,
            root,
            project,
            today,
            zone_name,
            relative_roots,
            config,
        )


def _add_file_structure_zone(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    zone_name: str,
    relative_roots: tuple[str, ...],
    config: dict[str, object],
) -> None:
    _add_repo_zone_file_structure(
        snapshot,
        root,
        project,
        today,
        zone_name,
        relative_roots,
        config,
    )


def _merge_storage_layer_config(
    base_sink: dict[str, object],
    pipeline_sink: dict[str, object],
    layer_name: str,
) -> dict[str, object]:
    merged: dict[str, object] = {}
    base_layer = base_sink.get(layer_name)
    if isinstance(base_layer, dict):
        merged.update(base_layer)
    override_layer = pipeline_sink.get(layer_name)
    if isinstance(override_layer, dict):
        merged.update(override_layer)
    return merged


def _merge_sink_config(
    base_sink: dict[str, object],
    override_sink: dict[str, object],
) -> dict[str, object]:
    merged: dict[str, object] = dict(base_sink)
    for raw_layer_name, override_layer in override_sink.items():
        layer_name = str(raw_layer_name)
        base_layer = merged.get(layer_name)
        if isinstance(base_layer, dict) and isinstance(override_layer, dict):
            layer_config = dict(base_layer)
            layer_config.update(override_layer)
            merged[layer_name] = layer_config
        else:
            merged[layer_name] = override_layer
    return merged


def _entity_pipeline_sink_config(payload: dict[str, object]) -> dict[str, object]:
    direct_sink = _as_mapping(payload.get("sink"))
    pipeline_payload = _as_mapping(payload.get("pipeline"))
    nested_sink = _as_mapping(pipeline_payload.get("sink"))
    return _merge_sink_config(direct_sink, nested_sink)


def _storage_ref_from_output_path(raw_path: str) -> str:
    normalized = raw_path.strip().strip("/")
    if normalized.startswith("data/output/"):
        normalized = normalized.removeprefix("data/output/")
    return normalized


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalized_text_list(value: object) -> list[str] | None:
    if not isinstance(value, list | tuple):
        return None
    normalized = [str(item).strip() for item in value if str(item).strip()]
    return normalized


def _storage_ref_identity(ref: str) -> tuple[str | None, str | None, str | None]:
    parts = [part for part in ref.split("/") if part]
    if len(parts) < 3:
        return (parts[0] if parts else None, None, None)
    return parts[0], parts[1], "/".join(parts[2:])


def _infer_storage_format(ref: str) -> str | None:
    suffix = Path(ref).suffix.casefold()
    if suffix == ".json":
        return "json"
    if suffix == ".jsonl":
        return "jsonl"
    if suffix == ".txt":
        return "txt"
    return None


def _storage_schema_properties(
    payload: dict[str, object],
    *,
    layer_name: str,
) -> dict[str, JsonValue]:
    schema_payload = _as_mapping(payload.get("schema"))
    layer_schema = _as_mapping(schema_payload.get(layer_name))
    column_groups = _as_iterable(schema_payload.get("column_groups"))
    schema_column_groups = [
        name
        for item in column_groups
        if isinstance(item, dict)
        for name in [_optional_text(item.get("name"))]
        if name is not None
    ]
    return {
        "schema_present": bool(layer_schema),
        "schema_column_groups": schema_column_groups if schema_column_groups else None,
        "schema_include_groups": _normalized_text_list(
            layer_schema.get("include_groups")
        ),
        "schema_exclude_fields": _normalized_text_list(
            layer_schema.get("exclude_fields")
        ),
        "schema_alias_policy": _optional_text(layer_schema.get("alias_policy")),
    }


def _schema_group_field_map(payload: dict[str, object]) -> dict[str, list[str]]:
    schema_payload = _as_mapping(payload.get("schema"))
    column_groups = schema_payload.get("column_groups")
    group_map: dict[str, list[str]] = {}
    if not isinstance(column_groups, list):
        return group_map
    for item in column_groups:
        if not isinstance(item, dict):
            continue
        group_name = _optional_text(item.get("name"))
        if group_name is None:
            continue
        fields = _normalized_text_list(item.get("fields")) or []
        if fields:
            group_map[group_name] = fields
    return group_map


def _filtered_group_fields(
    payload: dict[str, object],
    *,
    layer_name: str,
) -> list[tuple[str, str]]:
    schema_payload = _as_mapping(payload.get("schema"))
    layer_schema = _as_mapping(schema_payload.get(layer_name))
    include_groups = _normalized_text_list(layer_schema.get("include_groups")) or []
    exclude_patterns = _normalized_text_list(layer_schema.get("exclude_fields")) or []
    group_map = _schema_group_field_map(payload)
    results: list[tuple[str, str]] = []
    for group_name in include_groups:
        for field_name in group_map.get(group_name, []):
            if any(
                fnmatch.fnmatch(field_name, pattern) for pattern in exclude_patterns
            ):
                continue
            results.append((group_name, field_name))
    return results


def _field_quality_index(payload: dict[str, object]) -> dict[str, dict[str, JsonValue]]:
    quality_payload = _as_mapping(payload.get("quality"))
    index: dict[str, dict[str, JsonValue]] = {}
    field_validations = quality_payload.get("entity_field_validations")
    if isinstance(field_validations, list):
        for item in field_validations:
            _merge_field_validation_item(index, item)
    key_nullability = quality_payload.get("key_nullability")
    if isinstance(key_nullability, list):
        for item in key_nullability:
            _merge_key_nullability_item(index, item)
    return index


def _merge_field_validation_item(
    index: dict[str, dict[str, JsonValue]],
    item: object,
) -> None:
    if not isinstance(item, dict):
        return
    field_name = _optional_text(item.get("field"))
    if field_name is None:
        return
    entry = index.setdefault(field_name, {})
    validation_types = set(_normalized_text_list(entry.get("validation_types")) or [])
    validation_type = _optional_text(item.get("type"))
    if validation_type is not None:
        validation_types.add(validation_type)
    entry["validation_types"] = sorted(validation_types) if validation_types else None
    if validation_type == "required" and item.get("nullable") is False:
        entry["required_in_quality"] = True


def _merge_key_nullability_item(
    index: dict[str, dict[str, JsonValue]],
    item: object,
) -> None:
    if not isinstance(item, dict):
        return
    field_name = _optional_text(item.get("field"))
    if field_name is None:
        return
    if item.get("nullable") is False:
        entry = index.setdefault(field_name, {})
        entry["required_in_quality"] = True


def _add_schema_field_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    storage_key: NodeKey,
    *,
    field_name: str,
    field_group: str,
    today: str,
    spec: SchemaFieldSpec = SchemaFieldSpec(),
) -> NodeKey:
    storage_node = snapshot.nodes.get(storage_key)
    storage_ref = storage_key.name
    key = NodeKey("schema_field_surface", f"{storage_ref}::{field_name}")
    surface = snapshot.add_node(
        "schema_field_surface",
        key.name,
        summary=f"Schema field `{field_name}` for storage surface `{storage_ref}`.",
        field_name=field_name,
        field_group=field_group,
        storage_ref=storage_ref,
        storage_layer=(
            storage_node.properties.get("layer") if storage_node is not None else None
        ),
        provider=spec.scope.provider
        or (
            storage_node.properties.get("provider")
            if storage_node is not None
            else None
        ),
        entity=spec.scope.entity
        or (
            storage_node.properties.get("entity") if storage_node is not None else None
        ),
        pipeline_name=spec.scope.pipeline_name
        or (
            storage_node.properties.get("pipeline_name")
            if storage_node is not None
            else None
        ),
        contract_ref=spec.contract_ref,
        required_in_quality=spec.required_in_quality,
        validation_types=spec.validation_types,
        drift_classification=spec.drift_classification,
        source_storage_refs=spec.source_storage_refs,
        source_kind="schema_field_surface",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    if spec.drift_classification is None:
        snapshot.nodes[key].properties.setdefault("drift_classification", None)
    snapshot.add_relation(
        project, "HAS_SCHEMA_FIELD", surface, provenance="schema_fields"
    )
    snapshot.add_relation(
        storage_key, "HAS_SCHEMA_FIELD", surface, provenance="schema_fields"
    )
    if spec.contract_ref is not None:
        contract_key = NodeKey("contract_surface", spec.contract_ref)
        if contract_key in snapshot.nodes:
            snapshot.add_relation(
                contract_key, "HAS_SCHEMA_FIELD", surface, provenance="schema_fields"
            )
    return surface


def _merged_maintenance_config(
    base_payload: dict[str, object],
    payload: dict[str, object],
) -> dict[str, object]:
    merged: dict[str, object] = {}
    base_maintenance = base_payload.get("maintenance")
    if isinstance(base_maintenance, dict):
        merged.update(base_maintenance)
    payload_maintenance = payload.get("maintenance")
    if isinstance(payload_maintenance, dict):
        merged.update(payload_maintenance)
    return merged


def _add_storage_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    spec: StorageSurfaceSpec,
) -> NodeKey:
    (
        layer,
        provider,
        entity,
        storage_roles,
        pipeline_names,
        primary_storage_kind,
        primary_pipeline_name,
    ) = _storage_surface_state(snapshot, spec)
    semantic_properties = _storage_surface_semantic_properties(spec)
    format_name = spec.format_name or _infer_storage_format(spec.ref)
    surface = snapshot.add_node(
        "storage_surface",
        spec.ref,
        summary=spec.summary,
        layer=layer,
        storage_kind=primary_storage_kind,
        storage_roles=storage_roles,
        provider=provider,
        entity=entity,
        pipeline_name=primary_pipeline_name,
        pipeline_names=pipeline_names if pipeline_names else None,
        format=format_name,
        mode=spec.mode,
        enabled=spec.enabled,
        retention_days=spec.retention_days,
        config_version=spec.config_version,
        quality_version=spec.quality_version,
        last_verified=spec.today,
        ingest_wave="repo_sync_v1",
        confidence="high",
        **semantic_properties,
    )
    snapshot.add_relation(
        project, "HAS_STORAGE_SURFACE", surface, provenance="storage_surfaces"
    )
    return surface


def _storage_surface_state(
    snapshot: GraphSnapshot,
    spec: StorageSurfaceSpec,
) -> tuple[str, str | None, str | None, list[str], list[str], str, str | None]:
    key = NodeKey("storage_surface", spec.ref)
    existing = snapshot.nodes.get(key)
    inferred_layer, inferred_provider, inferred_entity = _storage_ref_identity(spec.ref)
    provider = spec.scope.provider or inferred_provider
    entity = spec.scope.entity or inferred_entity
    pipeline_name = spec.scope.pipeline_name
    layer = spec.layer or inferred_layer or ""

    existing_roles_raw = (
        existing.properties.get("storage_roles") if existing is not None else None
    )
    existing_roles = _normalized_text_list(existing_roles_raw) or []
    storage_roles = sorted({*existing_roles, spec.storage_kind})

    existing_pipeline_names_raw = (
        existing.properties.get("pipeline_names") if existing is not None else None
    )
    existing_pipeline_names = _normalized_text_list(existing_pipeline_names_raw) or []
    pipeline_names: list[str] = sorted(
        {
            *existing_pipeline_names,
            *([pipeline_name] if pipeline_name is not None else []),
        }
    )

    primary_storage_kind = (
        _optional_text(existing.properties.get("storage_kind"))
        if existing is not None
        else None
    ) or spec.storage_kind
    primary_pipeline_name = (
        _optional_text(existing.properties.get("pipeline_name"))
        if existing is not None
        else None
    ) or pipeline_name
    return (
        layer,
        provider,
        entity,
        storage_roles,
        pipeline_names,
        primary_storage_kind,
        primary_pipeline_name,
    )


def _storage_surface_semantic_properties(
    spec: StorageSurfaceSpec,
) -> dict[str, JsonValue]:
    # Merge curated semantic properties with the normalized top-level storage fields
    # without passing duplicate keyword arguments into add_node().
    semantic_properties = dict(spec.semantic_properties)
    explicit_semantic_fields: dict[str, JsonValue] = {
        "partition_by": spec.partition_by,
        "sort_by": spec.sort_by,
        "on_schema_mismatch": spec.on_schema_mismatch,
        "versioning_mode": spec.versioning_mode,
        "version_column": spec.version_column,
        "current_flag_column": spec.current_flag_column,
        "valid_from_column": spec.valid_from_column,
        "valid_to_column": spec.valid_to_column,
        "merge_strategy": spec.merge_strategy,
    }
    for field_name, field_value in explicit_semantic_fields.items():
        if field_value is not None:
            semantic_properties[field_name] = field_value
    return semantic_properties


def _add_control_plane_artifact_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    spec: ControlPlaneArtifactSpec,
) -> NodeKey:
    artifact = snapshot.add_node(
        "control_plane_artifact_surface",
        spec.artifact_name,
        summary=spec.summary,
        artifact_family=spec.artifact_family,
        artifact_kind=spec.artifact_kind,
        storage_ref=spec.storage_ref,
        artifact_format=spec.artifact_format,
        key_template=spec.key_template,
        last_verified=spec.today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(
        project, "HAS_CONTROL_PLANE_ARTIFACT", artifact, provenance="runtime_evidence"
    )
    return artifact


def _entity_pipeline_scope(
    provider_name: str, entity_name: str, pipeline_name: str
) -> EntityScope:
    return EntityScope(
        provider=provider_name, entity=entity_name, pipeline_name=pipeline_name
    )


def _scd_config_columns(layer_config: dict[str, object]) -> dict[str, str | None]:
    scd_config = _as_mapping(layer_config.get("scd_config"))
    return {
        "version_column": _optional_text(scd_config.get("version_col")),
        "current_flag_column": _optional_text(scd_config.get("current_flag_col")),
        "valid_from_column": _optional_text(scd_config.get("valid_from_col")),
        "valid_to_column": _optional_text(scd_config.get("valid_to_col")),
    }


def _add_entity_layer_field_nodes(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: EntityPipelineContext,
    layer_context: EntityLayerFieldContext,
) -> dict[str, NodeKey]:
    layer_field_nodes: dict[str, NodeKey] = {}
    scope = _entity_pipeline_scope(
        context.provider_name, context.entity_name, context.pipeline_name
    )
    drift_classification = (
        "staging_projection" if layer_context.layer_name == "bronze" else None
    )
    for field_group, field_name in _filtered_group_fields(
        layer_context.payload, layer_name=layer_context.layer_name
    ):
        _add_entity_regular_field_node(
            snapshot,
            project,
            context,
            layer_context,
            scope=scope,
            field_group=field_group,
            field_name=field_name,
            drift_classification=drift_classification,
            layer_field_nodes=layer_field_nodes,
        )
    for metadata_field in _scd_config_columns(layer_context.layer_config).values():
        _add_entity_metadata_field_node(
            snapshot,
            project,
            context,
            layer_context,
            scope=scope,
            metadata_field=metadata_field,
            layer_field_nodes=layer_field_nodes,
        )
    return layer_field_nodes


def _add_entity_regular_field_node(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: EntityPipelineContext,
    layer_context: EntityLayerFieldContext,
    *,
    scope: EntityScope,
    field_group: str,
    field_name: str,
    drift_classification: str | None,
    layer_field_nodes: dict[str, NodeKey],
) -> None:
    field_quality = layer_context.quality_index.get(field_name, {})
    field_node = _add_schema_field_surface(
        snapshot,
        project,
        layer_context.surface,
        field_name=field_name,
        field_group=field_group,
        today=context.today,
        spec=SchemaFieldSpec(
            contract_ref=context.contract_ref,
            scope=scope,
            required_in_quality=(
                bool(field_quality.get("required_in_quality"))
                if field_quality.get("required_in_quality") is not None
                else None
            ),
            validation_types=_normalized_text_list(
                field_quality.get("validation_types")
            ),
            drift_classification=drift_classification,
        ),
    )
    layer_field_nodes[field_name] = field_node
    _link_schema_field_definition(snapshot, field_node, context.config_artifact)


def _add_entity_metadata_field_node(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: EntityPipelineContext,
    layer_context: EntityLayerFieldContext,
    *,
    scope: EntityScope,
    metadata_field: str | None,
    layer_field_nodes: dict[str, NodeKey],
) -> None:
    if metadata_field is None or metadata_field in layer_field_nodes:
        return
    field_node = _add_schema_field_surface(
        snapshot,
        project,
        layer_context.surface,
        field_name=metadata_field,
        field_group="system",
        today=context.today,
        spec=SchemaFieldSpec(
            contract_ref=context.contract_ref,
            scope=scope,
            drift_classification="runtime_metadata",
        ),
    )
    layer_field_nodes[metadata_field] = field_node
    _link_schema_field_definition(snapshot, field_node, context.config_artifact)


def _link_schema_field_definition(
    snapshot: GraphSnapshot,
    field_node: NodeKey,
    config_artifact: NodeKey,
) -> None:
    if config_artifact in snapshot.nodes:
        snapshot.add_relation(
            field_node, "DEFINED_BY", config_artifact, provenance="schema_fields"
        )


def _add_entity_storage_layers(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: EntityPipelineContext,
    payload: dict[str, object],
    base_sink: dict[str, object],
    pipeline_sink: dict[str, object],
    quality_index: dict[str, dict[str, JsonValue]],
) -> tuple[dict[str, NodeKey], dict[str, dict[str, NodeKey]]]:
    layer_nodes: dict[str, NodeKey] = {}
    field_nodes_by_layer: dict[str, dict[str, NodeKey]] = {}
    scope = _entity_pipeline_scope(
        context.provider_name, context.entity_name, context.pipeline_name
    )
    for layer_name in ("bronze", "silver", "gold"):
        _add_entity_storage_layer(
            snapshot,
            project,
            context,
            payload,
            base_sink,
            pipeline_sink,
            quality_index,
            scope=scope,
            layer_name=layer_name,
            layer_nodes=layer_nodes,
            field_nodes_by_layer=field_nodes_by_layer,
        )
    return layer_nodes, field_nodes_by_layer


def _add_entity_storage_layer(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: EntityPipelineContext,
    payload: dict[str, object],
    base_sink: dict[str, object],
    pipeline_sink: dict[str, object],
    quality_index: dict[str, dict[str, JsonValue]],
    *,
    scope: EntityScope,
    layer_name: str,
    layer_nodes: dict[str, NodeKey],
    field_nodes_by_layer: dict[str, dict[str, NodeKey]],
) -> None:
    layer_config = _merge_storage_layer_config(base_sink, pipeline_sink, layer_name)
    if _skip_entity_storage_layer(layer_name, layer_config):
        return
    surface = _create_entity_storage_layer_surface(
        snapshot,
        project,
        context,
        payload,
        scope=scope,
        layer_name=layer_name,
        layer_config=layer_config,
    )
    layer_nodes[layer_name] = surface
    _link_entity_storage_layer_backing(snapshot, context, surface)
    field_nodes_by_layer[layer_name] = _add_entity_layer_field_nodes(
        snapshot,
        project,
        context,
        EntityLayerFieldContext(
            payload=payload,
            surface=surface,
            layer_name=layer_name,
            quality_index=quality_index,
            layer_config=layer_config,
        ),
    )


def _skip_entity_storage_layer(
    layer_name: str, layer_config: dict[str, object]
) -> bool:
    return layer_name == "gold" and not bool(layer_config.get("enabled", True))


def _create_entity_storage_layer_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: EntityPipelineContext,
    payload: dict[str, object],
    *,
    scope: EntityScope,
    layer_name: str,
    layer_config: dict[str, object],
) -> NodeKey:
    storage_ref = f"{layer_name}/{context.provider_name}/{context.entity_name}"
    return _add_storage_surface(
        snapshot,
        project,
        StorageSurfaceSpec(
            ref=storage_ref,
            summary=f"{layer_name.title()} storage surface for `{context.pipeline_name}`.",
            layer=layer_name,
            today=context.today,
            storage_kind="entity_layer_output",
            scope=scope,
            format_name=str(layer_config.get("format"))
            if layer_config.get("format") is not None
            else None,
            mode=str(layer_config.get("mode"))
            if layer_config.get("mode") is not None
            else None,
            enabled=bool(layer_config.get("enabled", True)),
            retention_days=context.retention_days,
            config_version=context.config_version,
            quality_version=context.quality_version,
            partition_by=_normalized_text_list(layer_config.get("partition_by")),
            sort_by=_normalized_text_list(layer_config.get("sort_by")),
            on_schema_mismatch=_optional_text(layer_config.get("on_schema_mismatch")),
            versioning_mode=_optional_text(layer_config.get("mode")),
            semantic_properties={
                **_scd_config_columns(layer_config),
                **_storage_schema_properties(payload, layer_name=layer_name),
            },
        ),
    )


def _link_entity_storage_layer_backing(
    snapshot: GraphSnapshot,
    context: EntityPipelineContext,
    surface: NodeKey,
) -> None:
    if context.pipeline_key in snapshot.nodes:
        snapshot.add_relation(
            context.pipeline_key, "WRITES_TO", surface, provenance="storage_surfaces"
        )
    if context.entity_key in snapshot.nodes:
        snapshot.add_relation(
            context.entity_key, "WRITES_TO", surface, provenance="storage_surfaces"
        )
    if context.config_artifact in snapshot.nodes:
        snapshot.add_relation(
            surface,
            "DEFINED_BY",
            context.config_artifact,
            provenance="storage_surfaces",
        )


def _link_entity_storage_promotions(
    snapshot: GraphSnapshot,
    layer_nodes: dict[str, NodeKey],
    field_nodes_by_layer: dict[str, dict[str, NodeKey]],
) -> None:
    bronze_fields = field_nodes_by_layer.get("bronze", {})
    silver_fields = field_nodes_by_layer.get("silver", {})
    gold_fields = field_nodes_by_layer.get("gold", {})
    for (
        source_name,
        target_name,
        source_fields,
        target_fields,
    ) in _entity_storage_promotion_pairs(
        layer_nodes,
        bronze_fields=bronze_fields,
        silver_fields=silver_fields,
        gold_fields=gold_fields,
    ):
        _link_storage_layer_promotion(
            snapshot,
            layer_nodes[source_name],
            layer_nodes[target_name],
            source_fields,
            target_fields,
        )
    if "silver" in layer_nodes and "gold" in layer_nodes:
        _classify_projected_storage_fields(snapshot, silver_fields, gold_fields)


def _entity_storage_promotion_pairs(
    layer_nodes: dict[str, NodeKey],
    *,
    bronze_fields: dict[str, NodeKey],
    silver_fields: dict[str, NodeKey],
    gold_fields: dict[str, NodeKey],
) -> tuple[tuple[str, str, dict[str, NodeKey], dict[str, NodeKey]], ...]:
    pairs: list[tuple[str, str, dict[str, NodeKey], dict[str, NodeKey]]] = []
    if "bronze" in layer_nodes and "silver" in layer_nodes:
        pairs.append(("bronze", "silver", bronze_fields, silver_fields))
    if "silver" in layer_nodes and "gold" in layer_nodes:
        pairs.append(("silver", "gold", silver_fields, gold_fields))
    return tuple(pairs)


def _link_storage_layer_promotion(
    snapshot: GraphSnapshot,
    source_layer: NodeKey,
    target_layer: NodeKey,
    source_fields: dict[str, NodeKey],
    target_fields: dict[str, NodeKey],
) -> None:
    snapshot.add_relation(
        source_layer, "PROMOTES_TO", target_layer, provenance="storage_surfaces"
    )
    for field_name, source_field in source_fields.items():
        target_field = target_fields.get(field_name)
        if target_field is not None:
            snapshot.add_relation(
                source_field,
                "PROMOTES_FIELD_TO",
                target_field,
                provenance="schema_fields",
            )


def _classify_projected_storage_fields(
    snapshot: GraphSnapshot,
    silver_fields: dict[str, NodeKey],
    gold_fields: dict[str, NodeKey],
) -> None:
    _classify_silver_storage_fields(snapshot, silver_fields, gold_fields)
    _classify_gold_storage_fields(snapshot, silver_fields, gold_fields)


def _classify_silver_storage_fields(
    snapshot: GraphSnapshot,
    silver_fields: dict[str, NodeKey],
    gold_fields: dict[str, NodeKey],
) -> None:
    for field_name, silver_field in silver_fields.items():
        silver_node = snapshot.nodes.get(silver_field)
        if silver_node is None:
            continue
        gold_field = gold_fields.get(field_name)
        if gold_field is not None:
            snapshot.add_relation(
                silver_field,
                "PROMOTES_FIELD_TO",
                gold_field,
                provenance="schema_fields",
            )
            silver_node.properties["drift_classification"] = "projected_to_gold"
            continue
        silver_node.properties["drift_classification"] = "silver_only"


def _classify_gold_storage_fields(
    snapshot: GraphSnapshot,
    silver_fields: dict[str, NodeKey],
    gold_fields: dict[str, NodeKey],
) -> None:
    for field_name, gold_field in gold_fields.items():
        gold_node = snapshot.nodes.get(gold_field)
        if gold_node is None:
            continue
        gold_node.properties["drift_classification"] = (
            "promoted_from_silver" if field_name in silver_fields else "gold_only"
        )


def _composite_group_fields(merge_payload: dict[str, object]) -> list[tuple[str, str]]:
    group_fields: list[tuple[str, str]] = []
    column_groups = merge_payload.get("column_groups")
    if not isinstance(column_groups, list):
        return group_fields
    for item in column_groups:
        group_fields.extend(_composite_group_field_entries(item))
    return group_fields


def _composite_group_field_entries(item: object) -> list[tuple[str, str]]:
    if not isinstance(item, dict):
        return []
    group_name = _optional_text(item.get("name"))
    if group_name is None:
        return []
    return [
        (group_name, field_name)
        for field_name in (_normalized_text_list(item.get("fields")) or [])
    ]


def _add_composite_seed_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: CompositePipelineContext,
    composite_payload: dict[str, object],
    has_dependency_pipelines: bool,
) -> list[str]:
    seed_storage_ref = _composite_seed_storage_ref(composite_payload)
    if seed_storage_ref is None:
        return []
    seed_surface = NodeKey("storage_surface", seed_storage_ref)
    if has_dependency_pipelines or seed_surface not in snapshot.nodes:
        seed_surface = _add_storage_surface(
            snapshot,
            project,
            StorageSurfaceSpec(
                ref=seed_storage_ref,
                summary=f"Seed storage surface for composite pipeline `{context.composite_name}`.",
                layer="silver",
                today=context.today,
                storage_kind="composite_seed_input",
                scope=EntityScope(pipeline_name=context.composite_name),
            ),
        )
    _link_composite_seed_surface(snapshot, context, seed_surface)
    return [seed_storage_ref]


def _composite_seed_storage_ref(composite_payload: dict[str, object]) -> str | None:
    seed_payload = _as_mapping(composite_payload.get("seed"))
    seed_table = seed_payload.get("silver_table")
    if not isinstance(seed_table, str) or not seed_table.strip():
        return None
    return seed_table.strip()


def _link_composite_seed_surface(
    snapshot: GraphSnapshot,
    context: CompositePipelineContext,
    seed_surface: NodeKey,
) -> None:
    if context.pipeline_key in snapshot.nodes:
        snapshot.add_relation(
            context.pipeline_key,
            "DEPENDS_ON",
            seed_surface,
            provenance="storage_surfaces",
        )
    if context.config_artifact in snapshot.nodes:
        snapshot.add_relation(
            seed_surface,
            "DEFINED_BY",
            context.config_artifact,
            provenance="storage_surfaces",
        )


def _add_composite_dependency_surfaces(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: CompositePipelineContext,
    dependencies: object,
) -> list[str]:
    source_storage_refs: list[str] = []
    if not isinstance(dependencies, list):
        return source_storage_refs
    for dependency in dependencies:
        storage_ref = _composite_dependency_storage_ref(dependency)
        if storage_ref is None:
            continue
        source_storage_refs.append(storage_ref)
        dependency_surface = _add_composite_dependency_surface(
            snapshot, project, context, storage_ref
        )
        _link_composite_dependency_surface(
            snapshot, context, dependency_surface, dependency
        )
    return source_storage_refs


def _composite_dependency_storage_ref(dependency: object) -> str | None:
    if not isinstance(dependency, dict):
        return None
    silver_table = dependency.get("silver_table")
    if not isinstance(silver_table, str) or not silver_table.strip():
        return None
    return silver_table.strip()


def _add_composite_dependency_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: CompositePipelineContext,
    storage_ref: str,
) -> NodeKey:
    return _add_storage_surface(
        snapshot,
        project,
        StorageSurfaceSpec(
            ref=storage_ref,
            summary=f"Dependency storage surface for composite pipeline `{context.composite_name}`.",
            layer="silver",
            today=context.today,
            storage_kind="composite_dependency_input",
            scope=EntityScope(pipeline_name=context.composite_name),
        ),
    )


def _link_composite_dependency_surface(
    snapshot: GraphSnapshot,
    context: CompositePipelineContext,
    dependency_surface: NodeKey,
    dependency: object,
) -> None:
    required = (
        bool(dependency.get("required", False))
        if isinstance(dependency, dict)
        else False
    )
    if context.pipeline_key in snapshot.nodes:
        snapshot.add_relation(
            context.pipeline_key,
            "DEPENDS_ON",
            dependency_surface,
            provenance="storage_surfaces",
            required=required,
        )
    if context.config_artifact in snapshot.nodes:
        snapshot.add_relation(
            dependency_surface,
            "DEFINED_BY",
            context.config_artifact,
            provenance="storage_surfaces",
        )


def _add_composite_output_layers(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: CompositePipelineContext,
    output_config: CompositeOutputConfig,
) -> tuple[dict[str, NodeKey], dict[str, dict[str, NodeKey]]]:
    layer_nodes: dict[str, NodeKey] = {}
    field_nodes_by_layer: dict[str, dict[str, NodeKey]] = {}
    composite_scope = EntityScope(
        provider="composite",
        entity=context.composite_name.removeprefix("composite_"),
        pipeline_name=context.composite_name,
    )
    for layer_name in ("silver", "gold"):
        surface = _add_composite_output_surface(
            snapshot,
            project,
            context,
            output_config,
            layer_name=layer_name,
        )
        if surface is None:
            continue
        layer_nodes[layer_name] = surface
        field_nodes_by_layer[layer_name] = _add_composite_output_field_nodes(
            snapshot,
            project,
            context,
            output_config,
            composite_scope=composite_scope,
            surface=surface,
        )
    return layer_nodes, field_nodes_by_layer


def _composite_output_storage_ref(
    output_payload: dict[str, object], layer_name: str
) -> str | None:
    output_path = output_payload.get(layer_name)
    if not isinstance(output_path, str) or not output_path.strip():
        return None
    return _storage_ref_from_output_path(output_path)


def _add_composite_output_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: CompositePipelineContext,
    output_config: CompositeOutputConfig,
    *,
    layer_name: str,
) -> NodeKey | None:
    storage_ref = _composite_output_storage_ref(
        output_config.output_payload, layer_name
    )
    if storage_ref is None:
        return None
    surface = _add_storage_surface(
        snapshot,
        project,
        StorageSurfaceSpec(
            ref=storage_ref,
            summary=f"{layer_name.title()} output surface for composite pipeline `{context.composite_name}`.",
            layer=layer_name,
            today=context.today,
            storage_kind="composite_layer_output",
            scope=EntityScope(pipeline_name=context.composite_name),
            config_version=context.composite_version,
            semantic_properties={
                "merge_strategy": _optional_text(
                    output_config.merge_payload.get("strategy")
                ),
                "sort_by": _normalized_text_list(
                    _as_mapping(output_config.merge_payload.get("sort_by")).get(
                        layer_name
                    )
                ),
            },
        ),
    )
    if context.pipeline_key in snapshot.nodes:
        snapshot.add_relation(
            context.pipeline_key, "WRITES_TO", surface, provenance="storage_surfaces"
        )
    if context.config_artifact in snapshot.nodes:
        snapshot.add_relation(
            surface,
            "DEFINED_BY",
            context.config_artifact,
            provenance="storage_surfaces",
        )
    return surface


def _add_composite_output_field_nodes(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: CompositePipelineContext,
    output_config: CompositeOutputConfig,
    *,
    composite_scope: EntityScope,
    surface: NodeKey,
) -> dict[str, NodeKey]:
    layer_field_nodes: dict[str, NodeKey] = {}
    for field_group, field_name in output_config.group_fields:
        candidate_sources = [
            ref
            for ref in output_config.source_storage_refs
            if field_name in output_config.schema_fields_by_storage.get(ref, {})
        ]
        field_node = _add_schema_field_surface(
            snapshot,
            project,
            surface,
            field_name=field_name,
            field_group=field_group,
            today=context.today,
            spec=SchemaFieldSpec(
                scope=composite_scope,
                drift_classification="inherited_field"
                if candidate_sources
                else "composite_only",
                source_storage_refs=candidate_sources if candidate_sources else None,
            ),
        )
        layer_field_nodes[field_name] = field_node
        if context.config_artifact in snapshot.nodes:
            snapshot.add_relation(
                field_node,
                "DEFINED_BY",
                context.config_artifact,
                provenance="schema_fields",
            )
        for source_ref in candidate_sources:
            source_field = output_config.schema_fields_by_storage.get(
                source_ref, {}
            ).get(field_name)
            if source_field is not None:
                snapshot.add_relation(
                    field_node,
                    "DERIVES_FIELD_FROM",
                    source_field,
                    provenance="schema_fields",
                )
    return layer_field_nodes


def _base_pipeline_storage_config(
    root: Path,
) -> tuple[dict[str, object], dict[str, object]]:
    base_pipeline_path = root / "configs" / "base" / "pipeline.yaml"
    base_payload = (
        _read_yaml(base_pipeline_path) if base_pipeline_path.is_file() else {}
    )
    base_sink = _as_mapping(base_payload.get("sink"))
    return base_payload, base_sink


def _add_storage_data_surfaces(
    snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str
) -> None:
    base_payload, base_sink = _base_pipeline_storage_config(root)
    schema_fields_by_storage: dict[str, dict[str, NodeKey]] = {}
    _add_entity_storage_data_surfaces(
        snapshot,
        root,
        project,
        today,
        base_payload=base_payload,
        base_sink=base_sink,
        schema_fields_by_storage=schema_fields_by_storage,
    )
    _add_composite_storage_data_surfaces(
        snapshot,
        root,
        project,
        today,
        schema_fields_by_storage=schema_fields_by_storage,
    )


def _add_entity_storage_data_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    *,
    base_payload: dict[str, object],
    base_sink: dict[str, object],
    schema_fields_by_storage: dict[str, dict[str, NodeKey]],
) -> None:
    entities_root = root / "configs" / "entities"
    for entity_path in sorted(entities_root.rglob(YAML_FILE_GLOB)):
        payload = _read_yaml(entity_path)
        context, pipeline_sink, quality_index = _entity_storage_context(
            root,
            entity_path,
            payload,
            today=today,
            base_payload=base_payload,
        )
        layer_nodes, field_nodes_by_layer = _add_entity_storage_layers(
            snapshot,
            project,
            context,
            payload=payload,
            base_sink=base_sink,
            pipeline_sink=pipeline_sink,
            quality_index=quality_index,
        )
        _index_storage_layer_fields(
            schema_fields_by_storage, layer_nodes, field_nodes_by_layer
        )
        _link_entity_storage_promotions(snapshot, layer_nodes, field_nodes_by_layer)


def _entity_storage_context(
    root: Path,
    entity_path: Path,
    payload: dict[str, object],
    *,
    today: str,
    base_payload: dict[str, object],
) -> tuple[
    EntityPipelineContext,
    dict[str, object],
    dict[str, dict[str, JsonValue]],
]:
    provider_name = str(payload.get("provider", entity_path.parent.name))
    entity_name = str(payload.get("entity", entity_path.stem))
    pipeline_payload = _as_mapping(payload.get("pipeline"))
    pipeline_name = str(
        pipeline_payload.get("pipeline_name", f"{provider_name}_{entity_name}")
    )
    maintenance_config = _merged_maintenance_config(base_payload, payload)
    retention_days = maintenance_config.get("vacuum_retention_days")
    quality_payload = _as_mapping(payload.get("quality"))
    context = EntityPipelineContext(
        provider_name=provider_name,
        entity_name=entity_name,
        pipeline_name=pipeline_name,
        pipeline_key=NodeKey("pipeline_surface", pipeline_name),
        entity_key=NodeKey("entity_config", pipeline_name),
        config_artifact=NodeKey("config_artifact", _rel_path(root, entity_path)),
        today=today,
        contract_ref=f"{provider_name}.{entity_name}",
        retention_days=_coerce_int(retention_days)
        if isinstance(retention_days, int | float)
        else None,
        config_version=_optional_text(payload.get("version")),
        quality_version=_optional_text(quality_payload.get("version")),
    )
    pipeline_sink = _entity_pipeline_sink_config(payload)
    return context, pipeline_sink, _field_quality_index(payload)


def _index_storage_layer_fields(
    schema_fields_by_storage: dict[str, dict[str, NodeKey]],
    layer_nodes: dict[str, NodeKey],
    field_nodes_by_layer: dict[str, dict[str, NodeKey]],
) -> None:
    for layer_name, surface in layer_nodes.items():
        schema_fields_by_storage[surface.name] = field_nodes_by_layer.get(
            layer_name, {}
        )


def _add_composite_storage_data_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    *,
    schema_fields_by_storage: dict[str, dict[str, NodeKey]],
) -> None:
    composites_root = root / "configs" / "composites"
    for composite_path in sorted(composites_root.glob(YAML_FILE_GLOB)):
        payload = _read_yaml(composite_path)
        context, composite_payload, dependencies = _composite_storage_context(
            root,
            composite_path,
            payload,
            today=today,
        )
        has_dependency_pipelines = isinstance(dependencies, list) and any(
            isinstance(item, dict) for item in dependencies
        )
        source_storage_refs = _add_composite_seed_surface(
            snapshot,
            project,
            context,
            composite_payload=composite_payload,
            has_dependency_pipelines=has_dependency_pipelines,
        )
        source_storage_refs.extend(
            _add_composite_dependency_surfaces(
                snapshot,
                project,
                context,
                dependencies=dependencies,
            )
        )
        merge_payload = _as_mapping(composite_payload.get("merge"))
        output_payload = _as_mapping(merge_payload.get("output"))
        layer_nodes, field_nodes_by_layer = _add_composite_output_layers(
            snapshot,
            project,
            context,
            CompositeOutputConfig(
                merge_payload=merge_payload,
                output_payload=output_payload,
                group_fields=_composite_group_fields(merge_payload),
                source_storage_refs=source_storage_refs,
                schema_fields_by_storage=schema_fields_by_storage,
            ),
        )
        _index_storage_layer_fields(
            schema_fields_by_storage, layer_nodes, field_nodes_by_layer
        )
        _link_composite_layer_promotions(snapshot, layer_nodes, field_nodes_by_layer)


def _link_composite_layer_promotions(
    snapshot: GraphSnapshot,
    layer_nodes: dict[str, NodeKey],
    field_nodes_by_layer: dict[str, dict[str, NodeKey]],
) -> None:
    silver_layer = layer_nodes.get("silver")
    gold_layer = layer_nodes.get("gold")
    if silver_layer is None or gold_layer is None:
        return
    snapshot.add_relation(
        silver_layer,
        "PROMOTES_TO",
        gold_layer,
        provenance="storage_surfaces",
    )
    gold_fields = field_nodes_by_layer.get("gold", {})
    for field_name, silver_field in field_nodes_by_layer.get("silver", {}).items():
        gold_field = gold_fields.get(field_name)
        if gold_field is None:
            continue
        snapshot.add_relation(
            silver_field,
            "PROMOTES_FIELD_TO",
            gold_field,
            provenance="schema_fields",
        )


def _composite_storage_context(
    root: Path,
    composite_path: Path,
    payload: dict[str, object],
    *,
    today: str,
) -> tuple[CompositePipelineContext, dict[str, object], object]:
    composite_payload = _as_mapping(payload.get("composite"))
    composite_name = str(composite_payload.get("name", composite_path.stem))
    context = CompositePipelineContext(
        composite_name=composite_name,
        pipeline_key=NodeKey("pipeline_surface", composite_name),
        config_artifact=NodeKey("config_artifact", _rel_path(root, composite_path)),
        today=today,
        composite_version=_optional_text(composite_payload.get("version")),
    )
    return context, composite_payload, composite_payload.get("dependencies")


CONTROL_PLANE_LEDGER_DOCS = (
    RUN_MANIFEST_LEDGER_DOC_PATH,
    RUN_MANIFEST_INSPECTION_DOC_PATH,
    "docs/02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md",
)

RUN_MANIFEST_RUNTIME_MODULES = (
    "src/bioetl/domain/control_plane/run_manifest.py",
    "src/bioetl/application/services/control_plane/run_manifest_service.py",
    "src/bioetl/application/services/control_plane/run_manifest_diagnostics.py",
    "src/bioetl/application/services/control_plane/run_manifest_inspection_service.py",
    "src/bioetl/interfaces/cli/commands/run_manifest.py",
    "src/bioetl/composition/bootstrap/cli/run_manifest.py",
    "src/bioetl/composition/runtime_builders/run_manifest_builder.py",
)

RUN_LEDGER_RUNTIME_MODULES = (
    "src/bioetl/domain/control_plane/run_ledger.py",
    "src/bioetl/application/services/control_plane/run_ledger_service.py",
)

EFFECTIVE_CONFIG_RUNTIME_MODULES = (
    "src/bioetl/domain/control_plane/effective_config_artifact.py",
    "src/bioetl/composition/services/effective_config_serializer.py",
    "src/bioetl/infrastructure/control_plane/file_effective_config_artifact_store.py",
)

LINEAGE_RUNTIME_MODULES = (
    "src/bioetl/application/services/lineage/lineage_inspection_service.py",
    "src/bioetl/composition/bootstrap/cli/lineage.py",
    "src/bioetl/infrastructure/control_plane/file_lineage_store.py",
)

RUNTIME_EVIDENCE_DEFINITIONS = (
    (
        "run_manifest",
        "Control-plane runtime evidence for immutable run manifests.",
        RUN_MANIFEST_LEDGER_DOC_PATH,
        CONTROL_PLANE_LEDGER_DOCS,
        RUN_MANIFEST_RUNTIME_MODULES,
        (
            (
                f"control/run_manifest/{MANIFEST_ID_TEMPLATE}.json",
                "json",
                MANIFEST_ID_TEMPLATE,
            ),
            (
                f"control/run_manifest/_by_run_id/{RUN_ID_TEMPLATE}.txt",
                "run_index",
                RUN_ID_TEMPLATE,
            ),
        ),
    ),
    (
        "run_ledger",
        "Control-plane runtime evidence for append-only run ledgers.",
        RUN_MANIFEST_LEDGER_DOC_PATH,
        CONTROL_PLANE_LEDGER_DOCS,
        RUN_LEDGER_RUNTIME_MODULES,
        (
            (
                f"control/run_ledger/{MANIFEST_ID_TEMPLATE}.jsonl",
                "jsonl",
                MANIFEST_ID_TEMPLATE,
            ),
            (
                f"control/run_ledger/_by_run_id/{RUN_ID_TEMPLATE}.txt",
                "run_index",
                RUN_ID_TEMPLATE,
            ),
        ),
    ),
    (
        "effective_config_artifact",
        "Runtime evidence for effective configuration artifacts and hashes.",
        "docs/04-reference/components/config-runtime-artifacts.md",
        (
            "docs/04-reference/components/config-runtime-artifacts.md",
            RUN_MANIFEST_INSPECTION_DOC_PATH,
        ),
        EFFECTIVE_CONFIG_RUNTIME_MODULES,
        (
            ("control/effective_config/{artifact_id}.json", "json", "{artifact_id}"),
            (
                f"control/effective_config/_by_run_id/{RUN_ID_TEMPLATE}.txt",
                "run_index",
                RUN_ID_TEMPLATE,
            ),
        ),
    ),
    (
        "lineage",
        "Runtime evidence for artifact lineage and inspection surfaces.",
        TRACEABILITY_SIGNAL_OWNERSHIP_DOC_PATH,
        (
            TRACEABILITY_SIGNAL_OWNERSHIP_DOC_PATH,
            RUN_MANIFEST_LEDGER_DOC_PATH,
        ),
        LINEAGE_RUNTIME_MODULES,
        (
            (
                "control/lineage/fragments/{fragment_hash}.json",
                "fragment",
                "{fragment_id}",
            ),
            (
                "control/lineage/_by_run_id/{run_id_hash}.jsonl",
                "run_index",
                RUN_ID_TEMPLATE,
            ),
            (
                "control/lineage/_by_manifest_id/{manifest_id_hash}.jsonl",
                "manifest_index",
                MANIFEST_ID_TEMPLATE,
            ),
            (
                "control/lineage/_by_node_id/{node_id_hash}.jsonl",
                "node_index",
                "{node_id}",
            ),
        ),
    ),
)


def _runtime_evidence_spec(
    *,
    name: str,
    summary: str,
    source_path: str,
    docs: tuple[str, ...],
    modules: tuple[str, ...],
    storage_refs: tuple[tuple[str, str, str], ...],
) -> dict[str, object]:
    return {
        "name": name,
        "summary": summary,
        "source_path": source_path,
        "docs": docs,
        "modules": modules,
        "storage_refs": storage_refs,
    }


def _runtime_evidence_definition_spec(
    definition: tuple[
        str,
        str,
        str,
        tuple[str, ...],
        tuple[str, ...],
        tuple[tuple[str, str, str], ...],
    ],
) -> dict[str, object]:
    name, summary, source_path, docs, modules, storage_refs = definition
    return _runtime_evidence_spec(
        name=name,
        summary=summary,
        source_path=source_path,
        docs=docs,
        modules=modules,
        storage_refs=storage_refs,
    )


def _control_plane_runtime_evidence_specs() -> tuple[dict[str, object], ...]:
    return tuple(
        _runtime_evidence_definition_spec(definition)
        for definition in RUNTIME_EVIDENCE_DEFINITIONS
    )


def _add_control_plane_runtime_evidence(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
) -> None:
    for spec in _control_plane_runtime_evidence_specs():
        _add_runtime_evidence_surface(snapshot, project, today, spec)

    _add_control_plane_run_instance_surfaces(snapshot, root, project, today)


def _add_runtime_evidence_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
    spec: dict[str, object],
) -> None:
    evidence_name = str(spec["name"])
    surface = snapshot.add_node(
        "runtime_evidence_surface",
        evidence_name,
        summary=str(spec["summary"]),
        source_path=str(spec["source_path"]),
        source_kind="runtime_evidence_surface",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(
        project, "HAS_RUNTIME_EVIDENCE", surface, provenance="runtime_evidence"
    )
    _link_runtime_evidence_support(snapshot, surface, spec)
    _add_runtime_evidence_storage_refs(
        snapshot,
        project,
        surface,
        evidence_name=evidence_name,
        storage_refs=spec["storage_refs"],
        today=today,
    )


def _link_runtime_evidence_support(
    snapshot: GraphSnapshot,
    surface: NodeKey,
    spec: dict[str, object],
) -> None:
    _link_runtime_evidence_docs(snapshot, surface, spec["docs"])
    _link_runtime_evidence_modules(snapshot, surface, spec["modules"])


def _add_runtime_evidence_storage_refs(
    snapshot: GraphSnapshot,
    project: NodeKey,
    surface: NodeKey,
    *,
    evidence_name: str,
    storage_refs: object,
    today: str,
) -> None:
    for storage_ref, suffix, key_template in _runtime_evidence_storage_refs(
        storage_refs
    ):
        _add_runtime_evidence_storage_artifact(
            snapshot,
            project,
            surface,
            evidence_name=evidence_name,
            storage_ref=storage_ref,
            suffix=suffix,
            key_template=key_template,
            today=today,
        )


def _runtime_evidence_storage_refs(
    storage_refs: object,
) -> tuple[tuple[str, str, str], ...]:
    if not isinstance(storage_refs, Iterable) or isinstance(
        storage_refs, str | bytes | dict
    ):
        return ()
    refs: list[tuple[str, str, str]] = []
    for candidate in storage_refs:
        if not isinstance(candidate, tuple | list) or len(candidate) != 3:
            continue
        if all(isinstance(item, str) for item in candidate):
            refs.append((candidate[0], candidate[1], candidate[2]))
    return tuple(refs)


def _iter_object_values(values: object) -> tuple[object, ...]:
    if not isinstance(values, Iterable) or isinstance(values, str | bytes | dict):
        return ()
    return tuple(values)


def _link_runtime_evidence_docs(
    snapshot: GraphSnapshot,
    surface: NodeKey,
    doc_paths: object,
) -> None:
    for doc_path in _iter_object_values(doc_paths):
        doc_key = NodeKey("doc_artifact", str(doc_path))
        if doc_key in snapshot.nodes:
            snapshot.add_relation(
                surface, "DESCRIBED_IN", doc_key, provenance="runtime_evidence"
            )


def _link_runtime_evidence_modules(
    snapshot: GraphSnapshot,
    surface: NodeKey,
    module_paths: object,
) -> None:
    for module_path in _iter_object_values(module_paths):
        module_key = NodeKey("module_surface", str(module_path))
        if module_key in snapshot.nodes:
            snapshot.add_relation(
                surface, "BACKED_BY", module_key, provenance="runtime_evidence"
            )


def _add_runtime_evidence_storage_artifact(
    snapshot: GraphSnapshot,
    project: NodeKey,
    surface: NodeKey,
    *,
    evidence_name: str,
    storage_ref: str,
    suffix: str,
    key_template: str,
    today: str,
) -> None:
    storage = _add_storage_surface(
        snapshot,
        project,
        StorageSurfaceSpec(
            ref=storage_ref,
            summary=f"Control-plane storage surface `{storage_ref}`.",
            layer="control",
            today=today,
            storage_kind="control_plane_artifact",
        ),
    )
    snapshot.add_relation(
        surface, "WRITES_TO", storage, provenance="runtime_evidence", suffix=suffix
    )
    artifact = _add_control_plane_artifact_surface(
        snapshot,
        project,
        ControlPlaneArtifactSpec(
            artifact_name=f"{evidence_name}::{suffix}",
            summary=f"{evidence_name} control-plane artifact `{storage_ref}`.",
            today=today,
            artifact_family=evidence_name,
            artifact_kind=suffix,
            storage_ref=storage_ref,
            artifact_format=_storage_surface_format(snapshot, storage),
            key_template=key_template,
        ),
    )
    snapshot.add_relation(
        surface, "EMITS_ARTIFACT", artifact, provenance="runtime_evidence"
    )
    snapshot.add_relation(
        artifact, "MATERIALIZED_AS", storage, provenance="runtime_evidence"
    )


def _storage_surface_format(snapshot: GraphSnapshot, storage: NodeKey) -> str | None:
    storage_node = snapshot.nodes.get(storage)
    if storage_node is None:
        return None
    format_value = storage_node.properties.get("format")
    return str(format_value) if format_value is not None else None


def _run_instance_fixture_spec(
    *,
    manifest_id: str,
    run_id: str,
    source_path: str,
    doc_paths: tuple[str, ...],
    artifact_refs: tuple[str, ...],
    **extra: object,
) -> dict[str, object]:
    spec: dict[str, object] = {
        "manifest_id": manifest_id,
        "run_id": run_id,
        "source_path": source_path,
        "doc_paths": doc_paths,
        "artifact_refs": artifact_refs,
    }
    spec.update(extra)
    return spec


RUN_INSTANCE_PRIMARY_DOCS = (RUN_MANIFEST_LEDGER_DOC_PATH,)
RUN_INSTANCE_CHAIN_DOCS = (
    RUN_MANIFEST_LEDGER_DOC_PATH,
    RUN_MANIFEST_INSPECTION_DOC_PATH,
)
RUN_INSTANCE_TRACEABILITY_DOCS = (
    RUN_MANIFEST_LEDGER_DOC_PATH,
    TRACEABILITY_SIGNAL_OWNERSHIP_DOC_PATH,
)
RUN_INSTANCE_PRIMARY_ARTIFACT_REFS = (
    RUN_MANIFEST_ARTIFACT_REF,
    EFFECTIVE_CONFIG_ARTIFACT_REF,
)
RUN_INSTANCE_CHAIN_ARTIFACT_REFS = (
    RUN_MANIFEST_ARTIFACT_REF,
    RUN_LEDGER_ARTIFACT_REF,
    EFFECTIVE_CONFIG_ARTIFACT_REF,
)
RUN_INSTANCE_SPECS = (
    (
        "manifest-left",
        "00000000-0000-0000-0000-000000000301",
        "tests/integration/ci/test_reproducibility_contract_suite.py",
        RUN_INSTANCE_PRIMARY_DOCS,
        RUN_INSTANCE_PRIMARY_ARTIFACT_REFS,
        {
            "execution_fingerprint": "fp-stable",
            "created_at": "2025-01-01T00:00:00+00:00",
            "effective_config_artifact_id": "eca-123",
            "config_hash": "deadbeef",
            "replay_capability": "rebuild_only",
            "surface_kind": "reproducibility_fixture",
            "lifecycle_status": "fixture_manifest_only",
        },
    ),
    (
        "manifest-chain-smoke",
        "00000000-0000-0000-0000-000000000103",
        "tests/unit/application/services/test_run_manifest_inspection_service.py",
        RUN_INSTANCE_CHAIN_DOCS,
        (
            *RUN_INSTANCE_CHAIN_ARTIFACT_REFS,
            "lineage::run_index",
        ),
        {
            "effective_config_artifact_id": "eca-smoke-1",
            "config_hash": "hash-smoke",
            "surface_kind": "lifecycle_smoke_fixture",
            "lifecycle_status": "success",
            "published_dataset_ref": "silver:chembl.activity@1",
            "lineage_fragment_id": "silver:fragment-smoke-1",
        },
    ),
    (
        "manifest-chain-2",
        "00000000-0000-0000-0000-000000000102",
        "tests/unit/application/services/test_run_manifest_inspection_service.py",
        RUN_INSTANCE_TRACEABILITY_DOCS,
        RUN_INSTANCE_CHAIN_ARTIFACT_REFS,
        {
            "effective_config_artifact_id": "eca-chain-2",
            "surface_kind": "dq_failure_fixture",
            "lifecycle_status": "failed",
            "dq_disposition": "fail",
            "dq_rule_id": "gold.not_null.id",
            "dq_report_path": "data/output/gold/chembl/activity/_dq.json",
        },
    ),
    (
        "manifest-composite-quarantine",
        "00000000-0000-0000-0000-000000000402",
        "tests/integration/ci/test_reproducibility_contract_suite.py",
        RUN_INSTANCE_TRACEABILITY_DOCS,
        RUN_INSTANCE_CHAIN_ARTIFACT_REFS,
        {
            "execution_fingerprint": "fp-stable",
            "created_at": "2025-01-01T00:00:00+00:00",
            "effective_config_artifact_id": "eca-123",
            "config_hash": "deadbeef",
            "surface_kind": "cross_validation_quarantine_fixture",
            "lifecycle_status": "quarantined",
            "last_event_at": "2025-02-03T00:00:00+00:00",
            "replay_contract": "excluded_from_exact_replay",
            "diagnostic_scope": "composite_cross_validation_quarantine",
        },
    ),
)


def _chembl_activity_run_instance_fixture(
    *,
    manifest_id: str,
    run_id: str,
    source_path: str,
    doc_paths: tuple[str, ...],
    artifact_refs: tuple[str, ...],
    **extra: object,
) -> dict[str, object]:
    return _run_instance_fixture_spec(
        manifest_id=manifest_id,
        run_id=run_id,
        source_path=source_path,
        doc_paths=doc_paths,
        artifact_refs=artifact_refs,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        run_type="incremental",
        contract_ref=CHEMBL_ACTIVITY_CONTRACT_REF,
        contract_version="1.0.0",
        **extra,
    )


def _run_instance_definition_spec(
    definition: tuple[
        str, str, str, tuple[str, ...], tuple[str, ...], Mapping[str, object]
    ],
) -> dict[str, object]:
    manifest_id, run_id, source_path, doc_paths, artifact_refs, extra = definition
    return _chembl_activity_run_instance_fixture(
        manifest_id=manifest_id,
        run_id=run_id,
        source_path=source_path,
        doc_paths=doc_paths,
        artifact_refs=artifact_refs,
        **dict(extra),
    )


def _control_plane_run_instance_specs() -> tuple[dict[str, object], ...]:
    return tuple(
        _run_instance_definition_spec(definition) for definition in RUN_INSTANCE_SPECS
    )


def _add_run_instance_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
    spec: dict[str, object],
) -> NodeKey:
    manifest_id = str(spec["manifest_id"])
    surface = snapshot.add_node(
        "run_instance_surface",
        manifest_id,
        summary=f"Deterministic control-plane run instance surface for `{manifest_id}`.",
        **_run_instance_properties(spec, manifest_id=manifest_id),
        source_kind="run_instance_surface",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(
        project, "HAS_RUN_INSTANCE", surface, provenance="runtime_evidence"
    )
    return surface


def _link_run_instance_surface(
    snapshot: GraphSnapshot,
    surface: NodeKey,
    spec: dict[str, object],
) -> None:
    _link_run_instance_dependencies(snapshot, surface, spec)
    _link_run_instance_documents(snapshot, surface, spec)
    _link_run_instance_artifacts(snapshot, surface, spec)


def _link_run_instance_dependencies(
    snapshot: GraphSnapshot,
    surface: NodeKey,
    spec: dict[str, object],
) -> None:
    _link_run_instance_pipeline_dependency(snapshot, surface, spec)
    _link_run_instance_contract_dependency(snapshot, surface, spec)


def _run_instance_properties(
    spec: dict[str, object],
    *,
    manifest_id: str,
) -> dict[str, object]:
    return {
        "manifest_id": manifest_id,
        "run_id": _optional_text(spec.get("run_id")),
        "pipeline_name": _optional_text(spec.get("pipeline_name")),
        "provider": _optional_text(spec.get("provider")),
        "entity": _optional_text(spec.get("entity")),
        "run_type": _optional_text(spec.get("run_type")),
        "execution_fingerprint": _optional_text(spec.get("execution_fingerprint")),
        "created_at": _optional_text(spec.get("created_at")),
        "contract_ref": _optional_text(spec.get("contract_ref")),
        "contract_version": _optional_text(spec.get("contract_version")),
        "effective_config_artifact_id": _optional_text(
            spec.get("effective_config_artifact_id")
        ),
        "config_hash": _optional_text(spec.get("config_hash")),
        "replay_capability": _optional_text(spec.get("replay_capability")),
        "lifecycle_status": _optional_text(spec.get("lifecycle_status")),
        "dq_disposition": _optional_text(spec.get("dq_disposition")),
        "dq_rule_id": _optional_text(spec.get("dq_rule_id")),
        "dq_report_path": _optional_text(spec.get("dq_report_path")),
        "published_dataset_ref": _optional_text(spec.get("published_dataset_ref")),
        "lineage_fragment_id": _optional_text(spec.get("lineage_fragment_id")),
        "replay_contract": _optional_text(spec.get("replay_contract")),
        "diagnostic_scope": _optional_text(spec.get("diagnostic_scope")),
        "last_event_at": _optional_text(spec.get("last_event_at")),
        "surface_kind": _optional_text(spec.get("surface_kind")),
        "source_path": _optional_text(spec.get("source_path")),
    }


def _link_run_instance_pipeline_dependency(
    snapshot: GraphSnapshot,
    surface: NodeKey,
    spec: dict[str, object],
) -> None:
    pipeline_name = _optional_text(spec.get("pipeline_name"))
    if pipeline_name is None:
        return
    pipeline_key = NodeKey("pipeline_surface", pipeline_name)
    if pipeline_key in snapshot.nodes:
        snapshot.add_relation(
            surface, "DEPENDS_ON", pipeline_key, provenance="runtime_evidence"
        )


def _link_run_instance_contract_dependency(
    snapshot: GraphSnapshot,
    surface: NodeKey,
    spec: dict[str, object],
) -> None:
    contract_ref = _optional_text(spec.get("contract_ref"))
    if contract_ref is None:
        return
    contract_key = NodeKey("contract_surface", contract_ref)
    if contract_key in snapshot.nodes:
        snapshot.add_relation(
            surface, "DEPENDS_ON", contract_key, provenance="runtime_evidence"
        )


def _link_run_instance_documents(
    snapshot: GraphSnapshot,
    surface: NodeKey,
    spec: dict[str, object],
) -> None:
    for doc_key in _run_instance_doc_targets(spec):
        if doc_key in snapshot.nodes:
            snapshot.add_relation(
                surface, "DESCRIBED_IN", doc_key, provenance="runtime_evidence"
            )


def _link_run_instance_artifacts(
    snapshot: GraphSnapshot,
    surface: NodeKey,
    spec: dict[str, object],
) -> None:
    for artifact_key in _run_instance_artifact_targets(spec):
        if artifact_key in snapshot.nodes:
            snapshot.add_relation(
                surface,
                "REFERENCES_ARTIFACT",
                artifact_key,
                provenance="runtime_evidence",
            )


def _run_instance_doc_targets(spec: dict[str, object]) -> tuple[NodeKey, ...]:
    targets: list[NodeKey] = []
    source_path = _optional_text(spec.get("source_path"))
    if source_path is not None:
        targets.append(NodeKey("test_artifact", source_path))
    targets.extend(
        NodeKey("doc_artifact", str(doc_path))
        for doc_path in _as_iterable(spec.get("doc_paths"))
    )
    return tuple(targets)


def _run_instance_artifact_targets(spec: dict[str, object]) -> tuple[NodeKey, ...]:
    return tuple(
        NodeKey("control_plane_artifact_surface", str(artifact_name))
        for artifact_name in _as_iterable(spec.get("artifact_refs"))
    )


def _runtime_state_specs() -> tuple[dict[str, object], ...]:
    return (
        {
            "name": "manifest-left::active-window",
            "manifest_id": "manifest-left",
            "state_kind": "active_run",
            "state_status": "in_progress",
            "retry_count": 0,
            "lock_key": "pipeline:chembl_activity:run",
            "lock_scope": "pipeline_execution",
            "owner_hint": "run_manifest_service",
            "workflow_name": "tests",
            "artifact_refs": (RUN_MANIFEST_ARTIFACT_REF, EFFECTIVE_CONFIG_ARTIFACT_REF),
            "runtime_evidence_refs": ("run_manifest", "effective_config_artifact"),
            "doc_paths": (RUN_MANIFEST_INSPECTION_DOC_PATH,),
        },
        {
            "name": "manifest-chain-2::retry-window",
            "manifest_id": "manifest-chain-2",
            "state_kind": "retry_state",
            "state_status": "retrying",
            "retry_count": 1,
            "retry_strategy": "resume_failed_only",
            "workflow_name": "tests",
            "artifact_refs": (RUN_LEDGER_ARTIFACT_REF, EFFECTIVE_CONFIG_ARTIFACT_REF),
            "runtime_evidence_refs": ("run_ledger", "effective_config_artifact"),
            "doc_paths": (RUN_MANIFEST_LEDGER_DOC_PATH,),
        },
        {
            "name": "chembl_activity::composite-lock",
            "manifest_id": "manifest-composite-quarantine",
            "state_kind": "lock_state",
            "state_status": "locked",
            "retry_count": 0,
            "lock_key": "composite:activity:cross_validation",
            "lock_scope": "cross_validation_quarantine",
            "owner_hint": "workflow_lock_service",
            "workflow_name": "tests",
            "artifact_refs": (RUN_LEDGER_ARTIFACT_REF,),
            "runtime_evidence_refs": ("run_ledger",),
            "doc_paths": (TRACEABILITY_SIGNAL_OWNERSHIP_DOC_PATH,),
        },
    )


def _add_runtime_state_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
    spec: dict[str, object],
) -> NodeKey:
    state = snapshot.add_node(
        "runtime_state_surface",
        str(spec["name"]),
        summary=f"Deterministic runtime state surface `{spec['name']}`.",
        **_runtime_state_properties(spec),
        source_kind="runtime_state_surface",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(
        project, "HAS_RUNTIME_STATE", state, provenance="runtime_state"
    )
    return state


def _link_runtime_state_surface(
    snapshot: GraphSnapshot,
    state: NodeKey,
    spec: dict[str, object],
) -> None:
    _link_runtime_state_run_and_pipeline(snapshot, state, spec)
    _link_runtime_state_dependencies(snapshot, state, spec)
    _link_runtime_state_evidence_materials(snapshot, state, spec)


def _link_runtime_state_run_and_pipeline(
    snapshot: GraphSnapshot,
    state: NodeKey,
    spec: dict[str, object],
) -> None:
    manifest_id = _optional_text(spec.get("manifest_id"))
    if manifest_id is not None:
        run_key = NodeKey("run_instance_surface", manifest_id)
        if run_key in snapshot.nodes:
            snapshot.add_relation(
                run_key, "HAS_RUNTIME_STATE", state, provenance="runtime_state"
            )
            pipeline_name = _optional_text(
                snapshot.nodes[run_key].properties.get("pipeline_name")
            )
            if pipeline_name is not None:
                pipeline_key = NodeKey("pipeline_surface", pipeline_name)
                if pipeline_key in snapshot.nodes:
                    snapshot.add_relation(
                        state, "DEPENDS_ON", pipeline_key, provenance="runtime_state"
                    )


def _link_runtime_state_dependencies(
    snapshot: GraphSnapshot,
    state: NodeKey,
    spec: dict[str, object],
) -> None:
    _link_runtime_state_workflow_dependency(snapshot, state, spec)
    _link_runtime_state_evidence_dependencies(snapshot, state, spec)


def _runtime_state_properties(spec: dict[str, object]) -> dict[str, object]:
    return {
        "manifest_id": _optional_text(spec.get("manifest_id")),
        "state_kind": _optional_text(spec.get("state_kind")),
        "state_status": _optional_text(spec.get("state_status")),
        "retry_count": _coerce_int(spec["retry_count"])
        if isinstance(spec.get("retry_count"), int)
        else None,
        "retry_strategy": _optional_text(spec.get("retry_strategy")),
        "lock_key": _optional_text(spec.get("lock_key")),
        "lock_scope": _optional_text(spec.get("lock_scope")),
        "owner_hint": _optional_text(spec.get("owner_hint")),
        "workflow_name": _optional_text(spec.get("workflow_name")),
    }


def _link_runtime_state_workflow_dependency(
    snapshot: GraphSnapshot,
    state: NodeKey,
    spec: dict[str, object],
) -> None:
    workflow_name = _optional_text(spec.get("workflow_name"))
    if workflow_name is None:
        return
    workflow_key = NodeKey("workflow_surface", workflow_name)
    if workflow_key in snapshot.nodes:
        snapshot.add_relation(
            state, "DEPENDS_ON", workflow_key, provenance="runtime_state"
        )


def _link_runtime_state_evidence_dependencies(
    snapshot: GraphSnapshot,
    state: NodeKey,
    spec: dict[str, object],
) -> None:
    for evidence_name in _as_iterable(spec.get("runtime_evidence_refs")):
        evidence_key = NodeKey("runtime_evidence_surface", str(evidence_name))
        if evidence_key in snapshot.nodes:
            snapshot.add_relation(
                state, "DEPENDS_ON", evidence_key, provenance="runtime_state"
            )


def _link_runtime_state_evidence_materials(
    snapshot: GraphSnapshot,
    state: NodeKey,
    spec: dict[str, object],
) -> None:
    for artifact_key in _runtime_state_artifact_targets(spec):
        if artifact_key in snapshot.nodes:
            snapshot.add_relation(
                state, "REFERENCES_ARTIFACT", artifact_key, provenance="runtime_state"
            )
    for doc_key in _runtime_state_doc_targets(spec):
        if doc_key in snapshot.nodes:
            snapshot.add_relation(
                state, "DESCRIBED_IN", doc_key, provenance="runtime_state"
            )


def _runtime_state_artifact_targets(spec: dict[str, object]) -> tuple[NodeKey, ...]:
    return tuple(
        NodeKey("control_plane_artifact_surface", str(artifact_name))
        for artifact_name in _as_iterable(spec.get("artifact_refs"))
    )


def _runtime_state_doc_targets(spec: dict[str, object]) -> tuple[NodeKey, ...]:
    return tuple(
        NodeKey("doc_artifact", str(doc_path))
        for doc_path in _as_iterable(spec.get("doc_paths"))
    )


def _add_control_plane_run_instance_surfaces(
    snapshot: GraphSnapshot,
    _root: Path,
    project: NodeKey,
    today: str,
) -> None:
    _add_run_instance_spec_surfaces(snapshot, project, today)
    _add_runtime_state_surfaces(snapshot, project, today)


def _add_run_instance_spec_surfaces(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
) -> None:
    for spec in _control_plane_run_instance_specs():
        surface = _add_run_instance_surface(snapshot, project, today, spec)
        _link_run_instance_surface(snapshot, surface, spec)


def _add_runtime_state_surfaces(
    snapshot: GraphSnapshot, project: NodeKey, today: str
) -> None:
    _add_runtime_state_spec_surfaces(snapshot, project, today)


def _add_runtime_state_spec_surfaces(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
) -> None:
    for spec in _runtime_state_specs():
        state = _add_runtime_state_surface(snapshot, project, today, spec)
        _link_runtime_state_surface(snapshot, state, spec)


def _workflow_script_targets(run_text: str) -> set[NodeKey]:
    targets: set[NodeKey] = set()
    targets.update(_workflow_module_script_targets(run_text))
    targets.update(_workflow_repo_path_targets(run_text))
    return targets


def _workflow_module_script_targets(run_text: str) -> tuple[NodeKey, ...]:
    module_pattern = re.compile(
        r"(?:uv\s+run\s+)?python(?:3)?\s+-m\s+scripts\.([\w.]+)"
    )
    return tuple(
        NodeKey(
            "script_surface", f"scripts/{match.group(1).replace('.', '/')}/{MAIN_PY}"
        )
        for match in module_pattern.finditer(run_text)
    )


def _workflow_repo_path_targets(run_text: str) -> tuple[NodeKey, ...]:
    path_pattern = re.compile(
        r"(?<![\w./-])((?:scripts|tests|configs|src|docs|grafana|\.github)/[\w./-]+)"
    )
    targets: list[NodeKey] = []
    for match in path_pattern.finditer(run_text):
        candidate = match.group(1).rstrip(".,:)")
        targets.extend(
            (
                NodeKey("script_surface", candidate),
                NodeKey("file_surface", candidate),
                NodeKey("directory_surface", candidate),
            )
        )
    return tuple(targets)


def _workflow_quality_gates(run_text: str) -> tuple[str, ...]:
    lowered = run_text.lower()
    gates: list[str] = []
    for predicate, gate_name in _WORKFLOW_GATE_RULES:
        if predicate(lowered):
            gates.append(gate_name)
    return tuple(dict.fromkeys(gates))


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


_WORKFLOW_GATE_RULES: tuple[tuple[Callable[[str], bool], str], ...] = (
    (lambda text: "pytest" in text, "pytest"),
    (lambda text: "mypy" in text, GATE_MYPY_STRICT),
    (
        lambda text: _contains_any(
            text, ("scripts.docs", "check-links", "build_docs_site.sh")
        ),
        GATE_DOCS_VERIFICATION,
    ),
    (
        lambda text: _contains_any(
            text,
            ("validate_pipeline_configs", "scripts.schema", "check_config_invariants"),
        ),
        GATE_CONFIG_VALIDATION,
    ),
    (lambda text: "neo4j-memory" in text, GATE_NEO4J_ONTOLOGY_INVARIANTS),
)


def _workflow_family(workflow_name: str, title: str) -> str:
    lowered = f"{workflow_name} {title}".lower()
    for family_name, needles in _WORKFLOW_FAMILY_RULES:
        if _contains_any(lowered, needles):
            return family_name
    return "test"


_WORKFLOW_FAMILY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("release", ("release", "publish")),
    ("docs", ("docs", "doc")),
    ("governance", ("governance", "schema", "quality")),
    ("docker", ("docker",)),
)


def _workflow_on_payload(payload: dict[str, object]) -> object:
    if "on" in payload:
        return payload.get("on")
    return cast(dict[object, object], payload).get(True)


def _workflow_trigger_names(payload: dict[str, object]) -> tuple[str, ...]:
    trigger_payload = _workflow_on_payload(payload)
    if isinstance(trigger_payload, str):
        return (trigger_payload,)
    if isinstance(trigger_payload, list):
        return _sorted_string_items(trigger_payload)
    if isinstance(trigger_payload, dict):
        return _sorted_string_items(trigger_payload.keys())
    return ()


def _workflow_environment_name(job_payload: dict[str, object]) -> str | None:
    environment_payload = job_payload.get("environment")
    if isinstance(environment_payload, str):
        return environment_payload
    return _workflow_environment_mapping_name(environment_payload)


def _workflow_environment_mapping_name(environment_payload: object) -> str | None:
    if not isinstance(environment_payload, dict):
        return None
    name = environment_payload.get("name")
    return name if isinstance(name, str) else None


def _sorted_string_items(items: Iterable[object]) -> tuple[str, ...]:
    return tuple(sorted(str(item) for item in items if isinstance(item, str)))


def _workflow_matrix_axes(job_payload: dict[str, object]) -> tuple[str, ...]:
    matrix_payload = _workflow_matrix_payload(job_payload)
    if not isinstance(matrix_payload, dict):
        return ()
    return tuple(
        sorted(
            _normalize_workflow_matrix_axis_name(str(key))
            for key in matrix_payload
            if key not in {"include", "exclude"}
        )
    )


def _normalize_workflow_matrix_axis_name(axis_name: str) -> str:
    """Stabilize workflow matrix axis names across workflow refactors."""
    if axis_name == "test-group":
        return "suite"
    return axis_name


def _workflow_matrix_variants(
    job_payload: dict[str, object],
) -> tuple[dict[str, str], ...]:
    matrix_payload = _workflow_matrix_payload(job_payload)
    if not isinstance(matrix_payload, dict):
        return ()

    base_axes = _workflow_matrix_base_axes(matrix_payload)
    if base_axes is None or not base_axes:
        return ()
    return _workflow_matrix_variants_with_includes(
        base_axes, matrix_payload.get("include")
    )


def _workflow_matrix_payload(job_payload: dict[str, object]) -> object:
    strategy_payload = job_payload.get("strategy")
    if not isinstance(strategy_payload, dict):
        return None
    return strategy_payload.get("matrix")


def _workflow_matrix_variants_with_includes(
    base_axes: list[tuple[str, list[str]]],
    include_payload: object,
) -> tuple[dict[str, str], ...]:
    variants = _workflow_matrix_base_variants(base_axes)
    _append_workflow_matrix_include_variants(variants, include_payload)
    return tuple(variants)


def _workflow_matrix_base_axes(
    matrix_payload: dict[str, object],
) -> list[tuple[str, list[str]]] | None:
    base_axes: list[tuple[str, list[str]]] = []
    for axis_name, axis_values in matrix_payload.items():
        if axis_name in {"include", "exclude"}:
            continue
        normalized = _workflow_matrix_axis_values(axis_values)
        if not normalized:
            return None
        normalized_axis_name = _normalize_workflow_matrix_axis_name(str(axis_name))
        base_axes.append((normalized_axis_name, normalized))
    return base_axes


def _workflow_matrix_axis_values(axis_values: object) -> list[str]:
    if isinstance(axis_values, list):
        return [
            str(item.get("name"))
            if isinstance(item, dict) and item.get("name") is not None
            else str(item)
            for item in axis_values
        ]
    return [str(axis_values)]


def _workflow_matrix_base_variants(
    base_axes: list[tuple[str, list[str]]],
) -> list[dict[str, str]]:
    variants: list[dict[str, str]] = []
    axis_names = [axis_name for axis_name, _ in base_axes]
    axis_values_product = itertools.product(*(values for _, values in base_axes))
    for values in axis_values_product:
        variants.append(dict(zip(axis_names, values, strict=False)))
        if len(variants) >= 16:
            break
    return variants


def _append_workflow_matrix_include_variants(
    variants: list[dict[str, str]],
    include_payload: object,
) -> None:
    if not isinstance(include_payload, list):
        return
    for include_item in include_payload:
        if not isinstance(include_item, dict):
            continue
        include_variant = {str(key): str(value) for key, value in include_item.items()}
        if include_variant and include_variant not in variants:
            variants.append(include_variant)
            if len(variants) >= 16:
                break


def _workflow_secret_refs(payload: object) -> tuple[str, ...]:
    secret_pattern = re.compile(r"secrets\.(\w+)")
    found: set[str] = set()

    def _visit(value: object) -> None:
        if isinstance(value, str):
            for match in secret_pattern.finditer(value):
                found.add(match.group(1))
            return
        if isinstance(value, dict):
            for nested in value.values():
                _visit(nested)
            return
        if isinstance(value, list):
            for nested in value:
                _visit(nested)

    _visit(payload)
    return tuple(sorted(found))


def _workflow_action_key(uses_ref: str) -> str:
    return uses_ref.split("@", 1)[0]


def _workflow_reusable_target(uses_ref: str) -> tuple[str | None, str]:
    normalized = _workflow_action_key(uses_ref)
    if normalized.startswith(f"./{GITHUB_WORKFLOWS_PREFIX}"):
        return Path(normalized).stem, "local_reusable_workflow"
    if GITHUB_WORKFLOWS_PREFIX in normalized:
        workflow_name = Path(normalized.split(GITHUB_WORKFLOWS_PREFIX, 1)[1]).stem
        return workflow_name, "remote_reusable_workflow"
    return None, "github_action"


def _workflow_output_specs(
    workflow_name: str,
    owner_name: str,
    outputs_payload: object,
    *,
    scope: str,
) -> tuple[tuple[str, str | None], ...]:
    if not isinstance(outputs_payload, dict):
        return ()
    return tuple(
        (
            f"{workflow_name}::{scope}::{owner_name}::{output_name}",
            _workflow_output_expression(output_value),
        )
        for output_name, output_value in outputs_payload.items()
    )


def _workflow_output_expression(output_value: object) -> str | None:
    if isinstance(output_value, str):
        return output_value
    if not isinstance(output_value, dict):
        return None
    raw_value = output_value.get("value")
    if isinstance(raw_value, str):
        return raw_value
    description = output_value.get("description")
    return description if isinstance(description, str) else None


def _workflow_concurrency_group(payload: dict[str, object]) -> str | None:
    concurrency_payload = payload.get("concurrency")
    if isinstance(concurrency_payload, str):
        return concurrency_payload
    if isinstance(concurrency_payload, dict):
        group = concurrency_payload.get("group")
        if isinstance(group, str):
            return group
    return None


def _workflow_artifact_specs(
    workflow_name: str,
    job_id: str,
    step: dict[str, object],
) -> tuple[tuple[str, str, str | None], ...]:
    uses_ref = step.get("uses")
    if not isinstance(uses_ref, str):
        return ()
    normalized_uses = uses_ref.lower()
    if (
        "upload-artifact" not in normalized_uses
        and "download-artifact" not in normalized_uses
    ):
        return ()
    relation_type = (
        "PUBLISHES_ARTIFACT" if "upload-artifact" in normalized_uses else "DEPENDS_ON"
    )
    with_payload = step.get("with")
    artifact_name = None
    artifact_path = None
    if isinstance(with_payload, dict):
        raw_name = with_payload.get("name")
        if isinstance(raw_name, str):
            artifact_name = raw_name
        raw_path = with_payload.get("path")
        if isinstance(raw_path, str):
            artifact_path = raw_path
    if artifact_name is None:
        step_name = step.get("name")
        artifact_name = (
            step_name
            if isinstance(step_name, str) and step_name
            else f"{job_id}-artifact"
        )
    return ((f"{workflow_name}::{artifact_name}", relation_type, artifact_path),)


def _normalize_cli_command_name(raw_command: str) -> str | None:
    lowered = raw_command.lower()
    if " -m bioetl " in lowered:
        match = re.search(r"-m\s+bioetl\s+([\w-]+)", raw_command)
        if match:
            return f"bioetl {match.group(1)}"
        return "bioetl"
    script_module_match = re.search(
        r"-m\s+scripts\.(\w+)(?:\s+([\w.-]+))?", raw_command
    )
    if script_module_match:
        module_name = script_module_match.group(1)
        subcommand = script_module_match.group(2)
        if subcommand and not subcommand.startswith("-"):
            return f"scripts.{module_name} {subcommand}"
        return f"scripts.{module_name}"
    script_path_match = re.search(r"scripts/(\w+)/([\w.-]+)", raw_command)
    if script_path_match:
        return f"scripts.{script_path_match.group(1)} {script_path_match.group(2)}"
    return None


def _extract_cli_options(raw_command: str) -> tuple[str, ...]:
    options = re.findall(r"(?<![\w-])(--[\w][\w-]*)", raw_command)
    return tuple(sorted(dict.fromkeys(options)))


def _cli_side_effect_class(command_name: str) -> str:
    lowered = command_name.lower()
    if any(
        token in lowered
        for token in (
            " check",
            " lint",
            " verify",
            "validate",
            "status",
            "show",
            "list",
        )
    ):
        return "read_only"
    if any(
        token in lowered
        for token in ("run", "sync", "generate", "update", "write", "create", "cleanup")
    ):
        return "mutating"
    return "mixed"


def _claim_modality(text: str) -> str:
    lowered = text.lower()
    if (
        "must not" in lowered
        or "never" in lowered
        or "forbidden" in lowered
        or "should not" in lowered
    ):
        return "forbidden"
    if "must" in lowered or "required" in lowered or "require" in lowered:
        return "required"
    return "guidance"


def _job_step_counts(steps: object) -> tuple[int, int]:
    if not isinstance(steps, list):
        return 0, 0
    inline_run_step_count = sum(
        1
        for step in steps
        if isinstance(step, dict) and isinstance(step.get("run"), str)
    )
    uses_step_count = sum(
        1
        for step in steps
        if isinstance(step, dict) and isinstance(step.get("uses"), str)
    )
    return inline_run_step_count, uses_step_count


def _add_workflow_surface(
    snapshot: GraphSnapshot,
    *,
    workflow_name: str,
    title: str,
    relative_path: str,
    today: str,
) -> WorkflowContext:
    workflow = snapshot.add_node(
        "workflow_surface",
        workflow_name,
        summary=f"GitHub Actions workflow `{title}`.",
        source_path=relative_path,
        source_kind="github_actions_workflow",
        workflow_title=title,
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    return WorkflowContext(
        workflow_name=workflow_name,
        title=title,
        relative_path=relative_path,
        today=today,
        workflow=workflow,
    )


def _attach_workflow_file_backing(
    snapshot: GraphSnapshot, workflow: NodeKey, relative_path: str
) -> None:
    parent_dir_relative = Path(relative_path).parent.as_posix()
    parent_dir_candidates = {
        parent_dir_relative,
        parent_dir_relative.replace("\\", "/"),
    }
    for candidate in sorted(parent_dir_candidates):
        parent_dir_key = NodeKey("directory_surface", candidate)
        if parent_dir_key in snapshot.nodes:
            snapshot.add_relation(
                parent_dir_key,
                "HOUSES",
                workflow,
                provenance="file_structure",
            )

    file_surface_candidates = {
        relative_path,
        relative_path.replace("\\", "/"),
    }
    for candidate in sorted(file_surface_candidates):
        file_surface_key = NodeKey("file_surface", candidate)
        if file_surface_key in snapshot.nodes:
            snapshot.add_relation(
                file_surface_key,
                "BACKS",
                workflow,
                provenance="workflow_graph",
            )


def _enrich_workflow_surface(
    snapshot: GraphSnapshot,
    context: WorkflowContext,
    payload: dict[str, object],
) -> None:
    snapshot.add_node(
        "workflow_surface",
        context.workflow_name,
        workflow_family=_workflow_family(context.workflow_name, context.title),
        trigger_names=list(_workflow_trigger_names(payload)) or None,
        concurrency_group=_workflow_concurrency_group(payload),
    )


def _add_workflow_call_entrypoint(
    snapshot: GraphSnapshot,
    context: WorkflowContext,
    payload: dict[str, object],
) -> NodeKey | None:
    workflow_call_payload = _workflow_on_payload(payload)
    if not isinstance(workflow_call_payload, dict):
        return None
    reusable_workflow_payload = workflow_call_payload.get("workflow_call")
    if not isinstance(reusable_workflow_payload, dict):
        return None
    workflow_call_entrypoint = snapshot.add_node(
        "workflow_call_surface",
        f"{context.workflow_name}::workflow_call",
        summary=f"Reusable workflow entrypoint for `{context.workflow_name}`.",
        source_path=context.relative_path,
        source_kind="workflow_call_surface",
        workflow=context.workflow_name,
        reusable_kind="workflow_call_trigger",
        last_verified=context.today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(
        context.workflow,
        "CALLS_WORKFLOW",
        workflow_call_entrypoint,
        provenance="workflow_graph",
    )
    snapshot.add_relation(
        workflow_call_entrypoint,
        "DEPENDS_ON",
        context.workflow,
        provenance="workflow_graph",
    )
    _add_workflow_outputs(
        snapshot,
        owner=context.workflow,
        workflow_name=context.workflow_name,
        relative_path=context.relative_path,
        today=context.today,
        owner_id=context.workflow_name,
        output_payload=reusable_workflow_payload.get("outputs"),
        scope="workflow_call_output",
        output_scope="workflow_call",
        summary_template="Reusable workflow output `{output_name}`.",
    )
    return workflow_call_entrypoint


def _add_secret_requirements(
    snapshot: GraphSnapshot,
    owner: NodeKey,
    secret_names: tuple[str, ...],
    *,
    relative_path: str,
    today: str,
) -> None:
    for secret_name in secret_names:
        secret = snapshot.add_node(
            "workflow_secret_surface",
            secret_name,
            summary=f"GitHub Actions secret usage hint `{secret_name}`.",
            source_path=relative_path,
            source_kind="github_actions_secret",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(
            owner, "REQUIRES_SECRET", secret, provenance="workflow_graph"
        )


def _add_workflow_output_surface(
    snapshot: GraphSnapshot,
    *,
    owner: NodeKey,
    output_name: str,
    expression: str | None,
    summary: str,
    relative_path: str,
    workflow_name: str,
    today: str,
    output_scope: str,
    job_id: str | None = None,
) -> None:
    output = snapshot.add_node(
        "workflow_output_surface",
        output_name,
        summary=summary,
        source_path=relative_path,
        source_kind="workflow_output_surface",
        workflow=workflow_name,
        job_id=job_id,
        output_scope=output_scope,
        output_expression=expression,
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(owner, "EMITS_OUTPUT", output, provenance="workflow_graph")


def _add_workflow_outputs(
    snapshot: GraphSnapshot,
    *,
    owner: NodeKey,
    workflow_name: str,
    relative_path: str,
    today: str,
    owner_id: str,
    output_payload: object,
    scope: str,
    output_scope: str,
    summary_template: str,
    job_id: str | None = None,
) -> None:
    for output_name, expression in _workflow_output_specs(
        workflow_name,
        owner_id,
        output_payload,
        scope=scope,
    ):
        _add_workflow_output_surface(
            snapshot,
            owner=owner,
            output_name=output_name,
            expression=expression,
            summary=summary_template.format(output_name=output_name),
            relative_path=relative_path,
            workflow_name=workflow_name,
            today=today,
            output_scope=output_scope,
            job_id=job_id,
        )


def _workflow_job_surface_metadata(
    job_payload: dict[str, object],
) -> tuple[
    int,
    int,
    tuple[str, ...],
    tuple[dict[str, str], ...],
    str | None,
    str | None,
    tuple[str, ...],
]:
    steps = job_payload.get("steps")
    inline_run_step_count, uses_step_count = _job_step_counts(steps)
    secret_usage_hints = _workflow_secret_refs(job_payload)
    matrix_axes = _workflow_matrix_axes(job_payload)
    matrix_variants = _workflow_matrix_variants(job_payload)
    environment_name = _workflow_environment_name(job_payload)
    concurrency_group = _workflow_concurrency_group(job_payload)
    return (
        inline_run_step_count,
        uses_step_count,
        matrix_axes,
        matrix_variants,
        environment_name,
        concurrency_group,
        secret_usage_hints,
    )


def _add_workflow_job_surface(
    snapshot: GraphSnapshot,
    context: WorkflowContext,
    *,
    job_id: str,
    job_payload: dict[str, object],
) -> tuple[WorkflowJobContext, tuple[dict[str, str], ...], tuple[str, ...]]:
    (
        inline_run_step_count,
        uses_step_count,
        matrix_axes,
        matrix_variants,
        environment_name,
        concurrency_group,
        secret_usage_hints,
    ) = _workflow_job_surface_metadata(job_payload)
    job_name = f"{context.workflow_name}::{job_id}"
    job = _create_workflow_job_surface(
        snapshot,
        context,
        job_name=job_name,
        job_id=job_id,
        job_payload=job_payload,
        inline_run_step_count=inline_run_step_count,
        uses_step_count=uses_step_count,
        matrix_axes=matrix_axes,
        matrix_variants=matrix_variants,
        environment_name=environment_name,
        secret_usage_hints=secret_usage_hints,
        concurrency_group=concurrency_group,
    )
    snapshot.add_relation(
        context.workflow, "CONTAINS", job, provenance="workflow_graph"
    )
    return (
        WorkflowJobContext(
            workflow_name=context.workflow_name,
            job_id=job_id,
            job_name=job_name,
            relative_path=context.relative_path,
            today=context.today,
            job=job,
        ),
        matrix_variants,
        secret_usage_hints,
    )


def _create_workflow_job_surface(
    snapshot: GraphSnapshot,
    context: WorkflowContext,
    *,
    job_name: str,
    job_id: str,
    job_payload: dict[str, object],
    inline_run_step_count: int,
    uses_step_count: int,
    matrix_axes: tuple[str, ...],
    matrix_variants: tuple[dict[str, str], ...],
    environment_name: str | None,
    secret_usage_hints: tuple[str, ...],
    concurrency_group: str | None,
) -> NodeKey:
    return snapshot.add_node(
        "workflow_job_surface",
        job_name,
        summary=f"GitHub Actions job `{job_id}` in workflow `{context.title}`.",
        source_path=context.relative_path,
        source_kind="github_actions_job",
        workflow=context.workflow_name,
        job_id=job_id,
        runs_on=str(job_payload.get("runs-on"))
        if job_payload.get("runs-on") is not None
        else None,
        inline_run_step_count=inline_run_step_count,
        uses_step_count=uses_step_count,
        matrix_axes=list(matrix_axes) if matrix_axes else None,
        matrix_variant_count=len(matrix_variants) if matrix_variants else None,
        environment_name=environment_name,
        secret_usage_hints=list(secret_usage_hints) if secret_usage_hints else None,
        concurrency_group=concurrency_group,
        last_verified=context.today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )


def _add_workflow_action_surface(
    snapshot: GraphSnapshot,
    context: WorkflowJobContext,
    *,
    action_key: str,
    uses_ref: str,
    summary: str,
) -> NodeKey:
    action = snapshot.add_node(
        "workflow_action_surface",
        action_key,
        summary=summary,
        source_path=context.relative_path,
        source_kind="github_actions_uses",
        uses_ref=uses_ref,
        last_verified=context.today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(
        context.job, "USES_ACTION", action, provenance="workflow_graph"
    )
    return action


def _link_reusable_job_workflow(
    snapshot: GraphSnapshot,
    workflow_nodes: dict[str, NodeKey],
    workflow_name_by_relative_path: dict[str, str],
    context: WorkflowJobContext,
    reusable_workflow_ref: str,
) -> None:
    action_key = _workflow_action_key(reusable_workflow_ref)
    target_workflow_name, reusable_kind = _workflow_reusable_target(
        reusable_workflow_ref
    )
    _add_workflow_action_surface(
        snapshot,
        context,
        action_key=action_key,
        uses_ref=reusable_workflow_ref,
        summary=f"Workflow action or reusable workflow `{action_key}`.",
    )
    if target_workflow_name is None:
        return
    workflow_call = snapshot.add_node(
        "workflow_call_surface",
        f"{context.job_name}::{action_key}",
        summary=f"Reusable workflow call `{action_key}` from job `{context.job_name}`.",
        source_path=context.relative_path,
        source_kind="workflow_call_surface",
        workflow=context.workflow_name,
        job_id=context.job_id,
        uses_ref=reusable_workflow_ref,
        reusable_kind=reusable_kind,
        target_workflow=target_workflow_name,
        last_verified=context.today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(
        context.job, "CALLS_WORKFLOW", workflow_call, provenance="workflow_graph"
    )
    target_key = _reusable_target_workflow_key(
        workflow_nodes,
        workflow_name_by_relative_path,
        reusable_workflow_ref,
        target_workflow_name,
    )
    if target_key is not None:
        snapshot.add_relation(
            workflow_call, "DEPENDS_ON", target_key, provenance="workflow_graph"
        )


def _reusable_target_workflow_key(
    workflow_nodes: dict[str, NodeKey],
    workflow_name_by_relative_path: dict[str, str],
    reusable_workflow_ref: str,
    target_workflow_name: str,
) -> NodeKey | None:
    target_key = workflow_nodes.get(target_workflow_name)
    if target_key is not None:
        return target_key
    local_relative_path = _workflow_action_key(reusable_workflow_ref).removeprefix("./")
    target_workflow = workflow_name_by_relative_path.get(local_relative_path)
    if target_workflow is None:
        return None
    return workflow_nodes.get(target_workflow)


def _add_job_matrix_variants(
    snapshot: GraphSnapshot,
    context: WorkflowJobContext,
    matrix_variants: tuple[dict[str, str], ...],
) -> None:
    for variant_payload in matrix_variants:
        variant_name = ", ".join(
            f"{axis}={value}" for axis, value in sorted(variant_payload.items())
        )
        matrix_variant = snapshot.add_node(
            "workflow_matrix_variant_surface",
            f"{context.job_name}[{variant_name}]",
            summary=f"Expanded matrix variant `{variant_name}` for workflow job `{context.job_name}`.",
            source_path=context.relative_path,
            source_kind="workflow_matrix_variant_surface",
            workflow=context.workflow_name,
            job_id=context.job_id,
            variant_axes=variant_payload,
            last_verified=context.today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(
            context.job,
            "HAS_MATRIX_VARIANT",
            matrix_variant,
            provenance="workflow_graph",
        )


def _add_job_outputs(
    snapshot: GraphSnapshot,
    context: WorkflowJobContext,
    output_payload: object,
) -> None:
    _add_workflow_outputs(
        snapshot,
        owner=context.job,
        workflow_name=context.workflow_name,
        relative_path=context.relative_path,
        today=context.today,
        owner_id=context.job_id,
        output_payload=output_payload,
        scope="job_output",
        output_scope="job",
        summary_template="Workflow output `{output_name}`.",
        job_id=context.job_id,
    )


def _process_workflow_steps(
    snapshot: GraphSnapshot,
    context: WorkflowJobContext,
    steps: object,
) -> None:
    if not isinstance(steps, list):
        return
    for step in steps:
        if not isinstance(step, dict):
            continue
        uses_ref = step.get("uses")
        if isinstance(uses_ref, str):
            _process_workflow_uses_step(snapshot, context, uses_ref, step)
        run_text = step.get("run")
        if not isinstance(run_text, str):
            continue
        _link_workflow_run_targets(snapshot, context, run_text)
        _add_secret_requirements(
            snapshot,
            context.job,
            _workflow_secret_refs(step),
            relative_path=context.relative_path,
            today=context.today,
        )


def _process_workflow_uses_step(
    snapshot: GraphSnapshot,
    context: WorkflowJobContext,
    uses_ref: str,
    step: dict[str, object],
) -> None:
    action_key = _workflow_action_key(uses_ref)
    _add_workflow_action_surface(
        snapshot,
        context,
        action_key=action_key,
        uses_ref=uses_ref,
        summary=f"Workflow action `{action_key}`.",
    )
    for artifact_name, artifact_relation, artifact_path in _workflow_artifact_specs(
        context.workflow_name,
        context.job_id,
        step,
    ):
        artifact = snapshot.add_node(
            "workflow_artifact_surface",
            artifact_name,
            summary=f"Workflow artifact `{artifact_name}`.",
            source_path=context.relative_path,
            source_kind="github_actions_artifact",
            artifact_path=artifact_path,
            workflow=context.workflow_name,
            last_verified=context.today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(
            context.job, artifact_relation, artifact, provenance="workflow_graph"
        )


def _link_workflow_run_targets(
    snapshot: GraphSnapshot,
    context: WorkflowJobContext,
    run_text: str,
) -> None:
    for target in sorted(
        _workflow_script_targets(run_text), key=lambda item: (item.label, item.name)
    ):
        if target in snapshot.nodes:
            snapshot.add_relation(
                context.job, "RUNS_VIA", target, provenance="workflow_graph"
            )
    for gate_name in _workflow_quality_gates(run_text):
        gate_key = NodeKey("quality_gate", gate_name)
        if gate_key in snapshot.nodes:
            snapshot.add_relation(
                context.job, "EXECUTES_GATE", gate_key, provenance="workflow_graph"
            )


def _link_workflow_job_dependencies(
    snapshot: GraphSnapshot,
    workflow_name: str,
    jobs: dict[str, object],
    job_nodes: dict[tuple[str, str], NodeKey],
) -> None:
    for job_id, job_payload in jobs.items():
        if not isinstance(job_payload, dict):
            continue
        job = job_nodes.get((workflow_name, str(job_id)))
        if job is None:
            continue
        for dependency_id in _workflow_job_dependency_ids(job_payload):
            dependency_key = job_nodes.get((workflow_name, dependency_id))
            if dependency_key is not None:
                snapshot.add_relation(
                    job, "DEPENDS_ON", dependency_key, provenance="workflow_graph"
                )


def _workflow_job_dependency_ids(job_payload: dict[str, object]) -> tuple[str, ...]:
    needs_payload = job_payload.get("needs")
    if isinstance(needs_payload, str):
        return (needs_payload,)
    if isinstance(needs_payload, list):
        return tuple(str(item) for item in needs_payload if isinstance(item, str))
    return ()


def _add_ci_workflow_graph(
    snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str
) -> None:
    workflows_root = root / GITHUB_DIR / "workflows"
    if not workflows_root.is_dir():
        return

    workflow_files = _workflow_graph_files(workflows_root)
    workflow_name_by_relative_path = {
        _rel_path(root, workflow_path): workflow_path.stem
        for workflow_path in workflow_files
    }
    workflow_nodes: dict[str, NodeKey] = {}
    job_nodes: dict[tuple[str, str], NodeKey] = {}
    for workflow_path in workflow_files:
        _process_workflow_file(
            snapshot,
            root,
            project,
            today,
            workflow_path,
            workflow_nodes=workflow_nodes,
            workflow_name_by_relative_path=workflow_name_by_relative_path,
            job_nodes=job_nodes,
        )


def _workflow_graph_files(workflows_root: Path) -> list[Path]:
    return sorted(workflows_root.glob("*.y*ml"))


def _process_workflow_file(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    workflow_path: Path,
    *,
    workflow_nodes: dict[str, NodeKey],
    workflow_name_by_relative_path: dict[str, str],
    job_nodes: dict[tuple[str, str], NodeKey],
) -> None:
    workflow_name, payload, context, workflow_call_entrypoint = (
        _add_workflow_file_surface(
            snapshot,
            root,
            project,
            today,
            workflow_path,
        )
    )
    workflow_nodes[workflow_name] = context.workflow
    jobs = payload.get("jobs")
    if not isinstance(jobs, dict):
        return
    _add_workflow_jobs(
        snapshot,
        context=context,
        jobs=jobs,
        workflow_nodes=workflow_nodes,
        workflow_name_by_relative_path=workflow_name_by_relative_path,
        workflow_call_entrypoint=workflow_call_entrypoint,
        job_nodes=job_nodes,
    )


def _add_workflow_file_surface(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    workflow_path: Path,
) -> tuple[str, dict[str, object], WorkflowContext, NodeKey | None]:
    payload = _read_yaml(workflow_path)
    workflow_name = workflow_path.stem
    title_value = payload.get("name")
    title = title_value if isinstance(title_value, str) else workflow_name
    relative_path = _rel_path(root, workflow_path)
    context = _add_workflow_surface(
        snapshot,
        workflow_name=workflow_name,
        title=title,
        relative_path=relative_path,
        today=today,
    )
    _enrich_workflow_surface(snapshot, context, payload)
    snapshot.add_relation(
        project, "HAS_WORKFLOW", context.workflow, provenance="workflow_graph"
    )
    _attach_workflow_file_backing(snapshot, context.workflow, relative_path)
    workflow_call_entrypoint = _add_workflow_call_entrypoint(snapshot, context, payload)
    return workflow_name, payload, context, workflow_call_entrypoint


def _add_workflow_jobs(
    snapshot: GraphSnapshot,
    *,
    context: WorkflowContext,
    jobs: dict[object, object],
    workflow_nodes: dict[str, NodeKey],
    workflow_name_by_relative_path: dict[str, str],
    workflow_call_entrypoint: NodeKey | None,
    job_nodes: dict[tuple[str, str], NodeKey],
) -> None:
    for job_id, job_payload in jobs.items():
        if not isinstance(job_payload, dict):
            continue
        _process_workflow_job(
            snapshot,
            context=context,
            job_id=str(job_id),
            job_payload=job_payload,
            workflow_nodes=workflow_nodes,
            workflow_name_by_relative_path=workflow_name_by_relative_path,
            workflow_call_entrypoint=workflow_call_entrypoint,
            job_nodes=job_nodes,
        )
    _link_workflow_job_dependencies(
        snapshot,
        context.workflow_name,
        {str(key): value for key, value in jobs.items()},
        job_nodes,
    )


def _process_workflow_job(
    snapshot: GraphSnapshot,
    *,
    context: WorkflowContext,
    job_id: str,
    job_payload: dict[str, object],
    workflow_nodes: dict[str, NodeKey],
    workflow_name_by_relative_path: dict[str, str],
    workflow_call_entrypoint: NodeKey | None,
    job_nodes: dict[tuple[str, str], NodeKey],
) -> None:
    job_context, matrix_variants, secret_usage_hints = _add_workflow_job_surface(
        snapshot,
        context,
        job_id=job_id,
        job_payload=job_payload,
    )
    _register_workflow_job(
        snapshot,
        context=context,
        job_id=job_id,
        job_context=job_context,
        workflow_call_entrypoint=workflow_call_entrypoint,
        job_nodes=job_nodes,
    )
    _populate_workflow_job_surface(
        snapshot,
        workflow_nodes=workflow_nodes,
        workflow_name_by_relative_path=workflow_name_by_relative_path,
        job_context=job_context,
        job_payload=job_payload,
        matrix_variants=matrix_variants,
        secret_usage_hints=secret_usage_hints,
    )


def _register_workflow_job(
    snapshot: GraphSnapshot,
    *,
    context: WorkflowContext,
    job_id: str,
    job_context: WorkflowJobContext,
    workflow_call_entrypoint: NodeKey | None,
    job_nodes: dict[tuple[str, str], NodeKey],
) -> None:
    job_nodes[(context.workflow_name, job_id)] = job_context.job
    if workflow_call_entrypoint is not None:
        snapshot.add_relation(
            job_context.job,
            "CALLS_WORKFLOW",
            workflow_call_entrypoint,
            provenance="workflow_graph",
        )


def _populate_workflow_job_surface(
    snapshot: GraphSnapshot,
    *,
    workflow_nodes: dict[str, NodeKey],
    workflow_name_by_relative_path: dict[str, str],
    job_context: WorkflowJobContext,
    job_payload: dict[str, object],
    matrix_variants: tuple[dict[str, str], ...],
    secret_usage_hints: tuple[str, ...],
) -> None:
    _link_workflow_job_reusable_target(
        snapshot,
        workflow_nodes,
        workflow_name_by_relative_path,
        job_context,
        job_payload.get("uses"),
    )
    _add_secret_requirements(
        snapshot,
        job_context.job,
        secret_usage_hints,
        relative_path=job_context.relative_path,
        today=job_context.today,
    )
    _add_job_matrix_variants(snapshot, job_context, matrix_variants)
    _add_job_outputs(snapshot, job_context, job_payload.get("outputs"))
    _process_workflow_steps(snapshot, job_context, job_payload.get("steps"))


def _normalize_docs_repo_reference(raw_ref: str) -> str | None:
    candidate = _trim_docs_reference_candidate(raw_ref)
    if not candidate:
        return None
    candidate = _normalize_docs_glob_candidate(candidate)
    candidate = candidate.rstrip("/")
    if candidate in {"README.md", "mkdocs.yml"}:
        return candidate
    if any(candidate.startswith(prefix) for prefix in _DOCS_REFERENCE_ALLOWED_PREFIXES):
        return candidate
    return None


_DOCS_REFERENCE_ALLOWED_PREFIXES = (
    "src/",
    "configs/",
    "scripts/",
    "tests/",
    "docs/",
    "grafana/",
    GITHUB_PATH_PREFIX,
)

_DOC_LIKE_LABELS = {"doc_source_surface", "doc_artifact", "policy_surface"}
_DOCS_DRIFT_TEXT_EXTENSIONS = {".md", ".rst", ".txt", YAML_SUFFIX, ".yml"}
_DOCS_DRIFT_EXCLUDED_PREFIXES = (
    ".github/ISSUES",
    ".github/ISSUE_TEMPLATE",
    ".github/actions",
    ".github/workflows",
    "docs/00-project/ai",
    "docs/02-architecture/diagrams/descriptions",
    "docs/reports/evidence",
    "docs/reports",
)


def _is_docs_drift_source_candidate(node: GraphNode) -> bool:
    """Return whether a doc-like node should be parsed for docs-code drift.

    File-structure ingestion creates one ``doc_artifact`` per tracked document.
    Parsing all of them turns snapshot invariants into a root-wide filesystem
    scan on mounted Windows/WSL checkouts. Curated docs and policy surfaces are
    the supported drift sources; file-structure artifacts remain represented in
    the graph through ``HAS_DOC_ARTIFACT``/``BACKED_BY`` edges.
    """
    if node.key.label != "doc_artifact":
        return True
    return "repo_zone" not in node.properties


def _trim_docs_reference_candidate(raw_ref: str) -> str:
    return raw_ref.strip().strip("`").rstrip(".,:;)]}")


def _normalize_docs_glob_candidate(candidate: str) -> str:
    if candidate.endswith("/**"):
        return candidate[: -len("/**")]
    if "/*." in candidate:
        return candidate.rsplit("/", 1)[0]
    if candidate.endswith("/*"):
        return candidate[: -len("/*")]
    return candidate


def _heading_anchor_slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "section"


def _markdown_heading_context(text: str, offset: int) -> tuple[str | None, str | None]:
    current_title: str | None = None
    current_anchor: str | None = None
    for line_start, title in _markdown_headings(text):
        if line_start > offset:
            break
        current_title = title
        current_anchor = _heading_anchor_slug(current_title)
    return current_title, current_anchor


def _markdown_headings(text: str) -> Iterator[tuple[int, str]]:
    offset = 0
    for raw_line in text.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        stripped = line.lstrip(" \t")
        leading_indent = len(line) - len(stripped)
        if leading_indent > 3 or not stripped.startswith("#"):
            offset += len(raw_line)
            continue

        level = len(stripped) - len(stripped.lstrip("#"))
        if level < 1 or level > 6:
            offset += len(raw_line)
            continue

        if len(stripped) <= level or stripped[level] not in {" ", "\t"}:
            offset += len(raw_line)
            continue

        title = stripped[level:].strip()
        if title:
            yield offset, title
        offset += len(raw_line)


def _resolve_docs_reference_target(
    snapshot: GraphSnapshot,
    ref: str,
) -> tuple[NodeKey | None, str, str]:
    for candidate in _docs_reference_exact_candidates(ref):
        if candidate in snapshot.nodes:
            return candidate, "direct_path", "high"

    for node in tuple(snapshot.nodes.values()):
        source_path = node.properties.get("source_path")
        if isinstance(source_path, str) and source_path == ref:
            return node.key, "source_path_match", "medium"
    return None, "unresolved", "low"


def _docs_reference_exact_candidates(ref: str) -> tuple[NodeKey, ...]:
    return (
        NodeKey("module_surface", ref),
        NodeKey("script_surface", ref),
        NodeKey("test_artifact", ref),
        NodeKey("config_artifact", ref),
        NodeKey(
            "workflow_surface",
            Path(ref).stem if ref.startswith(GITHUB_WORKFLOWS_PREFIX) else ref,
        ),
        NodeKey("cli_command_surface", _normalize_cli_command_name(ref) or ref),
        NodeKey("file_surface", ref),
        NodeKey("directory_surface", ref),
    )


def _resolve_claim_targets(
    snapshot: GraphSnapshot, claim_text: str
) -> tuple[tuple[NodeKey, str, str], ...]:
    resolved: list[tuple[NodeKey, str, str]] = []
    seen: set[NodeKey] = set()
    for token in sorted(_claim_target_tokens(claim_text)):
        normalized_token = PORTS_MODULE_PREFIX if token == "domain.ports" else token
        for candidate in _claim_exact_candidates(normalized_token):
            if candidate in snapshot.nodes and candidate not in seen:
                resolved.append((candidate, "claim_token", "medium"))
                seen.add(candidate)
                break
    return tuple(resolved)


def _claim_target_tokens(claim_text: str) -> set[str]:
    tokens: set[str] = set()
    tokens.update(match.group(1) for match in re.finditer(r"`([^`]+)`", claim_text))
    tokens.update(
        match.group(0) for match in re.finditer(r"\bbioetl\s+[\w-]+\b", claim_text)
    )
    tokens.update(
        match.group(0)
        for match in re.finditer(r"\bscripts\.\w+(?:\s+[\w.-]+)?\b", claim_text)
    )
    tokens.update(
        match.group(0)
        for match in re.finditer(r"\b(?:bioetl|domain)\.[\w.]+\b", claim_text)
    )
    return tokens


def _claim_exact_candidates(normalized_token: str) -> tuple[NodeKey, ...]:
    return (
        NodeKey("port_surface", normalized_token),
        NodeKey("cli_command_surface", normalized_token),
        NodeKey("script_surface", normalized_token),
        NodeKey("module_surface", normalized_token),
        NodeKey("workflow_surface", normalized_token),
        NodeKey("execution_path", normalized_token),
    )


def _add_docs_to_code_drift_edges(snapshot: GraphSnapshot, root: Path) -> None:
    path_pattern = _docs_path_pattern()
    command_pattern = _docs_command_pattern()
    config = _file_structure_config(_load_memory_mapping(root))
    for source_node, source_path, text in _docs_drift_sources(snapshot, root, config):
        _add_doc_path_reference_edges(snapshot, source_node, text, path_pattern)
        _add_doc_command_reference_edges(snapshot, source_node, text, command_pattern)
        _add_doc_claim_edges(snapshot, source_node, source_path, text, path_pattern)


def _is_describes_doc_to_module(relation: GraphRelation) -> bool:
    return (
        relation.relation_type == "DESCRIBES"
        and relation.source.label
        in {"doc_source_surface", "doc_artifact", "policy_surface"}
        and relation.target.label == "module_surface"
    )


def _collect_artifact_source_surfaces(
    snapshot: GraphSnapshot,
) -> dict[NodeKey, list[NodeKey]]:
    artifact_sources: dict[NodeKey, list[NodeKey]] = {}
    for relation in tuple(snapshot.relations.values()):
        if relation.relation_type != "BACKED_BY":
            continue
        if relation.source.label != "doc_source_surface":
            continue
        if relation.target.label != "doc_artifact":
            continue
        artifact_sources.setdefault(relation.target, []).append(relation.source)
    return artifact_sources


def _add_reverse_module_doc_edges(snapshot: GraphSnapshot) -> None:
    for relation in tuple(snapshot.relations.values()):
        if not _is_describes_doc_to_module(relation):
            continue
        snapshot.add_relation(
            relation.target,
            "DESCRIBED_IN",
            relation.source,
            provenance="docs_code_drift_reverse",
            confidence=relation.properties.get("confidence"),
        )

    artifact_sources = _collect_artifact_source_surfaces(snapshot)
    for relation in tuple(snapshot.relations.values()):
        if relation.relation_type != "DESCRIBED_IN":
            continue
        if relation.source.label != "module_surface":
            continue
        if relation.target.label != "doc_artifact":
            continue
        for source_surface in artifact_sources.get(relation.target, ()):
            snapshot.add_relation(
                relation.source,
                "DESCRIBED_IN",
                source_surface,
                provenance="docs_code_drift_curated_source",
                confidence=relation.properties.get("confidence"),
            )


def _add_pipeline_doc_edges(snapshot: GraphSnapshot) -> None:
    for node in tuple(snapshot.nodes.values()):
        if node.key.label != "pipeline_surface":
            continue
        pipeline_kind = node.properties.get("pipeline_kind")
        if pipeline_kind == "entity":
            provider_name = str(node.properties.get("provider") or "")
            entity_name = str(node.properties.get("entity") or "")
        elif pipeline_kind == "composite":
            provider_name = "composite"
            entity_name = node.key.name.removeprefix("composite_")
        else:
            continue
        if not provider_name or not entity_name:
            continue
        _link_pipeline_doc_artifacts(
            snapshot,
            node.key,
            _pipeline_doc_artifact_targets(
                snapshot,
                provider_name=provider_name,
                entity_name=entity_name,
            ),
            provenance="impact_pipeline_docs",
        )


def _add_adr_constraint_edges(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
) -> None:
    decisions_dir = root / ADR_DECISIONS_DIR
    if not decisions_dir.is_dir():
        return
    path_pattern = _docs_path_pattern()
    for adr_path in sorted(decisions_dir.glob("ADR-*.md")):
        _add_single_adr_constraint_edges(
            snapshot,
            root,
            project,
            today,
            adr_path,
            path_pattern,
        )


def _add_single_adr_constraint_edges(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    adr_path: Path,
    path_pattern: re.Pattern[str],
) -> None:
    relative_adr_path = _rel_path(root, adr_path)
    adr_node = _add_adr_decision_node(snapshot, root, project, today, adr_path)
    adr_doc = NodeKey("doc_artifact", relative_adr_path)
    if adr_doc in snapshot.nodes:
        snapshot.add_relation(
            adr_node, "DESCRIBED_IN", adr_doc, provenance="adr_constraints"
        )
    text = _read_text(adr_path)
    seen_targets: set[NodeKey] = set()
    for path_match in path_pattern.finditer(text):
        normalized = _normalize_docs_repo_reference(path_match.group(1))
        if normalized is None or normalized == relative_adr_path:
            continue
        target = _resolve_adr_constraint_target(snapshot, normalized)
        if target is None or target in seen_targets:
            continue
        seen_targets.add(target)
        section_title, section_anchor, line_number = _doc_reference_context(
            text, path_match.start()
        )
        snapshot.add_relation(
            adr_node,
            "CONSTRAINS",
            target,
            provenance="adr_path_reference",
            doc_reference=normalized,
            section_title=section_title,
            section_anchor=section_anchor,
            line_number=line_number,
            confidence="medium",
        )


def _add_adr_decision_node(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    adr_path: Path,
) -> NodeKey:
    relative_adr_path = _rel_path(root, adr_path)
    title = _adr_title(adr_path)
    adr_node = snapshot.add_node(
        "decision",
        adr_path.stem,
        summary=title,
        source_path=relative_adr_path,
        source_kind="adr",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(project, "HAS_DECISION", adr_node, provenance="adr")
    return adr_node


def _adr_title(adr_path: Path) -> str:
    text = _read_text(adr_path)
    for _offset, title in _markdown_headings(text):
        return title
    return adr_path.stem


def _resolve_adr_constraint_target(
    snapshot: GraphSnapshot, normalized_ref: str
) -> NodeKey | None:
    for candidate in _adr_constraint_candidates(normalized_ref):
        if candidate in snapshot.nodes:
            return candidate
    return None


def _adr_constraint_candidates(normalized_ref: str) -> tuple[NodeKey, ...]:
    return (
        NodeKey("module_surface", normalized_ref),
        NodeKey("config_artifact", normalized_ref),
        NodeKey("test_artifact", normalized_ref),
        NodeKey("file_surface", normalized_ref),
        NodeKey("directory_surface", normalized_ref),
    )


def _docs_path_pattern() -> re.Pattern[str]:
    return re.compile(
        r"(?<![\w./-])("
        r"README\.md|mkdocs\.yml|\.github/[\w./*-]+|"
        r"(?:src|configs|scripts|tests|docs|grafana)/[\w./*-]+"
        r")"
    )


def _docs_command_pattern() -> re.Pattern[str]:
    return re.compile(
        r"(?:python3?\s+-m\s+(?:bioetl|scripts\.\w+)(?:\s+[\w.-]+)?(?:\s+--?[\w][\w-]*(?:[ =][^\s`]+)?)*|"
        r"uv\s+run\s+python3?\s+-m\s+(?:bioetl|scripts\.\w+)(?:\s+[\w.-]+)?(?:\s+--?[\w][\w-]*(?:[ =][^\s`]+)?)*|"
        r"uv\s+run\s+python\s+-m\s+(?:bioetl|scripts\.\w+)(?:\s+[\w.-]+)?(?:\s+--?[\w][\w-]*(?:[ =][^\s`]+)?)*"
        r")"
    )


def _is_excluded_docs_drift_prefix(normalized_source_path: str) -> bool:
    return any(
        normalized_source_path == prefix
        or normalized_source_path.startswith(f"{prefix}/")
        for prefix in _DOCS_DRIFT_EXCLUDED_PREFIXES
    )


def _normalize_docs_drift_source_path(
    root: Path,
    source_path: object,
    config: dict[str, object],
) -> str | None:
    if not isinstance(source_path, str):
        return None
    normalized_source_path = _coerce_repo_relative_path(root, source_path)
    if not normalized_source_path:
        return None
    if _is_excluded_docs_drift_prefix(normalized_source_path):
        return None
    if _is_excluded_file_structure_path(normalized_source_path, config):
        return None
    if Path(normalized_source_path).suffix.lower() not in _DOCS_DRIFT_TEXT_EXTENSIONS:
        return None
    return normalized_source_path


def _read_docs_drift_text(
    root: Path,
    normalized_source_path: str,
    cached_text: dict[str, str],
) -> str | None:
    text = cached_text.get(normalized_source_path)
    if text is not None:
        return text
    try:
        text = _read_text(root / normalized_source_path)
    except OSError:
        # Some tracked doc paths can exist in the graph but still be
        # unreadable on a given checkout or platform mount. Skip them
        # instead of failing the entire snapshot build.
        return None
    cached_text[normalized_source_path] = text
    return text


def _docs_drift_sources(
    snapshot: GraphSnapshot,
    root: Path,
    config: dict[str, object],
) -> Iterator[tuple[NodeKey, str, str]]:
    cached_text: dict[str, str] = {}
    for node in tuple(snapshot.nodes.values()):
        if node.key.label not in _DOC_LIKE_LABELS:
            continue
        if not _is_docs_drift_source_candidate(node):
            continue
        normalized_source_path = _normalize_docs_drift_source_path(
            root,
            node.properties.get("source_path"),
            config,
        )
        if normalized_source_path is None:
            continue
        text = _read_docs_drift_text(root, normalized_source_path, cached_text)
        if text is None:
            continue
        yield node.key, normalized_source_path, text


def _doc_reference_context(
    text: str, offset: int
) -> tuple[str | None, str | None, int]:
    section_title, section_anchor = _markdown_heading_context(text, offset)
    line_number = text.count("\n", 0, offset) + 1
    return section_title, section_anchor, line_number


def _add_doc_path_reference_edges(
    snapshot: GraphSnapshot,
    source_node: NodeKey,
    text: str,
    path_pattern: re.Pattern[str],
) -> None:
    seen_matches: set[tuple[str, str]] = set()
    for path_match in path_pattern.finditer(text):
        match = path_match.group(1)
        normalized = _normalize_docs_repo_reference(match)
        if normalized is None:
            continue
        target, evidence_kind, confidence = _resolve_docs_reference_target(
            snapshot, normalized
        )
        if target is None or target == source_node:
            continue
        dedupe_key = (normalized, target.name)
        if dedupe_key in seen_matches:
            continue
        seen_matches.add(dedupe_key)
        _add_doc_describes_relation(
            snapshot,
            source_node,
            target,
            text,
            path_match.start(),
            doc_reference=normalized,
            evidence_kind=evidence_kind,
            confidence=confidence,
        )


def _add_doc_command_reference_edges(
    snapshot: GraphSnapshot,
    source_node: NodeKey,
    text: str,
    command_pattern: re.Pattern[str],
) -> None:
    seen_commands: set[str] = set()
    for command_match in command_pattern.finditer(text):
        raw_command = command_match.group(0).strip()
        command_name = _normalize_cli_command_name(raw_command)
        if command_name is None or command_name in seen_commands:
            continue
        command_key = NodeKey("cli_command_surface", command_name)
        if command_key not in snapshot.nodes:
            continue
        seen_commands.add(command_name)
        _add_doc_describes_relation(
            snapshot,
            source_node,
            command_key,
            text,
            command_match.start(),
            doc_reference=raw_command,
            evidence_kind="command_reference",
            confidence="medium",
        )


def _add_doc_describes_relation(
    snapshot: GraphSnapshot,
    source_node: NodeKey,
    target: NodeKey,
    text: str,
    offset: int,
    *,
    doc_reference: str,
    evidence_kind: str,
    confidence: str,
) -> None:
    section_title, section_anchor, line_number = _doc_reference_context(text, offset)
    snapshot.add_relation(
        source_node,
        "DESCRIBES",
        target,
        provenance="docs_code_drift",
        doc_reference=doc_reference,
        evidence_kind=evidence_kind,
        confidence=confidence,
        section_title=section_title,
        section_anchor=section_anchor,
        line_number=line_number,
    )


def _is_claim_candidate(stripped_line: str) -> bool:
    if not stripped_line or len(stripped_line) < 12:
        return False
    lowered = stripped_line.lower()
    return any(
        token in lowered
        for token in ("must", "never", "must not", "should not", "required")
    )


def _add_doc_claim_edges(
    snapshot: GraphSnapshot,
    source_node: NodeKey,
    source_path: str,
    text: str,
    path_pattern: re.Pattern[str],
) -> None:
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        claim_line = _claim_line_context(raw_line)
        if claim_line is None:
            continue
        section_title, section_anchor = _claim_section_context(text, raw_line)
        claim = snapshot.add_node(
            "doc_claim_surface",
            f"{source_path}#L{line_number}",
            summary=f"Claim extracted from `{source_path}`.",
            source_path=source_path,
            source_kind="doc_claim_surface",
            claim_text=claim_line.clean_text,
            modality=_claim_modality(claim_line.clean_text),
            section_title=section_title,
            section_anchor=section_anchor,
            line_number=line_number,
            last_verified=str(date.today()),
            ingest_wave="repo_sync_v1",
            confidence="medium",
        )
        snapshot.add_relation(source_node, "ASSERTS", claim, provenance="docs_claims")
        claim_has_target = _add_claim_path_targets(
            snapshot,
            claim,
            source_node,
            claim_line.stripped,
            section_title=section_title,
            section_anchor=section_anchor,
            line_number=line_number,
            path_pattern=path_pattern,
        )
        claim_has_target = (
            _add_claim_token_targets(
                snapshot,
                claim,
                claim_line.clean_text,
                section_title=section_title,
                section_anchor=section_anchor,
                line_number=line_number,
            )
            or claim_has_target
        )
        if not claim_has_target:
            _add_claim_fallback_target(
                snapshot,
                claim,
                source_path,
                section_title=section_title,
                section_anchor=section_anchor,
                line_number=line_number,
            )


@dataclass(frozen=True)
class ClaimLineContext:
    stripped: str
    clean_text: str


def _claim_line_context(raw_line: str) -> ClaimLineContext | None:
    stripped = raw_line.strip()
    if not _is_claim_candidate(stripped):
        return None
    return ClaimLineContext(
        stripped=stripped,
        clean_text=stripped.lstrip("-*0123456789. ").strip(),
    )


def _claim_section_context(text: str, raw_line: str) -> tuple[str | None, str | None]:
    line_offset = text.find(raw_line)
    return _markdown_heading_context(text, line_offset)


def _add_claim_path_targets(
    snapshot: GraphSnapshot,
    claim: NodeKey,
    source_node: NodeKey,
    stripped: str,
    *,
    section_title: str | None,
    section_anchor: str | None,
    line_number: int,
    path_pattern: re.Pattern[str],
) -> bool:
    claim_has_target = False
    for claim_match in path_pattern.finditer(stripped):
        normalized = _normalize_docs_repo_reference(claim_match.group(1))
        if normalized is None:
            continue
        target, evidence_kind, confidence = _resolve_docs_reference_target(
            snapshot, normalized
        )
        if target is None or target == source_node:
            continue
        _add_claim_target_relation(
            snapshot,
            claim,
            target,
            provenance="docs_claims",
            section_title=section_title,
            section_anchor=section_anchor,
            line_number=line_number,
            doc_reference=normalized,
            evidence_kind=evidence_kind,
            confidence=confidence,
        )
        claim_has_target = True
    return claim_has_target


def _add_claim_token_targets(
    snapshot: GraphSnapshot,
    claim: NodeKey,
    clean_text: str,
    *,
    section_title: str | None,
    section_anchor: str | None,
    line_number: int,
) -> bool:
    claim_has_target = False
    for target, evidence_kind, confidence in _resolve_claim_targets(
        snapshot, clean_text
    ):
        _add_claim_target_relation(
            snapshot,
            claim,
            target,
            provenance="docs_claims",
            section_title=section_title,
            section_anchor=section_anchor,
            line_number=line_number,
            evidence_kind=evidence_kind,
            confidence=confidence,
        )
        claim_has_target = True
    return claim_has_target


def _add_claim_target_relation(
    snapshot: GraphSnapshot,
    claim: NodeKey,
    target: NodeKey,
    *,
    provenance: str,
    section_title: str | None,
    section_anchor: str | None,
    line_number: int,
    evidence_kind: str,
    confidence: str,
    doc_reference: str | None = None,
) -> None:
    snapshot.add_relation(
        claim,
        "ASSERTS_ABOUT",
        target,
        provenance=provenance,
        doc_reference=doc_reference,
        evidence_kind=evidence_kind,
        confidence=confidence,
        section_title=section_title,
        section_anchor=section_anchor,
        line_number=line_number,
    )


def _add_claim_fallback_target(
    snapshot: GraphSnapshot,
    claim: NodeKey,
    source_path: str,
    *,
    section_title: str | None,
    section_anchor: str | None,
    line_number: int,
) -> None:
    file_surface_key = NodeKey("file_surface", source_path)
    if file_surface_key in snapshot.nodes:
        snapshot.add_relation(
            claim,
            "ASSERTS_ABOUT",
            file_surface_key,
            provenance="docs_claims_fallback",
            evidence_kind="source_document",
            confidence="low",
            section_title=section_title,
            section_anchor=section_anchor,
            line_number=line_number,
        )


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
    facade = _add_port_facade_surface(snapshot, project, family, today)
    port_nodes.add(facade)

    descriptors, _, _ = _build_port_surface_catalog(root)
    for descriptor in descriptors:
        _register_protocol_port_surface(
            snapshot,
            project,
            facade,
            family,
            descriptor,
            today,
            port_nodes=port_nodes,
        )
    return port_nodes


def _register_protocol_port_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    facade: NodeKey,
    family: NodeKey,
    descriptor: PortSurfaceDescriptor,
    today: str,
    *,
    port_nodes: set[NodeKey],
) -> None:
    port = _add_protocol_port_surface(
        snapshot,
        project,
        facade,
        family,
        descriptor,
        today,
    )
    port_nodes.add(port)


def _add_port_facade_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    family: NodeKey,
    today: str,
) -> NodeKey:
    facade = snapshot.add_node(
        "port_surface",
        PORTS_MODULE_PREFIX,
        summary="Canonical facade exporting stable domain port protocols.",
        source_path=f"src/bioetl/domain/ports/{INIT_PY}",
        source_kind="domain_port_facade",
        granularity="facade",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(project, "HAS_PORT", facade, provenance="impact_ports")
    if family in snapshot.nodes:
        snapshot.add_relation(family, "CONTAINS", facade, provenance="impact_ports")
    facade_module = NodeKey("module_surface", PORTS_FACADE_SOURCE_PATH)
    if facade_module in snapshot.nodes:
        snapshot.add_relation(
            facade, "BACKED_BY", facade_module, provenance="impact_ports"
        )
    return facade


def _add_protocol_port_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    facade: NodeKey,
    family: NodeKey,
    descriptor: PortSurfaceDescriptor,
    today: str,
) -> NodeKey:
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
    snapshot.add_relation(project, "HAS_PORT", port, provenance="impact_ports")
    snapshot.add_relation(facade, "CONTAINS", port, provenance="impact_ports")
    if family in snapshot.nodes:
        snapshot.add_relation(family, "CONTAINS", port, provenance="impact_ports")
    module_key = NodeKey("module_surface", descriptor.source_path)
    if module_key in snapshot.nodes:
        snapshot.add_relation(port, "BACKED_BY", module_key, provenance="impact_ports")
    return port


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
    fine_grained_enabled = (
        bool(adapter_mapping.get("fine_grained_enabled", True))
        if isinstance(adapter_mapping, dict)
        else True
    )

    for child in sorted(adapters_root.iterdir()):
        _process_adapter_root_child(
            snapshot,
            root,
            project,
            today,
            child,
            adapter_family=adapter_family,
            adapter_nodes=adapter_nodes,
            port_module_surfaces=port_module_surfaces,
            port_symbol_index=port_symbol_index,
            port_names=port_names,
            fine_grained_enabled=fine_grained_enabled,
        )

    return adapter_nodes


def _process_adapter_root_child(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    child: Path,
    *,
    adapter_family: NodeKey,
    adapter_nodes: dict[str, NodeKey],
    port_module_surfaces: dict[str, set[str]],
    port_symbol_index: dict[str, dict[str, str]],
    port_names: set[str],
    fine_grained_enabled: bool,
) -> None:
    if _is_ignored_repo_path(child) or child.name.startswith("_"):
        return
    if child.is_dir():
        _process_adapter_package(
            snapshot,
            root,
            project,
            today,
            child,
            adapter_family=adapter_family,
            adapter_nodes=adapter_nodes,
            port_module_surfaces=port_module_surfaces,
            port_symbol_index=port_symbol_index,
            port_names=port_names,
            fine_grained_enabled=fine_grained_enabled,
        )
        return
    if child.suffix != ".py" or child.name == INIT_PY:
        return
    _process_adapter_module(
        snapshot,
        root,
        project,
        today,
        child,
        adapter_family=adapter_family,
        adapter_nodes=adapter_nodes,
        port_module_surfaces=port_module_surfaces,
        port_symbol_index=port_symbol_index,
        port_names=port_names,
    )


def _process_adapter_package(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    child: Path,
    *,
    adapter_family: NodeKey,
    adapter_nodes: dict[str, NodeKey],
    port_module_surfaces: dict[str, set[str]],
    port_symbol_index: dict[str, dict[str, str]],
    port_names: set[str],
    fine_grained_enabled: bool,
) -> None:
    adapter = _add_adapter_package_surface(
        snapshot,
        root,
        project,
        adapter_family,
        child,
        today,
    )
    adapter_nodes[child.name] = adapter
    provider_key = NodeKey("provider_surface", child.name)
    if provider_key in snapshot.nodes:
        snapshot.add_relation(
            provider_key, "PROVIDES", adapter, provenance="impact_adapters"
        )
    imported_ports = _add_adapter_package_impls(
        snapshot,
        root,
        adapter,
        child,
        port_module_surfaces,
        port_symbol_index,
        port_names,
        today,
        fine_grained_enabled=fine_grained_enabled,
    )
    _link_adapter_ports(
        snapshot, adapter, imported_ports, port_names, provenance="impact_adapters"
    )


def _process_adapter_module(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    child: Path,
    *,
    adapter_family: NodeKey,
    adapter_nodes: dict[str, NodeKey],
    port_module_surfaces: dict[str, set[str]],
    port_symbol_index: dict[str, dict[str, str]],
    port_names: set[str],
) -> None:
    adapter = _add_adapter_module_surface(
        snapshot,
        root,
        project,
        adapter_family,
        child,
        today,
    )
    adapter_nodes[child.stem] = adapter
    imported_ports = _imported_port_surfaces(
        child, port_module_surfaces, port_symbol_index
    )
    _link_adapter_ports(
        snapshot, adapter, imported_ports, port_names, provenance="impact_adapters"
    )


def _add_adapter_package_surface(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    adapter_family: NodeKey,
    child: Path,
    today: str,
) -> NodeKey:
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
    snapshot.add_relation(project, "HAS_ADAPTER", adapter, provenance="impact_adapters")
    if adapter_family in snapshot.nodes:
        snapshot.add_relation(
            adapter_family, "CONTAINS", adapter, provenance="impact_adapters"
        )
    return adapter


def _add_adapter_package_impls(
    snapshot: GraphSnapshot,
    root: Path,
    adapter: NodeKey,
    child: Path,
    port_module_surfaces: dict[str, set[str]],
    port_symbol_index: dict[str, dict[str, str]],
    port_names: set[str],
    today: str,
    *,
    fine_grained_enabled: bool,
) -> set[str]:
    imported_ports: set[str] = set()
    for module_path in sorted(child.rglob("*.py")):
        if _is_ignored_repo_path(module_path):
            continue
        module_ports = _imported_port_surfaces(
            module_path, port_module_surfaces, port_symbol_index
        )
        if fine_grained_enabled and module_path.name != INIT_PY:
            impl_node = _add_adapter_impl_surface(
                snapshot, root, adapter, module_path, today
            )
            _link_adapter_ports(
                snapshot,
                impl_node,
                module_ports,
                port_names,
                provenance="impact_adapter_impls",
            )
        imported_ports.update(module_ports)
    return imported_ports


def _add_adapter_impl_surface(
    snapshot: GraphSnapshot,
    root: Path,
    adapter: NodeKey,
    module_path: Path,
    today: str,
) -> NodeKey:
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
    snapshot.add_relation(
        adapter, "CONTAINS", impl_node, provenance="impact_adapter_impls"
    )
    impl_module_key = NodeKey("module_surface", impl_relative_path)
    if impl_module_key in snapshot.nodes:
        snapshot.add_relation(
            impl_node, "BACKED_BY", impl_module_key, provenance="impact_adapter_impls"
        )
    return impl_node


def _add_adapter_module_surface(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    adapter_family: NodeKey,
    child: Path,
    today: str,
) -> NodeKey:
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
    snapshot.add_relation(project, "HAS_ADAPTER", adapter, provenance="impact_adapters")
    if adapter_family in snapshot.nodes:
        snapshot.add_relation(
            adapter_family, "CONTAINS", adapter, provenance="impact_adapters"
        )
    module_key = NodeKey("module_surface", relative_path)
    if module_key in snapshot.nodes:
        snapshot.add_relation(
            adapter, "BACKED_BY", module_key, provenance="impact_adapters"
        )
    return adapter


def _link_adapter_ports(
    snapshot: GraphSnapshot,
    source: NodeKey,
    imported_ports: set[str],
    port_names: set[str],
    *,
    provenance: str,
) -> None:
    for port_name in sorted(imported_ports):
        if port_name in port_names:
            snapshot.add_relation(
                source,
                "DEPENDS_ON",
                NodeKey("port_surface", port_name),
                provenance=provenance,
            )


def _contract_mapping_config(
    memory_mapping: dict[str, object],
) -> ContractMappingConfig:
    contracts_mapping = _mapping_dict_or_empty(memory_mapping.get("contracts"))
    return ContractMappingConfig(
        source_prefixes=_contract_source_prefixes(contracts_mapping),
        control_plane_modules=_contract_mapping_values(
            contracts_mapping, "control_plane_modules"
        ),
        control_plane_runtime_modules=_contract_mapping_values(
            contracts_mapping, "control_plane_runtime_modules"
        ),
        lineage_modules=_contract_mapping_values(contracts_mapping, "lineage_modules"),
        lineage_runtime_modules=_contract_mapping_values(
            contracts_mapping, "lineage_runtime_modules"
        ),
        control_plane_docs=_contract_mapping_values(
            contracts_mapping, "control_plane_docs"
        ),
        lineage_docs=_contract_mapping_values(contracts_mapping, "lineage_docs"),
        control_plane_anchor_fields=_contract_mapping_values(
            contracts_mapping, "control_plane_anchor_fields"
        ),
        lineage_anchor_fields=_contract_mapping_values(
            contracts_mapping, "lineage_anchor_fields"
        ),
    )


def _contract_source_prefixes(contracts_mapping: dict[str, object]) -> tuple[str, ...]:
    return tuple(
        _contract_mapping_values(contracts_mapping, "registry_source_prefixes")
        or [
            "bioetl.domain.contracts.gold",
            "bioetl.domain.schemas",
        ]
    )


def _contract_mapping_values(
    contracts_mapping: dict[str, object],
    key: str,
) -> list[str]:
    return _as_string_list(contracts_mapping.get(key))


def _link_contract_source_dependencies(
    snapshot: GraphSnapshot,
    context: ContractEntryContext,
    source_prefixes: tuple[str, ...],
) -> None:
    resolved = _contract_source_resolved_path(context)
    if resolved is None:
        return
    _link_contract_source_module(snapshot, context, resolved)
    _link_contract_imported_modules(snapshot, context, resolved, source_prefixes)
    _update_contract_schema_classes(snapshot, context, resolved)


def _contract_source_resolved_path(context: ContractEntryContext) -> Path | None:
    source_path = context.raw_entry.get("source_path")
    if not isinstance(source_path, str):
        return None
    return _resolve_repo_path(context.root, context.registry_path, source_path)


def _update_contract_schema_classes(
    snapshot: GraphSnapshot,
    context: ContractEntryContext,
    resolved: Path,
) -> None:
    schema_classes = _dataframe_model_class_names(resolved)
    if schema_classes:
        snapshot.add_node(
            "contract_surface", context.contract_ref, schema_classes=schema_classes
        )


def _link_contract_source_module(
    snapshot: GraphSnapshot,
    context: ContractEntryContext,
    resolved: Path,
) -> None:
    module_key = NodeKey("module_surface", _rel_path(context.root, resolved))
    if module_key in snapshot.nodes:
        snapshot.add_relation(
            context.contract, "BACKED_BY", module_key, provenance="impact_contracts"
        )


def _link_contract_imported_modules(
    snapshot: GraphSnapshot,
    context: ContractEntryContext,
    resolved: Path,
    source_prefixes: tuple[str, ...],
) -> None:
    for imported_module in sorted(_imported_repo_modules(resolved, source_prefixes)):
        dependency_key = _resolve_python_module_surface(context.root, imported_module)
        if dependency_key is not None and dependency_key in snapshot.nodes:
            snapshot.add_relation(
                context.contract,
                "DEPENDS_ON",
                dependency_key,
                provenance="impact_contracts",
            )


def _add_contract_policy_config(
    snapshot: GraphSnapshot, context: ContractEntryContext
) -> None:
    contract_config_path = _contract_policy_config_path(context)
    if not contract_config_path.is_file():
        return
    contract_config = _read_yaml(contract_config_path)
    snapshot.add_node(
        "contract_surface",
        context.contract_ref,
        **_contract_policy_fields(contract_config),
    )
    artifact = _add_contract_policy_artifact(
        snapshot,
        context=context,
        contract_config_path=contract_config_path,
    )
    snapshot.add_relation(
        context.contract, "BACKED_BY", artifact, provenance="impact_contracts"
    )


def _contract_policy_config_path(context: ContractEntryContext) -> Path:
    return (
        context.root / "configs" / "contracts" / context.contract_ref.replace(".", "/")
    ).with_suffix(YAML_SUFFIX)


def _contract_policy_fields(contract_config: dict[str, object]) -> dict[str, object]:
    return {
        "contract_config_version": contract_config.get("contract_version"),
        "contract_config_ref": contract_config.get("contract_ref"),
        "soft_fail_threshold": contract_config.get("soft_fail_threshold"),
        "hard_fail_threshold": contract_config.get("hard_fail_threshold"),
        "strict_validation": contract_config.get(
            "strict_dq_validation", contract_config.get("strict_validation")
        ),
        "invalid_record_policy": contract_config.get("invalid_record_policy"),
        "default_disposition_policy": contract_config.get("default_disposition_policy"),
    }


def _add_contract_policy_artifact(
    snapshot: GraphSnapshot,
    *,
    context: ContractEntryContext,
    contract_config_path: Path,
) -> NodeKey:
    relative_path = _rel_path(context.root, contract_config_path)
    return snapshot.add_node(
        "config_artifact",
        relative_path,
        summary=f"Contract policy config for `{context.contract_ref}`.",
        source_path=relative_path,
        source_kind="contract_config",
        last_verified=context.today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )


def _add_published_contract_artifacts(
    snapshot: GraphSnapshot, context: ContractEntryContext
) -> None:
    for published_path in _published_contract_artifact_paths(context):
        artifact = _published_contract_artifact_key(snapshot, context, published_path)
        if artifact is None:
            continue
        snapshot.add_relation(
            context.contract, "BACKED_BY", artifact, provenance="impact_contracts"
        )


def _published_contract_artifact_paths(
    context: ContractEntryContext,
) -> tuple[str, ...]:
    published_artifacts = context.raw_entry.get("published_artifacts")
    if not isinstance(published_artifacts, list):
        return ()
    return tuple(path for path in published_artifacts if isinstance(path, str))


def _published_contract_artifact_key(
    snapshot: GraphSnapshot,
    context: ContractEntryContext,
    published_path: str,
) -> NodeKey | None:
    resolved = _resolve_repo_path(context.root, context.registry_path, published_path)
    if resolved is None:
        return None
    relative_path = _rel_path(context.root, resolved)
    return snapshot.add_node(
        "doc_artifact",
        relative_path,
        summary=f"Published contract artifact for `{context.contract_ref}`.",
        source_path=relative_path,
        source_kind="published_contract",
        last_verified=context.today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )


def _link_contract_module_dependencies(
    snapshot: GraphSnapshot,
    context: ContractEntryContext,
    module_paths: list[str],
    provenance: str,
) -> None:
    for module_path in module_paths:
        _link_contract_dependency_module(snapshot, context, module_path, provenance)


def _contract_dependency_module_key(root: Path, module_path: str) -> NodeKey | None:
    resolved_module = root / module_path
    if not resolved_module.is_file():
        return None
    return NodeKey("module_surface", _rel_path(root, resolved_module))


def _link_contract_dependency_module(
    snapshot: GraphSnapshot,
    context: ContractEntryContext,
    module_path: str,
    provenance: str,
) -> None:
    module_key = _contract_dependency_module_key(context.root, module_path)
    if module_key is not None and module_key in snapshot.nodes:
        snapshot.add_relation(
            context.contract, "DEPENDS_ON", module_key, provenance=provenance
        )


def _link_contract_doc_dependencies(
    snapshot: GraphSnapshot,
    context: ContractEntryContext,
    doc_paths: list[str],
    anchor_fields: list[str],
    *,
    summary: str,
    source_kind: str,
    provenance: str,
) -> None:
    for doc_path in doc_paths:
        resolved_doc = _contract_dependency_doc_path(
            context.root, doc_path, anchor_fields
        )
        if resolved_doc is None:
            continue
        artifact = _add_contract_doc_dependency(
            snapshot,
            context=context,
            doc_path=doc_path,
            summary=summary,
            source_kind=source_kind,
        )
        snapshot.add_relation(
            context.contract, "DESCRIBED_IN", artifact, provenance=provenance
        )


def _add_contract_doc_dependency(
    snapshot: GraphSnapshot,
    *,
    context: ContractEntryContext,
    doc_path: str,
    summary: str,
    source_kind: str,
) -> NodeKey:
    return snapshot.add_node(
        "doc_artifact",
        doc_path,
        summary=summary.format(contract_ref=context.contract_ref),
        source_path=doc_path,
        source_kind=source_kind,
        last_verified=context.today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )


def _contract_dependency_doc_path(
    root: Path,
    doc_path: str,
    anchor_fields: list[str],
) -> Path | None:
    resolved_doc = root / doc_path
    if not resolved_doc.is_file() or not _path_contains_any_token(
        resolved_doc, anchor_fields
    ):
        return None
    return resolved_doc


def _add_contract_entry_surface(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    registry_artifact: NodeKey,
    *,
    contract_ref: str,
    raw_entry: dict[str, object],
    today: str,
) -> ContractEntryContext:
    identity = _as_mapping(raw_entry.get("identity"))
    registry_path = root / CONTRACT_REGISTRY_RELATIVE_PATH
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
        rule_bundle_version=raw_entry.get("rule_bundle_version")
        or identity.get("rule_bundle_version"),
        owners=raw_entry.get("owners"),
        supported_versions=raw_entry.get("supported_versions"),
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(
        project, "HAS_CONTRACT", contract, provenance="impact_contracts"
    )
    snapshot.add_relation(
        contract, "BACKED_BY", registry_artifact, provenance="impact_contracts"
    )
    _link_contract_provider(snapshot, contract_ref, contract)
    return ContractEntryContext(
        root=root,
        registry_path=registry_path,
        today=today,
        contract_ref=contract_ref,
        contract=contract,
        raw_entry=raw_entry,
    )


def _link_contract_provider(
    snapshot: GraphSnapshot,
    contract_ref: str,
    contract: NodeKey,
) -> None:
    provider_name = contract_ref.split(".", 1)[0]
    provider_key = NodeKey("provider_surface", provider_name)
    if provider_key in snapshot.nodes:
        snapshot.add_relation(
            provider_key, "DEFINES", contract, provenance="impact_contracts"
        )


def _add_contract_registry_artifact(
    snapshot: GraphSnapshot,
    root: Path,
    today: str,
) -> NodeKey | None:
    registry_path = root / CONTRACT_REGISTRY_RELATIVE_PATH
    if not registry_path.is_file():
        return None
    relative_path = _rel_path(root, registry_path)
    return snapshot.add_node(
        "config_artifact",
        relative_path,
        summary="Contract registry for published data contracts.",
        source_path=relative_path,
        source_kind="contract_registry",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )


def _contract_registry_entries(root: Path) -> dict[str, dict[str, object]]:
    return {
        contract_ref: raw_entry
        for contract_ref, raw_entry in sorted(_contract_registry_payload(root).items())
        if isinstance(contract_ref, str) and isinstance(raw_entry, dict)
    }


def _contract_registry_payload(root: Path) -> dict[object, object]:
    payload = load_contract_registry_payload(root / DEFAULT_CONTRACT_REGISTRY_PATH)
    entries = payload.get("entries")
    return entries if isinstance(entries, dict) else {}


def _link_contract_dependencies(
    snapshot: GraphSnapshot,
    entry_context: ContractEntryContext,
    mapping_config: ContractMappingConfig,
) -> None:
    _link_contract_source_dependencies(
        snapshot, entry_context, mapping_config.source_prefixes
    )
    _add_contract_policy_config(snapshot, entry_context)
    _add_published_contract_artifacts(snapshot, entry_context)
    _link_contract_dependency_modules(snapshot, entry_context, mapping_config)
    _link_contract_dependency_docs(snapshot, entry_context, mapping_config)


def _link_contract_dependency_modules(
    snapshot: GraphSnapshot,
    entry_context: ContractEntryContext,
    mapping_config: ContractMappingConfig,
) -> None:
    for module_paths, provenance in _contract_dependency_module_specs(mapping_config):
        _link_contract_module_dependencies(
            snapshot,
            entry_context,
            module_paths,
            provenance,
        )


def _link_contract_dependency_docs(
    snapshot: GraphSnapshot,
    entry_context: ContractEntryContext,
    mapping_config: ContractMappingConfig,
) -> None:
    for (
        doc_paths,
        anchor_fields,
        summary,
        source_kind,
        provenance,
    ) in _contract_dependency_doc_specs(mapping_config):
        _link_contract_doc_dependencies(
            snapshot,
            entry_context,
            doc_paths,
            anchor_fields,
            summary=summary,
            source_kind=source_kind,
            provenance=provenance,
        )


def _contract_dependency_module_specs(
    mapping_config: ContractMappingConfig,
) -> tuple[tuple[list[str], str], ...]:
    return (
        (mapping_config.control_plane_modules, "impact_contracts_control_plane"),
        (mapping_config.control_plane_runtime_modules, "impact_contracts_runtime"),
        (mapping_config.lineage_modules, "impact_contracts_lineage"),
        (mapping_config.lineage_runtime_modules, "impact_contracts_lineage_runtime"),
    )


def _contract_dependency_doc_specs(
    mapping_config: ContractMappingConfig,
) -> tuple[tuple[list[str], list[str], str, str, str], ...]:
    return (
        (
            mapping_config.control_plane_docs,
            mapping_config.control_plane_anchor_fields,
            "Control-plane contract reference for `{contract_ref}`.",
            "control_plane_contract_doc",
            "impact_contracts_control_plane",
        ),
        (
            mapping_config.lineage_docs,
            mapping_config.lineage_anchor_fields,
            "Lineage/traceability contract reference for `{contract_ref}`.",
            "lineage_contract_doc",
            "impact_contracts_lineage",
        ),
    )


def _add_contract_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    memory_mapping: dict[str, object],
) -> dict[str, NodeKey]:
    registry_artifact = _add_contract_registry_artifact(snapshot, root, today)
    if registry_artifact is None:
        return {}
    entries = _contract_registry_entries(root)
    if not entries:
        return {}
    mapping_config = _contract_mapping_config(memory_mapping)

    contract_nodes: dict[str, NodeKey] = {}
    for contract_ref, raw_entry in entries.items():
        _register_contract_entry(
            snapshot,
            root,
            project,
            registry_artifact,
            contract_ref=contract_ref,
            raw_entry=raw_entry,
            today=today,
            mapping_config=mapping_config,
            contract_nodes=contract_nodes,
        )

    return contract_nodes


def _register_contract_entry(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    registry_artifact: NodeKey,
    *,
    contract_ref: str,
    raw_entry: dict[str, object],
    today: str,
    mapping_config: ContractMappingConfig,
    contract_nodes: dict[str, NodeKey],
) -> None:
    entry_context = _add_contract_entry_surface(
        snapshot,
        root,
        project,
        registry_artifact,
        contract_ref=contract_ref,
        raw_entry=raw_entry,
        today=today,
    )
    contract_nodes[contract_ref] = entry_context.contract
    _link_contract_dependencies(snapshot, entry_context, mapping_config)


def _register_duplication_class_surface(
    context: DuplicationExtractionContext,
    *,
    module_key: NodeKey,
    relative_path: str,
    dotted_path: str,
    family: DuplicateFamilyConfig,
    node: ast.ClassDef,
) -> NodeKey:
    class_key = context.snapshot.add_node(
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
            1
            for child in node.body
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        ),
        is_mixin=node.name.endswith("Mixin"),
        semantic_tags=list(_semantic_tags(relative_path, node.name)),
        last_verified=context.today,
        ingest_wave="repo_sync_v1",
        confidence="medium",
    )
    context.snapshot.add_relation(
        module_key, "DECLARES", class_key, provenance="code_duplication"
    )
    context.class_descriptors[class_key] = ClassDescriptor(
        node_key=class_key,
        family_name=family.name,
        package_family=family.package_family,
        source_path=relative_path,
        class_name=node.name,
        base_names=tuple(
            sorted(filter(None, (_base_name(base) for base in node.bases)))
        ),
        method_names=tuple(
            child.name
            for child in node.body
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        ),
    )
    context.class_name_index.setdefault(node.name, []).append(class_key)
    return class_key


def _register_duplication_method_surfaces(
    context: DuplicationExtractionContext,
    *,
    relative_path: str,
    dotted_path: str,
    family: DuplicateFamilyConfig,
    class_key: NodeKey,
    class_name: str,
    class_body: list[ast.stmt],
) -> None:
    for child in class_body:
        if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        method_key = _add_duplication_callable_surface(
            context,
            relative_path=relative_path,
            family=family,
            node=child,
            surface_label="method_surface",
            source_kind="python_method_surface",
            summary=f"Method surface `{class_name}.{child.name}` from `{dotted_path}`.",
            surface_name=f"{dotted_path}.{class_name}.{child.name}",
            parent_class=class_name,
        )
        context.snapshot.add_relation(
            class_key, "DECLARES", method_key, provenance="code_duplication"
        )
        context.callable_descriptors[method_key] = _duplication_callable_descriptor(
            context,
            method_key,
            family=family,
            relative_path=relative_path,
            callable_name=child.name,
            parent_class=class_name,
            surface_kind="method_surface",
        )


def _register_duplication_function_surface(
    context: DuplicationExtractionContext,
    *,
    module_key: NodeKey,
    relative_path: str,
    dotted_path: str,
    family: DuplicateFamilyConfig,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> None:
    function_key = _add_duplication_callable_surface(
        context,
        relative_path=relative_path,
        family=family,
        node=node,
        surface_label="function_surface",
        source_kind="python_function_surface",
        summary=f"Function surface `{node.name}` from `{dotted_path}`.",
        surface_name=f"{dotted_path}.{node.name}",
    )
    context.snapshot.add_relation(
        module_key, "DECLARES", function_key, provenance="code_duplication"
    )
    context.callable_descriptors[function_key] = _duplication_callable_descriptor(
        context,
        function_key,
        family=family,
        relative_path=relative_path,
        callable_name=node.name,
        parent_class=None,
        surface_kind="function_surface",
    )


def _add_duplication_callable_surface(
    context: DuplicationExtractionContext,
    *,
    relative_path: str,
    family: DuplicateFamilyConfig,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    surface_label: str,
    source_kind: str,
    summary: str,
    surface_name: str,
    parent_class: str | None = None,
) -> NodeKey:
    return context.snapshot.add_node(
        surface_label,
        surface_name,
        summary=summary,
        source_path=relative_path,
        source_kind=source_kind,
        family_name=family.name,
        package_family=family.package_family,
        callable_name=node.name,
        parent_class=parent_class,
        signature_hash=_signature_hash(node),
        ast_shape_hash=_normalized_callable_hash(node),
        ast_node_count=_callable_ast_node_count(node),
        branch_count=_callable_branch_count(node),
        nesting_depth=_callable_max_nesting_depth(node),
        call_count=_callable_call_count(node),
        helper_call_count=_callable_helper_call_count(node),
        semantic_tags=list(_semantic_tags(relative_path, node.name)),
        last_verified=context.today,
        ingest_wave="repo_sync_v1",
        confidence="medium",
    )


def _duplication_callable_descriptor(
    context: DuplicationExtractionContext,
    node_key: NodeKey,
    *,
    family: DuplicateFamilyConfig,
    relative_path: str,
    callable_name: str,
    parent_class: str | None,
    surface_kind: str,
) -> CallableDescriptor:
    callable_node = context.snapshot.nodes[node_key]
    return CallableDescriptor(
        node_key=node_key,
        family_name=family.name,
        package_family=family.package_family,
        source_path=relative_path,
        callable_name=callable_name,
        parent_class=parent_class,
        surface_kind=surface_kind,
        ast_shape_hash=str(callable_node.properties["ast_shape_hash"]),
        signature_hash=str(callable_node.properties["signature_hash"]),
        ast_node_count=_coerce_int(callable_node.properties["ast_node_count"]),
        semantic_tags=tuple(_semantic_tags(relative_path, callable_name)),
    )


def _collect_duplication_descriptors_for_module(
    context: DuplicationExtractionContext,
    module: GraphNode,
) -> None:
    relative_path = module.key.name
    family = _family_for_path(relative_path, context.config)
    if family is None:
        return
    module_path = context.root / relative_path
    tree = _parse_python_ast(module_path)
    if tree is None:
        return
    dotted_path = str(
        module.properties.get("dotted_path") or _module_dotted_name(relative_path)
    )
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            _collect_duplication_class_descriptors(
                context,
                module_key=module.key,
                relative_path=relative_path,
                dotted_path=dotted_path,
                family=family,
                node=node,
            )
            continue
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        _collect_duplication_function_descriptor(
            context,
            module_key=module.key,
            relative_path=relative_path,
            dotted_path=dotted_path,
            family=family,
            node=node,
        )


def _collect_duplication_class_descriptors(
    context: DuplicationExtractionContext,
    *,
    module_key: NodeKey,
    relative_path: str,
    dotted_path: str,
    family: DuplicateFamilyConfig,
    node: ast.ClassDef,
) -> None:
    class_key = _register_duplication_class_surface(
        context,
        module_key=module_key,
        relative_path=relative_path,
        dotted_path=dotted_path,
        family=family,
        node=node,
    )
    _register_duplication_method_surfaces(
        context,
        relative_path=relative_path,
        dotted_path=dotted_path,
        family=family,
        class_key=class_key,
        class_name=node.name,
        class_body=node.body,
    )


def _collect_duplication_function_descriptor(
    context: DuplicationExtractionContext,
    *,
    module_key: NodeKey,
    relative_path: str,
    dotted_path: str,
    family: DuplicateFamilyConfig,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> None:
    _register_duplication_function_surface(
        context,
        module_key=module_key,
        relative_path=relative_path,
        dotted_path=dotted_path,
        family=family,
        node=node,
    )


def _duplication_class_method_index(
    callable_descriptors: dict[NodeKey, CallableDescriptor],
) -> dict[tuple[NodeKey, str], NodeKey]:
    class_method_index: dict[tuple[NodeKey, str], NodeKey] = {}
    for callable_descriptor in callable_descriptors.values():
        if (
            callable_descriptor.surface_kind != "method_surface"
            or callable_descriptor.parent_class is None
        ):
            continue
        owner_name = callable_descriptor.node_key.name.rsplit(".", 1)[0]
        class_method_index[
            (NodeKey("class_surface", owner_name), callable_descriptor.callable_name)
        ] = callable_descriptor.node_key
    return class_method_index


def _link_duplication_override_relations(
    snapshot: GraphSnapshot,
    class_descriptors: dict[NodeKey, ClassDescriptor],
    class_name_index: dict[str, list[NodeKey]],
    class_method_index: dict[tuple[NodeKey, str], NodeKey],
) -> None:
    for class_descriptor in class_descriptors.values():
        for base_class in _resolved_base_classes(
            snapshot, class_descriptor, class_name_index
        ):
            snapshot.add_relation(
                class_descriptor.node_key,
                "DEPENDS_ON",
                base_class,
                provenance="code_duplication",
            )
            _link_duplication_override_methods(
                snapshot,
                class_descriptor=class_descriptor,
                base_class=base_class,
                class_method_index=class_method_index,
            )


def _resolved_base_classes(
    snapshot: GraphSnapshot,
    class_descriptor: ClassDescriptor,
    class_name_index: dict[str, list[NodeKey]],
) -> tuple[NodeKey, ...]:
    class_node = snapshot.nodes[class_descriptor.node_key]
    base_names = class_node.properties.get("base_names")
    if not isinstance(base_names, list):
        return ()
    resolved: list[NodeKey] = []
    for base_name in base_names:
        if not isinstance(base_name, str) or not base_name:
            continue
        base_candidates = class_name_index.get(base_name, [])
        if len(base_candidates) == 1:
            resolved.append(base_candidates[0])
    return tuple(resolved)


def _link_duplication_override_methods(
    snapshot: GraphSnapshot,
    *,
    class_descriptor: ClassDescriptor,
    base_class: NodeKey,
    class_method_index: dict[tuple[NodeKey, str], NodeKey],
) -> None:
    for method_name in class_descriptor.method_names:
        base_method = class_method_index.get((base_class, method_name))
        current_method = class_method_index.get(
            (class_descriptor.node_key, method_name)
        )
        if base_method is not None and current_method is not None:
            snapshot.add_relation(
                current_method, "OVERRIDES", base_method, provenance="code_duplication"
            )


def _duplication_promotion_target(
    snapshot: GraphSnapshot,
    config: dict[str, object],
    family_name: str,
    surface_kind: str,
    unique_members: list[CallableDescriptor],
) -> NodeKey | None:
    promotion_target = _method_surface_promotion_target(
        snapshot, surface_kind, unique_members
    )
    if promotion_target is not None:
        return promotion_target
    family = _duplication_family_by_name(config, family_name)
    if not isinstance(family, DuplicateFamilyConfig):
        return None
    for candidate in family.promotion_targets:
        if candidate in snapshot.nodes:
            return candidate
    return None


def _method_surface_promotion_target(
    snapshot: GraphSnapshot,
    surface_kind: str,
    unique_members: list[CallableDescriptor],
) -> NodeKey | None:
    if surface_kind != "method_surface" or not unique_members:
        return None
    method_name = unique_members[0].callable_name
    if not all(
        member.callable_name == method_name and member.parent_class
        for member in unique_members
    ):
        return None
    common_base_candidates: set[NodeKey] | None = None
    for member in unique_members:
        class_targets = _override_target_classes(snapshot, member)
        common_base_candidates = (
            class_targets
            if common_base_candidates is None
            else common_base_candidates & class_targets
        )
    if not common_base_candidates:
        return None
    return sorted(common_base_candidates, key=lambda item: item.name)[0]


def _override_target_classes(
    snapshot: GraphSnapshot,
    member: CallableDescriptor,
) -> set[NodeKey]:
    candidate_set = {
        relation.target
        for relation in snapshot.relations.values()
        if relation.source == member.node_key
        and relation.relation_type == "OVERRIDES"
        and relation.target.label == "method_surface"
    }
    return {
        NodeKey("class_surface", target.name.rsplit(".", 1)[0])
        for target in candidate_set
    }


def _duplication_family_by_name(
    config: dict[str, object],
    family_name: str,
) -> DuplicateFamilyConfig | None:
    return next(
        (
            item
            for item in _as_iterable(config.get("families"))
            if isinstance(item, DuplicateFamilyConfig) and item.name == family_name
        ),
        None,
    )


def _emit_duplication_clusters(
    snapshot: GraphSnapshot,
    project: NodeKey,
    *,
    today: str,
    config: dict[str, object],
    callable_descriptors: dict[NodeKey, CallableDescriptor],
    min_cluster_size: int,
    min_ast_nodes: int,
) -> None:
    for (family_name, surface_kind, shape_hash), members in _duplication_cluster_groups(
        callable_descriptors,
        min_ast_nodes=min_ast_nodes,
    ):
        if len(members) < min_cluster_size:
            continue
        unique_members = sorted(members, key=lambda item: item.node_key.name)
        cluster = _add_duplication_cluster_node(
            snapshot,
            today=today,
            family_name=family_name,
            surface_kind=surface_kind,
            shape_hash=shape_hash,
            unique_members=unique_members,
        )
        snapshot.add_relation(
            project, "CONTAINS", cluster, provenance="code_duplication"
        )
        _link_duplication_cluster_members(snapshot, cluster, unique_members)
        _link_same_shape_members(snapshot, unique_members)
        promotion_target = _duplication_promotion_target(
            snapshot, config, family_name, surface_kind, unique_members
        )
        if promotion_target is not None:
            snapshot.add_relation(
                cluster,
                "CAN_PROMOTE_TO",
                promotion_target,
                provenance="code_duplication",
            )
        package_family = NodeKey("package_family", unique_members[0].package_family)
        for relation in tuple(snapshot.relations.values()):
            if (
                relation.relation_type == "TESTS_PACKAGE_FAMILY"
                and relation.target == package_family
            ):
                snapshot.add_relation(
                    cluster,
                    "COVERED_BY_TEST",
                    relation.source,
                    provenance="code_duplication",
                )


def _duplication_cluster_groups(
    callable_descriptors: dict[NodeKey, CallableDescriptor],
    *,
    min_ast_nodes: int,
) -> tuple[tuple[tuple[str, str, str], list[CallableDescriptor]], ...]:
    grouped: dict[tuple[str, str, str], list[CallableDescriptor]] = {}
    for descriptor in callable_descriptors.values():
        if descriptor.ast_node_count < min_ast_nodes:
            continue
        grouped.setdefault(
            (
                descriptor.family_name,
                descriptor.surface_kind,
                descriptor.ast_shape_hash,
            ),
            [],
        ).append(descriptor)
    return tuple(sorted(grouped.items()))


def _add_duplication_cluster_node(
    snapshot: GraphSnapshot,
    *,
    today: str,
    family_name: str,
    surface_kind: str,
    shape_hash: str,
    unique_members: list[CallableDescriptor],
) -> NodeKey:
    return snapshot.add_node(
        "duplication_cluster",
        f"{family_name}:{surface_kind}:{shape_hash[:12]}",
        summary=f"Potential duplicate logic cluster for `{family_name}` {surface_kind}.",
        source_kind="semantic_duplication_cluster",
        family_name=family_name,
        surface_kind=surface_kind,
        duplicate_count=len(unique_members),
        ast_shape_hash=shape_hash,
        semantic_tags=sorted(
            {tag for member in unique_members for tag in member.semantic_tags}
        ),
        promotion_score=round(min(0.99, 0.35 + (0.1 * len(unique_members))), 2),
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="medium",
    )


def _link_duplication_cluster_members(
    snapshot: GraphSnapshot,
    cluster: NodeKey,
    unique_members: list[CallableDescriptor],
) -> None:
    for member in unique_members:
        snapshot.add_relation(
            cluster, "CONTAINS", member.node_key, provenance="code_duplication"
        )


def _link_same_shape_members(
    snapshot: GraphSnapshot,
    unique_members: list[CallableDescriptor],
) -> None:
    for index, left in enumerate(unique_members):
        for right in unique_members[index + 1 :]:
            snapshot.add_relation(
                left.node_key,
                "SAME_SHAPE_AS",
                right.node_key,
                provenance="code_duplication",
            )
            snapshot.add_relation(
                right.node_key,
                "SAME_SHAPE_AS",
                left.node_key,
                provenance="code_duplication",
            )


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

    min_cluster_size, min_ast_nodes = _duplication_cluster_thresholds(config)
    extraction = DuplicationExtractionContext(
        snapshot=snapshot,
        root=root,
        today=today,
        config=config,
    )
    for module in tuple(snapshot.nodes.values()):
        if module.key.label != "module_surface":
            continue
        _collect_duplication_descriptors_for_module(extraction, module)

    class_method_index = _duplication_class_method_index(
        extraction.callable_descriptors
    )
    _link_duplication_override_relations(
        snapshot,
        extraction.class_descriptors,
        extraction.class_name_index,
        class_method_index,
    )
    _emit_duplication_clusters(
        snapshot,
        project,
        today=today,
        config=config,
        callable_descriptors=extraction.callable_descriptors,
        min_cluster_size=min_cluster_size,
        min_ast_nodes=min_ast_nodes,
    )


def _duplication_cluster_thresholds(config: dict[str, object]) -> tuple[int, int]:
    return _coerce_int(config.get("min_cluster_size", 2), 2), _coerce_int(
        config.get("min_ast_nodes", 12), 12
    )


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
    context = _retirement_analysis_context(snapshot, config, today)

    candidate_nodes = _retirement_candidate_nodes(
        snapshot,
        duplication_config=duplication_config,
        family_names=context["family_names"],
        family_cache=context["family_cache"],
    )
    _prime_retirement_age_cache(
        root, context["today_date"], context["age_cache"], candidate_nodes
    )

    for node, source_path, family, module_key in candidate_nodes:
        candidate_payload = _retirement_candidate_payload(
            snapshot,
            root,
            node,
            source_path,
            module_key,
            indexes=context["indexes"],
            label_sets=context["label_sets"],
            text_cache=context["text_cache"],
            age_cache=context["age_cache"],
            family_name=family.name,
            config=config,
        )
        if candidate_payload is None:
            continue
        _emit_retirement_candidate(
            snapshot, project, today, config, node, candidate_payload
        )


def _retirement_analysis_context(
    snapshot: GraphSnapshot,
    config: RetirementAnalysisConfig,
    today: str,
) -> dict[str, object]:
    return {
        "label_sets": _retirement_analysis_label_sets(),
        "indexes": _build_surface_relation_indexes(snapshot),
        "today_date": date.fromisoformat(today),
        "text_cache": {},
        "age_cache": {},
        "family_cache": {},
        "family_names": set(config.family_names),
    }


def _prime_retirement_age_cache(
    root: Path,
    today_date: date,
    age_cache: dict[str, int | None],
    candidate_nodes: list[tuple[GraphNode, str, DuplicateFamilyConfig, NodeKey]],
) -> None:
    _git_last_commit_age_days_bulk(
        root,
        [source_path for _, source_path, _, _ in candidate_nodes],
        today_date,
        age_cache,
    )


def _retirement_candidate_payload(
    snapshot: GraphSnapshot,
    root: Path,
    node: GraphNode,
    source_path: str,
    module_key: NodeKey,
    *,
    indexes: SurfaceRelationIndexes,
    label_sets: AnalysisLabelSets,
    text_cache: dict[str, str],
    age_cache: dict[str, int | None],
    family_name: str,
    config: RetirementAnalysisConfig,
) -> dict[str, object] | None:
    return _evaluate_retirement_surface(
        snapshot,
        root,
        node,
        source_path,
        module_key,
        indexes=indexes,
        label_sets=label_sets,
        text_cache=text_cache,
        age_cache=age_cache,
        family_name=family_name,
        config=config,
    )


def _retirement_analysis_label_sets() -> AnalysisLabelSets:
    return AnalysisLabelSets(
        ignored_relation_types={
            "DECLARES",
            "OVERRIDES",
            "SAME_SHAPE_AS",
            "CONTAINS",
            "BACKS",
            "HOUSES",
            "CANDIDATE_FOR_REMOVAL",
        },
        runtime_labels={
            "pipeline_surface",
            "execution_path",
            "alert_surface",
            "adapter_surface",
            "adapter_impl_surface",
        },
        config_labels={
            "entity_config",
            "composite_config",
            "provider_surface",
            "contract_surface",
            "port_surface",
        },
        doc_labels={
            "policy_surface",
            "doc_source_surface",
            "doc_artifact",
            "dashboard_surface",
            "quality_gate",
        },
        test_labels={"test_surface", "test_artifact"},
    )


def _retirement_candidate_nodes(
    snapshot: GraphSnapshot,
    *,
    duplication_config: dict[str, object],
    family_names: set[str],
    family_cache: dict[str, DuplicateFamilyConfig | None],
) -> list[tuple[GraphNode, str, DuplicateFamilyConfig, NodeKey]]:
    analysis_labels = {
        "module_surface",
        "class_surface",
        "function_surface",
        "method_surface",
    }
    candidate_nodes: list[tuple[GraphNode, str, DuplicateFamilyConfig, NodeKey]] = []
    for node in sorted(
        snapshot.nodes.values(), key=lambda item: (item.key.label, item.key.name)
    ):
        if node.key.label not in analysis_labels:
            continue
        source_path = node.properties.get("source_path")
        if not isinstance(source_path, str) or not source_path.endswith(".py"):
            continue
        family = _analysis_family_for_source_path(
            source_path, duplication_config, family_cache
        )
        if family is None or family.name not in family_names:
            continue
        module_key = (
            node.key
            if node.key.label == "module_surface"
            else NodeKey("module_surface", source_path)
        )
        if module_key not in snapshot.nodes:
            continue
        candidate_nodes.append((node, source_path, family, module_key))
    return candidate_nodes


def _evaluate_retirement_surface(
    snapshot: GraphSnapshot,
    root: Path,
    node: GraphNode,
    source_path: str,
    module_key: NodeKey,
    *,
    indexes: SurfaceRelationIndexes,
    label_sets: AnalysisLabelSets,
    text_cache: dict[str, str],
    age_cache: dict[str, int | None],
    family_name: str,
    config: RetirementAnalysisConfig,
) -> dict[str, object] | None:
    anchors = _collect_analysis_anchor_nodes(
        snapshot,
        indexes,
        node.key,
        module_key,
        label_sets,
    )
    anchor_counts = _analysis_anchor_counts(anchors)
    source_text = _analysis_read_source_text(root, source_path, text_cache)
    wip_markers, deprecation_markers = _retirement_marker_sets(config, source_text)
    recent_age_days = age_cache.get(source_path)
    cycle_score, deletion_score, only_test_referenced = _retirement_scores(
        config,
        _retirement_score_inputs(
            anchor_counts,
            recent_age_days=recent_age_days,
            wip_markers=wip_markers,
            deprecation_markers=deprecation_markers,
        ),
    )
    return _retirement_surface_payload(
        family_name=family_name,
        anchors=anchors,
        anchor_counts=anchor_counts,
        wip_markers=wip_markers,
        deprecation_markers=deprecation_markers,
        recent_age_days=recent_age_days,
        cycle_score=cycle_score,
        deletion_score=deletion_score,
        only_test_referenced=only_test_referenced,
    )


def _retirement_marker_sets(
    config: RetirementAnalysisConfig,
    source_text: str,
) -> tuple[list[str], list[str]]:
    return (
        sorted({marker for marker in config.wip_markers if marker in source_text}),
        sorted(
            {marker for marker in config.deprecation_markers if marker in source_text}
        ),
    )


def _retirement_score_inputs(
    anchor_counts: dict[str, int],
    *,
    recent_age_days: int | None,
    wip_markers: list[str],
    deprecation_markers: list[str],
) -> RetirementScoreInputs:
    return RetirementScoreInputs(
        runtime_count=anchor_counts["runtime_count"],
        config_count=anchor_counts["config_count"],
        doc_count=anchor_counts["doc_count"],
        test_count=anchor_counts["test_count"],
        recent_age_days=recent_age_days,
        wip_markers=wip_markers,
        deprecation_markers=deprecation_markers,
    )


def _analysis_anchor_counts(anchors: SurfaceAnchorSets) -> dict[str, int]:
    return {
        "runtime_count": len(anchors.runtime),
        "config_count": len(anchors.config),
        "doc_count": len(anchors.docs),
        "test_count": len(anchors.tests),
    }


def _retirement_surface_payload(
    *,
    family_name: str,
    anchors: SurfaceAnchorSets,
    anchor_counts: dict[str, int],
    wip_markers: list[str],
    deprecation_markers: list[str],
    recent_age_days: int | None,
    cycle_score: int,
    deletion_score: int,
    only_test_referenced: bool,
) -> dict[str, object]:
    return {
        "family_name": family_name,
        "anchors": anchors,
        **anchor_counts,
        "wip_markers": wip_markers,
        "deprecation_markers": deprecation_markers,
        "recent_age_days": recent_age_days,
        "cycle_score": cycle_score,
        "deletion_score": deletion_score,
        "only_test_referenced": only_test_referenced,
    }


def _emit_retirement_candidate(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
    config: RetirementAnalysisConfig,
    node: GraphNode,
    payload: dict[str, object],
) -> None:
    metrics = _retirement_candidate_metrics(payload)
    cycle_score = metrics["cycle_score"]
    recent_age_days = payload["recent_age_days"]
    wip_markers = payload["wip_markers"]
    deletion_score = metrics["deletion_score"]
    if cycle_score >= 3:
        _annotate_current_cycle_surface(
            snapshot,
            node,
            cycle_score=cycle_score,
            recent_age_days=recent_age_days,
            wip_markers=wip_markers,
            runtime_count=metrics["runtime_count"],
            config_count=metrics["config_count"],
            doc_count=metrics["doc_count"],
            test_count=metrics["test_count"],
        )
    if deletion_score < config.dead_score_threshold:
        return
    confidence = _retirement_candidate_confidence(
        deletion_score=deletion_score,
        dead_score_threshold=config.dead_score_threshold,
    )
    candidate = _add_retirement_candidate_node(
        snapshot,
        today,
        node,
        payload,
        confidence=confidence,
        cycle_score=cycle_score,
        deletion_score=deletion_score,
        recent_age_days=recent_age_days,
        runtime_count=metrics["runtime_count"],
        config_count=metrics["config_count"],
        doc_count=metrics["doc_count"],
        test_count=metrics["test_count"],
        wip_markers=wip_markers,
    )
    _link_retirement_candidate(snapshot, project, candidate, node.key)


def _retirement_candidate_metrics(payload: dict[str, object]) -> dict[str, int]:
    return {
        "cycle_score": _coerce_int(payload["cycle_score"]),
        "runtime_count": _coerce_int(payload["runtime_count"]),
        "config_count": _coerce_int(payload["config_count"]),
        "doc_count": _coerce_int(payload["doc_count"]),
        "test_count": _coerce_int(payload["test_count"]),
        "deletion_score": _coerce_int(payload["deletion_score"]),
    }


def _retirement_candidate_confidence(
    *,
    deletion_score: int,
    dead_score_threshold: int,
) -> str:
    return "high" if deletion_score >= dead_score_threshold + 2 else "medium"


def _link_retirement_candidate(
    snapshot: GraphSnapshot,
    project: NodeKey,
    candidate: NodeKey,
    target: NodeKey,
) -> None:
    snapshot.add_relation(
        project, "CONTAINS", candidate, provenance="retirement_analysis"
    )
    snapshot.add_relation(
        candidate, "CANDIDATE_FOR_REMOVAL", target, provenance="retirement_analysis"
    )


def _annotate_current_cycle_surface(
    snapshot: GraphSnapshot,
    node: GraphNode,
    *,
    cycle_score: int,
    recent_age_days: object,
    wip_markers: object,
    runtime_count: int,
    config_count: int,
    doc_count: int,
    test_count: int,
) -> None:
    snapshot.add_node(
        node.key.label,
        node.key.name,
        current_cycle_status="current_cycle",
        current_cycle_score=cycle_score,
        current_cycle_recent_age_days=recent_age_days,
        current_cycle_wip_markers=wip_markers,
        current_cycle_runtime_anchor_count=runtime_count,
        current_cycle_config_anchor_count=config_count,
        current_cycle_doc_anchor_count=doc_count,
        current_cycle_test_anchor_count=test_count,
    )


def _add_retirement_candidate_node(
    snapshot: GraphSnapshot,
    today: str,
    node: GraphNode,
    payload: dict[str, object],
    *,
    confidence: str,
    cycle_score: int,
    deletion_score: int,
    recent_age_days: object,
    runtime_count: int,
    config_count: int,
    doc_count: int,
    test_count: int,
    wip_markers: object,
) -> NodeKey:
    anchors = payload["anchors"]
    return snapshot.add_node(
        "retirement_candidate",
        f"{node.key.label}:{node.key.name}",
        summary=f"Potential dead/stale code candidate `{node.key.name}` in `{payload['family_name']}`.",
        source_path=str(node.properties.get("source_path")),
        source_kind="retirement_candidate",
        family_name=str(payload["family_name"]),
        target_label=node.key.label,
        target_name=node.key.name,
        deletion_score=deletion_score,
        deletion_confidence=confidence,
        recent_age_days=recent_age_days,
        only_test_referenced=payload["only_test_referenced"],
        deprecation_markers=payload["deprecation_markers"],
        runtime_anchor_count=runtime_count,
        config_anchor_count=config_count,
        doc_anchor_count=doc_count,
        test_anchor_count=test_count,
        runtime_anchors=sorted(anchor.name for anchor in anchors.runtime),
        config_anchors=sorted(anchor.name for anchor in anchors.config),
        doc_anchors=sorted(anchor.name for anchor in anchors.docs),
        test_anchors=sorted(anchor.name for anchor in anchors.tests),
        blocked_by_current_cycle=cycle_score >= 3,
        blocked_by_current_cycle_target_name=node.key.name
        if cycle_score >= 3
        else None,
        blocked_by_current_cycle_score=cycle_score if cycle_score >= 3 else None,
        blocked_by_current_cycle_wip_markers=wip_markers if cycle_score >= 3 else None,
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence=confidence,
    )


def _add_complexity_analysis_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    memory_mapping: dict[str, object],
) -> None:
    duplication_config = _duplication_analysis_config(memory_mapping)
    retirement_config = _retirement_analysis_config(memory_mapping, duplication_config)
    config = _complexity_analysis_config(
        memory_mapping, duplication_config, retirement_config
    )
    if not config.enabled or not config.family_names:
        return
    analysis_context = _complexity_analysis_context(snapshot, config)
    for node in sorted(
        snapshot.nodes.values(), key=lambda item: (item.key.label, item.key.name)
    ):
        candidate_payload = _evaluate_complexity_surface(
            snapshot,
            root,
            node,
            duplication_config=duplication_config,
            family_names=analysis_context["family_names"],
            family_cache=analysis_context["family_cache"],
            label_sets=analysis_context["label_sets"],
            indexes=analysis_context["indexes"],
            text_cache=analysis_context["text_cache"],
            config=config,
        )
        if candidate_payload is None:
            continue
        _emit_complexity_candidate(
            snapshot, project, today, config, node, candidate_payload
        )


def _complexity_analysis_context(
    snapshot: GraphSnapshot,
    config: ComplexityAnalysisConfig,
) -> dict[str, object]:
    return {
        "family_names": set(config.family_names),
        "label_sets": _complexity_analysis_label_sets(),
        "indexes": _build_surface_relation_indexes(snapshot),
        "text_cache": {},
        "family_cache": {},
    }


def _complexity_analysis_label_sets() -> AnalysisLabelSets:
    return AnalysisLabelSets(
        ignored_relation_types={
            "DECLARES",
            "OVERRIDES",
            "SAME_SHAPE_AS",
            "CONTAINS",
            "BACKS",
            "HOUSES",
            "CANDIDATE_FOR_REMOVAL",
            "HAS_COMPLEXITY_SIGNAL",
            "CANDIDATE_FOR_SIMPLIFICATION",
            "JUSTIFIED_BY_RUNTIME",
            "BLOCKED_BY_VARIANCE",
        },
        runtime_labels={
            "pipeline_surface",
            "execution_path",
            "alert_surface",
            "adapter_surface",
            "adapter_impl_surface",
        },
        config_labels={
            "entity_config",
            "composite_config",
            "provider_surface",
            "contract_surface",
            "port_surface",
        },
        doc_labels={
            "policy_surface",
            "doc_source_surface",
            "doc_artifact",
            "dashboard_surface",
            "quality_gate",
        },
        test_labels={"test_surface", "test_artifact"},
    )


def _complexity_surface_prerequisites(
    snapshot: GraphSnapshot,
    root: Path,
    node: GraphNode,
    *,
    duplication_config: dict[str, object],
    family_names: set[str],
    family_cache: dict[str, DuplicateFamilyConfig | None],
    text_cache: dict[str, str],
) -> tuple[str, DuplicateFamilyConfig, NodeKey, str] | None:
    analysis_labels = {
        "module_surface",
        "class_surface",
        "function_surface",
        "method_surface",
    }
    if node.key.label not in analysis_labels:
        return None
    source_path = node.properties.get("source_path")
    if not isinstance(source_path, str) or not source_path.endswith(".py"):
        return None
    family = _analysis_family_for_source_path(
        source_path, duplication_config, family_cache
    )
    if family is None or family.name not in family_names:
        return None
    module_key = (
        node.key
        if node.key.label == "module_surface"
        else NodeKey("module_surface", source_path)
    )
    if module_key not in snapshot.nodes:
        return None
    source_text = _analysis_read_source_text(root, source_path, text_cache)
    return source_path, family, module_key, source_text


def _complexity_surface_measurements(
    snapshot: GraphSnapshot,
    node: GraphNode,
    *,
    source_path: str,
    module_key: NodeKey,
    source_text: str,
    label_sets: AnalysisLabelSets,
    indexes: SurfaceRelationIndexes,
    config: ComplexityAnalysisConfig,
) -> tuple[
    SurfaceAnchorSets,
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    SurfaceComplexityMetrics,
    bool,
    float,
    float,
    float,
]:
    anchors = _collect_analysis_anchor_nodes(
        snapshot, indexes, node.key, module_key, label_sets
    )
    symbol_name = node.key.name.removeprefix(f"{_module_dotted_name(source_path)}.")
    indirection_markers, stateful_markers, deprecation_markers = (
        _complexity_marker_buckets(
            config,
            source_path,
            symbol_name,
            source_text,
        )
    )
    metrics = _aggregate_surface_complexity_metrics(snapshot, indexes, node.key)
    blocked_by_current_cycle = bool(node.properties.get("current_cycle_status"))
    complexity_score, simplification_score, removable_score = (
        _complexity_surface_scores(
            metrics,
            anchors,
            blocked_by_current_cycle=blocked_by_current_cycle,
            indirection_markers=indirection_markers,
            stateful_markers=stateful_markers,
            deprecation_markers=deprecation_markers,
        )
    )
    return (
        anchors,
        indirection_markers,
        stateful_markers,
        deprecation_markers,
        metrics,
        blocked_by_current_cycle,
        complexity_score,
        simplification_score,
        removable_score,
    )


def _complexity_surface_scores(
    metrics: SurfaceComplexityMetrics,
    anchors: SurfaceAnchorSets,
    *,
    blocked_by_current_cycle: bool,
    indirection_markers: tuple[str, ...],
    stateful_markers: tuple[str, ...],
    deprecation_markers: tuple[str, ...],
) -> tuple[float, float, float]:
    return _complexity_scores(
        metrics,
        _complexity_score_inputs(
            anchors,
            blocked_by_current_cycle=blocked_by_current_cycle,
            indirection_markers=indirection_markers,
            stateful_markers=stateful_markers,
            deprecation_markers=deprecation_markers,
        ),
    )


def _complexity_score_inputs(
    anchors: SurfaceAnchorSets,
    *,
    blocked_by_current_cycle: bool,
    indirection_markers: tuple[str, ...],
    stateful_markers: tuple[str, ...],
    deprecation_markers: tuple[str, ...],
) -> ComplexityScoreInputs:
    return ComplexityScoreInputs(
        indirection_markers=indirection_markers,
        stateful_markers=stateful_markers,
        deprecation_markers=deprecation_markers,
        runtime_count=len(anchors.runtime),
        config_count=len(anchors.config),
        doc_count=len(anchors.docs),
        test_count=len(anchors.tests),
        blocked_by_current_cycle=blocked_by_current_cycle,
    )


def _complexity_candidate_context(
    payload: dict[str, object],
    *,
    config: ComplexityAnalysisConfig,
) -> ComplexityCandidateContext:
    anchors = cast("SurfaceAnchorSets", payload["anchors"])
    runtime_anchors, config_anchors, doc_anchors, test_anchors = (
        _complexity_candidate_anchor_slices(
            anchors,
            blocker_anchor_limit=config.blocker_anchor_limit,
        )
    )
    return ComplexityCandidateContext(
        anchors=anchors,
        metrics=cast("SurfaceComplexityMetrics", payload["metrics"]),
        runtime_anchors=runtime_anchors,
        config_anchors=config_anchors,
        doc_anchors=doc_anchors,
        test_anchors=test_anchors,
        blocked_by_current_cycle=bool(payload["blocked_by_current_cycle"]),
        simplification_score=float(payload["simplification_score"]),
        classification=str(payload["classification"]),
    )


def _evaluate_complexity_surface(
    snapshot: GraphSnapshot,
    root: Path,
    node: GraphNode,
    *,
    duplication_config: dict[str, object],
    family_names: set[str],
    family_cache: dict[str, DuplicateFamilyConfig | None],
    label_sets: AnalysisLabelSets,
    indexes: SurfaceRelationIndexes,
    text_cache: dict[str, str],
    config: ComplexityAnalysisConfig,
) -> dict[str, object] | None:
    prerequisites = _complexity_surface_prerequisites(
        snapshot,
        root,
        node,
        duplication_config=duplication_config,
        family_names=family_names,
        family_cache=family_cache,
        text_cache=text_cache,
    )
    if prerequisites is None:
        return None
    source_path, family, module_key, source_text = prerequisites
    (
        anchors,
        indirection_markers,
        stateful_markers,
        deprecation_markers,
        metrics,
        blocked_by_current_cycle,
        complexity_score,
        simplification_score,
        removable_score,
    ) = _complexity_surface_measurements(
        snapshot,
        node,
        source_path=source_path,
        module_key=module_key,
        source_text=source_text,
        label_sets=label_sets,
        indexes=indexes,
        config=config,
    )
    anchor_counts = _analysis_anchor_counts(anchors)
    if not _should_emit_complexity_candidate(
        config,
        complexity_score=complexity_score,
        removable_score=removable_score,
    ):
        return None
    classification, removal_confidence = _complexity_candidate_classification(
        config,
        removable_score=removable_score,
        anchor_counts=anchor_counts,
        blocked_by_current_cycle=blocked_by_current_cycle,
    )
    return _complexity_surface_payload(
        source_path=source_path,
        family_name=family.name,
        anchors=anchors,
        metrics=metrics,
        indirection_markers=indirection_markers,
        stateful_markers=stateful_markers,
        deprecation_markers=deprecation_markers,
        blocked_by_current_cycle=blocked_by_current_cycle,
        classification=classification,
        complexity_score=complexity_score,
        simplification_score=simplification_score,
        removable_score=removable_score,
        removal_confidence=removal_confidence,
    )


def _should_emit_complexity_candidate(
    config: ComplexityAnalysisConfig,
    *,
    complexity_score: float,
    removable_score: float,
) -> bool:
    return (
        complexity_score >= config.complexity_score_threshold
        or removable_score >= config.removable_score_threshold
    )


def _complexity_candidate_classification(
    config: ComplexityAnalysisConfig,
    *,
    removable_score: float,
    anchor_counts: dict[str, int],
    blocked_by_current_cycle: bool,
) -> tuple[str, str]:
    return _classify_complexity_candidate(
        config,
        removable_score=removable_score,
        runtime_count=anchor_counts["runtime_count"],
        config_count=anchor_counts["config_count"],
        doc_count=anchor_counts["doc_count"],
        blocked_by_current_cycle=blocked_by_current_cycle,
    )


def _complexity_surface_payload(
    *,
    source_path: str,
    family_name: str,
    anchors: SurfaceAnchorSets,
    metrics: SurfaceComplexityMetrics,
    indirection_markers: tuple[str, ...],
    stateful_markers: tuple[str, ...],
    deprecation_markers: tuple[str, ...],
    blocked_by_current_cycle: bool,
    classification: str,
    complexity_score: float,
    simplification_score: float,
    removable_score: float,
    removal_confidence: str,
) -> dict[str, object]:
    return {
        "source_path": source_path,
        "family_name": family_name,
        "anchors": anchors,
        "metrics": metrics,
        "indirection_markers": indirection_markers,
        "stateful_markers": stateful_markers,
        "deprecation_markers": deprecation_markers,
        "blocked_by_current_cycle": blocked_by_current_cycle,
        "classification": classification,
        "complexity_score": complexity_score,
        "simplification_score": simplification_score,
        "removable_score": removable_score,
        "removal_confidence": removal_confidence,
    }


def _emit_complexity_candidate(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
    config: ComplexityAnalysisConfig,
    node: GraphNode,
    payload: dict[str, object],
) -> None:
    context = _complexity_candidate_context(payload, config=config)
    candidate = _add_complexity_candidate_node(
        snapshot,
        today,
        config,
        node,
        payload,
        context=context,
    )
    _link_complexity_candidate(
        snapshot,
        project,
        candidate,
        node.key,
        context=context,
    )


def _complexity_candidate_anchor_slices(
    anchors: SurfaceAnchorSets,
    *,
    blocker_anchor_limit: int,
) -> tuple[
    tuple[NodeKey, ...],
    tuple[NodeKey, ...],
    tuple[NodeKey, ...],
    tuple[NodeKey, ...],
]:
    return (
        anchors.runtime[:blocker_anchor_limit],
        anchors.config[:blocker_anchor_limit],
        anchors.docs[:blocker_anchor_limit],
        anchors.tests[:blocker_anchor_limit],
    )


def _link_complexity_candidate(
    snapshot: GraphSnapshot,
    project: NodeKey,
    candidate: NodeKey,
    target: NodeKey,
    *,
    context: ComplexityCandidateContext,
) -> None:
    snapshot.add_relation(
        project, "CONTAINS", candidate, provenance="complexity_analysis"
    )
    snapshot.add_relation(
        target, "HAS_COMPLEXITY_SIGNAL", candidate, provenance="complexity_analysis"
    )
    snapshot.add_relation(
        candidate,
        "CANDIDATE_FOR_SIMPLIFICATION",
        target,
        provenance="complexity_analysis",
    )
    if context.classification == "removable_complexity":
        snapshot.add_relation(
            candidate, "CANDIDATE_FOR_REMOVAL", target, provenance="complexity_analysis"
        )
    for anchor in context.runtime_anchors:
        snapshot.add_relation(
            candidate, "JUSTIFIED_BY_RUNTIME", anchor, provenance="complexity_analysis"
        )
    for anchor in [*context.config_anchors, *context.doc_anchors]:
        snapshot.add_relation(
            candidate, "BLOCKED_BY_VARIANCE", anchor, provenance="complexity_analysis"
        )


def _add_complexity_candidate_node(
    snapshot: GraphSnapshot,
    today: str,
    config: ComplexityAnalysisConfig,
    node: GraphNode,
    payload: dict[str, object],
    *,
    context: ComplexityCandidateContext,
) -> NodeKey:
    blocker_context = _complexity_blocker_context(
        node,
        blocked_by_current_cycle=context.blocked_by_current_cycle,
    )
    return snapshot.add_node(
        "complexity_candidate",
        f"{node.key.label}:{node.key.name}",
        summary=f"Complexity analysis candidate for `{node.key.name}` in `{payload['family_name']}`.",
        source_path=str(payload["source_path"]),
        source_kind="complexity_candidate",
        family_name=str(payload["family_name"]),
        target_label=node.key.label,
        target_name=node.key.name,
        classification=context.classification,
        complexity_score=payload["complexity_score"],
        simplification_score=payload["simplification_score"],
        removable_score=payload["removable_score"],
        simplification_confidence="high"
        if context.simplification_score >= config.complexity_score_threshold + 2
        else "medium",
        removal_confidence=payload["removal_confidence"],
        branch_count=context.metrics.branch_count,
        nesting_depth=context.metrics.nesting_depth,
        call_count=context.metrics.call_count,
        helper_call_count=context.metrics.helper_call_count,
        abstraction_fanout=context.metrics.abstraction_fanout,
        api_surface_to_logic_ratio=context.metrics.api_surface_to_logic_ratio,
        runtime_anchor_count=len(context.anchors.runtime),
        config_anchor_count=len(context.anchors.config),
        doc_anchor_count=len(context.anchors.docs),
        test_anchor_count=len(context.anchors.tests),
        indirection_markers=payload["indirection_markers"],
        stateful_markers=payload["stateful_markers"],
        deprecation_markers=payload["deprecation_markers"],
        blocked_by_current_cycle=context.blocked_by_current_cycle,
        blocked_by_current_cycle_target_name=blocker_context["target_name"],
        blocked_by_current_cycle_score=blocker_context["score"],
        blocked_by_current_cycle_wip_markers=blocker_context["wip_markers"],
        runtime_anchors=[anchor.name for anchor in context.runtime_anchors],
        config_anchors=[anchor.name for anchor in context.config_anchors],
        doc_anchors=[anchor.name for anchor in context.doc_anchors],
        test_anchors=[anchor.name for anchor in context.test_anchors],
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="medium",
    )


def _complexity_blocker_context(
    node: GraphNode,
    *,
    blocked_by_current_cycle: bool,
) -> dict[str, object]:
    if not blocked_by_current_cycle:
        return {"target_name": None, "score": None, "wip_markers": None}
    return {
        "target_name": node.key.name,
        "score": node.properties.get("current_cycle_score"),
        "wip_markers": node.properties.get("current_cycle_wip_markers"),
    }


def _add_pipeline_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    contract_nodes: dict[str, NodeKey],
    adapter_nodes: dict[str, NodeKey],
) -> dict[str, NodeKey]:
    pipeline_nodes: dict[str, NodeKey] = {}
    _add_entity_pipeline_surfaces(
        snapshot,
        root,
        project,
        today,
        contract_nodes,
        adapter_nodes,
        pipeline_nodes,
    )
    _add_composite_pipeline_surfaces(
        snapshot,
        root,
        project,
        today,
        pipeline_nodes,
    )
    return pipeline_nodes


def _add_entity_pipeline_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    contract_nodes: dict[str, NodeKey],
    adapter_nodes: dict[str, NodeKey],
    pipeline_nodes: dict[str, NodeKey],
) -> None:
    entities_root = root / "configs" / "entities"
    for entity_path in sorted(entities_root.rglob(YAML_FILE_GLOB)):
        _add_entity_pipeline_surface(
            snapshot,
            root,
            project,
            today,
            entity_path,
            contract_nodes=contract_nodes,
            adapter_nodes=adapter_nodes,
            pipeline_nodes=pipeline_nodes,
        )


def _entity_pipeline_identity(
    entity_path: Path,
    payload: dict[str, object],
) -> tuple[str, str, str, str]:
    provider_name = str(payload.get("provider", entity_path.parent.name))
    entity_name = str(payload.get("entity", entity_path.stem))
    pipeline_payload = payload.get("pipeline")
    pipeline_name = f"{provider_name}_{entity_name}"
    pipeline_summary = f"Entity pipeline `{pipeline_name}`."
    if isinstance(pipeline_payload, dict):
        pipeline_name = str(pipeline_payload.get("pipeline_name", pipeline_name))
        pipeline_summary = str(pipeline_payload.get("description", pipeline_summary))
    return provider_name, entity_name, pipeline_name, pipeline_summary


def _link_entity_pipeline_dependencies(
    snapshot: GraphSnapshot,
    pipeline: NodeKey,
    *,
    pipeline_name: str,
    provider_name: str,
    entity_name: str,
    contract_nodes: dict[str, NodeKey],
    adapter_nodes: dict[str, NodeKey],
) -> None:
    entity_key = NodeKey("entity_config", pipeline_name)
    if entity_key in snapshot.nodes:
        snapshot.add_relation(
            pipeline, "BACKED_BY", entity_key, provenance="impact_pipelines"
        )
    provider_key = NodeKey("provider_surface", provider_name)
    if provider_key in snapshot.nodes:
        snapshot.add_relation(
            pipeline, "DEPENDS_ON", provider_key, provenance="impact_pipelines"
        )
    adapter_key = adapter_nodes.get(provider_name)
    if adapter_key is not None:
        snapshot.add_relation(
            pipeline, "DEPENDS_ON", adapter_key, provenance="impact_pipelines"
        )
    contract_key = contract_nodes.get(f"{provider_name}.{entity_name}")
    if contract_key is not None:
        snapshot.add_relation(
            pipeline, "DEPENDS_ON", contract_key, provenance="impact_pipelines"
        )
    config_artifact = _pipeline_source_config_artifact(snapshot, pipeline)
    if config_artifact in snapshot.nodes:
        snapshot.add_relation(
            pipeline, "DEFINED_BY", config_artifact, provenance="impact_pipelines"
        )
    _link_pipeline_doc_artifacts(
        snapshot,
        pipeline,
        _pipeline_doc_artifact_targets(
            snapshot,
            provider_name=provider_name,
            entity_name=entity_name,
        ),
        provenance="impact_pipeline_docs",
    )


def _add_entity_pipeline_surface(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    entity_path: Path,
    *,
    contract_nodes: dict[str, NodeKey],
    adapter_nodes: dict[str, NodeKey],
    pipeline_nodes: dict[str, NodeKey],
) -> None:
    payload = _read_yaml(entity_path)
    provider_name, entity_name, pipeline_name, pipeline_summary = (
        _entity_pipeline_identity(
            entity_path,
            payload,
        )
    )
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
    snapshot.add_relation(
        project, "HAS_PIPELINE", pipeline, provenance="impact_pipelines"
    )
    _link_entity_pipeline_dependencies(
        snapshot,
        pipeline,
        pipeline_name=pipeline_name,
        provider_name=provider_name,
        entity_name=entity_name,
        contract_nodes=contract_nodes,
        adapter_nodes=adapter_nodes,
    )


def _pipeline_source_config_artifact(
    snapshot: GraphSnapshot, pipeline: NodeKey
) -> NodeKey:
    source_path = snapshot.nodes[pipeline].properties.get("source_path", "")
    return NodeKey("config_artifact", str(source_path))


def _pipeline_doc_artifact_targets(
    snapshot: GraphSnapshot,
    *,
    provider_name: str,
    entity_name: str,
) -> tuple[NodeKey, ...]:
    entity_dash = entity_name.replace("_", "-")
    candidates = (
        f"docs/04-reference/providers/{provider_name}/{entity_dash}.md",
        f"docs/04-reference/pipelines/{provider_name}-{entity_dash}.md",
    )
    glob_prefix = f"docs/04-reference/pipelines/{provider_name}/"
    glob_suffix = f"-{entity_dash}-spec.md"
    doc_keys = [
        NodeKey("doc_artifact", path)
        for path in candidates
        if NodeKey("doc_artifact", path) in snapshot.nodes
    ]
    doc_keys.extend(
        node.key
        for node in snapshot.nodes.values()
        if node.key.label == "doc_artifact"
        and node.key.name.startswith(glob_prefix)
        and node.key.name.endswith(glob_suffix)
    )
    return tuple(sorted(set(doc_keys), key=lambda key: key.name))


def _link_pipeline_doc_artifacts(
    snapshot: GraphSnapshot,
    pipeline: NodeKey,
    doc_artifacts: tuple[NodeKey, ...],
    *,
    provenance: str,
) -> None:
    for doc_artifact in doc_artifacts:
        snapshot.add_relation(
            pipeline, "DESCRIBED_IN", doc_artifact, provenance=provenance
        )


def _add_composite_pipeline_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    pipeline_nodes: dict[str, NodeKey],
) -> None:
    composites_root = root / "configs" / "composites"
    for composite_path in sorted(composites_root.glob(YAML_FILE_GLOB)):
        _add_composite_pipeline_surface(
            snapshot,
            root,
            project,
            today,
            composite_path,
            pipeline_nodes=pipeline_nodes,
        )


def _composite_pipeline_name(
    composite_path: Path,
    composite_payload: object,
) -> str:
    composite_name = composite_path.stem
    if isinstance(composite_payload, dict):
        composite_name = str(composite_payload.get("name", composite_name))
    return composite_name


def _add_composite_pipeline_surface(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    composite_path: Path,
    *,
    pipeline_nodes: dict[str, NodeKey],
) -> None:
    payload = _read_yaml(composite_path)
    composite_payload = payload.get("composite")
    composite_name = _composite_pipeline_name(composite_path, composite_payload)
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
    snapshot.add_relation(
        project, "HAS_PIPELINE", pipeline, provenance="impact_pipelines"
    )
    composite_key = NodeKey("composite_config", composite_name)
    if composite_key in snapshot.nodes:
        snapshot.add_relation(
            pipeline, "BACKED_BY", composite_key, provenance="impact_pipelines"
        )
    config_artifact = NodeKey("config_artifact", _rel_path(root, composite_path))
    if config_artifact in snapshot.nodes:
        snapshot.add_relation(
            pipeline, "DEFINED_BY", config_artifact, provenance="impact_pipelines"
        )
    _link_pipeline_doc_artifacts(
        snapshot,
        pipeline,
        _pipeline_doc_artifact_targets(
            snapshot,
            provider_name="composite",
            entity_name=composite_name.removeprefix("composite_"),
        ),
        provenance="impact_pipeline_docs",
    )
    _link_composite_pipeline_dependencies(
        snapshot, pipeline, composite_payload, pipeline_nodes
    )


def _link_composite_pipeline_dependencies(
    snapshot: GraphSnapshot,
    pipeline: NodeKey,
    composite_payload: object,
    pipeline_nodes: dict[str, NodeKey],
) -> None:
    for dependency_key in _composite_pipeline_dependency_keys(
        composite_payload, pipeline_nodes
    ):
        snapshot.add_relation(
            pipeline,
            "DEPENDS_ON",
            dependency_key,
            provenance="impact_pipelines",
        )


def _composite_pipeline_dependency_keys(
    composite_payload: object,
    pipeline_nodes: dict[str, NodeKey],
) -> tuple[NodeKey, ...]:
    if not isinstance(composite_payload, dict):
        return ()
    keys: list[NodeKey] = []
    seed_pipeline = _composite_seed_pipeline_name(composite_payload.get("seed"))
    if seed_pipeline is not None and seed_pipeline in pipeline_nodes:
        keys.append(pipeline_nodes[seed_pipeline])
    keys.extend(
        _composite_dependency_pipeline_keys(
            composite_payload.get("dependencies"), pipeline_nodes
        )
    )
    return tuple(keys)


def _composite_seed_pipeline_name(seed: object) -> str | None:
    if not isinstance(seed, dict):
        return None
    seed_pipeline = seed.get("pipeline")
    return seed_pipeline if isinstance(seed_pipeline, str) else None


def _composite_dependency_pipeline_keys(
    dependencies: object,
    pipeline_nodes: dict[str, NodeKey],
) -> tuple[NodeKey, ...]:
    if not isinstance(dependencies, list):
        return ()
    keys: list[NodeKey] = []
    for dependency in dependencies:
        if not isinstance(dependency, dict):
            continue
        dependency_pipeline = dependency.get("pipeline")
        if (
            isinstance(dependency_pipeline, str)
            and dependency_pipeline in pipeline_nodes
        ):
            keys.append(pipeline_nodes[dependency_pipeline])
    return tuple(keys)


def _add_pipeline_normalization_edges(
    snapshot: GraphSnapshot,
    pipeline_nodes: dict[str, NodeKey],
    memory_mapping: dict[str, object],
) -> None:
    normalization_mapping = memory_mapping.get("normalization")
    if not isinstance(normalization_mapping, dict):
        return

    (
        relation_type,
        entity_relation_type,
        default_entity_modules,
        default_composite_modules,
        pipeline_overrides,
    ) = _normalization_edge_config(normalization_mapping)

    for (
        pipeline_name,
        pipeline_key,
        pipeline_kind,
        entity_key,
    ) in _pipeline_normalization_targets(
        snapshot,
        pipeline_nodes,
    ):
        modules = _pipeline_normalization_modules(
            pipeline_name,
            pipeline_kind,
            pipeline_overrides,
            default_entity_modules,
            default_composite_modules,
        )
        _link_pipeline_normalization_modules(
            snapshot,
            pipeline_key,
            entity_key=entity_key,
            pipeline_kind=pipeline_kind,
            modules=modules,
            relation_type=relation_type,
            entity_relation_type=entity_relation_type,
        )


def _pipeline_normalization_targets(
    snapshot: GraphSnapshot,
    pipeline_nodes: dict[str, NodeKey],
) -> tuple[tuple[str, NodeKey, str, NodeKey], ...]:
    targets: list[tuple[str, NodeKey, str, NodeKey]] = []
    for pipeline_name, pipeline_key in pipeline_nodes.items():
        pipeline_node = snapshot.nodes.get(pipeline_key)
        if pipeline_node is None:
            continue
        pipeline_kind = str(pipeline_node.properties.get("pipeline_kind", "entity"))
        targets.append(
            (
                pipeline_name,
                pipeline_key,
                pipeline_kind,
                NodeKey("entity_config", pipeline_name),
            )
        )
    return tuple(targets)


def _normalization_edge_config(
    normalization_mapping: dict[str, object],
) -> tuple[str, str, list[str], list[str], dict[str, object]]:
    relation_type = str(normalization_mapping.get("relation_type", "DEPENDS_ON"))
    entity_relation_type = str(
        normalization_mapping.get("entity_relation_type", relation_type)
    )
    defaults = normalization_mapping.get("defaults")
    default_entity_modules: list[str] = []
    default_composite_modules: list[str] = []
    if isinstance(defaults, dict):
        entity_defaults = defaults.get("entity")
        composite_defaults = defaults.get("composite")
        if isinstance(entity_defaults, dict):
            default_entity_modules = _as_string_list(entity_defaults.get("modules"))
        if isinstance(composite_defaults, dict):
            default_composite_modules = _as_string_list(
                composite_defaults.get("modules")
            )
    pipeline_entries = normalization_mapping.get("pipelines")
    pipeline_overrides = pipeline_entries if isinstance(pipeline_entries, dict) else {}
    return (
        relation_type,
        entity_relation_type,
        default_entity_modules,
        default_composite_modules,
        pipeline_overrides,
    )


def _pipeline_normalization_modules(
    pipeline_name: str,
    pipeline_kind: str,
    pipeline_overrides: dict[str, object],
    default_entity_modules: list[str],
    default_composite_modules: list[str],
) -> list[str]:
    modules = list(
        default_entity_modules
        if pipeline_kind == "entity"
        else default_composite_modules
    )
    pipeline_payload = pipeline_overrides.get(pipeline_name)
    if isinstance(pipeline_payload, dict):
        modules.extend(_as_string_list(pipeline_payload.get("modules")))
    return modules


def _link_pipeline_normalization_modules(
    snapshot: GraphSnapshot,
    pipeline_key: NodeKey,
    *,
    entity_key: NodeKey,
    pipeline_kind: str,
    modules: list[str],
    relation_type: str,
    entity_relation_type: str,
) -> None:
    seen_modules: set[str] = set()
    for module_path in modules:
        if module_path in seen_modules:
            continue
        seen_modules.add(module_path)
        module_key = NodeKey("module_surface", module_path)
        if module_key not in snapshot.nodes:
            continue
        snapshot.add_relation(
            pipeline_key, relation_type, module_key, provenance="impact_normalization"
        )
        if pipeline_kind == "entity" and entity_key in snapshot.nodes:
            snapshot.add_relation(
                entity_key,
                entity_relation_type,
                module_key,
                provenance="impact_normalization",
            )


def _build_normalization_pipeline_evidence() -> dict[str, dict[str, JsonValue]]:
    try:
        from bioetl.domain.normalization.profiles.registry import (
            NORMALIZATION_PROFILE_REGISTRY,
            resolve_normalization_profile_module_path,
        )
    except (AttributeError, ImportError):
        return {}

    evidence: dict[str, dict[str, JsonValue]] = {}
    for (provider, entity), profile in NORMALIZATION_PROFILE_REGISTRY.items():
        pipeline_name = f"{provider}_{entity}"
        payload = _empty_normalization_evidence_payload()
        payload["normalization_profile_registered"] = True
        payload["normalization_profile_module_path"] = (
            resolve_normalization_profile_module_path(provider, entity)
        )
        payload["profile_field_count"] = len(profile.field_rules)
        evidence[pipeline_name] = payload
    _finalize_normalization_evidence_defaults(evidence)
    return evidence


def _empty_normalization_evidence_payload() -> dict[str, JsonValue]:
    return {
        "profile_field_count": 0,
        "fallback_field_count": 0,
        "fallback_business_field_count": 0,
        "fallback_technical_passthrough_field_count": 0,
    }


def _accumulate_field_matrix_evidence(
    evidence: dict[str, dict[str, JsonValue]],
    rows: list[dict[str, object]],
    *,
    fallback_business: str,
    fallback_technical_passthrough: str,
) -> None:
    for row in rows:
        pipeline_name = str(row.get("pipeline_name", "")).strip()
        pipeline_kind = str(row.get("pipeline_kind", "")).strip()
        if not pipeline_name or pipeline_kind != "entity":
            continue
        payload = evidence.setdefault(
            pipeline_name, _empty_normalization_evidence_payload()
        )
        source = str(row.get("normalization_source", "")).strip()
        if source == "profile":
            payload["profile_field_count"] = (
                _coerce_int(payload["profile_field_count"]) + 1
            )
            continue
        payload["fallback_field_count"] = (
            _coerce_int(payload["fallback_field_count"]) + 1
        )
        if source == fallback_business:
            payload["fallback_business_field_count"] = (
                _coerce_int(payload["fallback_business_field_count"]) + 1
            )
        elif source == fallback_technical_passthrough:
            payload["fallback_technical_passthrough_field_count"] = (
                _coerce_int(payload["fallback_technical_passthrough_field_count"]) + 1
            )


def _enrich_registry_normalization_evidence(
    evidence: dict[str, dict[str, JsonValue]],
    registry: list[tuple[str, str]],
    resolve_module_path: Callable[[str, str], str | None],
) -> None:
    for provider, entity in registry:
        pipeline_name = f"{provider}_{entity}"
        payload = evidence.setdefault(
            pipeline_name, _empty_normalization_evidence_payload()
        )
        payload["normalization_profile_registered"] = True
        module_path = resolve_module_path(provider, entity)
        if module_path is not None:
            payload["normalization_profile_module_path"] = module_path


def _finalize_normalization_evidence_defaults(
    evidence: dict[str, dict[str, JsonValue]],
) -> None:
    for payload in evidence.values():
        payload.setdefault("normalization_profile_registered", False)


def _add_pipeline_normalization_evidence(
    snapshot: GraphSnapshot,
    pipeline_nodes: dict[str, NodeKey],
) -> None:
    evidence_by_pipeline = _build_normalization_pipeline_evidence()
    for (
        pipeline_name,
        entity_key,
        update_payload,
    ) in _iter_normalization_evidence_updates(
        pipeline_nodes,
        evidence_by_pipeline,
    ):
        pipeline = snapshot.add_node(
            "pipeline_surface", pipeline_name, **update_payload
        )
        if entity_key in snapshot.nodes:
            snapshot.add_node("entity_config", pipeline_name, **update_payload)
        _link_normalization_registry_module(
            snapshot,
            pipeline,
            entity_key=entity_key,
            module_path=update_payload["normalization_profile_module_path"],
        )


def _iter_normalization_evidence_updates(
    pipeline_nodes: dict[str, NodeKey],
    evidence_by_pipeline: dict[str, dict[str, JsonValue]],
) -> tuple[tuple[str, NodeKey, dict[str, JsonValue]], ...]:
    updates: list[tuple[str, NodeKey, dict[str, JsonValue]]] = []
    for pipeline_name, evidence in evidence_by_pipeline.items():
        if pipeline_nodes.get(pipeline_name) is None:
            continue
        updates.append(
            (
                pipeline_name,
                NodeKey("entity_config", pipeline_name),
                _normalization_evidence_update_payload(evidence),
            )
        )
    return tuple(updates)


def _normalization_evidence_update_payload(
    evidence: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    module_path = evidence.get("normalization_profile_module_path")
    return {
        "normalization_profile_registered": bool(
            evidence.get("normalization_profile_registered", False)
        ),
        "normalization_profile_module_path": (
            str(module_path) if isinstance(module_path, str) and module_path else None
        ),
        "profile_field_count": _coerce_int(evidence.get("profile_field_count", 0), 0),
        "fallback_field_count": _coerce_int(evidence.get("fallback_field_count", 0), 0),
        "fallback_business_field_count": _coerce_int(
            evidence.get("fallback_business_field_count", 0), 0
        ),
        "fallback_technical_passthrough_field_count": _coerce_int(
            evidence.get("fallback_technical_passthrough_field_count", 0), 0
        ),
    }


def _link_normalization_registry_module(
    snapshot: GraphSnapshot,
    pipeline: NodeKey,
    *,
    entity_key: NodeKey,
    module_path: JsonValue,
) -> None:
    if not isinstance(module_path, str) or not module_path:
        return
    module_key = NodeKey("module_surface", module_path)
    if module_key not in snapshot.nodes:
        return
    snapshot.add_relation(
        pipeline, "DEPENDS_ON", module_key, provenance="normalization_registry"
    )
    if entity_key in snapshot.nodes:
        snapshot.add_relation(
            entity_key, "DEPENDS_ON", module_key, provenance="normalization_registry"
        )


def _normalization_evidence_statements() -> list[dict[str, JsonValue]]:
    evidence_by_pipeline = _build_normalization_pipeline_evidence()
    statements: list[dict[str, JsonValue]] = []
    for pipeline_name, evidence in sorted(evidence_by_pipeline.items()):
        statements.append(_normalization_statement(pipeline_name, evidence))
    return statements


def _normalization_statement(
    pipeline_name: str,
    evidence: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    return {
        "statement": _NORMALIZATION_EVIDENCE_STATEMENT,
        "parameters": _normalization_statement_params(pipeline_name, evidence),
    }


_NORMALIZATION_EVIDENCE_STATEMENT = """
MATCH (p:pipeline_surface {name: $pipeline_name})
SET p.normalization_profile_registered = $normalization_profile_registered,
    p.normalization_profile_module_path = $normalization_profile_module_path,
    p.profile_field_count = $profile_field_count,
    p.fallback_field_count = $fallback_field_count,
    p.fallback_business_field_count = $fallback_business_field_count,
    p.fallback_technical_passthrough_field_count = $fallback_technical_passthrough_field_count
WITH p
OPTIONAL MATCH (p)-[rp:DEPENDS_ON {provenance: 'normalization_registry'}]->(:module_surface)
DELETE rp
WITH p
OPTIONAL MATCH (e:entity_config {name: $pipeline_name})
SET e.normalization_profile_registered = $normalization_profile_registered,
    e.normalization_profile_module_path = $normalization_profile_module_path,
    e.profile_field_count = $profile_field_count,
    e.fallback_field_count = $fallback_field_count,
    e.fallback_business_field_count = $fallback_business_field_count,
    e.fallback_technical_passthrough_field_count = $fallback_technical_passthrough_field_count
WITH p, e
OPTIONAL MATCH (e)-[re:DEPENDS_ON {provenance: 'normalization_registry'}]->(:module_surface)
DELETE re
WITH p, e
OPTIONAL MATCH (m:module_surface {name: $module_path})
FOREACH (_ IN CASE WHEN m IS NULL THEN [] ELSE [1] END |
    MERGE (p)-[:DEPENDS_ON {provenance: 'normalization_registry'}]->(m)
)
FOREACH (_ IN CASE WHEN e IS NULL OR m IS NULL THEN [] ELSE [1] END |
    MERGE (e)-[:DEPENDS_ON {provenance: 'normalization_registry'}]->(m)
)
RETURN $pipeline_name AS pipeline_name
""".strip()


def _normalization_statement_params(
    pipeline_name: str,
    evidence: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    module_path = evidence.get("normalization_profile_module_path")
    normalized_module_path = (
        str(module_path) if isinstance(module_path, str) and module_path else None
    )
    return {
        "pipeline_name": pipeline_name,
        "normalization_profile_registered": bool(
            evidence.get("normalization_profile_registered", False)
        ),
        "normalization_profile_module_path": normalized_module_path,
        "profile_field_count": _coerce_int(evidence.get("profile_field_count", 0), 0),
        "fallback_field_count": _coerce_int(evidence.get("fallback_field_count", 0), 0),
        "fallback_business_field_count": _coerce_int(
            evidence.get("fallback_business_field_count", 0), 0
        ),
        "fallback_technical_passthrough_field_count": _coerce_int(
            evidence.get("fallback_technical_passthrough_field_count", 0), 0
        ),
        "module_path": normalized_module_path,
    }


def _normalization_batch_pipeline_span(
    batch: list[dict[str, JsonValue]],
) -> tuple[str | None, str | None]:
    pipeline_names = _batch_pipeline_names(batch)
    if not pipeline_names:
        return None, None
    return pipeline_names[0], pipeline_names[-1]


def _emit_normalization_apply_progress(
    *,
    event: str,
    batch_index: int,
    batch_count: int,
    statement_count: int,
    pipeline_start: str | None,
    pipeline_end: str | None,
    elapsed_seconds: float | None = None,
) -> None:
    payload = _normalization_progress_payload(
        event=event,
        batch_index=batch_index,
        batch_count=batch_count,
        statement_count=statement_count,
        pipeline_start=pipeline_start,
        pipeline_end=pipeline_end,
        elapsed_seconds=elapsed_seconds,
    )
    sys.stderr.write(json.dumps(payload) + "\n")
    sys.stderr.flush()


def _batch_pipeline_names(batch: list[dict[str, JsonValue]]) -> list[str]:
    return [
        str(pipeline_name)
        for statement in batch
        for pipeline_name in [statement.get("parameters", {}).get("pipeline_name")]
        if isinstance(pipeline_name, str) and pipeline_name
    ]


def _normalization_progress_payload(
    *,
    event: str,
    batch_index: int,
    batch_count: int,
    statement_count: int,
    pipeline_start: str | None,
    pipeline_end: str | None,
    elapsed_seconds: float | None,
) -> dict[str, JsonValue]:
    payload: dict[str, JsonValue] = {
        "event": event,
        "sync_scope": "normalization_evidence_only",
        "batch_index": batch_index,
        "batch_count": batch_count,
        "statement_count": statement_count,
        "pipeline_start": pipeline_start,
        "pipeline_end": pipeline_end,
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }
    if elapsed_seconds is not None:
        payload["elapsed_seconds"] = round(elapsed_seconds, 3)
    return payload


def apply_normalization_evidence_only(
    root: Path,
    http_uri: str | None,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, JsonValue]:
    started_at = datetime.now(tz=UTC).isoformat()
    overall_started = time.perf_counter()
    base_uri, username, password, database = resolve_neo4j_connection(root, http_uri)
    client = Neo4jHttpClient(base_uri, username, password, database)
    evidence_started = time.perf_counter()
    statements = _normalization_evidence_statements()
    evidence_build_seconds = time.perf_counter() - evidence_started
    batches = _normalization_evidence_batches(statements, batch_size)
    batch_summaries: list[dict[str, JsonValue]] = []
    completed_statement_count = 0

    for batch_index, batch in enumerate(batches, start=1):
        batch_summary = _execute_normalization_evidence_batch(
            client,
            batch,
            batch_index=batch_index,
            batch_count=len(batches),
        )
        completed_statement_count += len(batch)
        batch_summaries.append(batch_summary)

    total_seconds = time.perf_counter() - overall_started
    return {
        "started_at": started_at,
        "pipeline_count": len(statements),
        "batch_count": len(batches),
        "batch_size": batch_size,
        "completed_statement_count": completed_statement_count,
        "evidence_build_seconds": round(evidence_build_seconds, 3),
        "total_seconds": round(total_seconds, 3),
        "batches": batch_summaries,
        "updated_at": datetime.now(tz=UTC).isoformat(),
    }


def _normalization_evidence_batches(
    statements: list[dict[str, JsonValue]],
    batch_size: int,
) -> list[list[dict[str, JsonValue]]]:
    return _batched(statements, batch_size)


def _execute_normalization_evidence_batch(
    client: Neo4jHttpClient,
    batch: list[dict[str, JsonValue]],
    *,
    batch_index: int,
    batch_count: int,
) -> dict[str, JsonValue]:
    pipeline_start, pipeline_end = _normalization_batch_pipeline_span(batch)
    _emit_normalization_batch_progress(
        event="batch_start",
        batch=batch,
        batch_index=batch_index,
        batch_count=batch_count,
        pipeline_start=pipeline_start,
        pipeline_end=pipeline_end,
    )
    batch_started = time.perf_counter()
    client.execute(
        batch,
        context=(
            "normalization evidence batch "
            f"{batch_index}/{batch_count} "
            f"pipelines {pipeline_start or '?'}..{pipeline_end or '?'}"
        ),
    )
    batch_elapsed = time.perf_counter() - batch_started
    _emit_normalization_batch_progress(
        event="batch_complete",
        batch=batch,
        batch_index=batch_index,
        batch_count=batch_count,
        pipeline_start=pipeline_start,
        pipeline_end=pipeline_end,
        elapsed_seconds=batch_elapsed,
    )
    return _normalization_batch_summary(
        batch=batch,
        batch_index=batch_index,
        pipeline_start=pipeline_start,
        pipeline_end=pipeline_end,
        elapsed_seconds=batch_elapsed,
    )


def _emit_normalization_batch_progress(
    *,
    event: str,
    batch: list[dict[str, JsonValue]],
    batch_index: int,
    batch_count: int,
    pipeline_start: str | None,
    pipeline_end: str | None,
    elapsed_seconds: float | None = None,
) -> None:
    _emit_normalization_apply_progress(
        event=event,
        batch_index=batch_index,
        batch_count=batch_count,
        statement_count=len(batch),
        pipeline_start=pipeline_start,
        pipeline_end=pipeline_end,
        elapsed_seconds=elapsed_seconds,
    )


def _normalization_batch_summary(
    *,
    batch: list[dict[str, JsonValue]],
    batch_index: int,
    pipeline_start: str | None,
    pipeline_end: str | None,
    elapsed_seconds: float,
) -> dict[str, JsonValue]:
    return {
        "batch_index": batch_index,
        "statement_count": len(batch),
        "pipeline_start": pipeline_start,
        "pipeline_end": pipeline_end,
        "elapsed_seconds": round(elapsed_seconds, 3),
    }


def _add_pipeline_test_edges(
    snapshot: GraphSnapshot,
    root: Path,
    _pipeline_nodes: dict[str, NodeKey],
    memory_mapping: dict[str, object],
) -> None:
    test_context = _pipeline_test_context(
        snapshot, root, memory_mapping.get("pipeline_tests")
    )
    if test_context is None:
        return
    test_linker = _pipeline_test_linker(snapshot, test_context.relation_type)
    _link_entity_pipeline_tests(
        test_linker,
        test_context.entity_pipeline_index,
        test_context.ownership,
    )
    _link_provider_regression_suite_tests(
        test_linker,
        test_context.provider_pipeline_index,
        suites=test_context.provider_regression_suites,
        enabled=test_context.include_provider_regression_suites,
    )


@dataclass(frozen=True)
class PipelineTestContext:
    relation_type: str
    ownership: dict[object, object]
    provider_regression_suites: object
    include_provider_regression_suites: bool
    entity_pipeline_index: dict[tuple[str, str], NodeKey]
    provider_pipeline_index: dict[str, list[NodeKey]]


def _pipeline_test_context(
    snapshot: GraphSnapshot,
    root: Path,
    tests_mapping: object,
) -> PipelineTestContext | None:
    relation_type, ownership_config, include_provider_regression_suites = (
        _pipeline_test_mapping_config(tests_mapping)
    )
    payload, ownership = _pipeline_test_payload(root, ownership_config)
    if payload is None or ownership is None:
        return None
    entity_pipeline_index, provider_pipeline_index = _pipeline_test_indexes(snapshot)
    return PipelineTestContext(
        relation_type=relation_type,
        ownership=ownership,
        provider_regression_suites=payload.get("provider_regression_suites"),
        include_provider_regression_suites=include_provider_regression_suites,
        entity_pipeline_index=entity_pipeline_index,
        provider_pipeline_index=provider_pipeline_index,
    )


def _pipeline_test_payload(
    root: Path,
    ownership_config: str,
) -> tuple[dict[str, object] | None, dict[object, object] | None]:
    ownership_path = _pipeline_test_ownership_path(root, ownership_config)
    if not ownership_path.is_file():
        return None, None
    payload = _read_yaml(ownership_path)
    return payload, _pipeline_test_ownership(payload)


def _pipeline_test_ownership_path(root: Path, ownership_config: str) -> Path:
    return root / ownership_config


def _pipeline_test_ownership(payload: dict[str, object]) -> dict[object, object] | None:
    ownership = payload.get("entity_test_ownership")
    return ownership if isinstance(ownership, dict) else None


def _pipeline_test_mapping_config(
    tests_mapping: object,
) -> tuple[str, str, bool]:
    if not isinstance(tests_mapping, dict):
        return "TESTED_BY", TEST_MATRIX_CONFIG_PATH, True
    return (
        str(tests_mapping.get("relation_type", "TESTED_BY")),
        str(tests_mapping.get("ownership_config", TEST_MATRIX_CONFIG_PATH)),
        bool(tests_mapping.get("provider_regression_suites", True)),
    )


def _pipeline_test_indexes(
    snapshot: GraphSnapshot,
) -> tuple[dict[tuple[str, str], NodeKey], dict[str, list[NodeKey]]]:
    return _entity_pipeline_test_index(snapshot), _provider_pipeline_test_index(
        snapshot
    )


def _entity_pipeline_test_index(
    snapshot: GraphSnapshot,
) -> dict[tuple[str, str], NodeKey]:
    return {
        identity: node.key
        for node in snapshot.nodes.values()
        for identity in [_entity_pipeline_node_identity(node)]
        if identity is not None
    }


def _entity_pipeline_node_identity(node: GraphNode) -> tuple[str, str] | None:
    if (
        node.key.label != "pipeline_surface"
        or node.properties.get("pipeline_kind") != "entity"
    ):
        return None
    return str(node.properties.get("provider")), str(node.properties.get("entity"))


def _provider_pipeline_test_index(snapshot: GraphSnapshot) -> dict[str, list[NodeKey]]:
    provider_pipeline_index: dict[str, list[NodeKey]] = {}
    for provider, node_key in _provider_pipeline_index_entries(snapshot):
        provider_pipeline_index.setdefault(provider, []).append(node_key)
    return provider_pipeline_index


def _provider_pipeline_index_entries(
    snapshot: GraphSnapshot,
) -> tuple[tuple[str, NodeKey], ...]:
    return tuple(
        (provider, node.key)
        for node in snapshot.nodes.values()
        for provider in [_provider_pipeline_index_key(node)]
        if provider is not None
    )


def _provider_pipeline_index_key(node: GraphNode) -> str | None:
    if node.key.label != "pipeline_surface":
        return None
    provider = node.properties.get("provider")
    return provider if isinstance(provider, str) else None


def _pipeline_test_linker(
    snapshot: GraphSnapshot,
    relation_type: str,
) -> Callable[[NodeKey, str, str], None]:
    def link_test_target(
        pipeline_key: NodeKey, test_path: str, provenance: str
    ) -> None:
        artifact_key = _test_artifact_key(test_path)
        if artifact_key not in snapshot.nodes:
            return
        _link_pipeline_test_artifact(
            snapshot, pipeline_key, relation_type, artifact_key, provenance
        )
        _link_pipeline_test_suite(
            snapshot, pipeline_key, relation_type, artifact_key, provenance
        )

    return link_test_target


def _test_artifact_key(test_path: str) -> NodeKey:
    return NodeKey("test_artifact", test_path)


def _link_pipeline_test_artifact(
    snapshot: GraphSnapshot,
    pipeline_key: NodeKey,
    relation_type: str,
    artifact_key: NodeKey,
    provenance: str,
) -> None:
    snapshot.add_relation(
        pipeline_key, relation_type, artifact_key, provenance=provenance
    )


def _link_pipeline_test_suite(
    snapshot: GraphSnapshot,
    pipeline_key: NodeKey,
    relation_type: str,
    artifact_key: NodeKey,
    provenance: str,
) -> None:
    suite_name = _pipeline_test_suite_name(snapshot, artifact_key)
    if suite_name is None:
        return
    snapshot.add_relation(
        pipeline_key,
        relation_type,
        NodeKey("test_surface", suite_name),
        provenance=provenance,
    )


def _pipeline_test_suite_name(
    snapshot: GraphSnapshot,
    artifact_key: NodeKey,
) -> str | None:
    return TEST_SURFACES.get(
        str(snapshot.nodes[artifact_key].properties.get("suite", ""))
    )


def _link_entity_pipeline_tests(
    link_test_target: Callable[[NodeKey, str, str], None],
    entity_pipeline_index: dict[tuple[str, str], NodeKey],
    ownership: dict[object, object],
) -> None:
    _link_pipeline_test_targets(
        link_test_target,
        _entity_pipeline_contract_tests(entity_pipeline_index, ownership),
        provenance="impact_pipeline_tests",
    )


def _entity_pipeline_contract_tests(
    entity_pipeline_index: dict[tuple[str, str], NodeKey],
    ownership: dict[object, object],
) -> tuple[tuple[NodeKey, tuple[str, ...]], ...]:
    return tuple(
        target
        for contract_ref, raw_tests in ownership.items()
        for target in [
            _entity_pipeline_contract_target(
                entity_pipeline_index, contract_ref, raw_tests
            )
        ]
        if target is not None
    )


def _entity_pipeline_contract_target(
    entity_pipeline_index: dict[tuple[str, str], NodeKey],
    contract_ref: object,
    raw_tests: object,
) -> tuple[NodeKey, tuple[str, ...]] | None:
    contract_identity = _contract_ref_identity(contract_ref)
    if contract_identity is None:
        return None
    pipeline_key = entity_pipeline_index.get(contract_identity)
    if pipeline_key is None:
        return None
    test_paths = tuple(_as_string_list(raw_tests))
    if not test_paths:
        return None
    return pipeline_key, test_paths


def _contract_ref_identity(contract_ref: object) -> tuple[str, str] | None:
    if not isinstance(contract_ref, str) or "." not in contract_ref:
        return None
    provider_name, entity_name = contract_ref.split(".", 1)
    return provider_name, entity_name


def _link_provider_regression_suite_tests(
    link_test_target: Callable[[NodeKey, str, str], None],
    provider_pipeline_index: dict[str, list[NodeKey]],
    *,
    suites: object,
    enabled: bool,
) -> None:
    if not enabled or not isinstance(suites, dict):
        return
    for suite_name, provider_targets in _provider_regression_suite_targets(suites):
        _link_provider_suite_targets(
            link_test_target,
            provider_pipeline_index,
            suite_name=suite_name,
            provider_targets=provider_targets,
        )


def _link_pipeline_test_targets(
    link_test_target: Callable[[NodeKey, str, str], None],
    targets: tuple[tuple[NodeKey, tuple[str, ...]], ...],
    *,
    provenance: str,
) -> None:
    for pipeline_key, test_paths in targets:
        _link_pipeline_test_paths(
            link_test_target,
            pipeline_key,
            test_paths,
            provenance=provenance,
        )


def _link_pipeline_test_paths(
    link_test_target: Callable[[NodeKey, str, str], None],
    pipeline_key: NodeKey,
    test_paths: tuple[str, ...],
    *,
    provenance: str,
) -> None:
    for test_path in test_paths:
        link_test_target(pipeline_key, test_path, provenance)


def _link_provider_suite_targets(
    link_test_target: Callable[[NodeKey, str, str], None],
    provider_pipeline_index: dict[str, list[NodeKey]],
    *,
    suite_name: str,
    provider_targets: tuple[tuple[str, str], ...],
) -> None:
    provenance = _provider_suite_provenance(suite_name)
    for provider_name, raw_test_path in provider_targets:
        for pipeline_key in provider_pipeline_index.get(provider_name, []):
            link_test_target(pipeline_key, raw_test_path, provenance)


def _provider_suite_provenance(suite_name: str) -> str:
    return f"impact_pipeline_regression_suite:{suite_name}"


def _provider_regression_suite_targets(
    suites: dict[object, object],
) -> tuple[tuple[str, tuple[tuple[str, str], ...]], ...]:
    return tuple(
        suite_target
        for suite_name, suite_payload in suites.items()
        for suite_target in [
            _provider_regression_suite_target(suite_name, suite_payload)
        ]
        if suite_target is not None
    )


def _provider_regression_suite_target(
    suite_name: object,
    suite_payload: object,
) -> tuple[str, tuple[tuple[str, str], ...]] | None:
    if not isinstance(suite_name, str) or not isinstance(suite_payload, dict):
        return None
    provider_targets = _provider_regression_provider_targets(suite_payload)
    if not provider_targets:
        return None
    return suite_name, provider_targets


def _provider_regression_provider_targets(
    suite_payload: dict[str, object],
) -> tuple[tuple[str, str], ...]:
    providers = suite_payload.get("providers")
    if not isinstance(providers, dict):
        return ()
    return tuple(
        target
        for provider_name, raw_test_path in providers.items()
        for target in [
            _provider_regression_provider_target(provider_name, raw_test_path)
        ]
        if target is not None
    )


def _provider_regression_provider_target(
    provider_name: object,
    raw_test_path: object,
) -> tuple[str, str] | None:
    if isinstance(provider_name, str) and isinstance(raw_test_path, str):
        return provider_name, raw_test_path
    return None


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

    dashboard_metrics, target_context = _alert_surface_context(
        snapshot,
        root,
        pipeline_nodes=pipeline_nodes,
        contract_nodes=contract_nodes,
        memory_mapping=memory_mapping,
    )
    for rules_path in _alert_rules_paths(rules_root):
        _add_alert_rule_file_surfaces(
            snapshot,
            root,
            project,
            today,
            rules_path,
            dashboard_metrics=dashboard_metrics,
            target_context=target_context,
            memory_mapping=memory_mapping,
        )


def _alert_rules_paths(rules_root: Path) -> tuple[Path, ...]:
    return tuple(sorted(rules_root.glob("*.y*ml")))


def _alert_surface_context(
    snapshot: GraphSnapshot,
    root: Path,
    *,
    pipeline_nodes: dict[str, NodeKey],
    contract_nodes: dict[str, NodeKey],
    memory_mapping: dict[str, object],
) -> tuple[dict[NodeKey, frozenset[str]], AlertTargetContext]:
    return (
        _dashboard_metric_index(root),
        _alert_target_context(
            snapshot,
            pipeline_nodes=pipeline_nodes,
            contract_nodes=contract_nodes,
            memory_mapping=memory_mapping,
        ),
    )


def _alert_target_context(
    snapshot: GraphSnapshot,
    *,
    pipeline_nodes: dict[str, NodeKey],
    contract_nodes: dict[str, NodeKey],
    memory_mapping: dict[str, object],
) -> AlertTargetContext:
    return AlertTargetContext(
        snapshot=snapshot,
        pipeline_nodes=pipeline_nodes,
        provider_nodes=_sorted_provider_surface_nodes(snapshot),
        contract_nodes=contract_nodes,
        memory_mapping=memory_mapping,
    )


def _sorted_provider_surface_nodes(snapshot: GraphSnapshot) -> list[NodeKey]:
    return sorted(
        (key for key in snapshot.nodes if key.label == "provider_surface"),
        key=lambda node: node.name,
    )


def _add_alert_rule_file_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    rules_path: Path,
    *,
    dashboard_metrics: dict[NodeKey, frozenset[str]],
    target_context: AlertTargetContext,
    memory_mapping: dict[str, object],
) -> None:
    file_context = _alert_rule_file_context(snapshot, root, today, rules_path)
    for group in _alert_rule_groups(file_context.payload):
        _add_alert_rule_group_surfaces(
            snapshot,
            root,
            project,
            today,
            rules_path,
            file_context.artifact,
            group,
            dashboard_metrics=dashboard_metrics,
            target_context=target_context,
            memory_mapping=memory_mapping,
        )


@dataclass(frozen=True)
class AlertRuleFileContext:
    payload: dict[str, object]
    artifact: NodeKey


def _alert_rule_file_context(
    snapshot: GraphSnapshot,
    root: Path,
    today: str,
    rules_path: Path,
) -> AlertRuleFileContext:
    return AlertRuleFileContext(
        payload=_alert_rule_file_payload(rules_path),
        artifact=_add_alert_rules_artifact(snapshot, root, rules_path, today),
    )


def _alert_rule_file_payload(rules_path: Path) -> dict[str, object]:
    return _read_yaml(rules_path)


def _add_alert_rules_artifact(
    snapshot: GraphSnapshot,
    root: Path,
    rules_path: Path,
    today: str,
) -> NodeKey:
    relative_path = _rel_path(root, rules_path)
    return snapshot.add_node(
        "config_artifact",
        relative_path,
        summary=f"Prometheus alert rules file `{rules_path.name}`.",
        source_path=relative_path,
        source_kind="prometheus_rules",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )


def _link_workflow_job_reusable_target(
    snapshot: GraphSnapshot,
    workflow_nodes: dict[str, NodeKey],
    workflow_name_by_relative_path: dict[str, str],
    job_context: WorkflowJobContext,
    reusable_workflow_ref: object,
) -> None:
    if isinstance(reusable_workflow_ref, str):
        _link_reusable_job_workflow(
            snapshot,
            workflow_nodes,
            workflow_name_by_relative_path,
            job_context,
            reusable_workflow_ref,
        )


def _alert_rule_groups(
    payload: dict[str, object],
) -> tuple[dict[str, object], ...]:
    groups = payload.get("groups")
    if not isinstance(groups, list):
        return ()
    return tuple(group for group in groups if isinstance(group, dict))


def _add_alert_surface_node(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    rules_path: Path,
    artifact: NodeKey,
    group_name: str,
    alert_name: str,
    annotations: dict[str, object],
    labels: dict[str, object],
) -> NodeKey:
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
    return alert


def _add_alert_rule_group_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    rules_path: Path,
    artifact: NodeKey,
    group: dict[str, object],
    *,
    dashboard_metrics: dict[NodeKey, frozenset[str]],
    target_context: AlertTargetContext,
    memory_mapping: dict[str, object],
) -> None:
    group_context = _alert_rule_group_context(group, rules_path)
    for rule in group_context.rules:
        _add_alert_surface_from_rule(
            snapshot,
            root,
            project,
            today,
            rules_path,
            artifact,
            group_name=group_context.group_name,
            rule=rule,
            dashboard_metrics=dashboard_metrics,
            target_context=target_context,
            memory_mapping=memory_mapping,
        )


def _alert_group_name(group: dict[str, object], rules_path: Path) -> str:
    return str(group.get("name", rules_path.stem))


def _alert_group_rules(group: dict[str, object]) -> tuple[dict[str, object], ...]:
    rules = group.get("rules")
    if not isinstance(rules, list):
        return ()
    return tuple(rule for rule in rules if isinstance(rule, dict))


@dataclass(frozen=True)
class AlertRuleGroupContext:
    group_name: str
    rules: tuple[dict[str, object], ...]


def _alert_rule_group_context(
    group: dict[str, object],
    rules_path: Path,
) -> AlertRuleGroupContext:
    return AlertRuleGroupContext(
        group_name=_alert_group_name(group, rules_path),
        rules=_alert_group_rules(group),
    )


def _add_single_alert_surface(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    rules_path: Path,
    artifact: NodeKey,
    group_name: str,
    rule: dict[str, object],
    *,
    dashboard_metrics: dict[NodeKey, frozenset[str]],
    target_context: AlertTargetContext,
    memory_mapping: dict[str, object],
) -> None:
    alert_context = _alert_rule_context(rule)
    if alert_context is None:
        return
    alert = _add_alert_surface_node(
        snapshot,
        root,
        project,
        today,
        rules_path,
        artifact,
        group_name,
        alert_context.alert_name,
        alert_context.annotations,
        alert_context.labels,
    )
    _link_alert_targets(
        snapshot,
        alert,
        alert_context.alert_name,
        group_name,
        rule,
        dashboard_metrics=dashboard_metrics,
        target_context=target_context,
        memory_mapping=memory_mapping,
    )
    _link_alert_runbook(
        snapshot,
        root,
        alert,
        alert_context.alert_name,
        alert_context.annotations,
        today,
    )


def _add_alert_surface_from_rule(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    rules_path: Path,
    artifact: NodeKey,
    *,
    group_name: str,
    rule: dict[str, object],
    dashboard_metrics: dict[NodeKey, frozenset[str]],
    target_context: AlertTargetContext,
    memory_mapping: dict[str, object],
) -> None:
    _add_single_alert_surface(
        snapshot,
        root,
        project,
        today,
        rules_path,
        artifact,
        group_name,
        rule,
        dashboard_metrics=dashboard_metrics,
        target_context=target_context,
        memory_mapping=memory_mapping,
    )


@dataclass(frozen=True)
class AlertRuleContext:
    alert_name: str
    annotations: dict[str, object]
    labels: dict[str, object]


def _alert_rule_context(rule: dict[str, object]) -> AlertRuleContext | None:
    alert_name = rule.get("alert")
    if not isinstance(alert_name, str):
        return None
    return AlertRuleContext(
        alert_name=alert_name,
        annotations=_alert_annotations(rule),
        labels=_alert_labels(rule),
    )


def _link_alert_targets(
    snapshot: GraphSnapshot,
    alert: NodeKey,
    alert_name: str,
    group_name: str,
    rule: dict[str, object],
    *,
    dashboard_metrics: dict[NodeKey, frozenset[str]],
    target_context: AlertTargetContext,
    memory_mapping: dict[str, object],
) -> None:
    expr, dimensions = _alert_target_inputs(rule)
    selection = _select_alert_targets(
        target_context,
        alert_name,
        group_name,
        expr,
        dimensions,
    )
    _link_selected_alert_targets(snapshot, alert, selection)
    _link_alert_observer_dashboards(
        snapshot,
        alert,
        alert_name,
        group_name,
        expr,
        dashboard_metrics,
        memory_mapping,
    )


@dataclass(frozen=True)
class AlertTargetInputs:
    expr: str
    dimensions: set[str]


@dataclass(frozen=True)
class AlertTargetSelection:
    selected_pipelines: tuple[NodeKey, ...]
    selected_providers: tuple[NodeKey, ...]
    selected_contracts: tuple[NodeKey, ...]


@dataclass(frozen=True)
class ComplexityCandidateContext:
    anchors: SurfaceAnchorSets
    metrics: SurfaceComplexityMetrics
    runtime_anchors: tuple[NodeKey, ...]
    config_anchors: tuple[NodeKey, ...]
    doc_anchors: tuple[NodeKey, ...]
    test_anchors: tuple[NodeKey, ...]
    blocked_by_current_cycle: bool
    simplification_score: float
    classification: str


def _alert_target_inputs(rule: dict[str, object]) -> tuple[str, set[str]]:
    annotations = _alert_annotations(rule)
    expr = str(rule.get("expr", ""))
    context = AlertTargetInputs(
        expr=expr,
        dimensions=_runtime_dimensions(expr, _alert_dimension_text(annotations)),
    )
    return context.expr, context.dimensions


def _alert_annotations(rule: dict[str, object]) -> dict[str, object]:
    annotations = rule.get("annotations")
    return annotations if isinstance(annotations, dict) else {}


def _alert_labels(rule: dict[str, object]) -> dict[str, object]:
    labels = rule.get("labels")
    return labels if isinstance(labels, dict) else {}


def _alert_dimension_text(annotations: dict[str, object]) -> str:
    return " ".join(str(value) for value in annotations.values())


def _link_selected_alert_targets(
    snapshot: GraphSnapshot,
    alert: NodeKey,
    selection: AlertTargetSelection,
) -> None:
    for target_group in _selected_alert_target_groups(selection):
        _link_alert_target_group(snapshot, alert, target_group)


def _selected_alert_target_groups(
    selection: AlertTargetSelection,
) -> tuple[tuple[NodeKey, ...], ...]:
    return tuple(
        targets
        for targets in (
            selection.selected_pipelines,
            selection.selected_providers,
            selection.selected_contracts,
        )
        if targets
    )


def _link_alert_target_group(
    snapshot: GraphSnapshot,
    alert: NodeKey,
    targets: tuple[NodeKey, ...],
) -> None:
    for target in targets:
        snapshot.add_relation(alert, "DEPENDS_ON", target, provenance="impact_alerts")


def _link_alert_observer_dashboards(
    snapshot: GraphSnapshot,
    alert: NodeKey,
    alert_name: str,
    group_name: str,
    expr: str,
    dashboard_metrics: dict[NodeKey, frozenset[str]],
    memory_mapping: dict[str, object],
) -> None:
    for dashboard in _existing_snapshot_nodes(
        snapshot,
        _selected_alert_dashboards(
            alert_name,
            group_name,
            expr,
            dashboard_metrics,
            memory_mapping,
        ),
    ):
        snapshot.add_relation(
            alert, "OBSERVED_BY", dashboard, provenance="impact_alerts"
        )


def _existing_snapshot_nodes(
    snapshot: GraphSnapshot,
    nodes: Iterable[NodeKey],
) -> tuple[NodeKey, ...]:
    return tuple(node for node in nodes if node in snapshot.nodes)


def _selected_alert_dashboards(
    alert_name: str,
    group_name: str,
    expr: str,
    dashboard_metrics: dict[NodeKey, frozenset[str]],
    memory_mapping: dict[str, object],
) -> tuple[NodeKey, ...]:
    return tuple(
        _select_alert_dashboards(
            alert_name,
            group_name,
            expr,
            dashboard_metrics,
            memory_mapping,
        )
    )


def _link_alert_runbook(
    snapshot: GraphSnapshot,
    root: Path,
    alert: NodeKey,
    alert_name: str,
    annotations: dict[str, object],
    today: str,
) -> None:
    runbook_context = _alert_runbook_context(root, annotations)
    if runbook_context is None:
        return
    doc = _add_alert_runbook_doc(snapshot, alert_name, runbook_context.runbook, today)
    snapshot.add_relation(alert, "DESCRIBED_IN", doc, provenance="impact_alerts")


@dataclass(frozen=True)
class AlertRunbookContext:
    runbook: str


def _alert_runbook_context(
    root: Path,
    annotations: dict[str, object],
) -> AlertRunbookContext | None:
    runbook = _alert_runbook_path(root, annotations)
    if runbook is None:
        return None
    return AlertRunbookContext(runbook=runbook)


def _alert_runbook_path(root: Path, annotations: dict[str, object]) -> str | None:
    runbook = annotations.get("runbook")
    if not isinstance(runbook, str):
        return None
    return runbook if (root / runbook).is_file() else None


def _add_alert_runbook_doc(
    snapshot: GraphSnapshot,
    alert_name: str,
    runbook: str,
    today: str,
) -> NodeKey:
    return snapshot.add_node(
        "doc_artifact",
        runbook,
        summary=f"Runbook referenced by alert `{alert_name}`.",
        source_path=runbook,
        source_kind="alert_runbook",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )


def _add_governance_edges(
    snapshot: GraphSnapshot,
    port_nodes: set[NodeKey],
    adapter_nodes: dict[str, NodeKey],
    pipeline_nodes: dict[str, NodeKey],
    contract_nodes: dict[str, NodeKey],
) -> None:
    for policy, target_groups in _governance_policy_targets(
        snapshot,
        port_nodes=port_nodes,
        adapter_nodes=adapter_nodes,
        pipeline_nodes=pipeline_nodes,
        contract_nodes=contract_nodes,
    ):
        _link_policy_governance_group(snapshot, policy, *target_groups)


def _governance_policy_targets(
    snapshot: GraphSnapshot,
    *,
    port_nodes: set[NodeKey],
    adapter_nodes: dict[str, NodeKey],
    pipeline_nodes: dict[str, NodeKey],
    contract_nodes: dict[str, NodeKey],
) -> tuple[tuple[NodeKey, tuple[Sequence[NodeKey], ...]], ...]:
    sorted_ports, sorted_adapters, sorted_pipelines, sorted_contracts = (
        _sorted_governance_targets(
            port_nodes=port_nodes,
            adapter_nodes=adapter_nodes,
            pipeline_nodes=pipeline_nodes,
            contract_nodes=contract_nodes,
        )
    )
    return tuple(
        _governance_policy_specs(
            snapshot,
            sorted_ports=sorted_ports,
            sorted_adapters=sorted_adapters,
            sorted_pipelines=sorted_pipelines,
            sorted_contracts=sorted_contracts,
        )
    )


def _sorted_governance_targets(
    *,
    port_nodes: set[NodeKey],
    adapter_nodes: dict[str, NodeKey],
    pipeline_nodes: dict[str, NodeKey],
    contract_nodes: dict[str, NodeKey],
) -> tuple[list[NodeKey], list[NodeKey], list[NodeKey], list[NodeKey]]:
    return (
        sorted(port_nodes, key=lambda node: node.name),
        sorted(adapter_nodes.values(), key=lambda node: node.name),
        sorted(pipeline_nodes.values(), key=lambda node: node.name),
        sorted(contract_nodes.values(), key=lambda node: node.name),
    )


def _governance_policy_specs(
    snapshot: GraphSnapshot,
    *,
    sorted_ports: list[NodeKey],
    sorted_adapters: list[NodeKey],
    sorted_pipelines: list[NodeKey],
    sorted_contracts: list[NodeKey],
) -> list[tuple[NodeKey, tuple[Sequence[NodeKey], ...]]]:
    return [
        _governance_policy_spec(*policy)
        for policy in _governance_policy_definitions(
            snapshot,
            sorted_ports=sorted_ports,
            sorted_adapters=sorted_adapters,
            sorted_pipelines=sorted_pipelines,
            sorted_contracts=sorted_contracts,
        )
    ]


def _governance_policy_definitions(
    snapshot: GraphSnapshot,
    *,
    sorted_ports: list[NodeKey],
    sorted_adapters: list[NodeKey],
    sorted_pipelines: list[NodeKey],
    sorted_contracts: list[NodeKey],
) -> tuple[tuple[str, Sequence[NodeKey], Sequence[NodeKey] | None], ...]:
    return (
        ("hexagonal import matrix", sorted_ports, sorted_adapters),
        ("hexagonal package layout", sorted_ports, sorted_adapters),
        ("pipeline assembly model", sorted_pipelines, None),
        ("medallion storage contract", sorted_contracts, sorted_pipelines),
        ("observability surface model", _alert_surface_nodes(snapshot), None),
    )


def _governance_policy_spec(
    policy_name: str,
    target_group: Sequence[NodeKey],
    extra_target_group: Sequence[NodeKey] | None = None,
) -> tuple[NodeKey, tuple[Sequence[NodeKey], ...]]:
    return NodeKey("policy_surface", policy_name), _governance_target_groups(
        target_group,
        extra_target_group,
    )


def _governance_target_groups(
    target_group: Sequence[NodeKey],
    extra_target_group: Sequence[NodeKey] | None = None,
) -> tuple[Sequence[NodeKey], ...]:
    return (
        (target_group,)
        if extra_target_group is None
        else (target_group, extra_target_group)
    )


def _link_policy_governance_group(
    snapshot: GraphSnapshot,
    policy: NodeKey,
    *target_groups: Sequence[NodeKey],
) -> None:
    if policy not in snapshot.nodes:
        return
    for targets in target_groups:
        for target in targets:
            snapshot.add_relation(
                policy, "GOVERNS", target, provenance="impact_governance"
            )


def _alert_surface_nodes(snapshot: GraphSnapshot) -> list[NodeKey]:
    return [
        node_key
        for node_key in sorted(snapshot.nodes, key=lambda node: (node.label, node.name))
        if node_key.label == "alert_surface"
    ]


def _pipeline_operational_section(
    memory_mapping: dict[str, object],
) -> dict[str, object]:
    return _mapping_section(memory_mapping, "pipeline_operational")


def _pipeline_dashboard_targets(
    pipeline_ops: dict[str, object],
) -> tuple[list[NodeKey], list[NodeKey], list[NodeKey]]:
    dashboards_cfg, kind_dashboards = _pipeline_dashboard_config(pipeline_ops)

    common_dashboards = _configured_node_keys(
        "dashboard_surface",
        dashboards_cfg.get("common"),
        DEFAULT_COMMON_PIPELINE_DASHBOARDS,
    )
    entity_dashboards = _configured_node_keys(
        "dashboard_surface",
        kind_dashboards.get("entity"),
        DEFAULT_ENTITY_PIPELINE_DASHBOARDS,
    )
    composite_dashboards = _configured_node_keys(
        "dashboard_surface",
        kind_dashboards.get("composite"),
        DEFAULT_COMPOSITE_PIPELINE_DASHBOARDS,
    )
    return common_dashboards, entity_dashboards, composite_dashboards


def _pipeline_dashboard_config(
    pipeline_ops: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    dashboards_cfg = pipeline_ops.get("dashboards")
    if not isinstance(dashboards_cfg, dict):
        dashboards_cfg = {}
    kind_dashboards = dashboards_cfg.get("by_kind")
    if not isinstance(kind_dashboards, dict):
        kind_dashboards = {}
    return dashboards_cfg, kind_dashboards


def _pipeline_kind_dashboards(
    pipeline_kind: object,
    *,
    entity_dashboards: list[NodeKey],
    composite_dashboards: list[NodeKey],
) -> list[NodeKey]:
    if pipeline_kind == "entity":
        return entity_dashboards
    if pipeline_kind == "composite":
        return composite_dashboards
    return []


@dataclass(frozen=True)
class PipelineOperationalContext:
    runtime_paths: list[NodeKey]
    validation_gates: list[NodeKey]
    common_dashboards: list[NodeKey]
    entity_dashboards: list[NodeKey]
    composite_dashboards: list[NodeKey]


def _link_pipeline_operational_targets(
    snapshot: GraphSnapshot,
    pipeline: NodeKey,
    *,
    runtime_paths: list[NodeKey],
    validation_gates: list[NodeKey],
    common_dashboards: list[NodeKey],
    kind_dashboards: list[NodeKey],
) -> None:
    _link_existing_targets(
        snapshot,
        pipeline,
        "RUNS_VIA",
        runtime_paths,
        provenance="impact_pipeline_ops",
    )
    _link_existing_targets(
        snapshot,
        pipeline,
        "VALIDATED_BY",
        validation_gates,
        provenance="impact_pipeline_ops",
    )
    _link_existing_targets(
        snapshot,
        pipeline,
        "OBSERVED_BY",
        common_dashboards,
        provenance="impact_pipeline_ops",
    )
    if kind_dashboards:
        _link_existing_targets(
            snapshot,
            pipeline,
            "OBSERVED_BY",
            kind_dashboards,
            provenance="impact_pipeline_ops",
        )


def _add_pipeline_operational_edges(
    snapshot: GraphSnapshot,
    pipeline_nodes: dict[str, NodeKey],
    memory_mapping: dict[str, object],
) -> None:
    operational_context = _pipeline_operational_context(memory_mapping)
    for pipeline in _sorted_pipeline_nodes(pipeline_nodes):
        _link_pipeline_operational_for_pipeline(
            snapshot,
            pipeline,
            operational_context=operational_context,
        )


def _pipeline_operational_context(
    memory_mapping: dict[str, object],
) -> PipelineOperationalContext:
    pipeline_ops = _pipeline_operational_section(memory_mapping)
    runtime_paths, validation_gates = _pipeline_operational_targets_config(pipeline_ops)
    common_dashboards, entity_dashboards, composite_dashboards = (
        _pipeline_dashboard_targets(pipeline_ops)
    )
    return PipelineOperationalContext(
        runtime_paths=runtime_paths,
        validation_gates=validation_gates,
        common_dashboards=common_dashboards,
        entity_dashboards=entity_dashboards,
        composite_dashboards=composite_dashboards,
    )


def _pipeline_operational_targets_config(
    pipeline_ops: dict[str, object],
) -> tuple[list[NodeKey], list[NodeKey]]:
    runtime_paths = _configured_node_keys(
        "execution_path",
        pipeline_ops.get("runtime_paths"),
        DEFAULT_PIPELINE_RUNTIME_PATHS,
    )
    validation_gates = _configured_node_keys(
        "quality_gate",
        pipeline_ops.get("validation_gates"),
        DEFAULT_PIPELINE_VALIDATION_GATES,
    )
    return runtime_paths, validation_gates


def _sorted_pipeline_nodes(pipeline_nodes: dict[str, NodeKey]) -> list[NodeKey]:
    return sorted(pipeline_nodes.values(), key=lambda node: node.name)


def _link_pipeline_operational_for_pipeline(
    snapshot: GraphSnapshot,
    pipeline: NodeKey,
    *,
    operational_context: PipelineOperationalContext,
) -> None:
    pipeline_props = snapshot.nodes[pipeline].properties
    pipeline_kind = pipeline_props.get("pipeline_kind")
    _link_pipeline_operational_targets(
        snapshot,
        pipeline,
        runtime_paths=operational_context.runtime_paths,
        validation_gates=operational_context.validation_gates,
        common_dashboards=operational_context.common_dashboards,
        kind_dashboards=_pipeline_kind_dashboards(
            pipeline_kind,
            entity_dashboards=operational_context.entity_dashboards,
            composite_dashboards=operational_context.composite_dashboards,
        ),
    )


class Neo4jHttpClient:
    def __init__(
        self, base_uri: str, username: str, password: str, database: str
    ) -> None:
        self._endpoint = f"{base_uri}/db/{database}/tx/commit"
        self._primary_endpoint = self._endpoint
        parsed = parse.urlparse(base_uri)
        self._fallback_endpoint: str | None = None
        if parsed.hostname == "host.docker.internal":
            fallback_base = (
                parsed._replace(netloc=f"localhost:{parsed.port or 7474}")
                .geturl()
                .rstrip("/")
            )
            self._fallback_endpoint = f"{fallback_base}/db/{database}/tx/commit"
        auth_token = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
        self._headers = {
            "Authorization": f"Basic {auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def execute(
        self,
        statements: list[dict[str, JsonValue]],
        *,
        context: str | None = None,
    ) -> dict[str, object]:
        payload = json.dumps({"statements": statements}).encode("utf-8")
        last_exc: Exception | None = None
        attempt_errors: list[str] = []
        for attempt in range(12):
            endpoint = self._endpoint
            try:
                raw = self._execute_request(payload)
                break
            except error.HTTPError as exc:  # pragma: no cover - live backend dependent
                last_exc = self._handle_http_error(
                    endpoint,
                    exc,
                    context=context,
                    attempt=attempt,
                    attempt_errors=attempt_errors,
                )
                continue
            except (
                error.URLError,
                TimeoutError,
                ConnectionResetError,
                ConnectionAbortedError,
                http.client.RemoteDisconnected,
            ) as exc:  # pragma: no cover - network errors vary per environment
                last_exc = self._handle_transport_error(
                    endpoint,
                    exc,
                    context=context,
                    attempt=attempt,
                    attempt_errors=attempt_errors,
                )
                continue
        else:  # pragma: no cover - loop always breaks or raises
            raise RuntimeError(
                self._format_transport_error(
                    last_exc,
                    context=context,
                    attempt_errors=attempt_errors,
                )
            )
        body = json.loads(raw)
        errors = body.get("errors", [])
        if errors:
            prefix = self._context_prefix(context)
            raise RuntimeError(f"{prefix}Neo4j query/runtime error: {errors}")
        return body

    def _execute_request(self, payload: bytes) -> str:
        req = request.Request(
            self._endpoint,
            data=payload,
            headers=self._headers,
            method="POST",
        )
        response_cm = request.urlopen(req, timeout=60)
        with response_cm as response:
            return response.read().decode("utf-8")

    def _handle_http_error(
        self,
        endpoint: str,
        exc: error.HTTPError,
        *,
        context: str | None,
        attempt: int,
        attempt_errors: list[str],
    ) -> RuntimeError:
        body_text = exc.read().decode("utf-8", errors="replace")
        attempt_errors.append(
            self._format_transport_attempt(
                endpoint=endpoint,
                exc=exc,
                body_text=body_text,
            )
        )
        if not self._should_retry_http_error(exc):
            raise RuntimeError(
                self._format_query_error(exc, context=context, body_text=body_text)
            ) from exc
        runtime_error = RuntimeError(
            self._format_transport_error(
                exc,
                context=context,
                body_text=body_text,
                attempt_errors=attempt_errors,
            )
        )
        self._retry_or_raise(runtime_error, endpoint, exc, attempt)
        return runtime_error

    def _handle_transport_error(
        self,
        endpoint: str,
        exc: Exception,
        *,
        context: str | None,
        attempt: int,
        attempt_errors: list[str],
    ) -> RuntimeError:
        attempt_errors.append(
            self._format_transport_attempt(endpoint=endpoint, exc=exc)
        )
        runtime_error = RuntimeError(
            self._format_transport_error(
                exc,
                context=context,
                attempt_errors=attempt_errors,
            )
        )
        self._retry_or_raise(runtime_error, endpoint, exc, attempt)
        return runtime_error

    def _retry_or_raise(
        self,
        runtime_error: RuntimeError,
        endpoint: str,
        exc: Exception,
        attempt: int,
    ) -> None:
        if self._switch_to_fallback_endpoint():
            return
        if endpoint != self._primary_endpoint or self._is_last_attempt(attempt):
            raise runtime_error from exc
        self._sleep_before_retry(attempt)

    @staticmethod
    def _should_retry_http_error(exc: error.HTTPError) -> bool:
        return exc.code in {429, 502, 503, 504}

    def _switch_to_fallback_endpoint(self) -> bool:
        if self._fallback_endpoint and self._endpoint != self._fallback_endpoint:
            self._endpoint = self._fallback_endpoint
            self._fallback_endpoint = None
            return True
        return False

    @staticmethod
    def _is_last_attempt(attempt: int) -> bool:
        return attempt == 11

    @staticmethod
    def _sleep_before_retry(attempt: int) -> None:
        time.sleep(min(3.0, 0.5 * (attempt + 1)))

    def query(
        self,
        statement: str,
        parameters: dict[str, JsonValue] | None = None,
        *,
        context: str | None = None,
    ) -> list[dict[str, JsonValue]]:
        body = self.execute(
            [
                {
                    "statement": statement,
                    "parameters": parameters or {},
                }
            ],
            context=context,
        )
        results = body.get("results", [])
        if not results:
            return []
        result = results[0]
        columns = result.get("columns", [])
        rows: list[dict[str, JsonValue]] = []
        for entry in result.get("data", []):
            raw_row = entry.get("row", [])
            row = {str(column): raw_row[index] for index, column in enumerate(columns)}
            rows.append(row)
        return rows

    @staticmethod
    def _context_prefix(context: str | None) -> str:
        return f"Neo4j {context} failed: " if context else ""

    def _format_transport_error(
        self,
        exc: Exception | None,
        *,
        context: str | None,
        body_text: str | None = None,
        attempt_errors: list[str] | None = None,
    ) -> str:
        prefix = self._context_prefix(context)
        detail = f"{exc}"
        if body_text:
            detail = f"{detail}; response={body_text[:500]}"
        attempts_suffix = ""
        if attempt_errors:
            attempts_suffix = " | attempts: " + " ; ".join(attempt_errors)
        return f"{prefix}transport error reaching HTTP endpoint {self._endpoint}: {detail}{attempts_suffix}"

    @staticmethod
    def _format_transport_attempt(
        *,
        endpoint: str,
        exc: Exception,
        body_text: str | None = None,
    ) -> str:
        detail = f"{type(exc).__name__}: {exc}"
        if body_text:
            detail = f"{detail}; response={body_text[:200]}"
        return f"{endpoint} -> {detail}"

    def _format_query_error(
        self,
        exc: error.HTTPError,
        *,
        context: str | None,
        body_text: str,
    ) -> str:
        prefix = self._context_prefix(context)
        detail: object = body_text[:500]
        try:
            payload = json.loads(body_text)
        except json.JSONDecodeError:
            payload = detail
        else:
            if isinstance(payload, dict) and isinstance(payload.get("errors"), list):
                detail = payload["errors"]
        return f"{prefix}query/runtime error (HTTP {exc.code}): {detail}"


def _sync_run_id() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _neo4j_property_value(value: JsonValue) -> JsonScalar | list[JsonScalar]:
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    if isinstance(value, list):
        normalized_items: list[JsonScalar] = []
        for item in value:
            if isinstance(item, dict | list):
                normalized_items.append(json.dumps(item, sort_keys=True))
            else:
                normalized_items.append(item)
        return normalized_items
    return value


def _managed_properties(
    properties: dict[str, JsonValue], sync_run: str
) -> dict[str, JsonValue]:
    managed = {key: _neo4j_property_value(value) for key, value in properties.items()}
    managed["managed_by"] = DEFAULT_MANAGED_BY
    managed["sync_run"] = sync_run
    managed.setdefault("ingest_wave", DEFAULT_INGEST_WAVE)
    return managed


def _node_statement(node: GraphNode, sync_run: str) -> dict[str, JsonValue]:
    return {
        "statement": (
            f"MERGE (n:`{node.key.label}` {{name: $name}}) SET n += $properties"
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


def _reset_managed_relations_statement(
    relation_types: list[str],
) -> dict[str, JsonValue]:
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


def _delete_managed_wave_nodes_statement(
    label: str, limit: int
) -> dict[str, JsonValue]:
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
            "limit": limit,
        },
    }


def _prune_legacy_unmanaged_nodes_statement(
    managed_labels: list[str],
) -> dict[str, JsonValue]:
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


def _resolved_sync_apply_options(
    options: SyncApplyOptions | int | None,
    legacy_kwargs: dict[str, object],
) -> SyncApplyOptions:
    if isinstance(options, SyncApplyOptions):
        return options

    resolved_batch_size = _legacy_or_default_batch_size(options, legacy_kwargs)
    if not isinstance(resolved_batch_size, int):
        raise TypeError("sync_snapshot requires batch_size or SyncApplyOptions")
    return SyncApplyOptions(
        batch_size=resolved_batch_size,
        prune_stale=bool(legacy_kwargs.get("prune_stale", False)),
        full_reset_managed_wave=bool(
            legacy_kwargs.get("full_reset_managed_wave", False)
        ),
        prune_legacy_unmanaged=bool(legacy_kwargs.get("prune_legacy_unmanaged", False)),
    )


def _legacy_or_default_batch_size(
    options: SyncApplyOptions | int | None,
    legacy_kwargs: dict[str, object],
) -> object:
    legacy_batch_size = legacy_kwargs.get("batch_size")
    return legacy_batch_size if legacy_batch_size is not None else options


def _selection_from_legacy_kwargs(
    legacy_kwargs: dict[str, object],
) -> SnapshotSelection:
    return SnapshotSelection(
        only_labels=tuple(legacy_kwargs.get("only_labels", ())),
        only_analysis_layer=bool(legacy_kwargs.get("only_analysis_layer", False)),
        only_retirement_layer=bool(legacy_kwargs.get("only_retirement_layer", False)),
        only_complexity_layer=bool(legacy_kwargs.get("only_complexity_layer", False)),
        only_storage_layer=bool(legacy_kwargs.get("only_storage_layer", False)),
        only_runtime_evidence_layer=bool(
            legacy_kwargs.get("only_runtime_evidence_layer", False)
        ),
        only_workflow_graph=bool(legacy_kwargs.get("only_workflow_graph", False)),
        only_docs_drift=bool(legacy_kwargs.get("only_docs_drift", False)),
    )


def _statement_groups(
    snapshot: GraphSnapshot,
    sync_run: str,
) -> tuple[
    list[str],
    dict[str, list[dict[str, JsonValue]]],
    dict[str, list[dict[str, JsonValue]]],
    dict[str, list[dict[str, JsonValue]]],
    dict[str, list[dict[str, JsonValue]]],
    dict[str, list[dict[str, JsonValue]]],
    dict[str, list[dict[str, JsonValue]]],
]:
    managed_labels = sorted(
        {node.key.label for node in snapshot.nodes.values()}
        | set(DEFAULT_LEGACY_PRUNE_LABELS)
    )
    node_groups = _node_statement_groups(snapshot, sync_run)
    relation_groups = _relation_statement_groups(snapshot, sync_run)
    (
        core_node_groups,
        analysis_node_groups,
        core_relation_groups,
        analysis_relation_groups,
    ) = _partition_groups(node_groups, relation_groups)
    return (
        managed_labels,
        node_groups,
        relation_groups,
        core_node_groups,
        analysis_node_groups,
        core_relation_groups,
        analysis_relation_groups,
    )


def _node_statement_groups(
    snapshot: GraphSnapshot,
    sync_run: str,
) -> dict[str, list[dict[str, JsonValue]]]:
    node_groups: dict[str, list[dict[str, JsonValue]]] = {}
    for node in snapshot.nodes.values():
        node_groups.setdefault(node.key.label, []).append(
            _node_statement(node, sync_run)
        )
    return node_groups


def _relation_statement_groups(
    snapshot: GraphSnapshot,
    sync_run: str,
) -> dict[str, list[dict[str, JsonValue]]]:
    relation_groups: dict[str, list[dict[str, JsonValue]]] = {}
    for relation in snapshot.relations.values():
        relation_groups.setdefault(relation.relation_type, []).append(
            _relation_statement(relation, sync_run)
        )
    return relation_groups


def _delete_managed_wave_if_requested(
    client: Neo4jHttpClient,
    managed_labels: list[str],
    options: SyncApplyOptions,
) -> None:
    if not options.full_reset_managed_wave:
        return

    delete_batch_size = _delete_managed_wave_batch_size(options.batch_size)
    for label in managed_labels:
        while True:
            delete_statement = _delete_managed_wave_nodes_statement(
                label, delete_batch_size
            )
            rows = client.query(
                delete_statement["statement"],
                delete_statement["parameters"],
            )
            deleted = _coerce_int(rows[0]["deleted"]) if rows else 0
            if deleted == 0:
                break


def _delete_managed_wave_batch_size(batch_size: int) -> int:
    return max(1, min(batch_size, 50))


def _analysis_batch_size(
    batch_size: int,
    *,
    reduced_limit: int,
    contains_high_priority: bool,
    high_priority_limit: int,
) -> int:
    if contains_high_priority:
        return max(1, min(batch_size, high_priority_limit))
    return max(1, min(batch_size, reduced_limit))


def _analysis_node_batch_size(
    analysis_node_groups: dict[str, list[dict[str, JsonValue]]],
    batch_size: int,
) -> int:
    if "complexity_candidate" in analysis_node_groups:
        return 1
    return _analysis_batch_size(
        batch_size,
        reduced_limit=10,
        contains_high_priority="retirement_candidate" in analysis_node_groups,
        high_priority_limit=5,
    )


def _analysis_relation_batch_size(
    analysis_relation_groups: dict[str, list[dict[str, JsonValue]]],
    batch_size: int,
) -> int:
    return _analysis_batch_size(
        batch_size,
        reduced_limit=5,
        contains_high_priority="CANDIDATE_FOR_REMOVAL" in analysis_relation_groups,
        high_priority_limit=3,
    )


def _verification_sync_run(
    targeted_mode: bool,
    prune_stale: bool,
    sync_run: str,
) -> str | None:
    if targeted_mode or prune_stale:
        return sync_run
    return None


def _prune_managed_graph_if_requested(
    client: Neo4jHttpClient,
    options: SyncApplyOptions,
    sync_run: str,
    managed_labels: list[str],
) -> None:
    if options.prune_stale:
        _execute_prune_stale_statements(client, sync_run)
    if options.prune_legacy_unmanaged:
        client.execute([_prune_legacy_unmanaged_nodes_statement(managed_labels)])


def _execute_prune_stale_statements(
    client: Neo4jHttpClient,
    sync_run: str,
) -> None:
    client.execute([_prune_stale_relations_statement(sync_run)])
    client.execute([_prune_stale_nodes_statement(sync_run)])


def _reset_managed_relations_if_requested(
    client: Neo4jHttpClient,
    snapshot: GraphSnapshot,
    relation_groups: dict[str, list[dict[str, JsonValue]]],
    options: SyncApplyOptions,
) -> None:
    if not options.prune_stale or not relation_groups:
        return
    relation_types = sorted(
        {relation.relation_type for relation in snapshot.relations.values()}
    )
    client.execute([_reset_managed_relations_statement(relation_types)])


def _apply_snapshot_statement_groups(
    client: Neo4jHttpClient,
    snapshot: GraphSnapshot,
    *,
    options: SyncApplyOptions,
    relation_groups: dict[str, list[dict[str, JsonValue]]],
    core_node_groups: dict[str, list[dict[str, JsonValue]]],
    analysis_node_groups: dict[str, list[dict[str, JsonValue]]],
    core_relation_groups: dict[str, list[dict[str, JsonValue]]],
    analysis_relation_groups: dict[str, list[dict[str, JsonValue]]],
) -> None:
    _execute_grouped_statements(
        client, core_node_groups, options.batch_size, "core node"
    )
    _execute_grouped_statements(
        client,
        analysis_node_groups,
        _analysis_node_batch_size(analysis_node_groups, options.batch_size),
        "analysis node",
    )
    _reset_managed_relations_if_requested(client, snapshot, relation_groups, options)
    _execute_grouped_statements(
        client, core_relation_groups, options.batch_size, "core relation"
    )
    _execute_grouped_statements(
        client,
        analysis_relation_groups,
        _analysis_relation_batch_size(analysis_relation_groups, options.batch_size),
        "analysis relation",
    )


def _verify_sync_snapshot(
    client: Neo4jHttpClient,
    *,
    targeted_mode: bool,
    prune_stale: bool,
    sync_run: str,
    batch_size: int,
    node_groups: dict[str, list[dict[str, JsonValue]]],
    relation_groups: dict[str, list[dict[str, JsonValue]]],
    analysis_node_groups: dict[str, list[dict[str, JsonValue]]],
    analysis_relation_groups: dict[str, list[dict[str, JsonValue]]],
) -> None:
    verification_sync_run = _verification_sync_run(
        targeted_mode,
        prune_stale,
        sync_run,
    )
    _retry_critical_analysis_groups(
        client,
        analysis_node_groups,
        analysis_relation_groups,
        batch_size,
        sync_run=verification_sync_run,
    )
    _verify_expected_group_counts(
        client,
        analysis_node_groups if targeted_mode else {},
        analysis_relation_groups if targeted_mode else {},
        strict_analysis=not targeted_mode,
        sync_run=verification_sync_run,
    )
    if targeted_mode:
        _verify_expected_group_counts(
            client,
            node_groups,
            relation_groups,
            strict_analysis=False,
            sync_run=verification_sync_run,
        )


def sync_snapshot(
    snapshot: GraphSnapshot,
    root: Path,
    http_uri: str | None,
    options: SyncApplyOptions | int | None = None,
    selection: SnapshotSelection | None = None,
    **legacy_kwargs: object,
) -> None:
    resolved_options = _resolved_sync_apply_options(options, legacy_kwargs)
    if selection is None:
        selection = _selection_from_legacy_kwargs(legacy_kwargs)
    base_uri, username, password, database = resolve_neo4j_connection(root, http_uri)
    client = Neo4jHttpClient(base_uri, username, password, database)
    sync_run = _sync_run_id()
    snapshot = _filtered_snapshot(snapshot, selection=selection)
    targeted_mode = selection.targeted_mode()
    if targeted_mode:
        _ensure_targeted_apply_prerequisites(
            client,
            snapshot,
            mode_description=selection.mode_description(),
        )
    (
        managed_labels,
        node_groups,
        relation_groups,
        core_node_groups,
        analysis_node_groups,
        core_relation_groups,
        analysis_relation_groups,
    ) = _statement_groups(
        snapshot,
        sync_run,
    )
    _delete_managed_wave_if_requested(client, managed_labels, resolved_options)
    _apply_snapshot_statement_groups(
        client,
        snapshot,
        options=resolved_options,
        relation_groups=relation_groups,
        core_node_groups=core_node_groups,
        analysis_node_groups=analysis_node_groups,
        core_relation_groups=core_relation_groups,
        analysis_relation_groups=analysis_relation_groups,
    )
    _verify_sync_snapshot(
        client,
        targeted_mode=targeted_mode,
        prune_stale=resolved_options.prune_stale,
        sync_run=sync_run,
        batch_size=resolved_options.batch_size,
        node_groups=node_groups,
        relation_groups=relation_groups,
        analysis_node_groups=analysis_node_groups,
        analysis_relation_groups=analysis_relation_groups,
    )
    _prune_managed_graph_if_requested(
        client,
        resolved_options,
        sync_run,
        managed_labels,
    )


def _batched[T](items: list[T], size: int) -> list[list[T]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _statement_failure_context(statement: dict[str, JsonValue]) -> str:
    parameters = statement.get("parameters", {})
    node_name = parameters.get("name")
    if node_name is not None:
        return f"name={node_name!r}"
    source_name = parameters.get("source_name")
    target_name = parameters.get("target_name")
    return f"source={source_name!r}, target={target_name!r}"


def _raise_grouped_statement_failure(
    context: GroupedStatementFailureContext,
    statement: dict[str, JsonValue],
    cause: Exception,
) -> None:
    raise RuntimeError(
        f"Neo4j sync failed while applying {context.kind} group `{context.group_name}` "
        f"(batch {context.batch_index}/{context.batch_count}, "
        f"statement {context.statement_index}/{context.statement_count}, "
        f"{_statement_failure_context(statement)})"
    ) from cause


def _execute_statement_batch(
    client: Neo4jHttpClient,
    batch: list[dict[str, JsonValue]],
    *,
    kind: str,
    group_name: str,
    batch_index: int,
    batch_count: int,
) -> None:
    try:
        client.execute(batch)
    except Exception as exc:  # pragma: no cover - depends on live backend state
        if len(batch) == 1:
            _raise_grouped_statement_failure(
                GroupedStatementFailureContext(
                    kind=kind,
                    group_name=group_name,
                    batch_index=batch_index,
                    batch_count=batch_count,
                    statement_index=1,
                    statement_count=1,
                ),
                statement=batch[0],
                cause=exc,
            )
        for statement_index, statement in enumerate(batch, start=1):
            try:
                client.execute([statement])
            except (
                Exception
            ) as statement_exc:  # pragma: no cover - live backend dependent
                _raise_grouped_statement_failure(
                    GroupedStatementFailureContext(
                        kind=kind,
                        group_name=group_name,
                        batch_index=batch_index,
                        batch_count=batch_count,
                        statement_index=statement_index,
                        statement_count=len(batch),
                    ),
                    statement=statement,
                    cause=statement_exc,
                )


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
            _execute_statement_batch(
                client,
                batch,
                kind=kind,
                group_name=group_name,
                batch_index=batch_index,
                batch_count=len(grouped_batches),
            )


def _live_managed_node_count(client: Neo4jHttpClient, label: str) -> int:
    return _live_managed_node_counts(
        client,
        (label,),
        context=f"managed node count for label `{label}`",
    ).get(label, 0)


def _live_managed_relation_count(client: Neo4jHttpClient, relation_type: str) -> int:
    return _live_managed_relation_counts(
        client,
        (relation_type,),
        context=f"managed relation count for type `{relation_type}`",
    ).get(relation_type, 0)


def _managed_sync_run_clause(
    alias: str,
    sync_run: str | None,
) -> str:
    return f"AND coalesce({alias}.sync_run, '') = $sync_run " if sync_run else ""


def _count_rows_by_key(
    rows: list[dict[str, JsonValue]],
    keys: tuple[str, ...],
    key_field: str,
) -> dict[str, int]:
    counts = dict.fromkeys(keys, 0)
    for row in rows:
        key_value = row.get(key_field)
        count = row.get("count")
        if isinstance(key_value, str) and isinstance(count, (int, float)):
            counts[key_value] = _coerce_int(count)
    return counts


def _live_managed_node_counts(
    client: Neo4jHttpClient,
    labels: tuple[str, ...],
    *,
    context: str,
    sync_run: str | None = None,
) -> dict[str, int]:
    if not labels:
        return {}
    rows = client.query(
        (
            "UNWIND $labels AS label "
            "OPTIONAL MATCH (n) "
            "WHERE label IN labels(n) "
            "AND coalesce(n.managed_by, '') = $managed_by "
            "AND coalesce(n.ingest_wave, '') = $ingest_wave "
            f"{_managed_sync_run_clause('n', sync_run)}"
            "RETURN label, count(n) AS count "
            "ORDER BY label"
        ),
        {
            "labels": list(labels),
            "managed_by": DEFAULT_MANAGED_BY,
            "ingest_wave": DEFAULT_INGEST_WAVE,
            "sync_run": sync_run or "",
        },
        context=context,
    )
    return _count_rows_by_key(rows, labels, "label")


def _live_managed_relation_counts(
    client: Neo4jHttpClient,
    relation_types: tuple[str, ...],
    *,
    context: str,
    sync_run: str | None = None,
) -> dict[str, int]:
    if not relation_types:
        return {}
    rows = client.query(
        (
            "UNWIND $relation_types AS relation_type "
            "OPTIONAL MATCH ()-[r]->() "
            "WHERE type(r) = relation_type "
            "AND coalesce(r.managed_by, '') = $managed_by "
            "AND coalesce(r.ingest_wave, '') = $ingest_wave "
            f"{_managed_sync_run_clause('r', sync_run)}"
            "RETURN relation_type, count(r) AS count "
            "ORDER BY relation_type"
        ),
        {
            "relation_types": list(relation_types),
            "managed_by": DEFAULT_MANAGED_BY,
            "ingest_wave": DEFAULT_INGEST_WAVE,
            "sync_run": sync_run or "",
        },
        context=context,
    )
    return _count_rows_by_key(rows, relation_types, "relation_type")


def _targeted_apply_required_anchor_labels(snapshot: GraphSnapshot) -> tuple[str, ...]:
    present_labels = {node.key.label for node in snapshot.nodes.values()}
    required_labels = {
        relation.source.label
        for relation in snapshot.relations.values()
        if relation.source.label not in present_labels
    }
    required_labels |= {
        relation.target.label
        for relation in snapshot.relations.values()
        if relation.target.label not in present_labels
    }
    return tuple(sorted(required_labels))


def _targeted_apply_external_anchor_keys(
    snapshot: GraphSnapshot,
) -> tuple[NodeKey, ...]:
    present_keys = set(snapshot.nodes)
    external_anchor_keys: set[NodeKey] = set()
    for relation in snapshot.relations.values():
        if relation.source not in present_keys:
            external_anchor_keys.add(relation.source)
        if relation.target not in present_keys:
            external_anchor_keys.add(relation.target)
    return tuple(sorted(external_anchor_keys, key=lambda key: (key.label, key.name)))


def _missing_managed_anchor_keys(
    client: Neo4jHttpClient,
    anchor_keys: tuple[NodeKey, ...],
    *,
    context: str,
) -> tuple[NodeKey, ...]:
    if not anchor_keys:
        return ()

    missing_keys: list[NodeKey] = []
    chunk_size = 250
    for start in range(0, len(anchor_keys), chunk_size):
        chunk = anchor_keys[start : start + chunk_size]
        missing_keys.extend(
            _missing_anchor_keys_in_chunk(client, chunk, context=context)
        )
    return tuple(missing_keys)


def _missing_anchor_keys_in_chunk(
    client: Neo4jHttpClient,
    chunk: tuple[NodeKey, ...],
    *,
    context: str,
) -> list[NodeKey]:
    rows = client.query(
        (
            "UNWIND $anchors AS anchor "
            "OPTIONAL MATCH (n) "
            "WHERE anchor.label IN labels(n) "
            "AND n.name = anchor.name "
            "AND coalesce(n.managed_by, '') = $managed_by "
            "AND coalesce(n.ingest_wave, '') = $ingest_wave "
            "RETURN anchor.label AS label, anchor.name AS name, count(n) AS count "
            "ORDER BY label, name"
        ),
        {
            "anchors": [{"label": key.label, "name": key.name} for key in chunk],
            "managed_by": DEFAULT_MANAGED_BY,
            "ingest_wave": DEFAULT_INGEST_WAVE,
        },
        context=context,
    )
    live_counts = _anchor_count_rows(rows)
    return [key for key in chunk if live_counts.get(key, 0) == 0]


def _anchor_count_rows(rows: list[dict[str, JsonValue]]) -> dict[NodeKey, int]:
    return {
        NodeKey(str(row["label"]), str(row["name"])): _coerce_int(row["count"])
        for row in rows
        if isinstance(row.get("label"), str)
        and isinstance(row.get("name"), str)
        and isinstance(row.get("count"), (int, float))
    }


def _ensure_targeted_apply_prerequisites(
    client: Neo4jHttpClient,
    snapshot: GraphSnapshot,
    *,
    mode_description: str,
) -> None:
    required_anchor_labels = _targeted_apply_required_anchor_labels(snapshot)
    if not required_anchor_labels:
        return
    live_anchor_counts = _live_managed_node_counts(
        client,
        required_anchor_labels,
        context=f"{mode_description} prerequisite anchor check",
    )
    missing_labels = _missing_anchor_labels(required_anchor_labels, live_anchor_counts)
    if missing_labels:
        raise RuntimeError(
            _missing_anchor_labels_message(mode_description, missing_labels)
        )
    external_anchor_keys = _targeted_apply_external_anchor_keys(snapshot)
    missing_anchor_keys = _missing_managed_anchor_keys(
        client,
        external_anchor_keys,
        context=f"{mode_description} prerequisite anchor node check",
    )
    if missing_anchor_keys:
        raise RuntimeError(
            _missing_anchor_keys_message(mode_description, missing_anchor_keys)
        )


def _missing_anchor_labels(
    required_anchor_labels: tuple[str, ...],
    live_anchor_counts: dict[str, int],
) -> list[str]:
    return [
        label
        for label in required_anchor_labels
        if live_anchor_counts.get(label, 0) == 0
    ]


def _missing_anchor_labels_message(
    mode_description: str,
    missing_labels: list[str],
) -> str:
    missing_summary = ", ".join(f"`{label}`" for label in missing_labels)
    return (
        f"{mode_description} requires pre-existing managed anchor labels in the live graph, "
        f"but these labels are missing or empty: {missing_summary}. "
        "Run a base sync first (for example `python -m scripts.memory sync --apply --prune-stale`)."
    )


def _missing_anchor_keys_message(
    mode_description: str,
    missing_anchor_keys: tuple[NodeKey, ...],
) -> str:
    sample = ", ".join(f"`{key.label}:{key.name}`" for key in missing_anchor_keys[:10])
    remainder = len(missing_anchor_keys) - min(len(missing_anchor_keys), 10)
    remainder_suffix = f" and {remainder} more" if remainder > 0 else ""
    return (
        f"{mode_description} requires pre-existing managed anchor nodes in the live graph, "
        f"but these nodes are missing: {sample}{remainder_suffix}. "
        "Run a base sync first (for example `python -m scripts.memory sync --apply --prune-stale`)."
    )


def _active_group_names(
    ordered_names: tuple[str, ...],
    grouped_statements: dict[str, list[dict[str, JsonValue]]],
) -> list[str]:
    return [name for name in ordered_names if name in grouped_statements]


def _missing_group_names(
    active_names: list[str],
    grouped_statements: dict[str, list[dict[str, JsonValue]]],
    live_counts: dict[str, int],
) -> list[str]:
    return [
        name
        for name in active_names
        if live_counts.get(name, 0) != len(grouped_statements[name])
    ]


def _retry_missing_groups(
    client: Neo4jHttpClient,
    grouped_statements: dict[str, list[dict[str, JsonValue]]],
    missing_names: list[str],
    retry_batch_size: int,
    *,
    kind: str,
) -> None:
    if not missing_names:
        return
    _execute_grouped_statements(
        client,
        {name: grouped_statements[name] for name in missing_names},
        retry_batch_size,
        kind,
    )


def _critical_analysis_retry_batch_size(batch_size: int) -> int:
    return max(1, min(batch_size, 5))


def _refresh_node_counts_if_retried(
    client: Neo4jHttpClient,
    active_node_labels: list[str],
    missing_node_labels: list[str],
    *,
    sync_run: str | None,
    live_node_counts: dict[str, int],
) -> dict[str, int]:
    if not missing_node_labels:
        return live_node_counts
    return _live_managed_node_counts(
        client,
        tuple(active_node_labels),
        context="post-retry critical node verification",
        sync_run=sync_run,
    )


def _refresh_relation_counts_if_retried(
    client: Neo4jHttpClient,
    active_relation_types: list[str],
    missing_relation_types: list[str],
    *,
    sync_run: str | None,
    live_relation_counts: dict[str, int],
) -> dict[str, int]:
    if not missing_relation_types:
        return live_relation_counts
    return _live_managed_relation_counts(
        client,
        tuple(active_relation_types),
        context="post-retry critical relation verification",
        sync_run=sync_run,
    )


def _group_mismatch_messages(
    active_names: list[str],
    grouped_statements: dict[str, list[dict[str, JsonValue]]],
    live_counts: dict[str, int],
    *,
    noun: str,
) -> list[str]:
    mismatches: list[str] = []
    for name in active_names:
        live_count = live_counts.get(name, 0)
        expected = len(grouped_statements[name])
        if live_count == expected:
            continue
        mismatches.append(
            f"{noun} `{name}` expected {expected}, live managed {live_count}"
        )
    return mismatches


def _raise_analysis_group_mismatches(
    mismatches: list[str],
    *,
    prefix: str,
) -> None:
    if mismatches:
        raise RuntimeError(prefix + "; ".join(mismatches))


def _retry_critical_analysis_groups(
    client: Neo4jHttpClient,
    node_groups: dict[str, list[dict[str, JsonValue]]],
    relation_groups: dict[str, list[dict[str, JsonValue]]],
    batch_size: int,
    sync_run: str | None = None,
) -> None:
    retry_batch_size = _critical_analysis_retry_batch_size(batch_size)
    active_node_labels = _active_group_names(CRITICAL_ANALYSIS_NODE_LABELS, node_groups)
    active_relation_types = _active_group_names(
        CRITICAL_ANALYSIS_RELATION_TYPES, relation_groups
    )
    live_node_counts, live_relation_counts = _critical_analysis_group_counts(
        client,
        active_node_labels=active_node_labels,
        active_relation_types=active_relation_types,
        sync_run=sync_run,
    )
    live_node_counts = _retry_critical_node_groups(
        client,
        active_node_labels,
        node_groups,
        live_node_counts=live_node_counts,
        retry_batch_size=retry_batch_size,
        sync_run=sync_run,
    )
    live_relation_counts = _retry_critical_relation_groups(
        client,
        active_relation_types,
        relation_groups,
        live_relation_counts=live_relation_counts,
        retry_batch_size=retry_batch_size,
        sync_run=sync_run,
    )

    missing_after_retry = _critical_analysis_mismatch_messages(
        active_node_labels=active_node_labels,
        node_groups=node_groups,
        live_node_counts=live_node_counts,
        active_relation_types=active_relation_types,
        relation_groups=relation_groups,
        live_relation_counts=live_relation_counts,
    )
    _raise_analysis_group_mismatches(
        missing_after_retry,
        prefix="Post-apply verification failed for critical analysis groups: ",
    )


def _retry_critical_node_groups(
    client: Neo4jHttpClient,
    active_node_labels: list[str],
    node_groups: dict[str, list[dict[str, JsonValue]]],
    *,
    live_node_counts: dict[str, int],
    retry_batch_size: int,
    sync_run: str | None,
) -> dict[str, int]:
    missing_node_labels = _missing_group_names(
        active_node_labels,
        node_groups,
        live_node_counts,
    )
    _retry_missing_groups(
        client,
        node_groups,
        missing_node_labels,
        retry_batch_size,
        kind="critical node retry",
    )
    return _refresh_node_counts_if_retried(
        client,
        active_node_labels,
        missing_node_labels,
        sync_run=sync_run,
        live_node_counts=live_node_counts,
    )


def _retry_critical_relation_groups(
    client: Neo4jHttpClient,
    active_relation_types: list[str],
    relation_groups: dict[str, list[dict[str, JsonValue]]],
    *,
    live_relation_counts: dict[str, int],
    retry_batch_size: int,
    sync_run: str | None,
) -> dict[str, int]:
    missing_relation_types = _missing_group_names(
        active_relation_types,
        relation_groups,
        live_relation_counts,
    )
    _retry_missing_groups(
        client,
        relation_groups,
        missing_relation_types,
        retry_batch_size,
        kind="critical relation retry",
    )
    return _refresh_relation_counts_if_retried(
        client,
        active_relation_types,
        missing_relation_types,
        sync_run=sync_run,
        live_relation_counts=live_relation_counts,
    )


def _critical_analysis_group_counts(
    client: Neo4jHttpClient,
    *,
    active_node_labels: list[str],
    active_relation_types: list[str],
    sync_run: str | None,
) -> tuple[dict[str, int], dict[str, int]]:
    return (
        _live_managed_node_counts(
            client,
            tuple(active_node_labels),
            context="post-apply critical node verification",
            sync_run=sync_run,
        ),
        _live_managed_relation_counts(
            client,
            tuple(active_relation_types),
            context="post-apply critical relation verification",
            sync_run=sync_run,
        ),
    )


def _critical_analysis_mismatch_messages(
    *,
    active_node_labels: list[str],
    node_groups: dict[str, list[dict[str, JsonValue]]],
    live_node_counts: dict[str, int],
    active_relation_types: list[str],
    relation_groups: dict[str, list[dict[str, JsonValue]]],
    live_relation_counts: dict[str, int],
) -> list[str]:
    mismatches = _group_mismatch_messages(
        active_node_labels,
        node_groups,
        live_node_counts,
        noun="label",
    )
    mismatches.extend(
        _group_mismatch_messages(
            active_relation_types,
            relation_groups,
            live_relation_counts,
            noun="relation",
        )
    )
    return mismatches


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
        label: statements
        for label, statements in node_groups.items()
        if label in ANALYSIS_NODE_LABELS
    }
    core_node_groups = {
        label: statements
        for label, statements in node_groups.items()
        if label not in ANALYSIS_NODE_LABELS
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
    return (
        core_node_groups,
        analysis_node_groups,
        core_relation_groups,
        analysis_relation_groups,
    )


def _verify_expected_group_counts(
    client: Neo4jHttpClient,
    node_groups: dict[str, list[dict[str, JsonValue]]],
    relation_groups: dict[str, list[dict[str, JsonValue]]],
    *,
    strict_analysis: bool,
    sync_run: str | None = None,
) -> None:
    live_node_counts, live_relation_counts = _expected_group_counts(
        client,
        node_groups=node_groups,
        relation_groups=relation_groups,
        sync_run=sync_run,
    )
    mismatches = _expected_group_mismatches(
        node_groups=node_groups,
        relation_groups=relation_groups,
        live_node_counts=live_node_counts,
        live_relation_counts=live_relation_counts,
    )

    if strict_analysis:
        active_tokens = tuple(node_groups) + tuple(relation_groups)
        critical_mismatches = [
            mismatch
            for mismatch in mismatches
            if any(token in mismatch for token in active_tokens)
        ]
        _raise_analysis_group_mismatches(
            critical_mismatches,
            prefix="Post-apply verification failed for critical analysis groups: ",
        )
    else:
        _raise_analysis_group_mismatches(
            mismatches,
            prefix="Post-apply verification failed for targeted sync groups: ",
        )


def _expected_group_mismatches(
    *,
    node_groups: dict[str, list[dict[str, JsonValue]]],
    relation_groups: dict[str, list[dict[str, JsonValue]]],
    live_node_counts: dict[str, int],
    live_relation_counts: dict[str, int],
) -> list[str]:
    mismatches = _group_count_mismatches(
        grouped_statements=node_groups,
        live_counts=live_node_counts,
        noun="label",
    )
    mismatches.extend(
        _group_count_mismatches(
            grouped_statements=relation_groups,
            live_counts=live_relation_counts,
            noun="relation",
        )
    )
    return mismatches


def _group_count_mismatches(
    *,
    grouped_statements: dict[str, list[dict[str, JsonValue]]],
    live_counts: dict[str, int],
    noun: str,
) -> list[str]:
    mismatches: list[str] = []
    for name, statements in sorted(grouped_statements.items()):
        expected = len(statements)
        live_count = live_counts.get(name, 0)
        if live_count != expected:
            mismatches.append(
                f"{noun} `{name}` expected {expected}, live managed {live_count}"
            )
    return mismatches


def _group_names(
    grouped_statements: dict[str, list[dict[str, JsonValue]]],
) -> tuple[str, ...]:
    return tuple(sorted(grouped_statements))


def _expected_group_counts(
    client: Neo4jHttpClient,
    *,
    node_groups: dict[str, list[dict[str, JsonValue]]],
    relation_groups: dict[str, list[dict[str, JsonValue]]],
    sync_run: str | None,
) -> tuple[dict[str, int], dict[str, int]]:
    return (
        _live_managed_node_counts(
            client,
            _group_names(node_groups),
            context="post-apply node group verification",
            sync_run=sync_run,
        ),
        _live_managed_relation_counts(
            client,
            _group_names(relation_groups),
            context="post-apply relation group verification",
            sync_run=sync_run,
        ),
    )


def _write_export(path: Path, snapshot: GraphSnapshot) -> None:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=REPO_ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot.to_dict(), indent=2) + "\n", encoding="utf-8")


def _write_json(path: Path, payload: JsonValue) -> None:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=REPO_ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
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


def _has_required_relation(
    relation_keys: set[tuple[str, str, str, str]],
    *,
    source_labels: set[str],
    relation_type: str,
    target_labels: set[str] | None = None,
) -> bool:
    for source_label, _, current_relation_type, target_label in relation_keys:
        if source_label not in source_labels or current_relation_type != relation_type:
            continue
        if target_labels is None or target_label in target_labels:
            return True
    return False


def _append_missing_relation_issues(
    issues: list[str],
    relation_keys: set[tuple[str, str, str, str]],
    requirements: tuple[tuple[str, set[str], str, set[str] | None], ...],
) -> None:
    for message, source_labels, relation_type, target_labels in requirements:
        if _has_required_relation(
            relation_keys,
            source_labels=source_labels,
            relation_type=relation_type,
            target_labels=target_labels,
        ):
            continue
        issues.append(message)


def _missing_node_support_names(
    snapshot: GraphSnapshot,
    label: str,
    is_supported: Callable[[NodeKey], bool],
) -> list[str]:
    return sorted(
        key.name
        for key in (
            node.key for node in snapshot.nodes.values() if node.key.label == label
        )
        if not is_supported(key)
    )


def _append_support_issue(issues: list[str], prefix: str, names: list[str]) -> None:
    if names:
        issues.append(f"{prefix}: {', '.join(names[:10])}")


def _relation_requirement_keys(
    relations: tuple[GraphRelation, ...],
) -> set[tuple[str, str, str, str]]:
    return {
        (rel.source.label, rel.source.name, rel.relation_type, rel.target.label)
        for rel in relations
    }


def _append_snapshot_support_issues(
    issues: list[str],
    snapshot: GraphSnapshot,
    relations: tuple[GraphRelation, ...],
) -> None:
    relation_index = _build_snapshot_relation_index(relations)
    for prefix, label, predicate in _snapshot_support_specs():
        _append_support_issue(
            issues,
            prefix,
            _missing_node_support_names(
                snapshot, label, lambda key, fn=predicate: fn(relation_index, key)
            ),
        )


SNAPSHOT_REQUIRED_LABELS = (
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
    "storage_surface",
    "runtime_evidence_surface",
    "control_plane_artifact_surface",
    "run_instance_surface",
    "runtime_state_surface",
    "schema_field_surface",
    "workflow_surface",
    "workflow_job_surface",
    "workflow_call_surface",
    "workflow_matrix_variant_surface",
    "workflow_output_surface",
    "workflow_action_surface",
    "workflow_artifact_surface",
    "workflow_secret_surface",
    "cli_command_surface",
    "cli_option_surface",
    "doc_claim_surface",
)
SNAPSHOT_REQUIRED_RELATION_TYPES = (
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
    "DESCRIBES",
    "WRITES_TO",
    "PROMOTES_TO",
    "HAS_RUNTIME_EVIDENCE",
    "HAS_CONTROL_PLANE_ARTIFACT",
    "HAS_RUN_INSTANCE",
    "HAS_RUNTIME_STATE",
    "HAS_WORKFLOW",
    "HAS_CLI_COMMAND",
    "HAS_SCHEMA_FIELD",
    "CALLS_WORKFLOW",
    "HAS_MATRIX_VARIANT",
    "EMITS_OUTPUT",
    "ACCEPTS_OPTION",
    "SIDE_EFFECTS_ON",
    "ASSERTS",
    "ASSERTS_ABOUT",
    "EXECUTES_GATE",
    "EMITS_ARTIFACT",
    "MATERIALIZED_AS",
    "REFERENCES_ARTIFACT",
    "PROMOTES_FIELD_TO",
    "DERIVES_FIELD_FROM",
    "USES_ACTION",
    "PUBLISHES_ARTIFACT",
    "REQUIRES_SECRET",
    "CONSTRAINS",
)
SNAPSHOT_RELATION_REQUIREMENTS = (
    (
        "missing project -> HAS_REPO_ZONE -> repo_zone links",
        {"project"},
        "HAS_REPO_ZONE",
        {"repo_zone"},
    ),
    (
        "missing directory_surface -> CONTAINS -> file_surface links",
        {"directory_surface"},
        "CONTAINS",
        {"file_surface"},
    ),
    (
        "missing file_surface -> BACKS -> module_surface links",
        {"file_surface"},
        "BACKS",
        {"module_surface"},
    ),
    (
        "missing directory_surface -> HOUSES -> package_family links",
        {"directory_surface"},
        "HOUSES",
        {"package_family"},
    ),
    (
        "missing directory_surface -> HOUSES -> entity_config links",
        {"directory_surface"},
        "HOUSES",
        {"entity_config"},
    ),
    (
        "missing directory_surface -> HOUSES -> doc_source_surface links",
        {"directory_surface"},
        "HOUSES",
        {"doc_source_surface"},
    ),
    (
        "missing directory_surface -> HOUSES -> test_artifact links",
        {"directory_surface"},
        "HOUSES",
        {"test_artifact"},
    ),
    (
        "missing module_surface -> DECLARES -> class_surface links",
        {"module_surface"},
        "DECLARES",
        {"class_surface"},
    ),
    (
        "missing class_surface -> DECLARES -> method_surface links",
        {"class_surface"},
        "DECLARES",
        {"method_surface"},
    ),
    (
        "missing module_surface -> DECLARES -> function_surface links",
        {"module_surface"},
        "DECLARES",
        {"function_surface"},
    ),
    (
        "missing duplication_cluster promotion targets",
        {"duplication_cluster"},
        "CAN_PROMOTE_TO",
        None,
    ),
    (
        "missing duplication_cluster -> CONTAINS -> callable surface links",
        {"duplication_cluster"},
        "CONTAINS",
        {"method_surface", "function_surface"},
    ),
    (
        "missing callable duplication links",
        {"method_surface", "function_surface"},
        "SAME_SHAPE_AS",
        None,
    ),
    (
        "missing code surface -> HAS_COMPLEXITY_SIGNAL -> complexity_candidate links",
        {"module_surface", "class_surface", "function_surface", "method_surface"},
        "HAS_COMPLEXITY_SIGNAL",
        {"complexity_candidate"},
    ),
    (
        "missing complexity simplification candidates",
        {"complexity_candidate"},
        "CANDIDATE_FOR_SIMPLIFICATION",
        None,
    ),
    (
        "missing contract_surface -> DEPENDS_ON -> module_surface relations",
        {"contract_surface"},
        "DEPENDS_ON",
        {"module_surface"},
    ),
    (
        "missing contract_surface -> DESCRIBED_IN -> doc_artifact relations",
        {"contract_surface"},
        "DESCRIBED_IN",
        {"doc_artifact"},
    ),
    (
        "missing pipeline_surface operational runtime links",
        {"pipeline_surface"},
        "RUNS_VIA",
        {"execution_path"},
    ),
    (
        "missing pipeline_surface direct test coverage links",
        {"pipeline_surface"},
        "TESTED_BY",
        {"test_artifact"},
    ),
    (
        "missing pipeline_surface -> DEFINED_BY -> config_artifact links",
        {"pipeline_surface"},
        "DEFINED_BY",
        {"config_artifact"},
    ),
    (
        "missing pipeline_surface -> DESCRIBED_IN -> doc_artifact links",
        {"pipeline_surface"},
        "DESCRIBED_IN",
        {"doc_artifact"},
    ),
    (
        "missing pipeline_surface -> DEPENDS_ON -> module_surface links",
        {"pipeline_surface"},
        "DEPENDS_ON",
        {"module_surface"},
    ),
    (
        "missing module_surface -> DESCRIBED_IN -> doc_artifact links",
        {"module_surface"},
        "DESCRIBED_IN",
        {"doc_artifact"},
    ),
    (
        "missing entity_config -> DEPENDS_ON -> module_surface links",
        {"entity_config"},
        "DEPENDS_ON",
        {"module_surface"},
    ),
    (
        "missing alert_surface dependency links",
        {"alert_surface"},
        "DEPENDS_ON",
        {"pipeline_surface", "provider_surface"},
    ),
    (
        "missing alert_surface -> DEPENDS_ON -> contract_surface links",
        {"alert_surface"},
        "DEPENDS_ON",
        {"contract_surface"},
    ),
    (
        "missing alert_surface -> OBSERVED_BY -> dashboard_surface links",
        {"alert_surface"},
        "OBSERVED_BY",
        {"dashboard_surface"},
    ),
    (
        "missing project -> HAS_RUNTIME_EVIDENCE -> runtime_evidence_surface links",
        {"project"},
        "HAS_RUNTIME_EVIDENCE",
        {"runtime_evidence_surface"},
    ),
    (
        "missing project -> HAS_CONTROL_PLANE_ARTIFACT -> control_plane_artifact_surface links",
        {"project"},
        "HAS_CONTROL_PLANE_ARTIFACT",
        {"control_plane_artifact_surface"},
    ),
    (
        "missing project -> HAS_RUN_INSTANCE -> run_instance_surface links",
        {"project"},
        "HAS_RUN_INSTANCE",
        {"run_instance_surface"},
    ),
    (
        "missing project -> HAS_RUNTIME_STATE -> runtime_state_surface links",
        {"project"},
        "HAS_RUNTIME_STATE",
        {"runtime_state_surface"},
    ),
    (
        "missing project -> HAS_WORKFLOW -> workflow_surface links",
        {"project"},
        "HAS_WORKFLOW",
        {"workflow_surface"},
    ),
    (
        "missing project -> HAS_CLI_COMMAND -> cli_command_surface links",
        {"project"},
        "HAS_CLI_COMMAND",
        {"cli_command_surface"},
    ),
    (
        "missing workflow_surface -> CONTAINS -> workflow_job_surface links",
        {"workflow_surface"},
        "CONTAINS",
        {"workflow_job_surface"},
    ),
    (
        "missing workflow/workflow_job -> CALLS_WORKFLOW -> workflow_call_surface links",
        {"workflow_surface", "workflow_job_surface"},
        "CALLS_WORKFLOW",
        {"workflow_call_surface"},
    ),
    (
        "missing workflow_job_surface -> HAS_MATRIX_VARIANT -> workflow_matrix_variant_surface links",
        {"workflow_job_surface"},
        "HAS_MATRIX_VARIANT",
        {"workflow_matrix_variant_surface"},
    ),
    (
        "missing workflow/workflow_job -> EMITS_OUTPUT -> workflow_output_surface links",
        {"workflow_surface", "workflow_job_surface"},
        "EMITS_OUTPUT",
        {"workflow_output_surface"},
    ),
    (
        "missing workflow_job_surface -> RUNS_VIA operational target links",
        {"workflow_job_surface"},
        "RUNS_VIA",
        {"script_surface", "file_surface", "directory_surface"},
    ),
    (
        "missing workflow_job_surface -> EXECUTES_GATE -> quality_gate links",
        {"workflow_job_surface"},
        "EXECUTES_GATE",
        {"quality_gate"},
    ),
    (
        "missing workflow_job_surface -> USES_ACTION -> workflow_action_surface links",
        {"workflow_job_surface"},
        "USES_ACTION",
        {"workflow_action_surface"},
    ),
    (
        "missing workflow_job_surface -> PUBLISHES_ARTIFACT -> workflow_artifact_surface links",
        {"workflow_job_surface"},
        "PUBLISHES_ARTIFACT",
        {"workflow_artifact_surface"},
    ),
    (
        "missing workflow_job_surface -> REQUIRES_SECRET -> workflow_secret_surface links",
        {"workflow_job_surface"},
        "REQUIRES_SECRET",
        {"workflow_secret_surface"},
    ),
    (
        "missing cli_command_surface -> RUNS_VIA -> execution_path links",
        {"cli_command_surface"},
        "RUNS_VIA",
        {"execution_path"},
    ),
    (
        "missing cli_command_surface -> ACCEPTS_OPTION -> cli_option_surface links",
        {"cli_command_surface"},
        "ACCEPTS_OPTION",
        {"cli_option_surface"},
    ),
    (
        "missing cli_command_surface side effect links",
        {"cli_command_surface"},
        "SIDE_EFFECTS_ON",
        None,
    ),
    (
        "missing storage_surface -> HAS_SCHEMA_FIELD -> schema_field_surface links",
        {"storage_surface"},
        "HAS_SCHEMA_FIELD",
        {"schema_field_surface"},
    ),
    (
        "missing contract_surface -> HAS_SCHEMA_FIELD -> schema_field_surface links",
        {"contract_surface"},
        "HAS_SCHEMA_FIELD",
        {"schema_field_surface"},
    ),
    (
        "missing pipeline_surface -> WRITES_TO -> storage_surface links",
        {"pipeline_surface"},
        "WRITES_TO",
        {"storage_surface"},
    ),
    (
        "missing storage_surface promotion links",
        {"storage_surface"},
        "PROMOTES_TO",
        {"storage_surface"},
    ),
    (
        "missing runtime_evidence_surface -> WRITES_TO -> storage_surface links",
        {"runtime_evidence_surface"},
        "WRITES_TO",
        {"storage_surface"},
    ),
    (
        "missing runtime_evidence_surface -> EMITS_ARTIFACT -> control_plane_artifact_surface links",
        {"runtime_evidence_surface"},
        "EMITS_ARTIFACT",
        {"control_plane_artifact_surface"},
    ),
    (
        "missing control_plane_artifact_surface -> MATERIALIZED_AS -> storage_surface links",
        {"control_plane_artifact_surface"},
        "MATERIALIZED_AS",
        {"storage_surface"},
    ),
    (
        "missing run_instance_surface -> REFERENCES_ARTIFACT -> control_plane_artifact_surface links",
        {"run_instance_surface"},
        "REFERENCES_ARTIFACT",
        {"control_plane_artifact_surface"},
    ),
    (
        "missing run_instance_surface -> HAS_RUNTIME_STATE -> runtime_state_surface links",
        {"run_instance_surface"},
        "HAS_RUNTIME_STATE",
        {"runtime_state_surface"},
    ),
    (
        "missing runtime_state_surface dependency links",
        {"runtime_state_surface"},
        "DEPENDS_ON",
        {"pipeline_surface", "workflow_surface", "runtime_evidence_surface"},
    ),
    (
        "missing runtime_state_surface -> REFERENCES_ARTIFACT -> control_plane_artifact_surface links",
        {"runtime_state_surface"},
        "REFERENCES_ARTIFACT",
        {"control_plane_artifact_surface"},
    ),
    (
        "missing schema_field_surface promotion links",
        {"schema_field_surface"},
        "PROMOTES_FIELD_TO",
        {"schema_field_surface"},
    ),
    (
        "missing schema_field_surface derivation links",
        {"schema_field_surface"},
        "DERIVES_FIELD_FROM",
        {"schema_field_surface"},
    ),
    (
        "missing docs-to-code drift edges",
        {"doc_source_surface", "doc_artifact", "policy_surface"},
        "DESCRIBES",
        {
            "module_surface",
            "script_surface",
            "config_artifact",
            "workflow_surface",
            "cli_command_surface",
            "file_surface",
            "directory_surface",
            "execution_path",
        },
    ),
    (
        "missing ADR constraint edges",
        {"decision"},
        "CONSTRAINS",
        {
            "module_surface",
            "file_surface",
            "config_artifact",
            "test_artifact",
            "directory_surface",
        },
    ),
    (
        "missing doc claim extraction edges",
        {"doc_source_surface", "doc_artifact", "policy_surface"},
        "ASSERTS",
        {"doc_claim_surface"},
    ),
    (
        "missing doc claim traceability edges",
        {"doc_claim_surface"},
        "ASSERTS_ABOUT",
        {
            "module_surface",
            "script_surface",
            "config_artifact",
            "workflow_surface",
            "cli_command_surface",
            "file_surface",
            "directory_surface",
            "execution_path",
        },
    ),
    (
        "missing adapter_surface -> CONTAINS -> adapter_impl_surface links",
        {"adapter_surface"},
        "CONTAINS",
        {"adapter_impl_surface"},
    ),
)


def _support_runtime_evidence_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return _has_outbound_relation(
        relation_index, key, {"BACKED_BY", "DESCRIBED_IN", "WRITES_TO"}
    )


def _support_control_plane_artifact_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return _has_inbound_relation(
        relation_index,
        key,
        {"EMITS_ARTIFACT"},
        source_labels={"runtime_evidence_surface"},
    ) and _has_outbound_relation(
        relation_index,
        key,
        {"MATERIALIZED_AS"},
        target_labels={"storage_surface"},
    )


def _support_run_instance_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return _has_inbound_relation(
        relation_index,
        key,
        {"HAS_RUN_INSTANCE"},
        source_labels={"project"},
    ) and _has_outbound_relation(
        relation_index,
        key,
        {"REFERENCES_ARTIFACT"},
        target_labels={"control_plane_artifact_surface"},
    )


def _support_runtime_state_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return (
        _has_inbound_relation(
            relation_index,
            key,
            {"HAS_RUNTIME_STATE"},
            source_labels={"project", "run_instance_surface"},
        )
        and _has_outbound_relation(
            relation_index,
            key,
            {"DEPENDS_ON"},
        )
        and _has_outbound_relation(
            relation_index,
            key,
            {"REFERENCES_ARTIFACT"},
            target_labels={"control_plane_artifact_surface"},
        )
    )


def _support_storage_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return _has_inbound_relation(
        relation_index,
        key,
        {"WRITES_TO", "DEPENDS_ON", "DEFINED_BY"},
        source_labels={
            "pipeline_surface",
            "entity_config",
            "runtime_evidence_surface",
            "storage_surface",
        },
    ) or _has_outbound_relation(
        relation_index,
        key,
        {"PROMOTES_TO", "DEFINED_BY"},
    )


def _support_schema_field_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return _has_inbound_relation(
        relation_index,
        key,
        {"HAS_SCHEMA_FIELD"},
        source_labels={"storage_surface", "contract_surface"},
    ) and _has_outbound_relation(
        relation_index,
        key,
        {"DEFINED_BY", "PROMOTES_FIELD_TO", "DERIVES_FIELD_FROM"},
    )


def _support_workflow_job_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return _has_inbound_relation(
        relation_index, key, {"CONTAINS"}, source_labels={"workflow_surface"}
    )


def _support_cli_command_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return _has_outbound_relation(
        relation_index,
        key,
        {"RUNS_VIA", "EXECUTES_GATE", "DEPENDS_ON"},
    ) or _has_inbound_relation(
        relation_index,
        key,
        {"HAS_CLI_COMMAND"},
        source_labels={"project"},
    )


def _support_workflow_artifact_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return _has_inbound_relation(
        relation_index,
        key,
        {"PUBLISHES_ARTIFACT", "DEPENDS_ON"},
        source_labels={"workflow_job_surface"},
    )


def _support_workflow_call_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return _has_inbound_relation(
        relation_index,
        key,
        {"CALLS_WORKFLOW"},
        source_labels={"workflow_surface", "workflow_job_surface"},
    ) or _has_outbound_relation(
        relation_index,
        key,
        {"DEPENDS_ON"},
        target_labels={"workflow_surface"},
    )


def _support_workflow_output_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return _has_inbound_relation(
        relation_index,
        key,
        {"EMITS_OUTPUT"},
        source_labels={"workflow_surface", "workflow_job_surface"},
    )


def _support_cli_option_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return _has_inbound_relation(
        relation_index,
        key,
        {"ACCEPTS_OPTION"},
        source_labels={"cli_command_surface"},
    )


def _support_doc_claim_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return _has_inbound_relation(
        relation_index,
        key,
        {"ASSERTS"},
        source_labels={"doc_source_surface", "doc_artifact", "policy_surface"},
    ) or _has_outbound_relation(
        relation_index,
        key,
        {"ASSERTS_ABOUT"},
    )


def _snapshot_support_specs() -> tuple[
    tuple[str, str, Callable[[_SnapshotRelationIndex, NodeKey], bool]], ...
]:
    return (
        (
            "runtime evidence surfaces without support links",
            "runtime_evidence_surface",
            _support_runtime_evidence_surface,
        ),
        (
            "control-plane artifacts without runtime/storage links",
            "control_plane_artifact_surface",
            _support_control_plane_artifact_surface,
        ),
        (
            "run instance surfaces without support links",
            "run_instance_surface",
            _support_run_instance_surface,
        ),
        (
            "runtime state surfaces without support links",
            "runtime_state_surface",
            _support_runtime_state_surface,
        ),
        (
            "storage surfaces without ownership or lineage links",
            "storage_surface",
            _support_storage_surface,
        ),
        (
            "schema fields without storage/contract/lineage links",
            "schema_field_surface",
            _support_schema_field_surface,
        ),
        (
            "workflow jobs without workflow parent links",
            "workflow_job_surface",
            _support_workflow_job_surface,
        ),
        (
            "cli command surfaces without runtime/support links",
            "cli_command_surface",
            _support_cli_command_surface,
        ),
        (
            "workflow artifacts without job links",
            "workflow_artifact_surface",
            _support_workflow_artifact_surface,
        ),
        (
            "workflow calls without job/workflow links",
            "workflow_call_surface",
            _support_workflow_call_surface,
        ),
        (
            "workflow outputs without workflow/job links",
            "workflow_output_surface",
            _support_workflow_output_surface,
        ),
        (
            "cli options without command links",
            "cli_option_surface",
            _support_cli_option_surface,
        ),
        (
            "doc claims without doc/target links",
            "doc_claim_surface",
            _support_doc_claim_surface,
        ),
    )


def _required_population_issues(stats: dict[str, JsonValue]) -> list[str]:
    issues: list[str] = []
    issues.extend(
        _missing_required_population(stats["labels"], SNAPSHOT_REQUIRED_LABELS, "label")
    )
    issues.extend(
        _missing_required_population(
            stats["relation_types"], SNAPSHOT_REQUIRED_RELATION_TYPES, "relation"
        )
    )
    return issues


@dataclass(frozen=True)
class _SnapshotRelationIndex:
    outbound_by_source: dict[NodeKey, tuple[GraphRelation, ...]]
    inbound_by_target: dict[NodeKey, tuple[GraphRelation, ...]]


def _build_snapshot_relation_index(
    relations: tuple[GraphRelation, ...],
) -> _SnapshotRelationIndex:
    outbound: dict[NodeKey, list[GraphRelation]] = {}
    inbound: dict[NodeKey, list[GraphRelation]] = {}
    for relation in relations:
        outbound.setdefault(relation.source, []).append(relation)
        inbound.setdefault(relation.target, []).append(relation)
    return _SnapshotRelationIndex(
        outbound_by_source={key: tuple(value) for key, value in outbound.items()},
        inbound_by_target={key: tuple(value) for key, value in inbound.items()},
    )


def _has_inbound_relation(
    relation_index: _SnapshotRelationIndex,
    key: NodeKey,
    relation_types: set[str],
    *,
    source_labels: set[str] | None = None,
) -> bool:
    return any(
        rel.target == key
        and rel.relation_type in relation_types
        and (source_labels is None or rel.source.label in source_labels)
        for rel in relation_index.inbound_by_target.get(key, ())
    )


def _has_outbound_relation(
    relation_index: _SnapshotRelationIndex,
    key: NodeKey,
    relation_types: set[str],
    *,
    target_labels: set[str] | None = None,
) -> bool:
    return any(
        rel.source == key
        and rel.relation_type in relation_types
        and (target_labels is None or rel.target.label in target_labels)
        for rel in relation_index.outbound_by_source.get(key, ())
    )


def _missing_required_population(
    counts: object,
    names: Iterable[str],
    kind: str,
) -> list[str]:
    if not isinstance(counts, dict):
        return [f"missing required {kind} population: {name}" for name in names]
    return [
        f"missing required {kind} population: {name}"
        for name in names
        if _coerce_int(counts.get(name, 0), 0) <= 0
    ]


def _nodes_with_label(snapshot: GraphSnapshot, label: str) -> list[GraphNode]:
    return [node for node in snapshot.nodes.values() if node.key.label == label]


def _protocol_class_ports(snapshot: GraphSnapshot) -> list[GraphNode]:
    return [
        node
        for node in _nodes_with_label(snapshot, "port_surface")
        if node.properties.get("granularity") == "protocol_class"
    ]


def _rich_contract_surfaces(snapshot: GraphSnapshot) -> list[GraphNode]:
    return [
        node
        for node in _nodes_with_label(snapshot, "contract_surface")
        if node.properties.get("dq_policy_ref")
        and node.properties.get("schema_classes")
    ]


def _port_and_contract_metadata_issues(snapshot: GraphSnapshot) -> list[str]:
    issues: list[str] = []
    if NodeKey("port_surface", PORTS_MODULE_PREFIX) not in snapshot.nodes:
        issues.append(f"missing {PORTS_MODULE_PREFIX} facade port surface")

    if not _protocol_class_ports(snapshot):
        issues.append("missing protocol-class port surfaces")

    if not _rich_contract_surfaces(snapshot):
        issues.append("missing rich contract metadata on contract surfaces")

    return issues


def _support_and_relation_issues(
    snapshot: GraphSnapshot,
    relations: tuple[GraphRelation, ...],
) -> list[str]:
    issues: list[str] = []
    relation_keys = _relation_requirement_keys(relations)
    _append_missing_relation_issues(
        issues, relation_keys, SNAPSHOT_RELATION_REQUIREMENTS
    )
    _append_snapshot_support_issues(issues, snapshot, relations)
    return issues


def _ignored_runtime_paths(snapshot: GraphSnapshot) -> list[str]:
    return [
        node.key.name
        for node in snapshot.nodes.values()
        if "__pycache__" in node.key.name
        or "__pycache__" in str(node.properties.get("source_path", ""))
    ]


def _excluded_file_structure_paths(snapshot: GraphSnapshot) -> list[str]:
    return [
        node.key.name
        for node in snapshot.nodes.values()
        if node.key.label in {"directory_surface", "file_surface"}
        and (
            node.key.name.startswith("docs/site")
            or node.key.name.startswith("docs/site/")
            or node.key.name.startswith("docs/99-archive")
            or node.key.name.startswith("docs/exports")
            or node.key.name.startswith("docs/reports/generated")
            or node.key.name.startswith("docs/02-architecture/generated")
            or node.key.name.startswith("docs/02-architecture/diagrams/bundles")
            or node.key.name.startswith("scripts/archive")
            or "/png" in node.key.name
            or "/svg" in node.key.name
        )
    ]


def _sampled_sorted_unique(values: list[str], limit: int) -> list[str]:
    return sorted(set(values))[:limit]


def _append_path_issue(
    issues: list[str],
    prefix: str,
    paths: list[str],
    *,
    limit: int,
) -> None:
    if paths:
        issues.append(f"{prefix}: {_sampled_sorted_unique(paths, limit)}")


def _path_leak_issues(snapshot: GraphSnapshot) -> list[str]:
    issues: list[str] = []
    _append_path_issue(
        issues,
        "ignored runtime paths leaked into snapshot",
        _ignored_runtime_paths(snapshot),
        limit=5,
    )
    excluded_paths = _excluded_file_structure_paths(snapshot)
    if excluded_paths:
        issues.append(
            "excluded file-structure paths leaked into snapshot: "
            + ", ".join(_sampled_sorted_unique(excluded_paths, 10))
        )
    return issues


def _format_orphan_nodes(orphan_nodes: list[NodeKey], limit: int) -> str:
    return ", ".join(f"{node.label}:{node.name}" for node in orphan_nodes[:limit])


def _orphan_node_issues(snapshot: GraphSnapshot) -> list[str]:
    orphan_nodes = snapshot_orphans(snapshot)
    if not orphan_nodes:
        return []
    return ["snapshot contains orphan nodes: " + _format_orphan_nodes(orphan_nodes, 10)]


def snapshot_invariant_issues(snapshot: GraphSnapshot) -> list[str]:
    stats = snapshot.stats()
    relations = tuple(snapshot.relations.values())
    return (
        _required_population_issues(stats)
        + _port_and_contract_metadata_issues(snapshot)
        + _support_and_relation_issues(snapshot, relations)
        + _path_leak_issues(snapshot)
        + _orphan_node_issues(snapshot)
    )


def _build_diff_entries(
    snapshot_counts: dict[str, int], live_counts: dict[str, int]
) -> list[dict[str, JsonValue]]:
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


def _live_repo_label_rows(
    client: Neo4jHttpClient, managed_labels: list[str]
) -> list[dict[str, JsonValue]]:
    if not managed_labels:
        return []
    rows = client.query(
        (
            "UNWIND $managed_labels AS label "
            "OPTIONAL MATCH (n) "
            "WHERE label IN labels(n) "
            "WITH label, count(n) AS total "
            "OPTIONAL MATCH (managed_node) "
            "WHERE label IN labels(managed_node) "
            "AND coalesce(managed_node.managed_by, '') = $managed_by "
            "AND coalesce(managed_node.ingest_wave, '') = $ingest_wave "
            "WITH label, total, count(managed_node) AS managed "
            "OPTIONAL MATCH (unmanaged_node) "
            "WHERE label IN labels(unmanaged_node) "
            "AND coalesce(unmanaged_node.managed_by, '') = '' "
            "RETURN label, total, managed, count(unmanaged_node) AS unmanaged "
            "ORDER BY label"
        ),
        {
            "managed_labels": managed_labels,
            "managed_by": DEFAULT_MANAGED_BY,
            "ingest_wave": DEFAULT_INGEST_WAVE,
        },
        context="full audit label summary",
    )
    return [
        {
            "label": str(row["label"]),
            "total": _coerce_int(row["total"]),
            "managed": _coerce_int(row["managed"]),
            "unmanaged": _coerce_int(row["unmanaged"]),
        }
        for row in rows
        if isinstance(row.get("label"), str)
        and isinstance(row.get("total"), (int, float))
        and isinstance(row.get("managed"), (int, float))
        and isinstance(row.get("unmanaged"), (int, float))
    ]


def _live_managed_relation_rows(
    client: Neo4jHttpClient,
    relation_types: list[str],
) -> list[dict[str, JsonValue]]:
    counts = _live_managed_relation_counts(
        client,
        tuple(relation_types),
        context="full audit relation summary",
    )
    return [
        {"relation_type": relation_type, "total": total}
        for relation_type, total in sorted(counts.items())
    ]


def _live_orphan_rows(
    client: Neo4jHttpClient, managed_labels: list[str]
) -> list[dict[str, JsonValue]]:
    if not managed_labels:
        return []
    rows = client.query(
        (
            "UNWIND $managed_labels AS label "
            "OPTIONAL MATCH (n) "
            "WHERE label IN labels(n) "
            "AND coalesce(n.managed_by, '') = $managed_by "
            "AND coalesce(n.ingest_wave, '') = $ingest_wave "
            "AND NOT (n)--() "
            "RETURN label, count(n) AS count, collect(n.name)[0..10] AS samples "
            "ORDER BY label"
        ),
        {
            "managed_labels": managed_labels,
            "managed_by": DEFAULT_MANAGED_BY,
            "ingest_wave": DEFAULT_INGEST_WAVE,
        },
        context="full audit orphan summary",
    )
    return [
        {
            "label": str(row["label"]),
            "count": _coerce_int(row["count"]),
            "samples": row.get("samples", []),
        }
        for row in rows
        if isinstance(row.get("label"), str)
        and isinstance(row.get("count"), (int, float))
        and _coerce_int(row["count"]) > 0
    ]


def _live_unmanaged_repo_rows(
    client: Neo4jHttpClient, managed_labels: list[str]
) -> list[dict[str, JsonValue]]:
    if not managed_labels:
        return []
    rows = client.query(
        (
            "UNWIND $managed_labels AS label "
            "OPTIONAL MATCH (n) "
            "WHERE label IN labels(n) "
            "AND coalesce(n.managed_by, '') = '' "
            "RETURN label, count(n) AS count, collect(n.name)[0..10] AS samples "
            "ORDER BY label"
        ),
        {
            "managed_labels": managed_labels,
        },
        context="full audit unmanaged summary",
    )
    return [
        {
            "label": str(row["label"]),
            "count": _coerce_int(row["count"]),
            "samples": row.get("samples", []),
        }
        for row in rows
        if isinstance(row.get("label"), str)
        and isinstance(row.get("count"), (int, float))
        and _coerce_int(row["count"]) > 0
    ]


def _live_scalar(
    client: Neo4jHttpClient, statement: str, parameters: dict[str, JsonValue]
) -> int:
    rows = client.query(statement, parameters)
    if not rows:
        return 0
    value = next(iter(rows[0].values()), 0)
    return int(value) if isinstance(value, (int, float)) else 0


def _row_int_total(rows: list[dict[str, JsonValue]], key: str) -> int:
    return sum(
        _coerce_int(row[key]) for row in rows if isinstance(row.get(key), (int, float))
    )


def _managed_label_counts_from_rows(
    rows: list[dict[str, JsonValue]],
) -> dict[str, int]:
    return {
        str(row["label"]): _coerce_int(row["managed"])
        for row in rows
        if isinstance(row.get("label"), str)
    }


def _managed_relation_counts_from_rows(
    rows: list[dict[str, JsonValue]],
) -> dict[str, int]:
    return {
        str(row["relation_type"]): _coerce_int(row["total"])
        for row in rows
        if isinstance(row.get("relation_type"), str)
    }


def _snapshot_count_map(
    snapshot_stats: dict[str, JsonValue],
    key: str,
) -> dict[str, int]:
    raw_counts = snapshot_stats[key]
    if not isinstance(raw_counts, dict):
        return {}
    return {str(name): _coerce_int(count) for name, count in raw_counts.items()}


def _snapshot_subset_count_map(
    snapshot_stats: dict[str, JsonValue],
    key: str,
    names: tuple[str, ...],
) -> dict[str, int]:
    raw_counts = snapshot_stats[key]
    if not isinstance(raw_counts, dict):
        return {}
    return {name: _coerce_int(raw_counts.get(name, 0)) for name in names}


def _managed_label_summary_from_counts(
    label_counts: dict[str, int],
) -> list[dict[str, JsonValue]]:
    return [
        {
            "label": label,
            "managed": count,
            "count": count,
            "unmanaged": 0,
        }
        for label, count in label_counts.items()
    ]


def _managed_relation_summary_from_counts(
    relation_counts: dict[str, int],
) -> list[dict[str, JsonValue]]:
    return [
        {"relation_type": relation_type, "total": total}
        for relation_type, total in relation_counts.items()
    ]


def _audit_live_summary(
    *,
    managed_node_total: int,
    managed_relation_total: int,
    unmanaged_repo_node_total: int,
    label_summary: list[dict[str, JsonValue]],
    managed_relation_summary: list[dict[str, JsonValue]],
    orphan_summary: list[dict[str, JsonValue]],
    unmanaged_summary: list[dict[str, JsonValue]],
) -> dict[str, JsonValue]:
    return {
        "managed_node_total": managed_node_total,
        "managed_relation_total": managed_relation_total,
        "unmanaged_repo_node_total": unmanaged_repo_node_total,
        "label_summary": label_summary,
        "managed_relation_summary": managed_relation_summary,
        "orphan_summary": {
            "total": _row_int_total(orphan_summary, "count"),
            "by_label": orphan_summary,
        },
        "unmanaged_summary": {
            "total": unmanaged_repo_node_total,
            "by_label": unmanaged_summary,
        },
    }


def _audit_report_payload(
    *,
    snapshot_payload: dict[str, JsonValue],
    managed_labels: list[str],
    live_summary: dict[str, JsonValue],
    snapshot_label_counts: dict[str, int],
    live_managed_label_counts: dict[str, int],
    snapshot_relation_counts: dict[str, int],
    live_managed_relation_counts: dict[str, int],
) -> dict[str, JsonValue]:
    return {
        "generated_at": _sync_run_id(),
        "managed_by": DEFAULT_MANAGED_BY,
        "ingest_wave": DEFAULT_INGEST_WAVE,
        "snapshot": snapshot_payload,
        "managed_labels": managed_labels,
        "live": live_summary,
        "diff": {
            "labels": _build_diff_entries(
                snapshot_label_counts, live_managed_label_counts
            ),
            "relation_types": _build_diff_entries(
                snapshot_relation_counts, live_managed_relation_counts
            ),
        },
    }


def build_audit_report(
    snapshot: GraphSnapshot,
    root: Path,
    http_uri: str | None,
) -> dict[str, JsonValue]:
    base_uri, username, password, database = resolve_neo4j_connection(root, http_uri)
    client = Neo4jHttpClient(base_uri, username, password, database)
    managed_labels = sorted(
        {node.key.label for node in snapshot.nodes.values()}
        | set(DEFAULT_LEGACY_PRUNE_LABELS)
    )
    snapshot_relation_types = sorted(
        {relation.relation_type for relation in snapshot.relations.values()}
    )
    snapshot_stats = snapshot.stats()
    live_label_rows = _live_repo_label_rows(client, managed_labels)
    live_relation_rows = _live_managed_relation_rows(client, snapshot_relation_types)
    orphan_rows = _live_orphan_rows(client, managed_labels)
    unmanaged_rows = _live_unmanaged_repo_rows(client, managed_labels)

    live_managed_label_counts = _managed_label_counts_from_rows(live_label_rows)
    live_managed_relation_counts = _managed_relation_counts_from_rows(
        live_relation_rows
    )
    managed_node_total = _row_int_total(live_label_rows, "managed")
    unmanaged_repo_node_total = _row_int_total(unmanaged_rows, "count")
    managed_relation_total = sum(live_managed_relation_counts.values())
    live_summary = _audit_live_summary(
        managed_node_total=managed_node_total,
        managed_relation_total=managed_relation_total,
        unmanaged_repo_node_total=unmanaged_repo_node_total,
        label_summary=live_label_rows,
        managed_relation_summary=live_relation_rows,
        orphan_summary=orphan_rows,
        unmanaged_summary=unmanaged_rows,
    )
    return _audit_report_payload(
        snapshot_payload=snapshot_stats,
        managed_labels=managed_labels,
        live_summary=live_summary,
        snapshot_label_counts=_snapshot_count_map(snapshot_stats, "labels"),
        live_managed_label_counts=live_managed_label_counts,
        snapshot_relation_counts=_snapshot_count_map(snapshot_stats, "relation_types"),
        live_managed_relation_counts=live_managed_relation_counts,
    )


def build_fast_analysis_audit_report(
    snapshot: GraphSnapshot,
    root: Path,
    http_uri: str | None,
) -> dict[str, JsonValue]:
    base_uri, username, password, database = resolve_neo4j_connection(root, http_uri)
    client = Neo4jHttpClient(base_uri, username, password, database)
    snapshot_stats = snapshot.stats()
    active_labels, active_relation_types = _fast_analysis_scope(snapshot_stats)
    snapshot_label_counts, snapshot_relation_counts = _fast_analysis_snapshot_counts(
        snapshot_stats,
        active_labels,
        active_relation_types,
    )
    live_managed_label_counts, live_managed_relation_counts = (
        _fast_analysis_live_counts(
            client,
            active_labels,
            active_relation_types,
        )
    )
    live_summary = _fast_analysis_live_summary(
        live_managed_label_counts,
        live_managed_relation_counts,
    )
    return _audit_report_payload(
        snapshot_payload=_fast_audit_snapshot_payload(
            snapshot_label_counts, snapshot_relation_counts
        ),
        managed_labels=list(active_labels),
        live_summary=live_summary,
        snapshot_label_counts=snapshot_label_counts,
        live_managed_label_counts=live_managed_label_counts,
        snapshot_relation_counts=snapshot_relation_counts,
        live_managed_relation_counts=live_managed_relation_counts,
    )


def _fast_analysis_scope(
    snapshot_stats: dict[str, JsonValue],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return (
        _active_critical_names(snapshot_stats, "labels", CRITICAL_ANALYSIS_NODE_LABELS),
        _active_critical_names(
            snapshot_stats, "relation_types", CRITICAL_ANALYSIS_RELATION_TYPES
        ),
    )


def _fast_analysis_snapshot_counts(
    snapshot_stats: dict[str, JsonValue],
    active_labels: tuple[str, ...],
    active_relation_types: tuple[str, ...],
) -> tuple[dict[str, int], dict[str, int]]:
    return (
        _snapshot_subset_count_map(snapshot_stats, "labels", active_labels),
        _snapshot_subset_count_map(
            snapshot_stats, "relation_types", active_relation_types
        ),
    )


def _fast_analysis_live_counts(
    client: Neo4jHttpClient,
    active_labels: tuple[str, ...],
    active_relation_types: tuple[str, ...],
) -> tuple[dict[str, int], dict[str, int]]:
    return (
        _live_managed_node_counts(
            client,
            active_labels,
            context="fast audit label summary",
        ),
        _live_managed_relation_counts(
            client,
            active_relation_types,
            context="fast audit relation summary",
        ),
    )


def _fast_analysis_live_summary(
    live_managed_label_counts: dict[str, int],
    live_managed_relation_counts: dict[str, int],
) -> dict[str, JsonValue]:
    return _audit_live_summary(
        managed_node_total=sum(live_managed_label_counts.values()),
        managed_relation_total=sum(live_managed_relation_counts.values()),
        unmanaged_repo_node_total=0,
        label_summary=_managed_label_summary_from_counts(live_managed_label_counts),
        managed_relation_summary=_managed_relation_summary_from_counts(
            live_managed_relation_counts
        ),
        orphan_summary=[],
        unmanaged_summary=[],
    )


def _active_critical_names(
    snapshot_stats: dict[str, JsonValue],
    key: str,
    critical_names: set[str],
) -> tuple[str, ...]:
    raw_counts = snapshot_stats.get(key)
    if not isinstance(raw_counts, dict):
        return ()
    return tuple(
        name for name in critical_names if _coerce_int(raw_counts.get(name, 0)) > 0
    )


def _fast_audit_snapshot_payload(
    snapshot_label_counts: dict[str, int],
    snapshot_relation_counts: dict[str, int],
) -> dict[str, JsonValue]:
    return {
        "node_count": sum(snapshot_label_counts.values()),
        "relation_count": sum(snapshot_relation_counts.values()),
        "labels": snapshot_label_counts,
        "relation_types": snapshot_relation_counts,
    }


def _critical_analysis_audit_issues(report: dict[str, JsonValue]) -> list[str]:
    issues: list[str] = []
    diff = report.get("diff", {})
    label_rows = diff.get("labels", []) if isinstance(diff, dict) else []
    relation_rows = diff.get("relation_types", []) if isinstance(diff, dict) else []

    issues.extend(
        _critical_diff_issues(label_rows, CRITICAL_ANALYSIS_NODE_LABELS, kind="label")
    )
    issues.extend(
        _critical_diff_issues(
            relation_rows, CRITICAL_ANALYSIS_RELATION_TYPES, kind="relation"
        )
    )
    return issues


def _critical_diff_issues(
    rows: object,
    critical_names: set[str],
    *,
    kind: str,
) -> list[str]:
    issues: list[str] = []
    if not isinstance(rows, list):
        return issues
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = row.get("name")
        delta = row.get("delta")
        if name in critical_names and delta:
            issues.append(
                f"{kind} `{name}` expected {row.get('snapshot')}, live managed {row.get('live_managed')}"
            )
    return issues


def _selection_from_args(args: argparse.Namespace) -> SnapshotSelection:
    from memory.graph.sync_pkg import cli as _cli

    return _cli._selection_from_args(args)


def _validate_cli_args(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> None:
    from memory.graph.sync_pkg import cli as _cli

    _cli._validate_cli_args(parser, args)


def _print_snapshot_stats(snapshot: GraphSnapshot) -> None:
    from memory.graph.sync_pkg import cli as _cli

    return _cli._print_snapshot_stats(snapshot)


def _export_snapshot_if_requested(
    snapshot: GraphSnapshot,
    export_path: Path | None,
) -> None:
    from memory.graph.sync_pkg import cli as _cli

    _cli._export_snapshot_if_requested(snapshot, export_path)


def _sync_snapshot_if_requested(
    args: argparse.Namespace,
    snapshot: GraphSnapshot,
    root: Path,
    selection: SnapshotSelection,
) -> None:
    from memory.graph.sync_pkg import cli as _cli

    _cli._sync_snapshot_if_requested(args, snapshot, root, selection)


def _report_payload(
    snapshot: GraphSnapshot,
    root: Path,
    http_uri: str | None,
    report_fast: bool,
) -> dict[str, JsonValue]:
    from memory.graph.sync_pkg import cli as _cli

    return _cli._report_payload(snapshot, root, http_uri, report_fast)


def _write_report_if_requested(
    snapshot: GraphSnapshot,
    root: Path,
    http_uri: str | None,
    report_path: Path | None,
    report_fast: bool,
) -> None:
    from memory.graph.sync_pkg import cli as _cli

    _cli._write_report_if_requested(
        snapshot,
        root,
        http_uri,
        report_path,
        report_fast,
    )


def _normalization_operation_count(summary: dict[str, JsonValue]) -> int:
    from memory.graph.sync_pkg import cli as _cli

    return _cli._normalization_operation_count(summary)


def _snapshot_operation_count(args: argparse.Namespace) -> int:
    from memory.graph.sync_pkg import cli as _cli

    return _cli._snapshot_operation_count(args)


def _run_apply_normalization_evidence_only(args: argparse.Namespace) -> int:
    """Execute normalization-evidence-only mode and return the CLI exit code."""
    from memory.graph.sync_pkg import cli as _cli

    return _cli._run_apply_normalization_evidence_only(args)


def _run_snapshot_cli(args: argparse.Namespace) -> int:
    """Execute the standard snapshot/sync CLI flow and return the exit code."""
    from memory.graph.sync_pkg import cli as _cli

    return _cli._run_snapshot_cli(args)


def main(argv: list[str] | None = None) -> int:
    from memory.graph.sync_pkg import cli as _cli

    return _cli.main(argv)


__all__ = [name for name in globals() if not name.startswith("__")]


if __name__ == "__main__":
    raise SystemExit(main())
