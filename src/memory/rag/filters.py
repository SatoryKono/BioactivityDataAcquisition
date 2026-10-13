"""Filtering helpers for deterministic RAG source selection."""

from __future__ import annotations

import os
import re
import subprocess
from fnmatch import fnmatch
from pathlib import Path

from memory.resources import CATALOG_DIR, POLICY_DIR, load_yaml_resource

DEFAULT_SOURCE_PATHS = (
    Path("docs/00-project"),
    Path("docs/01-requirements"),
    Path("docs/02-architecture/decisions"),
    Path("docs/plans"),
    Path("docs/05-operations/runbooks"),
    Path(".devin/wiki.json"),
    Path("src/bioetl"),
    Path("tests"),
    Path("configs"),
    Path(".github/workflows"),
    Path("grafana"),
    Path("scripts/engineering"),
)

DEFAULT_SELECTED_SOURCE_IDS = (
    "active_docs",
    "planning_docs",
    "accepted_adrs",
    "devin_wiki",
    "runtime_code",
    "memory_implementation",
    "tests",
    "project_configs",
    "operational_assets",
)
WORKFLOW_RAG_SOURCE_IDS = (
    "active_docs",
    "accepted_adrs",
    "runtime_code",
    "memory_implementation",
    "project_configs",
    "operational_assets",
)
WORKFLOW_RAG_MAX_SOURCES = 160

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
    "devin_wiki": CONFIG_SUFFIXES,
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


def _load_source_priority_order() -> tuple[str, ...]:
    payload = load_yaml_resource(POLICY_DIR / "source_priority.yaml")
    ordered_sources = payload.get("ordered_sources", [])
    priority_order = tuple(
        source_id for source_id in ordered_sources if isinstance(source_id, str)
    )
    return priority_order or DEFAULT_SELECTED_SOURCE_IDS


def _load_source_specs(
    *,
    selected_ids: tuple[str, ...] = DEFAULT_SELECTED_SOURCE_IDS,
) -> list[tuple[str, Path]]:
    registry = load_yaml_resource(CATALOG_DIR / "source_registry.yaml")
    selected_id_set = set(selected_ids)
    specs: list[tuple[str, Path]] = []
    for item in registry.get("sources", []):
        if not isinstance(item, dict):
            continue
        source_id = item.get("id")
        if source_id not in selected_id_set:
            continue
        for raw_path in item.get("paths", []):
            if isinstance(raw_path, str):
                specs.append((str(source_id), Path(raw_path)))
    if specs:
        return specs
    fallback = [
        ("active_docs", Path("docs/00-project")),
        ("active_docs", Path("docs/01-requirements")),
        ("accepted_adrs", Path("docs/02-architecture/decisions")),
        ("devin_wiki", Path(".devin/wiki.json")),
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
    return [item for item in fallback if item[0] in selected_id_set]


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
    resolved_root = root.resolve()
    git_paths = _git_source_paths(root=root, base=base)
    if git_paths is not None:
        return _filter_git_source_paths(root, resolved_root, git_paths, suffixes)
    return _fallback_source_paths(root, resolved_root, base, suffixes)


def _filter_git_source_paths(
    root: Path, resolved_root: Path, paths: list[Path], suffixes: set[str]
) -> list[Path]:
    return [
        rel_path
        for rel_path in paths
        if rel_path.suffix.lower() in suffixes
        and _safe_source_path(root / rel_path, resolved_root)
        and (root / rel_path).is_file()
    ]


def _fallback_source_paths(
    root: Path, resolved_root: Path, base: Path, suffixes: set[str]
) -> list[Path]:
    source_dir = root / base
    if not source_dir.exists() or source_dir.is_symlink():
        return []
    if not source_dir.is_dir():
        if source_dir.suffix.lower() in suffixes and _safe_source_path(
            source_dir, resolved_root
        ):
            return [base]
        return []
    candidates: list[Path] = []
    for current_root, dirnames, filenames in os.walk(source_dir):
        dirnames.sort()
        current_path = Path(current_root)
        rel_dir = current_path.relative_to(source_dir)
        for filename in sorted(filenames):
            if Path(filename).suffix.lower() not in suffixes:
                continue
            candidate = base / rel_dir / filename
            if _safe_source_path(root / candidate, resolved_root):
                candidates.append(candidate)
    return candidates


def _safe_source_path(path: Path, resolved_root: Path) -> bool:
    """Keep generated RAG sources inside the repository, without symlinks."""
    try:
        return not path.is_symlink() and path.resolve(strict=True).is_relative_to(
            resolved_root
        )
    except (OSError, RuntimeError):
        return False


def _git_source_paths(*, root: Path, base: Path) -> list[Path] | None:
    git_dir = root / ".git"
    if not git_dir.exists():
        return None
    try:
        result = subprocess.run(
            [
                "git",
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "--",
                base.as_posix(),
            ],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return [
        Path(line) for line in sorted(set(result.stdout.splitlines())) if line.strip()
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


def _tokenize_focus_query(query: str | None) -> tuple[str, ...]:
    if not query:
        return ()
    tokens = {
        token.lower()
        for token in re.findall(r"[A-Za-z0-9_./:-]+", query)
        if len(token) >= 3
    }
    return tuple(sorted(tokens))


def _workflow_focus_score(
    *,
    source_id: str,
    rel_path: str,
    focus_tokens: tuple[str, ...],
    content_scores: dict[str, int],
    priority_index: dict[str, int],
) -> tuple[int, int, str]:
    lowered_path = rel_path.lower()
    token_hits = sum(token in lowered_path for token in focus_tokens)
    direct_bonus = (
        1 if any(f"/{token}" in lowered_path for token in focus_tokens) else 0
    )
    source_priority = priority_index.get(source_id, len(priority_index))
    content_bonus = 3 * content_scores.get(rel_path, 0)
    return (-(token_hits + direct_bonus + content_bonus), source_priority, rel_path)


def _content_focus_scores(
    root: Path,
    entries: list[tuple[str, Path]],
    focus_tokens: tuple[str, ...],
    selected_ids: tuple[str, ...],
    focus_query: str | None,
) -> dict[str, int]:
    """Score eligible content by matched query terms before the source cap."""
    eligible = {path.as_posix() for _, path in entries}
    if not focus_tokens:
        return {}
    candidates = eligible
    if (root / ".git").exists():
        specs = tuple(
            dict.fromkeys(
                base.as_posix()
                for _, base in _load_source_specs(selected_ids=selected_ids)
            )
        )
        try:
            result = subprocess.run(
                [
                    "git",
                    "grep",
                    "--untracked",
                    "-i",
                    "-l",
                    "-F",
                    *(arg for token in focus_tokens for arg in ("-e", token)),
                    "--",
                    *specs,
                ],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode in {0, 1}:
                candidates = set(result.stdout.splitlines()) & eligible
        except OSError:
            pass
    scores: dict[str, int] = {}
    exact_query = (focus_query or "").strip().lower()
    for rel_path in candidates:
        try:
            content = (
                (root / rel_path).read_text(encoding="utf-8", errors="replace").lower()
            )
        except OSError:
            continue
        matched_terms = sum(token in content for token in focus_tokens)
        if matched_terms:
            scores[rel_path] = matched_terms + (
                len(focus_tokens) + 1 if exact_query in content else 0
            )
    return scores


def iter_rag_sources(
    root: Path,
    *,
    selected_ids: tuple[str, ...] = DEFAULT_SELECTED_SOURCE_IDS,
    workflow_focus_query: str | None = None,
    max_sources: int | None = None,
) -> list[Path]:
    """Return deterministic repository-relative RAG source paths."""
    exclusion_patterns = _load_exclusion_patterns()
    entries: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for source_id, base in _load_source_specs(selected_ids=selected_ids):
        for path in _candidate_source_paths(root=root, source_id=source_id, base=base):
            rel_path = path.as_posix()
            if not _should_include_source(
                rel_path=rel_path,
                seen=seen,
                exclusion_patterns=exclusion_patterns,
            ):
                continue
            seen.add(rel_path)
            entries.append((source_id, path))

    if not entries:
        return []

    if max_sources is None:
        return [path for _, path in entries]

    focus_tokens = _tokenize_focus_query(workflow_focus_query)
    priority_order = _load_source_priority_order()
    priority_index = {
        source_id: index for index, source_id in enumerate(priority_order)
    }
    if focus_tokens:
        content_scores = _content_focus_scores(
            root, entries, focus_tokens, selected_ids, workflow_focus_query
        )
        ranked_entries = sorted(
            entries,
            key=lambda item: _workflow_focus_score(
                source_id=item[0],
                rel_path=item[1].as_posix(),
                focus_tokens=focus_tokens,
                content_scores=content_scores,
                priority_index=priority_index,
            ),
        )
    else:
        ranked_entries = sorted(
            entries,
            key=lambda item: (
                priority_index.get(item[0], len(priority_index)),
                item[1].as_posix(),
            ),
        )
    return [path for _, path in ranked_entries[:max_sources]]


def iter_markdown_sources(root: Path) -> list[Path]:
    """Return only markdown RAG sources for backward-compatible callers."""
    return [
        path
        for path in iter_rag_sources(root)
        if path.suffix.lower() in MARKDOWN_SUFFIXES
    ]
