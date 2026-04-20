"""Filtering helpers for deterministic RAG source selection."""

from __future__ import annotations

from pathlib import Path

from memory.resources import CATALOG_DIR, POLICY_DIR, load_yaml_resource

DEFAULT_SOURCE_PATHS = (
    Path("docs/00-project"),
    Path("docs/02-architecture/decisions"),
    Path("docs/05-operations/runbooks"),
)


def _load_exclusion_patterns() -> list[str]:
    payload = load_yaml_resource(POLICY_DIR / "exclusions.yaml")
    patterns = []
    for section in ("default_exclusions", "rag_exclusions"):
        for item in payload.get(section, []):
            if isinstance(item, dict) and isinstance(item.get("pattern"), str):
                patterns.append(item["pattern"])
    return patterns


def _load_source_paths() -> tuple[Path, ...]:
    registry = load_yaml_resource(CATALOG_DIR / "source_registry.yaml")
    selected_ids = {"active_docs", "accepted_adrs"}
    paths: list[Path] = []
    for item in registry.get("sources", []):
        if not isinstance(item, dict) or item.get("id") not in selected_ids:
            continue
        for raw_path in item.get("paths", []):
            if isinstance(raw_path, str):
                paths.append(Path(raw_path))
    return tuple(paths) or DEFAULT_SOURCE_PATHS


def iter_markdown_sources(root: Path) -> list[Path]:
    """Return deterministic markdown sources for the initial RAG corpus."""
    exclusion_patterns = _load_exclusion_patterns()
    results: list[Path] = []
    for base in _load_source_paths():
        source_dir = root / base
        if not source_dir.exists():
            continue
        for path in sorted(source_dir.rglob("*.md")):
            rel_path = path.relative_to(root).as_posix()
            if any(path.match(pattern) or rel_path.startswith(pattern.rstrip("/**")) for pattern in exclusion_patterns):
                continue
            if "/notes/" in rel_path:
                continue
            results.append(path)
    return results
