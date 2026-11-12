"""Receipts invalidate on measured state changes; non-PASS cannot qualify."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
import subprocess

import pytest

from scripts.engineering.repo import hook_receipts as receipts

pytestmark = pytest.mark.unit


@pytest.fixture
def private_repo(tmp_path, monkeypatch):
    root = tmp_path / "fixture"
    root.mkdir()
    disabled = tmp_path / "disabled"
    disabled.mkdir()
    env = dict(os.environ)
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
        env.pop(key, None)

    def git(*args):
        subprocess.run(
            [
                "git",
                "-c",
                f"core.hooksPath={disabled}",
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                *args,
            ],
            cwd=root,
            env=env,
            check=True,
            capture_output=True,
            timeout=10,
        )

    git("init")
    (root / "fixture.txt").write_text("initial")
    git("add", ".")
    git("commit", "-m", "fixture")
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    monkeypatch.setattr(
        receipts, "environment_identity", lambda env=None: "fixture-environment"
    )
    return root, git


def _checks(status="PASS", code=0):
    return [{"id": "fixture-check", "status": status, "returncode": code}]


def test_same_state_receipt_qualifies_only_local_observation(private_repo):
    root, _ = private_repo
    state = receipts.snapshot(root)
    path = receipts.write_receipt(root, state, _checks())
    result = receipts.validate_receipt(
        root, path, receipts.snapshot(root), ["fixture-check"]
    )
    assert result == {"status": "PASS", "reason": "same_local_state_only"}
    payload = json.loads(path.read_text())
    assert payload["ci_acceptance"] is False
    assert payload["runtime_admission"] is False


@pytest.mark.parametrize("change", ["unstaged", "index", "head", "untracked"])
def test_changed_source_or_index_or_head_invalidates(private_repo, change):
    root, git = private_repo
    state = receipts.snapshot(root)
    path = receipts.write_receipt(root, state, _checks())
    target = root / ("new.txt" if change == "untracked" else "fixture.txt")
    target.write_text("changed")
    if change in {"index", "head"}:
        git("add", ".")
    if change == "head":
        git("commit", "-m", "changed fixture")
    assert (
        receipts.validate_receipt(
            root, path, receipts.snapshot(root), ["fixture-check"]
        )["status"]
        == "ERROR"
    )


def test_changed_checker_invalidates(private_repo, tmp_path, monkeypatch):
    root, _ = private_repo
    checker = tmp_path / "checkers/checker.py"
    checker.parent.mkdir()
    checker.write_text("fixture v1")
    monkeypatch.setattr(receipts, "__file__", str(checker))
    state = receipts.snapshot(root)
    path = receipts.write_receipt(root, state, _checks())
    checker.write_text("fixture v2")
    assert (
        receipts.validate_receipt(
            root, path, receipts.snapshot(root), ["fixture-check"]
        )["status"]
        == "ERROR"
    )


@pytest.mark.parametrize(
    "status,code",
    [
        ("SKIP", 3),
        ("ERROR", 2),
        ("FAIL", 1),
        ("STOP", 0),
        ("DEGRADED", 0),
        ("PASS", False),
    ],
)
def test_nonpass_and_invalid_codes_do_not_qualify(private_repo, status, code):
    root, _ = private_repo
    state = receipts.snapshot(root)
    path = receipts.write_receipt(root, state, _checks(status, code))
    assert (
        receipts.validate_receipt(root, path, state, ["fixture-check"])["status"]
        == "ERROR"
    )


def test_corrupted_or_wrong_check_receipt_fails(private_repo):
    root, _ = private_repo
    state = receipts.snapshot(root)
    path = receipts.write_receipt(root, state, _checks())
    assert (
        receipts.validate_receipt(root, path, state, ["additional-required-check"])[
            "status"
        ]
        == "ERROR"
    )
    path.write_text("invalid JSON")
    assert (
        receipts.validate_receipt(root, path, state, ["fixture-check"])["status"]
        == "ERROR"
    )


def test_parallel_receipts_remain_distinct_and_valid(private_repo):
    root, _ = private_repo
    state = receipts.snapshot(root)
    with ThreadPoolExecutor(max_workers=4) as pool:
        paths = list(
            pool.map(lambda _: receipts.write_receipt(root, state, _checks()), range(8))
        )
    assert len(set(paths)) == 8
    assert all(
        receipts.validate_receipt(root, path, state, ["fixture-check"])["status"]
        == "PASS"
        for path in paths
    )


def test_receipt_cannot_cross_synthetic_worktrees(private_repo, tmp_path):
    root, git = private_repo
    state = receipts.snapshot(root)
    path = receipts.write_receipt(root, state, _checks())
    other = tmp_path / "other-private-fixture"
    # One-file synthetic repository, never a BioETL checkout.
    git("worktree", "add", "--detach", str(other), "HEAD")
    current = receipts.snapshot(other)
    assert (
        receipts.validate_receipt(other, path, current, ["fixture-check"])["status"]
        == "ERROR"
    )


def test_hidden_index_input_is_not_cacheable(private_repo):
    root, git = private_repo
    git("update-index", "--assume-unchanged", "fixture.txt")
    with pytest.raises(ValueError, match="hidden index"):
        receipts.snapshot(root)


def test_base_ref_drift_changes_receipt_identity(private_repo):
    root, git = private_repo
    original = receipts.snapshot(root)
    (root / "fixture.txt").write_text("new base")
    git("add", ".")
    git("commit", "-m", "new base")
    pinned = receipts.snapshot(root)
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    assert receipts.snapshot(root)["base_sha"] != pinned["base_sha"]
    assert original["head_sha"] != pinned["head_sha"]


def test_supplied_index_does_not_hide_default_index_change(private_repo, monkeypatch):
    root, git = private_repo
    alternate = root / ".git" / "alternate-index"
    alternate.write_bytes((root / ".git" / "index").read_bytes())
    monkeypatch.setenv("GIT_INDEX_FILE", str(alternate))
    before = receipts.snapshot(root)
    (root / "fixture.txt").write_text("default index changed")
    git("add", "fixture.txt")  # Fixture helper captured the unmodified environment.
    after = receipts.snapshot(root)
    assert before["index_sha256"] != after["index_sha256"]


def test_snapshot_rejects_concurrent_protected_state_change(private_repo, monkeypatch):
    root, _ = private_repo
    before = receipts.protected_state(root)
    states = iter([before, {**before, "head_sha": "changed"}])
    monkeypatch.setattr(receipts, "protected_state", lambda *args: next(states))
    with pytest.raises(ValueError, match="state changed"):
        receipts.snapshot(root)


def test_changed_environment_invalidates(private_repo, monkeypatch):
    root, _ = private_repo
    state = receipts.snapshot(root)
    path = receipts.write_receipt(root, state, _checks())
    monkeypatch.setattr(
        receipts, "environment_identity", lambda env=None: "other-environment"
    )
    assert (
        receipts.validate_receipt(
            root, path, receipts.snapshot(root), ["fixture-check"]
        )["status"]
        == "ERROR"
    )


def test_only_declared_timeless_checks_can_be_reused_briefly(private_repo, monkeypatch):
    root, _ = private_repo
    state = receipts.snapshot(root)
    ordinary = receipts.write_receipt(root, state, _checks())
    assert (
        receipts.validate_receipt(
            root, ordinary, state, ["fixture-check"], for_reuse=True
        )["status"]
        == "ERROR"
    )
    checks = _checks()
    checks[0]["cacheable"] = True
    path = receipts.write_receipt(root, state, checks)
    assert (
        receipts.validate_receipt(root, path, state, ["fixture-check"], for_reuse=True)[
            "status"
        ]
        == "PASS"
    )
    created = json.loads(path.read_text())["created_at_unix"]
    monkeypatch.setattr(receipts.time, "time", lambda: created + 61)
    assert (
        receipts.validate_receipt(root, path, state, ["fixture-check"], for_reuse=True)[
            "status"
        ]
        == "ERROR"
    )


@pytest.mark.parametrize("payload", ["null", '"text"', "[]", "{invalid"])
def test_invalid_json_shapes_are_errors(private_repo, payload):
    root, _ = private_repo
    state = receipts.snapshot(root)
    path = receipts.write_receipt(root, state, _checks())
    path.write_text(payload)
    assert (
        receipts.validate_receipt(root, path, state, ["fixture-check"])["status"]
        == "ERROR"
    )
