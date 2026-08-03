# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Guardrails for the removed RunExecutionContext compatibility shim."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SELF = Path(__file__).resolve()
REMOVED_COMPAT_MODULE = "bioetl.application.services.cli_run_orchestration_models"
REMOVED_COMPAT_FILE = (
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "services"
    / "cli_run_orchestration_models.py"
)
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
def test_run_execution_context_compat_module_has_been_removed() -> None:
    """Legacy execution-context shim module must stay removed."""
    assert not REMOVED_COMPAT_FILE.exists()
    with pytest.raises(ModuleNotFoundError):
        import_module(REMOVED_COMPAT_MODULE)


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
