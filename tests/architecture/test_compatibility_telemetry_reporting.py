"""Architecture guardrails for compatibility telemetry reporting."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest
import sys

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ci._compatibility_telemetry import (
    collect_compatibility_surface_snapshot,
    render_compatibility_surface_section,
)

ROOT = Path(__file__).resolve().parents[2]
INVENTORY_DOC = (
    ROOT / "docs" / "02-architecture" / "07-compatibility-facade-inventory.md"
)


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
    snapshot = collect_compatibility_surface_snapshot()
    status_counts = _iter_inventory_statuses()
    text = INVENTORY_DOC.read_text(encoding="utf-8")

    assert snapshot.curated_inventory_rows == sum(status_counts.values())
    assert snapshot.deprecated_warn_modules == status_counts["deprecated-warn"]
    assert snapshot.compat_shim_modules == status_counts["compat-shim"]
    assert snapshot.mixed_modules == status_counts["mixed-module"]
    assert snapshot.retained_entrypoints == status_counts["retained-entrypoint"]
    assert (
        f"- Curated inventory rows: `{snapshot.curated_inventory_rows}`" in text
    )
    assert (
        f"- Measured tracked modules: `{snapshot.measured_tracked_modules}`" in text
    )
    assert f"- Measured-only modules outside curated inventory: `{snapshot.measured_only_modules}`" in text


@pytest.mark.architecture
def test_compatibility_surface_summary_section_lists_required_metrics() -> None:
    """Rendered telemetry section should expose stable metric names for CI reports."""
    snapshot = collect_compatibility_surface_snapshot()
    section = render_compatibility_surface_section(
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
