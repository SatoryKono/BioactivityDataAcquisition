"""Tests for authorization-gated Proof-or-Stop evidence ingestion."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from memory.proof_gate import ProofIngestionAuthorizationError, ingest_bundle
from memory.proof import (
    assemble_bundle,
    build_receipt,
    load_schema,
    load_policy,
    verify_bundle,
)
from tests.helpers.clock import FIXED_TEST_TIME

pytestmark = pytest.mark.unit


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _init_repo(repo: Path) -> None:
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "proof@example.invalid")
    _git(repo, "config", "user.name", "Proof Test")
    (repo / "tracked.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(repo, "add", "tracked.py")
    _git(repo, "commit", "-m", "test fixture")


def _bundle(tmp_path: Path, *, status: str = "pass") -> tuple[Path, dict[str, object]]:
    repo = tmp_path / "repo"
    _init_repo(repo)
    policy = load_policy()
    skip_reason = None
    follow_up = None
    if status in {"skip", "unavailable"}:
        skip_reason = "runner unavailable"
        follow_up = "rerun on the supported CI runner"
    receipt = build_receipt(
        repo_root=repo,
        policy=policy,
        task_id="task-1",
        claim="tested",
        receipt_id="tests-1",
        producer="test_health",
        evidence_kind="tests",
        command="python -m scripts.engineering.qa run-tests --suite fast",
        argv=[],
        cwd=str(repo),
        started_at=FIXED_TEST_TIME.isoformat(),
        duration_ms=1,
        exit_code=0 if status == "pass" else 1 if status == "fail" else None,
        status=status,
        output_path=None,
        trust_tier="ci",
        skip_reason=skip_reason,
        follow_up=follow_up,
        ci_run_id="ci-1",
    )
    bundle = assemble_bundle(
        repo_root=repo,
        policy=policy,
        run_id="run-1",
        task_id="task-1",
        claim="tested",
        actor="agent",
        runtime="codex",
        trust_tier="ci",
        receipts=[receipt],
        ci_run_id="ci-1",
    )
    return repo, bundle


def _verification(*, bundle: dict[str, object], repo: Path) -> dict[str, object]:
    result = verify_bundle(
        bundle=bundle,
        repo_root=repo,
        policy=load_policy(),
        schema=load_schema(),
    )
    return {
        **result.to_dict(),
        "bundle_digest": bundle["bundle_digest"],
        "claim": bundle["claim"],
        "run_id": bundle["run_id"],
    }


def test_ingestion_fails_before_write_without_authority(tmp_path: Path) -> None:
    storage = tmp_path / "memory"
    repo, bundle = _bundle(tmp_path)

    with pytest.raises(ProofIngestionAuthorizationError):
        ingest_bundle(
            bundle=bundle,
            verification=_verification(bundle=bundle, repo=repo),
            storage_root=storage,
            repo_root=repo,
            expected_task_id="task-1",
            policy=load_policy(),
            schema=load_schema(),
            actor="agent",
            runtime="codex",
            memory_mode="read-only",
        )

    assert not storage.exists()


def test_ingestion_records_receipt_and_gate_but_no_decision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = tmp_path / "memory"
    repo, bundle = _bundle(tmp_path, status="fail")
    monkeypatch.setenv("BIOETL_AI_AGENT", "agent")
    monkeypatch.setenv("BIOETL_AI_RUNTIME", "codex")

    digests = ingest_bundle(
        bundle=bundle,
        verification=_verification(bundle=bundle, repo=repo),
        storage_root=storage,
        repo_root=repo,
        expected_task_id="task-1",
        policy=load_policy(),
        schema=load_schema(),
        actor="agent",
        runtime="codex",
        memory_mode="read-write",
    )

    assert len(digests) == 2
    evidence_files = list(storage.rglob("evidence.jsonl"))
    assert len(evidence_files) == 1
    rows = [json.loads(line) for line in evidence_files[0].read_text().splitlines()]
    assert {row["evidence_kind"] for row in rows} == {
        "proof_or_stop_gate",
        "proof_or_stop_receipt",
    }
    receipt = next(row for row in rows if row["evidence_kind"].endswith("receipt"))
    assert receipt["result"]["status"] == "fail"
    assert receipt["result"]["bundle_digest"] == bundle["bundle_digest"]
    assert not list(storage.rglob("decisions.jsonl"))


@pytest.mark.parametrize(
    ("status", "expected_outcome"),
    [
        ("pass", "ADMIT"),
        ("fail", "STOP"),
        ("skip", "DEGRADED"),
        ("unavailable", "DEGRADED"),
    ],
)
def test_ingestion_preserves_all_receipt_outcome_classes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: str,
    expected_outcome: str,
) -> None:
    repo, bundle = _bundle(tmp_path, status=status)
    monkeypatch.setenv("BIOETL_AI_AGENT", "agent")
    monkeypatch.setenv("BIOETL_AI_RUNTIME", "codex")

    ingest_bundle(
        bundle=bundle,
        verification=_verification(bundle=bundle, repo=repo),
        storage_root=tmp_path / "memory",
        repo_root=repo,
        expected_task_id="task-1",
        policy=load_policy(),
        schema=load_schema(),
        actor="agent",
        runtime="codex",
        memory_mode="read-write",
    )

    evidence_file = next((tmp_path / "memory").rglob("evidence.jsonl"))
    rows = [json.loads(line) for line in evidence_file.read_text().splitlines()]
    receipt = next(row for row in rows if row["evidence_kind"].endswith("receipt"))
    gate = next(row for row in rows if row["evidence_kind"].endswith("gate"))
    assert receipt["result"]["status"] == status
    assert gate["result"]["outcome"] == expected_outcome


def test_ingestion_rejects_tampered_bundle_before_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, bundle = _bundle(tmp_path)
    receipts = bundle["receipts"]
    assert isinstance(receipts, list) and isinstance(receipts[0], dict)
    receipts[0]["duration_ms"] = 999
    monkeypatch.setenv("BIOETL_AI_AGENT", "agent")
    monkeypatch.setenv("BIOETL_AI_RUNTIME", "codex")
    storage = tmp_path / "memory"

    with pytest.raises(ValueError, match="bundle_not_ingestible"):
        ingest_bundle(
            bundle=bundle,
            verification=_verification(bundle=bundle, repo=repo),
            storage_root=storage,
            repo_root=repo,
            expected_task_id="task-1",
            policy=load_policy(),
            schema=load_schema(),
            actor="agent",
            runtime="codex",
            memory_mode="read-write",
        )

    assert not storage.exists()


def test_ingestion_rejects_repository_worktree_and_task_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, bundle = _bundle(tmp_path)
    other_repo = tmp_path / "other-repo"
    _init_repo(other_repo)
    monkeypatch.setenv("BIOETL_AI_AGENT", "agent")
    monkeypatch.setenv("BIOETL_AI_RUNTIME", "codex")
    storage = tmp_path / "memory"

    with pytest.raises(ValueError, match="cross_scope"):
        ingest_bundle(
            bundle=bundle,
            verification=_verification(bundle=bundle, repo=repo),
            storage_root=storage,
            repo_root=other_repo,
            expected_task_id="another-task",
            policy=load_policy(),
            schema=load_schema(),
            actor="agent",
            runtime="codex",
            memory_mode="read-write",
        )

    assert not storage.exists()
