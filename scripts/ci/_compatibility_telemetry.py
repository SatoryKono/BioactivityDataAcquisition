"""Compatibility-surface telemetry helpers for CI quality reporting."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

INVENTORY_ROW_CELL_COUNT = 10
TRACKED_DOCSTRING_PREFIXES = (
    "Backward-compatible ",
    "Compatibility ",
    "Compatibility-",
    "Deprecated compatibility",
    "Composition-level compatibility",
    "Pipeline factory compatibility-only facade",
    "Storage compatibility-only facade",
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INVENTORY_DOC = (
    _REPO_ROOT / "docs" / "02-architecture" / "07-compatibility-facade-inventory.md"
)
DEFAULT_SRC_ROOT = _REPO_ROOT / "src" / "bioetl"


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


def _iter_inventory_rows(inventory_doc: Path) -> list[dict[str, str]]:
    text = inventory_doc.read_text(encoding="utf-8")
    rows: list[dict[str, str]] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("| `src/bioetl/"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != INVENTORY_ROW_CELL_COUNT:
            raise ValueError(f"Unexpected compatibility inventory row format: {line}")
        rows.append(
            {
                "path": cells[0].strip("`"),
                "status": cells[3].strip("`"),
            }
        )

    return rows


def _iter_docstring_tracked_modules(src_root: Path, repo_root: Path) -> set[str]:
    tracked_paths: set[str] = set()

    for path in src_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        module_docstring = ast.get_docstring(tree)
        if module_docstring is None:
            continue
        first_line = module_docstring.splitlines()[0].strip()
        if first_line.startswith(TRACKED_DOCSTRING_PREFIXES):
            tracked_paths.add(path.relative_to(repo_root).as_posix())

    return tracked_paths


def collect_compatibility_surface_snapshot(
    *,
    inventory_doc: Path = DEFAULT_INVENTORY_DOC,
    src_root: Path = DEFAULT_SRC_ROOT,
) -> CompatibilitySurfaceSnapshot:
    """Collect compatibility-surface counters from inventory + tracked docstrings."""
    repo_root = inventory_doc.resolve().parents[2]
    rows = _iter_inventory_rows(inventory_doc.resolve())
    inventory_paths = {row["path"] for row in rows}
    measured_paths = inventory_paths | _iter_docstring_tracked_modules(
        src_root.resolve(), repo_root
    )

    status_counts = {
        "deprecated-warn": 0,
        "compat-shim": 0,
        "mixed-module": 0,
        "retained-entrypoint": 0,
    }
    for row in rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1

    return CompatibilitySurfaceSnapshot(
        curated_inventory_rows=len(rows),
        measured_tracked_modules=len(measured_paths),
        measured_only_modules=len(measured_paths - inventory_paths),
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
