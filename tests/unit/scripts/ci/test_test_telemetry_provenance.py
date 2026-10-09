"""Negative regressions for captured-run identity across a squash merge."""

from __future__ import annotations

import copy
import subprocess
from pathlib import Path

import pytest

from scripts.engineering.ci.test_telemetry_provenance import validate_squash_bridge

pytestmark = pytest.mark.unit


@pytest.fixture
def bridge(tmp_path: Path):
    def git(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=tmp_path, text=True).strip()

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
