"""Filtering helpers for deterministic RAG source selection."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

from memory.resources import CATALOG_DIR, POLICY_DIR, load_yaml_resource

DEFAULT_SOURCE_PATHS = (
    Path("docs/00-project"),
    Path("docs/02-architecture/decisions"),
    Path("docs/05-operations/runbooks"),
    Path("src/bioetl"),
    Path("tests"),
    Path("configs"),
)

MARKDOWN_SUFFIXES = {".md"}
PYTHON_SUFFIXES = {".py"}
CONFIG_SUFFIXES = {".yaml", ".yml", ".json", ".toml"}

SOURCE_SUFFIXES = {
    "active_docs": MARKDOWN_SUFFIXES,
    "accepted_adrs": MARKDOWN_SUFFIXES,
    "runtime_code": PYTHON_SUFFIXES,
    "tests": PYTHON_SUFFIXES,
    "project_configs": CONFIG_SUFFIXES,
}


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
    selected_ids = {
        "active_docs",
        "accepted_adrs",
        "runtime_code",
        "tests",
        "project_configs",
    }
    paths: list[Path] = []
    for item in registry.get("sources", []):
        if not isinstance(item, dict) or item.get("id") not in selected_ids:
            continue
        for raw_path in item.get("paths", []):
            if isinstance(raw_path, str):
                paths.append(Path(raw_path))
    return tuple(paths) or DEFAULT_SOURCE_PATHS


def _load_source_specs() -> list[tuple[str, Path]]:
    registry = load_yaml_resource(CATALOG_DIR / "source_registry.yaml")
    selected_ids = {
        "active_docs",
        "accepted_adrs",
        "runtime_code",
        "tests",
        "project_configs",
    }
    specs: list[tuple[str, Path]] = []
    for item in registry.get("sources", []):
        if not isinstance(item, dict):
            continue
        source_id = item.get("id")
        if source_id not in selected_ids:
            continue
        for raw_path in item.get("paths", []):
            if isinstance(raw_path, str):
                specs.append((str(source_id), Path(raw_path)))
    if specs:
        return specs
    return [
        ("active_docs", Path("docs/00-project")),
        ("accepted_adrs", Path("docs/02-architecture/decisions")),
        ("active_docs", Path("docs/05-operations/runbooks")),
        ("runtime_code", Path("src/bioetl")),
        ("tests", Path("tests")),
        ("project_configs", Path("configs")),
    ]


def _is_excluded(rel_path: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        normalized = pattern.rstrip("/")
        if fnmatch(rel_path, pattern):
            return True
        if normalized.endswith("/**") and rel_path.startswith(normalized[:-3]):
            return True
    return False


def iter_rag_sources(root: Path) -> list[Path]:
    """Return deterministic RAG sources across docs, code, tests, and configs."""
    exclusion_patterns = _load_exclusion_patterns()
    results: list[Path] = []
    seen: set[str] = set()
    for source_id, base in _load_source_specs():
        suffixes = SOURCE_SUFFIXES.get(source_id, MARKDOWN_SUFFIXES)
        source_dir = root / base
        if not source_dir.exists():
            continue
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in suffixes:
                continue
            rel_path = path.relative_to(root).as_posix()
            if rel_path in seen:
                continue
            if _is_excluded(rel_path, exclusion_patterns):
                continue
            if "/notes/" in rel_path:
                continue
            seen.add(rel_path)
            results.append(path)
    return results


def iter_markdown_sources(root: Path) -> list[Path]:
    """Return only markdown RAG sources for backward-compatible callers."""
    return [path for path in iter_rag_sources(root) if path.suffix.lower() in MARKDOWN_SUFFIXES]
