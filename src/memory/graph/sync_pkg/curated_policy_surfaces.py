"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg.default_batch_size import (
    DOC_ARCHITECTURE_DIAGRAMS_HUB,
    DOC_DIAGRAM_TOOLING_README,
    DOC_GRAFANA_DASHBOARDS_JSON,
    DOCS_VERIFICATION_GUIDE_PATH,
    GATE_CONFIG_VALIDATION,
    GATE_DIAGRAM_QUALITY,
    GATE_DOCS_VERIFICATION,
    GATE_MYPY_STRICT,
    GATE_PRETEST_GUARDRAILS,
    INTEGRATION_VCR_POLICY_PATH,
    KNOWN_LAYERS,
    RULES_DOC_PATH,
    TEST_MATRIX_CONFIG_PATH,
    TEST_SURFACE_ARCHITECTURE,
    TEST_SURFACE_E2E,
    TEST_SURFACE_INTEGRATION,
    TESTING_GUIDE_PATH,
)

__all__ = [
    "CURATED_POLICY_SURFACES",
]

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
