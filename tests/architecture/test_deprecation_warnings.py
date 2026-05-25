"""Guardrail: runtime assembly should not retain deprecated FSM bootstrap shims."""

from __future__ import annotations

from pathlib import Path


def test_runner_assembly_has_no_deprecated_fsm_bootstrap_warning() -> None:
    """Composite runner assembly should require explicit FSM helper injection."""
    source = Path(
        "src/bioetl/composition/bootstrap/runtime/runner_assembly.py"
    ).read_text(encoding="utf-8")
    assert (
        "Creating CompositePipelineRunner without fsm_state_helper is deprecated"
        not in source
    )
    assert "DeprecationWarning" not in source


def test_composite_application_services_do_not_reintroduce_legacy_aliases() -> None:
    """Composite application helpers should expose canonical service names only."""
    fsm_source = Path("src/bioetl/application/composite/fsm_helper.py").read_text(
        encoding="utf-8"
    )
    dedup_source = Path("src/bioetl/application/composite/deduplication.py").read_text(
        encoding="utf-8"
    )

    assert "class FSMStateHelper(" not in fsm_source
    assert '"FSMStateHelper"' not in fsm_source
    assert "class EnricherDeduplicator(" not in dedup_source
    assert '"EnricherDeduplicator"' not in dedup_source
