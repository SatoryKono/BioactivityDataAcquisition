"""Freeze sanctioned public entrypoints and composition primary API surface.

Issue #7708 — unplanned growth of public-entrypoint inventory / composition
``*_api`` seams requires an explicit scorecard update, not silent expansion.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCORECARD_PATH = PROJECT_ROOT / "configs" / "quality" / "debt_scorecard.yaml"
COMPAT_INVENTORY_PATH = (
    PROJECT_ROOT / "configs" / "quality" / "compatibility_facade_inventory.yaml"
)
COMPOSITION_ROOT = PROJECT_ROOT / "src" / "bioetl" / "composition"
COMPOSITION_README = COMPOSITION_ROOT / "README.md"

# Primary composition public seams (package-root only; not nested factories/*).
# Bumping this set requires README + scorecard/governance review (#7708).
EXPECTED_COMPOSITION_PRIMARY_API_MODULES = frozenset(
    {
        "composite_api.py",
        "control_plane_api.py",
        "entrypoints.py",
        "execution_api.py",
        "health_api.py",
        "maintenance_api.py",
        "observability_api.py",
        "registry_api.py",
        "resources_api.py",
    }
)


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _public_entrypoint_count_from_inventory(inventory: dict[str, Any]) -> int:
    retained = inventory.get("retained_entrypoints", [])
    assert isinstance(retained, list)
    return sum(
        1
        for entry in retained
        if isinstance(entry, dict) and entry.get("status") == "public-entrypoint"
    )


def _scorecard_public_entrypoint_max(scorecard: dict[str, Any]) -> int:
    section = scorecard.get("sanctioned_public_entrypoint_governance", {})
    assert isinstance(section, dict)
    metrics = section.get("metrics", {})
    assert isinstance(metrics, dict)
    entry = metrics.get("public_entrypoint_count", {})
    assert isinstance(entry, dict)
    current = entry.get("current_count")
    assert isinstance(current, int)
    return current


def test_public_entrypoint_inventory_does_not_exceed_scorecard_max() -> None:
    scorecard = _load_yaml(SCORECARD_PATH)
    inventory = _load_yaml(COMPAT_INVENTORY_PATH)
    live_count = _public_entrypoint_count_from_inventory(inventory)
    max_count = _scorecard_public_entrypoint_max(scorecard)

    assert live_count == max_count, (
        f"public-entrypoint inventory count ({live_count}) must match "
        f"debt_scorecard sanctioned_public_entrypoint_governance."
        f"public_entrypoint_count.current_count ({max_count}). "
        "Raising the max requires an explicit scorecard review; silent growth "
        "is forbidden (#7708)."
    )
    assert live_count <= max_count


def test_composition_primary_api_modules_are_frozen() -> None:
    present = {
        path.name
        for path in COMPOSITION_ROOT.glob("*_api.py")
        if path.is_file()
    }
    present.add("entrypoints.py")
    assert COMPOSITION_ROOT.joinpath("entrypoints.py").is_file()

    unexpected = sorted(present - EXPECTED_COMPOSITION_PRIMARY_API_MODULES)
    missing = sorted(EXPECTED_COMPOSITION_PRIMARY_API_MODULES - present)
    assert not unexpected, (
        "New composition package-root public API modules require scorecard / "
        f"README governance update (#7708). Unexpected: {unexpected}"
    )
    assert not missing, (
        "Composition primary API modules were removed without updating the "
        f"freeze set (#7708). Missing: {missing}"
    )


def test_composition_readme_maps_primary_apis_to_factories() -> None:
    readme = COMPOSITION_README.read_text(encoding="utf-8")
    assert "Primary API → factory / builder map" in readme or (
        "API → factory" in readme
    ), "composition README must publish a primary API → factory/builder map (#7708)"

    for module_name in sorted(EXPECTED_COMPOSITION_PRIMARY_API_MODULES):
        stem = module_name.removesuffix(".py")
        assert stem in readme, (
            f"composition README must document primary seam `{stem}` (#7708)"
        )

    for token in (
        "factories/pipeline",
        "bootstrap/runtime",
        "runtime_builders",
        "public_entrypoint_count",
    ):
        assert token in readme, (
            f"composition README factory map must mention `{token}` (#7708)"
        )
