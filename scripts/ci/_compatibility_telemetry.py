"""Compatibility-surface telemetry helpers for CI quality reporting."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _compatibility_registry import (  # type: ignore[import-not-found]
        DEFAULT_REGISTRY_PATH,
        load_compatibility_registry,
    )
else:
    from ._compatibility_registry import (
        DEFAULT_REGISTRY_PATH,
        load_compatibility_registry,
    )

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INVENTORY_DOC = (
    _REPO_ROOT / "docs" / "02-architecture" / "07-compatibility-facade-inventory.md"
)


@dataclass(frozen=True)
class CompatibilitySurfaceSnapshot:
    """Compact compatibility-surface counters used by CI reports."""

    curated_inventory_rows: int
    measured_tracked_modules: int
    measured_only_modules: int
    deprecated_warn_modules: int
    compat_shim_modules: int
    mixed_modules: int
    retained_entrypoints: int

    def as_dict(self) -> dict[str, int]:
        """Return a stable JSON-serializable mapping."""
        return {
            "curated_inventory_rows": self.curated_inventory_rows,
            "measured_tracked_modules": self.measured_tracked_modules,
            "measured_only_modules": self.measured_only_modules,
            "deprecated_warn_modules": self.deprecated_warn_modules,
            "compat_shim_modules": self.compat_shim_modules,
            "mixed_modules": self.mixed_modules,
            "retained_entrypoints": self.retained_entrypoints,
        }


def collect_compatibility_surface_snapshot(
    *,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
) -> CompatibilitySurfaceSnapshot:
    """Collect compatibility-surface counters from the canonical YAML registry."""
    registry = load_compatibility_registry(registry_path)
    rows = registry.curated_rows

    status_counts = {
        "deprecated-warn": 0,
        "compat-shim": 0,
        "mixed-module": 0,
        "retained-entrypoint": 0,
    }
    for row in rows:
        status_counts[row.status] = status_counts.get(row.status, 0) + 1

    return CompatibilitySurfaceSnapshot(
        curated_inventory_rows=len(rows),
        measured_tracked_modules=len(registry.measured_tracked_paths),
        measured_only_modules=len(registry.measured_only_paths),
        deprecated_warn_modules=status_counts["deprecated-warn"],
        compat_shim_modules=status_counts["compat-shim"],
        mixed_modules=status_counts["mixed-module"],
        retained_entrypoints=status_counts["retained-entrypoint"],
    )


def render_compatibility_surface_section(
    snapshot: CompatibilitySurfaceSnapshot, *, heading: str
) -> str:
    """Render a markdown section for CI summaries and weekly reports."""
    return "\n".join(
        [
            heading,
            f"- curated_inventory_rows: `{snapshot.curated_inventory_rows}`",
            f"- measured_tracked_modules: `{snapshot.measured_tracked_modules}`",
            f"- measured_only_modules: `{snapshot.measured_only_modules}`",
            f"- deprecated_warn_modules: `{snapshot.deprecated_warn_modules}`",
            f"- compat_shim_modules: `{snapshot.compat_shim_modules}`",
            f"- mixed_modules: `{snapshot.mixed_modules}`",
            f"- retained_entrypoints: `{snapshot.retained_entrypoints}`",
        ]
    )
