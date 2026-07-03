"""Architecture tests for diagram quality budget output-path hardening."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


pytestmark = pytest.mark.architecture


def _load_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[2]
    module_path = (
        repo_root / "scripts" / "diagrams" / "enforce_diagram_quality_budget.py"
    )
    spec = importlib.util.spec_from_file_location(
        "diagram_quality_budget_module", module_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_write_output_rejects_parent_traversal() -> None:
    module = _load_module()

    with pytest.raises(ValueError, match="outside"):
        module._write_output(Path("../outside/budget.json"), "{}\n")
