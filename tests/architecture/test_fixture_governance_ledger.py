"""Architecture ratchets for fixture-governance rollout ownership."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "configs" / "quality" / "test_matrix.yaml"


YamlMap = dict[str, Any]


def _load_yaml(path: Path) -> YamlMap:
    with path.open(encoding="utf-8") as handle:
        return cast(YamlMap, yaml.safe_load(handle))


def _load_matrix() -> YamlMap:
    return _load_yaml(MATRIX_PATH)


def _ledger_path(matrix: YamlMap) -> Path:
    fixture_governance = cast(YamlMap, matrix.get("fixture_governance", {}))
    return ROOT / cast(str, fixture_governance["governance_ledger_location"])


def _load_ledger(matrix: YamlMap) -> YamlMap:
    return _load_yaml(_ledger_path(matrix))


@pytest.mark.architecture
class TestFixtureGovernanceLedger:
    """Keep replay-governance rollout tied to an explicit hardening ledger."""

    def test_matrix_declares_canonical_fixture_governance_ledger(self) -> None:
        matrix = _load_matrix()
        ledger_path = _ledger_path(matrix)

        assert (
            matrix.get("fixture_governance", {}).get("governance_ledger_location")
            == "configs/quality/fixture_governance_ledger.yaml"
        )
        assert ledger_path.exists(), (
            "fixture governance rollout must declare a canonical tracked ledger"
        )

    def test_ledger_tracks_every_rollout_field_without_drift(self) -> None:
        matrix = _load_matrix()
        rollout = matrix.get("fixture_governance", {}).get("rollout", {})
        ledger = _load_ledger(matrix)
        entries = {entry["field"]: entry for entry in ledger.get("entries", [])}

        assert ledger.get("policy_scope") == "fixture_governance_rollout"
        assert set(entries) == set(rollout), (
            "fixture governance ledger must track every rollout field exactly once"
        )

        for field, status in rollout.items():
            assert entries[field]["status"] == status, (
                f"fixture governance ledger drift for '{field}': expected {status!r}"
            )

    def test_partial_or_planned_rollout_fields_have_owner_and_promotion_contract(
        self,
    ) -> None:
        matrix = _load_matrix()
        ledger = _load_ledger(matrix)
        allowed_blockers = {
            "legacy_filename_inventory",
            "missing_contract_snapshot_registry",
            "missing_metadata_backfill",
            "missing_policy_test_ratchet",
            "representative_scope_gap",
        }

        for entry in ledger.get("entries", []):
            if entry["status"] not in {"partial", "planned"}:
                continue

            for field_name in (
                "owner",
                "blocking_classification",
                "next_step",
                "promotion_criteria",
            ):
                assert entry.get(field_name), (
                    f"fixture governance field '{entry['field']}' must define {field_name}"
                )

            assert entry["blocking_classification"] in allowed_blockers
            assert entry.get("current_evidence_paths"), (
                f"fixture governance field '{entry['field']}' must point to current evidence"
            )
            assert entry.get("artifact_paths"), (
                f"fixture governance field '{entry['field']}' must point to local artifacts"
            )

    def test_ledger_artifacts_exist_for_active_rollout_items(self) -> None:
        matrix = _load_matrix()
        ledger = _load_ledger(matrix)

        for entry in ledger.get("entries", []):
            for relative_path in entry.get("current_evidence_paths", []):
                assert (ROOT / relative_path).exists(), (
                    f"fixture governance evidence path missing for '{entry['field']}': "
                    f"{relative_path}"
                )
            for relative_path in entry.get("artifact_paths", []):
                assert (ROOT / relative_path).exists(), (
                    f"fixture governance artifact path missing for '{entry['field']}': "
                    f"{relative_path}"
                )

    def test_fixture_pruning_policy_is_inventory_and_owner_driven(self) -> None:
        matrix = _load_matrix()
        ledger = _load_ledger(matrix)
        policy = ledger.get("pruning_policy")
        assert isinstance(policy, dict), (
            "fixture governance ledger must define pruning_policy"
        )

        assert policy["linked_issue"] == "#5583"
        assert policy["default_action"] == "retain"
        assert policy["owner"].startswith("@bioetl-")

        required_evidence = set(policy["required_evidence"])
        assert {
            "metadata_owner",
            "reachability_owner_paths",
            "generator_or_catalog_drift_check",
            "targeted_replay_or_contract_test",
            "rollback_or_rerecord_path",
        } <= required_evidence

        forbidden_basis = set(policy["forbidden_basis"])
        assert {
            "filename_age_only",
            "unreferenced_by_text_search_only",
            "local_disk_pressure_only",
        } <= forbidden_basis

        for relative_path in policy["canonical_checks"]:
            assert (ROOT / relative_path).exists(), relative_path
