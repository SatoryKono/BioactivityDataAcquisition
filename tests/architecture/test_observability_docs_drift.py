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
"""Guardrails for observability docs/code drift."""

from __future__ import annotations

import re

import pytest

from pathlib import Path

from bioetl.infrastructure.observability.prometheus_metric_registries import (
    REGISTERED_PROMETHEUS_METRIC_NAMES,
)

pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OBSERVABILITY_MAP_BLOCK = (
    "│   │   ├── observability/       # Observability port package"
)
LEGACY_OBSERVABILITY_MAP_BLOCK = (
    "│   │   ├── observability.py     # MetricsPort, TracingPort, LoggerPort"
)
MANUAL_METRIC_COUNT_CLAIMS = (
    "101 metrics",
    "110 metrics",
)
CANONICAL_REGISTRY_REFERENCE = "REGISTERED_PROMETHEUS_METRIC_NAMES"
INVENTORY_REPORT_COMMAND = (
    "python -m scripts.engineering.qa report-observability-metric-inventory --json"
)
LEGACY_METRICS_PORT_PATH = PROJECT_ROOT / "src/bioetl/domain/ports/metrics_port.py"
METRICS_CATALOG_PATH = (
    PROJECT_ROOT / "docs/04-reference/observability/metrics-catalog.md"
)
TRACING_GUIDE_PATH = (
    PROJECT_ROOT / "docs/04-reference/observability/tracing-guide.md"
)
LOGGING_GUIDE_PATH = (
    PROJECT_ROOT / "docs/04-reference/observability/logging-guide.md"
)


def test_project_navigator_tracks_package_based_observability_ports() -> None:
    navigator = (PROJECT_ROOT / "docs/00-project/00-map.md").read_text(encoding="utf-8")
    assert OBSERVABILITY_MAP_BLOCK in navigator, (
        "Project Navigator must describe package-based observability ports."
    )
    assert LEGACY_OBSERVABILITY_MAP_BLOCK not in navigator, (
        "Project Navigator still references the legacy single-file observability "
        "port layout."
    )


def test_canonical_observability_docs_reference_registry_not_manual_count() -> None:
    registered_count = len(REGISTERED_PROMETHEUS_METRIC_NAMES)
    docs = {
        "docs/02-architecture/observability-layers.md": (
            PROJECT_ROOT / "docs/02-architecture/observability-layers.md"
        ).read_text(encoding="utf-8"),
        "docs/04-reference/contracts/observability.md": (
            PROJECT_ROOT / "docs/04-reference/contracts/observability.md"
        ).read_text(encoding="utf-8"),
    }

    for relative_path, content in docs.items():
        assert CANONICAL_REGISTRY_REFERENCE in content, (
            f"{relative_path} must reference the registry-backed metric inventory."
        )
        assert INVENTORY_REPORT_COMMAND in content, (
            f"{relative_path} must point to the inventory reconciliation command."
        )
        for claim in MANUAL_METRIC_COUNT_CLAIMS:
            assert claim not in content, (
                f"{relative_path} still contains a stale manual metric-count claim "
                f"({claim}); current registry count is {registered_count}."
            )


def test_legacy_metrics_port_file_is_removed() -> None:
    assert not LEGACY_METRICS_PORT_PATH.exists(), (
        "Legacy src/bioetl/domain/ports/metrics_port.py must not coexist with the "
        "canonical package-based observability metrics port."
    )


def test_metrics_catalog_runtime_rows_match_canonical_registry() -> None:
    catalog = METRICS_CATALOG_PATH.read_text(encoding="utf-8")
    runtime_section, separator, governed_section = catalog.partition(
        "## Governed Recording And Current-State Metrics"
    )
    assert separator, "Governed metrics section not found in catalog"

    catalog_runtime_metrics = set(
        re.findall(
            r"^\| `([^`]+)` \| (?:Counter|Gauge|Histogram) \|",
            runtime_section,
            flags=re.MULTILINE,
        )
    )
    registered_metrics = set(REGISTERED_PROMETHEUS_METRIC_NAMES)

    assert catalog_runtime_metrics == registered_metrics
    registered_count = len(registered_metrics)
    assert f"**Runtime Metrics: {registered_count}**" in catalog
    assert f"**Runtime Metrics**: {registered_count}" in catalog

    alias_section = governed_section.split("## Governed Policy Aliases", 1)[1].split(
        "## Governed Recording And Current-State Inventory", 1
    )[0]
    inventory_section = governed_section.split(
        "## Governed Recording And Current-State Inventory", 1
    )[1].split("\n---", 1)[0]
    alias_metrics = set(
        re.findall(r"^\| `([^`]+)` \|", alias_section, flags=re.MULTILINE)
    )
    governed_metrics = set(
        re.findall(r"^\| `([^`]+)` \|", inventory_section, flags=re.MULTILINE)
    )

    assert registered_metrics.isdisjoint(alias_metrics)
    assert registered_metrics.isdisjoint(governed_metrics)
    assert len(alias_metrics) == 15
    assert len(governed_metrics) == 41
    assert "**Governed Recording/Current-State Metrics: 41**" in catalog
    assert "**Governed Recording/Current-State Metrics**: 41" in catalog


def test_dq_validation_score_docs_use_canonical_ratio_scale() -> None:
    rules = (PROJECT_ROOT / "docs/00-project/RULES.md").read_text(encoding="utf-8")
    panel_guide = (
        PROJECT_ROOT / "docs/03-guides/dashboards/panels/bioetl-dq-v2-panels.md"
    ).read_text(encoding="utf-8")
    dashboard = (PROJECT_ROOT / "grafana/dashboards/bioetl-dq-v2.json").read_text(
        encoding="utf-8"
    )

    for content in (rules, panel_guide, dashboard):
        assert "0.0-1.0" in content
        assert "0-100" not in content


def test_reference_guides_distinguish_run_identity_from_otel_context() -> None:
    """Reference docs must not model a run UUID as an OTel trace identifier."""
    tracing_guide = TRACING_GUIDE_PATH.read_text(encoding="utf-8")
    logging_guide = LOGGING_GUIDE_PATH.read_text(encoding="utf-8")

    assert "uuid.uuid4()" not in tracing_guide
    for content in (tracing_guide, logging_guide):
        assert "`run_id`" in content
        assert "`trace_id`" in content
        assert "`span_id`" in content
        assert "OpenTelemetry" in content
    assert "32 символа" in tracing_guide
    assert "16 символов" in tracing_guide
    assert "Без активного span" in logging_guide
