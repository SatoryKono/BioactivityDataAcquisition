"""Duplication family scoring extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg.graph_contexts import DuplicateFamilyConfig

__all__ = [
    "_family_for_path",
    "_family_matches_relative_path",
    "_family_root_priority",
    "_presence_score",
    "_semantic_tags",
    "_threshold_score",
]


def _threshold_score(value: int, *, medium: int, high: int) -> int:
    if value >= high:
        return 2
    if value >= medium:
        return 1
    return 0


def _presence_score(size: int) -> int:
    return _threshold_score(size, medium=1, high=2)


def _semantic_tags(relative_path: str, symbol_name: str) -> tuple[str, ...]:
    normalized = f"{relative_path} {symbol_name}".lower()
    tags = []
    for tag in (
        "normalize",
        "health",
        "retry",
        "fallback",
        "merge",
        "join",
        "request",
        "response",
        "contract",
        "schema",
        "manifest",
        "lineage",
        "metadata",
        "pipeline",
    ):
        if tag in normalized:
            tags.append(tag)
    return tuple(sorted(set(tags)))


def _family_for_path(
    relative_path: str, config: dict[str, object]
) -> DuplicateFamilyConfig | None:
    families = config.get("families", ())
    if not isinstance(families, tuple):
        return None
    best: DuplicateFamilyConfig | None = None
    for family in families:
        if not isinstance(family, DuplicateFamilyConfig):
            continue
        if not _family_matches_relative_path(relative_path, family):
            continue
        if best is None or _family_root_priority(family) > _family_root_priority(best):
            best = family
    return best


def _family_matches_relative_path(
    relative_path: str, family: DuplicateFamilyConfig
) -> bool:
    if relative_path in family.excluded_paths:
        return False
    return any(
        relative_path == root or relative_path.startswith(f"{root}/")
        for root in family.roots
    )


def _family_root_priority(family: DuplicateFamilyConfig) -> int:
    return max(len(root) for root in family.roots)
