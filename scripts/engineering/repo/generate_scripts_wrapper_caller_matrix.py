#!/usr/bin/env python3
"""Generate the tracked scripts wrapper caller matrix report."""

from __future__ import annotations

import argparse
import difflib
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

SEARCH_ROOTS: Final[tuple[str, ...]] = (
    "AGENTS.md",
    ".pre-commit-config.yaml",
    ".codex/agents",
    ".codex/skills",
    ".github/workflows",
    "pyproject.toml",
    "Makefile",
    "makefile",
    "configs",
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
MAX_SEARCH_FILE_BYTES: Final[int] = 512 * 1024
DEFAULT_OUTPUT: Final[str] = (
    "docs/plans/scripts-cli-wrapper-caller-matrix-2026-04-28.md"
)
SELF_GENERATOR_REL: Final[str] = (
    "scripts/engineering/repo/generate_scripts_wrapper_caller_matrix.py"
)
COMPATIBILITY_WRAPPER_ROLE: Final[str] = "compatibility wrapper"
BOOTSTRAP_TRANSPORT_ROLE: Final[str] = "local bootstrap transport adapter"
WINDOWS_TRANSPORT_ROLE: Final[str] = "Windows WSL transport adapter"
BOOTSTRAP_HELPER_ROLE: Final[str] = "runtime bootstrap helper"


@dataclass(frozen=True)
class Candidate:
    path: str
    current_role: str
    allow_basename_match: bool = True


CANDIDATES: Final[tuple[Candidate, ...]] = (
    Candidate("scripts/docs/build_docs_site.sh", "shell transport adapter"),
    Candidate(
        "scripts/engineering/repo/cleanup_branch_candidates.sh",
        COMPATIBILITY_WRAPPER_ROLE,
    ),
    Candidate("scripts/ops/launchers/codex/codex.sh", BOOTSTRAP_TRANSPORT_ROLE),
    Candidate(
        "scripts/ops/launchers/codex/codex-exec.sh",
        BOOTSTRAP_TRANSPORT_ROLE,
    ),
    Candidate("scripts/ops/launchers/codex/codex-exec.bat", WINDOWS_TRANSPORT_ROLE),
    Candidate("scripts/ops/launchers/codex/setup_plugins.sh", BOOTSTRAP_HELPER_ROLE),
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


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
    return sorted(set(files))


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
    if rel_path.startswith("configs/"):
        return "config"
    if rel_path.startswith("tests/"):
        return "tests"
    if rel_path.startswith("docs/"):
        return "docs"
    if rel_path == "AGENTS.md":
        return "agents"
    if rel_path.startswith("scripts/") or rel_path.startswith("src/tools/"):
        return "scripts"
    return "other"


def _basename_patterns() -> dict[str, re.Pattern[str]]:
    return {
        candidate.path: re.compile(
            rf"(?<![A-Za-z0-9_.-]){re.escape(Path(candidate.path).name)}(?![A-Za-z0-9_.-])"
        )
        for candidate in CANDIDATES
    }


def _read_normalized_search_text(file_path: Path) -> str | None:
    """Read one search file and normalize path separators."""
    try:
        return file_path.read_text(encoding="utf-8").replace("\\", "/")
    except (OSError, UnicodeDecodeError):
        return None


def _mentions_any_candidate(
    normalized_text: str,
    basename_patterns: dict[str, re.Pattern[str]],
) -> bool:
    """Return whether one file references any tracked wrapper candidate."""
    return any(
        candidate.path in normalized_text
        or (
            candidate.allow_basename_match
            and basename_patterns[candidate.path].search(normalized_text)
        )
        for candidate in CANDIDATES
    )


def _collect_callers_for_file(
    *,
    callers: dict[str, set[tuple[str, str]]],
    rel: str,
    normalized_text: str,
    basename_patterns: dict[str, re.Pattern[str]],
) -> None:
    """Record all wrapper references found in one normalized file body."""
    source_group = _source_group(rel)
    for candidate in CANDIDATES:
        if rel == candidate.path:
            continue
        if candidate.path in normalized_text or (
            candidate.allow_basename_match
            and basename_patterns[candidate.path].search(normalized_text)
        ):
            callers[candidate.path].add((source_group, rel))


def _discover_callers(root: Path) -> dict[str, set[tuple[str, str]]]:
    callers = {candidate.path: set() for candidate in CANDIDATES}
    basename_patterns = _basename_patterns()

    for file_path in _iter_search_files(root):
        rel = file_path.relative_to(root).as_posix()
        if rel in {DEFAULT_OUTPUT, SELF_GENERATOR_REL}:
            continue
        normalized_text = _read_normalized_search_text(file_path)
        if normalized_text is None:
            continue

        if not _mentions_any_candidate(normalized_text, basename_patterns):
            continue

        _collect_callers_for_file(
            callers=callers,
            rel=rel,
            normalized_text=normalized_text,
            basename_patterns=basename_patterns,
        )

    return callers


def _format_callers(items: set[tuple[str, str]]) -> str:
    if not items:
        return "none"
    ordered = sorted(items, key=lambda item: (item[0], item[1]))
    return ", ".join(path for _group, path in ordered)


def _is_governance_evidence_path(rel_path: str) -> bool:
    if rel_path.startswith("configs/quality/"):
        return True
    if rel_path.startswith("docs/plans/"):
        return True
    if (
        rel_path
        == "tests/unit/scripts/repo/test_generate_scripts_wrapper_caller_matrix.py"
    ):
        return True
    if rel_path in {
        "tests/architecture/test_codex_launcher_bootstrap.py",
        "tests/architecture/test_ops_ai_setup_scripts.py",
        "tests/architecture/test_dev_setup_copilot_codex_mcp_consolidation.py",
        "tests/architecture/test_diagram_bundle_generator_contracts.py",
        "tests/architecture/test_docs_compat_shim_governance.py",
        "tests/architecture/test_check_doc_links_guardrails.py",
        "tests/architecture/test_docs_kpi_workflow.py",
    }:
        return True
    return False


def _render_report(root: Path) -> str:
    callers = _discover_callers(root)
    zero_operational_candidates: list[str] = []
    governance_only_candidates: list[str] = []
    lines = [
        "# Scripts CLI Wrapper Caller Matrix",
        "",
        "> Generated by `python -m scripts.engineering.repo sync-wrapper-caller-matrix`.",
        "> Do not edit manually. Delete wrappers only when this report shows zero repo callers.",
        "",
        "This report tracks compatibility-wrapper retention for the `scripts/*` CLI",
        "refactor wave and supports RF-008.",
        "",
        "## Scope",
        "",
        "Candidate wrappers reviewed:",
        "",
        "| Path | Current role | Operational callers | Governance/evidence callers | Deletion status |",
        "| --- | --- | --- | --- | --- |",
    ]

    for candidate in CANDIDATES:
        observed = callers[candidate.path]
        governance_only = {
            item for item in observed if _is_governance_evidence_path(item[1])
        }
        operational = observed - governance_only
        if not observed:
            deletion_status = "ready-to-delete"
            zero_operational_candidates.append(candidate.path)
        elif not operational:
            deletion_status = "governance-only"
            governance_only_candidates.append(candidate.path)
        else:
            deletion_status = "retain"
        lines.append(
            f"| `{candidate.path}` | {candidate.current_role} | "
            f"{_format_callers(operational)} | "
            f"{_format_callers(governance_only)} | {deletion_status} |"
        )

    lines.extend(
        (
            "",
            "## Notes",
            "",
            "- The current safe wave is internal dispatch consolidation, not blanket file deletion.",
            "- `scripts/ops/launchers/codex/codex.sh` and "
            "`scripts/ops/launchers/codex/codex-exec.sh` are retained "
            "bootstrap transport adapters, not deletion-first thin wrappers.",
            "- `scripts/ops/launchers/codex/setup_plugins.sh` is retained as a "
            "bootstrap helper because it carries runtime-selection and "
            "`--pytest-only` semantics beyond simple delegation.",
            "- `governance-only` means runtime callers are gone and only "
            "inventory, plan, or governance-test references still mention the wrapper.",
        )
    )
    if zero_operational_candidates:
        joined = ", ".join(f"`{item}`" for item in zero_operational_candidates)
        lines.append(f"- Zero-caller candidates in this snapshot: {joined}.")
    else:
        lines.append(
            "- No zero-caller wrapper candidates were found in this snapshot, so no deletion batch was applied."
        )
    if governance_only_candidates:
        joined = ", ".join(f"`{item}`" for item in governance_only_candidates)
        lines.append(
            f"- Governance-only wrapper candidates in this snapshot: {joined}."
        )
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the scripts wrapper caller matrix report."
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Output path relative to repo root (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write the generated report to --output instead of stdout.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the committed report differs from the generated output.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = _project_root()
    report = _render_report(root)
    output_path = root / args.output

    if args.check:
        if not output_path.exists():
            print(f"Missing caller matrix report: {args.output}", file=sys.stderr)
            return 1
        existing = output_path.read_text(encoding="utf-8")
        if existing != report:
            diff = "".join(
                difflib.unified_diff(
                    existing.splitlines(keepends=True),
                    report.splitlines(keepends=True),
                    fromfile=f"committed:{args.output}",
                    tofile=f"generated:{args.output}",
                )
            )
            print(diff, file=sys.stderr, end="")
            return 1
        return 0

    if args.write:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        return 0

    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
