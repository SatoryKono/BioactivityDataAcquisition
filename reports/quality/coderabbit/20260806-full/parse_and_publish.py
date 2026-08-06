#!/usr/bin/env python3
"""Parse CR agent JSONL → FINDINGS/TRIAGE → GH issue per accepted finding."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(os.environ.get("OUT_DIR", "/tmp/bioetl-cr-artifacts/20260806-full"))
# also merge host path
HOST_OUT = Path(
    "/mnt/e/github/BioactivityDataAcquisition/reports/quality/coderabbit/20260806-full"
)
REPO = os.environ.get("GH_REPO", "SatoryKono/BioactivityDataAcquisition")
DRY = os.environ.get("CR_DRY_RUN", "0") == "1"
EXTRA_LOG_DIRS = [
    OUT / "logs",
    HOST_OUT / "logs",
    Path("/tmp/bioetl-cr-artifacts/20260806-domain-retry"),
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_log_file(log: Path, leaf_hint: str = "") -> list[dict]:
    findings: list[dict] = []
    leaf = leaf_hint or log.stem.replace("review_", "").replace(".agent", "")
    text = log.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") != "finding":
            continue
        sev = (obj.get("severity") or "minor").lower()
        path = (obj.get("fileName") or obj.get("file") or "").replace("\\", "/")
        claim = obj.get("codegenInstructions") or obj.get("description") or ""
        claim_short = claim
        m = re.search(
            r"(?:Add|Update|Fix|Ensure|Remove|Refactor|Verify|Move|In @).{10,180}",
            claim,
            re.I | re.S,
        )
        if m:
            claim_short = re.sub(r"\s+", " ", m.group(0))[:180]
        elif len(claim) > 180:
            claim_short = claim[:180] + "…"
        fp = hashlib.sha1(f"{path}|{sev}|{claim_short}".encode()).hexdigest()[:12]
        findings.append(
            {
                "id": f"{leaf}:{fp}",
                "leaf": leaf,
                "severity": sev,
                "path": path,
                "claim": claim_short.strip(),
                "claim_full": claim.strip(),
                "fingerprint": fp,
                "confidence": "medium",
                "fix_class": "test" if "test" in claim.lower() else "code",
                "status": "confirm",
                "log": str(log),
            }
        )
    return findings


def collect_findings() -> list[dict]:
    raw: list[dict] = []
    seen_logs: set[str] = set()
    for d in EXTRA_LOG_DIRS:
        if not d.exists():
            continue
        for log in list(d.glob("review_*.jsonl")) + list(d.glob("review_*.log")) + list(
            d.glob("review_*.agent.json")
        ):
            key = str(log.resolve()) if log.exists() else str(log)
            if key in seen_logs:
                continue
            seen_logs.add(key)
            raw.extend(parse_log_file(log))
    # dedupe by fingerprint
    by_fp: dict[str, dict] = {}
    for f in raw:
        by_fp.setdefault(f["fingerprint"], f)
    return list(by_fp.values())


def priority_label(sev: str) -> str:
    return {
        "critical": "priority:critical",
        "major": "priority:high",
        "minor": "priority:medium",
        "trivial": "priority:low",
    }.get(sev, "priority:medium")


def gh_env() -> dict:
    env = {**os.environ, "NO_COLOR": "1", "GH_FORCE_TTY": "0", "TERM": "dumb"}
    if not env.get("GH_TOKEN") and env.get("CODEX_GITHUB_PERSONAL_ACCESS_TOKEN"):
        env["GH_TOKEN"] = env["CODEX_GITHUB_PERSONAL_ACCESS_TOKEN"]
    return env


def find_existing(path: str) -> int | None:
    if not path:
        return None
    r = subprocess.run(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            REPO,
            "--state",
            "open",
            "--search",
            f"residual in:title {path}",
            "--limit",
            "30",
            "--json",
            "number,title",
        ],
        capture_output=True,
        text=True,
        env=gh_env(),
        check=False,
    )
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        items = json.loads(re.sub(r"\x1b\[[0-9;]*m", "", r.stdout))
    except json.JSONDecodeError:
        return None
    pl = path.lower()
    for it in items:
        if pl in it.get("title", "").lower():
            return int(it["number"])
    return None


def create_issue(f: dict) -> dict:
    path = f["path"] or "(unknown)"
    sev = f["severity"]
    short = f["claim"][:80].replace("\n", " ")
    title = f"[CR-FULL][{sev}] residual in `{path}` — {short}"
    if len(title) > 240:
        title = title[:237] + "..."
    body = f"""## Source

- Campaign: **CR-FULL-20260806-full**
- Leaf: `{f.get('leaf')}`
- Finding id: `{f['id']}`
- Fingerprint: `{f['fingerprint']}`
- Log: `{f.get('log','')}`

## Severity

- **{sev}** (confidence: {f.get('confidence','medium')})
- Fix class: `{f.get('fix_class','code')}`

## Path

`{path}`

## Claim

{f.get('claim_full') or f.get('claim')}

## Acceptance

- [ ] Confirm against current `main` (code wins)
- [ ] Fix or reject with evidence
- [ ] Do **not** grow tech-debt / quality budgets
- [ ] Prefer focused PR for this path

## Notes

Auto-filed from CodeRabbit CLI residual campaign (`coderabbit review --agent`).
"""
    existing = find_existing(path)
    # only link if title severity matches-ish and path exact — still create if claim differs heavily
    # For per-problem requirement: if existing title contains same short claim prefix, link
    if existing:
        r = subprocess.run(
            ["gh", "issue", "view", str(existing), "--repo", REPO, "--json", "title,body"],
            capture_output=True,
            text=True,
            env=gh_env(),
            check=False,
        )
        if r.returncode == 0:
            try:
                data = json.loads(re.sub(r"\x1b\[[0-9;]*m", "", r.stdout))
                blob = (data.get("title", "") + data.get("body", "")).lower()
                if f["fingerprint"] in blob or f["claim"][:50].lower() in blob:
                    return {
                        "finding_id": f["id"],
                        "issue": existing,
                        "action": "linked_existing",
                        "severity": sev,
                        "path": path,
                        "url": f"https://github.com/{REPO}/issues/{existing}",
                    }
            except json.JSONDecodeError:
                pass

    if DRY:
        return {
            "finding_id": f["id"],
            "issue": None,
            "action": "dry_run",
            "severity": sev,
            "path": path,
            "title": title,
            "body": body,
        }

    cmd = [
        "gh",
        "issue",
        "create",
        "--repo",
        REPO,
        "--title",
        title,
        "--body",
        body,
        "--label",
        "quality",
        "--label",
        priority_label(sev),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, env=gh_env(), check=False)
    out = re.sub(r"\x1b\[[0-9;]*m", "", (r.stdout or "") + (r.stderr or ""))
    m = re.search(r"issues/(\d+)", out)
    if not m:
        # retry without labels
        cmd2 = [
            "gh",
            "issue",
            "create",
            "--repo",
            REPO,
            "--title",
            title,
            "--body",
            body,
        ]
        r = subprocess.run(cmd2, capture_output=True, text=True, env=gh_env(), check=False)
        out = re.sub(r"\x1b\[[0-9;]*m", "", (r.stdout or "") + (r.stderr or ""))
        m = re.search(r"issues/(\d+)", out)
    if not m:
        return {
            "finding_id": f["id"],
            "issue": None,
            "action": "failed",
            "severity": sev,
            "path": path,
            "error": out[:500],
            "title": title,
            "body": body,
        }
    num = int(m.group(1))
    return {
        "finding_id": f["id"],
        "issue": num,
        "action": "created",
        "severity": sev,
        "path": path,
        "url": f"https://github.com/{REPO}/issues/{num}",
        "title": title,
    }


def write_mirror(name: str, text: str) -> None:
    for base in (OUT, HOST_OUT):
        try:
            base.mkdir(parents=True, exist_ok=True)
            (base / name).write_text(text, encoding="utf-8")
        except Exception:
            pass


def main() -> int:
    findings = collect_findings()
    sev_c = Counter(f["severity"] for f in findings)
    accepted = [f for f in findings if f.get("path") or f.get("claim")]
    for f in findings:
        if not f.get("path") and not f.get("claim"):
            f["status"] = "reject"
        else:
            f["status"] = "confirm"

    find_md = [
        "# FINDINGS — CR-FULL-20260806-full",
        "",
        f"Generated: {now()}",
        f"Deduped findings: {len(findings)}",
        f"By severity: {dict(sev_c)}",
        "",
    ]
    for f in sorted(findings, key=lambda x: (x["severity"], x["path"])):
        find_md.append(
            f"- `{f['id']}` **{f['severity']}** `{f['path']}` — {f['claim'][:140]}"
        )
    write_mirror("FINDINGS.md", "\n".join(find_md) + "\n")
    write_mirror(
        "FINDINGS.jsonl",
        "\n".join(json.dumps(f, ensure_ascii=False) for f in findings)
        + ("\n" if findings else ""),
    )
    triage = ["# TRIAGE", "", "Default: CONFIRM all non-empty findings.", ""]
    for f in accepted:
        triage.append(f"- CONFIRM `{f['id']}` {f['severity']} `{f['path']}`")
    write_mirror("TRIAGE.md", "\n".join(triage) + "\n")
    write_mirror(
        "DE_DUPE_MAP.json",
        json.dumps({f["fingerprint"]: f["id"] for f in findings}, indent=2),
    )

    print(f"findings={len(findings)} accepted={len(accepted)} sev={dict(sev_c)}")

    map_rows = []
    for f in accepted:
        row = create_issue(f)
        map_rows.append(row)
        f["gh_issue"] = row.get("issue")
        print(
            f"  {row.get('action')} #{row.get('issue')} {f['severity']} {f['path'][:70]}",
            flush=True,
        )
        time.sleep(0.35)

    write_mirror("ISSUES_MAP.json", json.dumps(map_rows, indent=2, ensure_ascii=False))
    write_mirror(
        "FINDINGS.jsonl",
        "\n".join(json.dumps(f, ensure_ascii=False) for f in findings)
        + ("\n" if findings else ""),
    )

    created = sum(1 for r in map_rows if r.get("action") == "created")
    linked = sum(1 for r in map_rows if r.get("action") == "linked_existing")
    failed = [r for r in map_rows if r.get("action") == "failed"]
    md = [
        "# ISSUES_CREATED",
        "",
        f"created={created} linked={linked} failed={len(failed)} total_map={len(map_rows)}",
        "",
        "| finding | severity | issue | path | action |",
        "|---------|----------|------:|------|--------|",
    ]
    for r in map_rows:
        md.append(
            f"| `{r.get('finding_id')}` | {r.get('severity')} | {r.get('issue') or '—'} | `{r.get('path')}` | {r.get('action')} |"
        )
    if failed:
        md.append("")
        md.append("## Failed")
        for r in failed:
            md.append(f"### {r.get('title')}")
            md.append(f"ERROR: {r.get('error')}")
            md.append("")
            md.append(r.get("body") or "")
            md.append("")
    write_mirror("ISSUES_CREATED.md", "\n".join(md) + "\n")
    print(f"ISSUES created={created} linked={linked} failed={len(failed)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
