"""Guardrails for observability docs/code drift."""

from __future__ import annotations

from pathlib import Path

from bioetl.infrastructure.observability.prometheus_metric_registries import (
    REGISTERED_PROMETHEUS_METRIC_NAMES,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OBSERVABILITY_MAP_BLOCK = "│   │   ├── observability/       # Observability port package"
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


def test_project_navigator_tracks_package_based_observability_ports() -> None:
    navigator = (PROJECT_ROOT / "docs/00-project/00-map.md").read_text(
        encoding="utf-8"
    )
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
