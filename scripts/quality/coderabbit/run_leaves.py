"""Sequential CodeRabbit leaf runner for CR-FULL-20260806-full."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict, cast


class Leaf(TypedDict, total=False):
    id: str
    wave: str
    files: str
    dir: str
    use_file_list: str


class LeafResult(TypedDict, total=False):
    id: str
    status: str
    reason: str
    log: str
    exit_code: int
    elapsed_s: float
    bytes: int
    cmd: list[str]


class Progress(TypedDict, total=False):
    started: str
    updated: str
    results: dict[str, LeafResult]
    completed: list[str]
    failed: list[str]
    skipped: list[str]


OUT = Path("reports/quality/coderabbit/20260806-full")
MATRIX = OUT / "01-scope-matrix.json"
PROGRESS = OUT / "progress.json"
LOG_DIR = OUT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Prefer WSL path then local
CODERABBIT = os.environ.get("CODERABBIT_BIN", "coderabbit")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_progress() -> Progress:
    if PROGRESS.exists():
        return cast(Progress, json.loads(PROGRESS.read_text(encoding="utf-8")))
    return {"started": now(), "results": {}, "completed": [], "failed": [], "skipped": []}


def save_progress(p: Progress) -> None:
    p["updated"] = now()
    PROGRESS.write_text(json.dumps(p, indent=2, ensure_ascii=False), encoding="utf-8")


def run_leaf(leaf: Leaf, base: str = "main") -> LeafResult:
    lid = leaf["id"]
    log_path = LOG_DIR / f"review_{lid}.log"
    cmd: list[str]
    env = os.environ.copy()
    # Prefer local WSL/Linux coderabbit install when present
    env["PATH"] = f"/home/fedor/.local/bin:{env.get('PATH', '')}"
    env["NO_COLOR"] = "1"
    env["TERM"] = "dumb"

    if leaf.get("dir"):
        cmd = [
            CODERABBIT,
            "review",
            "--base",
            base,
            "--dir",
            leaf["dir"],
            "--plain",
        ]
    elif leaf.get("use_file_list"):
        # CodeRabbit CLI may not accept arbitrary file lists; try --dir parent if single root
        # Fallback: use first common directory prefix
        files = Path(leaf["use_file_list"]).read_text(encoding="utf-8").splitlines()
        files = [f for f in files if f.strip()]
        if not files:
            return {
                "id": lid,
                "status": "skipped",
                "reason": "empty file list",
                "log": str(log_path),
            }
        # Use smallest common directory that still has under-cap... actually use first path's parent chain
        # Preferred: temporary approach --dir on longest common prefix
        parts = [Path(f).parts for f in files]
        common: list[str] = []
        for segs in zip(*parts):
            if len(set(segs)) == 1:
                common.append(segs[0])
            else:
                break
        if not common:
            return {
                "id": lid,
                "status": "skipped",
                "reason": "no common dir prefix for file list",
                "log": str(log_path),
            }
        common_dir = "/".join(common)
        # If common dir is too broad, still run — file count already capped at leaf level
        # but --dir will review ALL files under dir which may exceed 300!
        # For safety: skip if git ls-files under common_dir > 300 and note residual
        r = subprocess.run(
            ["git", "ls-files", "--", common_dir],
            capture_output=True,
            text=True,
            check=False,
        )
        n = len([x for x in r.stdout.splitlines() if x.strip()])
        if n > 300:
            return {
                "id": lid,
                "status": "skipped",
                "reason": f"common_dir {common_dir} expands to {n}>300; need sparse checkout",
                "log": str(log_path),
                "common_dir": common_dir,
                "expanded_files": n,
            }
        cmd = [
            CODERABBIT,
            "review",
            "--base",
            base,
            "--dir",
            common_dir,
            "--plain",
        ]
    else:
        return {
            "id": lid,
            "status": "skipped",
            "reason": "no dir or file list",
            "log": str(log_path),
        }

    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=900,
            check=False,
        )
        out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        log_path.write_text(out, encoding="utf-8")
        elapsed = round(time.time() - t0, 1)
        low = out.lower()
        status = "ok"
        reason = ""
        if proc.returncode != 0:
            status = "error"
            reason = f"exit {proc.returncode}"
        if "rate limit" in low or "rate_limit" in low:
            status = "rate_limit"
            reason = "rate_limit"
        if "all files ignored" in low:
            status = "ignored"
            reason = "all_files_ignored"
        if "not authenticated" in low or "auth" in low and "fail" in low:
            status = "auth_error"
            reason = "auth"
        return {
            "id": lid,
            "status": status,
            "reason": reason,
            "exit_code": proc.returncode,
            "elapsed_s": elapsed,
            "log": str(log_path),
            "bytes": len(out),
            "cmd": cmd,
        }
    except subprocess.TimeoutExpired:
        log_path.write_text("TIMEOUT after 900s\n", encoding="utf-8")
        return {
            "id": lid,
            "status": "timeout",
            "reason": "timeout 900s",
            "log": str(log_path),
            "cmd": cmd,
        }


def main() -> int:
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    leaves = matrix["leaves"]
    # optional filters
    only_wave = os.environ.get("CR_WAVE")  # e.g. A
    only_ids = os.environ.get("CR_LEAVES")  # comma ids
    max_leaves = int(os.environ.get("CR_MAX_LEAVES", "0") or "0")
    sleep_s = float(os.environ.get("CR_SLEEP", "5"))

    if only_wave:
        leaves = [L for L in leaves if L["wave"] == only_wave]
    if only_ids:
        want = set(only_ids.split(","))
        leaves = [L for L in leaves if L["id"] in want]
    # stable order: wave then id
    wave_order = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "R": 6}
    leaves = sorted(leaves, key=lambda L: (wave_order.get(L["wave"], 9), L["id"]))
    if max_leaves > 0:
        leaves = leaves[:max_leaves]

    progress = load_progress()
    done = set(progress.get("completed", [])) | set(progress.get("results", {}).keys())

    print(f"planned={len(leaves)} already={len(done)} sleep={sleep_s}")
    rate_limit_hits = 0

    for i, leaf in enumerate(leaves, 1):
        lid = leaf["id"]
        if lid in done and progress.get("results", {}).get(lid, {}).get("status") in {
            "ok",
            "ignored",
            "skipped",
        }:
            print(f"[{i}/{len(leaves)}] SKIP done {lid}")
            continue
        print(f"[{i}/{len(leaves)}] RUN {lid} wave={leaf['wave']} files={leaf['files']} dir={leaf.get('dir')}")
        result = run_leaf(leaf)
        progress.setdefault("results", {})[lid] = result
        st = result["status"]
        if st == "ok":
            progress.setdefault("completed", []).append(lid)
        elif st in {"skipped", "ignored"}:
            progress.setdefault("skipped", []).append(lid)
        else:
            progress.setdefault("failed", []).append(lid)
        save_progress(progress)
        print(f"  -> {st} {result.get('reason','')} log={result.get('log')} bytes={result.get('bytes')}")

        if st == "rate_limit":
            rate_limit_hits += 1
            wait = min(300, 30 * rate_limit_hits)
            print(f"  rate_limit backoff {wait}s")
            time.sleep(wait)
            # retry once
            print(f"  RETRY {lid}")
            result = run_leaf(leaf)
            progress["results"][lid] = result
            if result["status"] == "ok":
                progress.setdefault("completed", []).append(lid)
            save_progress(progress)
            print(f"  -> retry {result['status']}")
            if result["status"] == "rate_limit":
                print("  hard rate_limit — stop batch; resume later")
                break
        elif st == "auth_error":
            print("  auth error — abort")
            break
        else:
            time.sleep(sleep_s)

    # summary
    results = progress.get("results", {})
    counts: dict[str, int] = {}
    for r in results.values():
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("SUMMARY", counts)
    (OUT / "run_summary.json").write_text(
        json.dumps({"counts": counts, "results": results}, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
