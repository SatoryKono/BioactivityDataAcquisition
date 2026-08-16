"""Unit tests for source-bound Proof-or-Stop assembly and verification."""

from __future__ import annotations

import copy
import subprocess
from pathlib import Path

import pytest

import memory.proof as proof
from memory.proof import (
    DEFAULT_SCHEMA_PATH,
    ProofError,
    assemble_bundle,
    build_receipt,
    canonical_digest,
    discover_context,
    emit_receipt_from_environment,
    load_policy,
    load_schema,
    verify_bundle,
)
from memory.proof_cli import main
from tests.helpers.clock import FIXED_TEST_TIME

pytestmark = pytest.mark.unit


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture()
def proof_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "proof@example.invalid")
    _git(repo, "config", "user.name", "Proof Test")
    (repo / "tracked.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(repo, "add", "tracked.py")
    _git(repo, "commit", "-m", "test fixture")
    return repo


def _bundle(repo: Path, *, trust_tier: str = "ci") -> dict[str, object]:
    policy = load_policy()
    ci_run_id = "ci-123" if trust_tier == "ci" else None
    receipt = build_receipt(
        repo_root=repo,
        policy=policy,
        task_id="task-1",
        claim="tested",
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

    discover_context(proof_repo, policy=policy, claim="tested")

    assert observed == [180.0, 180.0]


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
