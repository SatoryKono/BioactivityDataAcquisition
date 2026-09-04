"""Integration tests for the explicit Proof-or-Stop ingestion CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from memory.proof import (
    ReceiptInput,
    assemble_bundle,
    build_receipt,
    load_policy,
    load_schema,
    verify_bundle,
)
from memory.proof_cli import main
from tests.helpers.clock import FIXED_TEST_TIME
from tests.helpers.isolated_git import init_tracked_fixture_repo

pytestmark = pytest.mark.integration


def _artifacts(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo = init_tracked_fixture_repo(tmp_path / "repo")
    policy = load_policy()
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
            argv=[],
            cwd=str(repo),
            started_at=FIXED_TEST_TIME.isoformat(),
            duration_ms=1,
            exit_code=0,
            status="pass",
            output_path=None,
        ),
        trust_tier="ci",
        ci_run_id="ci-1",
    )
    bundle = assemble_bundle(
        repo_root=repo,
        policy=policy,
        run_id="run-1",
        task_id="task-1",
        claim="tested",
        actor="producer",
        runtime="github-actions",
        trust_tier="ci",
        receipts=[receipt],
        ci_run_id="ci-1",
    )
    result = verify_bundle(
        bundle=bundle,
        repo_root=repo,
        policy=policy,
        schema=load_schema(),
    )
    verification = {
        **result.to_dict(),
        "bundle_digest": bundle["bundle_digest"],
        "claim": bundle["claim"],
        "run_id": bundle["run_id"],
    }
    bundle_path = tmp_path / "bundle.json"
    verification_path = tmp_path / "verification.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    verification_path.write_text(json.dumps(verification), encoding="utf-8")
    return repo, bundle_path, verification_path


def test_authorized_cli_ingestion_is_source_bound_and_decision_free(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, bundle, verification = _artifacts(tmp_path)
    storage = tmp_path / "memory"
    monkeypatch.setenv("BIOETL_AI_MEMORY_MODE", "read-write")
    monkeypatch.setenv("BIOETL_AI_AGENT", "ingester")
    monkeypatch.setenv("BIOETL_AI_RUNTIME", "codex")

    exit_code = main(
        [
            "ingest",
            "--repo-root",
            str(repo),
            "--task-id",
            "task-1",
            "--bundle",
            str(bundle),
            "--verification",
            str(verification),
            "--storage-root",
            str(storage),
            "--actor",
            "ingester",
            "--runtime",
            "codex",
        ]
    )

    assert exit_code == 0
    assert len(list(storage.rglob("evidence.jsonl"))) == 1
    assert not list(storage.rglob("decisions.jsonl"))


def test_cli_rejects_verification_for_another_bundle_before_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, bundle, verification = _artifacts(tmp_path)
    payload = json.loads(verification.read_text(encoding="utf-8"))
    payload["bundle_digest"] = "0" * 64
    verification.write_text(json.dumps(payload), encoding="utf-8")
    storage = tmp_path / "memory"
    monkeypatch.setenv("BIOETL_AI_MEMORY_MODE", "read-write")
    monkeypatch.setenv("BIOETL_AI_AGENT", "ingester")
    monkeypatch.setenv("BIOETL_AI_RUNTIME", "codex")

    exit_code = main(
        [
            "ingest",
            "--repo-root",
            str(repo),
            "--task-id",
            "task-1",
            "--bundle",
            str(bundle),
            "--verification",
            str(verification),
            "--storage-root",
            str(storage),
            "--actor",
            "ingester",
            "--runtime",
            "codex",
        ]
    )

    assert exit_code == 2
    assert not storage.exists()
