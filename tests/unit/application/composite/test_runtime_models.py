"""Unit tests for canonical composite runtime models."""

from __future__ import annotations

from pathlib import Path

from bioetl.application.composite.runtime_models import (
    CompositeRunnerDependencies,
    CompositeExecutionContext,
    CompositeRuntimeConfig,
)


def test_runtime_models_exports_stable_symbols() -> None:
    """Stable runtime module should own the canonical orchestration models."""
    assert CompositeRuntimeConfig.__name__ == "CompositeRuntimeConfig"
    assert CompositeExecutionContext.__name__ == "CompositeExecutionContext"
    assert CompositeRunnerDependencies.__name__ == "CompositeRunnerDependencies"


def test_first_party_src_does_not_reference_removed_dependency_group_alias() -> None:
    """Composite application code should use only the canonical dependency name."""
    root = Path(__file__).resolve().parents[4] / "src" / "bioetl"
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "CompositeRunnerDependencyGroup" in text:
            offenders.append(str(path.relative_to(root.parent.parent)))

    assert offenders == []
