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
"""Closeout guards for refactoring follow-up issues #6097 through #6100."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.engineering.qa.vcr import check_replay_preflight
from tests.architecture.test_runtime_import_scc import (
    ACCEPTED_RUNTIME_SCCS,
    REVIEWED_RUNTIME_SCC_BUDGET_MAX,
)

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = (
    ROOT / "reports" / "quality" / "refactoring-followups-6097-6100-closeout.json"
)
COMPATIBILITY_CENSUS = (
    ROOT / "reports" / "quality" / "compatibility-importer-census.json"
)
COMPATIBILITY_INVENTORY = (
    ROOT / "configs" / "quality" / "compatibility_facade_inventory.yaml"
)
CONFIG_BASELINE = ROOT / "reports" / "quality" / "config-discrepancy-baseline.json"
CONFIG_COMPATIBILITY = (
    ROOT / "configs" / "quality" / "config_compatibility_registry.yaml"
)
CONTRACT_DIAGNOSTICS = (
    ROOT / "reports" / "quality" / "contract-registry-diagnostics.json"
)
VCR_CATALOG = ROOT / "reports" / "quality" / "vcr-metadata-catalog.json"
EXPECTED_ISSUES = {6097, 6098, 6099, 6100}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_issue_6097_public_facades_have_explicit_owners_and_bounded_census() -> None:
    census = _load_json(COMPATIBILITY_CENSUS)
    summary = census["summary"]
    inventory = _load_yaml(COMPATIBILITY_INVENTORY)
    rows = inventory["retained_entrypoints"]

    assert summary["retained_entrypoint_count"] <= 12
    assert summary["retained_public_export_facade_count"] <= 4
    assert summary["twin_pair_count"] == 0
    assert summary["retained_public_export_facades_with_duplicate_exports"] == 0
    assert summary["retained_public_export_facades_with_resolution_conflicts"] == 0
    assert summary["retained_public_export_facades_with_wrapper_contract_drift"] == 0

    assert len(rows) == summary["retained_entrypoint_count"]
    public_export_rows = [row for row in rows if "public_export_contract" in row]
    assert len(public_export_rows) == summary["retained_public_export_facade_count"]

    for row in rows:
        assert row["status"] == "public-entrypoint"
        assert str(row["owner"]).strip()
        assert str(row["compatibility_role"]).strip()
        assert str(row["allowed_call_sites"]).strip()
        assert str(row["migration_path"]).strip()
        assert str(row["exit_criteria"]).strip()
        assert row["external_breaking_change_required"] is True


def test_issue_6098_runtime_scc_budget_was_reduced_without_stale_acceptance() -> None:
    accepted = set(ACCEPTED_RUNTIME_SCCS)

    assert REVIEWED_RUNTIME_SCC_BUDGET_MAX == 1
    assert len(ACCEPTED_RUNTIME_SCCS) == 1
    assert not any(
        {
            "bioetl.infrastructure.storage.support.atomic_group",
            "bioetl.infrastructure.storage.support.atomic_ops",
        }
        == set(component)
        for component in accepted
    )


def test_issue_6099_config_governance_has_owner_map_and_zero_drift() -> None:
    baseline = _load_json(CONFIG_BASELINE)
    diagnostics = _load_json(CONTRACT_DIAGNOSTICS)
    compatibility = _load_yaml(CONFIG_COMPATIBILITY)

    metrics = baseline["metrics"]
    assert metrics["inconsistent_parameter_count"] == 0
    assert metrics["raw_inconsistent_parameter_count"] == 0
    assert metrics["sanctioned_partial_parameter_count"] == 0
    assert diagnostics["valid"] is True
    assert diagnostics["blocking_issue_count"] == 0

    taxonomy = baseline["parameter_taxonomy"]
    assert taxonomy["evolution_policy"]["alias_registry"] == (
        "configs/quality/config_compatibility_registry.yaml"
    )
    assert taxonomy["evolution_policy"]["blocking_issue_budget"] == 0
    group_owner_map = taxonomy["group_owner_map"]
    assert group_owner_map["compatibility_legacy"]["owner"] == "config-governance"
    assert group_owner_map["domain_entity_contract"]["owner"] == "contract-governance"
    for family in taxonomy["families"].values():
        assert set(family["group_owner_map"]) == set(family["groups"])

    accepted_shapes = compatibility["accepted_shapes"]
    assert (
        len(accepted_shapes)
        <= compatibility["policy"]["burn_down"]["accepted_shape_max"]
    )
    for entry in accepted_shapes:
        assert entry["status"] == "canonical-alias"
        assert str(entry["permanent_rationale"]).strip()
        assert entry["exit_strategy"] == "retain-permanent-canonical-alias"


def test_issue_6100_vcr_replay_preflight_is_registered_and_catalog_safe() -> None:
    qa_main = (ROOT / "scripts" / "engineering" / "qa" / "__main__.py").read_text(
        encoding="utf-8"
    )
    vcr_main = (
        ROOT / "scripts" / "engineering" / "qa" / "vcr" / "__main__.py"
    ).read_text(encoding="utf-8")
    docs = (ROOT / "docs" / "03-guides" / "testing.md").read_text(encoding="utf-8")
    catalog = _load_json(VCR_CATALOG)

    assert "check-vcr-replay-preflight" in qa_main
    assert "check-replay-preflight" in vcr_main
    assert "git lfs pull" in docs

    report = check_replay_preflight.collect_vcr_replay_preflight(ROOT)
    assert report["schema_version"] == "vcr-replay-preflight-v1"
    assert report["catalog"]["exists"] is True
    assert report["catalog"]["totals_match"] is True
    assert report["sanitizer_status"]["replay_only"] is True
    assert report["sanitizer_status"]["has_request_sanitizer"] is True

    totals = catalog["totals"]
    assert totals["cassette_count"] == report["cassette_count"]
    assert totals["metadata_sidecar_count"] == report["metadata_sidecar_count"]
    assert totals["unowned_cassette_count"] == 0
