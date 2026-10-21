"""Contract for the shipped local ``make test-benchmark`` caller."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]

ROOT = Path(__file__).resolve().parents[6]
MAKEFILE = ROOT / "Makefile"
GUARD_PLUGIN = "tests.benchmarks.benchmark_vcs_guard"


def _target_recipe(name: str) -> str:
    """Return one Makefile target body, including line continuations."""
    lines = MAKEFILE.read_text(encoding="utf-8").splitlines()
    start = lines.index(f"{name}:")
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line and not line.startswith(("\t", " ")):
            break
        body.append(line)
    return "\n".join(body)


def test_makefile_benchmark_target_is_phony_and_documented() -> None:
    """The target is a real phony goal and appears in ``make help``."""
    text = MAKEFILE.read_text(encoding="utf-8")
    phony = next(
        line
        for line in text.splitlines()
        if line.startswith(".PHONY:") and "test-benchmark" in line
    )
    assert " test-benchmark " in f" {phony} "
    assert "make test-benchmark" in text


def test_makefile_benchmark_target_loads_guard_before_plugin() -> None:
    """The local caller matches the nightly measurement contract."""
    recipe = _target_recipe("test-benchmark")
    command = " ".join(
        line.strip().removesuffix("\\").strip() for line in recipe.splitlines()
    )

    assert "mkdir -p reports/performance" in command
    assert "BIOETL_BENCHMARK_CALLER=local-makefile" in command
    assert "BIOETL_BENCHMARK_DATASET=bioetl-synthetic-benchmarks-v1" in command
    assert "$(RUN) pytest tests/benchmarks/" in command
    assert "-m benchmark" in command
    assert "-p no:xdist" in command
    assert "--benchmark-json=reports/performance/benchmark-measurements.json" in command
    assert "tests/performance/" not in command
    assert "-p no:benchmark" not in command
    assert command.index(f"-p {GUARD_PLUGIN}") < command.index("-p benchmark")
