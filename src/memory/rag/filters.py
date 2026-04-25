"""Filtering helpers for deterministic RAG source selection."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

from memory.resources import CATALOG_DIR, POLICY_DIR, load_yaml_resource

DEFAULT_SOURCE_PATHS = (
    Path("docs/00-project"),
    Path("docs/01-requirements"),
    Path("docs/02-architecture/decisions"),
    Path("docs/plans"),
    Path("docs/05-operations/runbooks"),
    Path("src/bioetl"),
    Path("tests"),
    Path("configs"),
    Path(".github/workflows"),
    Path("grafana"),
    Path("scripts/engineering"),
)

MARKDOWN_SUFFIXES = {".md"}
PYTHON_SUFFIXES = {".py"}
CONFIG_SUFFIXES = {".yaml", ".yml", ".json", ".toml"}
SCRIPT_SUFFIXES = {".py", ".sh", ".ps1"}
OPERATIONAL_SUFFIXES = MARKDOWN_SUFFIXES | CONFIG_SUFFIXES | SCRIPT_SUFFIXES
MEMORY_SUFFIXES = MARKDOWN_SUFFIXES | PYTHON_SUFFIXES | CONFIG_SUFFIXES

SOURCE_SUFFIXES = {
    "active_docs": MARKDOWN_SUFFIXES,
    "planning_docs": MARKDOWN_SUFFIXES,
    "accepted_adrs": MARKDOWN_SUFFIXES,
    "runtime_code": PYTHON_SUFFIXES,
    "memory_implementation": MEMORY_SUFFIXES,
    "tests": PYTHON_SUFFIXES,
    "project_configs": CONFIG_SUFFIXES,
    "operational_assets": OPERATIONAL_SUFFIXES,
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
        "planning_docs",
        "accepted_adrs",
        "runtime_code",
        "memory_implementation",
        "tests",
        "project_configs",
        "operational_assets",
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
        "planning_docs",
        "accepted_adrs",
        "runtime_code",
        "memory_implementation",
        "tests",
        "project_configs",
        "operational_assets",
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
        ("active_docs", Path("docs/01-requirements")),
        ("accepted_adrs", Path("docs/02-architecture/decisions")),
        ("active_docs", Path("docs/plans")),
        ("active_docs", Path("docs/05-operations/runbooks")),
        ("runtime_code", Path("src/bioetl")),
        ("memory_implementation", Path("src/memory")),
        ("tests", Path("tests")),
        ("project_configs", Path("configs")),
        ("operational_assets", Path(".github/workflows")),
        ("operational_assets", Path("grafana")),
        ("operational_assets", Path("scripts/engineering")),
    ]


def _is_excluded(rel_path: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        normalized = pattern.rstrip("/")
        if fnmatch(rel_path, pattern):
            return True
        if normalized.endswith("/**") and rel_path.startswith(normalized[:-3]):
            return True
    return False


def _candidate_source_paths(
    *,
    root: Path,
    source_id: str,
    base: Path,
) -> list[Path]:
    suffixes = SOURCE_SUFFIXES.get(source_id, MARKDOWN_SUFFIXES)
    source_dir = root / base
    if not source_dir.exists():
        return []
    return [
        path
        for path in sorted(source_dir.rglob("*"))
        if path.is_file() and path.suffix.lower() in suffixes
    ]


def _should_include_source(
    *,
    rel_path: str,
    seen: set[str],
    exclusion_patterns: list[str],
) -> bool:
    if rel_path in seen:
        return False
    if _is_excluded(rel_path, exclusion_patterns):
        return False
    return "/notes/" not in rel_path


def iter_rag_sources(root: Path) -> list[Path]:
    """Return deterministic RAG sources across docs, code, tests, and configs."""
    exclusion_patterns = _load_exclusion_patterns()
    results: list[Path] = []
    seen: set[str] = set()
    for source_id, base in _load_source_specs():
        for path in _candidate_source_paths(root=root, source_id=source_id, base=base):
            rel_path = path.relative_to(root).as_posix()
            if not _should_include_source(
                rel_path=rel_path,
                seen=seen,
                exclusion_patterns=exclusion_patterns,
            ):
                continue
            seen.add(rel_path)
            results.append(path)
    print(f"DEBUG: iter_rag_sources found {len(results)} files.")
    return results


def iter_markdown_sources(root: Path) -> list[Path]:
    """Return only markdown RAG sources for backward-compatible callers."""
    return [
        path
        for path in iter_rag_sources(root)
        if path.suffix.lower() in MARKDOWN_SUFFIXES
    ]
