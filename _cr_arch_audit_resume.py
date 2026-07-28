#!/usr/bin/env python3
"""Resume remaining CodeRabbit architecture scopes + write FINAL."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = "f7ec4386fda4549fa44faa071ab6627e219ba6c1"
# keep same stamp family as partial run for aggregation
STAMP = os.environ.get("CR_AUDIT_STAMP", "20260728_1520")
OUT = ROOT / "reports" / "grok"
WSL_ROOT = "/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2"
MAX_FILES = 300

REMAINING = [
    ("app_pipelines", "src/bioetl/application/pipelines"),  # retry rate-limit
    ("infra_storage", "src/bioetl/infrastructure/storage"),
    ("infra_observability", "src/bioetl/infrastructure/observability"),
    ("infra_config", "src/bioetl/infrastructure/config"),
    ("infra_quality", "src/bioetl/infrastructure/quality"),
    ("composition", "src/bioetl/composition"),
    ("interfaces", "src/bioetl/interfaces"),
    ("tests_architecture", "tests/architecture"),
    ("configs_quality", "configs/quality"),
    ("docs_decisions", "docs/02-architecture/decisions"),
    ("docs_00_project", "docs/00-project"),
    # skip docs_architecture_layers 451 unless light and time allows
    ("docs_architecture_layers", "docs/02-architecture"),
]


def load_key() -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("CODERABBIT_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("no key")


def sh_quote(s: str) -> str:
    return "'" + s.replace("'", "'\"'\"'") + "'"


def diff_count(path: str) -> int:
    r = subprocess.run(
        ["git", "diff", "--name-only", f"{BASE}...HEAD", "--", path],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return len([x for x in r.stdout.splitlines() if x.strip()])


def run_one(sid: str, d: str, key: str) -> dict:
    n = diff_count(d)
    light = n > MAX_FILES
    log = OUT / f"review_coderabbit_arch_{sid}_{STAMP}.log"
    # skip if already has complete
    if log.exists() and log.stat().st_size > 200:
        t = log.read_text(encoding="utf-8", errors="replace")
        if '"type":"complete"' in t and "Rate limit" not in t:
            print(f"SKIP existing {sid}", flush=True)
            return {"scope_id": sid, "dir": d, "file_count": n, "exit_code": 0, "skipped": True, "log": str(log)}

    wsl_log = f"{WSL_ROOT}/reports/grok/{log.name}"
    light_flag = " --light" if light else ""
    bash = (
        f"cd {sh_quote(WSL_ROOT)} && "
        f"export CODERABBIT_API_KEY={sh_quote(key)} && "
        f"coderabbit auth login --api-key \"$CODERABBIT_API_KEY\" >/dev/null 2>&1 || true; "
        f"stdbuf -oL -eL coderabbit review --agent{light_flag} --base-commit {BASE} "
        f"--dir {sh_quote(d)} > {sh_quote(wsl_log)} 2>&1; echo EXIT:$?"
    )
    print(f"=== RUN {sid} n={n} light={light} ===", flush=True)
    t0 = time.time()
    r = subprocess.run(
        ["wsl", "-e", "bash", "-lc", bash],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=2400,
    )
    elapsed = round(time.time() - t0, 1)
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"EXIT:(\d+)", out)
    code = int(m.group(1)) if m else r.returncode
    text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else out
    rate = "rate limit" if "rate limit" in text.lower() else ""
    print(f"=== DONE {sid} exit={code} {elapsed}s {rate} size={len(text)} ===", flush=True)
    return {
        "scope_id": sid,
        "dir": d,
        "file_count": n,
        "exit_code": code,
        "elapsed_sec": elapsed,
        "log": f"reports/grok/{log.name}",
        "light": light,
        "rate_limit": bool(rate),
        "size": len(text),
    }


def parse_all_logs() -> tuple[list[dict], list[dict]]:
    findings: list[dict] = []
    completes: list[dict] = []
    for p in sorted(OUT.glob(f"review_coderabbit_arch_*_{STAMP}.log")):
        sid = p.name.replace("review_coderabbit_arch_", "").replace(f"_{STAMP}.log", "")
        t = p.read_text(encoding="utf-8", errors="replace")
        for line in t.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            o["scope_id"] = sid
            o["log"] = p.name
            if o.get("type") == "finding":
                findings.append(o)
            elif o.get("type") == "complete":
                completes.append(o)
            elif o.get("type") == "error":
                findings.append(
                    {
                        "type": "error",
                        "severity": "error",
                        "message": o.get("message"),
                        "scope_id": sid,
                    }
                )
    return findings, completes


def write_final(results: list[dict]) -> Path:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    findings, completes = parse_all_logs()
    real = [f for f in findings if f.get("type") == "finding" or (
        f.get("severity") in {"major", "minor", "trivial", "critical"} and f.get("type") != "error"
    )]
    # normalize: type finding
    real = [f for f in findings if f.get("type") == "finding"]
    errors = [f for f in findings if f.get("type") == "error" or f.get("severity") == "error"]
    sev = Counter(str(f.get("severity", "?")).lower() for f in real)

    # de-dupe by file+severity+first 80 of instructions
    seen: set[str] = set()
    uniq: list[dict] = []
    for f in real:
        key = (
            f"{f.get('fileName')}|{f.get('severity')}|"
            f"{str(f.get('codegenInstructions', ''))[:100]}"
        )
        if key in seen:
            continue
        seen.add(key)
        uniq.append(f)

    md_path = OUT / f"review_coderabbit_architecture_audit_{STAMP}_FINAL.md"
    json_path = OUT / f"review_coderabbit_architecture_audit_{STAMP}.json"

    payload = {
        "stamp": STAMP,
        "head": head,
        "base_commit": BASE,
        "tool": "coderabbit CLI 0.7.0 WSL --agent",
        "method": "split --dir residual audit base...HEAD (ARCH-RES baseline)",
        "playbook": "docs/03-guides/coderabbit-audit-playbook.md",
        "scopes_meta": results,
        "completes": len(completes),
        "findings_raw": len(real),
        "findings_unique": len(uniq),
        "severity_counts": dict(sev),
        "errors": len(errors),
        "findings": uniq,
    }
    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    lines = [
        "# CodeRabbit Full Architecture Audit",
        "",
        f"- stamp: `{STAMP}`",
        f"- head: `{head}`",
        f"- base-commit: `{BASE}` (ARCH-RES closeout residual window)",
        f"- tool: CodeRabbit CLI 0.7.0 (WSL), `--agent`",
        f"- method: curated package scopes on `base...HEAD`",
        f"- playbook: `docs/03-guides/coderabbit-audit-playbook.md`",
        f"- prior morning FINAL: `reports/grok/review_coderabbit_architecture_audit_20260728_1203_FINAL.md`",
        "",
        "## Executive summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Completed review scopes (complete events) | {len(completes)} |",
        f"| Unique findings | {len(uniq)} |",
        f"| Major | {sev.get('major', 0)} |",
        f"| Minor | {sev.get('minor', 0)} |",
        f"| Trivial | {sev.get('trivial', 0)} |",
        f"| Transport errors / rate limits | {len(errors)} |",
        "",
        "### Interpretation",
        "",
        "Full architecture **residual** audit of current HEAD vs architecture-program",
        "baseline (same method as morning exhaustive CR). Empty-tree bases are not",
        "supported by CodeRabbit (no merge base). Rate limits forced a resume wave.",
        "",
        "## Scope log inventory",
        "",
        "| Log | Bytes | Notes |",
        "| --- | ---: | --- |",
    ]
    for p in sorted(OUT.glob(f"review_coderabbit_arch_*_{STAMP}.log")):
        t = p.read_text(encoding="utf-8", errors="replace")
        note = "complete" if '"type":"complete"' in t else (
            "rate-limit" if "rate limit" in t.lower() else (
                "error" if '"type":"error"' in t else "incomplete"
            )
        )
        lines.append(f"| `{p.name}` | {len(t)} | {note} |")

    lines += ["", "## Unique findings", ""]
    for i, f in enumerate(uniq, 1):
        lines.append(
            f"### F-{i:03d} **{f.get('severity')}** — `{f.get('fileName', '?')}`"
        )
        lines.append(f"- scope: `{f.get('scope_id')}`")
        instr = str(f.get("codegenInstructions", ""))
        # strip boilerplate prefix
        instr = re.sub(
            r"^Verify each finding against current code\.[^\n]*\n\n",
            "",
            instr,
        )
        lines.extend(["", instr[:1200], ""])
        if f.get("suggestions"):
            lines.append("Suggestions:")
            for s in f.get("suggestions") or []:
                lines.append(f"- ```\n{s[:400]}\n```")
            lines.append("")

    lines += [
        "## Triage guidance",
        "",
        "1. Prefer architecture tests + basedpyright over CR narrative.",
        "2. De-dupe vs closed ARCH-CR (#6862–#6870) and types epic #6925.",
        "3. Many findings are **missing tests** (not production defects).",
        "4. Registry composite stub / path-only validation may already be fixed — verify before issues.",
        "5. Do not raise debt budgets.",
        "",
        f"- JSON: `{json_path.relative_to(ROOT).as_posix()}`",
        "",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"FINAL {md_path} unique={len(uniq)}", flush=True)
    return md_path


def main() -> int:
    key = load_key()
    print(f"Resume stamp={STAMP} base={BASE}", flush=True)
    results: list[dict] = []
    for sid, d in REMAINING:
        try:
            res = run_one(sid, d, key)
            results.append(res)
            if res.get("rate_limit"):
                print("rate limited — sleeping 180s", flush=True)
                time.sleep(180)
            else:
                time.sleep(45)
        except subprocess.TimeoutExpired:
            results.append({"scope_id": sid, "dir": d, "exit_code": -1, "error": "timeout"})
            time.sleep(60)
        except Exception as e:  # noqa: BLE001
            results.append({"scope_id": sid, "dir": d, "exit_code": -2, "error": str(e)})
            time.sleep(30)

    write_final(results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
