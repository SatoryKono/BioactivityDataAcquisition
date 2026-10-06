#!/usr/bin/env python3
"""Extract and triage CodeRabbit findings from 20260925 audit."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path("reports/quality/coderabbit/20260925_085141")
REPO = Path(".")


def extract() -> list[dict]:
    findings: list[dict] = []
    for path in sorted(ROOT.glob("review_*.jsonl")):
        leaf = path.name.removeprefix("review_").removesuffix(".jsonl")
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("type") != "finding":
                continue
            text = obj.get("codegenInstructions") or obj.get("message") or ""
            m = re.search(r"In @([^\s]+) around lines? ([0-9 -]+), (.+)", text, re.S)
            m2 = re.search(r"In @([^\s]+) at line ([0-9]+), (.+)", text, re.S)
            if m:
                file_name, lines, body = m.group(1), m.group(2), m.group(3).strip()
            elif m2:
                file_name, lines, body = m2.group(1), m2.group(2), m2.group(3).strip()
            else:
                file_name = obj.get("fileName") or "?"
                lines = "?"
                body = text.split("\n\n")[-1][:600] if text else ""
            findings.append(
                {
                    "leaf": leaf,
                    "severity": obj.get("severity") or "unknown",
                    "file": file_name,
                    "lines": lines.replace(" ", ""),
                    "body": body[:800],
                    "full": text,
                }
            )
    return findings


def parse_line_span(span: str) -> tuple[int, int] | None:
    nums = [int(x) for x in re.findall(r"\d+", span)]
    if not nums:
        return None
    if len(nums) == 1:
        return nums[0], nums[0]
    return nums[0], nums[-1]


def snippet(path: Path, start: int, end: int, pad: int = 3) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    lo = max(1, start - pad)
    hi = min(len(lines), end + pad)
    return "\n".join(f"{i}:{lines[i-1]}" for i in range(lo, hi + 1))


def keyword_hits(body: str, code: str) -> list[str]:
    """Cheap signals that the cited concern may still be present."""
    tokens: list[str] = []
    for pat in (
        r"`([^`]+)`",
        r"_([a-zA-Z][a-zA-Z0-9_]{4,})",
        r"\b([A-Z][a-zA-Z0-9_]{4,})\b",
        r"\b([a-z_][a-z0-9_]{6,})\b",
    ):
        tokens.extend(re.findall(pat, body))
    interesting = []
    seen = set()
    for t in tokens:
        if t.lower() in {"update", "replace", "move", "keep", "leave", "ensure", "preserve", "treat", "verify", "finding", "composition", "application"}:
            continue
        if t in seen or len(t) < 5:
            continue
        seen.add(t)
        if t in code or t.lower() in code.lower():
            interesting.append(t)
        if len(interesting) >= 8:
            break
    return interesting


def triage(findings: list[dict]) -> list[dict]:
    out: list[dict] = []
    for f in findings:
        rel = f["file"]
        path = REPO / rel
        status = "unknown"
        reason = ""
        code = ""
        hits: list[str] = []
        span = parse_line_span(f["lines"])
        if not path.exists():
            status = "stale_missing_file"
            reason = "file missing on HEAD"
        elif span is None:
            status = "needs_manual"
            reason = "no line span"
            code = path.read_text(encoding="utf-8", errors="replace")[:2000]
            hits = keyword_hits(f["body"], code)
        else:
            start, end = span
            code = snippet(path, start, end, pad=8)
            hits = keyword_hits(f["body"], code)
            # Heuristics for common "move layer" architectural findings:
            # still current if cited symbols/paths still exist near the span.
            body_l = f["body"].lower()
            if not code.strip():
                status = "stale_lines_moved"
                reason = "line span empty / beyond EOF"
            elif "move" in body_l and ("application" in body_l or "infrastructure" in body_l or "observer" in body_l):
                status = "likely_current_arch" if hits else "needs_manual"
                reason = "layering recommendation; symbols " + (",".join(hits) if hits else "not near span")
            elif hits:
                status = "likely_current"
                reason = "keywords near span: " + ",".join(hits)
            else:
                status = "needs_manual"
                reason = "no strong keyword hit near cited lines"
        item = dict(f)
        item.update({"status": status, "reason": reason, "hits": hits, "snippet": code[:1200]})
        out.append(item)
    return out


def main() -> None:
    findings = extract()
    triaged = triage(findings)
    out = ROOT / "findings_triage.json"
    out.write_text(json.dumps(triaged, ensure_ascii=False, indent=2), encoding="utf-8")
    print("total", len(triaged))
    print("by_sev", dict(Counter(f["severity"] for f in triaged)))
    print("by_status", dict(Counter(f["status"] for f in triaged)))
    print("by_leaf", dict(Counter(f["leaf"] for f in triaged)))
    # Print compact table for critical/major
    print("\n## CRITICAL/MAJOR")
    for f in triaged:
        if f["severity"] not in {"critical", "major"}:
            continue
        print(f"- [{f['severity']}] [{f['status']}] {f['file']}:{f['lines']}")
        print(f"  {f['body'][:220].replace(chr(10), ' ')}")
        print(f"  reason: {f['reason']}")


if __name__ == "__main__":
    main()
