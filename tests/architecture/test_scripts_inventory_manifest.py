"""Architecture tests for scripts inventory manifest drift."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_inventory_module():
    root = _project_root()
    module_path = (
        root
        / "scripts"
        / "engineering"
        / "repo"
        / "check_scripts_inventory.py"
    )
    spec = importlib.util.spec_from_file_location(
        "check_scripts_inventory_for_manifest_test", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_scripts_inventory_manifest_exists_and_has_required_keys() -> None:
    """Inventory manifest must exist and keep a stable schema."""
    root = _project_root()
    manifest_path = root / "configs" / "quality" / "scripts_inventory_manifest.json"

    assert manifest_path.exists(), (
        "Scripts inventory manifest is missing: "
        f"{manifest_path}. Run scripts/engineering/repo/check_scripts_inventory.py --update."
    )

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    required_keys = {"schema_version", "generated_at", "summary", "scripts"}
    assert required_keys.issubset(payload.keys()), (
        f"Missing required manifest keys: {sorted(required_keys - set(payload.keys()))}"
    )

    summary = payload["summary"]
    assert isinstance(summary, dict)
    assert "total_scripts" in summary
    assert "status_counts" in summary


@pytest.mark.slow
@pytest.mark.timeout(300)
def test_scripts_inventory_manifest_drift_check_passes() -> None:
    """Committed manifest must match current scripts inventory."""
    module = _load_inventory_module()
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        rc = module.main(
            [
                "--check",
                "--manifest",
                "configs/quality/scripts_inventory_manifest.json",
            ]
        )

    assert rc == 0, (
        "Scripts inventory drift check failed.\n"
        f"stdout:\n{stdout.getvalue()}\n"
        f"stderr:\n{stderr.getvalue()}\n"
        "Run scripts/engineering/repo/check_scripts_inventory.py --update to refresh manifest."
    )
