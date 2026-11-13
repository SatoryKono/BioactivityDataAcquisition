#!/usr/bin/env python3
"""Branch and worktree hygiene: classify local state and apply safe cleanup.

Two phases, dry-run friendly:

    classify
        Scan worktrees, on-disk orphans, root clutter, and local branches.
        Bucket everything into safe-to-act classes (see Runbook
        docs/05-operations/runbooks/branch-hygiene-wave.md) and write
        ``classification.json`` plus a human table into ``--out``.

    apply
        Execute the safe classes from a fresh classification:
        detached/gone worktrees (with WIP archive when dirty), orphan and
        root-clutter quarantine, trash hard-delete older than 7 days, and
        branch deletion with a bundle backup of every removed tip.

Safety invariants:
    * locked worktrees, the main checkout, dirty-without-archive trees,
      checked-out branches, open-PR branches, and fresh tips are never touched;
    * every branch tip is bundled before deletion;
    * every removed worktree dirt is archived to ``wip-archive/`` first;
    * ``apply`` defaults to a preview and always re-classifies before --execute;
    * Git dirty/lock protections stay enabled even after a WIP archive is saved.

Usage:
    python scripts/engineering/repo/branch_hygiene.py classify
    python scripts/engineering/repo/branch_hygiene.py classify --out reports/local/hygiene-x
    python scripts/engineering/repo/branch_hygiene.py apply --out reports/local/hygiene-x
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.engineering.repo._branch_cleanup_policy import is_protected_branch

REPO = Path(__file__).resolve().parents[3]
WT_ROOT = REPO.parent / f"{REPO.name}-worktrees"
ROOT = REPO.parent
GOVERNED_WORKSPACE_ROOT = Path("D:/github")
DAY = 86400.0
STALE_HOURS = 12
SAFE_DIR_ARG = "safe.directory=*"
CLASSIFICATION_FILE = "classification.json"
TRASH_TTL_DAYS = 7
EXCLUDE_NAMES = (".env", ".env.local", ".env.example")
EXCLUDE_PARTS = (".venv", ".venv-win", "node_modules", "__pycache__")
ROOT_CLUTTER_PREFIXES = (f"{REPO.name}-", "codex-")


def _now() -> float:
    return time.time()


def stamp() -> str:
    return datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")


def run(
    args: list[str],
    cwd: Path | None = None,
    timeout: int = 600,
    *,
    binary: bool = False,
) -> subprocess.CompletedProcess:
    if not args or args[0] not in {"git", "gh"}:
        raise RuntimeError("Only fixed Git and GitHub CLI executables are permitted")
    command = ["git", *args[1:]] if args[0] == "git" else ["gh", *args[1:]]
    environment = os.environ.copy()
    for key in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_COMMON_DIR",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_PREFIX",
    ):
        environment.pop(key, None)
    return subprocess.run(
        command,
        shell=False,
        cwd=cwd or REPO,
        capture_output=True,
        text=not binary,
        encoding=None if binary else "utf-8",
        env=environment,
        timeout=timeout,
    )


def git(*args: str) -> str:
    r = run(["git", *args])
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def registered_worktrees() -> list[dict[str, Any]]:
    raw = git("worktree", "list", "--porcelain")
    rows: list[dict[str, Any]] = []
    cur: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            if cur:
                rows.append(cur)
            cur = {}
            continue
        key, _, val = line.partition(" ")
        cur[key] = val
    if cur:
        rows.append(cur)
    out = []
    for r in rows:
        branch_ref = r.get("branch", "")
        out.append(
            {
                "path": r["worktree"],
                "head": r.get("HEAD", ""),
                "branch": branch_ref.removeprefix("refs/heads/") or None,
                "detached": "detached" in r,
                "locked": (r.get("locked") or "locked") if "locked" in r else None,
                "prunable": "prunable" in r,
            }
        )
    return out


def status_counts(path: Path) -> tuple[bool, bool, bool] | None:
    """Return (tracked_dirty, untracked_present, ok)."""
    try:
        r = run(
            ["git", "-c", SAFE_DIR_ARG, "status", "--porcelain"],
            cwd=path,
            timeout=180,
        )
        if r.returncode != 0:
            return None
        lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
        untracked = any(ln.startswith("??") for ln in lines)
        tracked = any(not ln.startswith("??") for ln in lines)
        return tracked, untracked, True
    except (subprocess.TimeoutExpired, OSError):
        return None


def local_branches() -> list[dict[str, Any]]:
    fmt = "%(refname:short)|%(objectname)|%(upstream:short)|%(upstream:track)|%(committerdate:unix)"
    out = []
    for line in git("branch", "--format", fmt).splitlines():
        name, sha, upstream, track, cdate = line.split("|")
        out.append(
            {
                "name": name.strip(),
                "sha": sha.strip(),
                "upstream": upstream.strip(),
                "gone": "gone" in track,
                "tip_ctime": int(cdate),
            }
        )
    return out


def pr_state_map() -> dict[str, list[str]]:
    r = run(
        [
            "gh",
            "pr",
            "list",
            "--state",
            "all",
            "--limit",
            "1000",
            "--json",
            "number,state,headRefName",
        ],
        timeout=300,
    )
    if r.returncode != 0:
        raise RuntimeError("Cannot classify safely: GitHub PR lookup failed")
    m: dict[str, list[str]] = {}
    for row in json.loads(r.stdout):
        m.setdefault(row["headRefName"], []).append(row["state"])
    return m


def cherry_unique(sha_or_name: str) -> int | None:
    r = run(["git", "cherry", "main", sha_or_name], timeout=180)
    if r.returncode != 0:
        return None
    return sum(1 for ln in r.stdout.splitlines() if ln.startswith("+"))


def _worktree_action(
    w: dict[str, Any],
    branches: list[dict[str, Any]],
    exists: bool,
    status: tuple[bool, bool, bool] | None,
    age: float,
    detached_days: float,
    branch_days: float,
) -> tuple[str, str]:
    if Path(w["path"]).resolve() == REPO.resolve():
        return "KEEP", "main checkout"
    if w["locked"]:
        return "KEEP_LOCKED", f"locked: {w['locked']}"
    if not exists:
        return "REMOVE", "directory missing"
    if status is None:
        return "KEEP", "status unavailable"
    dirty = status[0] or status[1]
    removal = "REMOVE_ARCHIVE" if dirty else "REMOVE"
    if w["detached"] and age > detached_days:
        return removal, f"detached, idle {age}d"
    branch = next((item for item in branches if item["name"] == w["branch"]), None)
    if branch and branch["gone"] and age > branch_days:
        return removal, f"branch upstream gone, idle {age}d"
    return "KEEP", "fresh or active branch"


def _classify_worktree(
    w: dict[str, Any],
    branches: list[dict[str, Any]],
    detached_days: float,
    branch_days: float,
) -> dict[str, Any]:
    path = Path(w["path"])
    try:
        commit_ts = (
            int(git("log", "-1", "--format=%ct", w["head"]).strip()) if w["head"] else 0
        )
    except (RuntimeError, ValueError):
        commit_ts = 0
    try:
        modified = int(os.stat(path).st_mtime)
    except OSError:
        modified = 0
    age = round((_now() - max(commit_ts, modified)) / DAY, 1)
    exists = path.exists()
    status = status_counts(path) if exists else None
    if status and (status[0] or status[1]):
        age = min(age, round((_now() - _latest_activity(path)) / DAY, 1))
    action, reason = _worktree_action(
        w, branches, exists, status, age, detached_days, branch_days
    )
    return {
        **w,
        "age_days": age,
        "tracked_dirty": bool(status and status[0]),
        "untracked": bool(status and status[1]),
        "exists": exists,
        "action": action,
        "reason": reason,
    }


def _latest_activity(path: Path) -> float:
    """Keep trees when activity cannot be safely excluded; never read file contents."""
    latest = 0.0
    try:
        for base, directories, files in os.walk(path, followlinks=False):
            directories[:] = [
                name
                for name in directories
                if name not in EXCLUDE_PARTS and name != ".git"
            ]
            for name in directories + files:
                item = Path(base) / name
                if name.startswith(".env") or item.is_symlink() or item.is_junction():
                    return _now()
                latest = max(latest, item.stat().st_mtime)
    except OSError:
        return _now()
    return latest


def classify_worktrees(
    wts: list[dict[str, Any]],
    brs: list[dict[str, Any]],
    detached_days: float,
    branch_days: float,
) -> list[dict[str, Any]]:
    return [_classify_worktree(w, brs, detached_days, branch_days) for w in wts]


def _orphan_row(
    entry: Path, base: Path, registered: set[str], trash: Path
) -> dict[str, Any] | None:
    if entry in (WT_ROOT, REPO) or str(entry).replace("\\", "/") in registered:
        return None
    is_trash = ".__trash_" in entry.name
    if base == ROOT and (not entry.name.startswith(ROOT_CLUTTER_PREFIXES) or is_trash):
        return None
    action = "HARD_DELETE" if is_trash and trash_date(entry.name) else "QUARANTINE"
    return {
        "path": str(entry).replace("\\", "/"),
        "kind": "trash-old" if is_trash else "orphan",
        "action": action,
        "quarantine": str(trash / entry.name) if action == "QUARANTINE" else None,
    }


def classify_orphans(wts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    registered = {w["path"].replace("\\", "/") for w in wts}
    trash = WT_ROOT / f".__trash_{datetime.now(tz=UTC):%Y%m%d}"
    rows = []
    for base in (WT_ROOT, ROOT):
        if not base.exists():
            continue
        for entry in sorted(base.iterdir()):
            row = _orphan_row(entry, base, registered, trash)
            if row is not None:
                rows.append(row)
    return rows


def _branch_bucket(
    branch: dict[str, Any], states: list[str], age: float, branch_days: float
) -> tuple[str, dict[str, Any]]:
    if "OPEN" in states:
        return "E", {"pr_states": states}
    if age <= branch_days:
        return "E", {"pr_states": states}
    if branch["upstream"] and not branch["gone"]:
        bucket = "A" if any(state in ("MERGED", "CLOSED") for state in states) else "E"
        return bucket, {"pr_states": states}
    if branch["gone"]:
        return ("A" if age > branch_days else "E"), {}
    unique = cherry_unique(f"refs/heads/{branch['name']}")
    if unique == 0:
        return "B", {}
    extra = {"unique_commits": unique}
    if age > branch_days and unique is not None:
        extra["delete_ok"] = True
    return "C", extra


def classify_branches(
    brs: list[dict[str, Any]],
    wts: list[dict[str, Any]],
    current: str,
    branch_days: float,
) -> dict[str, list[dict[str, Any]]]:
    now = _now()
    checked_out = {w["branch"] for w in wts if w["branch"]}
    pr_map = pr_state_map()
    buckets: dict[str, list[dict[str, Any]]] = {k: [] for k in "ABCDE"}
    for b in brs:
        age = round((now - b["tip_ctime"]) / DAY, 1)
        entry: dict[str, Any] = {
            "name": b["name"],
            "sha": b["sha"],
            "age_days": age,
            "upstream": b["upstream"],
        }
        if (
            is_protected_branch(b["name"])
            or b["name"] == current
            or b["name"] in checked_out
        ):
            buckets["D"].append(entry)
            continue
        states = pr_map.get(b["name"], [])
        bucket, extra = _branch_bucket(b, states, age, branch_days)
        buckets[bucket].append({**entry, **extra})
    return buckets


def do_classify(args: argparse.Namespace) -> int:
    _classify_impl(args)
    return 0


def _classify_impl(args: argparse.Namespace) -> Path:
    out = _report_directory(args.out)
    out.mkdir(parents=True, exist_ok=True)
    wts = registered_worktrees()
    brs = local_branches()
    current = git("rev-parse", "--abbrev-ref", "HEAD").strip()
    wt_rows = classify_worktrees(wts, brs, args.detached_days, args.branch_days)
    orphan_rows = classify_orphans(wts)
    buckets = classify_branches(brs, wts, current, args.branch_days)
    payload = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "cutoffs": {
            "detached_days": args.detached_days,
            "branch_days": args.branch_days,
        },
        "worktrees": wt_rows,
        "orphans": orphan_rows,
        "branches": buckets,
        "summary": {
            "worktrees": {
                a: sum(1 for r in wt_rows if r["action"] == a)
                for a in {r["action"] for r in wt_rows}
            },
            "orphans": {
                a: sum(1 for r in orphan_rows if r["action"] == a)
                for a in {r["action"] for r in orphan_rows}
            },
            "branches": {k: len(v) for k, v in buckets.items()},
        },
    }
    (out / CLASSIFICATION_FILE).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"[classify] -> {out}")
    print(json.dumps(payload["summary"], indent=1, ensure_ascii=False))
    return out


def excluded(rel: str) -> bool:
    parts = Path(rel).parts
    name = parts[-1] if parts else rel
    if name in EXCLUDE_NAMES or name.startswith(".env"):
        return True
    return any(p in EXCLUDE_PARTS for p in parts)


def _copy_archive_file(src: str, dst: str) -> str:
    source = Path(src)
    if source.is_symlink() or excluded(str(source)):
        raise RuntimeError(f"Excluded or linked archive input: {source}")
    return shutil.copy2(src, dst)


def archive_tree(path: Path, name: str, head: str, archive: Path) -> dict[str, Any]:
    """Create a complete archive or raise before permitting removal."""
    for selection in ([], ["--cached"]):
        changed = run(
            ["git", "-C", str(path), "diff", *selection, "--name-only", "-z", "HEAD"]
        )
        if changed.returncode:
            raise RuntimeError("Cannot read complete worktree changes")
        if any(excluded(name) for name in changed.stdout.split("\0") if name):
            raise RuntimeError("Cannot archive excluded tracked inputs")
    archive.mkdir(parents=True, exist_ok=True)
    snapshot = Path(tempfile.mkdtemp(prefix=f"{name}-", dir=archive))
    for label, selection in (("working", []), ("index", ["--cached"])):
        diff = run(
            ["git", "-C", str(path), "diff", *selection, "--binary", "HEAD"],
            binary=True,
        )
        if diff.returncode:
            raise RuntimeError("Cannot read complete worktree changes")
        (snapshot / f"{label}.patch").write_bytes(diff.stdout)
    status = run(
        ["git", "-C", str(path), "ls-files", "--others", "--exclude-standard", "-z"]
    )
    if status.returncode:
        raise RuntimeError("Cannot read complete worktree changes")
    copied = 0
    for rel in filter(None, status.stdout.split("\0")):
        source = path / rel
        if excluded(rel) or source.is_symlink():
            raise RuntimeError(f"Cannot preserve excluded or linked input: {rel}")
        destination = snapshot / "untracked" / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        _copy_archive_file(str(source), str(destination))
        copied += 1
    (snapshot / "head.txt").write_text(f"{head} {name}\n", encoding="utf-8")
    return {
        "archive": str(snapshot),
        "untracked_copied": copied,
        "complete": True,
    }


def trash_date(name: str) -> str | None:
    marker = ".__trash_"
    if marker not in name:
        return None
    tail = name.split(marker, 1)[1]
    token = tail[:8]
    if len(token) != 8 or not token.isdigit():
        return None
    try:
        datetime.strptime(token, "%Y%m%d")
    except ValueError:
        return None
    return token


def _lexically_confined(path: Path, root: Path, *, allow_root: bool = False) -> Path:
    """Reject outside locations before querying the caller-supplied filesystem path."""
    candidate = Path(os.path.abspath(path))
    base = Path(os.path.abspath(root))
    if not candidate.is_relative_to(base) or (candidate == base and not allow_root):
        raise RuntimeError("Refusing target outside governed workspace")
    if any(part.startswith(".env") for part in candidate.relative_to(base).parts):
        raise RuntimeError("Refusing env or linked tree input")
    return candidate


def _safe_tree_target(path: Path, *, must_exist: bool = True) -> Path:
    configured_root = Path(os.path.abspath(GOVERNED_WORKSPACE_ROOT))
    candidate = _lexically_confined(path, configured_root)
    allowed = configured_root.resolve()
    if allowed != configured_root:
        raise RuntimeError("Governed workspace root was redirected")
    target = candidate.resolve(strict=must_exist)
    if not target.is_relative_to(allowed) or target == allowed:
        raise RuntimeError("Refusing target outside governed workspace")
    if candidate.is_symlink() or candidate.is_junction():
        raise RuntimeError("Refusing linked target")
    for base, directories, files in os.walk(target, followlinks=False):
        for name in directories + files:
            item = Path(base) / name
            if name.startswith(".env") or item.is_symlink() or item.is_junction():
                raise RuntimeError(f"Refusing env or linked tree input: {item}")
    return target


def _report_directory(value: Path | None) -> Path:
    root = REPO / "reports" / "local"
    if root.resolve(strict=False) != Path(os.path.abspath(root)):
        raise RuntimeError("Owned reports root was redirected")
    proposed = value if value is not None else root / f"branch-hygiene-{stamp()}"
    candidate = _lexically_confined(proposed, root)
    resolved = candidate.resolve(strict=False)
    if not resolved.is_relative_to(root.resolve(strict=False)):
        raise RuntimeError("Report directory escapes owned reports root")
    return resolved


def _bundle_worktree_head(path: Path, archive: Path) -> Path:
    archive.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix="head-", dir=archive)) / "history.bundle"
    commands = (
        ["git", "-C", str(path), "bundle", "create", str(backup), "HEAD"],
        ["git", "-C", str(path), "bundle", "verify", str(backup)],
    )
    for command in commands:
        if run(command, timeout=1800).returncode:
            raise RuntimeError("Cannot preserve complete worktree HEAD history")
    return backup


def _apply_worktree(
    row: dict[str, Any],
    archive: Path,
    args: argparse.Namespace,
    actions: list[dict[str, Any]],
) -> None:
    path = Path(row["path"])
    entry: dict[str, Any] = {
        "kind": "worktree",
        "path": str(path),
        "action": row["action"],
        "head": row["head"],
    }
    current = classify_worktrees(
        registered_worktrees(),
        local_branches(),
        args.detached_days,
        args.branch_days,
    )
    fresh = next(
        (candidate for candidate in current if candidate["path"] == row["path"]),
        None,
    )
    if fresh != row:
        entry["result"] = "kept: worktree state changed"
        actions.append(entry)
        return
    try:
        path = _safe_tree_target(path, must_exist=False)
        if path.exists():
            entry["head_bundle"] = str(_bundle_worktree_head(path, archive))
        if row["action"] == "REMOVE_ARCHIVE" and path.exists():
            entry["wip"] = archive_tree(path, path.name, row["head"], archive)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        entry["wip_error"] = str(exc)
        actions.append(entry)
        return
    rm = run(["git", "worktree", "remove", str(path)])
    entry["remove_rc"] = rm.returncode
    if rm.returncode != 0:
        entry["remove_err"] = (rm.stderr or "").strip()[:300]
    actions.append(entry)
    print(f"[{'OK' if rm.returncode == 0 else 'FAIL'}] worktree {path.name}")


def _delete_trash(src: Path) -> str:
    date = trash_date(src.name)
    if date is None:
        return "kept: unknown quarantine date"
    created = datetime.strptime(date, "%Y%m%d").replace(tzinfo=UTC).timestamp()
    age = (_now() - max(created, src.stat().st_mtime)) / DAY
    if age < TRASH_TTL_DAYS:
        return f"kept (trash {age:.1f}d < {TRASH_TTL_DAYS}d)"
    shutil.rmtree(src)
    return "hard_deleted"


def _safe_quarantine_destination(destination: Path) -> Path:
    candidate = _lexically_confined(destination, WT_ROOT)
    configured = Path(os.path.abspath(WT_ROOT))
    root = WT_ROOT.resolve()
    governed = Path(os.path.abspath(GOVERNED_WORKSPACE_ROOT))
    if (
        root != configured
        or governed.resolve() != governed
        or not root.is_relative_to(governed)
    ):
        raise RuntimeError(
            "Quarantine root was redirected or outside governed workspace"
        )
    resolved = candidate.resolve(strict=False)
    if resolved == root or not resolved.is_relative_to(root):
        raise RuntimeError("Quarantine destination escapes governed worktree root")
    if resolved.exists():
        raise RuntimeError("Quarantine destination already exists")
    return resolved


def _apply_orphan(row: dict[str, Any]) -> dict[str, Any]:
    src = Path(row["path"])
    entry = {"kind": row["kind"], "path": str(src), "action": row["action"]}
    try:
        src = _safe_tree_target(src)
        if row["action"] == "HARD_DELETE":
            entry["result"] = _delete_trash(src)
        else:
            dst = _safe_quarantine_destination(Path(row["quarantine"]))
            dst.parent.mkdir(parents=True, exist_ok=True)
            os.rename(src, dst)
            entry["result"] = f"quarantined -> {dst}"
    except (OSError, RuntimeError) as exc:
        entry["result"] = f"kept: {exc}"
    return entry


def _deletion_candidates(
    buckets: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    return (
        buckets["A"]
        + buckets["B"]
        + [item for item in buckets["C"] if item.get("delete_ok")]
    )


def _delete_one_branch(
    candidate: dict[str, Any], args: argparse.Namespace
) -> dict[str, Any]:
    fresh = classify_branches(
        local_branches(),
        registered_worktrees(),
        git("rev-parse", "--abbrev-ref", "HEAD").strip(),
        args.branch_days,
    )
    entry = {"kind": "branch", "name": candidate["name"]}
    permitted = any(
        item["name"] == candidate["name"] and item["sha"] == candidate["sha"]
        for item in _deletion_candidates(fresh)
    )
    if not permitted:
        return {**entry, "result": "kept: state changed"}
    result = run(["git", "branch", "-D", "--", candidate["name"]])
    return {**entry, "rc": result.returncode, "error": result.stderr.strip()[:120]}


def _bundle_and_delete(
    candidates: list[dict[str, Any]],
    out: Path,
    args: argparse.Namespace,
    actions: list[dict[str, Any]],
) -> tuple[int, str | None]:
    if not candidates:
        return 0, None
    backup = (
        Path(tempfile.mkdtemp(prefix="branches-backup-", dir=out)) / "history.bundle"
    )
    refs = [f"refs/heads/{item['name']}" for item in candidates]
    result = run(["git", "bundle", "create", str(backup), *refs], timeout=1800)
    if result.returncode:
        print(f"[FATAL] bundle failed: {result.stderr}")
        return 1, None
    for item in candidates:
        actions.append(_delete_one_branch(item, args))
    return 0, str(backup)


def _action_succeeded(action: dict[str, Any]) -> bool:
    return (
        action.get("remove_rc") == 0
        or action.get("rc") == 0
        or "quarantined" in str(action.get("result"))
        or action.get("result") == "hard_deleted"
    )


def do_apply(args: argparse.Namespace) -> int:
    if not args.execute:
        print("[dry-run] no trees or branches changed; pass --execute to apply")
        return 0
    out = _classify_impl(args)
    cls = json.loads((out / CLASSIFICATION_FILE).read_text(encoding="utf-8"))
    archive = out / "wip-archive"
    actions: list[dict[str, Any]] = []

    rc, backup, error = 1, None, None
    try:
        for row in cls["worktrees"]:
            if row["action"] in ("REMOVE", "REMOVE_ARCHIVE"):
                _apply_worktree(row, archive, args, actions)
        for row in cls["orphans"]:
            actions.append(_apply_orphan(row))
        rc, backup = _bundle_and_delete(
            _deletion_candidates(cls["branches"]), out, args, actions
        )
        if rc:
            error = "branch bundle failed; remaining actions stopped"
        else:
            result = run(["git", "worktree", "prune"])
            rc = int(result.returncode != 0)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        rc, error = 1, str(exc)
    finally:
        journal = (
            json.dumps(
                {
                    "finished_at": datetime.now(tz=UTC).isoformat(),
                    "bundle": str(backup) if backup else None,
                    "actions": actions,
                    "returncode": rc,
                    "error": error,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )
        snapshot = Path(tempfile.mkdtemp(prefix="apply-", dir=out))
        (snapshot / "apply-actions.json").write_text(journal, encoding="utf-8")
        (out / "apply-actions.json").write_text(journal, encoding="utf-8")
    if rc:
        return rc

    ok = sum(_action_succeeded(action) for action in actions)
    print(f"[apply] done: {len(actions)} actions, ok {ok}")
    print(
        f"[apply] worktrees now {len(registered_worktrees())}, branches now {len(local_branches())}"
    )
    failed = any(
        "wip_error" in action
        or str(action.get("result", "")).startswith("kept: ")
        or action.get("remove_rc", 0) != 0
        or action.get("rc", 0) != 0
        for action in actions
    )
    return int(failed)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("classify", "apply"):
        s = sub.add_parser(name)
        s.add_argument(
            "--execute", action="store_true", help="Explicitly permit apply mutations"
        )
        s.add_argument("--out", type=Path, default=None)
        s.add_argument("--detached-days", type=float, default=2.0)
        s.add_argument("--branch-days", type=float, default=3.0)
        s.set_defaults(func=do_classify if name == "classify" else do_apply)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "out", None) is None and args.command == "apply":
        raise SystemExit("apply requires --out pointing at a classification dir")
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
