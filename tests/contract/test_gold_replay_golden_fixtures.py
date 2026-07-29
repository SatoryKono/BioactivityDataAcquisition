# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Bounded no-network Gold replay golden fixture checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

pytestmark = [pytest.mark.contract, pytest.mark.no_api]

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = (
    ROOT
    / "tests"
    / "fixtures"
    / "golden"
    / "reproducibility"
    / "gold_replay_representative_v1.json"
)
EXPECTED_FAMILIES = {"provider", "publication", "composite"}


def _load_fixture() -> dict[str, Any]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _sha256_rows(rows: object) -> str:
    return hashlib.sha256(
        json.dumps(
            rows,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def test_gold_replay_fixture_covers_representative_gold_families() -> None:
    fixture = _load_fixture()
    cases = fixture["cases"]

    assert fixture["schema_version"] == "gold-replay-representative-v1"
    assert fixture["network_policy"] == "no_live_api"
    assert {case["gold_family"] for case in cases} == EXPECTED_FAMILIES
    assert {case["layer"] for case in cases} == {"gold"}


def test_gold_replay_fixture_hashes_and_control_plane_anchors_are_stable() -> None:
    fixture = _load_fixture()

    for case in fixture["cases"]:
        output = case["output"]
        manifest = case["manifest"]
        checkpoint = case["checkpoint"]
        ledger_events = case["ledger"]["events"]
        content_hash = _sha256_rows(output["rows"])

        assert output["content_hash"] == content_hash
        assert checkpoint["output_content_hash"] == content_hash
        assert ledger_events == [
            {
                "event_type": "gold_artifact_published",
                "manifest_id": manifest["manifest_id"],
                "artifact_layer": "gold",
                "artifact_path": ledger_events[0]["artifact_path"],
                "artifact_content_hash": content_hash,
            }
        ]
        assert checkpoint["manifest_id"] == manifest["manifest_id"]
        assert checkpoint["effective_config_hash"] == manifest["effective_config_hash"]
        assert checkpoint["contract_ref"] == manifest["contract_ref"]
        assert (
            checkpoint["input_snapshot_content_hashes"]
            == manifest["input_snapshot_content_hashes"]
        )
        assert manifest["effective_config_artifact_id"]


def test_gold_replay_fixture_evidence_paths_exist() -> None:
    fixture = _load_fixture()
    evidence = [
        path for case in fixture["cases"] for path in case["evidence"]
    ] + fixture["out_of_scope"]["evidence"]

    missing = [path for path in evidence if not (ROOT / path).exists()]

    assert missing == []
