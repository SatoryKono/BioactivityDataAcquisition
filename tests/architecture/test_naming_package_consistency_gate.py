"""Architecture checks for naming/package consistency pre-merge gate."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType

from tests.helpers import run_repo_python


def _load_consistency_gate_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[2]
    module_path = (
        repo_root
        / "scripts"
        / "engineering"
        / "qa"
        / "check_naming_package_consistency.py"
    )
    spec = importlib.util.spec_from_file_location(
        "check_naming_package_consistency_runtime", module_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_naming_package_consistency_runtime"] = module
    spec.loader.exec_module(module)
    return module


def test_consistency_gate_script_runs_clean_in_check_mode() -> None:
    """Consistency gate should stay stable on the current repository baseline."""
    repo_root = Path(__file__).resolve().parents[2]
    script = (
        repo_root
        / "scripts"
        / "engineering"
        / "qa"
        / "check_naming_package_consistency.py"
    )
    assert script.exists(), (
        "scripts/engineering/qa/check_naming_package_consistency.py must exist"
    )

    result = run_repo_python(str(script), "--check", cwd=repo_root)
    if result.returncode == 0:
        return

    assert result.returncode == 0, (
        "Naming/package consistency gate must stay clean on the current baseline.\n"
        f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
    )


def test_consistency_gate_references_canonical_naming_audit_path() -> None:
    """The gate must stay wired to the canonical engineering QA naming audit."""
    repo_root = Path(__file__).resolve().parents[2]
    script = (
        repo_root
        / "scripts"
        / "engineering"
        / "qa"
        / "check_naming_package_consistency.py"
    )
    source = script.read_text(encoding="utf-8")
    assert "scripts/qa/naming_audit.py" not in source

    module = _load_consistency_gate_module()
    assert module.CANONICAL_NAMING_AUDIT_PATH.as_posix() == (
        "scripts/engineering/qa/naming_audit.py"
    )


def test_tests_workflow_runs_naming_package_consistency_gate() -> None:
    """Pre-merge tests workflow must run the consistency gate."""
    repo_root = Path(__file__).resolve().parents[2]
    workflow = (repo_root / ".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "Pre-merge naming/package consistency gate" in workflow
    assert "python -m scripts.engineering.qa check-naming-pkg --check" in workflow
