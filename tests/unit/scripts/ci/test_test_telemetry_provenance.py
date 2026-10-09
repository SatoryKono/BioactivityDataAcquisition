"""Negative regressions for captured-run identity across a squash merge."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import urllib.request
from pathlib import Path

import pytest

from scripts.engineering.ci.test_telemetry_provenance import validate_squash_bridge
from scripts.engineering.ci import test_telemetry_provenance as provenance

pytestmark = pytest.mark.unit


@pytest.fixture
def bridge(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")

    def git(*args: str) -> str:
        return subprocess.check_output(
            [
                "git",
                "-c",
                "commit.gpgsign=false",
                "-c",
                f"core.hooksPath={os.devnull}",
                *args,
            ],
            cwd=tmp_path,
            text=True,
        ).strip()

    git("init", "-q")
    git("config", "user.name", "Provenance fixture")
    git("config", "user.email", "fixture@example.invalid")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_source.py").write_text("value = 1\n")
    git("add", ".")
    git("commit", "-qm", "base")
    base = git("rev-parse", "HEAD")
    (tmp_path / "tests/test_source.py").write_text("value = 2\n")
    git("add", ".")
    git("commit", "-qm", "source run")
    source = git("rev-parse", "HEAD")
    (tmp_path / "evidence.json").write_text("{}\n")
    git("add", ".")
    git("commit", "-qm", "captured outputs")
    pr_head = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    merge = git("commit-tree", tree, "-p", base, "-m", "capture (#42)")
    git("reset", "--hard", merge)
    payload = {
        "source_commit": source,
        "source_run_id": "local-real-run",
        "source_tree_sha256": "snapshot",
    }
    receipt = {
        "schema_version": 1,
        **payload,
        "merged_tree": tree,
        "retrieved_from": "https://api.github.com/repos/SatoryKono/BioactivityDataAcquisition/pulls/42",
        "github_pull_request": {
            "number": 42,
            "merged": True,
            "base": {"repo": {"full_name": "SatoryKono/BioactivityDataAcquisition"}},
            "head": {"sha": pr_head},
            "merge_commit_sha": merge,
        },
    }
    return tmp_path, merge, payload, receipt, git


@pytest.mark.parametrize(
    "destination",
    [
        "https://uploads.github.com/repos/example",
        "https://api.github.com:8443/repos/example",
    ],
)
def test_redirect_handler_strips_authorization_for_another_origin(
    destination: str,
) -> None:
    request = urllib.request.Request(
        "https://api.github.com/repos/example",
        headers={"Authorization": "Bearer secret"},
    )
    redirected = provenance._SameOriginAuthRedirectHandler().redirect_request(
        request,
        None,
        302,
        "Found",
        {},
        destination,
    )
    assert redirected is not None
    assert redirected.get_header("Authorization") is None


def test_redirect_handler_rejects_https_downgrade() -> None:
    request = urllib.request.Request(
        "https://api.github.com/repos/example",
        headers={"Authorization": "Bearer secret"},
    )

    redirected = provenance._SameOriginAuthRedirectHandler().redirect_request(
        request,
        None,
        302,
        "Found",
        {},
        "http://api.github.com/repos/example",
    )

    assert redirected is None


def test_redirect_handler_preserves_authorization_for_the_same_origin() -> None:
    request = urllib.request.Request(
        "https://api.github.com/repos/example",
        headers={"Authorization": "Bearer secret"},
    )
    redirected = provenance._SameOriginAuthRedirectHandler().redirect_request(
        request,
        None,
        302,
        "Found",
        {},
        "https://api.github.com:443/repos/renamed",
    )
    assert redirected is not None
    assert redirected.get_header("Authorization") == "Bearer secret"


def test_accepts_equal_inputs_and_confirmed_squash_tree(bridge) -> None:
    root, head, payload, receipt, _ = bridge
    assert validate_squash_bridge(payload, receipt, root, head)


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_commit", "0" * 40),
        ("source_run_id", "invented-run"),
        ("source_tree_sha256", "changed-inputs"),
        ("merged_tree", "0" * 40),
        ("retrieved_from", "https://example.invalid/pulls/42"),
    ],
)
def test_rejects_forged_capture_or_tree(bridge, field, value) -> None:
    root, head, payload, receipt, _ = bridge
    changed = copy.deepcopy(receipt)
    changed[field] = value
    assert not validate_squash_bridge(payload, changed, root, head)


@pytest.mark.parametrize(
    "field,value", [("number", 99), ("merged", False), ("merge_commit_sha", "0" * 40)]
)
def test_rejects_unrelated_or_unconfirmed_pr(bridge, field, value) -> None:
    root, head, payload, receipt, _ = bridge
    changed = copy.deepcopy(receipt)
    changed["github_pull_request"][field] = value
    assert not validate_squash_bridge(payload, changed, root, head)


def test_rejects_modified_inputs_even_when_squash_tree_matches(bridge) -> None:
    root, _, payload, receipt, git = bridge
    git("checkout", "--detach", receipt["github_pull_request"]["head"]["sha"])
    (root / "tests/test_source.py").write_text("value = 3\n")
    git("add", ".")
    git("commit", "-qm", "changed maintained test")
    pr_head = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    merge = git(
        "commit-tree", tree, "-p", payload["source_commit"], "-m", "capture (#42)"
    )
    receipt["github_pull_request"]["head"]["sha"] = pr_head
    receipt["github_pull_request"]["merge_commit_sha"] = merge
    receipt["merged_tree"] = tree
    assert not validate_squash_bridge(payload, receipt, root, merge)


def test_rejects_wrong_repository(bridge) -> None:
    root, head, payload, receipt, _ = bridge
    receipt["github_pull_request"]["base"]["repo"]["full_name"] = "other/repository"
    assert not validate_squash_bridge(payload, receipt, root, head)


def test_rejects_merge_not_reachable_from_current_branch(bridge) -> None:
    root, _, payload, receipt, _ = bridge
    assert not validate_squash_bridge(payload, receipt, root, payload["source_commit"])


def _pending_live_receipt(root, payload, receipt) -> None:
    pending = copy.deepcopy(receipt)
    pending["verification_mode"] = "live_github"
    pending["github_pull_request"]["merged"] = False
    pending["github_pull_request"]["merge_commit_sha"] = None
    path = root / provenance.RECEIPT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pending), encoding="utf-8")


def test_new_capture_survives_future_squash_without_restamping_source(
    bridge, monkeypatch
) -> None:
    root, head, payload, receipt, _ = bridge
    payload["source_run_id"] = "local-new-canonical-capture"
    receipt["source_run_id"] = payload["source_run_id"]
    _pending_live_receipt(root, payload, receipt)
    seen = []

    def read(path):
        seen.append(path)
        return copy.deepcopy(receipt["github_pull_request"])

    monkeypatch.setattr(provenance, "_read_github_json", read)
    original = copy.deepcopy(payload)
    assert provenance.source_commit_is_reachable(payload, root, head)
    assert payload == original
    assert seen == ["pulls/42"]


@pytest.mark.parametrize("state", ["unmerged", "wrong-pr", "unavailable"])
def test_live_capture_fails_closed_without_confirmed_github_merge(
    bridge, monkeypatch, state
) -> None:
    root, head, payload, receipt, _ = bridge
    _pending_live_receipt(root, payload, receipt)

    def read(_path):
        if state == "unavailable":
            raise OSError("GitHub access unavailable")
        pr = copy.deepcopy(receipt["github_pull_request"])
        if state == "unmerged":
            pr["merged"] = False
        else:
            pr["number"] = 99
        return pr

    monkeypatch.setattr(provenance, "_read_github_json", read)
    assert not provenance.source_commit_is_reachable(payload, root, head)


def test_live_capture_rejects_a_different_run_before_api_read(
    bridge, monkeypatch
) -> None:
    root, head, payload, receipt, _ = bridge
    _pending_live_receipt(root, payload, receipt)
    payload["source_run_id"] = "unrelated-run"
    monkeypatch.setattr(
        provenance, "_read_github_json", lambda _path: pytest.fail("must not read API")
    )
    assert not provenance.source_commit_is_reachable(payload, root, head)


@pytest.mark.parametrize(
    "file",
    [
        {"filename": "reports/coverage-summary.json"},
        {"filename": "tests/changed.py"},
        {"filename": "docs/moved.txt", "previous_filename": "src/bioetl/moved.py"},
    ],
)
def test_shallow_clone_checks_remote_ancestry_tree_and_changed_inputs(
    bridge, monkeypatch, file
) -> None:
    root, head, payload, receipt, _ = bridge
    _pending_live_receipt(root, payload, receipt)
    pr_head = receipt["github_pull_request"]["head"]["sha"]
    real_tree = provenance._tree
    monkeypatch.setattr(
        provenance,
        "_tree",
        lambda root, commit: "" if commit == pr_head else real_tree(root, commit),
    )

    def read(path):
        if path == "pulls/42":
            return copy.deepcopy(receipt["github_pull_request"])
        if path.startswith("compare/"):
            return {
                "status": "ahead",
                "merge_base_commit": {"sha": payload["source_commit"]},
                "files": [file],
            }
        if path.startswith("git/commits/"):
            return {"tree": {"sha": receipt["merged_tree"]}}
        pytest.fail(f"unexpected API path {path}")

    monkeypatch.setattr(provenance, "_read_github_json", read)
    expected = file["filename"].startswith("reports/")
    assert provenance.source_commit_is_reachable(payload, root, head) is expected
