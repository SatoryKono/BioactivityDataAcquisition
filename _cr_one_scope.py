#!/usr/bin/env python3
"""Run one CodeRabbit scope: python _cr_one_scope.py <scope_id> <dir>"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = "f7ec4386fda4549fa44faa071ab6627e219ba6c1"
STAMP = "20260728_1520"
WSL_ROOT = "/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2"


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: _cr_one_scope.py scope_id dir")
        return 2
    sid, d = sys.argv[1], sys.argv[2]
    key = ""
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("CODERABBIT_API_KEY="):
            key = line.split("=", 1)[1].strip().strip('"').strip("'")
    log = ROOT / "reports" / "grok" / f"review_coderabbit_arch_{sid}_{STAMP}.log"
    wsl_log = f"{WSL_ROOT}/reports/grok/{log.name}"
    if log.exists() and log.stat().st_size > 200:
        t = log.read_text(encoding="utf-8", errors="replace")
        if '"type":"complete"' in t and "Rate limit" not in t:
            print(f"already complete {sid}")
            return 0
    n = len(
        subprocess.check_output(
            ["git", "diff", "--name-only", f"{BASE}...HEAD", "--", d], text=True
        ).splitlines()
    )
    light = " --light" if n > 300 else ""
    bash = (
        f"cd {WSL_ROOT!r} && "
        f"export CODERABBIT_API_KEY={key!r} && "
        f"coderabbit auth login --api-key \"$CODERABBIT_API_KEY\" >/dev/null 2>&1 || true; "
        f"stdbuf -oL -eL coderabbit review --agent{light} --base-commit {BASE} "
        f"--dir {d!r} > {wsl_log!r} 2>&1; echo EXIT:$?"
    )
    print(f"RUN {sid} n={n} light={bool(light)}", flush=True)
    t0 = time.time()
    r = subprocess.run(
        ["wsl", "-e", "bash", "-lc", bash],
        capture_output=True,
        text=True,
        timeout=2400,
    )
    print(r.stdout, flush=True)
    print(
        f"elapsed={time.time() - t0:.1f}s size={log.stat().st_size if log.exists() else -1}",
        flush=True,
    )
    if log.exists():
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.startswith("{"):
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if o.get("type") in {"finding", "complete", "error"}:
                print(
                    o.get("type"),
                    o.get("severity"),
                    (o.get("fileName") or "")[:70],
                    (o.get("message") or "")[:100],
                    flush=True,
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
