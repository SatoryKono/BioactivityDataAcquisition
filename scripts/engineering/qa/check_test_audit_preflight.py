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

GitRunner = Callable[[list[str]], subprocess.CompletedProcess[str]]


def _default_git_runner(root: Path) -> GitRunner:
    def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )

    return _run


def _git_value(runner: GitRunner, args: list[str]) -> dict[str, Any]:
    result = runner(args)
    return {
        "ok": result.returncode == 0,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "returncode": result.returncode,
    }


def _detect_default_branch(runner: GitRunner) -> str:
    remote_head = _git_value(
        runner,
        ["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"],
    )
    if remote_head["ok"] and remote_head["stdout"].startswith("origin/"):
        return str(remote_head["stdout"]).split("/", 1)[1]
    return "main"


def _scan_lfs_pointer_files(root: Path) -> list[str]:
    vcr_root = root / VCR_FIXTURE_ROOT
    if not vcr_root.exists():
        return []

    pointer_files: list[str] = []
    for path in sorted(vcr_root.rglob("*")):
        if not path.is_file():
            continue
        try:
            if path.read_bytes()[: len(LFS_POINTER_PREFIX)] == LFS_POINTER_PREFIX:
                pointer_files.append(path.relative_to(root).as_posix())
        except OSError:
            continue
    return pointer_files


def collect_test_audit_preflight(
    root: Path = ROOT,
    *,
    runner: GitRunner | None = None,
    git_lfs_path: str | None = None,
) -> dict[str, Any]:
    """Collect preflight facts needed before treating an audit as reproducible."""
    root = root.resolve()
    git_runner = runner or _default_git_runner(root)
    lfs_path = git_lfs_path if git_lfs_path is not None else shutil.which("git-lfs")

    current_branch = _git_value(git_runner, ["branch", "--show-current"])
    current_commit = _git_value(git_runner, ["rev-parse", "--short", "HEAD"])
    default_branch = _detect_default_branch(git_runner)
    default_commit = _git_value(git_runner, ["rev-parse", "--short", default_branch])
    git_status = _git_value(git_runner, ["status", "--short", "--untracked-files=no"])

    baseline_path = root / TELEMETRY_BASELINE
    baseline_exists = baseline_path.exists()
    baseline_text = (
        baseline_path.read_text(encoding="utf-8") if baseline_exists else ""
    )
    baseline_has_coverage = "Actual coverage:" in baseline_text
    lfs_pointer_files = _scan_lfs_pointer_files(root)

    blockers: list[dict[str, str]] = []
    if not lfs_path:
        blockers.append(
            {
                "id": "missing_git_lfs",
                "message": "git-lfs is required before comparing main-branch audit evidence.",
            }
        )
    if not git_status["ok"]:
        blockers.append(
            {
                "id": "git_status_failed",
                "message": git_status["stderr"] or "git status failed.",
            }
        )
    if not baseline_exists:
        blockers.append(
            {
                "id": "missing_telemetry_baseline",
                "message": f"Missing {TELEMETRY_BASELINE.as_posix()}.",
            }
        )
    if baseline_exists and not baseline_has_coverage:
        blockers.append(
            {
                "id": "telemetry_baseline_without_coverage",
                "message": "Telemetry baseline exists but does not expose Actual coverage.",
            }
        )

    return {
        "root": root.as_posix(),
        "current_branch": current_branch,
        "current_commit": current_commit,
        "default_branch": default_branch,
        "default_commit": default_commit,
        "git_status": git_status,
        "git_lfs": {
            "available": bool(lfs_path),
            "path": lfs_path,
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
