#!/usr/bin/env python3
"""Run read-only architecture audit evidence checks without pretest sync."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
GIT_STATUS_TIMEOUT_SECONDS = 120
QA_MODULE = "scripts.engineering.qa"
IMPORT_LINTER_CONFIG = ".importlinter"

MUTATION_GUARD_PATHS = (
    ".github",
    "configs/quality",
    "docs",
    "reports/quality",
    "scripts",
    "src/bioetl",
    "tests",
)


@dataclass(frozen=True, slots=True)
class ArchitectureAuditCheck:
    """One read-only architecture audit command."""

    name: str
    command: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ArchitectureAuditCheckResult:
    """Result for one read-only architecture audit command."""

    name: str
    command: tuple[str, ...]
    returncode: int
    duration_seconds: float
    stdout_tail: str
    stderr_tail: str

    @property
    def status(self) -> str:
        return "pass" if self.returncode == 0 else "fail"


def _tail(value: str, *, max_lines: int = 30) -> str:
    lines = value.splitlines()
    return "\n".join(lines[-max_lines:])


def _timeout_stream_text(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return str(value or "")


def _lint_imports_command(repo_root: Path) -> tuple[str, ...]:
    venv_candidate = repo_root / ".venv" / "bin" / "lint-imports"
    if venv_candidate.exists():
        return (str(venv_candidate), "--config", IMPORT_LINTER_CONFIG)
    active_venv_candidate = Path(sys.executable).with_name("lint-imports")
    if active_venv_candidate.exists():
        return (str(active_venv_candidate), "--config", IMPORT_LINTER_CONFIG)
    discovered = shutil.which("lint-imports") or "lint-imports"
    return (discovered, "--config", IMPORT_LINTER_CONFIG)


def architecture_audit_checks(
    repo_root: Path = PROJECT_ROOT,
) -> tuple[ArchitectureAuditCheck, ...]:
    """Return the canonical read-only architecture audit command set."""
    python = sys.executable
    return (
        ArchitectureAuditCheck(
            name="import_linter_contracts",
            command=_lint_imports_command(repo_root),
        ),
        ArchitectureAuditCheck(
            name="runtime_import_scc",
            command=(
                python,
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                "tests/architecture/test_runtime_import_scc.py",
                "-q",
            ),
        ),
        ArchitectureAuditCheck(
            name="module_coverage_inventory",
            command=(
                python,
                "-m",
                QA_MODULE,
                "report-module-coverage",
                "--check",
                "--allow-missing-coverage-xml",
            ),
        ),
        ArchitectureAuditCheck(
            name="hotspot_family_baseline",
            command=(
                python,
                "-m",
                QA_MODULE,
                "report-family-baseline",
                "--check",
            ),
        ),
        ArchitectureAuditCheck(
            name="contract_coverage_matrix",
            command=(
                python,
                "-m",
                QA_MODULE,
                "report-contract-coverage-matrix",
                "--check",
            ),
        ),
        ArchitectureAuditCheck(
            name="domain_io_taint_inventory",
            command=(
                python,
                "-m",
                QA_MODULE,
                "report-domain-io-taint-inventory",
                "--check",
            ),
        ),
        ArchitectureAuditCheck(
            name="port_adapter_factory_coverage",
            command=(
                python,
                "-m",
                QA_MODULE,
                "report-port-adapter-factory-coverage",
                "--check",
            ),
        ),
        ArchitectureAuditCheck(
            name="observability_metric_inventory",
            command=(
                python,
                "-m",
                QA_MODULE,
                "report-observability-metric-inventory",
                "--check",
                "--json",
                "--allow-local-cardinality-fallback",
            ),
        ),
        ArchitectureAuditCheck(
            name="domain_aggregate_invariant_registry",
            command=(
                python,
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                "tests/architecture/test_domain_aggregate_invariant_registry.py",
                "-q",
            ),
        ),
        ArchitectureAuditCheck(
            name="remote_main_debt_baseline",
            command=(
                python,
                "-m",
                QA_MODULE,
                "report-architecture-debt-remote-main-baseline",
                "--check",
            ),
        ),
        ArchitectureAuditCheck(
            name="debt_governance_gates",
            command=(
                python,
                "-m",
                QA_MODULE,
                "report-debt-governance-gates",
                "--check",
            ),
        ),
    )


def _git_tracked_status(
    repo_root: Path,
    *,
    paths: tuple[str, ...] = MUTATION_GUARD_PATHS,
    timeout_seconds: int = GIT_STATUS_TIMEOUT_SECONDS,
) -> tuple[str, ...]:
    try:
        result = subprocess.run(
            list(_git_status_command(paths)),
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return (
            "<git-status-timeout>",
            _tail(_timeout_stream_text(exc.stderr)),
        )
    if result.returncode != 0:
        return (f"<git-status-failed:{result.returncode}>", _tail(result.stderr))
    return tuple(line for line in result.stdout.splitlines() if line.strip())


def _git_status_unavailable(status: tuple[str, ...]) -> bool:
    """Return whether the mutation guard failed to inspect tracked status."""
    return bool(status) and status[0].startswith("<git-status-")


def _git_status_command(paths: tuple[str, ...]) -> tuple[str, ...]:
    """Build a tracked-status command that cannot invoke Git LFS clean filters."""
    return (
        "git",
        "-c",
        "filter.lfs.clean=",
        "-c",
        "filter.lfs.smudge=",
        "-c",
        "filter.lfs.process=",
        "-c",
        "filter.lfs.required=false",
        "status",
        "--short",
        "--untracked-files=no",
        "--",
        *paths,
    )


def _run_check(
    check: ArchitectureAuditCheck,
    *,
    repo_root: Path,
    timeout_seconds: int,
    env: dict[str, str],
) -> ArchitectureAuditCheckResult:
    started_at = time.monotonic()
    try:
        result = subprocess.run(
            list(check.command),
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = _timeout_stream_text(exc.stdout)
        stderr = _timeout_stream_text(exc.stderr)
        return ArchitectureAuditCheckResult(
            name=check.name,
            command=check.command,
            returncode=124,
            duration_seconds=round(time.monotonic() - started_at, 3),
            stdout_tail=_tail(stdout),
            stderr_tail=_tail(stderr or f"Timed out after {timeout_seconds}s"),
        )
    return ArchitectureAuditCheckResult(
        name=check.name,
        command=check.command,
        returncode=result.returncode,
        duration_seconds=round(time.monotonic() - started_at, 3),
        stdout_tail=_tail(result.stdout),
        stderr_tail=_tail(result.stderr),
    )


def _architecture_audit_environment(
    repo_root: Path,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build a src-layout child environment without discarding caller settings."""
    env = dict(os.environ if environ is None else environ)
    src_path = str((repo_root / "src").resolve())
    caller_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{src_path}{os.pathsep}{caller_pythonpath}" if caller_pythonpath else src_path
    )
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run_architecture_audit_read_only(
    *,
    repo_root: Path = PROJECT_ROOT,
    timeout_seconds: int = 240,
) -> dict[str, object]:
    """Run architecture evidence checks and fail if tracked files mutate."""
    repo_root = repo_root.resolve()
    env = _architecture_audit_environment(repo_root)

    before_status = _git_tracked_status(repo_root)
    results = [
        _run_check(
            check,
            repo_root=repo_root,
            timeout_seconds=timeout_seconds,
            env=env,
        )
        for check in architecture_audit_checks(repo_root)
    ]
    after_status = _git_tracked_status(repo_root)
    mutation_detected = before_status != after_status
    mutation_status_unavailable = _git_status_unavailable(
        before_status
    ) or _git_status_unavailable(after_status)
    mutation_guard_failed = mutation_status_unavailable or mutation_detected
    return {
        "schema_version": 1,
        "generated_by": "scripts.engineering.qa.run_architecture_audit_read_only",
        "read_only": True,
        "mutation_guard_paths": list(MUTATION_GUARD_PATHS),
        "mutation_guard": {
            "status": "fail" if mutation_guard_failed else "pass",
            "before": list(before_status),
            "after": list(after_status),
            "status_unavailable": mutation_status_unavailable,
        },
        "checks": [{**asdict(result), "status": result.status} for result in results],
        "summary": {
            "check_count": len(results),
            "pass_count": sum(1 for result in results if result.returncode == 0),
            "fail_count": sum(1 for result in results if result.returncode != 0),
            "mutation_detected": mutation_detected,
            "mutation_status_unavailable": mutation_status_unavailable,
        },
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--timeout-seconds", type=int, default=240)
    parser.add_argument("--json", action="store_true", help="Emit JSON payload.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    payload = run_architecture_audit_read_only(
        repo_root=args.repo_root,
        timeout_seconds=args.timeout_seconds,
    )
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        summary = payload["summary"]
        assert isinstance(summary, dict)
        print(
            "[architecture-audit-read-only] "
            f"checks={summary['check_count']}; "
            f"pass={summary['pass_count']}; "
            f"fail={summary['fail_count']}; "
            f"mutation_detected={summary['mutation_detected']}"
        )
        checks = payload["checks"]
        if not isinstance(checks, list):
            raise ValueError("architecture audit checks must be a list")
        for check in checks:
            assert isinstance(check, dict)
            print(
                "[architecture-audit-read-only] "
                f"{check['name']}: {check['status']} "
                f"({check['duration_seconds']}s)"
            )
    summary = payload["summary"]
    assert isinstance(summary, dict)
    mutation_guard = payload["mutation_guard"]
    assert isinstance(mutation_guard, dict)
    return 0 if summary["fail_count"] == 0 and mutation_guard["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
