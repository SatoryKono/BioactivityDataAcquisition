"""Lock AUD-007: composite ownership graph, mixin sizes, jscpd threshold."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
OWNERSHIP_YAML = ROOT / "configs" / "quality" / "composite_ownership.yaml"
COMPOSITE = ROOT / "src" / "bioetl" / "application" / "composite"
JSCPD_JSON = ROOT / ".jscpd.json"
DUPLICATION_WORKFLOW = ROOT / ".github" / "workflows" / "duplication-complexity.yml"
MAX_MIXIN_LINES = 200
JSCPD_THRESHOLD = 10


def _areas() -> list[dict]:
    payload = yaml.safe_load(OWNERSHIP_YAML.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert payload["policy_scope"] == "composite_ownership"
    return list(payload["areas"])


@pytest.mark.architecture
def test_every_composite_module_has_exactly_one_owner() -> None:
    actual = {
        path.relative_to(ROOT).as_posix() for path in COMPOSITE.rglob("*.py")
    }
    listed: list[str] = []
    for area in _areas():
        assert area["name"] and area["responsibility"], area
        listed.extend(area["modules"])
    assert sorted(listed) == sorted(actual), (
        "Ownership map drift (AUD-007).\n"
        f"missing: {sorted(actual - set(listed))}\n"
        f"stale: {sorted(set(listed) - actual)}\n"
        f"duplicated: {sorted({m for m in listed if listed.count(m) > 1})}"
    )


@pytest.mark.architecture
def test_ownership_graph_edges_reference_known_areas() -> None:
    areas = _areas()
    names = {area["name"] for area in areas}
    for area in areas:
        for dep in area.get("depends_on") or []:
            assert dep in names, f"{area['name']} -> unknown {dep}"
            assert dep != area["name"], f"{area['name']} self-depends"


@pytest.mark.architecture
def test_no_composite_mixin_exceeds_size_cap() -> None:
    offenders = {}
    for path in sorted(COMPOSITE.rglob("*mixin*.py")):
        size = len(path.read_text(encoding="utf-8").splitlines())
        if size > MAX_MIXIN_LINES:
            offenders[path.relative_to(ROOT).as_posix()] = size
    assert offenders == {}, (
        f"Composite mixins must stay under {MAX_MIXIN_LINES} lines (AUD-007): "
        f"{offenders}"
    )


@pytest.mark.architecture
def test_jscpd_threshold_is_raised_consistently() -> None:
    config = json.loads(JSCPD_JSON.read_text(encoding="utf-8"))
    assert config["threshold"] == JSCPD_THRESHOLD, (
        f".jscpd.json threshold must be {JSCPD_THRESHOLD} (AUD-007)"
    )
    workflow = DUPLICATION_WORKFLOW.read_text(encoding="utf-8")
    assert f"--threshold {JSCPD_THRESHOLD}" in workflow
    assert "--threshold 5" not in workflow
