from __future__ import annotations

import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "engineering" / "dev" / "pretest_guardrails.sh"


def _command(report_path: Path) -> list[str]:
    return [
        "bash",
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
