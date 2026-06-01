"""Unit tests for canonical composite runtime models."""

from __future__ import annotations

import pytest

import os
from pathlib import Path

from bioetl.application.composite.runtime_models import (
    CompositeRunnerDependencies,
    CompositeExecutionContext,
    CompositeRuntimeConfig,
)


pytestmark = pytest.mark.unit

def test_runtime_models_exports_stable_symbols() -> None:
    """Stable runtime module should own the canonical orchestration models."""
    assert CompositeRuntimeConfig.__name__ == "CompositeRuntimeConfig"
    assert CompositeExecutionContext.__name__ == "CompositeExecutionContext"
    assert CompositeRunnerDependencies.__name__ == "CompositeRunnerDependencies"


def _file_contains_bytes(path: Path, needle: bytes, *, chunk_size: int = 65536) -> bool:
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            if needle in chunk:
                return True
    return False


def test_first_party_src_does_not_reference_removed_dependency_group_alias() -> None:
    """Composite application code should use only the canonical dependency name."""
    root = (
        Path(__file__).resolve().parents[4]
        / "src"
        / "bioetl"
        / "application"
        / "composite"
    )
    needle = b"CompositeRunnerDependencyGroup"
    offenders: list[str] = []
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            path = Path(dirpath) / filename
            if _file_contains_bytes(path, needle):
                offenders.append(str(path.relative_to(root.parents[2])))

    assert offenders == []
