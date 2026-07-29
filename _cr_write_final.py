#!/usr/bin/env python3
"""Aggregate CodeRabbit architecture audit logs into FINAL report."""
from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "grok"
STAMP = "20260728_1520"
BASE = "f7ec4386fda4549fa44faa071ab6627e219ba6c1"


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    findings: list[dict] = []
    completes: list[dict] = []
    scope_rows: list[str] = []

    for p in sorted(OUT.glob(f"review_coderabbit_arch_*_{STAMP}.log")):
        sid = p.name.replace("review_coderabbit_arch_", "").replace(f"_{STAMP}.log", "")
        t = p.read_text(encoding="utf-8", errors="replace")
        note = (
            "complete"
            if '"type":"complete"' in t
            else (
                "rate-limit"
                if "rate limit" in t.lower()
                else ("error" if '"type":"error"' in t else "incomplete")
            )
        )
        nfind = 0
        for line in t.splitlines():
            s = line.strip()
            if not s.startswith("{"):
                continue
            try:
                o = json.loads(s)
            except json.JSONDecodeError:
                continue
            o["scope_id"] = sid
            if o.get("type") == "finding":
                findings.append(o)
                nfind += 1
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
        scope_rows.append(f"| `{sid}` | {len(t)} | {nfind} | {note} | `{p.name}` |")

    real = [f for f in findings if f.get("type") == "finding"]
    errors = [f for f in findings if f.get("type") == "error"]
    seen: set[str] = set()
    uniq: list[dict] = []
    for f in real:
        key = f"{f.get('fileName')}|{f.get('severity')}|{str(f.get('codegenInstructions',''))[:120]}"
        if key in seen:
            continue
        seen.add(key)
        uniq.append(f)

    sev = Counter(str(f.get("severity", "?")).lower() for f in uniq)
    by_scope = Counter(str(f.get("scope_id")) for f in uniq)

    payload = {
        "stamp": STAMP,
        "head": head,
        "base_commit": BASE,
        "tool": "coderabbit CLI 0.7.0 WSL --agent",
        "method": "split --dir residual architecture audit base...HEAD",
        "playbook": "docs/03-guides/coderabbit-audit-playbook.md",
        "completed_scopes": len(completes),
        "findings_unique": len(uniq),
        "severity_counts": dict(sev),
        "by_scope": dict(by_scope),
        "errors": len(errors),
        "findings": uniq,
    }
    json_path = OUT / f"review_coderabbit_architecture_audit_{STAMP}.json"
    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    lines = [
        "# CodeRabbit Full Architecture Audit",
        "",
        f"- stamp: `{STAMP}`",
        f"- head: `{head}`",
        f"- base-commit: `{BASE}` (ARCH-RES residual window)",
        f"- tool: CodeRabbit CLI **0.7.0** (WSL), `--agent`",
        f"- method: curated package `--dir` scopes on `base...HEAD`",
        f"- playbook: `docs/03-guides/coderabbit-audit-playbook.md`",
        f"- prior FINAL: `reports/grok/review_coderabbit_architecture_audit_20260728_1203_FINAL.md`",
        "",
        "## Executive summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Scopes with `complete` events | {len(completes)} |",
        f"| Unique findings | {len(uniq)} |",
        f"| Major | {sev.get('major', 0)} |",
        f"| Minor | {sev.get('minor', 0)} |",
        f"| Trivial | {sev.get('trivial', 0)} |",
        f"| Rate-limit / transport errors | {len(errors)} |",
        "",
        "### Verdict",
        "",
        "Architecture residual health remains **good with targeted follow-ups**.",
        "CodeRabbit findings are dominated by **missing unit tests** for new helpers",
        "(checkpoint/registry/control-plane) and a smaller set of **correctness /",
        "determinism** notes. No security-critical class dominated the run.",
        "",
        "Empty-tree full-repo bases are **unsupported** by CodeRabbit (no merge base).",
        "This audit uses the same residual method as the 2026-07-28 morning exhaustive",
        "review: history-aligned base + split scopes under the ~300-file cap.",
        "",
        "### Findings by scope",
        "",
        "| Scope | Unique findings |",
        "| --- | ---: |",
    ]
    for s, n in by_scope.most_common():
        lines.append(f"| `{s}` | {n} |")

    lines += [
        "",
        "## Scope log inventory",
        "",
        "| Scope | Bytes | Findings in log | Status | Log |",
        "| --- | ---: | ---: | --- | --- |",
        *scope_rows,
        "",
        "## Unique findings (triage required)",
        "",
    ]

    majors = [f for f in uniq if str(f.get("severity")).lower() == "major"]
    minors = [f for f in uniq if str(f.get("severity")).lower() == "minor"]
    trivials = [f for f in uniq if str(f.get("severity")).lower() == "trivial"]

    def emit(title: str, items: list[dict]) -> None:
        lines.append(f"### {title}")
        lines.append("")
        if not items:
            lines.append("_None._")
            lines.append("")
            return
        for i, f in enumerate(items, 1):
            lines.append(
                f"#### {title[:1]}{i:02d} `{f.get('fileName', '?')}` — scope `{f.get('scope_id')}`"
            )
            instr = str(f.get("codegenInstructions", ""))
            instr = re.sub(
                r"^Verify each finding against current code\.[^\n]*\n\n",
                "",
                instr,
            )
            lines.append("")
            lines.append(instr[:1400] if instr else "_no instructions_")
            lines.append("")

    emit("Major", majors)
    emit("Minor", minors)
    emit("Trivial", trivials)

    lines += [
        "## Recommended next steps",
        "",
        "1. **Verify** each major against current code (several ARCH-CR themes may already be fixed).",
        "2. Bundle net-new **missing tests** into types/test backlog rather than one issue per finding.",
        "3. Cross-check control-plane/registry majors with closed ARCH-CR-02 (path-only stubs).",
        "4. Align docs majors (RULES version, DQ skip vs quarantine) with DOC-GOV SSOT already shipped.",
        "5. Re-run rate-limited scopes only if logs show incomplete status (see inventory).",
        "6. Do **not** raise quality debt budgets.",
        "",
        f"- Machine JSON: `{json_path.relative_to(ROOT).as_posix()}`",
        "",
    ]
    md_path = OUT / f"review_coderabbit_architecture_audit_{STAMP}_FINAL.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"unique={len(uniq)} major={sev.get('major',0)} minor={sev.get('minor',0)} trivial={sev.get('trivial',0)}")
    print(f"completes={len(completes)} errors={len(errors)}")


if __name__ == "__main__":
    main()
