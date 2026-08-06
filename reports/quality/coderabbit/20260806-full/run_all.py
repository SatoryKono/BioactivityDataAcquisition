#!/usr/bin/env python3
"""CR-FULL residual campaign — bare-clone orphan scopes + CodeRabbit --agent."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

MAIN = Path(os.environ.get("MAIN_REPO", "/mnt/e/github/BioactivityDataAcquisition"))
BARE = Path(os.environ.get("BARE", "/tmp/bioetl-cr-bare.git"))
WT_BASE = Path(os.environ.get("WT_BASE", "/tmp/bioetl-cr-scopes-full"))
OUT = Path(os.environ.get("OUT_DIR", "/tmp/bioetl-cr-artifacts/20260806-full"))
MATRIX = Path(os.environ.get("MATRIX", str(OUT / "01-scope-matrix.json")))
PROGRESS = OUT / "progress.json"
LOGS = OUT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)
WT_BASE.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

CR_SLEEP = float(os.environ.get("CR_SLEEP", "40"))
CR_TIMEOUT = int(os.environ.get("CR_TIMEOUT", "600"))
CR_WAVE = os.environ.get("CR_WAVE", "")
CR_MAX = int(os.environ.get("CR_MAX_LEAVES", "0") or "0")
CR_LEAVES = os.environ.get("CR_LEAVES", "")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(
    cmd: list[str],
    cwd: Path | None = None,
    timeout: int | None = None,
    binary: bool = False,
) -> subprocess.CompletedProcess:
    if binary:
        return subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}", flush=True)


def ensure_bare() -> str:
    if not BARE.exists():
        log(f"clone bare {BARE}")
        r = run(["git", "clone", "--bare", str(MAIN), str(BARE)])
        if r.returncode != 0:
            raise SystemExit(r.stderr)
    run(["git", "fetch", "origin", "main:main"], cwd=BARE)
    sha = run(["git", "rev-parse", "main"], cwd=BARE).stdout.strip()
    (OUT / "BASE_SHA.txt").write_text(sha + "\n", encoding="utf-8")
    log(f"BASE_SHA={sha}")
    return sha


def load_progress() -> dict:
    if PROGRESS.exists():
        try:
            return json.loads(PROGRESS.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"results": {}, "started": now()}


def save_progress(p: dict) -> None:
    p["updated"] = now()
    PROGRESS.write_text(json.dumps(p, indent=2), encoding="utf-8")


def resolve_file_list(file_list_path: str | None) -> list[str]:
    if not file_list_path:
        return []
    candidates = [
        Path(file_list_path),
        MAIN / "reports/quality/coderabbit/20260806-full" / Path(file_list_path).name,
        OUT / Path(file_list_path).name,
    ]
    for fl in candidates:
        if fl.exists():
            return [ln.strip() for ln in fl.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return []


def prepare(
    leaf_id: str, tip: str, dir_path: str | None, file_list_path: str | None
) -> tuple[Path | None, str, int]:
    wt = WT_BASE / leaf_id
    if wt.exists():
        shutil.rmtree(wt, ignore_errors=True)
    wt.mkdir(parents=True)
    run(["git", "init"], cwd=wt)
    run(["git", "config", "user.email", "coderabbit-audit@local"], cwd=wt)
    run(["git", "config", "user.name", "CR Residual Audit"], cwd=wt)
    # CodeRabbit needs a named base branch
    run(["git", "checkout", "-b", "main"], cwd=wt)
    run(["git", "config", "coderabbit.baseBranch", "main"], cwd=wt)
    run(["git", "commit", "--allow-empty", "-m", f"empty {leaf_id}"], cwd=wt)
    empty = run(["git", "rev-parse", "HEAD"], cwd=wt).stdout.strip()
    run(["git", "checkout", "-b", f"cr-scope-{leaf_id}"], cwd=wt)

    paths: list[str] = []
    if dir_path:
        paths.append(dir_path)
    paths.extend(resolve_file_list(file_list_path))

    for p in paths:
        r = run(["git", "archive", tip, "--", p], cwd=BARE, binary=True)
        if r.returncode == 0 and r.stdout:
            subprocess.run(
                ["tar", "-x", "-C", str(wt)],
                input=r.stdout,
                check=False,
                capture_output=True,
            )

    run(["git", "add", "-A"], cwd=wt)
    count = len(
        [x for x in run(["git", "ls-files"], cwd=wt).stdout.splitlines() if x.strip()]
    )
    if count == 0:
        return None, empty, 0
    if count > 300:
        return None, empty, count
    run(["git", "commit", "-m", f"scope {leaf_id} {count}"], cwd=wt)
    return wt, empty, count


def run_leaf(leaf: dict, tip: str) -> dict:
    lid = leaf["id"]
    logf = LOGS / f"review_{lid}.jsonl"
    errf = LOGS / f"review_{lid}.err"
    wt, empty, count = prepare(
        lid, tip, leaf.get("dir"), leaf.get("use_file_list")
    )
    if wt is None:
        reason = "over_cap" if count > 300 else "0_files"
        return {
            "id": lid,
            "status": "skipped",
            "reason": reason,
            "findings": 0,
            "files": count,
            "log": str(logf),
        }

    cmd = ["coderabbit", "review", "--base-commit", empty, "--agent", "--light"]
    t0 = time.time()
    try:
        proc = run(cmd, cwd=wt, timeout=CR_TIMEOUT)
    except subprocess.TimeoutExpired:
        logf.write_text('{"type":"error","errorType":"timeout"}\n', encoding="utf-8")
        return {
            "id": lid,
            "status": "timeout",
            "reason": "timeout",
            "findings": 0,
            "files": count,
            "log": str(logf),
            "elapsed_s": CR_TIMEOUT,
        }

    out = proc.stdout or ""
    err = proc.stderr or ""
    if isinstance(out, bytes):
        out = out.decode("utf-8", "replace")
    if isinstance(err, bytes):
        err = err.decode("utf-8", "replace")
    logf.write_text(out, encoding="utf-8")
    errf.write_text(err, encoding="utf-8")
    low = (out + err).lower()
    status = "ok"
    reason = ""
    if proc.returncode != 0:
        status = "error"
        reason = f"exit_{proc.returncode}"
    if "rate_limit" in low or "rate limit" in low:
        status = "rate_limit"
        reason = "rate_limit"
    if "all files ignored" in low:
        status = "ignored"
        reason = "all_files_ignored"
    if not out.strip() and status == "ok":
        status = "error"
        reason = "empty_output"
    findings = len(re.findall(r'"type"\s*:\s*"finding"', out))
    return {
        "id": lid,
        "wave": leaf.get("wave"),
        "status": status,
        "reason": reason,
        "findings": findings,
        "files": count,
        "log": str(logf),
        "elapsed_s": round(time.time() - t0, 1),
    }


def main() -> None:
    tip = ensure_bare()
    leaves = json.loads(MATRIX.read_text(encoding="utf-8"))["leaves"]
    order = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "R": 6}
    if CR_WAVE:
        leaves = [L for L in leaves if L.get("wave") == CR_WAVE]
    if CR_LEAVES:
        want = set(CR_LEAVES.split(","))
        leaves = [L for L in leaves if L["id"] in want]
    leaves = sorted(leaves, key=lambda L: (order.get(L.get("wave"), 9), L["id"]))
    if CR_MAX > 0:
        leaves = leaves[:CR_MAX]

    prog = load_progress()
    results = prog.setdefault("results", {})
    log(f"leaves={len(leaves)} tip={tip}")

    for i, leaf in enumerate(leaves, 1):
        lid = leaf["id"]
        prev = results.get(lid, {})
        if prev.get("status") in {"ok", "ignored"}:
            log(f"[{i}/{len(leaves)}] SKIP {lid}")
            continue
        log(
            f"[{i}/{len(leaves)}] RUN {lid} wave={leaf.get('wave')} "
            f"files={leaf.get('files')} dir={leaf.get('dir')}"
        )
        res = run_leaf(leaf, tip)
        results[lid] = res
        save_progress(prog)
        log(
            f"  -> {res['status']} findings={res.get('findings')} "
            f"reason={res.get('reason')} elapsed={res.get('elapsed_s')}"
        )
        if res["status"] == "rate_limit":
            time.sleep(180)
            res = run_leaf(leaf, tip)
            results[lid] = res
            save_progress(prog)
            log(f"  -> retry {res['status']} findings={res.get('findings')}")
            if res["status"] == "rate_limit":
                log("hard rate_limit stop")
                break
        else:
            time.sleep(CR_SLEEP)

    c = Counter(r.get("status") for r in results.values())
    tf = sum(int(r.get("findings") or 0) for r in results.values())
    log(f"SUMMARY {dict(c)} findings={tf}")
    (OUT / "run_summary.json").write_text(
        json.dumps(
            {"counts": dict(c), "total_findings": tf, "results": results}, indent=2
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
