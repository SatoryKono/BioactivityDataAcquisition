"""Architecture contract checks enforcing ADR-056 Proof-or-Stop control plane."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

pytestmark = pytest.mark.architecture

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


def test_staged_registry_promotes_proof_gate_to_soft_fail() -> None:
    """#8415: first enforcement promotion is soft_fail with observe rollback."""
    registry = yaml.safe_load(
        (ROOT / "configs/quality/staged_enforcement_policy_registry.yaml").read_text(
            encoding="utf-8"
        )
    )
    proof_policy = next(
        item
        for item in registry["policies"]
        if item["check_name"] == "proof_or_stop_closeout"
    )

    assert proof_policy["current_stage"] == "soft_fail"
    assert proof_policy["rollback_stage"] == "observe"
    assert proof_policy["domain_engine"] is False
    assert "adversarial_pilot_zero_false_admit" in proof_policy["promotion_requirements"]
    assert "adversarial_pilot_zero_tamper_accepts" in proof_policy["promotion_requirements"]
    assert "two_clean_ci_observation_runs" in proof_policy["promotion_requirements"]
    assert proof_policy.get("next_stage") == "hard_fail"
    assert registry["linked_issue"] == "#8415"
    assert registry["owner"]
    assert registry["review_cadence"]
    assert registry["escalation"]


def test_ci_runs_the_adversarial_pilot_before_staged_enforcement() -> None:
    workflow = (ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8")

    assert "proof-or-stop pilot" in workflow
    assert workflow.index("proof-or-stop pilot") < workflow.index(
        "Apply staged Proof-or-Stop enforcement"
    )


def test_ci_staged_enforcement_honors_soft_fail_and_hard_fail() -> None:
    """Validation gate: CI must warn on soft_fail and block only on hard_fail."""
    workflow = (ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8")
    apply_step = workflow.split("Apply staged Proof-or-Stop enforcement", 1)[1]

    assert '== "hard_fail"' in apply_step
    assert '== "soft_fail"' in apply_step
    assert "::warning::" in apply_step
    assert "::error::" in apply_step
    assert "observe stage" in apply_step


def test_proof_or_stop_contract_documents_rollback_without_gate_disable() -> None:
    contract = (
        ROOT / "docs/04-reference/contracts/proof-or-stop-evidence.md"
    ).read_text(encoding="utf-8")
    compact = " ".join(contract.split())

    assert "Rollback returns the entry to `observe`" in compact
    assert "existing evidence remains immutable" in compact
    assert "Branch-protection changes are outside this mechanism" in compact
    assert "do not disable existing quality" in compact
    assert "soft_fail" in compact
    assert "hard_fail" in compact
