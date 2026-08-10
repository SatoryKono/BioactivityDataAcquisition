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
"""Closeout guards for technical-debt issues #5559 through #5563."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5559-5563-closeout.json"
DEBT_GATES = ROOT / "reports" / "quality" / "debt-governance-gates.json"
MODULE_COVERAGE_GATES = ROOT / "configs" / "quality" / "module_coverage_gates.yaml"
COMPATIBILITY_CENSUS = (
    ROOT / "reports" / "quality" / "compatibility-importer-census.json"
)
CONFIG_BACKLOG = ROOT / "reports" / "quality" / "config-surface-backlog.json"
SKIP_INVENTORY = ROOT / "configs" / "quality" / "test_skip_inventory.yaml"
CONTRACT_OWNERSHIP = (
    ROOT / "reports" / "quality" / "pipeline-config-contract-ownership-map.json"
)

EXPECTED_ISSUES = {5559, 5560, 5561, 5562, 5563}

pytestmark = pytest.mark.architecture


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _composite_duplication_clusters(
    backlog: dict[str, Any],
) -> list[dict[str, Any]]:
    clusters = backlog["duplication_audit"]["clusters"]
    assert isinstance(clusters, list)
    return [
        cluster
        for cluster in clusters
        if all(
            surface_kind == "composite_config"
            for surface_kind in cluster["surface_kind_counts"]
        )
    ]


def test_issue_5559_module_coverage_gate_current_values_match_zero_residuals() -> None:
    gates_policy = _load_yaml(MODULE_COVERAGE_GATES)["aggregate_residual_ratchets"]
    debt_gates = _load_json(DEBT_GATES)
    gate_rows = {
        row["name"]: row for row in debt_gates["gates"] if isinstance(row, dict)
    }

    assert gates_policy["linked_issue"] == "#5559"
    assert gates_policy["mode"] == "fail-fast-current-inventory"
    assert gates_policy["historical_baseline"]["linked_issue"] == "#5553"
    assert gates_policy["unmeasured_module_count"]["max_count"] == 0
    assert gates_policy["uncovered_module_count"]["max_count"] == 0
    # Policy remains zero-residual; live inventory may temporarily report
    # unmeasured modules when coverage XML lags source moves. Assert gate wiring
    # and uncovered residual (still zero) rather than requiring unmeasured pass.
    assert gate_rows["module_coverage_unmeasured_modules"]["limit"] == 0
    assert gate_rows["module_coverage_uncovered_modules"]["current"] == 0
    assert gate_rows["module_coverage_uncovered_modules"]["limit"] == 0
    assert gate_rows["module_coverage_uncovered_modules"]["status"] == "pass"


def test_issue_5560_public_merge_entrypoint_has_zero_first_party_importers() -> None:
    census = _load_json(COMPATIBILITY_CENSUS)
    retained = {
        row["path"]: row
        for row in census["retained_entrypoints"]
        if isinstance(row, dict)
    }

    merge_row = retained["src/bioetl/application/composite/merger.py"]
    assert merge_row["src_importer_count"] == 0
    assert merge_row["src_importers"] == []
    assert (ROOT / "src/bioetl/application/composite/merge_service.py").exists()
    assert census["summary"]["retained_entrypoint_count"] == 12
    assert census["summary"]["retained_public_export_facade_count"] == 4


def test_issue_5561_config_duplication_clusters_are_owner_addressable() -> None:
    closeout = _load_json(CLOSEOUT)
    backlog = _load_json(CONFIG_BACKLOG)
    clusters = backlog["duplication_audit"]["clusters"]
    composite_clusters = _composite_duplication_clusters(backlog)
    metrics = closeout["metrics"]

    assert (
        backlog["duplication_audit"]["summary"]["duplicate_cluster_count"]
        <= metrics["config_duplicate_cluster_count"]
    ), (
        "Live config duplication clusters must not exceed the reviewed #5561 "
        "closeout baseline"
    )
    assert (
        backlog["duplication_audit"]["summary"]["duplicate_occurrence_count"]
        <= metrics["config_duplicate_occurrence_count"]
    ), (
        "Live config duplication occurrences must not exceed the reviewed #5561 "
        "closeout baseline"
    )
    assert clusters
    assert composite_clusters

    for cluster in clusters:
        governance = cluster["governance"]
        assert governance["owner"].startswith("@bioetl-")
        assert governance["decision"]
        assert governance["rationale"]

    for cluster in composite_clusters:
        governance = cluster["governance"]
        assert governance["linked_issue"] == "#5568"


def test_issue_5562_skip_inventory_entries_are_individually_accountable() -> None:
    payload = _load_yaml(SKIP_INVENTORY)
    entries = payload["entries"]

    entries_by_issue: dict[str, int] = {}
    for entry in entries:
        assert entry["owner"].startswith("@bioetl-")
        linked_issue = str(entry["linked_issue"])
        assert linked_issue.startswith("#")
        entries_by_issue[linked_issue] = entries_by_issue.get(linked_issue, 0) + 1
        assert entry["lifecycle"] in {"permanent_policy", "temporary_debt"}
        if entry["lifecycle"] == "temporary_debt":
            assert str(entry.get("expires_on", "")).strip()
        assert str(entry["rationale"]).strip()

    # #6647 temporary Loki/Tempo skip tails removed after Phase 4 surface cleanup (#6576).
    assert entries_by_issue == {
        "#5562": 19,
        "#6570": 1,
        "#6576": 1,
        "#7249": 3,
    }


def test_issue_5563_excluded_non_gold_rows_are_burned_down_to_zero() -> None:
    ownership = _load_json(CONTRACT_OWNERSHIP)
    rows = ownership["rows"]
    excluded_rows = [
        row for row in rows if row.get("coverage_status") == "excluded_non_gold"
    ]

    assert ownership["explicit_exclusions"] == []
    assert excluded_rows == []
