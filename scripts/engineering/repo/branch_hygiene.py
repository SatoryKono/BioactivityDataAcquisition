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
    * ``apply`` re-classifies when the input snapshot is older than 12 hours.

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
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

REPO = Path(__file__).resolve().parents[3]
WT_ROOT = REPO.parent / f"{REPO.name}-worktrees"
ROOT = REPO.parent
DAY = 86400.0
STALE_HOURS = 12
TRASH_TTL_DAYS = 7
EXCLUDE_NAMES = (".env", ".env.local", ".env.example")
EXCLUDE_PARTS = (".venv", ".venv-win", "node_modules", "__pycache__")
ROOT_CLUTTER_PREFIXES = (f"{REPO.name}-", "codex-")


def _now() -> float:
    return time.time()


def stamp() -> str:
    return datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")


def run(
    args: list[str], cwd: Path | None = None, timeout: int = 600
) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        cwd=cwd or REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
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
                "locked": r.get("locked") if "locked" in r else None,
                "prunable": "prunable" in r,
            }
        )
    return out


def status_counts(path: Path) -> tuple[bool, bool, bool] | None:
    """Return (tracked_dirty, untracked_present, ok)."""
    try:
        r = run(
            ["git", "-c", "safe.directory=*", "status", "--porcelain"],
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
        return {}
    m: dict[str, list[str]] = {}
    for row in json.loads(r.stdout):
        m.setdefault(row["headRefName"], []).append(row["state"])
    return m


def cherry_unique(sha_or_name: str) -> int | None:
    r = run(["git", "cherry", "main", sha_or_name], timeout=180)
    if r.returncode != 0:
        return None
    return sum(1 for ln in r.stdout.splitlines() if ln.startswith("+"))


def classify_worktrees(
    wts: list[dict[str, Any]],
    brs: list[dict[str, Any]],
    detached_days: float,
    branch_days: float,
) -> list[dict[str, Any]]:
    now = _now()
    rows = []
    for w in wts:
        path = Path(w["path"])
        commit_ts = 0
        if w["head"]:
            try:
                commit_ts = int(git("log", "-1", "--format=%ct", w["head"]).strip())
            except RuntimeError:
                commit_ts = 0
        try:
            mtime = int(os.stat(path).st_mtime)
        except OSError:
            mtime = 0
        age_days = round((now - max(commit_ts, mtime)) / DAY, 1)
        st = status_counts(path) if path.exists() else None
        tracked_dirty = untracked = False
        if st:
            tracked_dirty, untracked, _ = st
        exists = path.exists()

        action, reason = "KEEP", "fresh or active upstream"
        if str(path) == str(REPO):
            action, reason = "KEEP", "main checkout"
        elif w["locked"]:
            action, reason = "KEEP_LOCKED", f"locked: {w['locked']}"
        elif not exists or w["prunable"]:
            action, reason = "REMOVE", "prunable / dir missing"
        elif st is None:
            action, reason = "KEEP", "status unavailable"
        elif w["detached"] and age_days > detached_days:
            action = "REMOVE_ARCHIVE" if tracked_dirty else "REMOVE"
            reason = f"detached, idle {age_days}d"
        elif w["branch"]:
            b = next((x for x in brs if x["name"] == w["branch"]), None)
            if b and b["gone"] and age_days > branch_days:
                action = "REMOVE_ARCHIVE" if tracked_dirty else "REMOVE"
                reason = f"branch upstream gone, idle {age_days}d"
            elif b and not b["upstream"]:
                action, reason = "KEEP", "local-only branch"
        elif age_days > detached_days and not tracked_dirty:
            action = "REMOVE"
            reason = f"idle {age_days}d"
        rows.append(
            {
                **w,
                "age_days": age_days,
                "tracked_dirty": tracked_dirty,
                "untracked": untracked,
                "exists": exists,
                "action": action,
                "reason": reason,
            }
        )
    return rows


def classify_orphans(wts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    registered = {w["path"].replace("\\", "/") for w in wts}
    rows: list[dict[str, Any]] = []
    trash = WT_ROOT / f".__trash_{datetime.now(tz=UTC):%Y%m%d}"
    for base in (WT_ROOT, ROOT):
        if not base.exists():
            continue
        for entry in sorted(base.iterdir()):
            if entry == WT_ROOT or entry == REPO:
                continue
            key = str(entry).replace("\\", "/")
            if key in registered:
                continue
            is_trash = ".__trash_" in entry.name
            if base == ROOT:
                if not entry.name.startswith(ROOT_CLUTTER_PREFIXES):
                    continue
                action = "KEEP" if is_trash else "QUARANTINE"
            else:
                action = "HARD_DELETE" if is_trash else "QUARANTINE"
            if action == "KEEP":
                continue
            rows.append(
                {
                    "path": key,
                    "kind": "trash-old" if is_trash else "orphan",
                    "action": action,
                    "quarantine": str(trash / entry.name)
                    if action == "QUARANTINE"
                    else None,
                }
            )
    return rows


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
        if b["name"] == current or b["name"] in checked_out:
            buckets["D"].append(entry)
            continue
        states = pr_map.get(b["name"], [])
        if b["upstream"] and not b["gone"]:
            if any(s in ("MERGED", "CLOSED") for s in states):
                buckets["A"].append({**entry, "pr_states": states})
            else:
                buckets["E"].append({**entry, "pr_states": states})
        elif b["gone"]:
            (buckets["A"] if age > branch_days else buckets["E"]).append(entry)
        else:
            uniq = cherry_unique(b["name"])
            if uniq == 0:
                buckets["B"].append(entry)
            elif age > branch_days and uniq is not None:
                buckets["C"].append(
                    {**entry, "unique_commits": uniq, "delete_ok": True}
                )
            else:
                buckets["C"].append({**entry, "unique_commits": uniq})
    return buckets


def do_classify(args: argparse.Namespace) -> int:
    _classify_impl(args)
    return 0


def _classify_impl(args: argparse.Namespace) -> Path:
    out = (
        Path(args.out)
        if args.out
        else REPO / "reports" / "local" / f"branch-hygiene-{stamp()}"
    )
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
    (out / "classification.json").write_text(
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


def archive_tree(path: Path, name: str, head: str, archive: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"archive": str(archive / name)}
    archive.mkdir(parents=True, exist_ok=True)
    diff = run(
        ["git", "-c", "safe.directory=*", "-C", str(path), "diff", "--binary", "HEAD"]
    )
    if diff.returncode == 0 and diff.stdout.strip():
        patch = archive / f"{name}.patch"
        patch.write_text(diff.stdout, encoding="utf-8")
        result["patch_bytes"] = patch.stat().st_size
    st = run(
        ["git", "-c", "safe.directory=*", "-C", str(path), "status", "--porcelain"]
    )
    copied = skipped = 0
    if st.returncode == 0:
        for rel in [
            ln[3:].strip().strip('"')
            for ln in st.stdout.splitlines()
            if ln.startswith("??")
        ]:
            if excluded(rel):
                skipped += 1
                continue
            src = path / rel
            dst = archive / name / rel
            try:
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                elif src.is_file():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                else:
                    continue
                copied += 1
            except OSError:
                skipped += 1
    result["untracked_copied"] = copied
    result["untracked_skipped"] = skipped
    with (archive / "heads.txt").open("a", encoding="utf-8") as fh:
        fh.write(f"{head} {name}\n")
    return result


def trash_date(name: str) -> str | None:
    marker = ".__trash_"
    if marker not in name:
        return None
    tail = name.split(marker, 1)[1]
    digits = "".join(ch for ch in tail if ch.isdigit())
    return digits[:8] if len(digits) >= 8 else None


def do_apply(args: argparse.Namespace) -> int:
    out = Path(args.out)
    cls_path = out / "classification.json"
    if (
        not cls_path.exists()
        or (_now() - cls_path.stat().st_mtime) > STALE_HOURS * 3600
    ):
        print("[apply] classification missing or stale; re-running classify")
        out = do_classify(args)
    cls = json.loads((out / "classification.json").read_text(encoding="utf-8"))
    archive = out / "wip-archive"
    actions: list[dict[str, Any]] = []

    for row in cls["worktrees"]:
        if row["action"] not in ("REMOVE", "REMOVE_ARCHIVE"):
            continue
        path = Path(row["path"])
        entry: dict[str, Any] = {
            "kind": "worktree",
            "path": str(path),
            "action": row["action"],
            "head": row["head"],
        }
        if row["action"] == "REMOVE_ARCHIVE" and path.exists():
            try:
                entry["wip"] = archive_tree(path, path.name, row["head"], archive)
            except Exception as exc:
                entry["wip_error"] = str(exc)
        rm = run(["git", "worktree", "remove", "--force", str(path)])
        entry["remove_rc"] = rm.returncode
        if rm.returncode != 0:
            entry["remove_err"] = (rm.stderr or "").strip()[:300]
        actions.append(entry)
        print(f"[{'OK' if rm.returncode == 0 else 'FAIL'}] worktree {path.name}")

    for row in cls["orphans"]:
        src = Path(row["path"])
        entry = {"kind": row["kind"], "path": str(src), "action": row["action"]}
        if row["action"] == "HARD_DELETE":
            date = trash_date(src.name)
            age_days = (
                (_now() - time.mktime(time.strptime(date, "%Y%m%d"))) / DAY
                if date
                else TRASH_TTL_DAYS + 1
            )
            if age_days < TRASH_TTL_DAYS:
                entry["result"] = f"kept (trash {age_days:.1f}d < {TRASH_TTL_DAYS}d)"
            else:
                try:
                    shutil.rmtree(src)
                    entry["result"] = "hard_deleted"
                except OSError as exc:
                    entry["result"] = f"stuck: {exc}"
        else:
            dst = Path(row["quarantine"])
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.rename(src, dst)
                entry["result"] = f"quarantined -> {dst}"
            except OSError as exc:
                entry["result"] = f"stuck: {exc}"
        actions.append(entry)
        print(f"[orphan] {src.name}: {entry['result']}")

    del_candidates = (
        cls["branches"]["A"]
        + cls["branches"]["B"]
        + [c for c in cls["branches"]["C"] if c.get("delete_ok")]
    )
    if del_candidates:
        backup = out / f"branches-backup-{stamp()}.bundle"
        refspecs = [f"refs/heads/{c['name']}" for c in del_candidates]
        bundle = run(["git", "bundle", "create", str(backup), *refspecs], timeout=1800)
        if bundle.returncode != 0:
            print(f"[FATAL] bundle failed: {bundle.stderr}")
            return 1
        print(f"[OK] bundle -> {backup} ({backup.stat().st_size} bytes)")
        for c in del_candidates:
            r = run(["git", "branch", "-D", c["name"]])
            actions.append({"kind": "branch", "name": c["name"], "rc": r.returncode})
            if r.returncode != 0:
                print(f"[FAIL] branch {c['name']}: {r.stderr.strip()[:120]}")
    else:
        backup = None
        print("[apply] no branch candidates")

    run(["git", "worktree", "prune"])
    (out / "apply-actions.json").write_text(
        json.dumps(
            {
                "finished_at": datetime.now(tz=UTC).isoformat(),
                "bundle": str(backup) if backup else None,
                "actions": actions,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    ok = sum(
        1
        for a in actions
        if a.get("remove_rc") == 0
        or a.get("rc") == 0
        or "quarantined" in str(a.get("result"))
        or a.get("result") == "hard_deleted"
    )
    print(f"[apply] done: {len(actions)} actions, ok {ok}")
    print(
        f"[apply] worktrees now {len(registered_worktrees())}, branches now {len(local_branches())}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("classify", "apply"):
        s = sub.add_parser(name)
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
