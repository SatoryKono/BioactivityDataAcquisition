"""Architecture contract checks enforcing ADR-056 Proof-or-Stop control plane."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


def test_proof_or_stop_policy_reuses_existing_gate_thresholds() -> None:
    policy = yaml.safe_load(
        (ROOT / "configs/quality/proof_or_stop_policy.yaml").read_text()
    )

    assert policy["evidence_store"]["automatic_ci_ingestion"] is False
    assert policy["evidence_store"]["create_decision_records"] is False
    assert not any(key in policy for key in ("budgets", "thresholds", "exemptions"))


def test_proof_bundle_schema_is_valid_draft_2020_12() -> None:
    schema = json.loads(
        (ROOT / "configs/quality/proof_or_stop_bundle.schema.json").read_text()
    )

    Draft202012Validator.check_schema(schema)


def test_staged_registry_starts_proof_gate_in_observe() -> None:
    registry = yaml.safe_load(
        (ROOT / "configs/quality/staged_enforcement_policy_registry.yaml").read_text()
    )
    proof_policy = next(
        item
        for item in registry["policies"]
        if item["check_name"] == "proof_or_stop_closeout"
    )

    assert proof_policy["current_stage"] == "observe"
    assert proof_policy["rollback_stage"] == "observe"
