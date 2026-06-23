"""Architecture guards for JSCPD-excluded governance artifact duplication audit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from scripts.engineering.qa import __main__ as qa_router
from scripts.engineering.qa.report_artifact_duplication_audit import (
    DEFAULT_JSON_ARTIFACT,
    JSCPD_BLIND_SPOT_ANCHORS,
    collect_artifact_duplication_report,
)

ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "configs" / "quality" / "test_matrix.yaml"
ROUTING_PATH = ROOT / "configs" / "quality" / "generated_artifact_routing.yaml"
JSCPD_PATH = ROOT / ".jscpd.json"
REPORT_PATH = ROOT / DEFAULT_JSON_ARTIFACT

pytestmark = pytest.mark.architecture


def _load_yaml(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load(path.read_text(encoding="utf-8")))


def test_artifact_duplication_audit_report_matches_live_collector() -> None:
    payload = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    report = collect_artifact_duplication_report(ROOT)

    assert payload == report
    assert payload["policy_scope"] == "config_contract_registry_artifact_duplication"
    assert {"config", "contract", "registry"}.issubset(
        payload["scope_file_counts"]
    )
    assert payload["duplicate_groups"] == len(payload["groups"])


def test_artifact_duplication_audit_is_registered_for_jscpd_blind_spot() -> None:
    matrix = _load_yaml(MATRIX_PATH)
    routing = _load_yaml(ROUTING_PATH)
    jscpd = json.loads(JSCPD_PATH.read_text(encoding="utf-8"))
    policy = cast(
        dict[str, Any],
        cast(dict[str, Any], matrix["fixture_governance"])[
            "config_contract_registry_duplication_inventory_contract"
        ],
    )

    assert set(JSCPD_BLIND_SPOT_ANCHORS).issubset(set(jscpd["ignore"]))
    assert policy["issue_ref"] == "#5409"
    assert policy["generator"] == (
        "scripts/engineering/qa/report_artifact_duplication_audit.py"
    )
    assert policy["command"] == (
        "python -m scripts.engineering.qa report-artifact-duplication-audit"
    )
    assert policy["inventory_location"] == DEFAULT_JSON_ARTIFACT.as_posix()
    assert policy["jscpd_blind_spot_source"] == ".jscpd.json"
    assert set(policy["required_scopes"]) == {"config", "contract", "registry"}

    routing_entries = cast(list[dict[str, Any]], routing["routes"])
    matching_entries = [
        entry
        for entry in routing_entries
        if entry["id"] == "config-contract-registry-artifact-duplication-quality-report"
    ]
    assert len(matching_entries) == 1
    assert matching_entries[0]["outputs"] == [DEFAULT_JSON_ARTIFACT.as_posix()]


def test_qa_router_exposes_artifact_duplication_audit_command() -> None:
    assert qa_router.COMMAND_MODULES["report-artifact-duplication-audit"] == (
        "scripts.engineering.qa.report_artifact_duplication_audit"
    )
