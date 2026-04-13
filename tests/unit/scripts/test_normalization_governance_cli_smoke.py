"""Smoke tests for normalization governance CLI entrypoints."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _run_command(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_docs_cli_generate_pipeline_normalization_matrix_help_smoke() -> None:
    result = _run_command(
        "-m",
        "scripts.docs",
        "generate-pipeline-normalization-matrix",
        "--help",
    )

    assert result.returncode == 0, result.stderr
    assert "Generate deterministic normalization field-matrix artifacts" in result.stdout


def test_qa_cli_report_normalization_fallback_inventory_help_smoke() -> None:
    result = _run_command(
        "-m",
        "scripts.qa",
        "report-normalization-fallback-inventory",
        "--help",
    )

    assert result.returncode == 0, result.stderr
    assert "Generate a report-only inventory of fields still using fallback normalization." in result.stdout
