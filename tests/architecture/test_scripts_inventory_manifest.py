"""Architecture tests for scripts inventory manifest drift."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


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
@pytest.mark.timeout(600)
def test_scripts_inventory_manifest_drift_check_passes() -> None:
    """Committed manifest must match current scripts inventory."""
    root = _project_root()
    script_path = (
        root
        / "scripts"
        / "engineering"
        / "repo"
        / "check_scripts_inventory.py"
    )
    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--check",
            "--manifest",
            "configs/quality/scripts_inventory_manifest.json",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )

    assert result.returncode == 0, (
        "Scripts inventory drift check failed.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}\n"
        "Run scripts/engineering/repo/check_scripts_inventory.py --update to refresh manifest."
    )
