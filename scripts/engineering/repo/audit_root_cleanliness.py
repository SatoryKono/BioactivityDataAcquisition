#!/usr/bin/env python3
"""Validate tracked repository-root files and directories."""

from __future__ import annotations

import argparse
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import Any

import yaml

ALLOWLIST_FILE = Path(".github/root-allowlist.txt")
STRUCTURE_CATALOG_FILE = Path("configs/quality/repo_structure_catalog.yaml")
CANONICAL_ROOT_TEXT_FILES: frozenset[str] = frozenset(
    {
        "AGENTS.md",
        "CHANGELOG.md",
        "GEMINI.md",
        "README.md",
    }
)
FORBIDDEN_TRACKED_PATH_PREFIXES: tuple[str, ...] = (
    ".coverage-sharded/",
    ".python-user/",
    "MagicMock/",
    "htmlcov/",
    "logs/",
    "node_modules/",
    "output/",
    "src/tools/reports/",
    "test-output/",
)
FORBIDDEN_TRACKED_ROOT_FILES: frozenset[str] = frozenset(
    {
        "contract-identity-diagnostics.json",
        "contract-registry-diagnostics.json",
        "contract-registry-dq-diagnostics.json",
        "contract-schema-classifier-diagnostics.json",
        "coverage.json",
        "coverage.xml",
        "contract-results.xml",
        "hypothesis-contracts-results.xml",
        "port-contracts-results.xml",
        "provider-contract-drift-report.json",
        "trivy-results.sarif",
    }
)

ALLOWED_ROOT_DIRECTORIES: frozenset[str] = frozenset(
    {
        ".ai",
        ".aiassistant",
        ".claude",
        ".codex",
        ".codex_tmp",
        ".gemini",
        ".github",
        ".jules",
        ".junie",
        ".vibe",
        ".cursor",
        ".idea",
        ".sonarlint",
        ".vscode",
        "script-codex",
        "script-gemini",
        "script-mistrall",
        "script-mistrallvibe",
        "assets",
        "configs",
        "data",
        "docs",
        "grafana",
        "reports",
        "scripts",
        "src",
        "tests",
    }
)


def _approved_root_directories(catalog: dict[str, Any]) -> frozenset[str]:
    """Return allowed root directories, including catalog-ratified test support."""
    approved_test_support_dirs: set[str] = set()
    test_support = catalog.get("test_support_roots")
    if isinstance(test_support, dict):
        approved_test_support_dirs = _collect_cataloged_paths(
            test_support.get("approved_roots", [])
        )
    return frozenset(ALLOWED_ROOT_DIRECTORIES | approved_test_support_dirs)


def _load_structure_catalog(repo_root: Path) -> dict[str, Any]:
    """Load machine-readable structure governance catalog."""
    catalog_path = repo_root / STRUCTURE_CATALOG_FILE
    if not catalog_path.exists():
        raise RuntimeError(f"Structure catalog does not exist: {catalog_path}")

    with catalog_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}

    required_sections = {
        "docs_drafts",
        "plans",
        "src_sidecars",
        "blocked_cleanup_zones",
    }
    missing_sections = sorted(
        section for section in required_sections if section not in payload
    )
    if missing_sections:
        missing = ", ".join(missing_sections)
        raise RuntimeError(f"Structure catalog missing required sections: {missing}")
    return payload


def _load_allowed_root_files(repo_root: Path) -> frozenset[str]:
    """Load canonical root-file allowlist from .github/root-allowlist.txt."""
    allowlist_path = repo_root / ALLOWLIST_FILE
    if not allowlist_path.exists():
        raise RuntimeError(f"Allowlist file does not exist: {allowlist_path}")

    entries: set[str] = set()
    with allowlist_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            cleaned = line.strip()
            if not cleaned or cleaned.startswith("#"):
                continue
            if "/" in cleaned:
                raise RuntimeError(
                    "Root allowlist must contain only root-level file names "
                    f"(invalid entry: {cleaned})"
                )
            entries.add(cleaned)

    if not entries:
        raise RuntimeError(f"Allowlist is empty: {allowlist_path}")
    return frozenset(entries)


def _discover_repo_root(script_root: Path) -> Path:
    """Best-effort repository root discovery that works in mixed Windows/WSL runs."""

    def _find_from(start: Path) -> Path | None:
        current = start if start.is_dir() else start.parent
        for candidate in (current, *current.parents):
            if (candidate / ".git").exists():
                return candidate
        return None

    for base in (Path.cwd(), script_root):
        resolved = _find_from(base)
        if resolved is not None:
            return resolved
    return script_root


def _run_git(repo_root: Path, *git_args: str) -> subprocess.CompletedProcess[bytes]:
    """Run git with fallbacks for path/cwd interoperability issues."""
    attempts: list[tuple[list[str], Path | None]] = [
        (["git", "-C", str(repo_root), *git_args], None),
        (["git", *git_args], repo_root),
        (["git", *git_args], Path.cwd()),
    ]
    if sys.platform == "win32":
        # Mixed WSL/Windows runs can fail to spawn native git reliably from
        # Windows Python; route through wsl as a last-resort fallback.
        attempts.extend(
            (
                (["wsl.exe", "git", *git_args], repo_root),
                (["wsl", "git", *git_args], repo_root),
            )
        )
    last_error: subprocess.CalledProcessError | None = None
    for command, cwd in attempts:
        try:
            return subprocess.run(  # nosec
                command,
                check=True,
                capture_output=True,
                text=False,
                cwd=str(cwd) if cwd is not None else None,
            )
        except subprocess.CalledProcessError as exc:
            last_error = exc
    assert last_error is not None
    raise last_error


def _get_tracked_paths(repo_root: Path) -> list[str]:
    """Return tracked paths from git index, excluding staged deletions."""
    completed = _run_git(repo_root, "ls-files", "-z")
    staged_deleted = _run_git(
        repo_root,
        "diff",
        "--cached",
        "--name-only",
        "--diff-filter=D",
        "-z",
    )
    decoded = completed.stdout.decode("utf-8", errors="replace")
    deleted = {
        path
        for path in staged_deleted.stdout.decode("utf-8", errors="replace").split("\0")
        if path
    }
    return [path for path in decoded.split("\0") if path and path not in deleted]


def _collect_tracked_root_entries(paths: list[str]) -> tuple[set[str], set[str]]:
    """Split tracked paths into root files and root directories."""
    root_files: set[str] = set()
    root_dirs: set[str] = set()
    for path in paths:
        if "/" not in path:
            root_files.add(path)
            continue
        root_dirs.add(path.split("/", maxsplit=1)[0])
    return root_files, root_dirs


def _get_untracked_paths(repo_root: Path) -> list[str]:
    """Return untracked (non-ignored) paths from git working tree."""
    completed = _run_git(repo_root, "ls-files", "--others", "--exclude-standard", "-z")
    decoded = completed.stdout.decode("utf-8", errors="replace")
    return [path for path in decoded.split("\0") if path]


def _collect_untracked_root_files(paths: list[str]) -> set[str]:
    """Return only root-level untracked files."""
    return {path for path in paths if "/" not in path}


def _collect_untracked_root_dirs(paths: list[str]) -> set[str]:
    """Return root directory names inferred from untracked nested paths."""
    return {path.split("/", maxsplit=1)[0] for path in paths if "/" in path}


def _report_root_layout_violations(
    *,
    unexpected_root_files: list[str],
    unexpected_root_dirs: list[str],
) -> int:
    if not unexpected_root_files and not unexpected_root_dirs:
        return 0

    sys.stderr.write("ERROR: root layout policy violation detected.\n")
    if unexpected_root_files:
        sys.stderr.write("Unexpected tracked root files:\n")
        for entry in unexpected_root_files:
            sys.stderr.write(f"  - {entry}\n")
    if unexpected_root_dirs:
        sys.stderr.write("Unexpected tracked root directories:\n")
        for entry in unexpected_root_dirs:
            sys.stderr.write(f"  - {entry}\n")
    return 1


def _is_forbidden_tracked_artifact(path: str) -> bool:
    """Return True when a tracked path belongs to a generated/local artifact family."""
    if path.startswith(FORBIDDEN_TRACKED_PATH_PREFIXES):
        return True
    if "/" in path:
        return False
    if path in FORBIDDEN_TRACKED_ROOT_FILES:
        return True
    if path.startswith(".coverage"):
        return True
    if path.startswith("coverage-") and path.endswith(".xml"):
        return True
    if path.startswith("tasks_architecture_metric_exemptions_") and path.endswith(
        ".json"
    ):
        return True
    return "sonar-scanner" in path and path.endswith(".zip")


def _collect_tracked_policy_violations(paths: list[str]) -> list[str]:
    """Return tracked paths that violate root and generated-artifact policy."""
    violations: list[str] = []
    for path in paths:
        if _is_forbidden_tracked_artifact(path):
            violations.append(f"{path}: generated/runtime artifact must not be tracked")
            continue
        if "/" in path:
            continue
        if path.endswith(".py"):
            violations.append(f"{path}: root-level Python files are not allowed")
            continue
        if path.endswith((".md", ".txt")) and path not in CANONICAL_ROOT_TEXT_FILES:
            violations.append(
                f"{path}: root text files must be canonical entrypoints only"
            )
    return sorted(violations)


def _report_tracked_policy_violations(violations: list[str]) -> int:
    if not violations:
        return 0

    sys.stderr.write("ERROR: tracked repository placement policy violation detected.\n")
    for violation in violations:
        sys.stderr.write(f"  - {violation}\n")
    return 1


def _report_missing_allowed_files(missing_allowed_files: list[str]) -> None:
    if not missing_allowed_files:
        return
    sys.stdout.write(
        "INFO: allowlisted root files currently absent (forward-compatible):\n"
    )
    for entry in missing_allowed_files:
        sys.stdout.write(f"  - {entry}\n")


def _collect_cataloged_paths(
    entries: list[dict[str, Any]], *, field_name: str = "path"
) -> set[str]:
    """Return normalized path set from catalog entries."""
    cataloged: set[str] = set()
    for entry in entries:
        path = entry.get(field_name)
        if not isinstance(path, str) or not path:
            raise RuntimeError(
                f"Structure catalog entry must contain non-empty '{field_name}'"
            )
        cataloged.add(path)
    return cataloged


def _collect_structure_policy_violations(
    repo_root: Path,
    tracked_paths: list[str],
    catalog: dict[str, Any],
) -> list[str]:
    """Return policy violations beyond the root allowlist."""
    tracked_set = set(tracked_paths)
    violations: list[str] = []

    docs_drafts = _collect_cataloged_paths(catalog["docs_drafts"]["allowed_files"])
    actual_docs_drafts = {
        path
        for path in tracked_paths
        if path.startswith("docs/D-") and path.endswith(".md")
    }
    for path in sorted(actual_docs_drafts - docs_drafts):
        violations.append(
            f"{path}: legacy flat doc must be cataloged in {STRUCTURE_CATALOG_FILE.as_posix()}"
        )
    for path in sorted(docs_drafts - tracked_set):
        violations.append(f"{path}: cataloged legacy doc is missing from tracked tree")

    plans_readme = catalog["plans"].get("readme")
    if not isinstance(plans_readme, str) or not plans_readme:
        raise RuntimeError("Structure catalog plans.readme must be a non-empty path")
    if plans_readme not in tracked_set:
        violations.append(f"{plans_readme}: plans readme required by structure catalog")

    cataloged_plan_paths = _collect_cataloged_paths(catalog["plans"]["allowed_files"])
    actual_plan_paths = {
        path
        for path in tracked_paths
        if path.startswith("docs/plans/")
        and path.endswith(".md")
        and path != plans_readme
    }
    for path in sorted(actual_plan_paths - cataloged_plan_paths):
        violations.append(
            f"{path}: plan file must be cataloged in {STRUCTURE_CATALOG_FILE.as_posix()}"
        )
    for path in sorted(cataloged_plan_paths - tracked_set):
        violations.append(f"{path}: cataloged plan file is missing from tracked tree")

    plan_entries = catalog["plans"]["allowed_files"]
    active_backlog_count = sum(
        1 for entry in plan_entries if entry.get("lifecycle") == "active_backlog"
    )
    max_active_backlog = catalog["plans"].get("max_active_backlog")
    if not isinstance(max_active_backlog, int) or max_active_backlog < 1:
        raise RuntimeError("Structure catalog plans.max_active_backlog must be >= 1")
    if active_backlog_count != max_active_backlog:
        violations.append(
            "docs/plans lifecycle policy expects exactly "
            f"{max_active_backlog} active_backlog file(s), found {active_backlog_count}"
        )

    approved_src_roots = _collect_cataloged_paths(
        catalog["src_sidecars"]["approved_roots"]
    )
    actual_src_roots = {
        "/".join(path.split("/", maxsplit=2)[:2])
        for path in tracked_paths
        if path.startswith("src/") and len(path.split("/", maxsplit=2)) >= 2
    }
    for path in sorted(actual_src_roots - approved_src_roots):
        violations.append(
            f"{path}: new src top-level family requires explicit structure catalog approval"
        )

    blocked_cleanup_entries = catalog["blocked_cleanup_zones"]
    blocked_cleanup_paths = _collect_cataloged_paths(blocked_cleanup_entries)
    for path in sorted(blocked_cleanup_paths):
        if not (repo_root / path).exists():
            violations.append(
                f"{path}: blocked cleanup zone declared in catalog but missing"
            )

    return violations


def _report_structure_policy_violations(violations: list[str]) -> int:
    if not violations:
        return 0

    sys.stderr.write("ERROR: structure governance policy violation detected.\n")
    for violation in violations:
        sys.stderr.write(f"  - {violation}\n")
    return 1


def _unexpected_untracked_root_dirs(
    untracked_paths: list[str],
    tracked_root_dirs: set[str],
    allowed_root_dirs: frozenset[str],
) -> list[str]:
    return sorted(
        root_dir
        for root_dir in _collect_untracked_root_dirs(untracked_paths)
        if root_dir not in tracked_root_dirs and root_dir not in allowed_root_dirs
    )


def _report_untracked_root_entries(
    *,
    unexpected_untracked_root_files: list[str],
    unexpected_untracked_root_dirs: list[str],
) -> bool:
    has_violations = False
    if unexpected_untracked_root_files:
        has_violations = True
        sys.stdout.write(
            "WARNING: non-ignored untracked root files detected "
            "(SHOULD be moved under tests/fixtures/reports or ignored):\n"
        )
        for entry in unexpected_untracked_root_files:
            sys.stdout.write(f"  - {entry}\n")
    if unexpected_untracked_root_dirs:
        has_violations = True
        sys.stdout.write(
            "WARNING: non-ignored untracked root directories detected "
            "(SHOULD be reviewed/moved/ignored):\n"
        )
        for entry in unexpected_untracked_root_dirs:
            sys.stdout.write(f"  - {entry}\n")
    return has_violations


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate root tracked layout and flag unexpected untracked root files.",
    )
    parser.add_argument(
        "--strict-untracked",
        action="store_true",
        help="Fail when non-ignored untracked root files are present.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    script_root = Path(__file__).resolve().parents[3]
    repo_root = _discover_repo_root(script_root)

    try:
        allowed_root_files = _load_allowed_root_files(repo_root)
    except (OSError, RuntimeError) as exc:
        sys.stderr.write(f"ERROR: failed to load root allowlist: {exc}\n")
        return 2
    try:
        structure_catalog = _load_structure_catalog(repo_root)
    except (OSError, RuntimeError, yaml.YAMLError) as exc:
        sys.stderr.write(f"ERROR: failed to load structure catalog: {exc}\n")
        return 2

    try:
        tracked_paths = _get_tracked_paths(repo_root)
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(f"ERROR: failed to query git index: {exc}\n")
        return 2

    allowed_root_dirs = _approved_root_directories(structure_catalog)

    tracked_root_files, tracked_root_dirs = _collect_tracked_root_entries(tracked_paths)

    unexpected_root_files = sorted(tracked_root_files - allowed_root_files)
    unexpected_root_dirs = sorted(tracked_root_dirs - allowed_root_dirs)
    missing_allowed_files = sorted(allowed_root_files - tracked_root_files)

    root_layout_exit = _report_root_layout_violations(
        unexpected_root_files=unexpected_root_files,
        unexpected_root_dirs=unexpected_root_dirs,
    )
    if root_layout_exit:
        return root_layout_exit

    tracked_policy_exit = _report_tracked_policy_violations(
        _collect_tracked_policy_violations(tracked_paths)
    )
    if tracked_policy_exit:
        return tracked_policy_exit

    structure_policy_exit = _report_structure_policy_violations(
        _collect_structure_policy_violations(
            repo_root, tracked_paths, structure_catalog
        )
    )
    if structure_policy_exit:
        return structure_policy_exit

    _report_missing_allowed_files(missing_allowed_files)

    try:
        untracked_paths = _get_untracked_paths(repo_root)
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(f"ERROR: failed to query untracked paths: {exc}\n")
        return 2

    unexpected_untracked_root_files = sorted(
        _collect_untracked_root_files(untracked_paths)
    )
    unexpected_untracked_root_dirs = _unexpected_untracked_root_dirs(
        untracked_paths, tracked_root_dirs, allowed_root_dirs
    )
    strict_untracked_violation = _report_untracked_root_entries(
        unexpected_untracked_root_files=unexpected_untracked_root_files,
        unexpected_untracked_root_dirs=unexpected_untracked_root_dirs,
    )
    if args.strict_untracked and strict_untracked_violation:
        return 1

    sys.stdout.write(
        "OK: root layout audit passed "
        f"({len(tracked_root_files)} root files, {len(tracked_root_dirs)} root directories validated).\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
