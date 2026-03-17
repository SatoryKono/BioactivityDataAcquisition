"""Architecture guardrails for compatibility telemetry reporting."""

from __future__ import annotations

from collections import Counter
import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
INVENTORY_DOC = (
    ROOT / "docs" / "02-architecture" / "07-compatibility-facade-inventory.md"
)


def _load_compatibility_telemetry_module() -> ModuleType:
    script = (ROOT / "scripts" / "ci" / "_compatibility_telemetry.py").resolve()
    spec = importlib.util.spec_from_file_location(
        "compatibility_telemetry_reporting", str(script)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["compatibility_telemetry_reporting"] = module
    spec.loader.exec_module(module)
    return module


def _iter_inventory_statuses() -> Counter[str]:
    statuses: Counter[str] = Counter()
    text = INVENTORY_DOC.read_text(encoding="utf-8")

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("| `src/bioetl/"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        statuses[cells[3].strip("`")] += 1

    return statuses


@pytest.mark.architecture
def test_compatibility_surface_snapshot_matches_inventory_status_counts() -> None:
    """CI telemetry should stay aligned with curated compatibility inventory rows."""
    mod = _load_compatibility_telemetry_module()
    snapshot = mod.collect_compatibility_surface_snapshot()
    status_counts = _iter_inventory_statuses()
    text = INVENTORY_DOC.read_text(encoding="utf-8")

    assert snapshot.curated_inventory_rows == sum(status_counts.values())
    assert snapshot.deprecated_warn_modules == status_counts["deprecated-warn"]
    assert snapshot.compat_shim_modules == status_counts["compat-shim"]
    assert snapshot.mixed_modules == status_counts["mixed-module"]
    assert snapshot.retained_entrypoints == status_counts["retained-entrypoint"]
    assert f"- Curated inventory rows: `{snapshot.curated_inventory_rows}`" in text
    assert f"- Measured tracked modules: `{snapshot.measured_tracked_modules}`" in text
    assert (
        f"- Measured-only modules outside curated inventory: `{snapshot.measured_only_modules}`"
        in text
    )


@pytest.mark.architecture
def test_compatibility_surface_summary_section_lists_required_metrics() -> None:
    """Rendered telemetry section should expose stable metric names for CI reports."""
    mod = _load_compatibility_telemetry_module()
    snapshot = mod.collect_compatibility_surface_snapshot()
    section = mod.render_compatibility_surface_section(
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
    ):
        assert f"- {key}: `" in section
