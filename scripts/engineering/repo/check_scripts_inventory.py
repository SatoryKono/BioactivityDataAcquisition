#!/usr/bin/env python3
"""Generate and validate scripts inventory metadata.

This tool inventories script entrypoints in:
- scripts/**
- src/tools/**

It classifies each script by discovered call-sites and can:
- update a committed manifest (`--update`)
- verify drift against a manifest (`--check`)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

try:
    from datetime import UTC
except ImportError:
    UTC = UTC
from pathlib import Path
from typing import Final

UTC = UTC

SCRIPT_EXTENSIONS: Final[tuple[str, ...]] = (
    ".py",
    ".sh",
    ".ps1",
    ".cmd",
    ".bat",
    ".mjs",
    ".sql",
)
SCRIPT_ROOTS: Final[tuple[str, ...]] = ("scripts", "src/tools")
SEARCH_ROOTS: Final[tuple[str, ...]] = (
    "AGENTS.md",
    ".pre-commit-config.yaml",
    ".codex/agents",
    ".codex/skills",
    ".github/workflows",
    "pyproject.toml",
    "Makefile",
    "makefile",
    "docs",
    "tests",
    "scripts",
    "src/tools",
)
SKIP_DIR_NAMES: Final[set[str]] = {
    ".cache",
    ".git",
    ".idea",
    ".venv",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    "__pycache__",
    "node_modules",
}
SKIP_PATH_PREFIXES: Final[tuple[str, ...]] = (
    "docs/02-architecture/generated/",
    "docs/99-archive/",
    "docs/exports/",
    "docs/fixes/",
    "docs/plans/",
    "docs/refactoring_plans/",
    "docs/reports/",
    "tests/fixtures/",
)
SKIP_FILE_EXTENSIONS: Final[set[str]] = {
    ".7z",
    ".avi",
    ".bmp",
    ".doc",
    ".docx",
    ".gif",
    ".gz",
    ".ico",
    ".jpeg",
    ".jpg",
    ".mp3",
    ".mp4",
    ".parquet",
    ".pdf",
    ".png",
    ".tar",
    ".tgz",
    ".wav",
    ".webm",
    ".webp",
    ".whl",
    ".xz",
    ".zip",
}
SCRIPT_PATH_TOKENS: Final[tuple[str, ...]] = ("scripts/", "src/tools/")
MODULE_REF_TOKENS: Final[tuple[str, ...]] = (
    "python -m scripts.",
    "python -m src.tools.",
    "uv run python -m scripts.",
    "uv run python -m src.tools.",
)
SCRIPT_PATH_CANDIDATE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:scripts|src/tools)/[A-Za-z0-9._/-]+\.(?:py|sh|ps1|cmd|bat|mjs|sql)"
)
BASENAME_REF_CANDIDATE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"[A-Za-z0-9._-]+\.(?:py|sh|ps1|cmd|bat|mjs|sql)"
)
MODULE_REF_CANDIDATE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:uv\s+run\s+)?(?:python(?:3(?:\.\d+)?)?|py)\s+-m\s+"
    r"((?:scripts|src\.tools)(?:\.[A-Za-z0-9_]+)+)"
)
SCRIPT_PATH_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "scripts/ops/launchers/codex/codex-exec.bat": ("scripts/codex-exec.bat",),
    "scripts/ops/launchers/codex/codex.bat": ("scripts/codex.bat",),
    "scripts/ops/runtime/wsl/start-wsl-proxy.bat": ("scripts/start-wsl-proxy.bat",),
    "scripts/codex-exec.bat": ("scripts/ops/launchers/codex/codex-exec.bat",),
    "scripts/codex.bat": ("scripts/ops/launchers/codex/codex.bat",),
    "scripts/start-wsl-proxy.bat": ("scripts/ops/runtime/wsl/start-wsl-proxy.bat",),
}
MODULE_COMMAND_SCRIPT_ALIASES: Final[dict[str, dict[str, str]]] = {
    "scripts.docs": {
        "check-links": "scripts/docs/checks/check_links.py",
    },
    "scripts.engineering.qa": {
        "check-c901": "scripts/engineering/qa/check_c901_baseline.py",
        "check-naming-pkg": (
            "scripts/engineering/qa/check_naming_package_consistency.py"
        ),
    },
    "scripts.engineering.qa.vcr": {
        "check-placement": "scripts/engineering/qa/vcr/check_root_vcr_cassettes.py",
        "check-naming": "scripts/engineering/qa/vcr/check_vcr_filename_policy.py",
        "check-metadata-age": "scripts/engineering/qa/vcr/check_vcr_metadata_age.py",
    },
    "scripts.engineering.repo": {
        "check-inventory": "scripts/engineering/repo/check_scripts_inventory.py",
        "check-catalog": "scripts/engineering/repo/check_scripts_catalog.py",
    },
}
MANIFEST_DEFAULT: Final[str] = "configs/quality/scripts_inventory_manifest.json"
DEPRECATION_REPORT_DEFAULT: Final[str] = (
    "reports/quality/scripts_deprecation_backlog.md"
)
LIFECYCLE_REGISTRY_DEFAULT: Final[str] = (
    "configs/quality/scripts_lifecycle_registry.json"
)
SCHEMA_VERSION: Final[str] = "1.0"
MAX_SEARCH_FILE_BYTES: Final[int] = 512 * 1024
STRONG_ACTIVE_GROUPS: Final[frozenset[str]] = frozenset(
    {"ci", "build", "skills", "agents"}
)
LEGACY_MANUAL_OPS_SCRIPTS: Final[frozenset[str]] = frozenset(
    {
        "scripts/ops/maintenance/github/close_superseded_prs.sh",
        "scripts/ops/maintenance/github/close_duplicate_prs_wave2.sh",
        "scripts/ops/maintenance/github/close_duplicate_prs_wave3.sh",
    }
)
LEGACY_ISSUE_SPECIFIC_OPS_SCRIPTS: Final[frozenset[str]] = frozenset(
    {
        "scripts/ops/maintenance/github/post_issue_rescope_comments.sh",
        "scripts/ops/maintenance/github/update_issue_rescope_bodies.sh",
    }
)
LEGACY_INTERNAL_AI_LAUNCHERS: Final[frozenset[str]] = frozenset(
    {
        "scripts/ai/code-reviewer.sh",
        "scripts/ai/data-engineer.sh",
        "scripts/ai/literature-researcher.sh",
    }
)
LEGACY_NAMED_SCRIPTS: Final[frozenset[str]] = frozenset(
    {
        "scripts/engineering/dev/dev_setup.sh",
        "scripts/engineering/diagnostics/_tmp_inspect_vcr.py",
    }
)
LEGACY_SRC_TOOLS_WRAPPERS: Final[frozenset[str]] = frozenset(
    {
        "src/tools/scripts/generate_contracts.py",
    }
)
DEPRECATED_LEGACY_PATHS: Final[frozenset[str]] = frozenset(
    {
        "scripts/engineering/qa/generate_reports.py",
    }
)
ACTIVE_EXPLICIT_SCRIPTS: Final[frozenset[str]] = frozenset(
    {
        "scripts/ci_check_docs_parity.sh",
        "scripts/ops/support/repo/cleanup_repository.py",
        "scripts/check_dq_dsl_parity.py",
        "scripts/engineering/ci/validate_control_plane_artifacts.py",
        "scripts/ops/data/__main__.py",
        "scripts/ai/codex/helper/check-env.ps1",
        "scripts/ai/codex/helper/check-env.sh",
        "scripts/ai/codex/helper/setup-env.sh",
        "scripts/ai/gemini/helper/check-env.ps1",
        "scripts/ai/gemini/helper/setup-env.sh",
        "scripts/ai/mistrall/helper/check-env.ps1",
        "scripts/ai/mistrall/helper/check-env.sh",
        "scripts/ai/mistrall/helper/setup-env.sh",
        "scripts/ai/mistrallvibe/helper/check-env.ps1",
        "scripts/ai/mistrallvibe/helper/check-env.sh",
    }
)
SUPPORTING_LIFECYCLE_DECISIONS: Final[frozenset[str]] = frozenset(
    {
        "compatibility_wrapper",
        "internal_compatibility_launcher",
        "windows_compatibility_wrapper",
        "shared_helper_module",
        "internal_helper_orphan",
        "legacy_manual_utility",
    }
)
NON_ACTIVE_STATUSES: Final[tuple[str, ...]] = (
    "unknown",
    "orphan",
    "temporary_diagnostic",
    "supporting",
    "legacy",
)


@dataclass(frozen=True)
class RefEvidence:
    """Reference evidence item for a script."""

    path: str
    line: int
    text: str
    source_group: str


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _iter_script_files_in_base(base: Path) -> list[Path]:
    scripts: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIR_NAMES]
        current_path = Path(dirpath)
        for filename in filenames:
            file_path = current_path / filename
            if not file_path.is_file():
                continue
            if (
                file_path.suffix not in SCRIPT_EXTENSIONS
                or file_path.name == "__init__.py"
            ):
                continue
            scripts.append(file_path)
    return scripts


def _iter_scripts(root: Path) -> list[Path]:
    scripts: list[Path] = []
    for rel_root in SCRIPT_ROOTS:
        base = root / rel_root
        if not base.exists():
            continue
        scripts.extend(_iter_script_files_in_base(base))
    return sorted(set(scripts))


def _is_skipped_rel_path(rel_path: str) -> bool:
    return any(
        rel_path == prefix.rstrip("/") or rel_path.startswith(prefix)
        for prefix in SKIP_PATH_PREFIXES
    )


def _should_include_search_file(root: Path, file_path: Path) -> bool:
    rel_path = file_path.relative_to(root).as_posix()
    if _is_skipped_rel_path(rel_path):
        return False
    if file_path.suffix.lower() in SKIP_FILE_EXTENSIONS:
        return False
    try:
        if file_path.stat().st_size > MAX_SEARCH_FILE_BYTES:
            return False
    except OSError:
        return False
    return True


def _iter_dir_search_files(root: Path, base: Path) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(base):
        current_path = Path(dirpath)
        rel_dir = current_path.relative_to(root).as_posix()
        if _is_skipped_rel_path(f"{rel_dir}/"):
            dirnames.clear()
            continue

        dirnames[:] = [name for name in dirnames if name not in SKIP_DIR_NAMES]
        for filename in filenames:
            file_path = current_path / filename
            if _should_include_search_file(root, file_path):
                files.append(file_path)
    return files


def _iter_search_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for rel in SEARCH_ROOTS:
        path = root / rel
        if not path.exists():
            continue
        if path.is_file():
            if _should_include_search_file(root, path):
                files.append(path)
            continue
        files.extend(_iter_dir_search_files(root, path))
    return sorted(files)


def _source_group(rel_path: str) -> str:
    if rel_path.startswith(".github/workflows/"):
        return "ci"
    if rel_path == ".pre-commit-config.yaml":
        return "ci"
    if rel_path.startswith(".codex/skills/"):
        return "skills"
    if rel_path.startswith(".codex/agents/"):
        return "agents"
    if rel_path in {"Makefile", "makefile", "pyproject.toml"}:
        return "build"
    if rel_path.startswith("tests/"):
        return "tests"
    if rel_path.startswith("docs/"):
        return "docs"
    if rel_path == "AGENTS.md":
        return "agents"
    if rel_path.startswith("scripts/") or rel_path.startswith("src/tools/"):
        return "scripts"
    return "other"


def _discover_refs(root: Path, scripts: list[Path]) -> dict[str, list[RefEvidence]]:
    rel_scripts = [path.relative_to(root).as_posix() for path in scripts]
    script_set = set(rel_scripts)
    basename_map = _build_basename_map(rel_scripts)
    refs: dict[str, list[RefEvidence]] = {item: [] for item in rel_scripts}
    for script_rel in rel_scripts:
        for alias in SCRIPT_PATH_ALIASES.get(script_rel, ()):
            refs.setdefault(alias, [])
    search_files = _iter_search_files(root)

    for file_path in search_files:
        discovered = _discover_refs_in_file(
            root=root,
            file_path=file_path,
            script_set=script_set,
            basename_map=basename_map,
        )
        if not discovered:
            continue
        for script_rel, evidence in discovered:
            refs[script_rel].append(evidence)
            for alias in SCRIPT_PATH_ALIASES.get(script_rel, ()):
                refs.setdefault(alias, []).append(evidence)
    return refs


def _line_has_reference_candidate(
    normalized_line: str,
    basename_map: dict[str, tuple[str, ...]],
) -> bool:
    return (
        any(token in normalized_line for token in SCRIPT_PATH_TOKENS)
        or any(token in normalized_line for token in MODULE_REF_TOKENS)
        or _line_has_basename_script_candidate(normalized_line, basename_map)
    )


def _make_ref_evidence(
    *,
    rel: str,
    line_no: int,
    raw_line: str,
    source_group: str,
) -> RefEvidence:
    return RefEvidence(
        path=rel,
        line=line_no,
        text=raw_line.strip()[:200],
        source_group=source_group,
    )


def _discover_script_path_refs(
    *,
    rel: str,
    line_no: int,
    raw_line: str,
    normalized_line: str,
    source_group: str,
    script_set: set[str],
) -> list[tuple[str, RefEvidence]]:
    discovered: list[tuple[str, RefEvidence]] = []
    evidence = _make_ref_evidence(
        rel=rel, line_no=line_no, raw_line=raw_line, source_group=source_group
    )
    for script_rel in set(SCRIPT_PATH_CANDIDATE_PATTERN.findall(normalized_line)):
        candidate_paths = (script_rel, *SCRIPT_PATH_ALIASES.get(script_rel, ()))
        for candidate_path in candidate_paths:
            if candidate_path not in script_set or rel == candidate_path:
                continue
            discovered.append((candidate_path, evidence))
    return discovered


def _discover_module_refs(
    *,
    rel: str,
    line_no: int,
    raw_line: str,
    normalized_line: str,
    source_group: str,
    script_set: set[str],
) -> list[tuple[str, RefEvidence]]:
    evidence = _make_ref_evidence(
        rel=rel, line_no=line_no, raw_line=raw_line, source_group=source_group
    )
    discovered: list[tuple[str, RefEvidence]] = []
    for module_name in set(MODULE_REF_CANDIDATE_PATTERN.findall(normalized_line)):
        candidate_path = f"{module_name.replace('.', '/')}/__main__.py"
        if candidate_path not in script_set or rel == candidate_path:
            continue
        discovered.append((candidate_path, evidence))
    return discovered


def _discover_basename_refs(
    *,
    rel: str,
    line_no: int,
    raw_line: str,
    normalized_line: str,
    source_group: str,
    script_set: set[str],
    basename_map: dict[str, tuple[str, ...]],
) -> list[tuple[str, RefEvidence]]:
    discovered: list[tuple[str, RefEvidence]] = []
    evidence = _make_ref_evidence(
        rel=rel, line_no=line_no, raw_line=raw_line, source_group=source_group
    )
    basenames = {
        match.group(0)
        for match in BASENAME_REF_CANDIDATE_PATTERN.finditer(normalized_line)
    }
    for basename in basenames:
        for candidate_path in _resolve_basename_candidates(
            rel=rel, basename=basename, basename_map=basename_map
        ):
            if candidate_path not in script_set or rel == candidate_path:
                continue
            discovered.append((candidate_path, evidence))
    return discovered


def _build_basename_map(script_paths: list[str]) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for script_path in script_paths:
        grouped[Path(script_path).name].append(script_path)
    return {basename: tuple(sorted(paths)) for basename, paths in grouped.items()}


def _discover_refs_in_file(
    root: Path,
    file_path: Path,
    script_set: set[str],
    basename_map: dict[str, tuple[str, ...]],
) -> list[tuple[str, RefEvidence]]:
    rel = file_path.relative_to(root).as_posix()
    try:
        text = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    normalized_text = text.replace("\\", "/")
    has_script_path_refs = any(token in normalized_text for token in SCRIPT_PATH_TOKENS)
    has_module_refs = any(token in normalized_text for token in MODULE_REF_TOKENS)
    has_basename_refs = _line_has_basename_script_candidate(
        normalized_text, basename_map
    )
    if not has_script_path_refs and not has_module_refs and not has_basename_refs:
        return []

    source_group = _source_group(rel)
    discovered = _discover_module_command_refs_in_file(
        rel=rel,
        text=text,
        normalized_text=normalized_text,
        source_group=source_group,
        script_set=script_set,
    )
    original_lines = text.splitlines()
    normalized_lines = normalized_text.splitlines()
    for line_no, (raw_line, normalized_line) in enumerate(
        zip(original_lines, normalized_lines, strict=True),
        start=1,
    ):
        if not _line_has_reference_candidate(normalized_line, basename_map):
            continue
        discovered.extend(
            _discover_refs_from_line(
                rel=rel,
                line_no=line_no,
                raw_line=raw_line,
                normalized_line=normalized_line,
                source_group=source_group,
                script_set=script_set,
                basename_map=basename_map,
            )
        )
    return discovered


def _discover_module_command_refs_in_file(
    *,
    rel: str,
    text: str,
    normalized_text: str,
    source_group: str,
    script_set: set[str],
) -> list[tuple[str, RefEvidence]]:
    """Resolve dispatcher-style ``python -m scripts.* <command>`` references."""
    discovered: list[tuple[str, RefEvidence]] = []
    for module_name, command_map in MODULE_COMMAND_SCRIPT_ALIASES.items():
        if module_name not in normalized_text:
            continue
        for command_name, script_rel in command_map.items():
            if script_rel not in script_set or rel == script_rel:
                continue
            if not _has_module_command_reference(
                normalized_text=normalized_text,
                module_name=module_name,
                command_name=command_name,
            ):
                continue
            line_no, raw_line = _get_first_module_command_line(
                text=text,
                module_name=module_name,
                command_name=command_name,
            )
            discovered.append(
                (
                    script_rel,
                    _make_ref_evidence(
                        rel=rel,
                        line_no=line_no,
                        raw_line=raw_line,
                        source_group=source_group,
                    ),
                )
            )
    return discovered


def _has_module_command_reference(
    *,
    normalized_text: str,
    module_name: str,
    command_name: str,
) -> bool:
    if module_name not in normalized_text:
        return False
    command_pattern = rf"(?<![\w-]){re.escape(command_name)}(?![\w-])"
    return re.search(command_pattern, normalized_text) is not None


def _get_first_module_command_line(
    *,
    text: str,
    module_name: str,
    command_name: str,
) -> tuple[int, str]:
    module_line: tuple[int, str] | None = None
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        normalized_line = raw_line.replace("\\", "/")
        if module_line is None and module_name in normalized_line:
            module_line = (line_no, raw_line)
        if command_name in normalized_line:
            return line_no, raw_line
    return module_line or (1, "")


def _line_has_basename_script_candidate(
    normalized_text: str, basename_map: dict[str, tuple[str, ...]]
) -> bool:
    for match in BASENAME_REF_CANDIDATE_PATTERN.finditer(normalized_text):
        if match.group(0) in basename_map:
            return True
    return False


def _discover_refs_from_line(
    *,
    rel: str,
    line_no: int,
    raw_line: str,
    normalized_line: str,
    source_group: str,
    script_set: set[str],
    basename_map: dict[str, tuple[str, ...]],
) -> list[tuple[str, RefEvidence]]:
    discovered: list[tuple[str, RefEvidence]] = []
    discovered.extend(
        _discover_script_path_refs(
            rel=rel,
            line_no=line_no,
            raw_line=raw_line,
            normalized_line=normalized_line,
            source_group=source_group,
            script_set=script_set,
        )
    )
    discovered.extend(
        _discover_module_refs(
            rel=rel,
            line_no=line_no,
            raw_line=raw_line,
            normalized_line=normalized_line,
            source_group=source_group,
            script_set=script_set,
        )
    )
    discovered.extend(
        _discover_basename_refs(
            rel=rel,
            line_no=line_no,
            raw_line=raw_line,
            normalized_line=normalized_line,
            source_group=source_group,
            script_set=script_set,
            basename_map=basename_map,
        )
    )
    return discovered


def _resolve_basename_candidates(
    *,
    rel: str,
    basename: str,
    basename_map: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    candidates = basename_map.get(basename, ())
    if len(candidates) <= 1:
        return candidates

    rel_parent = Path(rel).parent.as_posix()
    same_parent = tuple(
        candidate
        for candidate in candidates
        if Path(candidate).parent.as_posix() == rel_parent
    )
    if same_parent:
        return same_parent
    return ()


def _dedupe_refs(refs: list[RefEvidence]) -> list[RefEvidence]:
    seen: set[tuple[str, int, str]] = set()
    result: list[RefEvidence] = []
    for item in refs:
        key = (item.path, item.line, item.text)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return sorted(result, key=lambda item: (item.path, item.line, item.text))


def _status_from_lifecycle_decision(decision: str | None) -> str | None:
    if decision == "active":
        return "active"
    if decision == "temporary_diagnostic":
        return "temporary_diagnostic"
    if decision in SUPPORTING_LIFECYCLE_DECISIONS:
        return "supporting"
    return None


def _load_lifecycle_decision_map(root: Path) -> dict[str, str]:
    registry_path = root / LIFECYCLE_REGISTRY_DEFAULT
    if not registry_path.exists():
        return {}
    try:
        registry = _load_json(registry_path)
    except ValueError:
        return {}

    entries_raw = registry.get("entries")
    if not isinstance(entries_raw, dict):
        return {}

    decisions: dict[str, str] = {}
    for path_value, meta in entries_raw.items():
        if not isinstance(path_value, str) or not isinstance(meta, dict):
            continue
        decision = meta.get("decision")
        if isinstance(decision, str):
            decisions[path_value] = decision
    return decisions


def _status_for(
    script_rel: str,
    refs: list[RefEvidence],
    lifecycle_decisions: dict[str, str],
) -> str:
    groups = {item.source_group for item in refs}
    legacy_status_sets = (
        LEGACY_MANUAL_OPS_SCRIPTS,
        LEGACY_ISSUE_SPECIFIC_OPS_SCRIPTS,
        LEGACY_INTERNAL_AI_LAUNCHERS,
        LEGACY_NAMED_SCRIPTS,
        LEGACY_SRC_TOOLS_WRAPPERS,
        DEPRECATED_LEGACY_PATHS,
    )
    if any(script_rel in candidates for candidates in legacy_status_sets):
        return "active" if groups & STRONG_ACTIVE_GROUPS else "legacy"
    if script_rel in ACTIVE_EXPLICIT_SCRIPTS:
        return "active"

    lifecycle_status = _status_from_lifecycle_decision(
        lifecycle_decisions.get(script_rel)
    )

    if not refs:
        if lifecycle_status is not None:
            return lifecycle_status
        return (
            "legacy" if ("_tmp" in script_rel or "debug_" in script_rel) else "orphan"
        )

    if groups & {"ci", "build", "skills", "tests", "scripts", "agents"}:
        return "active"
    if groups == {"docs"}:
        if lifecycle_status is not None:
            return lifecycle_status
        return "unknown"
    if lifecycle_status is not None:
        return lifecycle_status
    return "unknown"


def _agent_usage(refs: list[RefEvidence]) -> list[str]:
    usages: set[str] = set()
    for item in refs:
        if item.path.startswith(".codex/skills/"):
            parts = item.path.split("/")
            if len(parts) >= 4:
                usages.add(parts[2])
            continue
        if item.path.startswith(".codex/agents/"):
            agent_name = Path(item.path).stem
            if agent_name:
                usages.add(agent_name)
    return sorted(usages)


def _build_inventory(root: Path) -> dict[str, object]:
    scripts = _iter_scripts(root)
    refs_map = _discover_refs(root, scripts)
    lifecycle_decisions = _load_lifecycle_decision_map(root)
    rows: list[dict[str, object]] = []
    status_counts: Counter[str] = Counter()
    group_counts: Counter[str] = Counter()

    for script in scripts:
        script_rel = script.relative_to(root).as_posix()
        refs = _dedupe_refs(refs_map[script_rel])
        status = _status_for(script_rel, refs, lifecycle_decisions)
        status_counts[status] += 1
        for group in {item.source_group for item in refs}:
            group_counts[group] += 1

        rows.append(
            {
                "path": script_rel,
                "type": script.suffix.lstrip("."),
                "status": status,
                "agent_usage": _agent_usage(refs),
                "reference_count": len(refs),
                "references": [
                    {
                        "path": item.path,
                        "line": item.line,
                        "source_group": item.source_group,
                        "text": item.text,
                    }
                    for item in refs[:8]
                ],
            }
        )

    rows.sort(key=lambda item: str(item["path"]))
    summary = {
        "total_scripts": len(rows),
        "status_counts": dict(sorted(status_counts.items())),
        "reference_group_coverage": dict(sorted(group_counts.items())),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": summary,
        "scripts": rows,
    }


def _stable_manifest(data: dict[str, object]) -> dict[str, object]:
    normalized = dict(data)
    normalized.pop("generated_at", None)
    return normalized


def _write_manifest(path: Path, payload: dict[str, object]) -> None:
    _write_text_atomic(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )


def _write_text_atomic(path: Path, content: str) -> None:
    """Write text atomically to avoid readers observing partial files."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.parent / (f".{path.name}.tmp.{os.getpid()}.{time.time_ns()}")
    try:
        with temp_path.open("w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _check(manifest_path: Path, actual: dict[str, object]) -> int:
    if not manifest_path.exists():
        print(f"[FAIL] Manifest not found: {manifest_path}")
        print("Run with --update to create baseline manifest.")
        return 1

    expected = json.loads(manifest_path.read_text(encoding="utf-8"))
    if _stable_manifest(expected) == _stable_manifest(actual):
        print(f"[OK] Scripts inventory is in sync: {manifest_path}")
        return 0

    print(f"[FAIL] Scripts inventory drift detected: {manifest_path}")
    print("Run with --update to refresh manifest.")
    return 1


def _write_deprecation_report(path: Path, payload: dict[str, object]) -> None:
    scripts = payload["scripts"]
    assert isinstance(scripts, list)

    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for item in scripts:
        assert isinstance(item, dict)
        status = str(item.get("status", "unknown"))
        if status in NON_ACTIVE_STATUSES:
            grouped[status].append(item)

    lines = [
        "# Scripts Deprecation Backlog",
        "",
        "Auto-generated from `scripts/check_scripts_inventory.py`.",
        "",
    ]

    for status in NON_ACTIVE_STATUSES:
        entries = sorted(grouped.get(status, []), key=lambda row: str(row["path"]))
        lines.append(f"## {status} ({len(entries)})")
        lines.append("")
        lines.append("| Script Path | Type | Reference Count | Suggested Next Step |")
        lines.append("|---|---|---:|---|")
        for item in entries:
            path_value = str(item["path"])
            type_value = str(item["type"])
            ref_count_raw = item.get("reference_count", 0)
            if isinstance(ref_count_raw, (int, float, str)):
                ref_count = int(ref_count_raw)
            else:
                ref_count = 0
            if status == "unknown":
                next_step = (
                    "Validate runtime usage; promote to active or mark deprecated."
                )
            elif status == "orphan":
                next_step = (
                    "Plan staged removal or add explicit compatibility call-site."
                )
            elif status == "temporary_diagnostic":
                next_step = (
                    "Retain only while the bounded troubleshooting flow remains live."
                )
            elif status == "supporting":
                next_step = (
                    "Retain as a supporting surface/helper until a canonical replacement exists."
                )
            else:
                next_step = "Archive/remove after freeze window if no active consumers."
            lines.append(
                f"| `{path_value}` | `{type_value}` | {ref_count} | {next_step} |"
            )
        lines.append("")

    _write_text_atomic(path, "\n".join(lines).rstrip() + "\n")


def _load_json(path: Path) -> dict[str, object]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return raw


def _check_lifecycle_registry(
    root: Path,
    payload: dict[str, object],
    registry_rel_path: str,
    forbid_evaluate_active: bool,
) -> int:
    registry_path = root / registry_rel_path
    if not registry_path.exists():
        print(f"[FAIL] Lifecycle registry not found: {registry_path}")
        return 1

    try:
        registry = _load_json(registry_path)
    except ValueError as exc:
        print(f"[FAIL] {exc}")
        return 1

    entries_raw = _extract_registry_entries(registry, registry_path)
    if entries_raw is None:
        return 1
    script_map = _build_script_map(payload)
    target_statuses = set(NON_ACTIVE_STATUSES)
    missing, invalid, forbidden = _validate_target_registry_entries(
        script_map=script_map,
        entries_raw=entries_raw,
        target_statuses=target_statuses,
        forbid_evaluate_active=forbid_evaluate_active,
    )
    stale, stale_invalid = _validate_stale_registry_entries(
        script_map=script_map,
        entries_raw=entries_raw,
        target_statuses=target_statuses,
    )
    invalid.extend(stale_invalid)

    if missing or stale or invalid or forbidden:
        _print_lifecycle_validation_failures(
            registry_path=registry_path,
            missing=missing,
            stale=stale,
            invalid=invalid,
            forbidden=forbidden,
        )
        return 1

    print(
        f"[OK] Lifecycle registry covers non-active scripts: {registry_path}"
    )
    return 0


def _extract_registry_entries(
    registry: dict[str, object], registry_path: Path
) -> dict[str, object] | None:
    entries_raw = registry.get("entries")
    if isinstance(entries_raw, dict):
        return entries_raw
    print(
        f"[FAIL] Lifecycle registry must contain object field 'entries': {registry_path}"
    )
    return None


def _build_script_map(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    script_rows = payload["scripts"]
    assert isinstance(script_rows, list)
    return {str(item["path"]): item for item in script_rows if isinstance(item, dict)}


def _validate_target_registry_entries(
    *,
    script_map: dict[str, dict[str, object]],
    entries_raw: dict[str, object],
    target_statuses: set[str],
    forbid_evaluate_active: bool,
) -> tuple[list[str], list[str], list[str]]:
    missing: list[str] = []
    invalid: list[str] = []
    forbidden: list[str] = []
    required = {"owner", "decision", "review_by", "next_step"}

    for path, row in script_map.items():
        status = str(row.get("status", "unknown"))
        if status not in target_statuses:
            continue
        entry = entries_raw.get(path)
        if not isinstance(entry, dict):
            missing.append(path)
            continue
        absent = sorted(required - set(entry.keys()))
        if absent:
            invalid.append(f"{path}: missing fields {absent}")
        if forbid_evaluate_active and str(entry.get("decision")) == "evaluate_active":
            forbidden.append(path)

    return missing, invalid, forbidden


def _validate_stale_registry_entries(
    *,
    script_map: dict[str, dict[str, object]],
    entries_raw: dict[str, object],
    target_statuses: set[str],
) -> tuple[list[str], list[str]]:
    stale: list[str] = []
    invalid: list[str] = []

    for path, entry_value in entries_raw.items():
        if not isinstance(entry_value, dict):
            invalid.append(f"{path}: entry must be object")
            continue
        row_value = script_map.get(path)
        if row_value is None:
            stale.append(f"{path}: script not found in current inventory")
            continue
        status = str(row_value.get("status", "unknown"))
        if status not in target_statuses:
            stale.append(f"{path}: status changed to {status}")

    return stale, invalid


def _print_lifecycle_validation_failures(
    *,
    registry_path: Path,
    missing: list[str],
    stale: list[str],
    invalid: list[str],
    forbidden: list[str],
) -> None:
    print(f"[FAIL] Lifecycle registry validation failed: {registry_path}")
    if missing:
        print("  Missing entries:")
        for item in missing:
            print(f"    - {item}")
    if forbidden:
        print("  Forbidden decision values (evaluate_active):")
        for item in forbidden:
            print(f"    - {item}")
    if invalid:
        print("  Invalid entries:")
        for item in invalid:
            print(f"    - {item}")
    if stale:
        print("  Stale entries:")
        for item in stale:
            print(f"    - {item}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scripts inventory drift checker")
    parser.add_argument(
        "--manifest",
        default=MANIFEST_DEFAULT,
        help="Path to inventory manifest JSON",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print generated inventory JSON to stdout",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Write/update manifest file",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate current inventory against manifest file",
    )
    parser.add_argument(
        "--deprecation-report",
        default="",
        help=(
            "Optional path to write markdown backlog for non-active scripts. "
            f"Use default path with --deprecation-report={DEPRECATION_REPORT_DEFAULT}"
        ),
    )
    parser.add_argument(
        "--lifecycle-registry",
        default=LIFECYCLE_REGISTRY_DEFAULT,
        help="Path to lifecycle registry JSON for non-active scripts",
    )
    parser.add_argument(
        "--check-lifecycle",
        action="store_true",
        help="Validate lifecycle registry coverage for non-active scripts",
    )
    parser.add_argument(
        "--forbid-evaluate-active",
        action="store_true",
        help="Fail lifecycle validation if any entry has decision=evaluate_active",
    )
    return parser.parse_args(argv)


def _can_fast_path_json(args: argparse.Namespace) -> bool:
    """Return True when stdout JSON can skip full reference discovery."""
    return (
        args.json
        and not args.update
        and not args.check
        and not args.check_lifecycle
        and not str(args.deprecation_report).strip()
    )


def _build_fast_stdout_payload(root: Path) -> dict[str, object]:
    """Build a lightweight stdout payload without repository-wide reference scans."""
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "total_scripts": len(_iter_scripts(root)),
            "status_counts": {},
            "reference_group_coverage": {},
        },
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = _project_root()
    if _can_fast_path_json(args):
        _write_ascii_json_stdout(_build_fast_stdout_payload(root))
        return 0

    manifest_path = root / args.manifest
    payload = _build_inventory(root)

    if args.update:
        _write_manifest(manifest_path, payload)
        print(f"[OK] Updated scripts inventory manifest: {manifest_path}")

    check_result = _run_requested_checks(
        root=root, args=args, payload=payload, manifest_path=manifest_path
    )
    if check_result != 0:
        return check_result

    report_path_text = str(args.deprecation_report).strip()
    if report_path_text:
        report_path = root / report_path_text
        _write_deprecation_report(report_path, payload)
        print(f"[OK] Updated scripts deprecation report: {report_path}")

    _print_payload(args=args, payload=payload)

    return 0


def _run_requested_checks(
    *,
    root: Path,
    args: argparse.Namespace,
    payload: dict[str, object],
    manifest_path: Path,
) -> int:
    if args.check:
        result = _check(manifest_path, payload)
        if result != 0:
            return result

    if args.check_lifecycle:
        lifecycle_result = _check_lifecycle_registry(
            root=root,
            payload=payload,
            registry_rel_path=str(args.lifecycle_registry),
            forbid_evaluate_active=bool(args.forbid_evaluate_active),
        )
        if lifecycle_result != 0:
            return lifecycle_result
    return 0


def _coerce_int(value: object, *, default: int = 0) -> int:
    if isinstance(value, (int, float, str)):
        return int(value)
    return default


def _payload_status_counts(payload: dict[str, object]) -> tuple[int, dict[str, object]]:
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("Inventory payload must contain object field 'summary'")
    total_scripts = _coerce_int(summary.get("total_scripts", 0))
    status_counts_raw = summary.get("status_counts", {})
    status_counts = status_counts_raw if isinstance(status_counts_raw, dict) else {}
    return total_scripts, status_counts


def _write_ascii_json_stdout(payload: dict[str, object]) -> None:
    """Write ASCII-only JSON bytes regardless of console codepage settings."""
    rendered = (
        json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
        )
        + "\n"
    )
    stdout_buffer = getattr(sys.stdout, "buffer", None)
    if stdout_buffer is not None:
        stdout_buffer.write(rendered.encode("ascii"))
        stdout_buffer.flush()
        return
    sys.stdout.write(rendered)


def _stdout_payload(payload: dict[str, object]) -> dict[str, object]:
    """Return a compact JSON payload suitable for console/stdout transport.

    The full inventory is still used for manifest updates and drift checks.
    For `--json` stdout we intentionally emit only summary-level data, which is
    sufficient for machine checks in this repository and avoids large captured
    subprocess payloads stalling on Windows codepage-constrained pipes.
    """
    return {
        "schema_version": payload.get("schema_version"),
        "generated_at": payload.get("generated_at"),
        "summary": payload.get("summary", {}),
    }


def _print_payload(*, args: argparse.Namespace, payload: dict[str, object]) -> None:
    if args.json:
        _write_ascii_json_stdout(_stdout_payload(payload))
        return

    total_scripts, status_counts = _payload_status_counts(payload)
    print(
        "[INFO] scripts={total} active={active} unknown={unknown} orphan={orphan} legacy={legacy}".format(
            total=total_scripts,
            active=status_counts.get("active", 0),
            unknown=status_counts.get("unknown", 0),
            orphan=status_counts.get("orphan", 0),
            legacy=status_counts.get("legacy", 0),
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
