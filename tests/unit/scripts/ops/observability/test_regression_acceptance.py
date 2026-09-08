"""Adversarial RF-005 checks: measurements, inventories and source binding."""

import hashlib
import json

import pytest

from scripts.ops.observability.grafana import regression_acceptance as subject

pytestmark = pytest.mark.unit


def put(root, name, payload):
    raw = json.dumps(payload).encode()
    (root / name).write_bytes(raw)
    return {"path": name, "sha256": hashlib.sha256(raw).hexdigest()}


@pytest.fixture
def bundle(tmp_path):
    evidence = put(
        tmp_path, "raw-evidence.json", {"fixture": "synthetic test evidence"}
    )
    contract = {
        "baseline_ref": "a" * 40,
        "candidate_ref": "b" * 40,
        "occurrence_id": "test",
        "time_range": {"from": "1000", "to": "61000", "timezone": "UTC"},
        "variable_matrix": [{"pipeline": "All"}],
        "viewports": [[1366, 768], [900, 768]],
    }
    common = {k: v for k, v in contract.items() if k != "baseline_ref"}
    common["dashboard_uids"] = sorted(subject.UIDS)
    row = {
        "id": "check",
        "actual": 1,
        "expected": 1,
        "tolerance": 0,
        "comparison": "eq",
        "reference": evidence,
        "evidence": evidence,
    }
    findings = [
        {
            **row,
            "id": name,
            "severity": "P1",
            "acceptance_test": name,
            "disposition": "FIXED",
            "before": evidence,
            "after": evidence,
        }
        for name in sorted(subject.FINDINGS)
    ]
    baseline = {
        "baseline_ref": contract["baseline_ref"],
        "approved_by": "owner",
        "findings": findings,
        "required_measurements": {
            name: {"checks": [row]} for name in subject.MEASUREMENT_GATES
        },
    }
    contract["baseline"] = put(tmp_path, "baseline.json", baseline)
    artifacts = {
        name: {**common, "measurements": [row]} for name in subject.MEASUREMENT_GATES
    }
    artifacts["findings"] = {**common, "findings": findings}
    artifacts["new_regressions"] = {
        **common,
        "findings": [],
        "reviewer": "reviewer",
        "search_evidence": evidence,
    }
    artifacts["operator"] = {
        **common,
        "page_goals_approved_by": "owner",
        "primary_role": "operator",
        "observations": [
            {
                "task_id": f"{uid}:Q{q}",
                "participant_type": "HUMAN",
                "participant_id": "P1",
                "attempt_kind": "first",
                "success": True,
                "first_correct_seconds": 3,
                "clicks": 1,
                "interactions": 2,
                "diagnostic_depth": 1,
                "back_navigation": 1,
                "context_loss": 0,
                "reviewer": "R1",
                "answer": "answer",
                "answer_key_evidence": evidence,
                "path": ["start", "target"],
                "evidence": evidence,
            }
            for uid in subject.UIDS
            for q in (1, 2, 3)
        ],
    }

    def save():
        contract["artifacts"] = {
            name: put(tmp_path, name + ".json", payload)
            for name, payload in artifacts.items()
        }
        path = tmp_path / "input.json"
        path.write_text(json.dumps(contract))
        return path

    return contract, baseline, artifacts, save


def test_complete_reviewed_receipts_pass(bundle):
    report = subject.evaluate(bundle[3]())
    assert report["release_passed"] is True
    human = report["gates"]["operator"]["statistics"][0]
    assert human["attempt_count"] == 21
    assert human["first_correct_seconds"] == {"sample_size": 21, "median": 3, "max": 3}


@pytest.fixture
def ai_bundle(bundle, tmp_path):
    contract, _, artifacts, _ = bundle
    contract["operator_acceptance_mode"] = "AI_SCENARIOS"
    decision = {
        "candidate_ref": contract["candidate_ref"],
        "acceptance_mode": "AI_SCENARIOS",
        "human_usability_status": "NOT_MEASURED",
        "task_count": 21,
        "approved_by": "owner",
        "approved_at": "2026-09-08",
        "reason": "Explicitly accept AI scenario checks only",
    }
    contract["operator_scope_decision"] = put(tmp_path, "decision.json", decision)
    artifacts["operator"]["human_usability_status"] = "NOT_MEASURED"
    for row in artifacts["operator"]["observations"]:
        row.update(
            participant_type="AI_AGENT",
            first_correct_seconds=None,
            elapsed_seconds=42,
            destination_verified=True,
            return_verified=True,
        )
    return bundle


def test_explicit_ai_scope_passes_without_claiming_human_usability(ai_bundle):
    report = subject.evaluate(ai_bundle[3]())
    assert report["release_passed"] is True
    gate = report["gates"]["operator"]
    assert gate["numerator"] == 21
    assert gate["human_required"] is False
    assert gate["human_usability_status"] == "NOT_MEASURED"
    human = gate["statistics"][0]
    assert human["attempt_count"] == human["success_count"] == 0
    assert human["first_correct_seconds"]["median"] is None
    ai = next(
        row
        for row in gate["statistics"]
        if row["participant_type"] == "AI_AGENT"
        and row["task_id"] == "ALL"
        and row["attempt_kind"] == "first"
    )
    assert ai["elapsed_seconds"] == {"sample_size": 21, "median": 42, "max": 42}
    assert ai["first_correct_seconds"]["sample_size"] == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("elapsed_seconds", None),
        ("elapsed_seconds", float("nan")),
        ("first_correct_seconds", 3),
        ("participant_type", "HUMAN"),
        ("destination_verified", False),
        ("return_verified", False),
        ("answer", ""),
        ("reviewer", ""),
        ("context_loss", 1),
    ],
)
def test_incomplete_ai_task_blocks_release(ai_bundle, field, value):
    row = next(
        r
        for r in ai_bundle[2]["operator"]["observations"]
        if r["task_id"].endswith(":Q3")
    )
    row[field] = value
    report = subject.evaluate(ai_bundle[3]())
    assert report["release_passed"] is False
    assert report["gates"]["operator"]["status"] == "CANNOT_VERIFY"


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_decision",
        "changed_hash",
        "wrong_candidate",
        "no_approval",
        "no_disclosure",
        "unknown_mode",
        "no_opt_in",
        "missing_task",
        "layout_failure",
    ],
)
def test_ai_scope_cannot_bypass_acceptance_contract(ai_bundle, tmp_path, mutation):
    contract, _, artifacts, save = ai_bundle
    if mutation == "missing_decision":
        del contract["operator_scope_decision"]
    elif mutation == "changed_hash":
        (tmp_path / "decision.json").write_text("{}")
    elif mutation in {"wrong_candidate", "no_approval"}:
        decision = json.loads((tmp_path / "decision.json").read_text())
        decision[
            "candidate_ref" if mutation == "wrong_candidate" else "approved_by"
        ] = ""
        contract["operator_scope_decision"] = put(tmp_path, "decision.json", decision)
    elif mutation == "no_disclosure":
        del artifacts["operator"]["human_usability_status"]
    elif mutation == "unknown_mode":
        contract["operator_acceptance_mode"] = "PASS"
    elif mutation == "no_opt_in":
        del contract["operator_acceptance_mode"]
    elif mutation == "missing_task":
        artifacts["operator"]["observations"].pop()
    elif mutation == "layout_failure":
        artifacts["layout"]["measurements"] = []
    assert subject.evaluate(save())["release_passed"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        "same_ref",
        "moving_window",
        "missing_p1",
        "different_sha",
        "different_window",
        "missing_uid",
        "empty_denominator",
        "missing_measurement",
        "duplicate",
        "nan",
        "lowered_limit",
        "ai",
        "no_timer",
        "context_loss",
        "target_miss",
    ],
)
def test_incomplete_or_forged_pass_fails_closed(bundle, mutation):
    contract, baseline, artifacts, save = bundle
    if mutation == "same_ref":
        contract["candidate_ref"] = contract["baseline_ref"]
    elif mutation == "moving_window":
        contract["time_range"] = {"from": "now-6h", "to": "now", "timezone": "UTC"}
    elif mutation == "missing_p1":
        artifacts["findings"]["findings"] = artifacts["findings"]["findings"][1:]
    elif mutation == "different_sha":
        artifacts["layout"]["candidate_ref"] = "c" * 40
    elif mutation == "different_window":
        artifacts["layout"]["time_range"] = {
            "from": "2000",
            "to": "61000",
            "timezone": "UTC",
        }
    elif mutation == "missing_uid":
        artifacts["layout"]["dashboard_uids"] = ["bioetl-runtime"]
    elif mutation in {"empty_denominator", "missing_measurement"}:
        artifacts["layout"]["measurements"] = []
    elif mutation == "duplicate":
        artifacts["layout"]["measurements"] *= 2
    elif mutation == "nan":
        artifacts["layout"]["measurements"][0]["actual"] = float("nan")
    elif mutation == "lowered_limit":
        artifacts["layout"]["measurements"][0]["tolerance"] = 99
    elif mutation == "ai":
        artifacts["operator"]["observations"][0]["participant_type"] = "AI_AGENT"
    elif mutation == "no_timer":
        artifacts["operator"]["observations"][0]["first_correct_seconds"] = None
    elif mutation == "context_loss":
        artifacts["operator"]["observations"][0]["context_loss"] = 1
    elif mutation == "target_miss":
        artifacts["operator"]["observations"][0]["first_correct_seconds"] = 30
    assert subject.evaluate(save())["release_passed"] is False


def test_hash_mutation_and_output_overwrite_rejected(bundle, tmp_path):
    source = bundle[3]()
    (tmp_path / "layout.json").write_text("{}")
    output = tmp_path / "release-gate.json"
    assert subject.write_report(source, output) is False
    original = output.read_bytes()
    with pytest.raises(FileExistsError):
        subject.write_report(source, output)
    assert output.read_bytes() == original


def test_missing_inputs_never_pass(tmp_path):
    assert subject.evaluate(tmp_path / "absent.json")["release_passed"] is False


def test_absent_raw_measurements_block_even_with_pass_receipts(bundle, tmp_path):
    source = bundle[3]()
    (tmp_path / "raw-evidence.json").unlink()
    assert subject.evaluate(source)["release_passed"] is False


def test_wrong_checkout_identity_blocks(bundle, tmp_path):
    output = tmp_path / "release.json"
    assert (
        subject.write_report(bundle[3](), output, expected_candidate="c" * 40) is False
    )
    assert (
        json.loads(output.read_text())["gates"]["checkout_identity"]["status"]
        == "CANNOT_VERIFY"
    )


def test_dirty_checkout_cannot_claim_candidate_acceptance(bundle, tmp_path):
    assert (
        subject.write_report(
            bundle[3](), tmp_path / "dirty.json", working_tree_clean=False
        )
        is False
    )


def test_zero_attempts_have_null_statistics():
    metrics = subject._operator_statistics([])
    assert len(metrics) == 4
    assert all(
        row["attempt_count"] == 0 and row["first_correct_seconds"]["median"] is None
        for row in metrics
    )


def test_path_outside_bundle_rejected(tmp_path):
    with pytest.raises(ValueError, match="stay in reviewer bundle"):
        subject._read(tmp_path, {"path": "../escape.json", "sha256": "0" * 64})


def test_explained_empty_scope_is_na_not_percentage():
    result = subject._measurements(
        {"measurements": [], "na_reason": "No eligible items"},
        {"checks": [], "na_reason": "No eligible items", "approved_by": "owner"},
    )
    assert result["status"] == "NA"
    assert result["percentage"] is None
    with pytest.raises(ValueError):
        subject._measurements({"measurements": []}, {"checks": []})
