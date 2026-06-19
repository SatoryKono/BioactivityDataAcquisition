"""Architecture guardrails for curated surface telemetry reporting."""

from __future__ import annotations

from collections import Counter
import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_YAML = ROOT / "configs" / "quality" / "compatibility_facade_inventory.yaml"


def _load_module(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, str(path.resolve()))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_compatibility_telemetry_module() -> ModuleType:
    return _load_module(
        ROOT / "scripts" / "engineering" / "ci" / "_compatibility_telemetry.py",
        "compatibility_telemetry_reporting",
    )


def _load_compatibility_registry_module() -> ModuleType:
    return _load_module(
        ROOT / "scripts" / "engineering" / "ci" / "_compatibility_registry.py",
        "compatibility_registry_loader",
    )


@pytest.mark.architecture
def test_compatibility_surface_snapshot_matches_registry_status_counts() -> None:
    """CI telemetry should stay aligned with the canonical YAML registry."""
    telemetry = _load_compatibility_telemetry_module()
    registry_mod = _load_compatibility_registry_module()
    registry = registry_mod.load_compatibility_registry(REGISTRY_YAML)
    snapshot = telemetry.collect_compatibility_surface_snapshot(
        registry_path=REGISTRY_YAML
    )

    status_counts = Counter(row.status for row in registry.curated_rows)

    assert snapshot.curated_inventory_rows == len(registry.curated_rows)
    assert snapshot.measured_tracked_modules == len(registry.measured_tracked_paths)
    assert snapshot.measured_only_modules == len(registry.measured_only_paths)
    assert snapshot.deprecated_warn_modules == status_counts["deprecated-warn"]
    assert snapshot.compat_shim_modules == status_counts["compat-shim"]
    assert snapshot.mixed_modules == status_counts["mixed-module"]
    assert snapshot.retained_entrypoints == status_counts["retained-entrypoint"]
    assert snapshot.public_entrypoints == status_counts["public-entrypoint"]


@pytest.mark.architecture
def test_compatibility_surface_summary_section_lists_required_metrics() -> None:
    """Rendered telemetry section should expose stable metric names for CI reports."""
    telemetry = _load_compatibility_telemetry_module()
    snapshot = telemetry.collect_compatibility_surface_snapshot(
        registry_path=REGISTRY_YAML
    )
    section = telemetry.render_compatibility_surface_section(
        snapshot, heading="## Compatibility Surface Snapshot"
    )

    assert section.startswith("## Compatibility Surface Snapshot")
    for key in (
        "curated_inventory_rows",
        "measured_tracked_modules",
        "measured_only_modules",
        "deprecated_warn_modules",
        "compat_shim_modules",
        "mixed_modules",
        "retained_entrypoints",
        "public_entrypoints",
    ):
        assert f"- {key}: `" in section
