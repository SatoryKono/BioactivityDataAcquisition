# pyright: reportArgumentType=false
"""No-growth freeze for application.composite top-level modules (#7610 / #7605)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
COMPOSITE = ROOT / "src" / "bioetl" / "application" / "composite"
FREEZE = ROOT / "configs" / "quality" / "application_composite_public_surface.yaml"


def _top_level_module_count() -> int:
    return len([path for path in COMPOSITE.glob("*.py") if path.is_file()])


def test_composite_public_surface_policy_exists() -> None:
    payload = yaml.safe_load(FREEZE.read_text(encoding="utf-8"))
    assert payload["policy"]["new_top_level_modules"] == "require_allowlist_entry"
    assert "protocols.py" in payload["policy"]["preferred_extension_point"]


def test_composite_top_level_module_count_non_increasing() -> None:
    payload = yaml.safe_load(FREEZE.read_text(encoding="utf-8"))
    limit = int(payload["top_level_modules"]["max"])
    current = _top_level_module_count()
    assert current <= limit, (
        f"application/composite top-level modules grew: {current} > max {limit}. "
        "Extend protocols.py or place collaborators under checkpoint/helpers/runner_pkg "
        "(#7610). Update configs/quality/application_composite_public_surface.yaml only "
        "with explicit PR rationale."
    )
