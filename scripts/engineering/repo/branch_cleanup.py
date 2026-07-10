#!/usr/bin/env python3
"""Generate branch cleanup inventory and apply phases 0-2 cleanup actions.

Phase 0:
    Build ``reports/quality/branch-cleanup-inventory-<date>.json`` with branch,
    PR, and cleanup classification metadata.

Phase 1:
    Delete curated garbage remote branches (dry-run by default).

Phase 2:
    Close stale draft PRs for automation/report branches older than the cutoff
    and delete their head branches (dry-run by default).

Usage:
    python scripts/engineering/repo/branch_cleanup.py inventory
    python scripts/engineering/repo/branch_cleanup.py inventory --output reports/quality/branch-cleanup-inventory-2026-07-10.json
    python scripts/engineering/repo/branch_cleanup.py apply --phases 1
    python scripts/engineering/repo/branch_cleanup.py apply --phases 1,2 --apply
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional in minimal envs
    load_dotenv = None  # type: ignore[assignment]

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.engineering.repo._branch_cleanup_policy import (
    DEFAULT_CUTOFF_ISO,
    DEFAULT_OWNER,
    DEFAULT_REPO,
    BranchRecord,
    CATEGORY_ORDER,
    build_branch_record,
    is_protected_branch,
    parse_cutoff,
)

API_BASE: Final[str] = "https://api.github.com"
PHASE2_CLOSE_COMMENT: Final[str] = (
    "Closing stale automation draft during branch hygiene phase 2 "
    "(>30 days, no active review). Branch head may be deleted after closeout."
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_token() -> str:
    if load_dotenv is not None:
        load_dotenv(_repo_root() / ".env")
    for env_name in ("GITHUB_TOKEN", "GITHUB_PERSONAL_ACCESS_TOKEN", "GH_TOKEN"):
        token = os.getenv(env_name, "").strip()
        if token:
            return token
    raise ValueError(
        "Missing GitHub token. Set GITHUB_TOKEN or GITHUB_PERSONAL_ACCESS_TOKEN."
    )


def _github_request(
    *,
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any] | None = None,
    accept_status: frozenset[int] = frozenset({200, 201, 204}),
) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
    }
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    for attempt in range(1, 5):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                status = response.status
                raw = response.read().decode("utf-8")
            if status not in accept_status:
                raise RuntimeError(f"GitHub API {method} {url} unexpected status {status}")
            if not raw:
                return None
            return json.loads(raw)
        except urllib.error.HTTPError as exc:
            if exc.code in {429, 500, 502, 503, 504} and attempt < 4:
                time.sleep(1.5 * attempt)
                continue
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"GitHub API {method} {url} failed: {exc.code} {detail}"
            ) from exc
    raise RuntimeError(f"GitHub API {method} {url} exhausted retries")


def _list_remote_branches(*, token: str, owner: str, repo: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        url = f"{API_BASE}/repos/{owner}/{repo}/branches?per_page=100&page={page}"
        batch = _github_request(method="GET", url=url, token=token)
        if not isinstance(batch, list) or not batch:
            break
        rows.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return rows


def _list_open_pull_requests(*, token: str, owner: str, repo: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        url = (
            f"{API_BASE}/repos/{owner}/{repo}/pulls?state=open&per_page=100&page={page}"
        )
        batch = _github_request(method="GET", url=url, token=token)
        if not isinstance(batch, list) or not batch:
            break
        rows.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return rows


def _commit_date(*, token: str, owner: str, repo: str, sha: str, cache: dict[str, str]) -> str:
    if sha in cache:
        return cache[sha]
    url = f"{API_BASE}/repos/{owner}/{repo}/commits/{sha}"
    payload = _github_request(method="GET", url=url, token=token)
    if not isinstance(payload, dict):
        raise RuntimeError(f"Missing commit payload for {sha}")
    commit = payload.get("commit")
    if not isinstance(commit, dict):
        raise RuntimeError(f"Malformed commit payload for {sha}")
    committer = commit.get("committer")
    if not isinstance(committer, dict):
        raise RuntimeError(f"Missing committer for {sha}")
    date = str(committer.get("date", ""))
    cache[sha] = date
    return date


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def build_inventory(
    *,
    token: str,
    owner: str,
    repo: str,
    cutoff_iso: str,
) -> dict[str, Any]:
    cutoff = parse_cutoff(cutoff_iso)
    branches = _list_remote_branches(token=token, owner=owner, repo=repo)
    open_prs = _list_open_pull_requests(token=token, owner=owner, repo=repo)
    pr_by_head: dict[str, dict[str, Any]] = {}
    for pr in open_prs:
        head = pr.get("head")
        if isinstance(head, dict):
            ref = head.get("ref")
            if isinstance(ref, str):
                pr_by_head[ref] = pr

    commit_cache: dict[str, str] = {}
    records: list[BranchRecord] = []
    for branch in branches:
        name = str(branch.get("name", ""))
        commit = branch.get("commit")
        sha = ""
        if isinstance(commit, dict):
            sha = str(commit.get("sha", ""))
        if not name or not sha:
            continue
        committed_at = _commit_date(
            token=token,
            owner=owner,
            repo=repo,
            sha=sha,
            cache=commit_cache,
        )
        pr = pr_by_head.get(name)
        labels: tuple[str, ...] = ()
        open_pr_number: int | None = None
        open_pr_state: str | None = None
        open_pr_draft: bool | None = None
        open_pr_created_at: str | None = None
        if pr is not None:
            open_pr_number = int(pr["number"])
            open_pr_state = str(pr.get("state", ""))
            open_pr_draft = bool(pr.get("draft", False))
            open_pr_created_at = str(pr.get("created_at", ""))
            label_rows = pr.get("labels")
            if isinstance(label_rows, list):
                labels = tuple(
                    str(row.get("name"))
                    for row in label_rows
                    if isinstance(row, dict) and row.get("name")
                )
        records.append(
            build_branch_record(
                name=name,
                sha=sha,
                committed_at=committed_at,
                cutoff=cutoff,
                open_pr_number=open_pr_number,
                open_pr_state=open_pr_state,
                open_pr_draft=open_pr_draft,
                open_pr_created_at=open_pr_created_at,
                open_pr_labels=labels,
            )
        )

    records.sort(key=lambda row: (row.category, row.name))
    category_counts = Counter(record.category for record in records)
    generated_at = datetime.now(tz=UTC).isoformat()
    phase1_targets = [row.name for row in records if row.phase1_garbage]
    phase2_targets = [
        {
            "branch": row.name,
            "pr_number": row.open_pr_number,
            "created_at": row.open_pr_created_at,
            "labels": list(row.open_pr_labels),
        }
        for row in records
        if row.phase2_stale_draft and row.open_pr_number is not None
    ]
    return {
        "generated_at": generated_at,
        "owner": owner,
        "repo": repo,
        "cutoff_iso": cutoff_iso,
        "summary": {
            "total_branches": len(records),
            "protected_branches": sum(1 for row in records if row.protected),
            "phase1_garbage_targets": len(phase1_targets),
            "phase2_stale_draft_targets": len(phase2_targets),
            "categories": {
                category: category_counts.get(category, 0) for category in CATEGORY_ORDER
            },
        },
        "phase1_garbage_targets": phase1_targets,
        "phase2_stale_draft_targets": phase2_targets,
        "branches": [asdict(row) for row in records],
    }


def _delete_remote_branch(*, token: str, owner: str, repo: str, branch: str) -> None:
    encoded = urllib.parse.quote(branch, safe="")
    url = f"{API_BASE}/repos/{owner}/{repo}/git/refs/heads/{encoded}"
    _github_request(
        method="DELETE",
        url=url,
        token=token,
        accept_status=frozenset({204}),
    )


def _close_pull_request(
    *,
    token: str,
    owner: str,
    repo: str,
    pr_number: int,
    apply: bool,
) -> None:
    url = f"{API_BASE}/repos/{owner}/{repo}/pulls/{pr_number}"
    if not apply:
        print(f"[PLAN] PATCH {url} state=closed")
        return
    _github_request(
        method="PATCH",
        url=url,
        token=token,
        payload={"state": "closed"},
    )
    comment_url = f"{API_BASE}/repos/{owner}/{repo}/issues/{pr_number}/comments"
    _github_request(
        method="POST",
        url=comment_url,
        token=token,
        payload={"body": PHASE2_CLOSE_COMMENT},
    )


def apply_phases(
    *,
    token: str,
    owner: str,
    repo: str,
    cutoff_iso: str,
    phases: set[int],
    apply: bool,
    inventory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = inventory or build_inventory(
        token=token,
        owner=owner,
        repo=repo,
        cutoff_iso=cutoff_iso,
    )
    actions: list[dict[str, Any]] = []

    if 1 in phases:
        for branch in payload.get("phase1_garbage_targets", []):
            if not isinstance(branch, str) or is_protected_branch(branch):
                continue
            action = {"phase": 1, "action": "delete_remote_branch", "branch": branch}
            if apply:
                try:
                    _delete_remote_branch(token=token, owner=owner, repo=repo, branch=branch)
                    action["status"] = "done"
                except RuntimeError as exc:
                    action["status"] = "failed"
                    action["error"] = str(exc)
            else:
                action["status"] = "planned"
            actions.append(action)
            print(f"[{action['status'].upper()}] phase1 delete origin/{branch}")

    if 2 in phases:
        for target in payload.get("phase2_stale_draft_targets", []):
            if not isinstance(target, dict):
                continue
            branch = str(target.get("branch", ""))
            pr_number = target.get("pr_number")
            if not branch or not isinstance(pr_number, int):
                continue
            if is_protected_branch(branch):
                continue
            close_action = {
                "phase": 2,
                "action": "close_pull_request",
                "branch": branch,
                "pr_number": pr_number,
            }
            if apply:
                try:
                    _close_pull_request(
                        token=token,
                        owner=owner,
                        repo=repo,
                        pr_number=pr_number,
                        apply=True,
                    )
                    close_action["status"] = "done"
                except RuntimeError as exc:
                    close_action["status"] = "failed"
                    close_action["error"] = str(exc)
            else:
                close_action["status"] = "planned"
            actions.append(close_action)
            print(
                f"[{close_action['status'].upper()}] phase2 close PR #{pr_number} ({branch})"
            )

            delete_action = {
                "phase": 2,
                "action": "delete_remote_branch",
                "branch": branch,
                "pr_number": pr_number,
            }
            if apply and close_action.get("status") == "done":
                try:
                    _delete_remote_branch(
                        token=token, owner=owner, repo=repo, branch=branch
                    )
                    delete_action["status"] = "done"
                except RuntimeError as exc:
                    delete_action["status"] = "failed"
                    delete_action["error"] = str(exc)
            elif apply:
                delete_action["status"] = "skipped"
                delete_action["error"] = "PR close failed"
            else:
                delete_action["status"] = "planned"
            actions.append(delete_action)
            print(
                f"[{delete_action['status'].upper()}] phase2 delete origin/{branch}"
            )

    return {
        "mode": "apply" if apply else "dry-run",
        "phases": sorted(phases),
        "actions": actions,
        "summary": {
            "total_actions": len(actions),
            "done": sum(1 for row in actions if row.get("status") == "done"),
            "planned": sum(1 for row in actions if row.get("status") == "planned"),
            "failed": sum(1 for row in actions if row.get("status") == "failed"),
            "skipped": sum(1 for row in actions if row.get("status") == "skipped"),
        },
    }


def _default_inventory_path() -> Path:
    stamp = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    return _repo_root() / "reports" / "quality" / f"branch-cleanup-inventory-{stamp}.json"


def _parse_phases(raw: str) -> set[int]:
    phases: set[int] = set()
    for part in raw.split(","):
        piece = part.strip()
        if not piece:
            continue
        value = int(piece)
        if value not in {1, 2}:
            raise ValueError("Only phases 1 and 2 are supported by this command")
        phases.add(value)
    if not phases:
        raise ValueError("At least one phase must be provided")
    return phases


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory = subparsers.add_parser("inventory", help="Generate branch cleanup inventory")
    inventory.add_argument("--owner", default=DEFAULT_OWNER)
    inventory.add_argument("--repo", default=DEFAULT_REPO)
    inventory.add_argument("--cutoff-iso", default=DEFAULT_CUTOFF_ISO)
    inventory.add_argument("--output", type=Path, default=None)

    apply_cmd = subparsers.add_parser("apply", help="Apply cleanup phases 1-2")
    apply_cmd.add_argument("--owner", default=DEFAULT_OWNER)
    apply_cmd.add_argument("--repo", default=DEFAULT_REPO)
    apply_cmd.add_argument("--cutoff-iso", default=DEFAULT_CUTOFF_ISO)
    apply_cmd.add_argument("--phases", default="1,2")
    apply_cmd.add_argument("--inventory", type=Path, default=None)
    apply_cmd.add_argument("--apply", action="store_true")
    apply_cmd.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Optional JSON report path for apply actions",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    token = _load_token()

    if args.command == "inventory":
        payload = build_inventory(
            token=token,
            owner=args.owner,
            repo=args.repo,
            cutoff_iso=args.cutoff_iso,
        )
        output = args.output or _default_inventory_path()
        _atomic_write_json(output, payload)
        print(f"[DONE] inventory written to {output}")
        print(json.dumps(payload["summary"], indent=2, sort_keys=True))
        return 0

    if args.command == "apply":
        inventory_payload: dict[str, Any] | None = None
        if args.inventory is not None:
            inventory_payload = json.loads(args.inventory.read_text(encoding="utf-8"))
        phases = _parse_phases(args.phases)
        result = apply_phases(
            token=token,
            owner=args.owner,
            repo=args.repo,
            cutoff_iso=args.cutoff_iso,
            phases=phases,
            apply=args.apply,
            inventory=inventory_payload,
        )
        if args.report is not None:
            _atomic_write_json(args.report, result)
            print(f"[DONE] apply report written to {args.report}")
        print(json.dumps(result["summary"], indent=2, sort_keys=True))
        return 0 if result["summary"]["failed"] == 0 else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
