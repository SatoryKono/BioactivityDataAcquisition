"""Validate an auditable squash bridge without rewriting captured run identity.

The checked-in GitHub receipt is local reviewed evidence, not a signature or a
CI execution receipt. Git objects independently bind its commit/tree claims.
"""

from __future__ import annotations

import base64
import argparse
import binascii
import hashlib
import io
import json
import os
import re
import subprocess
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from datetime import UTC, datetime
from typing import Any

REPOSITORY = "SatoryKono/BioactivityDataAcquisition"
COVERAGE_ARTIFACT = "coverage-report"
DURATION_ARTIFACT = "test-duration-telemetry"
# These are the 17 coverage-data owners in tests.yml, not artifact presence.
# GitHub truncates long matrix display names, so their canonical prefix is used.
COVERAGE_PRODUCER_JOBS = (
    "tests / smoke-check",
    "tests / contract-confidence",
    *(f"tests / Repo-backed unit ({group})" for group in ("product", "tooling", "ops")),
    *(
        f"tests / Unit scripts tooling ({group})"
        for group in ("passport", "debt-governance", "other")
    ),
    "tests / unit-filesystem-contracts",
    "tests / unit-subprocess-backed",
    *(
        f"tests / test-matrix (3.13, {group}, "
        for group in (
            "unit-domain",
            "unit-application",
            "unit-infrastructure",
            "unit-other",
            "integration",
            "security",
        )
    ),
    "tests / serial-coverage",
)
RECEIPT = Path("reports/test-telemetry/squash-provenance.json")
PUBLICATION_RECEIPT = Path(
    "reports/quality/quality-move-qm08/publication-provenance.json"
)


class ShallowMergeHistoryError(ValueError):
    """The squash merge cannot be proven below a newer shallow tip."""


TEST_INPUTS = (
    "src/bioetl",
    "scripts/engineering/ci",
    "scripts/engineering/dev",
    "scripts/engineering/qa",
    "tests",
    "pyproject.toml",
    "configs/quality/test_matrix.yaml",
    ".github/workflows/tests.yml",
)


def _url_origin(url: str) -> tuple[str, str | None, int | None]:
    """Return the normalized origin used to decide whether auth may be reused."""
    parsed = urllib.parse.urlsplit(url)
    scheme = parsed.scheme.lower()
    port = parsed.port
    if port is None:
        port = {"http": 80, "https": 443}.get(scheme)
    return scheme, parsed.hostname, port


class _SameOriginAuthRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Keep authorization only when urllib redirects within the same origin."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        if urllib.parse.urlsplit(newurl).scheme.lower() != "https":
            return None
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None and _url_origin(req.full_url) != _url_origin(
            redirected.full_url
        ):
            redirected.remove_header("Authorization")
        return redirected


def _request_github_json(url: str, token: str | None) -> dict[str, Any]:
    """Read one GitHub JSON object. A scoped token is not required for public data."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "BioETL-telemetry",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    opener = urllib.request.build_opener(_SameOriginAuthRedirectHandler())
    with opener.open(request, timeout=15) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError("GitHub response must be an object")
    return payload


def _read_github_json(path: str) -> dict[str, Any]:
    """Read the fixed repository API once; access/network failures fail closed.

    ``GITHUB_TOKEN`` on a job limited to ``contents: read`` is rejected by the
    pull-request API. Public repository data is still readable without that
    token, so an authentication rejection retries once unauthenticated.
    """
    url = f"https://api.github.com/repos/{REPOSITORY}/{path}"
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    try:
        return _request_github_json(url, token)
    except urllib.error.HTTPError as exc:
        if token and exc.code in {401, 403}:
            return _request_github_json(url, None)
        raise


def _refresh_live_mapping(receipt: dict[str, Any]) -> dict[str, Any]:
    """Resolve the merge only when it exists, avoiding a future-SHA stamp."""
    number = receipt.get("github_pull_request", {}).get("number")
    if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
        raise ValueError("Invalid pull request number")
    url = f"https://api.github.com/repos/{REPOSITORY}/pulls/{number}"
    if receipt.get("retrieved_from") != url:
        raise ValueError("Unapproved receipt URL")
    refreshed = dict(receipt)
    refreshed["github_pull_request"] = _read_github_json(f"pulls/{number}")
    # The prior snapshot can predate the final evidence-only commit and squash.
    refreshed.pop("merged_tree", None)
    return refreshed


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def _ancestor(root: Path, commit: str, head: str) -> bool:
    return _git(root, "merge-base", "--is-ancestor", commit, head).returncode == 0


def _is_shallow(root: Path) -> bool:
    result = _git(root, "rev-parse", "--is-shallow-repository")
    return result.returncode == 0 and result.stdout.strip() == "true"


def _tree(root: Path, commit: str) -> str:
    result = _git(root, "rev-parse", f"{commit}^{{tree}}")
    return result.stdout.strip() if result.returncode == 0 else ""


def _verified_object(encoded: str, kind: str, oid: str) -> bytes:
    raw = base64.b64decode(encoded, validate=True)
    header = f"{kind} {len(raw)}\0".encode("ascii")
    if hashlib.sha1(header + raw, usedforsecurity=False).hexdigest() != oid:
        raise ValueError("Git object proof has a wrong object ID")
    return raw


def _commit_tree(raw: bytes) -> str:
    for line in raw.split(b"\n\n", 1)[0].splitlines():
        if line.startswith(b"tree "):
            return line[5:].decode("ascii")
    raise ValueError("Git object proof has no commit tree")


def _commit_parents(raw: bytes) -> list[str]:
    return [
        line[7:].decode("ascii")
        for line in raw.split(b"\n\n", 1)[0].splitlines()
        if line.startswith(b"parent ")
    ]


def _tree_entry(raw: bytes, name: bytes) -> tuple[bytes, str] | None:
    offset = 0
    while offset < len(raw):
        separator = raw.index(b" ", offset)
        end = raw.index(b"\0", separator + 1)
        mode = raw[offset:separator]
        entry_name = raw[separator + 1 : end]
        object_id = raw[end + 1 : end + 21]
        if len(object_id) != 20:
            raise ValueError("Truncated Git tree object")
        offset = end + 21
        if entry_name == name:
            return mode, object_id.hex()
    return None


def _proof_path(
    trees: dict[str, str], root_oid: str, path: str
) -> tuple[bytes, str] | None:
    oid = root_oid
    parts = path.encode("utf-8").split(b"/")
    for index, part in enumerate(parts):
        raw = _verified_object(trees[oid], "tree", oid)
        entry = _tree_entry(raw, part)
        if entry is None:
            return None
        mode, oid = entry
        if index < len(parts) - 1 and mode not in {b"40000", b"040000"}:
            return None
    return mode, oid


def _object_proof_relation(
    receipt: dict[str, Any], source: str, pr_head: str
) -> tuple[bool, str]:
    """Verify retained Git objects when squash removed the PR commits from main."""
    try:
        proof = receipt["git_object_proof"]
        chain = proof["commit_chain"]
        trees = proof["trees"]
        if not isinstance(chain, list) or not 1 <= len(chain) <= 128:
            return False, ""
        if chain[0]["oid"] != source or chain[-1]["oid"] != pr_head:
            return False, ""
        commits = [
            _verified_object(item["raw"], "commit", item["oid"]) for item in chain
        ]
        if any(
            chain[index - 1]["oid"] not in _commit_parents(commits[index])
            for index in range(1, len(chain))
        ):
            return False, ""
        source_tree = _commit_tree(commits[0])
        head_tree = _commit_tree(commits[-1])
        same_inputs = all(
            (entry := _proof_path(trees, source_tree, path)) is not None
            and entry == _proof_path(trees, head_tree, path)
            for path in TEST_INPUTS
        )
        return same_inputs, head_tree
    except (binascii.Error, KeyError, TypeError, ValueError, UnicodeError):
        return False, ""


def build_git_object_proof(root: Path, source: str, pr_head: str) -> dict[str, Any]:
    """Retain the minimal Git objects needed to audit unchanged test inputs."""
    if any(
        len(oid) != 40 or any(character not in "0123456789abcdef" for character in oid)
        for oid in (source, pr_head)
    ):
        raise ValueError("Git object proof requires full commit object IDs")

    def read(kind: str, oid: str) -> bytes:
        return subprocess.check_output(["git", "cat-file", kind, oid], cwd=root)

    reverse_chain = [pr_head]
    while reverse_chain[-1] != source:
        if len(reverse_chain) >= 128:
            raise ValueError("Git object proof exceeds 128 commits")
        parents = _commit_parents(read("commit", reverse_chain[-1]))
        parent = next(
            (oid for oid in parents if oid == source or _ancestor(root, source, oid)),
            None,
        )
        if parent is None or parent in reverse_chain:
            raise ValueError("Captured source is not an ancestor of PR head")
        reverse_chain.append(parent)
    commit_chain = [
        {"oid": oid, "raw": base64.b64encode(read("commit", oid)).decode("ascii")}
        for oid in reversed(reverse_chain)
    ]
    trees: dict[str, str] = {}
    for commit in (source, pr_head):
        root_oid = _tree(root, commit)
        if not root_oid:
            raise ValueError("Missing commit tree for Git object proof")
        for path in TEST_INPUTS:
            oid = root_oid
            for part in path.encode("utf-8").split(b"/"):
                raw = read("tree", oid)
                trees[oid] = base64.b64encode(raw).decode("ascii")
                entry = _tree_entry(raw, part)
                if entry is None:
                    raise ValueError(f"Missing test input in Git object proof: {path}")
                _, oid = entry
    proof: dict[str, Any] = {"commit_chain": commit_chain, "trees": trees}
    verified, _ = _object_proof_relation({"git_object_proof": proof}, source, pr_head)
    if not verified:
        raise ValueError("Git object proof does not preserve test inputs")
    return proof


def _ci_receipt_matches(receipt: dict[str, Any], payload: dict[str, Any]) -> bool:
    if payload.get("source_event") == "local_coverage_verify":
        return False
    if receipt.get("source_tree_sha256") != payload.get("source_tree_sha256"):
        return False
    if "metrics_sha256" not in receipt:
        return True  # Retain the existing reviewed legacy receipt contract.
    try:
        actual = receipt["metrics_sha256"]
        return isinstance(actual, str) and actual == telemetry_metrics_sha256(payload)
    except (KeyError, TypeError, ValueError):
        return False


def _receipt_matches_capture(receipt: dict[str, Any], payload: dict[str, Any]) -> bool:
    if receipt.get("schema_version") != 1:
        return False
    if any(
        receipt.get(key) != payload.get(key)
        for key in ("source_commit", "source_run_id")
    ):
        return False
    measurement = payload.get("measurement_provenance")
    if not isinstance(measurement, dict):
        return _ci_receipt_matches(receipt, payload)
    try:
        metrics_digest = telemetry_metrics_sha256(payload)
    except (KeyError, TypeError, ValueError):
        return False
    return (
        measurement.get("head") == payload.get("source_commit")
        and receipt.get("source_tree_sha256") == measurement.get("test_tree_sha256")
        and receipt.get("manifest_sha256") == measurement.get("manifest_sha256")
        and receipt.get("metrics_sha256") == metrics_digest
    )


def telemetry_metrics_sha256(payload: dict[str, Any]) -> str:
    """Bind the reported coverage and duration values to a reviewed capture."""
    metrics = {field: payload[field] for field in ("coverage", "duration_telemetry")}
    encoded = json.dumps(
        metrics, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def capture_metrics_are_bound(payload: dict[str, Any], root: Path) -> bool:
    """Require a capture-matched receipt before preserving metrics on rebind."""
    try:
        receipt = json.loads((root / RECEIPT).read_text(encoding="utf-8"))
        return _receipt_matches_capture(receipt, payload)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def _github_mapping(receipt: dict[str, Any]) -> tuple[str, str] | None:
    pr = receipt.get("github_pull_request", {})
    number = pr.get("number")
    if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
        return None
    expected_url = f"https://api.github.com/repos/{REPOSITORY}/pulls/{number}"
    if receipt.get("retrieved_from") != expected_url or pr.get("merged") is not True:
        return None
    if pr.get("base", {}).get("repo", {}).get("full_name") != REPOSITORY:
        return None
    head = pr.get("head", {}).get("sha", "")
    merge = pr.get("merge_commit_sha", "")
    if not all(
        isinstance(value, str)
        and len(value) == 40
        and all(c in "0123456789abcdef" for c in value)
        for value in (head, merge)
    ):
        return None
    return head, merge


def _source_relation(
    root: Path, source: str, pr_head: str, *, live: bool
) -> tuple[bool, dict[str, Any] | None]:
    """Use local objects, or an authoritative bounded compare for a shallow clone."""
    objects = all(_tree(root, commit) for commit in (source, pr_head))
    if objects and (_ancestor(root, source, pr_head) or not _is_shallow(root)):
        unchanged = _git(root, "diff", "--quiet", source, pr_head, "--", *TEST_INPUTS)
        return _ancestor(root, source, pr_head) and unchanged.returncode == 0, None
    if not live:
        return False, None
    comparison = _read_github_json(f"compare/{source}...{pr_head}")
    files = comparison.get("files")
    if not isinstance(files, list) or len(files) >= 300:
        return False, comparison
    ancestor = comparison.get("merge_base_commit", {}).get("sha") == source
    ahead = comparison.get("status") in {"ahead", "identical"}
    paths = [
        str(item.get(key, ""))
        for item in files
        for key in ("filename", "previous_filename")
    ]
    changed = any(
        path == owner or path.startswith(owner + "/")
        for path in paths
        for owner in TEST_INPUTS
    )
    return ancestor and ahead and not changed, comparison


def _pr_tree(root: Path, pr_head: str, *, live: bool) -> str:
    tree = _tree(root, pr_head)
    if not tree and live:
        tree = str(
            _read_github_json(f"git/commits/{pr_head}").get("tree", {}).get("sha", "")
        )
    return tree


LAST_REACHABILITY_REASON = ""


def _reject(reason: str) -> bool:
    """Record why a squash bridge was rejected and return False."""
    global LAST_REACHABILITY_REASON
    LAST_REACHABILITY_REASON = reason
    return False


def validate_squash_bridge(
    payload: dict[str, Any], receipt: dict[str, Any], root: Path, head: str
) -> bool:
    """Require merge history when HEAD is newer than a shallow squash checkout."""
    if not _receipt_matches_capture(receipt, payload):
        return _reject("receipt_mismatch")
    mapping = _github_mapping(receipt)
    if mapping is None:
        return _reject("mapping_missing")
    pr_head, merge = mapping
    if head != merge and _is_shallow(root):
        raise ShallowMergeHistoryError(
            "Unshallow the checkout before validating a squash merge below HEAD"
        )
    source = str(payload["source_commit"])
    live = receipt.get("verification_mode") == "live_github"
    source_tree = _tree(root, source)
    pr_tree = _tree(root, pr_head)
    related = False
    tree = ""
    if source_tree and pr_tree and _ancestor(root, source, pr_head):
        related, _ = _source_relation(root, source, pr_head, live=False)
        tree = pr_tree
    elif _is_shallow(root) or not (source_tree and pr_tree):
        if "git_object_proof" in receipt:
            related, tree = _object_proof_relation(receipt, source, pr_head)
        if not related and live:
            related, _ = _source_relation(root, source, pr_head, live=True)
            tree = _pr_tree(root, pr_head, live=True)
    if not related:
        return _reject("source_unrelated")
    if not _ancestor(root, merge, head):
        return _reject("merge_not_ancestor")
    if not tree or tree != _tree(root, merge):
        return _reject("tree_mismatch")
    if not live and tree != receipt.get("merged_tree"):
        return _reject("merged_tree_mismatch")
    number = receipt["github_pull_request"]["number"]
    subject = _git(root, "show", "-s", "--format=%s", merge)
    if subject.returncode or f"(#{number})" not in subject.stdout:
        return _reject("subject_mismatch")
    return True


def source_commit_is_reachable(payload: dict[str, Any], root: Path, head: str) -> bool:
    """Keep normal ancestry; require a reviewed bridge for a squash capture."""
    global LAST_REACHABILITY_REASON
    LAST_REACHABILITY_REASON = ""
    if _ancestor(root, str(payload["source_commit"]), head):
        return True
    try:
        receipt = json.loads((root / RECEIPT).read_text(encoding="utf-8"))
        if not _receipt_matches_capture(receipt, payload):
            return _reject("receipt_mismatch")
        if receipt.get("verification_mode") == "live_github":
            try:
                receipt = _refresh_live_mapping(receipt)
            except (OSError, ValueError, KeyError, TypeError, AttributeError):
                if "git_object_proof" not in receipt:
                    return False
        return validate_squash_bridge(payload, receipt, root, head)
    except ShallowMergeHistoryError:
        raise
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        return _reject(f"{type(exc).__name__}: {exc}")


def require_published_ancestor(root: Path, commit: str) -> None:
    """Require Git ancestry, or the same ancestry across a verified GitHub squash.

    This proves publication lineage only. Each caller must still verify all its
    pinned source/review/artifact inputs; this never qualifies changed inputs.
    """
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise ValueError("Full immutable source commit required")
    commit = bytes.fromhex(commit).hex()
    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    if _ancestor(root, commit, head):
        return
    receipt = json.loads((root / PUBLICATION_RECEIPT).read_text(encoding="utf-8"))
    reviewed = receipt.get("reviewed_source_commits")
    if (
        receipt.get("schema_version") != 1
        or receipt.get("verification_mode") != "live_github"
        or not isinstance(reviewed, list)
        or commit not in reviewed
    ):
        raise ValueError("Source lacks a reviewed publication bridge")
    refreshed = _refresh_live_mapping(receipt)
    mapping = _github_mapping(refreshed)
    if mapping is None:
        raise ValueError("GitHub has not confirmed the declared squash merge")
    pr_head, merge = mapping
    merged_tree, published_tree = _tree(root, merge), _tree(root, pr_head)
    if (
        not merged_tree
        or merged_tree != published_tree
        or not _ancestor(root, merge, head)
        or not _ancestor(root, commit, pr_head)
    ):
        raise ValueError("Publication tree/ancestry does not prove the pinned source")


def _ci_capture_run(payload: dict[str, Any], run_id: int) -> dict[str, Any]:
    """Read actual producer identity; overall workflow success is a separate gate."""
    if isinstance(run_id, bool) or run_id <= 0:
        raise ValueError("Positive CI run ID required")
    run = _read_github_json(f"actions/runs/{run_id}")
    if (
        str(run_id) != str(payload["source_run_id"])
        or run.get("id") != run_id
        or payload.get("source_event") != "workflow_dispatch"
        or run.get("head_sha") != payload["source_commit"]
        or run.get("head_branch") != payload["source_branch"]
        or run.get("html_url") != payload["source_run_url"]
        or run.get("html_url")
        != f"https://github.com/{REPOSITORY}/actions/runs/{run_id}"
        or run.get("event") != payload.get("source_event")
        or run.get("path") != ".github/workflows/nightly.yml"
        or run.get("status") != "completed"
    ):
        raise ValueError("CI run does not match the captured Nightly identity")
    jobs = _read_github_json(f"actions/runs/{run_id}/jobs?per_page=100")
    if jobs.get("total_count", 0) > 100 or jobs.get("total_count") != len(
        jobs.get("jobs", [])
    ):
        raise ValueError("Producer job response is incomplete")
    selected = _qualified_capture_jobs(run, jobs["jobs"])
    return {**run, "verified_capture_jobs": selected}


def _qualified_capture_jobs(
    run: dict[str, Any], jobs: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Reject coverage from failed, missing, duplicate or foreign producers."""
    selected = []
    for selector in (
        *COVERAGE_PRODUCER_JOBS,
        "tests / coverage-verify",
        "tests / duration-telemetry",
    ):
        matches = [
            job
            for job in jobs
            if (
                str(job.get("name", "")).startswith(selector)
                if selector.endswith(", ")
                else job.get("name") == selector
            )
        ]
        if len(matches) != 1:
            raise ValueError(
                "Required CI capture producer is missing or ambiguous: " + selector
            )
        job = matches[0]
        if (
            job.get("status") != "completed"
            or job.get("conclusion") != "success"
            or job.get("run_id") != run["id"]
            or job.get("run_attempt") != run["run_attempt"]
            or job.get("head_sha") != run["head_sha"]
        ):
            raise ValueError(
                "Required CI capture producer did not succeed on this attempt: "
                + selector
            )
        selected.append(
            {
                key: job[key]
                for key in (
                    "id",
                    "name",
                    "run_id",
                    "run_attempt",
                    "head_sha",
                    "status",
                    "conclusion",
                )
            }
        )
    return selected


def _publication_sources(root: Path, source: str) -> list[str]:
    review = json.loads(
        (
            root / "configs/quality/external_resource_inventory_qm08_review.json"
        ).read_text(encoding="utf-8")
    )
    host = json.loads(
        (root / "grafana/tooling/router-v7-bridge/host-image.json").read_text(
            encoding="utf-8"
        )
    )
    commits = sorted(
        {
            source,
            review["catalog_ref"],
            review["source_ref"],
            host["delivery_source"]["source_ref"],
        }
    )
    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    for commit in commits:
        if re.fullmatch(r"[0-9a-f]{40}", commit) is None or not _ancestor(
            root, commit, head
        ):
            raise ValueError("Publication input is not an immutable ancestor")
    return commits


def _require_clean_producer_inputs(root: Path) -> None:
    changed = _git(root, "diff", "--quiet", "HEAD", "--", *TEST_INPUTS)
    untracked = _git(
        root, "ls-files", "--others", "--exclude-standard", "--", *TEST_INPUTS
    )
    if changed.returncode or untracked.returncode or untracked.stdout.strip():
        raise ValueError("Producer inputs changed in the working tree")


def _read_artifact_bytes(artifact_id: int, size: int) -> bytes:
    """Download a fixed repository artifact without forwarding auth off-origin."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "BioETL-telemetry",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPOSITORY}/actions/artifacts/{artifact_id}/zip",
        headers=headers,
    )
    opener = urllib.request.build_opener(_SameOriginAuthRedirectHandler())
    with opener.open(request, timeout=30) as response:
        data = response.read(size + 1)
    if not isinstance(data, bytes):
        raise ValueError("Artifact response is not binary data")
    return data


def _verified_artifact_member(
    artifact: dict[str, Any], run: dict[str, Any], member: str
) -> bytes:
    identity, size = artifact.get("id"), artifact.get("size_in_bytes")
    workflow = artifact.get("workflow_run", {})
    if (
        not isinstance(identity, int)
        or isinstance(identity, bool)
        or identity <= 0
        or not isinstance(size, int)
        or isinstance(size, bool)
        or size <= 0
        or artifact.get("expired") is not False
        or workflow.get("id") != run["id"]
        or workflow.get("head_sha") != run["head_sha"]
        or workflow.get("head_branch") != run["head_branch"]
    ):
        raise ValueError("Artifact identity does not match the captured run")
    raw = _read_artifact_bytes(identity, size)
    if (
        len(raw) != size
        or artifact.get("digest") != "sha256:" + hashlib.sha256(raw).hexdigest()
    ):
        raise ValueError("Original artifact size/digest mismatch")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = [entry for entry in archive.infolist() if entry.filename == member]
        if len(entries) != 1 or entries[0].is_dir():
            raise ValueError("Artifact member is missing or ambiguous: " + member)
        return archive.read(entries[0])


def _require_original_ci_metrics(
    payload: dict[str, Any], run: dict[str, Any]
) -> list[dict[str, Any]]:
    """Derive expected metrics from run-bound archives, never from the YAML values."""
    from scripts.engineering.ci.update_test_telemetry_baseline import (
        DEFAULT_COVERAGE_THRESHOLD,
        build_baseline_payload,
    )

    listing = _read_github_json(f"actions/runs/{run['id']}/artifacts?per_page=100")
    artifacts = listing["artifacts"]
    if listing.get("total_count") != len(artifacts) or len(artifacts) > 100:
        raise ValueError("Artifact listing is incomplete")
    inputs = {}
    receipts = []
    for name, member in (
        (COVERAGE_ARTIFACT, "coverage/coverage.xml"),
        (DURATION_ARTIFACT, "slowest-tests.json"),
    ):
        matches = [a for a in artifacts if a.get("name") == name]
        if len(matches) != 1:
            raise ValueError("Capture artifact is missing or ambiguous: " + name)
        artifact = matches[0]
        inputs[name] = _verified_artifact_member(artifact, run, member)
        receipts.append(
            {
                "artifact": artifact,
                "member": member,
                "member_sha256": hashlib.sha256(inputs[name]).hexdigest(),
            }
        )
    slowest = json.loads(inputs[DURATION_ARTIFACT])
    if (
        slowest.get("source_commit") != run["head_sha"]
        or slowest.get("source_run_id") != f"github-{run['id']}-{run['run_attempt']}"
    ):
        raise ValueError("Duration artifact does not identify the captured attempt")
    with tempfile.TemporaryDirectory(prefix="bioetl-ci-capture-") as directory:
        coverage = Path(directory) / "coverage.xml"
        durations = Path(directory) / "slowest.json"
        coverage.write_bytes(inputs[COVERAGE_ARTIFACT])
        durations.write_bytes(inputs[DURATION_ARTIFACT])
        expected = build_baseline_payload(
            coverage_xml_path=coverage,
            coverage_percent=None,
            coverage_log_path=None,
            slowest_json_path=durations,
            junit_paths=[],
            source_branch=run["head_branch"],
            source_commit=run["head_sha"],
            source_run_id=str(run["id"]),
            coverage_threshold=DEFAULT_COVERAGE_THRESHOLD,
            source_tree_sha256=payload["source_tree_sha256"],
            source_event=run["event"],
            source_run_url=run["html_url"],
        )
    require_capture_metrics(payload, expected)
    return receipts


def build_ci_squash_receipt(
    payload: dict[str, Any], *, root: Path, pull_request: int, run_id: int
) -> dict[str, Any]:
    """Materialize a pending live bridge; never invent a future merge identity."""
    from scripts.engineering.ci.update_test_telemetry_baseline import (
        compute_test_telemetry_source_tree_sha256,
    )

    _require_clean_producer_inputs(root)
    run = _ci_capture_run(payload, run_id)
    source = str(payload["source_commit"])
    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    if payload["source_tree_sha256"] != compute_test_telemetry_source_tree_sha256(root):
        raise ValueError("Captured test inputs changed")
    related, _ = _source_relation(root, source, head, live=False)
    if not related:
        raise ValueError("Producer inputs changed after the captured run")
    artifacts = _require_original_ci_metrics(payload, run)
    pr = _read_github_json(f"pulls/{pull_request}")
    if (
        pr.get("number") != pull_request
        or pr.get("head", {}).get("sha") != head
        or pr.get("base", {}).get("repo", {}).get("full_name") != REPOSITORY
    ):
        raise ValueError("Published PR head does not match this checkout")
    return {
        "schema_version": 1,
        "verification_mode": "live_github",
        "source_commit": source,
        "source_run_id": payload["source_run_id"],
        "source_tree_sha256": payload["source_tree_sha256"],
        "metrics_sha256": telemetry_metrics_sha256(payload),
        "ci_artifact_inputs": artifacts,
        "ci_capture_producers": run["verified_capture_jobs"],
        "reviewed_source_commits": _publication_sources(root, source),
        "retrieved_from": f"https://api.github.com/repos/{REPOSITORY}/pulls/{pull_request}",
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "github_pull_request": {
            "number": pr["number"],
            "merged": pr["merged"],
            "base": {"repo": {"full_name": REPOSITORY}},
            "head": {"sha": head},
            "merge_commit_sha": pr["merge_commit_sha"] if pr["merged"] else None,
        },
        "ci_run": {
            key: run[key]
            for key in (
                "id",
                "head_sha",
                "event",
                "path",
                "status",
                "conclusion",
                "html_url",
                "run_attempt",
            )
        },
        "git_object_proof": build_git_object_proof(root, source, head),
        "trust_statement": "Reviewed publication mapping; not a CI execution attestation or trust upgrade.",
    }


def _write_receipt_atomically(destination: Path, receipt: dict[str, Any]) -> None:
    """Publish a complete receipt without truncating a prior valid one."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(receipt, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_ci_publication_receipts(root: Path, receipt: dict[str, Any]) -> None:
    """Keep source publication lineage independent of future telemetry captures."""
    publication = {
        key: receipt[key]
        for key in (
            "schema_version",
            "verification_mode",
            "reviewed_source_commits",
            "retrieved_from",
            "retrieved_at_utc",
            "github_pull_request",
            "trust_statement",
        )
    }
    _write_receipt_atomically(root / RECEIPT, receipt)
    _write_receipt_atomically(root / PUBLICATION_RECEIPT, publication)


def require_capture_metrics(payload: dict[str, Any], expected: dict[str, Any]) -> None:
    """Reject telemetry values that were not derived from the validated capture."""
    for field in ("coverage", "duration_telemetry"):
        if payload.get(field) != expected[field]:
            raise ValueError(f"Committed {field} does not match local measurement")


def build_reviewed_squash_receipt(
    payload: dict[str, Any],
    *,
    root: Path,
    measurement_root: Path,
    manifest_path: Path,
    pull_request: int,
) -> dict[str, Any]:
    """Build a local reviewed bridge from a validated capture and merged PR."""
    from scripts.engineering.ci.local_test_telemetry import (
        build_local_baseline,
        validate_local_measurement,
    )
    from scripts.engineering.ci.update_test_telemetry_baseline import (
        compute_test_telemetry_source_tree_sha256,
    )
    from scripts.engineering.qa.report_module_coverage_inventory import (
        compute_source_tree_sha256,
    )

    capture = validate_local_measurement(
        manifest_path,
        repo_root=measurement_root,
        test_tree_sha256=compute_test_telemetry_source_tree_sha256(measurement_root),
        source_tree_sha256=compute_source_tree_sha256(repo_root=measurement_root),
    )
    manifest = capture["manifest"]
    measured = payload.get("measurement_provenance", {})
    if (
        payload.get("source_event") != "local_coverage_verify"
        or manifest["head"] != payload.get("source_commit")
        or "local-" + manifest_path.parent.name != payload.get("source_run_id")
        or manifest["test_tree_sha256"] != measured.get("test_tree_sha256")
        or manifest["source_tree_sha256"] != measured.get("source_tree_sha256")
        or capture["manifest_sha256"] != measured.get("manifest_sha256")
        or manifest["finished_at_utc"] != payload.get("refreshed_at_utc")
    ):
        raise ValueError("Measurement does not match committed telemetry capture")
    expected = build_local_baseline(manifest_path, repo_root=measurement_root)
    require_capture_metrics(payload, expected)
    pr = _read_github_json(f"pulls/{pull_request}")
    url = f"https://api.github.com/repos/{REPOSITORY}/pulls/{pull_request}"
    source = str(payload["source_commit"])
    pr_head = str(pr.get("head", {}).get("sha", ""))
    receipt = {
        "schema_version": 1,
        "source_commit": source,
        "source_run_id": payload["source_run_id"],
        "source_tree_sha256": manifest["test_tree_sha256"],
        "manifest_sha256": capture["manifest_sha256"],
        "metrics_sha256": telemetry_metrics_sha256(expected),
        "retrieved_from": url,
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "github_pull_request": {
            "number": pr.get("number"),
            "merged": pr.get("merged"),
            "base": {
                "repo": {
                    "full_name": pr.get("base", {}).get("repo", {}).get("full_name")
                }
            },
            "head": {"sha": pr_head},
            "merge_commit_sha": pr.get("merge_commit_sha"),
        },
        "merged_tree": _tree(root, str(pr.get("merge_commit_sha", ""))),
        "git_object_proof": build_git_object_proof(measurement_root, source, pr_head),
    }
    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    if not validate_squash_bridge(payload, receipt, root, head):
        raise ValueError("Reviewed squash bridge does not validate against HEAD")
    return receipt


def main() -> int:
    """Materialize a reviewed bridge without inventing run or merge identity."""
    import yaml

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--measurement-repo-root", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--local-manifest", type=Path)
    mode.add_argument("--ci-run-id", type=int)
    parser.add_argument("--pull-request", type=int, required=True)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    payload = yaml.safe_load(
        (root / "configs/quality/test_telemetry_baseline.yaml").read_text(
            encoding="utf-8"
        )
    )
    if args.ci_run_id is not None:
        receipt = build_ci_squash_receipt(
            payload, root=root, pull_request=args.pull_request, run_id=args.ci_run_id
        )
        write_ci_publication_receipts(root, receipt)
    else:
        if args.measurement_repo_root is None:
            parser.error("--local-manifest requires --measurement-repo-root")
        receipt = build_reviewed_squash_receipt(
            payload,
            root=root,
            measurement_root=args.measurement_repo_root.resolve(),
            manifest_path=args.local_manifest.resolve(),
            pull_request=args.pull_request,
        )
        _write_receipt_atomically(root / RECEIPT, receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
