"""Guardrails for deprecation warning policy and retired compatibility shims."""

from __future__ import annotations

import pytest

from pathlib import Path
import tomllib

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"


def _pytest_filterwarnings() -> list[str]:
    payload = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    pytest_options = payload["tool"]["pytest"]["ini_options"]
    filterwarnings = pytest_options["filterwarnings"]
    assert isinstance(filterwarnings, list)
    assert all(isinstance(item, str) for item in filterwarnings)
    return list(filterwarnings)


def _iter_deprecation_warning_ignores() -> list[str]:
    offenders: list[str] = []
    for path in sorted((ROOT / "tests").rglob("test_*.py")):
        rel = path.relative_to(ROOT).as_posix()
        if rel == "tests/architecture/test_deprecation_warnings.py":
            continue
        text = path.read_text(encoding="utf-8")
        if "ignore::DeprecationWarning" in text:
            offenders.append(rel)
        if 'filterwarnings("ignore", category=DeprecationWarning' in text:
            offenders.append(rel)
        if "filterwarnings('ignore', category=DeprecationWarning" in text:
            offenders.append(rel)
    return offenders


def test_pytest_defaults_do_not_globally_ignore_deprecation_warnings() -> None:
    """Deprecation warnings must fail by default outside explicit compat coverage."""
    filterwarnings = _pytest_filterwarnings()

    assert "error" in filterwarnings
    assert "ignore::DeprecationWarning" not in filterwarnings


def test_deprecation_warning_ignores_are_not_hidden_in_test_modules() -> None:
    """Test modules must not silently suppress deprecation warnings."""
    offenders = _iter_deprecation_warning_ignores()
    assert not offenders, (
        "DeprecationWarning ignores must stay local, explicit, and reviewable. "
        "No committed test module should suppress them silently:\n"
        + "\n".join(offenders)
    )


def test_runner_assembly_has_no_deprecated_fsm_bootstrap_warning() -> None:
    """Composite runner assembly should require explicit FSM helper injection."""
    source = (ROOT / Path(
        "src/bioetl/composition/bootstrap/runtime/runner_assembly.py"
    )).read_text(encoding="utf-8")
    assert (
        "Creating CompositePipelineRunner without fsm_state_helper is deprecated"
        not in source
    )
    assert "DeprecationWarning" not in source


def test_composite_application_services_do_not_reintroduce_legacy_aliases() -> None:
    """Composite application helpers should expose canonical service names only."""
    fsm_source = (ROOT / Path("src/bioetl/application/composite/fsm_helper.py")).read_text(
        encoding="utf-8"
    )
    dedup_source = (
        ROOT / Path("src/bioetl/application/composite/deduplication.py")
    ).read_text(
        encoding="utf-8"
    )

    assert "class FSMStateHelper(" not in fsm_source
    assert '"FSMStateHelper"' not in fsm_source
    assert "class EnricherDeduplicator(" not in dedup_source
    assert '"EnricherDeduplicator"' not in dedup_source
