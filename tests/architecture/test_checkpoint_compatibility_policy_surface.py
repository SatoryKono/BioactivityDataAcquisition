"""Guardrails for active checkpoint compatibility policy surfaces."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ACTIVE_SURFACES = (
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "core"
    / "lifecycle"
    / "checkpoint_runtime.py",
    ROOT / "src" / "bioetl" / "infrastructure" / "config" / "_base.py",
    ROOT
    / "src"
    / "bioetl"
    / "composition"
    / "factories"
    / "pipeline"
    / "checkpoint_policy_helpers.py",
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "services"
    / "control_plane"
    / "run_manifest_reproducibility_scoring.py",
    ROOT / "docs" / "04-reference" / "cli.md",
)


@pytest.mark.architecture
def test_active_checkpoint_policy_surfaces_do_not_expose_removed_legacy_modes() -> None:
    forbidden_tokens = (
        "legacy_observe",
        "legacy_observe_loaded_degraded",
        "legacy_missing_context_loaded_degraded",
    )
    violations: list[str] = []
    for path in ACTIVE_SURFACES:
        text = path.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            if token in text:
                violations.append(f"{path.relative_to(ROOT)}: {token}")

    assert not violations, (
        "Active checkpoint compatibility surfaces must not expose removed legacy "
        "modes:\n" + "\n".join(violations)
    )
