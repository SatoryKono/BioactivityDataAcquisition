"""Produce the 17 blocking coverage shards locally, without a CI service.

Run with the project's Python environment from a clean checkout. Raw SQLite
coverage files stay on the local temporary filesystem, which avoids SQLite
locking on Windows-mounted WSL checkouts. A failed or incomplete run never
publishes a combined XML report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree

from scripts.engineering.qa.report_module_coverage_inventory import (
    compute_source_tree_sha256,
)
from scripts.engineering.ci.local_test_telemetry import junit_telemetry_sha256
from scripts.engineering.ci.update_test_telemetry_baseline import (
    compute_test_telemetry_source_tree_sha256,
)

ROOT = Path(__file__).resolve().parents[3]
COMMON_UNIT_MARKER = (
    "not serial and not memory and not fs_contract and not subprocess_backed"
)
TOOLING_MARKER = "not slow and not benchmark and not memory"
REPO_BACKED_MARKER = "repo_backed and not slow and not benchmark and not memory"


@dataclass(frozen=True)
class Shard:
    name: str
    paths: tuple[str, ...]
    marker: str
    parallel: bool = False


SHARDS = (
    Shard("smoke", ("tests/smoke/",), "not memory"),
    Shard(
        "contract-confidence",
        ("tests/contract/", "tests/unit/contracts/"),
        "no_api or not network",
    ),
    Shard(
        "repo-backed-unit-product",
        (
            "tests/unit/repo_backed/application/",
            "tests/unit/repo_backed/composition/",
            "tests/unit/repo_backed/contracts/",
            "tests/unit/repo_backed/coverage_gap/",
            "tests/unit/repo_backed/domain/",
            "tests/unit/repo_backed/infrastructure/",
            "tests/unit/repo_backed/interfaces/",
        ),
        REPO_BACKED_MARKER,
    ),
    Shard(
        "repo-backed-unit-tooling",
        (
            "tests/unit/repo_backed/scripts/",
            "tests/unit/repo_backed/tools/",
            "--ignore=tests/unit/repo_backed/scripts/ops/",
        ),
        REPO_BACKED_MARKER,
    ),
    Shard(
        "repo-backed-unit-ops",
        ("tests/unit/repo_backed/scripts/ops/",),
        REPO_BACKED_MARKER,
    ),
    Shard(
        "unit-scripts-tooling-passport",
        ("tests/unit/scripts/docs/passports/",),
        TOOLING_MARKER,
    ),
    Shard(
        "unit-scripts-tooling-debt-governance",
        ("tests/unit/scripts/qa/test_report_debt_governance_gates.py",),
        TOOLING_MARKER,
    ),
    Shard(
        "unit-scripts-tooling-other",
        (
            "tests/unit/scripts/",
            "--ignore=tests/unit/scripts/docs/passports/",
            "--ignore=tests/unit/scripts/qa/test_report_debt_governance_gates.py",
        ),
        TOOLING_MARKER,
    ),
    Shard(
        "unit-filesystem-contracts",
        ("tests/unit/",),
        "fs_contract and not slow and not benchmark and not memory",
    ),
    Shard(
        "unit-subprocess-backed",
        (
            "tests/unit/",
            "--ignore=tests/unit/scripts/",
            "--ignore=tests/unit/repo_backed/",
        ),
        "subprocess_backed and not slow and not benchmark and not memory",
    ),
    Shard("unit-domain", ("tests/unit/domain/",), COMMON_UNIT_MARKER, True),
    Shard("unit-application", ("tests/unit/application/",), COMMON_UNIT_MARKER, True),
    Shard(
        "unit-infrastructure", ("tests/unit/infrastructure/",), COMMON_UNIT_MARKER, True
    ),
    Shard(
        "unit-other",
        (
            "tests/unit/",
            "--ignore=tests/unit/domain/",
            "--ignore=tests/unit/application/",
            "--ignore=tests/unit/infrastructure/",
            "--ignore=tests/unit/repo_backed/",
            "--ignore=tests/unit/scripts/",
        ),
        COMMON_UNIT_MARKER,
        True,
    ),
    Shard("integration", ("tests/integration/",), COMMON_UNIT_MARKER),
    Shard("security", ("tests/security/",), COMMON_UNIT_MARKER, True),
    Shard(
        "serial",
        (
            "tests/",
            "--ignore=tests/e2e/",
            "--ignore=tests/contract/",
        ),
        "serial and not e2e and not benchmark and not memory",
    ),
)


def _measurement_environment() -> dict[str, str]:
    """Keep temporary Git fixtures independent of the caller's repository."""
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    env["WSLENV"] = ":".join(
        entry
        for entry in env.get("WSLENV", "").split(":")
        if entry and not entry.split("/")[0].startswith("GIT_")
    )
    return env


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _bash_safe_path(path: Path) -> str:
    """Render *path* for argv/env consumed through MSYS bash.

    ``bash`` on Windows converts ``X:/abs`` argv and env values into relative
    ``X︰`` subtrees under the CWD, which previously scattered mangled junit
    and .coverage files across the repo root. Paths under ROOT are emitted
    relative (no drive prefix, no conversion); out-of-tree paths keep their
    POSIX spelling as a best-effort fallback.
    """
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _windows_bash() -> str:
    """Resolve a Windows Git-bash for shard runners.

    Bare ``bash`` resolves through the Windows PATH inside ``subprocess``,
    where ``C:\\Windows\\System32\\bash.exe`` (the WSL launcher) wins over Git
    Bash. WSL does not inherit lane env vars (COVERAGE_FILE,
    BIOETL_PYTEST_RUNTIME_PYTHON, skip flags), which drops coverage and sends
    shards down the ``uv run`` fallback. Prefer an explicit override and Git's
    own bin directories before PATH lookup.
    """
    override = os.environ.get("BIOETL_LANE_BASH")
    candidates = [override] if override else []
    git = shutil.which("git")
    if git:
        git_root = Path(git).resolve().parent.parent
        candidates.extend(
            str(git_root / name)
            for name in ("bin/bash.exe", "usr/bin/bash.exe", "mingw64/bin/bash.exe")
        )
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    candidates.extend(
        str(Path(program_files) / suffix)
        for suffix in (
            Path("Git/bin/bash.exe"),
            Path("Git/usr/bin/bash.exe"),
            Path("Git/mingw64/bin/bash.exe"),
        )
    )
    for candidate in candidates:
        if (
            candidate
            and "system32" not in candidate.lower()
            and Path(candidate).is_file()
        ):
            return candidate
    return "bash"


def _command(shard: Shard, junit: Path) -> list[str]:
    command = [
        _windows_bash(),
        "scripts/engineering/dev/run_pytest.sh",
        "--narrow",
        *shard.paths,
        "-m",
        shard.marker,
        "--with-coverage",
        "--cov-report=",
        "--timeout=300",
        "-p",
        "no:cacheprovider",
        f"--junitxml={_bash_safe_path(junit)}",
    ]
    if shard.parallel:
        command.extend(("-n", "2", "--dist=loadscope", "--max-worker-restart=0"))
    else:
        command.extend(("-p", "no:xdist"))
    return command


def _write_manifest(path: Path, payload: dict[str, object]) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _run_logged(command: list[str], log: Path, *, env: dict[str, str]) -> int:
    with log.open("w", encoding="utf-8") as stream:
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            stdout=stream,
            stderr=subprocess.STDOUT,
            check=False,
        )
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list", action="store_true", help="Print the local 17-shard plan"
    )
    parser.add_argument(
        "--scratch-dir",
        type=Path,
        help="New empty run directory (default: system temp)",
    )
    args = parser.parse_args(argv)
    if len(SHARDS) != 17 or len({shard.name for shard in SHARDS}) != 17:
        raise RuntimeError("Local coverage plan must have 17 distinct shards")
    if args.list:
        for shard in SHARDS:
            print(f"{shard.name}: {' '.join(_command(shard, Path('<junit>')))}")
        return 0

    if _git(
        "status",
        "--porcelain",
        "--",
        "src/bioetl",
        "tests",
        "scripts/engineering/qa",
        "scripts/engineering/ci",
        "pyproject.toml",
        "configs/quality/test_matrix.yaml",
        ".github/workflows/tests.yml",
    ):
        raise RuntimeError(
            "Source, tests, and coverage runner must be committed before measurement"
        )
    head = _git("rev-parse", "HEAD")
    source_sha = compute_source_tree_sha256(repo_root=ROOT)
    test_sha = compute_test_telemetry_source_tree_sha256(repo_root=ROOT)
    if args.scratch_dir:
        scratch = args.scratch_dir.resolve()
        scratch.mkdir(parents=True, exist_ok=False)
    else:
        scratch = Path(tempfile.mkdtemp(prefix="bioetl-local-coverage-"))
    shards_dir = scratch / "shards"
    junit_dir = scratch / "junit"
    logs_dir = scratch / "logs"
    for directory in (shards_dir, junit_dir, logs_dir):
        directory.mkdir()
    manifest_path = scratch / "manifest.json"
    manifest: dict[str, object] = {
        "schema_version": 1,
        "producer": "run_local_coverage_verify.py",
        "head": head,
        "source_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "source_tree_sha256": source_sha,
        "test_tree_sha256": test_sha,
        "started_at_utc": datetime.now(UTC).isoformat(),
        "python": sys.version.split()[0],
        "scratch_dir": str(scratch),
        "required_shards": [shard.name for shard in SHARDS],
        "shards": [],
        "complete": False,
    }
    _write_manifest(manifest_path, manifest)
    print(
        f"[local-coverage] HEAD={head} source={source_sha} scratch={scratch}",
        flush=True,
    )
    env = _measurement_environment()
    env.update(
        {
            # MSYS bash resolves forward-slash drive paths; backslashes in
            # sys.executable break `[[ -x "$BIN" ]]` and fall through to `uv run`.
            "BIOETL_PYTEST_RUNTIME_PYTHON": Path(sys.executable).as_posix(),
            "BIOETL_AI_MEMORY_MODE": "off",
            "BIOETL_SKIP_PREFLIGHT": "1",
            "HYPOTHESIS_DATABASE": str(scratch / "hypothesis"),
            "PYTHONPYCACHEPREFIX": str(scratch / "pycache"),
        }
    )
    # When shards run through the WSL launcher only variables named in WSLENV
    # cross the boundary; plain Windows env vars are dropped, which previously
    # made every shard write a throwaway `.coverage` in the checkout root.
    wslenv_entries = [entry for entry in env.get("WSLENV", "").split(":") if entry]
    for entry in (
        "COVERAGE_FILE",
        "BIOETL_SKIP_PREFLIGHT",
        "BIOETL_SKIP_SETUP_PLUGINS",
        "BIOETL_AI_MEMORY_MODE",
        "HYPOTHESIS_DATABASE/p",
        "PYTHONPYCACHEPREFIX/p",
    ):
        if not any(e.split("/")[0] == entry.split("/")[0] for e in wslenv_entries):
            wslenv_entries.append(entry)
    env["WSLENV"] = ":".join(wslenv_entries)
    for shard in SHARDS:
        coverage_file = shards_dir / f".coverage.{shard.name}"
        junit = junit_dir / f"{shard.name}.xml"
        log = logs_dir / f"{shard.name}.log"
        command = _command(shard, junit)
        env["COVERAGE_FILE"] = _bash_safe_path(coverage_file)
        print(f"[local-coverage] start {shard.name}", flush=True)
        started = time.monotonic()
        exit_code = _run_logged(command, log, env=env)
        row = {
            "name": shard.name,
            "command": command,
            "exit_code": exit_code,
            "seconds": round(time.monotonic() - started, 2),
            "coverage_file": str(coverage_file),
            "coverage_sha256": (
                _sha256(coverage_file)
                if coverage_file.is_file() and coverage_file.stat().st_size > 0
                else None
            ),
            "junit_file": str(junit) if junit.is_file() else None,
            "junit_telemetry_sha256": junit_telemetry_sha256(junit)
            if junit.is_file()
            else None,
            "log_file": str(log),
        }
        assert isinstance(manifest["shards"], list)
        manifest["shards"].append(row)
        _write_manifest(manifest_path, manifest)
        print(
            f"[local-coverage] {shard.name} exit={exit_code} coverage={'yes' if row['coverage_sha256'] else 'no'}",
            flush=True,
        )

    if (
        _git("rev-parse", "HEAD") != head
        or (compute_test_telemetry_source_tree_sha256(repo_root=ROOT) != test_sha)
        or compute_source_tree_sha256(repo_root=ROOT) != source_sha
        or _git(
            "status",
            "--porcelain",
            "--",
            "src/bioetl",
            "tests",
            "scripts/engineering/qa",
            "scripts/engineering/ci",
            "pyproject.toml",
            "configs/quality/test_matrix.yaml",
            ".github/workflows/tests.yml",
        )
    ):
        print(
            "[local-coverage] source or test tree changed during measurement",
            file=sys.stderr,
        )
        return 1
    rows = manifest["shards"]
    assert isinstance(rows, list)
    if any(
        row["exit_code"] != 0 or not row["coverage_sha256"] or not row["junit_file"]
        for row in rows
    ):
        print(
            f"[local-coverage] incomplete; evidence: {manifest_path}", file=sys.stderr
        )
        return 1

    combined = scratch / "combined"
    combined.mkdir()
    env["COVERAGE_FILE"] = str(combined / ".coverage")
    combine_log = logs_dir / "combine.log"
    if (
        _run_logged(
            [sys.executable, "-m", "coverage", "combine", "--keep", str(shards_dir)],
            combine_log,
            env=env,
        )
        != 0
    ):
        print(f"[local-coverage] combine failed: {combine_log}", file=sys.stderr)
        return 1
    xml = scratch / "coverage.xml"
    xml_log = logs_dir / "xml.log"
    if (
        _run_logged(
            [sys.executable, "-m", "coverage", "xml", "-o", str(xml)], xml_log, env=env
        )
        != 0
    ):
        print(f"[local-coverage] XML failed: {xml_log}", file=sys.stderr)
        return 1
    line_log = logs_dir / "line-gate.log"
    line_exit = _run_logged(
        [sys.executable, "-m", "coverage", "report", "--fail-under=85"],
        line_log,
        env=env,
    )
    branch_log = logs_dir / "branch-gate.log"
    branch_exit = _run_logged(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa",
            "check-branch-coverage",
            "--coverage-xml",
            str(xml),
            "--min-percent",
            "85",
        ],
        branch_log,
        env=env,
    )
    root = ElementTree.parse(xml).getroot()
    manifest.update(
        {
            "coverage_xml": str(xml),
            "coverage_xml_sha256": _sha256(xml),
            "line_percent": round(float(root.attrib["line-rate"]) * 100, 2),
            "branch_percent": round(float(root.attrib["branch-rate"]) * 100, 2),
            "line_gate_exit_code": line_exit,
            "branch_gate_exit_code": branch_exit,
            "complete": line_exit == 0 and branch_exit == 0,
            "finished_at_utc": datetime.now(UTC).isoformat(),
        }
    )
    _write_manifest(manifest_path, manifest)
    print(
        f"[local-coverage] complete={manifest['complete']} evidence={manifest_path}",
        flush=True,
    )
    return 0 if manifest["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
