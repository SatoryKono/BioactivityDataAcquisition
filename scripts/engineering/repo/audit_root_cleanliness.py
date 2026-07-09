#!/usr/bin/env python3
"""Validate tracked repository-root files and directories."""

from __future__ import annotations

import argparse
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import yaml

from scripts.engineering.repo import _root_governance as root_governance

ALLOWLIST_FILE = root_governance.ALLOWLIST_FILE
STRUCTURE_CATALOG_FILE = root_governance.STRUCTURE_CATALOG_FILE
GENERATED_ARTIFACT_ROUTING_FILE = Path(
    "configs/quality/generated_artifact_routing.yaml"
)
CANONICAL_ROOT_TEXT_FILES: frozenset[str] = frozenset(
    {
        "AGENTS.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "GEMINI.md",
        "README.md",
        # Qodo documents this exact root filename for repo-level guidance.
        "best_practices.md",
    }
)
FORBIDDEN_TRACKED_PATH_PREFIXES: tuple[str, ...] = (
    ".coverage-sharded/",
    ".codex_tmp/",
    ".python-user/",
    "MagicMock/",
    "htmlcov/",
    "logs/",
    "node_modules/",
    "output/",
    "src/tools/reports/",
    "test-output/",
    "caddy/",
    "silver/",
)
FORBIDDEN_TRACKED_ROOT_FILES: frozenset[str] = frozenset(
    {
        "contract-identity-diagnostics.json",
        "contract-registry-diagnostics.json",
        "contract-registry-dq-diagnostics.json",
        "contract-schema-classifier-diagnostics.json",
        "coverage.html",
        "coverage.json",
        "coverage.xml",
        "contract-results.xml",
        "hypothesis-contracts-results.xml",
        "port-contracts-results.xml",
        "provider-contract-drift-report.json",
        "Test Results - Pytest_All.html",
        "trivy-results.sarif",
    }
)
FORBIDDEN_LOCAL_ROOT_FILES: frozenset[str] = frozenset(
    {
        "_tmp_panel_inventory.mjs",
        "_tmp_panel_inventory.ps1",
    }
)
FORBIDDEN_DATA_SUBPATH_PREFIXES: tuple[str, ...] = ("data/.idea/",)

ALLOWED_ROOT_DIRECTORIES: frozenset[str] = root_governance.BASE_ALLOWED_ROOT_DIRECTORIES


def _approved_root_directories(catalog: dict[str, Any]) -> frozenset[str]:
    """Return allowed root directories, including catalog-ratified test support."""
    return root_governance.approved_root_directories(catalog)


def _load_structure_catalog(repo_root: Path) -> dict[str, Any]:
    """Load machine-readable structure governance catalog."""
    return root_governance.load_structure_catalog(repo_root)


def _load_allowed_root_files(repo_root: Path) -> frozenset[str]:
    """Load canonical root-file allowlist from .github/root-allowlist.txt."""
    return root_governance.load_allowed_root_files(repo_root)


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


def _get_ignored_or_untracked_paths(repo_root: Path) -> list[str]:
    """Return ignored/untracked paths for local generated-output preflight."""
    completed = _run_git(
        repo_root,
        "ls-files",
        "--others",
        "--ignored",
        "--exclude-standard",
        "--directory",
        "-z",
    )
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
    # SECRET-BEARING .env files are forbidden at root (RULES.md REQ-SECRET-004)
    if path == ".env" or (path.startswith(".env.") and path != ".env.example"):
        return True
    if path in FORBIDDEN_TRACKED_ROOT_FILES:
        return True
    if path.startswith(".coverage"):
        return True
    if path.startswith("coverage-") and path.endswith(".xml"):
        return True
    if path.startswith("coverage_") and path.endswith(".xml"):
        return True
    if path.startswith("tasks_architecture_metric_exemptions_") and path.endswith(
        ".json"
    ):
        return True
    return "sonar-scanner" in path and path.endswith(".zip")


def _load_generated_artifact_routing(repo_root: Path) -> dict[str, Any]:
    routing_path = repo_root / GENERATED_ARTIFACT_ROUTING_FILE
    with routing_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise RuntimeError(
            f"{GENERATED_ARTIFACT_ROUTING_FILE} must contain a YAML object"
        )
    return payload


def _forbidden_output_roots(routing: dict[str, Any]) -> tuple[str, ...]:
    roots = routing.get("forbidden_output_roots")
    if not isinstance(roots, list) or not roots:
        raise RuntimeError("generated artifact routing missing forbidden_output_roots")
    normalized_roots: list[str] = []
    for root in roots:
        if not isinstance(root, str) or not root:
            raise RuntimeError(
                "forbidden_output_roots entries must be non-empty strings"
            )
        normalized_roots.append(root.rstrip("/"))
    return tuple(normalized_roots)


def _path_matches_root(path: str, root: str) -> bool:
    normalized_path = path.rstrip("/")
    normalized_root = root.rstrip("/")
    return normalized_path == normalized_root or normalized_path.startswith(
        f"{normalized_root}/"
    )


def _collect_forbidden_local_output_roots(
    local_paths: list[str],
    *,
    forbidden_roots: tuple[str, ...],
    blocked_cleanup_paths: frozenset[str],
    tolerated_local_root_dirs: frozenset[str] = frozenset(),
) -> list[str]:
    """Return forbidden local output roots present outside blocked cleanup zones."""
    violations: set[str] = set()
    for raw_path in local_paths:
        normalized = raw_path.rstrip("/")
        if not normalized:
            continue
        if root_governance.is_within_blocked_cleanup_zone(
            normalized,
            blocked_cleanup_paths,
        ):
            continue
        for forbidden_root in forbidden_roots:
            if _path_matches_root(normalized, forbidden_root):
                if forbidden_root in tolerated_local_root_dirs:
                    continue
                violations.add(forbidden_root)
    return sorted(violations)


def _report_forbidden_local_output_roots(violations: list[str]) -> int:
    if not violations:
        return 0
    sys.stderr.write("ERROR: forbidden local generated output roots detected:\n")
    for violation in violations:
        sys.stderr.write(f"  - {violation}\n")
    return 1


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
    return root_governance.collect_cataloged_paths(entries, field_name=field_name)


def _collect_docs_policy_violations(
    tracked_paths: list[str],
    catalog: dict[str, Any],
    violations: list[str],
) -> None:
    """Append documentation placement policy violations."""
    tracked_set = set(tracked_paths)
    docs_drafts = _collect_cataloged_paths(catalog["docs_drafts"]["allowed_files"])
    _collect_docs_draft_policy_violations(
        tracked_paths=tracked_paths,
        docs_drafts=docs_drafts,
        violations=violations,
    )
    _collect_docs_missing_policy_violations(
        tracked_set=tracked_set,
        docs_drafts=docs_drafts,
        violations=violations,
    )


def _collect_docs_draft_policy_violations(
    *,
    tracked_paths: list[str],
    docs_drafts: set[str],
    violations: list[str],
) -> None:
    actual_docs_drafts = {
        path
        for path in tracked_paths
        if path.startswith("docs/D-") and path.endswith(".md")
    }
    for path in sorted(actual_docs_drafts - docs_drafts):
        violations.append(
            f"{path}: legacy flat doc must be cataloged in {STRUCTURE_CATALOG_FILE.as_posix()}"
        )


def _collect_docs_missing_policy_violations(
    *,
    tracked_set: set[str],
    docs_drafts: set[str],
    violations: list[str],
) -> None:
    for path in sorted(docs_drafts - tracked_set):
        violations.append(f"{path}: cataloged legacy doc is missing from tracked tree")


def _collect_plan_policy_violations(
    tracked_paths: list[str],
    catalog: dict[str, Any],
    violations: list[str],
) -> None:
    """Append plan catalog policy violations."""
    tracked_set = set(tracked_paths)
    plans = catalog["plans"]
    plans_readme = plans.get("readme")
    if not isinstance(plans_readme, str) or not plans_readme:
        raise RuntimeError("Structure catalog plans.readme must be a non-empty path")
    _collect_plans_readme_violation(plans_readme, tracked_set, violations)
    _collect_plans_catalog_violations(
        tracked_paths, plans, plans_readme, tracked_set, violations
    )
    _collect_plans_lifecycle_violation(plans, violations)


def _collect_plans_readme_violation(
    plans_readme: str,
    tracked_set: set[str],
    violations: list[str],
) -> None:
    """Ensure the plans readme exists in tracked files."""
    if plans_readme not in tracked_set:
        violations.append(f"{plans_readme}: plans readme required by structure catalog")


def _collect_plans_catalog_violations(
    tracked_paths: list[str],
    plans: dict[str, Any],
    plans_readme: str,
    tracked_set: set[str],
    violations: list[str],
) -> None:
    """Ensure tracked plans match the catalog allowlist."""
    cataloged_plan_paths = _collect_cataloged_paths(plans["allowed_files"])
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


def _collect_plans_lifecycle_violation(
    plans: dict[str, Any],
    violations: list[str],
) -> None:
    """Ensure the active backlog count matches the catalog constraint."""
    plan_entries = plans["allowed_files"]
    active_backlog_count = sum(
        1 for entry in plan_entries if entry.get("lifecycle") == "active_backlog"
    )
    max_active_backlog = plans.get("max_active_backlog")
    if not isinstance(max_active_backlog, int) or max_active_backlog < 1:
        raise RuntimeError("Structure catalog plans.max_active_backlog must be >= 1")
    if active_backlog_count != max_active_backlog:
        violations.append(
            "docs/plans lifecycle policy expects exactly "
            f"{max_active_backlog} active_backlog file(s), found {active_backlog_count}"
        )


def _collect_src_policy_violations(
    tracked_paths: list[str],
    catalog: dict[str, Any],
    violations: list[str],
) -> None:
    """Append src family approval policy violations."""
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


def _collect_blocked_cleanup_violations(
    repo_root: Path,
    catalog: dict[str, Any],
    violations: list[str],
) -> None:
    """Append violations for blocked cleanup zones missing on disk."""
    blocked_cleanup_entries = catalog["blocked_cleanup_zones"]
    blocked_cleanup_paths = _collect_cataloged_paths(blocked_cleanup_entries)
    for path in sorted(blocked_cleanup_paths):
        if not (repo_root / path).exists():
            violations.append(
                f"{path}: blocked cleanup zone declared in catalog but missing"
            )


def _collect_structure_policy_violations(
    repo_root: Path,
    tracked_paths: list[str],
    catalog: dict[str, Any],
) -> list[str]:
    """Return policy violations beyond the root allowlist."""
    violations: list[str] = []

    _collect_docs_policy_violations(tracked_paths, catalog, violations)
    _collect_plan_policy_violations(tracked_paths, catalog, violations)
    _collect_src_policy_violations(tracked_paths, catalog, violations)
    for path in sorted(tracked_paths):
        if path == "data/.idea" or path.startswith(FORBIDDEN_DATA_SUBPATH_PREFIXES):
            violations.append(
                f"{path}: IDE metadata must not live inside governed data/ surfaces"
            )
    _collect_blocked_cleanup_violations(repo_root, catalog, violations)

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


def _unexpected_local_root_python_files(
    repo_root: Path,
    tracked_root_files: set[str],
) -> list[str]:
    """Return unexpected local root Python files present on disk."""
    violations: list[str] = []
    for entry in repo_root.iterdir():
        if not entry.is_file():
            continue
        if entry.name in tracked_root_files:
            continue
        if entry.suffix == ".py":
            violations.append(entry.name)
    return sorted(violations)


def _unexpected_local_root_temp_files(
    repo_root: Path,
    tracked_root_files: set[str],
) -> list[str]:
    """Return forbidden local root temp files present on disk."""
    violations: list[str] = []
    for entry in repo_root.iterdir():
        if not entry.is_file():
            continue
        if entry.name in tracked_root_files:
            continue
        if entry.name in FORBIDDEN_LOCAL_ROOT_FILES:
            violations.append(entry.name)
    return sorted(violations)


def _unexpected_local_root_dirs_on_disk(
    repo_root: Path,
    *,
    tracked_root_dirs: set[str],
    allowed_root_dirs: frozenset[str],
    tolerated_local_root_dirs: frozenset[str],
) -> list[str]:
    """Return unexpected root directories present on disk, including ignored dirs."""
    violations: list[str] = []
    for entry in repo_root.iterdir():
        if entry.name == ".git" or not entry.is_dir():
            continue
        if entry.name in tracked_root_dirs:
            continue
        if entry.name in allowed_root_dirs:
            continue
        if entry.name in tolerated_local_root_dirs:
            continue
        violations.append(entry.name)
    return sorted(violations)


def _report_strict_local_root_clutter(
    *,
    unexpected_local_root_python_files: list[str],
    unexpected_local_root_temp_files: list[str],
    unexpected_local_root_dirs: list[str],
) -> bool:
    """Report local root clutter that strict mode must reject even if ignored."""
    has_violations = False
    if unexpected_local_root_python_files:
        has_violations = True
        sys.stderr.write(
            "ERROR: unexpected local root Python files detected in strict mode:\n"
        )
        for entry in unexpected_local_root_python_files:
            sys.stderr.write(f"  - {entry}\n")
    if unexpected_local_root_temp_files:
        has_violations = True
        sys.stderr.write(
            "ERROR: unexpected local root temporary files detected in strict mode:\n"
        )
        for entry in unexpected_local_root_temp_files:
            sys.stderr.write(f"  - {entry}\n")
    if unexpected_local_root_dirs:
        has_violations = True
        sys.stderr.write(
            "ERROR: unexpected local root directories detected in strict mode:\n"
        )
        for entry in unexpected_local_root_dirs:
            sys.stderr.write(f"  - {entry}\n")
    return has_violations


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


def collect_root_layout_state(
    repo_root: Path,
    *,
    include_untracked: bool = True,
) -> dict[str, object]:
    """Return deterministic root-layout state for audits and evidence export."""
    allowed_root_files = _load_allowed_root_files(repo_root)
    structure_catalog = _load_structure_catalog(repo_root)
    tracked_paths = _get_tracked_paths(repo_root)
    allowed_root_dirs = _approved_root_directories(structure_catalog)
    tracked_root_files, tracked_root_dirs = _collect_tracked_root_entries(tracked_paths)

    state: dict[str, object] = {
        "allowed_root_files": allowed_root_files,
        "allowed_root_dirs": allowed_root_dirs,
        "structure_catalog": structure_catalog,
        "tracked_paths": tracked_paths,
        "tracked_root_files": tracked_root_files,
        "tracked_root_dirs": tracked_root_dirs,
        "unexpected_root_files": sorted(tracked_root_files - allowed_root_files),
        "unexpected_root_dirs": sorted(tracked_root_dirs - allowed_root_dirs),
        "missing_allowed_files": sorted(allowed_root_files - tracked_root_files),
    }
    if include_untracked:
        untracked_paths = _get_untracked_paths(repo_root)
        state["untracked_paths"] = untracked_paths
        state["unexpected_untracked_root_files"] = sorted(
            _collect_untracked_root_files(untracked_paths)
        )
        state["unexpected_untracked_root_dirs"] = _unexpected_untracked_root_dirs(
            untracked_paths,
            tracked_root_dirs,
            allowed_root_dirs,
        )
    return state


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate root tracked layout and flag unexpected untracked root files.",
    )
    parser.add_argument(
        "--strict-untracked",
        action="store_true",
        help="Fail when non-ignored untracked root files are present.",
    )
    parser.add_argument(
        "--check-local-forbidden-outputs",
        action="store_true",
        help=(
            "Fail when ignored/local forbidden output roots from "
            "generated_artifact_routing.yaml are present outside blocked zones."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    script_root = Path(__file__).resolve().parents[3]
    repo_root = _discover_repo_root(script_root)

    try:
        layout_state = collect_root_layout_state(repo_root)
    except (
        OSError,
        RuntimeError,
        subprocess.CalledProcessError,
        yaml.YAMLError,
    ) as exc:
        sys.stderr.write(f"ERROR: failed to collect root layout state: {exc}\n")
        return 2

    structure_catalog = layout_state["structure_catalog"]
    tracked_paths = layout_state["tracked_paths"]
    tracked_root_files = layout_state["tracked_root_files"]
    tracked_root_dirs = layout_state["tracked_root_dirs"]
    allowed_root_dirs = layout_state["allowed_root_dirs"]
    unexpected_root_files = layout_state["unexpected_root_files"]
    unexpected_root_dirs = layout_state["unexpected_root_dirs"]
    missing_allowed_files = layout_state["missing_allowed_files"]
    tolerated_local_root_dirs = root_governance.local_tolerated_root_directories(
        structure_catalog
    )

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

    strict_local_root_violation = _report_strict_local_root_clutter(
        unexpected_local_root_python_files=_unexpected_local_root_python_files(
            repo_root, tracked_root_files
        ),
        unexpected_local_root_temp_files=_unexpected_local_root_temp_files(
            repo_root, tracked_root_files
        ),
        unexpected_local_root_dirs=_unexpected_local_root_dirs_on_disk(
            repo_root,
            tracked_root_dirs=tracked_root_dirs,
            allowed_root_dirs=allowed_root_dirs,
            tolerated_local_root_dirs=tolerated_local_root_dirs,
        ),
    )
    if args.strict_untracked and strict_local_root_violation:
        return 1

    unexpected_untracked_root_files = layout_state["unexpected_untracked_root_files"]
    unexpected_untracked_root_dirs = layout_state["unexpected_untracked_root_dirs"]
    strict_untracked_violation = _report_untracked_root_entries(
        unexpected_untracked_root_files=unexpected_untracked_root_files,
        unexpected_untracked_root_dirs=unexpected_untracked_root_dirs,
    )
    if args.strict_untracked and strict_untracked_violation:
        return 1

    if args.check_local_forbidden_outputs:
        try:
            routing = _load_generated_artifact_routing(repo_root)
            ignored_or_untracked_paths = _get_ignored_or_untracked_paths(repo_root)
        except (
            OSError,
            RuntimeError,
            subprocess.CalledProcessError,
            yaml.YAMLError,
        ) as exc:
            sys.stderr.write(f"ERROR: failed to query local generated outputs: {exc}\n")
            return 2
        forbidden_local_outputs = _collect_forbidden_local_output_roots(
            ignored_or_untracked_paths,
            forbidden_roots=_forbidden_output_roots(routing),
            blocked_cleanup_paths=root_governance.blocked_cleanup_paths(
                structure_catalog
            ),
            tolerated_local_root_dirs=tolerated_local_root_dirs,
        )
        forbidden_local_output_exit = _report_forbidden_local_output_roots(
            forbidden_local_outputs
        )
        if forbidden_local_output_exit:
            return forbidden_local_output_exit

    sys.stdout.write(
        "OK: root layout audit passed "
        f"({len(tracked_root_files)} root files, {len(tracked_root_dirs)} root directories validated).\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
