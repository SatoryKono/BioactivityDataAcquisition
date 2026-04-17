"""Architecture tests for scripts catalog governance policy."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_catalog_module():
    root = _project_root()
    module_path = (
        root
        / "scripts"
        / "engineering"
        / "repo"
        / "check_scripts_catalog.py"
    )
    spec = importlib.util.spec_from_file_location(
        "check_scripts_catalog_governance_test", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_scripts_catalog_governance_check_passes() -> None:
    """Scripts catalog policy must pass structural and lifecycle checks."""
    module = _load_catalog_module()
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        rc = module.main(["--catalog", "scripts/catalog.yaml"])

    assert rc == 0, (
        "Scripts catalog governance validation failed.\n"
        f"stdout:\n{stdout.getvalue()}\n"
        f"stderr:\n{stderr.getvalue()}\n"
    )
