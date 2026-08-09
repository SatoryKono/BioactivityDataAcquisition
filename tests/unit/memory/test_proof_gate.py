"""Tests for authorization-gated Proof-or-Stop evidence ingestion."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from memory.proof_gate import ProofIngestionAuthorizationError, ingest_bundle
from memory.proof import (
    assemble_bundle,
    build_receipt,
    load_policy,
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _bundle(tmp_path: Path) -> dict[str, object]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "proof@example.invalid")
    _git(repo, "config", "user.name", "Proof Test")
    (repo / "tracked.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(repo, "add", "tracked.py")
    _git(repo, "commit", "-m", "test fixture")
    policy = load_policy()
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
        started_at=datetime.now(UTC).isoformat(),
        duration_ms=1,
        exit_code=0,
        status="pass",
        output_path=None,
        trust_tier="ci",
        ci_run_id="ci-1",
    )
    return assemble_bundle(
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


def test_ingestion_fails_before_write_without_authority(tmp_path: Path) -> None:
    storage = tmp_path / "memory"

    with pytest.raises(ProofIngestionAuthorizationError):
        ingest_bundle(
            bundle=_bundle(tmp_path),
            verification={"outcome": "ADMIT", "claim_qualified": True},
            storage_root=storage,
            actor="agent",
            runtime="codex",
            memory_mode="read-only",
        )

    assert not storage.exists()


def test_ingestion_records_receipt_and_gate_but_no_decision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = tmp_path / "memory"
    monkeypatch.setenv("BIOETL_AI_AGENT", "agent")

    digests = ingest_bundle(
        bundle=_bundle(tmp_path),
        verification={
            "outcome": "STOP",
            "claim_qualified": False,
            "errors": ["failed_receipt:tests"],
            "degradations": [],
        },
        storage_root=storage,
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
    assert not list(storage.rglob("decisions.jsonl"))
