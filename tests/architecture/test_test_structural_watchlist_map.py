# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture tests for residual test/CI to structural-watchlist mapping."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
MAP_PATH = ROOT / "configs" / "quality" / "test_structural_watchlist_map.yaml"


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


@pytest.mark.architecture
class TestResidualTestCiStructuralWatchlistMap:
    """Keep residual CI/test debt tied to concrete structural watchlists."""

    def test_watchlist_map_is_present_and_points_to_source_artifacts(self) -> None:
        mapping = _load_yaml(MAP_PATH)

        assert (
            mapping.get("policy_scope")
            == "residual_test_ci_to_structural_watchlist_mapping"
        )
        for relative_path in mapping.get("source_artifacts", []):
            assert (ROOT / relative_path).exists(), (
                f"watchlist map source artifact is missing: {relative_path}"
            )

    def test_watchlist_families_use_family_level_units(self) -> None:
        mapping = _load_yaml(MAP_PATH)
        families = mapping.get("watchlist_families", [])
        family_names = {entry["family"] for entry in families}

        assert family_names == {
            "infrastructure_adapters",
            "infrastructure_storage",
            "composition_bootstrap_runtime",
        }

        for entry in families:
            assert entry["status"] in {"active_family", "candidate_family"}
            assert entry.get("owner")
            assert entry.get("path_prefixes")
            assert entry.get("representative_modules")
            for module_path in entry["representative_modules"]:
                assert (ROOT / module_path).exists(), (
                    f"representative watchlist module missing: {module_path}"
                )

    def test_ranked_intersections_form_one_unique_priority_queue(self) -> None:
        mapping = _load_yaml(MAP_PATH)
        ranked = mapping.get("ranked_intersections", [])
        ranks = [entry["rank"] for entry in ranked]
        surfaces = [entry["weak_surface"] for entry in ranked]
        allowed_priority_bands = {"P0", "P1", "P2"}
        allowed_blast_radius = {"high", "medium", "low"}
        allowed_maturity = {"partial", "policy_stabilized", "active", "candidate"}
        family_names = {
            entry["family"] for entry in mapping.get("watchlist_families", [])
        }

        assert ranks == [1, 2, 3]
        assert len(set(surfaces)) == len(surfaces)

        for entry in ranked:
            assert entry["priority_band"] in allowed_priority_bands
            assert entry["blast_radius"] in allowed_blast_radius
            assert entry["governance_maturity"] in allowed_maturity
            assert entry["primary_family"] in family_names
            assert entry.get("linked_artifacts")
            assert entry.get("rationale")
            assert entry.get("next_wave_entrypoint")
            for relative_path in entry["linked_artifacts"]:
                assert (ROOT / relative_path).exists(), (
                    f"linked artifact missing for surface {entry['weak_surface']}: {relative_path}"
                )
            for family in entry.get("secondary_families", []):
                assert family in family_names

    def test_selection_outcome_matches_top_ranked_intersection(self) -> None:
        mapping = _load_yaml(MAP_PATH)
        ranked = mapping.get("ranked_intersections", [])
        outcome = mapping.get("selection_outcome", {})

        top = ranked[0]
        assert outcome.get("recommended_next_family") == top["primary_family"]
        assert outcome.get("recommended_next_surface") == top["weak_surface"]
        assert outcome.get("why")
        assert outcome.get("defer_until_after_mapping")
