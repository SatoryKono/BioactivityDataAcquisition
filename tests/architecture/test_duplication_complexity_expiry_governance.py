"""Lock AUD-002: exemption expiries stay staggered, tracked, and enforced."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest
import yaml


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_YAML = (
    ROOT / "configs" / "quality" / "duplication_complexity_exemptions.yaml"
)
CHECK_SCRIPT = (
    ROOT
    / "scripts"
    / "engineering"
    / "qa"
    / "check_duplication_complexity_exemptions.py"
)
PROGRESS_MARKER = "Progress 2026-"


def _entries() -> list[dict]:
    payload = yaml.safe_load(REGISTRY_YAML.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return [
        *(payload.get("path_entries") or []),
        *(payload.get("function_entries") or []),
    ]


@pytest.mark.architecture
def test_exemption_expiries_are_desynchronized() -> None:
    expiries = {str(entry["expiry"]) for entry in _entries()}
    assert len(expiries) >= 3, (
        "Exemption expiries must not collapse onto one cliff date "
        f"(AUD-002): {sorted(expiries)}"
    )


@pytest.mark.architecture
def test_every_removal_step_carries_progress() -> None:
    missing = [
        str(entry.get("path") or entry.get("name"))
        for entry in _entries()
        if PROGRESS_MARKER not in str(entry.get("removal_step", ""))
    ]
    assert missing == [], (
        "Every exemption needs removal_step progress (AUD-002):\n"
        + "\n".join(missing)
    )


@pytest.mark.architecture
def test_exemption_registry_check_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(CHECK_SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, (
        "Duplication/complexity exemption registry check failed (AUD-002).\n"
        + (result.stdout or "")
        + (result.stderr or "")
    )
