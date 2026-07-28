"""Guardrails for canonical runner-factory helper naming in composition."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COMPOSITION_ROOT = ROOT / "src" / "bioetl" / "composition"


@pytest.mark.architecture
def test_create_runner_from_factory_name_is_owned_by_pipeline_factory_helpers() -> None:
    """Only one composition helper should own the generic create_runner_from_factory name."""
    owners: list[str] = []
    needle = "def create_runner_from_factory("
    for path in sorted(COMPOSITION_ROOT.rglob("*.py")):
        if needle in path.read_text(encoding="utf-8"):
            owners.append(path.relative_to(ROOT).as_posix())

    assert owners == [
        "src/bioetl/composition/factories/pipeline_support/assembler_helpers.py"
    ]
