"""Preflight checks for reproducible BioETL test-surface audits."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/v1"
TELEMETRY_BASELINE = Path("docs/05-engineering/test-telemetry-baseline.md")
VCR_FIXTURE_ROOT = Path("tests/fixtures/vcr")
DEFAULT_GIT_TIMEOUT_SECONDS = 5.0
WINDOWS_GIT_LFS_CANDIDATES = (
    Path("/mnt/c/Program Files/Git/mingw64/bin/git-lfs.exe"),
    Path("/mnt/c/Program Files/Git/cmd/git-lfs.exe"),
)
WINDOWS_GIT_CANDIDATES = (
    Path("/mnt/c/Program Files/Git/bin/git.exe"),
    Path("/mnt/c/Program Files/Git/cmd/git.exe"),
)
STRICT_BLOCKER_IDS = (
    "missing_git_lfs",
    "git_lfs_unhealthy",
    "git_status_failed",
    "dirty_vcr_worktree",
    "lfs_pointer_files_present",
    "missing_telemetry_baseline",
    "telemetry_baseline_without_coverage",
)

GitRunner = Callable[[list[str]], subprocess.CompletedProcess[str]]


def _default_git_runner(
    root: Path, *, timeout_seconds: float = DEFAULT_GIT_TIMEOUT_SECONDS
) -> GitRunner:
    def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )

    return _run


def _normalize_process_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip()
    return value.strip()


def _git_value(runner: GitRunner, args: list[str]) -> dict[str, Any]:
    try:
        result = runner(args)
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "stdout": _normalize_process_output(exc.stdout),
            "stderr": _normalize_process_output(exc.stderr)
            or f"git {' '.join(args)} timed out after {exc.timeout}s.",
            "returncode": None,
            "timed_out": True,
        }
    return {
        "ok": result.returncode == 0,
        "stdout": _normalize_process_output(result.stdout),
        "stderr": _normalize_process_output(result.stderr),
        "returncode": result.returncode,
        "timed_out": False,
    }


def _process_value(
    command: list[str],
    *,
    root: Path,
    timeout_seconds: float = DEFAULT_GIT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "stdout": _normalize_process_output(exc.stdout),
            "stderr": _normalize_process_output(exc.stderr)
            or f"{' '.join(command)} timed out after {exc.timeout}s.",
            "returncode": None,
            "timed_out": True,
        }
    return {
        "ok": result.returncode == 0,
        "stdout": _normalize_process_output(result.stdout),
        "stderr": _normalize_process_output(result.stderr),
        "returncode": result.returncode,
        "timed_out": False,
    }


def _first_existing_candidate(candidates: tuple[Path, ...]) -> str | None:
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate.as_posix()
    return None


def _detect_git_lfs_path(explicit_path: str | None) -> str | None:
    if explicit_path is not None:
        return explicit_path or None
    return shutil.which("git-lfs") or _first_existing_candidate(
        WINDOWS_GIT_LFS_CANDIDATES
    )


def _git_lfs_version(
    *,
    lfs_path: str,
    root: Path,
    git_runner: GitRunner,
    prefer_direct_binary: bool,
) -> dict[str, Any]:
    if prefer_direct_binary and Path(lfs_path).exists():
        return _process_value([lfs_path, "version"], root=root)
    return _git_value(git_runner, ["lfs", "version"])


def _windows_git_status(
    root: Path,
    *,
    status_args: list[str] | None = None,
) -> dict[str, Any] | None:
    git_path = _first_existing_candidate(WINDOWS_GIT_CANDIDATES)
    if git_path is None:
        return None
    resolved_status_args = status_args or [
        "status",
        "--short",
        "--untracked-files=no",
    ]
    result = _process_value(
        [git_path, *resolved_status_args],
        root=root,
    )
    if result["ok"]:
        result["fallback"] = git_path
    return result


def _detect_default_branch(runner: GitRunner) -> str:
    remote_head = _git_value(
        runner,
        ["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"],
    )
    if remote_head["ok"] and remote_head["stdout"].startswith("origin/"):
        return str(remote_head["stdout"]).split("/", 1)[1]
    return "main"


def _skipped_git_status_due_to_missing_lfs() -> dict[str, Any]:
    return {
        "ok": True,
        "stdout": "",
        "stderr": (
            "Skipped git status because git-lfs is unavailable; missing_git_lfs "
            "is the strict reproducibility blocker."
        ),
        "returncode": None,
        "timed_out": False,
        "skipped": True,
    }


def _changed_paths_from_git_status(status_output: str) -> list[str]:
    paths: list[str] = []
    for raw_line in status_output.splitlines():
        line = raw_line.rstrip()
        if len(line) < 3:
            continue
        # Git status porcelain emits a two-character status plus an optional
        # separator space before the path. Be tolerant if a leading space was
        # already stripped from the first stdout line by higher-level
        # normalization, so " M path" and "M path" both resolve to "path".
        path = line[3:] if len(line) >= 4 and line[2] == " " else line[2:]
        path = path.lstrip()
        if " -> " in path:
            path = path.rsplit(" -> ", maxsplit=1)[-1]
        paths.append(path)
    return paths


def _scan_lfs_pointer_files(root: Path) -> list[str]:
    vcr_root = root / VCR_FIXTURE_ROOT
    if not vcr_root.exists():
        return []

    pointer_files: list[str] = []
    max_pointer_bytes = 4096
    for path in sorted(vcr_root.rglob("*")):
        if not path.is_file():
            continue
        try:
            if path.stat().st_size > max_pointer_bytes:
                continue
            if path.read_bytes()[: len(LFS_POINTER_PREFIX)] == LFS_POINTER_PREFIX:
                pointer_files.append(path.relative_to(root).as_posix())
        except OSError:
            continue
    return pointer_files


def _collect_git_status_surfaces(
    *,
    git_runner: GitRunner,
    lfs_available: bool,
    using_default_runner: bool,
    root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not lfs_available:
        skipped = _skipped_git_status_due_to_missing_lfs()
        return skipped, skipped
    git_status = _git_value(git_runner, ["status", "--short", "--untracked-files=no"])
    vcr_git_status = _git_value(
        git_runner,
        [
            "status",
            "--short",
            "--untracked-files=all",
            "--",
            VCR_FIXTURE_ROOT.as_posix(),
        ],
    )
    if using_default_runner and git_status["timed_out"]:
        fallback_status = _windows_git_status(root)
        if fallback_status is not None:
            git_status = fallback_status
    if using_default_runner and vcr_git_status["timed_out"]:
        fallback_status = _windows_git_status(
            root,
            status_args=[
                "status",
                "--short",
                "--untracked-files=all",
                "--",
                VCR_FIXTURE_ROOT.as_posix(),
            ],
        )
        if fallback_status is not None:
            vcr_git_status = fallback_status
    return git_status, vcr_git_status


def _append_blocker(
    blockers: list[dict[str, str]], *, blocker_id: str, message: str
) -> None:
    blockers.append({"id": blocker_id, "message": message})


def _append_lfs_blockers(
    blockers: list[dict[str, str]],
    *,
    lfs_path: str | None,
    git_lfs_version: dict[str, Any] | None,
    lfs_pointer_files: list[str],
) -> None:
    if not lfs_path:
        _append_blocker(
            blockers,
            blocker_id="missing_git_lfs",
            message=(
                "git-lfs is required before comparing main-branch audit evidence."
            ),
        )
    elif git_lfs_version is not None and not git_lfs_version["ok"]:
        _append_blocker(
            blockers,
            blocker_id="git_lfs_unhealthy",
            message=(
                git_lfs_version["stderr"]
                or git_lfs_version["stdout"]
                or "git lfs version failed."
            ),
        )
    if lfs_pointer_files:
        _append_blocker(
            blockers,
            blocker_id="lfs_pointer_files_present",
            message=(
                f"Found {len(lfs_pointer_files)} unresolved git-lfs pointer "
                "files under tests/fixtures/vcr; run git lfs install/pull "
                "before treating VCR-backed audit evidence as reproducible."
            ),
        )


def _append_git_status_blockers(
    blockers: list[dict[str, str]],
    *,
    git_status: dict[str, Any],
    vcr_git_status: dict[str, Any],
    dirty_vcr_paths: list[str],
) -> None:
    if not git_status["ok"]:
        _append_blocker(
            blockers,
            blocker_id="git_status_failed",
            message=(
                git_status["stderr"] or git_status["stdout"] or "git status failed."
            ),
        )
    if not vcr_git_status["ok"]:
        _append_blocker(
            blockers,
            blocker_id="git_status_failed",
            message=(
                vcr_git_status["stderr"]
                or vcr_git_status["stdout"]
                or "git status failed for tests/fixtures/vcr."
            ),
        )
    if dirty_vcr_paths:
        _append_blocker(
            blockers,
            blocker_id="dirty_vcr_worktree",
            message=(
                f"Found {len(dirty_vcr_paths)} dirty VCR cassette path(s); "
                "commit, restore, or intentionally re-record them before "
                "treating VCR-backed audit evidence as reproducible."
            ),
        )


def _append_baseline_blockers(
    blockers: list[dict[str, str]],
    *,
    baseline_exists: bool,
    baseline_has_coverage: bool,
) -> None:
    if not baseline_exists:
        _append_blocker(
            blockers,
            blocker_id="missing_telemetry_baseline",
            message=f"Missing {TELEMETRY_BASELINE.as_posix()}.",
        )
        return
    if not baseline_has_coverage:
        _append_blocker(
            blockers,
            blocker_id="telemetry_baseline_without_coverage",
            message="Telemetry baseline exists but does not expose Actual coverage.",
        )


def _build_preflight_blockers(
    *,
    lfs_path: str | None,
    git_lfs_version: dict[str, Any] | None,
    git_status: dict[str, Any],
    vcr_git_status: dict[str, Any],
    dirty_vcr_paths: list[str],
    lfs_pointer_files: list[str],
    baseline_exists: bool,
    baseline_has_coverage: bool,
) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    _append_lfs_blockers(
        blockers,
        lfs_path=lfs_path,
        git_lfs_version=git_lfs_version,
        lfs_pointer_files=lfs_pointer_files,
    )
    _append_git_status_blockers(
        blockers,
        git_status=git_status,
        vcr_git_status=vcr_git_status,
        dirty_vcr_paths=dirty_vcr_paths,
    )
    _append_baseline_blockers(
        blockers,
        baseline_exists=baseline_exists,
        baseline_has_coverage=baseline_has_coverage,
    )
    return blockers


def collect_test_audit_preflight(
    root: Path = ROOT,
    *,
    runner: GitRunner | None = None,
    git_lfs_path: str | None = None,
) -> dict[str, Any]:
    """Collect preflight facts needed before treating an audit as reproducible."""
    root = root.resolve()
    using_default_runner = runner is None
    git_runner = runner or _default_git_runner(root)
    lfs_path = _detect_git_lfs_path(git_lfs_path)

    current_branch = _git_value(git_runner, ["branch", "--show-current"])
    current_commit = _git_value(git_runner, ["rev-parse", "--short", "HEAD"])
    default_branch = _detect_default_branch(git_runner)
    default_commit = _git_value(git_runner, ["rev-parse", "--short", default_branch])
    lfs_available = bool(lfs_path)
    git_lfs_version = (
        _git_lfs_version(
            lfs_path=lfs_path,
            root=root,
            git_runner=git_runner,
            prefer_direct_binary=using_default_runner,
        )
        if lfs_path
        else None
    )
    git_status, vcr_git_status = _collect_git_status_surfaces(
        git_runner=git_runner,
        lfs_available=lfs_available,
        using_default_runner=using_default_runner,
        root=root,
    )

    baseline_path = root / TELEMETRY_BASELINE
    baseline_exists = baseline_path.exists()
    baseline_text = baseline_path.read_text(encoding="utf-8") if baseline_exists else ""
    baseline_has_coverage = "Actual coverage:" in baseline_text
    lfs_pointer_files = _scan_lfs_pointer_files(root)
    dirty_vcr_paths = (
        _changed_paths_from_git_status(str(vcr_git_status["stdout"]))
        if vcr_git_status["ok"]
        else []
    )
    blockers = _build_preflight_blockers(
        lfs_path=lfs_path,
        git_lfs_version=git_lfs_version,
        git_status=git_status,
        vcr_git_status=vcr_git_status,
        dirty_vcr_paths=dirty_vcr_paths,
        lfs_pointer_files=lfs_pointer_files,
        baseline_exists=baseline_exists,
        baseline_has_coverage=baseline_has_coverage,
    )

    return {
        "root": root.as_posix(),
        "current_branch": current_branch,
        "current_commit": current_commit,
        "default_branch": default_branch,
        "default_commit": default_commit,
        "git_status": git_status,
        "vcr_git_status": vcr_git_status,
        "git_lfs": {
            "available": bool(lfs_path),
            "path": lfs_path,
            "version": git_lfs_version,
        },
        "telemetry_baseline": {
            "path": TELEMETRY_BASELINE.as_posix(),
            "exists": baseline_exists,
            "has_actual_coverage": baseline_has_coverage,
        },
        "lfs_pointer_files": {
            "count": len(lfs_pointer_files),
            "examples": lfs_pointer_files[:20],
        },
        "dirty_vcr_worktree": {
            "count": len(dirty_vcr_paths),
            "examples": dirty_vcr_paths[:20],
        },
        "blockers": blockers,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Collect reproducibility preflight facts for BioETL test audits.",
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when reproducibility blockers are present.",
    )
    args = parser.parse_args(argv)

    report = collect_test_audit_preflight(args.root)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.strict and report["blockers"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
