"""Negative regressions for captured-run identity across a squash merge."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import urllib.error
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
    for name in provenance.TEST_INPUTS:
        path = tmp_path / name
        if path.suffix:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text("fixture input\n")
        else:
            path.mkdir(parents=True, exist_ok=True)
            (path / "fixture.py").write_text("value = 1\n")
    git("add", ".")
    git("commit", "-qm", "base")
    base = git("rev-parse", "HEAD")
    (tmp_path / "tests/test_source.py").write_text("value = 2\n")
    git("add", ".")
    git("commit", "-qm", "source run")
    source = git("rev-parse", "HEAD")
    from scripts.engineering.ci.update_test_telemetry_baseline import (
        compute_test_telemetry_source_tree_sha256,
    )

    captured_test_tree = compute_test_telemetry_source_tree_sha256(tmp_path)
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
        "source_tree_sha256": captured_test_tree,
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


def test_rejected_scope_retries_public_github_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str | None] = []

    def request(url: str, token: str | None) -> dict[str, bool]:
        calls.append(token)
        if token:
            raise urllib.error.HTTPError(url, 403, "Forbidden", hdrs=None, fp=None)
        return {"merged": True}

    monkeypatch.setenv("GITHUB_TOKEN", "ghs-contents-only")
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr(provenance, "_request_github_json", request)
    assert provenance._read_github_json("pulls/12231") == {"merged": True}
    assert calls == ["ghs-contents-only", None]


def test_unrelated_http_error_is_not_retried_without_a_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def request(url: str, token: str | None) -> dict[str, bool]:
        raise urllib.error.HTTPError(url, 404, "Not Found", hdrs=None, fp=None)

    monkeypatch.setenv("GITHUB_TOKEN", "ghs-contents-only")
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr(provenance, "_request_github_json", request)
    with pytest.raises(urllib.error.HTTPError):
        provenance._read_github_json("pulls/12231")


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


def test_normal_ancestry_ignores_stale_pending_bridge(bridge) -> None:
    root, _, payload, receipt, _ = bridge
    _pending_live_receipt(root, payload, receipt)
    assert provenance.source_commit_is_reachable(
        payload, root, receipt["github_pull_request"]["head"]["sha"]
    )


def test_squash_without_bridge_fails_closed(bridge) -> None:
    root, head, payload, _, _ = bridge
    assert not (root / provenance.RECEIPT).exists()
    assert not provenance.source_commit_is_reachable(payload, root, head)


def test_shallow_endpoints_without_intermediate_require_verified_proof(bridge) -> None:
    root, head, payload, receipt, git = bridge
    source = payload["source_commit"]
    pr_head = receipt["github_pull_request"]["head"]["sha"]
    receipt["git_object_proof"] = provenance.build_git_object_proof(
        root, source, pr_head
    )
    git("update-ref", "refs/heads/captured-source", source)
    git("update-ref", "refs/heads/reviewed-head", pr_head)
    shallow = root.parent / f"{root.name}-endpoint-shallow"
    subprocess.run(
        [
            "git",
            "clone",
            "-q",
            "--depth",
            "1",
            "--no-single-branch",
            root.as_uri(),
            str(shallow),
        ],
        check=True,
        capture_output=True,
    )
    assert provenance._tree(shallow, source)
    assert provenance._tree(shallow, pr_head)
    assert not provenance._ancestor(shallow, source, pr_head)
    assert validate_squash_bridge(payload, receipt, shallow, head)
    without_proof = copy.deepcopy(receipt)
    del without_proof["git_object_proof"]
    assert not validate_squash_bridge(payload, without_proof, shallow, head)


def test_newer_shallow_tip_requires_merge_history(bridge) -> None:
    root, _, payload, receipt, git = bridge
    receipt["git_object_proof"] = provenance.build_git_object_proof(
        root, payload["source_commit"], receipt["github_pull_request"]["head"]["sha"]
    )
    git("commit", "--allow-empty", "-qm", "later main")
    later_head = git("rev-parse", "HEAD")
    shallow = root.parent / f"{root.name}-later-shallow"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", root.as_uri(), str(shallow)],
        check=True,
        capture_output=True,
    )
    assert provenance._is_shallow(shallow)
    with pytest.raises(provenance.ShallowMergeHistoryError, match="Unshallow"):
        validate_squash_bridge(payload, receipt, shallow, later_head)
    receipt_path = shallow / provenance.RECEIPT
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(provenance.ShallowMergeHistoryError, match="Unshallow"):
        provenance.source_commit_is_reachable(payload, shallow, later_head)
    subprocess.run(
        ["git", "fetch", "-q", "--unshallow", "origin"],
        cwd=shallow,
        check=True,
        capture_output=True,
    )
    assert validate_squash_bridge(payload, receipt, shallow, later_head)
    assert provenance.source_commit_is_reachable(payload, shallow, later_head)


def test_receipt_publication_preserves_prior_file_on_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "squash-provenance.json"
    destination.write_text("prior valid receipt\n", encoding="utf-8")

    def fail_replace(_source: Path, _destination: Path) -> None:
        raise OSError("replace failed")

    with monkeypatch.context() as patch:
        patch.setattr(provenance.os, "replace", fail_replace)
        with pytest.raises(OSError, match="replace failed"):
            provenance._write_receipt_atomically(destination, {"schema_version": 1})
    assert destination.read_text(encoding="utf-8") == "prior valid receipt\n"
    assert list(tmp_path.glob(".squash-provenance.json.*.tmp")) == []
    provenance._write_receipt_atomically(destination, {"schema_version": 1})
    assert json.loads(destination.read_text(encoding="utf-8")) == {"schema_version": 1}


def test_complete_history_rejects_unrelated_source_even_with_proof(
    bridge, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, head, payload, receipt, git = bridge
    unrelated = git("commit-tree", git("rev-parse", "HEAD^{tree}"), "-m", "unrelated")
    payload["source_commit"] = unrelated
    receipt["source_commit"] = unrelated
    receipt["git_object_proof"] = {"commit_chain": [], "trees": {}}
    assert not provenance._is_shallow(root)
    assert provenance._tree(root, unrelated)
    monkeypatch.setattr(
        provenance,
        "_object_proof_relation",
        lambda *_args: pytest.fail("full history must not use fallback proof"),
    )
    assert not validate_squash_bridge(payload, receipt, root, head)


def test_local_capture_keeps_measured_identity_after_test_tree_changes(bridge) -> None:
    root, head, payload, receipt, _ = bridge
    payload["source_event"] = "local_coverage_verify"
    payload["source_tree_sha256"] = "current-audited-tree"
    payload["coverage"] = {"actual_percent": 99.0}
    payload["duration_telemetry"] = {"total_cases": 17}
    payload["measurement_provenance"] = {
        "head": payload["source_commit"],
        "test_tree_sha256": receipt["source_tree_sha256"],
        "manifest_sha256": "manifest",
    }
    receipt["manifest_sha256"] = "manifest"
    receipt["metrics_sha256"] = provenance.telemetry_metrics_sha256(payload)

    assert validate_squash_bridge(payload, receipt, root, head)
    receipt_path = root / provenance.RECEIPT
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    assert provenance.capture_metrics_are_bound(payload, root)
    changed_metrics = copy.deepcopy(payload)
    changed_metrics["coverage"]["actual_percent"] = 0.0
    assert not provenance.capture_metrics_are_bound(changed_metrics, root)
    assert not validate_squash_bridge(changed_metrics, receipt, root, head)
    for field in ("source_tree_sha256", "manifest_sha256"):
        changed_receipt = copy.deepcopy(receipt)
        changed_receipt[field] = "forged"
        assert not validate_squash_bridge(payload, changed_receipt, root, head)
    for field in ("head", "test_tree_sha256", "manifest_sha256"):
        changed = copy.deepcopy(payload)
        changed["measurement_provenance"][field] = "forged"
        assert not validate_squash_bridge(changed, receipt, root, head)
    without_measurement = copy.deepcopy(payload)
    del without_measurement["measurement_provenance"]
    assert not validate_squash_bridge(without_measurement, receipt, root, head)


def test_squash_bridge_verifies_without_old_pr_objects(
    bridge, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, head, payload, receipt, _ = bridge
    source = payload["source_commit"]
    pr_head = receipt["github_pull_request"]["head"]["sha"]
    receipt["git_object_proof"] = provenance.build_git_object_proof(
        root, source, pr_head
    )
    shallow = root.parent / f"{root.name}-shallow"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", root.as_uri(), str(shallow)],
        check=True,
        capture_output=True,
    )
    assert not provenance._tree(shallow, source)
    assert not provenance._tree(shallow, pr_head)
    assert validate_squash_bridge(payload, receipt, shallow, head)

    tampered = copy.deepcopy(receipt)
    tampered["git_object_proof"]["commit_chain"][-1]["raw"] = "Zm9yZ2Vk"
    assert not validate_squash_bridge(payload, tampered, shallow, head)
    tampered = copy.deepcopy(receipt)
    tree_oid = next(iter(tampered["git_object_proof"]["trees"]))
    tampered["git_object_proof"]["trees"][tree_oid] = "Zm9yZ2Vk"
    assert not validate_squash_bridge(payload, tampered, shallow, head)


def test_single_commit_object_proof_for_capture_on_pr_head(bridge) -> None:
    root, _, _, receipt, _ = bridge
    pr_head = receipt["github_pull_request"]["head"]["sha"]
    proof = provenance.build_git_object_proof(root, pr_head, pr_head)
    assert [item["oid"] for item in proof["commit_chain"]] == [pr_head]
    assert provenance._object_proof_relation(
        {"git_object_proof": proof}, pr_head, pr_head
    ) == (True, provenance._tree(root, pr_head))


def test_receipt_builder_uses_original_checkout_after_squash(
    bridge, monkeypatch: pytest.MonkeyPatch
) -> None:
    measurement_root, head, payload, prior_receipt, _ = bridge
    shallow = measurement_root.parent / f"{measurement_root.name}-receipt-shallow"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", measurement_root.as_uri(), str(shallow)],
        check=True,
        capture_output=True,
    )
    assert not provenance._tree(shallow, payload["source_commit"])
    manifest_path = measurement_root / "capture" / "manifest.json"
    manifest = {
        "head": payload["source_commit"],
        "test_tree_sha256": payload["source_tree_sha256"],
        "source_tree_sha256": "source-tree",
        "finished_at_utc": "2026-10-01T01:00:00+00:00",
    }
    payload.update(
        {
            "source_event": "local_coverage_verify",
            "source_run_id": "local-capture",
            "refreshed_at_utc": manifest["finished_at_utc"],
            "measurement_provenance": {
                "head": manifest["head"],
                "test_tree_sha256": manifest["test_tree_sha256"],
                "source_tree_sha256": manifest["source_tree_sha256"],
                "manifest_sha256": "manifest-digest",
            },
            "coverage": {"actual_percent": 99.0},
            "duration_telemetry": {"total_cases": 17},
        }
    )
    monkeypatch.setattr(
        "scripts.engineering.ci.local_test_telemetry.validate_local_measurement",
        lambda *_args, **_kwargs: {
            "manifest": manifest,
            "manifest_sha256": "manifest-digest",
        },
    )
    monkeypatch.setattr(
        "scripts.engineering.ci.local_test_telemetry.build_local_baseline",
        lambda *_args, **_kwargs: payload,
    )
    monkeypatch.setattr(
        "scripts.engineering.ci.update_test_telemetry_baseline.compute_test_telemetry_source_tree_sha256",
        lambda _root: manifest["test_tree_sha256"],
    )
    monkeypatch.setattr(
        "scripts.engineering.qa.report_module_coverage_inventory.compute_source_tree_sha256",
        lambda **_kwargs: manifest["source_tree_sha256"],
    )
    monkeypatch.setattr(
        provenance,
        "_read_github_json",
        lambda _path: prior_receipt["github_pull_request"],
    )

    receipt = provenance.build_reviewed_squash_receipt(
        payload,
        root=shallow,
        measurement_root=measurement_root,
        manifest_path=manifest_path,
        pull_request=42,
    )
    assert receipt["merged_tree"] == provenance._tree(shallow, head)
    assert validate_squash_bridge(payload, receipt, shallow, head)
    for field, key, value in (
        ("coverage", "actual_percent", 0.0),
        ("duration_telemetry", "total_cases", 999),
    ):
        changed = copy.deepcopy(payload)
        changed[field][key] = value
        with pytest.raises(ValueError, match=f"Committed {field}"):
            provenance.build_reviewed_squash_receipt(
                changed,
                root=shallow,
                measurement_root=measurement_root,
                manifest_path=manifest_path,
                pull_request=42,
            )


def test_squash_bridge_verifies_intermediate_evidence_commits(
    bridge, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, payload, receipt, git = bridge
    source = payload["source_commit"]
    base = git("rev-parse", f"{source}^")
    branch = git("symbolic-ref", "--short", "HEAD")
    git("checkout", "--detach", receipt["github_pull_request"]["head"]["sha"])
    (root / "more-evidence.json").write_text("{}\n")
    git("add", ".")
    git("commit", "-qm", "more captured outputs")
    pr_head = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    merge = git("commit-tree", tree, "-p", base, "-m", "capture (#42)")
    git("checkout", branch)
    git("reset", "--hard", merge)
    receipt["github_pull_request"]["head"]["sha"] = pr_head
    receipt["github_pull_request"]["merge_commit_sha"] = merge
    receipt["merged_tree"] = tree
    receipt["git_object_proof"] = provenance.build_git_object_proof(
        root, source, pr_head
    )
    assert len(receipt["git_object_proof"]["commit_chain"]) == 3

    shallow = root.parent / f"{root.name}-evidence-shallow"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", root.as_uri(), str(shallow)],
        check=True,
        capture_output=True,
    )
    assert not provenance._tree(shallow, source)
    assert not provenance._tree(shallow, pr_head)
    assert validate_squash_bridge(payload, receipt, shallow, merge)

    tampered = copy.deepcopy(receipt)
    del tampered["git_object_proof"]["commit_chain"][1]
    assert not validate_squash_bridge(payload, tampered, shallow, merge)


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


def _pending_publication_receipt(root, payload, receipt) -> None:
    _pending_live_receipt(root, payload, receipt)
    target = root / provenance.PUBLICATION_RECEIPT
    target.parent.mkdir(parents=True)
    target.write_bytes((root / provenance.RECEIPT).read_bytes())


def test_pinned_source_ancestry_survives_only_a_confirmed_identical_squash(
    bridge, monkeypatch
) -> None:
    root, head, payload, receipt, _ = bridge
    receipt["reviewed_source_commits"] = [payload["source_commit"]]
    _pending_publication_receipt(root, payload, receipt)
    monkeypatch.setattr(
        provenance,
        "_read_github_json",
        lambda _: copy.deepcopy(receipt["github_pull_request"]),
    )
    assert not provenance._ancestor(root, payload["source_commit"], head)
    provenance.require_published_ancestor(root, payload["source_commit"])


@pytest.mark.parametrize(
    "fault",
    [
        "unmerged",
        "wrong-pr",
        "wrong-repo",
        "tree",
        "unreviewed",
        "unavailable",
        "unreachable-merge",
        "unrelated-source",
        "missing-objects",
    ],
)
def test_source_publication_bridge_fails_closed(bridge, monkeypatch, fault) -> None:
    root, _, payload, receipt, git = bridge
    source = payload["source_commit"]
    if fault == "unrelated-source":
        source = git("commit-tree", receipt["merged_tree"], "-m", "unrelated source")
    receipt["reviewed_source_commits"] = [] if fault == "unreviewed" else [source]
    if fault == "unreachable-merge":
        receipt["github_pull_request"]["merge_commit_sha"] = git(
            "commit-tree",
            receipt["merged_tree"],
            "-p",
            receipt["github_pull_request"]["head"]["sha"],
            "-m",
            "not merged into current branch",
        )
    if fault == "missing-objects":
        original_tree = provenance._tree
        published = receipt["github_pull_request"]["head"]["sha"]
        monkeypatch.setattr(
            provenance,
            "_tree",
            lambda r, c: "" if c == published else original_tree(r, c),
        )
    _pending_publication_receipt(root, payload, receipt)

    def read(_):
        if fault == "unavailable":
            raise OSError("GitHub unavailable")
        pr = copy.deepcopy(receipt["github_pull_request"])
        if fault == "unmerged":
            pr["merged"] = False
        elif fault == "wrong-pr":
            pr["number"] = 99
        elif fault == "wrong-repo":
            pr["base"]["repo"]["full_name"] = "other/repository"
        elif fault == "tree":
            pr["head"]["sha"] = payload["source_commit"]
        return pr

    monkeypatch.setattr(provenance, "_read_github_json", read)
    with pytest.raises((ValueError, OSError)):
        provenance.require_published_ancestor(root, source)


def test_normal_ancestry_does_not_require_publication_or_network(
    bridge, monkeypatch
) -> None:
    root, _, _, _, git = bridge
    base = git("rev-parse", "HEAD^")
    monkeypatch.setattr(
        provenance, "_read_github_json", lambda _: pytest.fail("Unexpected network")
    )
    provenance.require_published_ancestor(root, base)


@pytest.mark.parametrize("qa_changed", ["unchanged", "committed", "dirty"])
def test_native_ci_receipt_retains_real_run_and_survives_squash(
    bridge, monkeypatch, qa_changed
) -> None:
    root, merge, payload, receipt, git = bridge
    published = receipt["github_pull_request"]["head"]["sha"]
    git("checkout", "--detach", published)
    payload.update(
        source_run_id="123",
        source_event="workflow_dispatch",
        source_branch="fixture",
        source_run_url="https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/123",
        coverage={},
        duration_telemetry={},
    )
    if qa_changed != "unchanged":
        changed = root / "scripts/engineering/qa/fixture.py"
        changed.write_text("changed = True\n")
        if qa_changed == "committed":
            git("add", "--", "scripts/engineering/qa/fixture.py")
            git("commit", "-qm", "changed producer input")
    review = root / "configs/quality/external_resource_inventory_qm08_review.json"
    review.write_text(
        json.dumps(
            {
                "catalog_ref": payload["source_commit"],
                "source_ref": payload["source_commit"],
            }
        )
    )
    host = root / "grafana/tooling/router-v7-bridge/host-image.json"
    host.parent.mkdir(parents=True)
    host.write_text(
        json.dumps({"delivery_source": {"source_ref": payload["source_commit"]}})
    )
    pr = copy.deepcopy(receipt["github_pull_request"])
    pr.update(
        merged=False, merge_commit_sha="0" * 40
    )  # GitHub's preview is not a merge.

    def read(path):
        if path == "pulls/42":
            return copy.deepcopy(pr)
        if path == "actions/runs/123":
            return {
                "id": 123,
                "head_sha": payload["source_commit"],
                "head_branch": "fixture",
                "event": "workflow_dispatch",
                "path": ".github/workflows/nightly.yml",
                "status": "completed",
                "conclusion": "failure",
                "html_url": "https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/123",
            }
        if path == "actions/runs/123/jobs?per_page=100":
            return {
                "total_count": 2,
                "jobs": [
                    {"name": name, "conclusion": "success"}
                    for name in (
                        "tests / coverage-verify",
                        "tests / duration-telemetry",
                    )
                ],
            }
        pytest.fail("Unexpected API path: " + path)

    monkeypatch.setattr(provenance, "_read_github_json", read)
    if qa_changed != "unchanged":
        with pytest.raises(ValueError, match="Producer inputs changed"):
            provenance.build_ci_squash_receipt(
                payload, root=root, pull_request=42, run_id=123
            )
        return
    original = copy.deepcopy(payload)
    result = provenance.build_ci_squash_receipt(
        payload, root=root, pull_request=42, run_id=123
    )
    assert result["github_pull_request"]["merged"] is False
    assert result["github_pull_request"]["merge_commit_sha"] is None
    assert (
        result["ci_run"]["conclusion"] == "failure"
    )  # Never promote overall CI to PASS.
    provenance.write_ci_publication_receipts(root, result)
    git("checkout", "--detach", merge)
    pr.update(merged=True, merge_commit_sha=merge)
    assert provenance.source_commit_is_reachable(payload, root, merge)
    provenance.require_published_ancestor(root, payload["source_commit"])
    assert payload == original
    changed = copy.deepcopy(payload)
    changed["coverage"]["forged"] = 100
    assert not provenance.source_commit_is_reachable(changed, root, merge)
    publication = root / provenance.PUBLICATION_RECEIPT
    before = publication.read_bytes()
    (root / provenance.RECEIPT).write_text("{}")
    provenance.require_published_ancestor(root, payload["source_commit"])
    assert publication.read_bytes() == before


@pytest.mark.parametrize(
    "fault",
    ["head", "event", "id", "failed-job", "missing-job", "duplicate-job", "incomplete"],
)
def test_ci_bridge_rejects_unqualified_or_mismatched_producer(
    monkeypatch, fault
) -> None:
    payload = {
        "source_commit": "a" * 40,
        "source_run_id": "123",
        "source_event": "workflow_dispatch",
        "source_branch": "fixture",
        "source_run_url": "https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/123",
    }
    run = {
        "id": 123,
        "head_sha": payload["source_commit"],
        "head_branch": "fixture",
        "html_url": payload["source_run_url"],
        "event": "workflow_dispatch",
        "path": ".github/workflows/nightly.yml",
        "status": "completed",
    }
    jobs = {
        "total_count": 2,
        "jobs": [
            {"name": name, "conclusion": "success"}
            for name in ("tests / coverage-verify", "tests / duration-telemetry")
        ],
    }
    if fault == "head":
        run["head_sha"] = "b" * 40
    elif fault == "event":
        run["event"] = "schedule"
    elif fault == "id":
        payload["source_run_id"] = "999"
    elif fault == "failed-job":
        jobs["jobs"][0]["conclusion"] = "failure"
    elif fault == "missing-job":
        jobs["jobs"].pop()
    elif fault == "duplicate-job":
        jobs["jobs"].append(copy.deepcopy(jobs["jobs"][0]))
    else:
        jobs["total_count"] = 101
    monkeypatch.setattr(
        provenance, "_read_github_json", lambda path: jobs if "/jobs?" in path else run
    )
    with pytest.raises(ValueError):
        provenance._ci_capture_run(payload, 123)


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
