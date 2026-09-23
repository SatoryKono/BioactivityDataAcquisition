"""Python/repo path helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import (
    _as_string_list,
    _module_dotted_name,
    _normalize_repo_relative_path,
)
from memory.graph.sync_pkg._core_models import NodeKey

__all__ = [
    "INIT_PY",
    "MAIN_PY",
    "OPS_SCRIPT_HUB_PREFIXES",
    "_coerce_repo_relative_path",
    "_is_excluded_file_structure_path",
    "_promoted_directory_hubs",
    "_python_surface_name",
    "_supplemental_directory_hubs_for_node",
]

INIT_PY = "__init__.py"
MAIN_PY = "__main__.py"

OPS_SCRIPT_HUB_PREFIXES: tuple[str, ...] = (
    "scripts/diagrams/",
    "scripts/docs/",
    "scripts/engineering/qa/",
    "scripts/schema/",
    "scripts/memory/",
)


def _python_surface_name(relative_path: str) -> str:
    init_suffix = f"/{INIT_PY}"
    if relative_path.endswith(init_suffix):
        dotted = relative_path.removesuffix(init_suffix).replace("/", ".")
    else:
        dotted = _module_dotted_name(relative_path)
    return dotted.removeprefix("src.")


def _coerce_repo_relative_path(root: Path, raw_path: str) -> str:
    normalized = _normalize_repo_relative_path(raw_path)
    if not normalized:
        return ""

    root_normalized = _normalize_repo_relative_path(root.resolve().as_posix())
    normalized_lower = normalized.casefold()
    root_lower = root_normalized.casefold()
    if normalized_lower == root_lower:
        return ""
    if normalized_lower.startswith(f"{root_lower}/"):
        return normalized[len(root_normalized) + 1 :]

    root_anchor = root.resolve().name.casefold()
    parts = [part for part in normalized.split("/") if part]
    parts_lower = [part.casefold() for part in parts]
    if root_anchor in parts_lower:
        anchor_index = parts_lower.index(root_anchor)
        return "/".join(parts[anchor_index + 1 :])

    return normalized


def _is_excluded_file_structure_path(
    relative_path: str, config: dict[str, object]
) -> bool:
    normalized = _normalize_repo_relative_path(relative_path)
    path = Path(normalized)
    excluded_dir_names = {
        name for name in _as_string_list(config.get("excluded_dir_names")) if name
    }
    if any(part in excluded_dir_names for part in path.parts):
        return True
    # Keep generated diagram raster/vector trees out of file-structure surfaces.
    # Aligns with snapshot_invariant_issues path-leak checks for /svg and /png.
    if any(part in {"svg", "png"} for part in path.parts):
        return True

    excluded_prefixes = [
        prefix.strip("/")
        for prefix in _as_string_list(config.get("excluded_prefixes"))
        if prefix
    ]
    return any(
        normalized == prefix or normalized.startswith(f"{prefix}/")
        for prefix in excluded_prefixes
    )


def _promoted_directory_hubs(
    relative_path: str, config: dict[str, object]
) -> list[str]:
    promoted = {
        entry.strip("/")
        for entry in _as_string_list(config.get("promoted_hubs"))
        if entry
    }
    path = Path(relative_path)
    matches: list[str] = []
    for index in range(1, len(path.parts) + 1):
        candidate = Path(*path.parts[:index]).as_posix()
        if candidate in promoted:
            matches.append(candidate)
    return matches


def _supplemental_directory_hubs_for_node(
    node_key: NodeKey, source_path_value: str
) -> tuple[str, ...]:
    if node_key.label == "script_surface" and any(
        source_path_value.startswith(prefix) for prefix in OPS_SCRIPT_HUB_PREFIXES
    ):
        return ("scripts/ops",)
    return ()
