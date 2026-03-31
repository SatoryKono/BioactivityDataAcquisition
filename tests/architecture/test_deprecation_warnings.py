"""Guardrail: runtime assembly should not retain deprecated FSM bootstrap shims."""

from __future__ import annotations

from pathlib import Path


def test_runner_assembly_has_no_deprecated_fsm_bootstrap_warning() -> None:
    """Composite runner assembly should require explicit FSM helper injection."""
    source = Path(
        "src/bioetl/composition/bootstrap/runtime/runner_assembly.py"
    ).read_text(encoding="utf-8")
    assert "Creating CompositePipelineRunner without fsm_state_helper is deprecated" not in source
    assert "DeprecationWarning" not in source
