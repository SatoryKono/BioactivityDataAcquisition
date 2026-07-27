"""No-growth ratchet for application/services root modules (ARCH-RES-05)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ROOT / "src" / "bioetl" / "application" / "services"
RATCHET = ROOT / "configs" / "quality" / "application_services_root_ratchet.yaml"
OWNERSHIP = SERVICES / "README.md"


def _root_module_count() -> int:
    return len([path for path in SERVICES.glob("*.py") if path.is_file()])


def test_services_ownership_map_exists() -> None:
    text = OWNERSHIP.read_text(encoding="utf-8")
    assert "No-growth rule" in text or "no-growth" in text.lower()
    assert "control_plane" in text


def test_application_services_root_module_count_non_increasing() -> None:
    payload = yaml.safe_load(RATCHET.read_text(encoding="utf-8"))
    limit = payload["root_module_count"]["max"]
    current = _root_module_count()
    assert current <= limit, (
        f"application/services root modules grew: {current} > max {limit}. "
        "Rehome new services into subdomain packages (ARCH-RES-05 / #6754)."
    )
    # Keep config current field honest for operators.
    assert payload["root_module_count"]["current"] == current
