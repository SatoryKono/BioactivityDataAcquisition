"""Explicit command qualification with real owned workers and synthetic evidence."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import stat
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from memory import proof
from scripts.engineering.repo import closeout_runtime as runtime
from scripts.engineering.repo import closeout_state as state
from scripts.engineering.repo import closeout_worker as worker
from scripts.engineering.repo.process_deadline import ProcessResult
from tests.helpers.clock import FIXED_TEST_TIME
from tests.helpers.isolated_git import (
    init_tracked_fixture_repo,
    isolated_git_env,
    run_isolated_git,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = init_tracked_fixture_repo(tmp_path / "repo")
    registry = root / "configs/quality/agent_guard_budget_surfaces.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "owner": "fixture",
                "surfaces": [
                    {"pattern": "configs/quality/*budget*.json", "kind": "budget"}
                ],
            }
        ),
        encoding="utf-8",
    )
    for args in (
        ("add", "."),
        ("commit", "--no-gpg-sign", "--no-verify", "-qm", "synthetic guard registry"),
        ("update-ref", "refs/remotes/origin/main", "HEAD"),
    ):
        result = run_isolated_git(root, *args)
        assert result.returncode == 0, result.stderr
    return root


def _bundle(root: Path, *, consumer: str = "codex", claim: str = "done") -> Path:
    """Synthetic self-declared CI evidence must never grant local admission."""
    policy = proof.load_policy()
    receipts = []
    for kind in policy["claims"][claim]["required_evidence"]:
        owner = policy["evidence_kinds"][kind]
        receipts.append(
            proof.build_receipt(
                repo_root=root,
                policy=policy,
                task_id="task-39",
                claim=claim,
                receipt_input=proof.ReceiptInput(
                    receipt_id=kind,
                    producer=owner["authorized_producers"][0],
                    evidence_kind=kind,
                    command=owner["command_families"][0],
                    argv=[],
                    cwd=str(root),
                    started_at=FIXED_TEST_TIME.isoformat(),
                    duration_ms=1,
                    exit_code=0,
                    status="pass",
                    output_path=None,
                ),
                trust_tier="ci",
                ci_run_id="synthetic-fixture-not-real-CI",
            )
        )
    bundle = proof.assemble_bundle(
        repo_root=root,
        policy=policy,
        run_id="synthetic-run",
        task_id="task-39",
        claim=claim,
        actor="fixture",
        runtime=consumer,
        trust_tier="ci",
        receipts=receipts,
        ci_run_id="synthetic-fixture-not-real-CI",
    )
    path = root / "reports/quality/proof-or-stop/bundle.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bundle), encoding="utf-8")
    return path


def _verify(root: Path, path: Path, **overrides):
    arguments = {"task_id": "task-39", "runtime": "codex", "claim": "done"}
    return runtime.verify(root, path, **{**arguments, **overrides})


@pytest.mark.parametrize(
    "consumer,claim",
    [
        ("codex", "done"),
        ("junie", "done"),
        ("devin", "done"),
        ("codex", "ready_to_merge"),
    ],
)
def test_real_worker_caps_declared_ci_to_local_degraded(repository, consumer, claim):
    path = _bundle(repository, consumer=consumer, claim=claim)
    result = _verify(repository, path, runtime=consumer, claim=claim)
    assert result["outcome"] == "DEGRADED", result
    assert result["core_outcome"] == "ADMIT"
    assert result["exit_code"] == 3
    assert all(
        result[key] is False
        for key in (
            "claim_qualified",
            "runtime_admission",
            "ci_acceptance",
            "native_event_observed",
        )
    )


def test_real_worker_accepts_equivalent_metadata_search_paths(
    repository: Path, tmp_path: Path
) -> None:
    metadata_root = tmp_path / "editable-site"
    metadata = metadata_root / "closeout_editable-1.0.dist-info/METADATA"
    metadata.parent.mkdir(parents=True)
    metadata.write_text(
        "Metadata-Version: 2.1\nName: Closeout-Editable\nVersion: 1.0\n",
        encoding="utf-8",
    )
    original = runtime._worker_argv

    def duplicate_entry(*args):
        command = list(original(*args))
        entry = command.index("-c") + 1
        command[entry] = (
            f"import sys;sys.path[:0]=[{str(metadata_root)!r},{str(metadata_root)!r}];"
            + command[entry]
        )
        return tuple(command)

    with (
        patch.object(sys, "path", [str(metadata_root), *sys.path]),
        patch.object(runtime, "_worker_argv", duplicate_entry),
    ):
        result = _verify(repository, _bundle(repository))
    assert result["outcome"] == "DEGRADED", result
    assert result["core_outcome"] == "ADMIT"
    assert result["claim_qualified"] is False


@pytest.mark.parametrize("change", ["working", "index", "head", "branch"])
def test_stale_source_or_branch_never_qualifies(repository, change):
    path = _bundle(repository)
    original = (repository / "tracked.py").read_bytes()
    (repository / "tracked.py").write_text("VALUE = 9\n", encoding="utf-8")
    if change in {"index", "head"}:
        assert run_isolated_git(repository, "add", "tracked.py").returncode == 0
    if change == "index":
        (repository / "tracked.py").write_bytes(original)
    if change == "head":
        assert (
            run_isolated_git(
                repository,
                "commit",
                "--no-gpg-sign",
                "--no-verify",
                "-qm",
                "new fixture revision",
            ).returncode
            == 0
        )
    if change == "branch":
        (repository / "tracked.py").write_bytes(original)
        assert (
            run_isolated_git(repository, "switch", "-c", "other-fixture").returncode
            == 0
        )
    result = _verify(repository, path)
    assert result["outcome"] == "STOP", result
    assert result["claim_qualified"] is False


@pytest.mark.parametrize(
    "field,value",
    [("task_id", "other-task"), ("runtime", "junie"), ("claim", "tested")],
)
def test_expected_scope_is_bound(repository, field, value):
    result = _verify(repository, _bundle(repository), **{field: value})
    assert result["outcome"] == "STOP", result


@pytest.mark.parametrize("mutation", ["missing", "skip", "fail"])
def test_required_receipt_failures_are_not_pass(repository, mutation):
    path = _bundle(repository)
    value = json.loads(path.read_bytes())
    if mutation == "missing":
        value["receipts"].pop()
    else:
        row = value["receipts"][0]
        row.update(
            status=mutation,
            exit_code=None if mutation == "skip" else 1,
            skip_reason="synthetic unavailable" if mutation == "skip" else None,
            follow_up="repeat fixture" if mutation == "skip" else None,
        )
        row["receipt_digest"] = proof.canonical_digest(
            {k: v for k, v in row.items() if k != "receipt_digest"}
        )
    value["bundle_digest"] = proof.canonical_digest(
        {k: v for k, v in value.items() if k != "bundle_digest"}
    )
    path.write_text(json.dumps(value), encoding="utf-8")
    result = _verify(repository, path)
    assert result["outcome"] == ("DEGRADED" if mutation == "skip" else "STOP"), result
    assert result["claim_qualified"] is False


def test_same_event_cannot_be_replayed_or_executed_in_parallel(repository):
    path = _bundle(repository)
    event = "a" * 32
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda _: _verify(repository, path, event_id=event), range(2))
        )
    assert sorted(result["outcome"] for result in results) == ["DEGRADED", "ERROR"]
    assert (
        _verify(repository, path, event_id=event)["reason"]
        == "duplicate_or_reentered_event"
    )


@pytest.mark.parametrize("failure", ["timeout", "exit130", "cleanup", "interrupt"])
def test_process_failures_and_parent_interrupt_are_distinct(
    repository, monkeypatch, failure
):
    path = _bundle(repository)
    if failure in {"timeout", "exit130"}:
        code = (
            "import time;time.sleep(10)"
            if failure == "timeout"
            else "raise SystemExit(130)"
        )
        monkeypatch.setattr(
            runtime, "_worker_argv", lambda *_: (sys.executable, "-I", "-B", "-c", code)
        )
    elif failure == "cleanup":
        monkeypatch.setattr(
            runtime,
            "run_owned",
            lambda *_, **__: ProcessResult(
                "ERROR", "containment_cleanup_failed", 0, 0.01
            ),
        )
    else:

        def interrupted(*_args, **_kwargs):
            raise KeyboardInterrupt

        monkeypatch.setattr(runtime, "run_owned", interrupted)
    result = _verify(repository, path, timeout=0.2 if failure == "timeout" else 120)
    assert result["outcome"] == ("USER_STOP" if failure == "interrupt" else "ERROR"), (
        result
    )
    assert result["exit_code"] == (130 if failure == "interrupt" else 2)
    assert result["claim_qualified"] is False


def test_untrusted_findings_and_arguments_do_not_echo_secret_canaries(
    repository, capsys
):
    path = _bundle(repository)
    value = json.loads(path.read_bytes())
    row = value["receipts"][0]
    row["producer"] = "SYNTHETIC_SECRET_CANARY"
    row["receipt_digest"] = proof.canonical_digest(
        {k: v for k, v in row.items() if k != "receipt_digest"}
    )
    value["bundle_digest"] = proof.canonical_digest(
        {k: v for k, v in value.items() if k != "bundle_digest"}
    )
    path.write_text(json.dumps(value), encoding="utf-8")
    result = _verify(repository, path)
    assert result["outcome"] in {"STOP", "ERROR"}
    assert "SYNTHETIC_SECRET_CANARY" not in json.dumps(result)
    directory = state.directory(repository, result["event_id"])
    assert all(
        "SYNTHETIC_SECRET_CANARY" not in file.read_text()
        for file in directory.iterdir()
    )
    with pytest.raises(SystemExit) as stopped:
        runtime.main(["--runtime", "SYNTHETIC_SECRET_CANARY"])
    assert stopped.value.code == 2
    captured = capsys.readouterr()
    assert "SYNTHETIC_SECRET_CANARY" not in captured.out + captured.err


def test_recursive_request_is_rejected_without_starting_worker(repository, monkeypatch):
    path = _bundle(repository)
    monkeypatch.setenv("BIOETL_CLOSEOUT_WORKER", "1")
    assert _verify(repository, path)["reason"] == "invalid_or_recursive_request"


@pytest.mark.skipif(os.name == "nt", reason="Requires POSIX executable-bit semantics")
def test_mode_change_after_real_verifier_is_rejected(repository: Path) -> None:
    root = repository
    assert run_isolated_git(root, "config", "core.filemode", "true").returncode == 0
    target = root / "tracked.py"
    target.write_text("VALUE = 20\n", encoding="utf-8")
    path = _bundle(root)
    request = {
        "event_id": "b" * 32,
        "state": state.capture(root, os.environ),
        "bundle_sha256": state.sha256(path.read_bytes()),
        "task_id_sha256": state.sha256(b"task-39"),
        "runtime": "codex",
        "claim": "done",
    }
    original = proof.verify_bundle

    def verify_then_change_mode(**kwargs):
        verified = original(**kwargs)
        assert verified.outcome == "ADMIT"
        target.chmod(target.stat().st_mode ^ stat.S_IXUSR)
        return verified

    with (
        path.open("rb") as stream,
        patch.object(sys, "stdin", SimpleNamespace(buffer=stream)),
        patch.object(proof, "verify_bundle", verify_then_change_mode),
    ):
        result = worker._verify(request, root)
    current = original(
        bundle=json.loads(path.read_text()),
        repo_root=root,
        policy=proof.load_policy(),
        schema=proof.load_schema(),
        check_current_source=True,
    )
    assert current.outcome == "STOP"
    assert result["outcome"] == "ERROR", result
    assert result["reason"] == "source_or_bundle_changed", result


@pytest.mark.parametrize("different", [False, True])
def test_supplied_index_must_be_represented_by_the_canonical_default_index(
    repository, monkeypatch, different
):
    path = _bundle(repository)
    alternate = repository / ".git/alternate-index"
    shutil.copyfile(repository / ".git/index", alternate)
    if different:
        result = run_isolated_git(
            repository,
            "read-tree",
            "--empty",
            env=isolated_git_env(extra={"GIT_INDEX_FILE": str(alternate)}),
        )
        assert result.returncode == 0, result.stderr
    monkeypatch.setenv("GIT_INDEX_FILE", str(alternate))
    result = _verify(repository, path)
    assert result["outcome"] == ("ERROR" if different else "DEGRADED"), result


@pytest.mark.parametrize(
    "change", ["working", "index", "head", "branch", "history", "bundle"]
)
def test_successful_child_cannot_hide_state_change_during_the_event(
    repository, monkeypatch, change
):
    path = _bundle(repository)
    code = (
        "import sys;from pathlib import Path;"
        f"sys.path.insert(0,{str(state.SOURCE_ROOT)!r});"
        "from tests.helpers.isolated_git import run_isolated_git;"
        f"root=Path({str(repository)!r});"
    )
    if change in {"working", "index"}:
        code += (
            "p=root/'tracked.py';original=p.read_bytes();p.write_text('VALUE = 10\\n');"
        )
        if change == "index":
            code += "assert run_isolated_git(root,'add','tracked.py').returncode==0;p.write_bytes(original);"
    elif change == "head":
        code += "assert run_isolated_git(root,'commit','--no-gpg-sign','--no-verify','--allow-empty','-qm','fixture change').returncode==0;"
    elif change == "branch":
        code += "assert run_isolated_git(root,'switch','-c','changed-fixture').returncode==0;"
    elif change == "history":
        code += "assert run_isolated_git(root,'fetch','--depth=1','.','HEAD').returncode==0;"
    else:
        code += f"Path({str(path)!r}).write_text('{{}}');"
    monkeypatch.setattr(
        runtime, "_worker_argv", lambda *_: (sys.executable, "-I", "-B", "-c", code)
    )
    result = _verify(repository, path)
    assert result["outcome"] == "ERROR", result
    assert result["reason"] == "source_or_bundle_changed", result


@pytest.mark.parametrize(
    "field", ["core_outcome", "errors_count", "findings_sha256", "reason"]
)
def test_integrity_valid_but_malformed_metadata_is_not_echoed(repository, field):
    event = "c" * 32
    target = state.directory(repository, event, reserve=True)
    request = {
        "event_id": event,
        "payload_sha256": "a" * 64,
        "state": {},
        "bundle_sha256": "b" * 64,
    }
    payload = {
        **state.result("DEGRADED", "local_transport_not_attested", event),
        "request_sha256": request["payload_sha256"],
        "core_outcome": "ADMIT",
        "errors_count": 0,
        "degradations_count": 0,
        "findings_sha256": "c" * 64,
        "state_sha256": state.hook_receipts.digest(request["state"]),
        "bundle_sha256": request["bundle_sha256"],
        field: "SYNTHETIC_SECRET_CANARY",
    }
    state.write_once(target, "result.json", payload)
    with pytest.raises(ValueError):
        runtime._consume(target, request)
