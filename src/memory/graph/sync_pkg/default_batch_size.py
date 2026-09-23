"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from bioetl.infrastructure.config.contract_registry_loader import (
    DEFAULT_CONTRACT_REGISTRY_PATH,
)
from memory.graph.sync_pkg._core_convert import GITHUB_DIR
from memory.graph.sync_pkg.python_paths import INIT_PY

__all__ = [
    "ADR_DECISIONS_DIR",
    "CHEMBL_ACTIVITY_CONTRACT_REF",
    "CONTRACT_REGISTRY_RELATIVE_PATH",
    "CURATED_DOC_SOURCES",
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_COMMON_PIPELINE_DASHBOARDS",
    "DEFAULT_COMPOSITE_PIPELINE_DASHBOARDS",
    "DEFAULT_ENTITY_PIPELINE_DASHBOARDS",
    "DEFAULT_LEGACY_REPORT_PATH",
    "DEFAULT_PIPELINE_RUNTIME_PATHS",
    "DEFAULT_PIPELINE_VALIDATION_GATES",
    "DOCS_VERIFICATION_GUIDE_PATH",
    "DOC_ARCHITECTURE_DIAGRAMS_HUB",
    "DOC_DIAGRAM_TOOLING_README",
    "DOC_GRAFANA_DASHBOARDS_JSON",
    "EFFECTIVE_CONFIG_ARTIFACT_REF",
    "GATE_CONFIG_VALIDATION",
    "GATE_DIAGRAM_QUALITY",
    "GATE_DOCS_VERIFICATION",
    "GATE_MYPY_STRICT",
    "GATE_NEO4J_ONTOLOGY_INVARIANTS",
    "GATE_PRETEST_GUARDRAILS",
    "GITHUB_WORKFLOWS_PREFIX",
    "GOVERNANCE_DECISIONS_SUMMARY_PATH",
    "INTEGRATION_VCR_POLICY_PATH",
    "KNOWN_LAYERS",
    "MANIFEST_ID_TEMPLATE",
    "PORTS_FACADE_SOURCE_PATH",
    "RULES_DOC_PATH",
    "RUN_ID_TEMPLATE",
    "RUN_LEDGER_ARTIFACT_REF",
    "RUN_MANIFEST_ARTIFACT_REF",
    "RUN_MANIFEST_INSPECTION_DOC_PATH",
    "RUN_MANIFEST_LEDGER_DOC_PATH",
    "TESTING_GUIDE_PATH",
    "TEST_MATRIX_CONFIG_PATH",
    "TEST_SURFACES",
    "TEST_SURFACE_ARCHITECTURE",
    "TEST_SURFACE_E2E",
    "TEST_SURFACE_INTEGRATION",
    "TRACEABILITY_SIGNAL_OWNERSHIP_DOC_PATH",
    "YAML_FILE_GLOB",
]

DEFAULT_BATCH_SIZE = 20
GITHUB_WORKFLOWS_PREFIX = f"{GITHUB_DIR}/workflows/"
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
ADR_DECISIONS_DIR = "docs/02-architecture/decisions"
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
