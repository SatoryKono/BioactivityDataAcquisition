from __future__ import annotations

import os
import shutil
from pathlib import Path
import stat
import subprocess
import sys

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "engineering" / "dev" / "pretest_guardrails.sh"


def _bash_executable() -> str:
    """Prefer a working bash; Windows System32 bash may be a broken WSL stub."""
    if os.name == "nt":
        for candidate in (
            Path(r"C:\Program Files\Git\bin\bash.exe"),
            Path(r"C:\Program Files\Git\usr\bin\bash.exe"),
        ):
            if candidate.is_file():
                return str(candidate)
    found = shutil.which("bash")
    if found:
        return found
    pytest.skip("bash is required for pretest_guardrails runtime tests")


def _command(report_path: Path) -> list[str]:
    return [
        _bash_executable(),
        str(SCRIPT),
        "--mode",
        "check",
        "--scope",
        "light",
        "--skip-cleanup",
        "--skip-repo",
        "--skip-docs",
        "--skip-architecture",
        "--skip-memory",
        "--dry-run",
        "--report-json",
        str(report_path),
    ]


def test_pretest_guardrails_accepts_runtime_with_required_yaml(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env["BIOETL_PYTEST_RUNTIME_PYTHON"] = sys.executable

    result = subprocess.run(
        _command(tmp_path / "valid-runtime-report.json"),
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "[pretest-guardrails] OK" in result.stdout


def test_pretest_guardrails_rejects_runtime_without_required_yaml(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "python-without-yaml"
    runtime.write_text(
        "#!/usr/bin/env bash\n"
        'if [[ "${1:-}" == "-c" && "${2:-}" == "import yaml" ]]; then\n'
        "  exit 1\n"
        "fi\n"
        f'exec "{sys.executable}" "$@"\n',
        encoding="utf-8",
    )
    runtime.chmod(runtime.stat().st_mode | stat.S_IXUSR)
    env = os.environ.copy()
    env["BIOETL_PYTEST_RUNTIME_PYTHON"] = str(runtime)

    result = subprocess.run(
        _command(tmp_path / "invalid-runtime-report.json"),
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "cannot import required module 'yaml'" in result.stderr
    assert "[pretest-guardrails] OK" not in result.stdout


@pytest.mark.parametrize("line_ending", ["\n", "\r\n"])
def test_architecture_targets_do_not_leak_line_terminators(line_ending: str) -> None:
    """Configuration line endings must not become part of pytest node IDs."""
    source = SCRIPT.read_text(encoding="utf-8")
    body = source.split("run_architecture_checks() {", 1)[1].split("\n}\n", 1)[0]
    function = "run_architecture_checks() {" + body + "\n}\n"
    target = "tests/architecture/test_generated_artifact_routing.py::test_example"
    env = os.environ.copy()
    env["TARGET_OUTPUT"] = target + line_ending
    harness = (
        "set -euo pipefail\n"
        + function
        + 'config_architecture_targets() { printf "%s" "$TARGET_OUTPUT"; }\n'
        + 'run_step() { printf "%s\\0" "$@"; }\n'
        + "SKIP_ARCHITECTURE=0\nARCHITECTURE_GROUP=fixture\n"
        + "run_architecture_checks\n"
    )
    result = subprocess.run(
        [_bash_executable(), "-c", harness],
        cwd=ROOT,
        env=env,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    arguments = result.stdout.split(b"\0")
    assert target.encode() in arguments
    assert all(b"\r" not in argument for argument in arguments)
