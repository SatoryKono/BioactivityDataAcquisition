"""Architecture guards for config compatibility taxonomy review evidence."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any, cast

import pytest

from scripts.schema.generate_config_matrix import (
    _classify_parameter_key,
    _collect_family_configs,
)


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = ROOT / "reports" / "quality" / "config-discrepancy-baseline.json"
REVIEW_PATH = (
    ROOT / "reports" / "quality" / "config-compatibility-legacy-taxonomy-review.json"
)
REQUIRED_FAMILIES = {"composite_runtime", "entity_effective"}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _live_compatibility_legacy_keys_by_family() -> dict[str, list[str]]:
    """Return exact live taxonomy keys so legacy drift cannot hide behind counts."""
    result: dict[str, list[str]] = {}
    for family_name, configs in _collect_family_configs().items():
        family_keys = sorted({key for values in configs.values() for key in values})
        result[family_name] = [
            key
            for key in family_keys
            if _classify_parameter_key(key) == "compatibility_legacy"
        ]
    return result


def test_config_compatibility_legacy_taxonomy_review_matches_live_baseline() -> None:
    """The reviewed taxonomy artifact must match the generated discrepancy report."""
    baseline = _load_json(BASELINE_PATH)
    review = _load_json(REVIEW_PATH)

    assert review["status"] == "reviewed_no_growth"
    assert review["budget_policy"] == "no_growth_ratchet_only"
    assert review["source_artifact"] == "reports/quality/config-discrepancy-baseline.json"

    baseline_families = cast(
        dict[str, Any],
        cast(dict[str, Any], baseline["parameter_taxonomy"])["families"],
    )
    review_families = cast(dict[str, Any], review["families"])
    assert set(review_families) == REQUIRED_FAMILIES

    for family_name in sorted(REQUIRED_FAMILIES):
        baseline_family = cast(dict[str, Any], baseline_families[family_name])
        review_family = cast(dict[str, Any], review_families[family_name])
        groups = cast(dict[str, int], baseline_family["groups"])

        assert review_family["compatibility_legacy_count"] == groups.get(
            "compatibility_legacy",
            0,
        )
        assert baseline_family["unclassified_parameter_count"] == 0
        assert cast(str, review_family["owner"]).strip()
        assert cast(str, review_family["rationale"]).strip()
        assert cast(str, review_family["action"]).strip()
        assert review_family["risk"] in {"low", "medium", "high"}
        assert date.fromisoformat(str(review_family["review_date"])) >= date(
            2026,
            6,
            16,
        )


def test_config_compatibility_legacy_review_freezes_exact_key_set() -> None:
    """Reviewed legacy taxonomy keys must not grow or rotate without review."""
    review = _load_json(REVIEW_PATH)
    review_families = cast(dict[str, Any], review["families"])
    live_keys_by_family = _live_compatibility_legacy_keys_by_family()

    assert set(live_keys_by_family) == REQUIRED_FAMILIES
    for family_name in sorted(REQUIRED_FAMILIES):
        review_family = cast(dict[str, Any], review_families[family_name])
        reviewed_keys = review_family.get("compatibility_legacy_keys")
        assert isinstance(reviewed_keys, list), (
            f"{family_name} must publish reviewed compatibility_legacy_keys"
        )
        assert reviewed_keys == sorted(reviewed_keys), (
            f"{family_name} compatibility_legacy_keys must be sorted"
        )
        assert reviewed_keys == live_keys_by_family[family_name], (
            f"{family_name} compatibility_legacy taxonomy changed without review"
        )
        assert review_family["compatibility_legacy_count"] == len(reviewed_keys)


def test_config_compatibility_legacy_taxonomy_has_ci_guard_links() -> None:
    """Every declared guard in the review artifact must be a real repo file."""
    review = _load_json(REVIEW_PATH)
    guards = review.get("guards")
    assert isinstance(guards, list) and guards

    for guard in guards:
        assert isinstance(guard, str) and guard
        assert (ROOT / guard).exists(), f"Missing config compatibility guard: {guard}"


def test_composite_runtime_alias_family_inventory_is_published() -> None:
    """Composite compatibility_legacy review must inventory active alias families."""
    review = _load_json(REVIEW_PATH)
    review_families = cast(dict[str, Any], review["families"])
    composite_runtime = cast(dict[str, Any], review_families["composite_runtime"])
    live_keys_by_family = _live_compatibility_legacy_keys_by_family()
    live_composite_keys = set(live_keys_by_family["composite_runtime"])

    alias_families = composite_runtime.get("alias_families")
    assert isinstance(alias_families, list) and alias_families

    family_names = {
        str(row["family_name"]) for row in alias_families if isinstance(row, dict)
    }
    assert family_names == {"hba_count", "hbd_count", "logp", "polar_surface_area"}

    for row in alias_families:
        assert isinstance(row, dict)
        assert row["owner"] == "config-governance"
        assert row["usage_classification"] == (
            "first_party_active_cross_provider_join_alias"
        )
        keys = row.get("compatibility_legacy_keys")
        assert isinstance(keys, list) and keys == sorted(keys)
        assert set(keys) <= live_composite_keys
        preconditions = row.get("removal_preconditions")
        assert isinstance(preconditions, list) and preconditions


def test_composite_runtime_first_safe_removal_wave_is_recorded() -> None:
    """The first confirmed-unused alias family removal must stay explicit."""
    review = _load_json(REVIEW_PATH)
    review_families = cast(dict[str, Any], review["families"])
    composite_runtime = cast(dict[str, Any], review_families["composite_runtime"])
    first_wave = composite_runtime.get("first_safe_removal_wave")
    assert isinstance(first_wave, dict)

    assert first_wave["family_name"] == "standard_inchi"
    assert first_wave["owner"] == "config-governance"
    assert first_wave["usage_classification"] == "confirmed_unused_config_duplicate"
    assert first_wave["state"] == "removed"
    assert first_wave["compatibility_legacy_keys_removed"] == [
        "composite.field_aliases.standard_inchi",
        "composite.field_aliases.standard_inchi.pubchem",
    ]
    satisfied = first_wave.get("removal_preconditions_satisfied")
    assert isinstance(satisfied, list) and satisfied
