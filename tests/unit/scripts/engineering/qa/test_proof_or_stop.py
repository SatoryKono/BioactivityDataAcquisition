"""Unit tests for source-bound Proof-or-Stop assembly and verification."""

from __future__ import annotations

import copy
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

import memory.proof as proof
from memory.proof import (
    DEFAULT_SCHEMA_PATH,
    ProofError,
    ReceiptInput,
    assemble_bundle,
    build_receipt,
    canonical_digest,
    command_set_hash,
    discover_context,
    emit_receipt_from_environment,
    load_policy,
    load_schema,
    verify_bundle,
)
from memory.proof_cli import (
    _mutate_cross_scope,
    _mutate_degraded_full,
    _mutate_dirty_full,
    _mutate_failed_as_pass,
    _mutate_invalid_skip,
    _mutate_missing,
    _mutate_partial,
    _mutate_sharded_ci,
    _mutate_source,
    _mutate_stale_head,
    _mutate_tampered,
    _mutate_unavailable,
    _mutate_vendor_override,
    _scenario_cases,
    main,
)
from tests.helpers.clock import FIXED_TEST_TIME
from tests.helpers.isolated_git import init_tracked_fixture_repo

pytestmark = pytest.mark.unit


@pytest.fixture()
def proof_repo(tmp_path: Path) -> Path:
    return init_tracked_fixture_repo(tmp_path / "repo")


def _bundle(repo: Path, *, trust_tier: str = "ci") -> dict[str, object]:
    policy = load_policy()
    ci_run_id = "ci-123" if trust_tier == "ci" else None
    receipt = build_receipt(
        repo_root=repo,
        policy=policy,
        task_id="task-1",
        claim="tested",
        receipt_input=ReceiptInput(
            receipt_id="tests-1",
            producer="test_health",
            evidence_kind="tests",
            command="python -m scripts.engineering.qa run-tests --suite fast",
            argv=["--suite", "fast"],
            cwd=str(repo),
            started_at=FIXED_TEST_TIME.isoformat(),
            duration_ms=10,
            exit_code=0,
            status="pass",
            output_path=None,
        ),
        trust_tier=trust_tier,
        ci_run_id=ci_run_id,
    )
    return assemble_bundle(
        repo_root=repo,
        policy=policy,
        run_id="run-1",
        task_id="task-1",
        claim="tested",
        actor="test-agent",
        runtime="codex",
        trust_tier=trust_tier,
        receipts=[receipt],
        ci_run_id=ci_run_id,
    )


def _resign(bundle: dict[str, object]) -> None:
    receipts = bundle["receipts"]
    assert isinstance(receipts, list)
    for receipt in receipts:
        assert isinstance(receipt, dict)
        receipt["receipt_digest"] = canonical_digest(
            {key: value for key, value in receipt.items() if key != "receipt_digest"}
        )
    bundle["bundle_digest"] = canonical_digest(
        {key: value for key, value in bundle.items() if key != "bundle_digest"}
    )


def test_ci_receipt_admits_matching_tested_claim(proof_repo: Path) -> None:
    result = verify_bundle(
        bundle=_bundle(proof_repo),
        repo_root=proof_repo,
        policy=load_policy(),
        schema=load_schema(),
    )

    assert result.outcome == "ADMIT"
    assert result.claim_qualified is True


@pytest.mark.parametrize("other_worktree", [False, True])
def test_ci_receipt_from_another_workflow_is_rejected(
    proof_repo: Path, other_worktree: bool
) -> None:
    bundle = _bundle(proof_repo)
    receipt = bundle["receipts"][0]
    receipt["repository"]["ci_run_id"] = "another-workflow"
    if other_worktree:
        receipt["repository"]["worktree_id"] = "another-checkout"
    _resign(bundle)
    result = verify_bundle(
        bundle=bundle, repo_root=proof_repo, policy=load_policy(), schema=load_schema()
    )
    assert result.outcome == "STOP"
    assert "cross_scope:ci_run_id" in result.errors


def test_ci_receipt_from_same_workflow_other_checkout_is_accepted(
    proof_repo: Path,
) -> None:
    bundle = _bundle(proof_repo)
    bundle["receipts"][0]["repository"]["worktree_id"] = "another-checkout"
    _resign(bundle)
    result = verify_bundle(
        bundle=bundle, repo_root=proof_repo, policy=load_policy(), schema=load_schema()
    )
    assert result.outcome == "ADMIT"


def test_local_digest_only_receipt_is_degraded(proof_repo: Path) -> None:
    result = verify_bundle(
        bundle=_bundle(proof_repo, trust_tier="local_single_host"),
        repo_root=proof_repo,
        policy=load_policy(),
        schema=load_schema(),
    )

    assert result.outcome == "DEGRADED"
    assert result.claim_qualified is False


def test_discover_context_uses_policy_timeout_for_full_diffs(
    proof_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = load_policy()
    observed: list[float] = []
    original_git = proof._git

    def recording_git(
        repo_root: Path,
        *args: str,
        timeout: float = proof.DEFAULT_GIT_TIMEOUT_SECONDS,
    ) -> bytes:
        if args and args[0] == "diff":
            observed.append(timeout)
        return original_git(repo_root, *args, timeout=timeout)

    monkeypatch.setattr(proof, "_git", recording_git)

    _, clean_source = discover_context(proof_repo, policy=policy, claim="tested")

    assert observed == [300.0]
    assert clean_source["dirty"] is False

    (proof_repo / "tracked.py").write_text("VALUE = 2\n", encoding="utf-8")
    _, dirty_source = discover_context(proof_repo, policy=policy, claim="tested")

    assert observed == [300.0, 300.0]
    assert dirty_source["dirty"] is True


@pytest.mark.parametrize("configured", [True, "180", 0, 301])
def test_discover_context_rejects_invalid_git_diff_timeout(
    proof_repo: Path, configured: object
) -> None:
    policy = load_policy()
    policy["source_binding"]["git_diff_timeout_seconds"] = configured

    with pytest.raises(ProofError, match="git_diff_timeout_seconds"):
        discover_context(proof_repo, policy=policy, claim="tested")


def test_failed_result_cannot_be_reported_as_pass(proof_repo: Path) -> None:
    bundle = copy.deepcopy(_bundle(proof_repo))
    receipts = bundle["receipts"]
    assert isinstance(receipts, list) and isinstance(receipts[0], dict)
    receipts[0]["exit_code"] = 1
    _resign(bundle)

    result = verify_bundle(
        bundle=bundle,
        repo_root=proof_repo,
        policy=load_policy(),
        schema=load_schema(),
    )

    assert result.outcome == "STOP"
    assert "failed_reported_as_pass:tests" in result.errors


def test_stale_source_is_rejected(proof_repo: Path) -> None:
    bundle = copy.deepcopy(_bundle(proof_repo))
    source = bundle["source"]
    assert isinstance(source, dict)
    source["material_hash"] = "0" * 64
    _resign(bundle)

    result = verify_bundle(
        bundle=bundle,
        repo_root=proof_repo,
        policy=load_policy(),
        schema=load_schema(),
    )

    assert result.outcome == "STOP"
    assert "stale_bundle:material_hash" in result.errors


def test_existing_producer_emits_only_when_capture_is_enabled(
    proof_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert (
        emit_receipt_from_environment(
            repo_root=proof_repo,
            producer="test_health",
            evidence_kind="tests",
            command="python -m scripts.engineering.qa run-tests",
            status="pass",
            exit_code=0,
            output_path=None,
        )
        is None
    )

    monkeypatch.setenv("PROOF_OR_STOP_RUN_ID", "run-1")
    monkeypatch.setenv("PROOF_OR_STOP_TASK_ID", "task-1")
    monkeypatch.setenv("PROOF_OR_STOP_CLAIM", "tested")
    monkeypatch.setenv("PROOF_OR_STOP_TRUST_TIER", "ci")
    monkeypatch.setenv("GITHUB_RUN_ID", "ci-1")
    monkeypatch.setenv("PROOF_OR_STOP_RECEIPT_DIR", str(proof_repo / "receipts"))

    path = emit_receipt_from_environment(
        repo_root=proof_repo,
        producer="test_health",
        evidence_kind="tests",
        command="python -m scripts.engineering.qa run-tests",
        status="pass",
        exit_code=0,
        output_path=None,
    )

    assert path is not None and path.exists()


def test_pilot_covers_adversarial_matrix(proof_repo: Path, tmp_path: Path) -> None:
    output = tmp_path / "pilot.json"
    result = main(
        [
            "pilot",
            "--repo-root",
            str(proof_repo),
            "--schema",
            str(DEFAULT_SCHEMA_PATH),
            "--output",
            str(output),
        ]
    )

    assert result == 0
    payload = output.read_text(encoding="utf-8")
    assert '"scenario_count": 15' in payload
    assert '"false_admit_count": 0' in payload
    assert '"tamper_accept_count": 0' in payload
    assert '"recommendation": "GO"' in payload
    assert '"reason_code_coverage"' in payload
    assert '"deterministic_replay"' in payload
    assert output.with_suffix(".md").is_file()
    _assert_scenario_routing()


def _full_suite_argv() -> list[str]:
    return [
        "python",
        "-m",
        "scripts.engineering.dev",
        "run-tests",
        "all",
        "--junitxml=reports/full.xml",
        "-p",
        "no:cacheprovider",
        "--basetemp=/tmp/full-suite",
        "--vcr-record=none",
    ]


def test_canonical_full_suite_wrapper_is_qualified_in_ci(proof_repo: Path) -> None:
    bundle = _bundle(proof_repo)
    receipt = bundle["receipts"][0]
    receipt["argv"] = _full_suite_argv()
    receipt["command"] = " ".join(receipt["argv"])
    _resign(bundle)
    result = verify_bundle(
        bundle=bundle, repo_root=proof_repo, policy=load_policy(), schema=load_schema()
    )
    assert result.outcome == "ADMIT"
    assert result.claim_qualified is True


@pytest.mark.parametrize(
    "trailing",
    [
        ["-k", "one_test"],
        ["-m", "unit"],
        ["tests/unit/"],
        ["--collect-only"],
        ["--ignore=tests/integration"],
        ["--vcr-record=all"],
        [";", "true"],
        ["--junitxml=other.xml"],
        ["-p", "no:cacheprovider"],
    ],
)
def test_full_suite_wrapper_rejects_selection_or_extra_arguments(
    proof_repo: Path, trailing: list[str]
) -> None:
    bundle = _bundle(proof_repo)
    receipt = bundle["receipts"][0]
    receipt["argv"] = _full_suite_argv() + trailing
    receipt["command"] = " ".join(receipt["argv"])
    _resign(bundle)
    result = verify_bundle(
        bundle=bundle, repo_root=proof_repo, policy=load_policy(), schema=load_schema()
    )
    assert result.outcome == "STOP"
    assert "command_not_authorized:tests" in result.errors


@pytest.mark.parametrize(
    "damage",
    [
        "missing_argv",
        "different_argv",
        "different_lane",
        "prefix_suffix",
        "missing_junit",
        "missing_basetemp",
        "missing_offline",
        "missing_plugin",
        "malformed_quotes",
    ],
)
def test_full_suite_wrapper_is_fail_closed(proof_repo: Path, damage: str) -> None:
    bundle = _bundle(proof_repo)
    receipt = bundle["receipts"][0]
    argv = _full_suite_argv()
    if damage == "different_lane":
        argv[4] = "unit"
    elif damage == "prefix_suffix":
        argv[4] = "all-untrusted"
    elif damage == "missing_junit":
        argv.remove("--junitxml=reports/full.xml")
    elif damage == "missing_basetemp":
        argv.remove("--basetemp=/tmp/full-suite")
    elif damage == "missing_offline":
        argv.remove("--vcr-record=none")
    elif damage == "missing_plugin":
        argv.remove("-p")
        argv.remove("no:cacheprovider")
    receipt["command"] = " ".join(argv)
    receipt["argv"] = argv
    if damage == "missing_argv":
        receipt["argv"] = []
    elif damage == "different_argv":
        receipt["argv"] = [*argv, "--collect-only"]
    elif damage == "malformed_quotes":
        receipt["command"] += " '"
    _resign(bundle)
    result = verify_bundle(
        bundle=bundle, repo_root=proof_repo, policy=load_policy(), schema=load_schema()
    )
    assert result.outcome == "STOP"
    assert "command_not_authorized:tests" in result.errors


def _mock_bundle() -> dict[str, Any]:
    bundle: dict[str, Any] = {
        "source": {"head_sha": "original_head"},
        "receipts": [
            {
                "source": {"head_sha": "original_head"},
                "exit_code": 0,
                "status": "pass",
                "skip_reason": "original",
                "follow_up": "original",
                "duration_ms": 10,
                "producer": "original_producer",
                "task_id": "original-task",
                "repository": {
                    "repo_id": "original-repo",
                    "worktree_id": "original-worktree",
                    "ci_run_id": "original-ci-run",
                },
            }
        ],
        "claim": "tested",
        "acceptance": {"require_full_trust": False},
    }
    _resign(bundle)
    return bundle


def _mock_policy() -> dict[str, Any]:
    return {
        "claims": {"ready_to_merge": {"required_evidence": ["evidence1", "evidence2"]}},
        "evidence_kinds": {
            "evidence1": {
                "authorized_producers": ["test_health"],
                "command_families": ["python -m pytest"],
            },
            "evidence2": {
                "authorized_producers": ["pretest_guardrails"],
                "command_families": [
                    "bash scripts/engineering/dev/pretest_guardrails.sh"
                ],
            },
        },
    }


def _assert_digests(bundle: dict[str, Any]) -> None:
    for receipt in bundle["receipts"]:
        assert receipt["receipt_digest"] == canonical_digest(
            {key: value for key, value in receipt.items() if key != "receipt_digest"}
        )
    assert bundle["bundle_digest"] == canonical_digest(
        {key: value for key, value in bundle.items() if key != "bundle_digest"}
    )


_HASH_FIELD_MUTATORS = frozenset({"task_diff_hash", "policy_hash", "command_set_hash"})
_SCENARIO_ROUTING_SPEC: tuple[tuple[str, str, bool, str], ...] = (
    ("stale_source", "STOP", True, "stale_head"),
    ("stale_diff", "STOP", True, "task_diff_hash"),
    ("policy_drift", "STOP", True, "policy_hash"),
    ("command_set_drift", "STOP", True, "command_set_hash"),
    ("missing_receipt", "STOP", True, "missing"),
    ("failed_reported_as_pass", "STOP", True, "failed_as_pass"),
    ("invalid_skip", "STOP", True, "invalid_skip"),
    ("unavailable_not_pass", "DEGRADED", True, "unavailable"),
    ("tampered_receipt", "STOP", True, "tampered"),
    ("unauthorized_vendor_override", "STOP", True, "vendor_override"),
    ("cross_scope_receipt", "STOP", True, "cross_scope"),
    ("dirty_untracked_full_claim", "STOP", False, "dirty_full"),
    ("sharded_ci_identity", "ADMIT", True, "sharded_ci"),
    ("degraded_not_full", "STOP", True, "degraded_full"),
    ("partial_fail_fast_receipt", "STOP", True, "partial"),
)


def _scenario_mutators() -> dict[str, Callable[[dict[str, Any], dict[str, Any]], None]]:
    return {
        "cross_scope": _mutate_cross_scope,
        "degraded_full": _mutate_degraded_full,
        "dirty_full": _mutate_dirty_full,
        "failed_as_pass": _mutate_failed_as_pass,
        "invalid_skip": _mutate_invalid_skip,
        "missing": _mutate_missing,
        "partial": _mutate_partial,
        "sharded_ci": _mutate_sharded_ci,
        "stale_head": _mutate_stale_head,
        "tampered": _mutate_tampered,
        "unavailable": _mutate_unavailable,
        "vendor_override": _mutate_vendor_override,
    }


def _assert_one_scenario(
    name: str,
    expected: str,
    check_source: bool,
    mutator_key: str,
) -> None:
    cases = {
        case_name: (outcome, source_check, mutator)
        for case_name, outcome, source_check, mutator in _scenario_cases()
    }
    actual_expected, actual_check_source, actual_mutate = cases[name]
    assert actual_expected == expected
    assert actual_check_source is check_source
    if mutator_key in _HASH_FIELD_MUTATORS:
        bundle = _mock_bundle()
        expected_bundle = copy.deepcopy(bundle)
        _mutate_source(expected_bundle, mutator_key)
        actual_mutate(bundle, {})
        assert bundle == expected_bundle
        return
    assert actual_mutate is _scenario_mutators()[mutator_key]


def _assert_scenario_routing() -> None:
    cases = _scenario_cases()
    spec_names = [
        name for name, _expected, _check_source, _key in _SCENARIO_ROUTING_SPEC
    ]
    case_names = [name for name, _expected, _check_source, _mutate in cases]
    assert len(cases) == len(spec_names) == 15
    assert len(set(spec_names)) == 15
    assert case_names == spec_names
    for name, expected, check_source, mutator_key in _SCENARIO_ROUTING_SPEC:
        _assert_one_scenario(name, expected, check_source, mutator_key)


@pytest.mark.parametrize(
    ("name", "expected", "check_source", "mutator_key"),
    _SCENARIO_ROUTING_SPEC,
)
def test_scenario_cases_routing(
    name: str,
    expected: str,
    check_source: bool,
    mutator_key: str,
) -> None:
    _assert_one_scenario(name, expected, check_source, mutator_key)


def test_mutate_stale_head() -> None:
    b = _mock_bundle()
    _mutate_stale_head(b, {})
    assert b["source"]["head_sha"] == "0" * 40
    assert b["receipts"][0]["source"]["head_sha"] == "0" * 40
    _assert_digests(b)


def test_mutate_missing() -> None:
    b = _mock_bundle()
    _mutate_missing(b, {})
    assert b["receipts"] == []
    _assert_digests(b)


def test_mutate_failed_as_pass() -> None:
    b = _mock_bundle()
    _mutate_failed_as_pass(b, {})
    assert b["receipts"][0]["exit_code"] == 1
    _assert_digests(b)


def test_mutate_invalid_skip() -> None:
    b = _mock_bundle()
    _mutate_invalid_skip(b, {})
    r = b["receipts"][0]
    assert r["status"] == "skip"
    assert r["exit_code"] is None
    assert r["skip_reason"] is None
    assert r["follow_up"] is None
    _assert_digests(b)


def test_mutate_unavailable() -> None:
    b = _mock_bundle()
    _mutate_unavailable(b, {})
    r = b["receipts"][0]
    assert r["status"] == "unavailable"
    assert r["exit_code"] is None
    assert r["skip_reason"] == "runner dependency unavailable"
    assert r["follow_up"] == "rerun on the supported CI runner"
    _assert_digests(b)


def test_mutate_tampered() -> None:
    b = _mock_bundle()
    original_receipt_digest = b["receipts"][0]["receipt_digest"]
    _mutate_tampered(b, {})
    r = b["receipts"][0]
    assert r["duration_ms"] == 999
    assert r["receipt_digest"] == original_receipt_digest
    assert r["receipt_digest"] != canonical_digest(
        {key: value for key, value in r.items() if key != "receipt_digest"}
    )
    assert b["bundle_digest"] == canonical_digest(
        {key: value for key, value in b.items() if key != "bundle_digest"}
    )


def test_mutate_vendor_override() -> None:
    b = _mock_bundle()
    _mutate_vendor_override(b, {})
    assert b["receipts"][0]["producer"] == "optional_vendor_evaluator"
    _assert_digests(b)


def test_mutate_cross_scope() -> None:
    b = _mock_bundle()
    _mutate_cross_scope(b, {})
    r = b["receipts"][0]
    assert r["task_id"] == "another-task"
    assert r["repository"]["repo_id"] == "another-repository"
    assert r["repository"]["worktree_id"] == "another-worktree"
    assert r["repository"]["ci_run_id"] == "another-ci-run"
    _assert_digests(b)


def test_mutate_dirty_full() -> None:
    b = _mock_bundle()
    p = _mock_policy()
    _mutate_dirty_full(b, p)
    assert b["source"]["dirty"] is True
    assert b["source"]["untracked_paths"] == ["untracked.py"]
    assert b["source"]["command_set_hash"] == command_set_hash(p, "ready_to_merge")
    assert b["claim"] == "ready_to_merge"
    assert b["acceptance"]["required_evidence"] == ["evidence1", "evidence2"]
    assert b["acceptance"]["require_full_trust"] is True
    assert b["receipts"][0]["source"]["dirty"] is True
    _assert_digests(b)
    changed_policy = copy.deepcopy(p)
    changed_policy["evidence_kinds"]["evidence1"]["command_families"].append(
        "python -m scripts.engineering.qa run-tests"
    )
    assert b["source"]["command_set_hash"] != command_set_hash(
        changed_policy, "ready_to_merge"
    )


def test_mutate_sharded_ci() -> None:
    b = _mock_bundle()
    _mutate_sharded_ci(b, {})
    assert b["receipts"][0]["repository"]["worktree_id"] == "another-shard"
    _assert_digests(b)


def test_mutate_degraded_full() -> None:
    b = _mock_bundle()
    _mutate_degraded_full(b, {})
    assert b["receipts"][0]["status"] == "unavailable"
    assert b["acceptance"]["require_full_trust"] is True
    _assert_digests(b)


def test_mutate_partial() -> None:
    b = _mock_bundle()
    _mutate_partial(b, {})
    assert b["receipts"][0]["status"] == "fail"
    assert b["receipts"][0]["exit_code"] == 1
    _assert_digests(b)
