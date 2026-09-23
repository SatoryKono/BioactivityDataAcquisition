"""File-structure mapping defaults extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import GITHUB_DIR, _as_string_list
from memory.graph.sync_pkg.mapping_io import _mapping_section

__all__ = [
    "DEFAULT_FILE_STRUCTURE_EXCLUDED_DIR_NAMES",
    "DEFAULT_FILE_STRUCTURE_EXCLUDED_PREFIXES",
    "DEFAULT_FILE_STRUCTURE_REPO_ZONES",
    "_file_structure_config",
]

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
    "docs/02-architecture/diagrams/providers",
    "scripts/diagrams/svg2png.mjs",
    "scripts/archive",
)
DEFAULT_FILE_STRUCTURE_EXCLUDED_DIR_NAMES: tuple[str, ...] = ("__pycache__",)


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
