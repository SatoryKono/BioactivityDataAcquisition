"""Validate an auditable squash bridge without rewriting captured run identity.

The checked-in GitHub receipt is local reviewed evidence, not a signature or a
CI execution receipt. Git objects independently bind its commit/tree claims.
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

REPOSITORY = "SatoryKono/BioactivityDataAcquisition"
RECEIPT = Path("reports/test-telemetry/squash-provenance.json")
TEST_INPUTS = (
    "src/bioetl",
    "scripts/engineering/ci",
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


def _read_github_json(path: str) -> dict[str, Any]:
    """Read the fixed repository API once; access/network failures fail closed."""
    url = f"https://api.github.com/repos/{REPOSITORY}/{path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "BioETL-telemetry",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    opener = urllib.request.build_opener(_SameOriginAuthRedirectHandler())
    with opener.open(request, timeout=15) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError("GitHub response must be an object")
    return payload


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
    if objects:
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
    live = receipt.get("verification_mode") == "live_github"
    related, _ = _source_relation(root, source, pr_head, live=live)
    if not related or not _ancestor(root, merge, head):
        return False
    tree = _pr_tree(root, pr_head, live=live)
    if not tree or tree != _tree(root, merge):
        return False
    if not live and tree != receipt.get("merged_tree"):
        return False
    number = receipt["github_pull_request"]["number"]
    subject = _git(root, "show", "-s", "--format=%s", merge)
    if subject.returncode or f"(#{number})" not in subject.stdout:
        return False
    return True


def source_commit_is_reachable(payload: dict[str, Any], root: Path, head: str) -> bool:
    """Keep normal ancestry; require a reviewed bridge for a squash capture."""
    if _ancestor(root, str(payload["source_commit"]), head):
        return True
    try:
        receipt = json.loads((root / RECEIPT).read_text(encoding="utf-8"))
        if not _receipt_matches_capture(receipt, payload):
            return False
        if receipt.get("verification_mode") == "live_github":
            receipt = _refresh_live_mapping(receipt)
        return validate_squash_bridge(payload, receipt, root, head)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False
