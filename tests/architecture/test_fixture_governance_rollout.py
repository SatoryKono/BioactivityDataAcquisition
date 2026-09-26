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
"""Architecture tests for fixture-governance rollout policy."""

from __future__ import annotations

from pathlib import Path

from tests.architecture._test_matrix_policy_support import (
    ROOT,
    TESTS_DIR,
    WORKFLOWS_DIR,
    load_matrix,
)

import pytest
import yaml


@pytest.mark.architecture
class TestFixtureGovernanceRollout:
    """Validate staged fixture-governance declarations match repository state."""

    def test_fixture_governance_rollout_matches_current_inventory(self) -> None:
        matrix = load_matrix()
        fixture_governance = matrix.get("fixture_governance", {})
        rollout = fixture_governance.get("rollout", {})
        vcr_dir = TESTS_DIR / "fixtures" / "vcr"
        golden_dir = TESTS_DIR / "fixtures" / "golden"
        contract_dir = TESTS_DIR / "fixtures" / "contracts"
        current_snapshot_dir = (
            ROOT / fixture_governance["current_silver_schema_snapshot_location"]
        )

        metadata_files = list(vcr_dir.rglob("*_meta.yaml")) if vcr_dir.exists() else []
        golden_files = list(golden_dir.rglob("*")) if golden_dir.exists() else []
        contract_files = list(contract_dir.rglob("*")) if contract_dir.exists() else []
        current_snapshot_files = (
            list(current_snapshot_dir.rglob("*.json"))
            if current_snapshot_dir.exists()
            else []
        )

        assert rollout.get("cassette_metadata") in {"planned", "partial", "enforced"}
        assert rollout.get("cassette_staleness_age") in {
            "metadata_gated",
            "partial",
            "enforced",
        }
        assert rollout.get("golden_masters") in {"planned", "partial", "enforced"}
        assert rollout.get("contract_snapshots") in {"planned", "partial", "enforced"}

        if fixture_governance.get("cassette_metadata_required"):
            assert rollout.get("cassette_metadata") == "enforced"
            assert metadata_files, (
                "cassette metadata is required but *_meta.yaml files are missing"
            )
        else:
            assert rollout.get("cassette_metadata") in {"planned", "partial"}

        if contract_files:
            assert rollout.get("contract_snapshots") in {"partial", "enforced"}
        else:
            assert rollout.get("contract_snapshots") == "planned"
            assert current_snapshot_files, (
                "external contract snapshot registry is still planned, but current "
                "silver schema snapshots are also missing"
            )

        if golden_files:
            assert rollout.get("golden_masters") == "enforced"
        else:
            assert rollout.get("golden_masters") == "planned"

    def test_vcr_filename_and_placement_policy_match_current_ci_contract(self) -> None:
        matrix = load_matrix()
        fixture_governance = matrix.get("fixture_governance", {})
        rollout = fixture_governance.get("rollout", {})
        workflow = (WORKFLOWS_DIR / "tests.yml").read_text(encoding="utf-8")
        allowlist_path = ROOT / fixture_governance["extensionless_allowlist"]
        vcr_dir = TESTS_DIR / "fixtures" / "vcr"
        legacy_dir = TESTS_DIR / "fixtures" / "vcr_cassettes"

        extensionless = [
            path.relative_to(ROOT).as_posix()
            for path in vcr_dir.rglob("*")
            if path.is_file() and path.name != ".gitkeep" and "." not in path.name
        ]
        from_root_markers = list(vcr_dir.rglob("*.from_root.yaml"))

        assert fixture_governance.get("root_vcr_policy_enforced") is True
        assert rollout.get("extensionless_filenames") in {"partial", "enforced"}
        assert "python -m scripts.engineering.qa.vcr check-placement" in workflow
        assert "python -m scripts.engineering.qa.vcr check-naming" in workflow
        assert not legacy_dir.exists(), (
            "legacy tests/fixtures/vcr_cassettes directory must stay removed"
        )
        assert not from_root_markers, (
            "legacy *.from_root.yaml markers must stay removed"
        )

        if rollout.get("extensionless_filenames") == "partial":
            assert allowlist_path.exists(), (
                "partial extensionless rollout requires an allowlist file"
            )
            allowlist_entries = {
                line.strip()
                for line in allowlist_path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            }
            assert extensionless, (
                "partial extensionless rollout is declared but no extensionless files remain"
            )
            assert set(extensionless) <= allowlist_entries, (
                "extensionless VCR inventory must stay fully allowlisted during partial rollout"
            )
        else:
            assert not extensionless, (
                "enforced extensionless rollout must not leave extensionless VCR files"
            )

    def test_vcr_cassette_age_rollout_matches_metadata_backfill_state(self) -> None:
        matrix = load_matrix()
        fixture_governance = matrix.get("fixture_governance", {})
        rollout = fixture_governance.get("rollout", {})
        workflow = (WORKFLOWS_DIR / "tests.yml").read_text(encoding="utf-8")
        vcr_dir = TESTS_DIR / "fixtures" / "vcr"
        metadata_files = list(vcr_dir.rglob("*_meta.yaml")) if vcr_dir.exists() else []

        assert fixture_governance.get("vcr_cassette_max_age_days") == 90
        assert rollout.get("cassette_staleness_age") in {
            "metadata_gated",
            "partial",
            "enforced",
        }
        assert fixture_governance.get("cassette_staleness_requires_metadata") in {
            True,
            False,
        }

        if rollout.get("cassette_staleness_age") == "metadata_gated":
            assert (
                fixture_governance.get("cassette_staleness_requires_metadata") is True
            )
            assert fixture_governance.get("cassette_metadata_required") is False
            assert not metadata_files, (
                "metadata-gated cassette stale-age policy must be updated once *_meta.yaml backfill begins"
            )
            assert "check_vcr_cassette_age" not in workflow
            assert "check_vcr_metadata_age" not in workflow
        elif rollout.get("cassette_staleness_age") == "partial":
            assert (
                fixture_governance.get("cassette_staleness_requires_metadata") is True
            )
            assert metadata_files, (
                "partial cassette stale-age rollout requires *_meta.yaml inventory"
            )
        else:
            assert (
                fixture_governance.get("cassette_staleness_requires_metadata") is True
            )
            assert fixture_governance.get("cassette_metadata_required") is True
            assert metadata_files, (
                "enforced cassette stale-age rollout requires *_meta.yaml inventory"
            )
            assert (
                "python -m scripts.engineering.qa.vcr check-metadata-age --max-age-days 90"
                in workflow
            )

    def test_vcr_metadata_catalog_and_backfill_policy_match_current_state(self) -> None:
        matrix = load_matrix()
        fixture_governance = matrix.get("fixture_governance", {})
        rollout = fixture_governance.get("rollout", {})
        workflow = (WORKFLOWS_DIR / "tests.yml").read_text(encoding="utf-8")
        vcr_dir = TESTS_DIR / "fixtures" / "vcr"
        metadata_files = list(vcr_dir.rglob("*_meta.yaml")) if vcr_dir.exists() else []
        catalog_path = ROOT / fixture_governance["cassette_metadata_catalog_location"]
        catalog_script = ROOT / fixture_governance["cassette_metadata_catalog_script"]
        backfill_script = ROOT / fixture_governance["cassette_metadata_backfill_script"]

        assert rollout.get("cassette_metadata_catalog") in {
            "planned",
            "partial",
            "enforced",
        }
        assert rollout.get("cassette_metadata_backfill") in {
            "planned",
            "partial",
            "enforced",
        }
        assert fixture_governance.get(
            "cassette_metadata_backfill_workflow_present"
        ) in {
            True,
            False,
        }

        if rollout.get("cassette_metadata_catalog") == "planned":
            assert not catalog_path.exists(), (
                "planned metadata catalog rollout must be updated once the canonical catalog exists"
            )
        else:
            assert catalog_path.exists(), (
                "active metadata catalog rollout requires canonical catalog artifact"
            )

        if rollout.get("cassette_metadata_backfill") == "planned":
            assert (
                fixture_governance.get("cassette_metadata_backfill_workflow_present")
                is False
            )
            assert not metadata_files, (
                "planned metadata backfill rollout must be updated once *_meta.yaml inventory appears"
            )
            assert not catalog_script.exists(), (
                "planned metadata catalog rollout must be updated once the canonical generator exists"
            )
            assert not backfill_script.exists(), (
                "planned metadata backfill rollout must be updated once the canonical migration exists"
            )
            assert "backfill_vcr_metadata" not in workflow
            assert "generate_vcr_metadata_catalog" not in workflow
        else:
            assert metadata_files, (
                "active metadata backfill rollout requires *_meta.yaml inventory"
            )
            if rollout.get("cassette_metadata_catalog") == "enforced":
                assert (
                    "python -m scripts.engineering.qa report-vcr-metadata --check"
                    in workflow
                )
            if rollout.get("cassette_metadata_backfill") == "enforced":
                assert (
                    "scripts/ops/migrations/active/backfill_vcr_metadata_sidecars.py --check"
                    in workflow
                )

    def test_partial_rollout_entries_carry_review_dates_and_targets(self) -> None:
        matrix = load_matrix()
        ledger_path = ROOT / matrix["fixture_governance"]["governance_ledger_location"]
        ledger = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))

        for entry in ledger["entries"]:
            status = entry.get("status")
            if status != "partial":
                continue
            assert entry["last_reviewed"].startswith("2026-")
            assert entry["target_resolution_date"].startswith("2026-")
            for relative_path in (
                entry["current_evidence_paths"] + entry["artifact_paths"]
            ):
                assert (ROOT / Path(relative_path)).exists(), (
                    f"fixture-governance ledger path is missing for {entry['field']}: "
                    f"{relative_path}"
                )
