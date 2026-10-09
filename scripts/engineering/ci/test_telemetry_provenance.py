"""Validate an auditable squash bridge without rewriting captured run identity.

The checked-in GitHub receipt is local reviewed evidence, not a signature or a
CI execution receipt. Git objects independently bind its commit/tree claims.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

REPOSITORY = "SatoryKono/BioactivityDataAcquisition"
RECEIPT = Path("reports/test-telemetry/squash-provenance.json")
TEST_INPUTS = (
    "tests",
    "pyproject.toml",
    "configs/quality/test_matrix.yaml",
    ".github/workflows/tests.yml",
)


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=False
    )


def _ancestor(root: Path, commit: str, head: str) -> bool:
    return _git(root, "merge-base", "--is-ancestor", commit, head).returncode == 0


def _tree(root: Path, commit: str) -> str:
    result = _git(root, "rev-parse", f"{commit}^{{tree}}")
    return result.stdout.strip() if result.returncode == 0 else ""


def _receipt_matches_capture(receipt: dict[str, Any], payload: dict[str, Any]) -> bool:
    return receipt.get("schema_version") == 1 and all(
        receipt.get(key) == payload.get(key)
        for key in ("source_commit", "source_run_id", "source_tree_sha256")
    )


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
        len(value) == 40 and all(c in "0123456789abcdef" for c in value)
        for value in (head, merge)
    ):
        return None
    return head, merge


def validate_squash_bridge(
    payload: dict[str, Any], receipt: dict[str, Any], root: Path, head: str
) -> bool:
    """Fail closed on a changed run, wrong PR, missing object, or different tree."""
    if not _receipt_matches_capture(receipt, payload):
        return False
    mapping = _github_mapping(receipt)
    if mapping is None:
        return False
    pr_head, merge = mapping
    source = str(payload["source_commit"])
    if not _ancestor(root, source, pr_head) or not _ancestor(root, merge, head):
        return False
    tree = _tree(root, pr_head)
    if not tree or tree != _tree(root, merge) or tree != receipt.get("merged_tree"):
        return False
    number = receipt["github_pull_request"]["number"]
    subject = _git(root, "show", "-s", "--format=%s", merge)
    if subject.returncode or f"(#{number})" not in subject.stdout:
        return False
    # Generated evidence can differ; maintained test inputs cannot.
    return (
        _git(root, "diff", "--quiet", source, pr_head, "--", *TEST_INPUTS).returncode
        == 0
    )


def source_commit_is_reachable(payload: dict[str, Any], root: Path, head: str) -> bool:
    """Keep normal ancestry; require a reviewed bridge for a squash capture."""
    if _ancestor(root, str(payload["source_commit"]), head):
        return True
    try:
        receipt = json.loads((root / RECEIPT).read_text(encoding="utf-8"))
        return validate_squash_bridge(payload, receipt, root, head)
    except (OSError, ValueError, KeyError, TypeError):
        return False
