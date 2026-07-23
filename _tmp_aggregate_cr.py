#!/usr/bin/env python3
"""Aggregate CodeRabbit finding JSONs into an architecture review report."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path.home() / ".coderabbit" / "reviews"
OUT_DIR = Path(
    "/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/reports/quality/coderabbit"
)
# also support windows path when run from Windows python
if not OUT_DIR.parent.exists():
    OUT_DIR = Path(
        r"E:\g-drive\05_AI\github\BioactivityDataAcquisition2\reports\quality\coderabbit"
    )

ARCH_PREFIXES = (
    "src/bioetl/domain/",
    "src/bioetl/application/",
    "src/bioetl/composition/",
    "src/bioetl/infrastructure/",
    "src/bioetl/interfaces/",
    "src/bioetl/",
    "tests/architecture/",
    "docs/02-architecture/",
    ".importlinter",
    "configs/",
    "scripts/engineering/qa/",
)


def is_arch(path: str) -> bool:
    p = path.replace("\\", "/")
    return any(p.startswith(pref) or pref.rstrip("/") == p for pref in ARCH_PREFIXES)


findings: list[dict] = []
seen: set[str] = set()

for p in ROOT.rglob("*.json"):
    if p.name in {
        "diff.json",
        "git.json",
        "internalState.json",
        "incrementalDiff.json",
    }:
        continue
    try:
        data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        continue
    if not isinstance(data, dict) or "fileName" not in data or "title" not in data:
        continue
    fp = str(data.get("fingerprint") or data.get("id") or "")
    key = fp or f"{data.get('fileName')}:{data.get('startLine')}:{data.get('title')}"
    if key in seen:
        continue
    seen.add(key)
    findings.append(
        {
            "fileName": data.get("fileName", ""),
            "title": data.get("title", ""),
            "severity": data.get("severity", ""),
            "category": data.get("commentCategory") or data.get("type") or "",
            "startLine": data.get("startLine"),
            "endLine": data.get("endLine"),
            "comment": (data.get("comment") or "")[:1200],
            "codegenInstructions": (data.get("codegenInstructions") or "")[:800],
            "source": str(p),
            "mtime": p.stat().st_mtime,
        }
    )

findings.sort(key=lambda x: (-x["mtime"], x["severity"], x["fileName"]))
arch = [f for f in findings if is_arch(str(f["fileName"]))]

sev = Counter(f["severity"] for f in arch)
cat = Counter(f["category"] for f in arch)
by_layer: dict[str, list] = defaultdict(list)
for f in arch:
    name = str(f["fileName"]).replace("\\", "/")
    layer = "other"
    for pref, label in (
        ("src/bioetl/domain/", "domain"),
        ("src/bioetl/application/", "application"),
        ("src/bioetl/composition/", "composition"),
        ("src/bioetl/infrastructure/", "infrastructure"),
        ("src/bioetl/interfaces/", "interfaces"),
        ("tests/architecture/", "tests/architecture"),
        ("docs/02-architecture/", "docs/architecture"),
        ("configs/", "configs"),
        ("scripts/", "scripts"),
    ):
        if name.startswith(pref):
            layer = label
            break
    by_layer[layer].append(f)

OUT_DIR.mkdir(parents=True, exist_ok=True)
out = OUT_DIR / "architecture-review-aggregated.md"
lines: list[str] = []
lines.append("# CodeRabbit — aggregated architecture review")
lines.append("")
lines.append(
    "CodeRabbit reviews diffs (not a full static scan of the whole tree). "
    "This report aggregates stored local CodeRabbit findings that touch "
    "hexagonal architecture surfaces (`src/bioetl/*`, architecture tests/docs)."
)
lines.append("")
lines.append(f"- Total unique findings scanned: **{len(findings)}**")
lines.append(f"- Architecture-related findings: **{len(arch)}**")
lines.append(f"- By severity: `{dict(sev)}`")
lines.append(f"- By category: `{dict(cat)}`")
lines.append("")

order = [
    "domain",
    "application",
    "composition",
    "infrastructure",
    "interfaces",
    "tests/architecture",
    "docs/architecture",
    "configs",
    "scripts",
    "other",
]
for layer in order:
    items = by_layer.get(layer) or []
    if not items:
        continue
    lines.append(f"## {layer} ({len(items)})")
    lines.append("")
    # prefer critical/major first
    sev_rank = {"critical": 0, "major": 1, "high": 1, "medium": 2, "minor": 3, "low": 4, "info": 5}
    items = sorted(
        items,
        key=lambda x: (sev_rank.get(str(x["severity"]).lower(), 9), x["fileName"], x["startLine"] or 0),
    )
    for i, f in enumerate(items[:40], 1):
        lines.append(
            f"### {i}. [{f['severity'] or '?'}] {f['title']}"
        )
        lines.append("")
        lines.append(
            f"- **File:** `{f['fileName']}:{f['startLine']}-{f['endLine']}`"
        )
        lines.append(f"- **Category:** {f['category']}")
        body = (f["comment"] or "").strip().replace("\r\n", "\n")
        if body:
            lines.append("")
            lines.append(body[:900])
        instr = (f["codegenInstructions"] or "").strip()
        if instr:
            lines.append("")
            lines.append("**Suggested fix direction:**")
            lines.append("")
            lines.append(instr[:500])
        lines.append("")
    if len(items) > 40:
        lines.append(f"_…and {len(items) - 40} more in this layer._")
        lines.append("")

out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("wrote", out)
print("arch_findings", len(arch), "total", len(findings))
print("by_layer", {k: len(v) for k, v in by_layer.items()})
print("severity", dict(sev))
# print top majors
print("--- TOP major/critical ---")
for f in arch:
    if str(f["severity"]).lower() in {"critical", "major", "high"}:
        print(f"[{f['severity']}] {f['fileName']}:{f['startLine']} {f['title']}")
