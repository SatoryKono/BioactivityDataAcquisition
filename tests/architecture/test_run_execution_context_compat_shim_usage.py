"""Guardrails for the removed RunExecutionContext compatibility export."""

from __future__ import annotations

from pathlib import Path

import pytest

import bioetl.application.services.cli_run_orchestration_models as legacy_models

ROOT = Path(__file__).resolve().parents[2]
SELF = Path(__file__).resolve()
FORBIDDEN_SYMBOL = "RunExecution" + "Context"


def _iter_symbol_mentions(root: Path) -> list[str]:
    offenders: list[str] = []
    for path in sorted(root.rglob("*.py")):
        if path == SELF:
            continue
        text = path.read_text(encoding="utf-8")
        if FORBIDDEN_SYMBOL in text:
            offenders.append(path.relative_to(ROOT).as_posix())
    return offenders


@pytest.mark.architecture
def test_run_execution_context_compat_export_has_been_removed() -> None:
    """Legacy facade should no longer expose the deprecated execution context name."""
    assert FORBIDDEN_SYMBOL not in legacy_models.__all__
    assert not hasattr(legacy_models, FORBIDDEN_SYMBOL)
    assert FORBIDDEN_SYMBOL not in dir(legacy_models)


@pytest.mark.architecture
def test_run_execution_context_symbol_is_absent_from_first_party_src() -> None:
    """Production code must not reference the removed compatibility symbol."""
    offenders = _iter_symbol_mentions(ROOT / "src")
    assert not offenders, (
        "Removed RunExecutionContext compatibility symbol is still referenced from "
        "src/:\n" + "\n".join(offenders)
    )


@pytest.mark.architecture
def test_run_execution_context_symbol_is_absent_from_tests() -> None:
    """Tests must stay off the removed compatibility symbol as well."""
    offenders = _iter_symbol_mentions(ROOT / "tests")
    assert not offenders, (
        "Removed RunExecutionContext compatibility symbol is still referenced from "
        "tests/:\n" + "\n".join(offenders)
    )
