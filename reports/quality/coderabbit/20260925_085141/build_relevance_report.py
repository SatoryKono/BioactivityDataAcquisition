#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("reports/quality/coderabbit/20260925_085141")
REPO = Path(".")
TRIAGED = json.loads((ROOT / "findings_triage.json").read_text(encoding="utf-8"))


def read_span(rel: str, span: str, pad: int = 5) -> str:
    path = REPO / rel
    if not path.exists():
        return "<MISSING>"
    nums = [int(x) for x in re.findall(r"\d+", span)]
    if not nums:
        return "<NO SPAN>"
    start, end = nums[0], nums[-1]
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    lo, hi = max(1, start - pad), min(len(lines), end + pad)
    return "\n".join(f"{i}|{lines[i-1]}" for i in range(lo, hi + 1))


def verify_critical() -> list[dict]:
    results = []
    for f in TRIAGED:
        if f["severity"] != "critical":
            continue
        code = read_span(f["file"], f["lines"], pad=10)
        body = f["body"].lower()
        still = False
        evidence = []
        if "records_bronze" in body or "confirmed" in body or "total_fetched" in body:
            # checkpoint count issue
            if "total_fetched" in code or "fetched" in code.lower():
                still = True
                evidence.append("still references fetched/total_fetched near span")
            if "records_bronze" not in code and "records_bronze" in body:
                still = True
                evidence.append("records_bronze not used at cited call site")
        if "_ensure_registrations" in body or "providers" in body:
            if "_ensure_registrations()" in code and "PROVIDERS" not in code:
                still = True
                evidence.append("_ensure_registrations() still no PROVIDERS scope")
        results.append(
            {
                "file": f["file"],
                "lines": f["lines"],
                "leaf": f["leaf"],
                "body": f["body"],
                "still_current": still,
                "evidence": evidence,
                "code": code,
            }
        )
    return results


# Domain-specific still-current checks for selected majors
CHECKS = [
    # (predicate on finding, verify_fn returning (still, evidence))
]


def group_key(f: dict) -> str:
    file = f["file"]
    if "batch_executor" in file or "batch_execution" in file:
        return "checkpoint-bronze-count"
    if file.startswith("src/bioetl/composition/"):
        if "layer" in f["body"].lower() or f["body"].lower().startswith("move"):
            return "composition-layering"
        return "composition-correctness"
    if "/domain/" in file.replace("\\", "/"):
        return "domain-hardening"
    if "/application/" in file.replace("\\", "/"):
        return "application-correctness"
    return "other"


def main() -> None:
    # S03 status
    s03 = ROOT / "review_S03-infra-adapters.jsonl"
    s03_findings = 0
    s03_types = Counter()
    if s03.exists():
        for line in s03.read_text(encoding="utf-8").splitlines():
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            s03_types[obj.get("type")] += 1
            if obj.get("type") == "finding":
                s03_findings += 1

    crit = verify_critical()
    by_group = defaultdict(list)
    for f in TRIAGED:
        by_group[group_key(f)].append(f)

    # Manual spot-checks for high-signal majors
    spot = []
    candidates = [
        ("src/bioetl/domain/ports/observability/metrics.py", "108", "127.0.0.1", "addr"),
        ("src/bioetl/domain/ports/observability/metrics.py", "9-23", "forbidden", "resolve_metric_labels"),
        ("src/bioetl/composition/factories/services/bundle.py", "166-168", "extract_entity_type", "_extract_entity_type"),
        ("src/bioetl/composition/factories/storage/clear_mixin.py", "107-117", "table_name", "clear_delta"),
        ("src/bioetl/application/core/batch_executor_loop_flow.py", "114-119", "total_fetched", "save_periodic"),
        ("src/bioetl/application/core/batch_execution/lifecycle.py", "179-193", "total_fetched", "save_checkpoint"),
        ("src/bioetl/composition/_resource_management.py", "79-87", "_ensure_registrations", "PROVIDERS"),
        ("src/bioetl/composition/_service_registry.py", "36", "_REGISTRY", "mutable"),
        ("src/bioetl/composition/_workflow_services.py", "161-166", "_workflow_memory_lock", "lock"),
        ("src/bioetl/domain/value_objects/run_context.py", "109-113", "started_at", "utcoffset"),
        ("src/bioetl/domain/normalization/_chembl_units.py", "22-39", "_UNIT_ALIASES", "case"),
    ]
    for file, lines, *needles in candidates:
        code = read_span(file, lines, pad=8)
        missing = [n for n in needles if n not in code]
        present = [n for n in needles if n in code]
        still = bool(present) and Path(file).exists()
        # special cases
        if file.endswith("metrics.py") and lines == "108":
            still = "127.0.0.1" not in code and ("addr" in code or "start" in code)
            evidence = "default addr not loopback" if still else "already loopback or missing"
        elif "PROVIDERS" in needles:
            still = "_ensure_registrations()" in code and "PROVIDERS" not in code
            evidence = "still bare _ensure_registrations()" if still else "fixed or changed"
        elif "total_fetched" in needles:
            still = "total_fetched" in code or ("fetched" in code and "records_bronze" not in code)
            evidence = "still uses fetched counts" if still else "uses bronze or changed"
        else:
            evidence = f"present={present} missing={missing}"
        spot.append(
            {
                "file": file,
                "lines": lines,
                "still_current": still,
                "evidence": evidence,
                "code_excerpt": code[:900],
            }
        )

    report = {
        "audit_dir": str(ROOT),
        "root_sha": (ROOT / "root_sha.txt").read_text(encoding="utf-8").strip(),
        "baseline_main_sha": (ROOT / "main_sha.txt").read_text(encoding="utf-8").strip(),
        "findings_total": len(TRIAGED),
        "by_severity": dict(Counter(f["severity"] for f in TRIAGED)),
        "by_leaf_ok": dict(Counter(f["leaf"] for f in TRIAGED)),
        "incomplete_leaves": {
            "S03-infra-adapters": {"findings_in_jsonl": s03_findings, "event_types": dict(s03_types)},
            "S05-interfaces": "rate_limit/connection failed",
            "S06a/S06b-tests-architecture": "all files ignored",
            "S07-configs-quality": "all files ignored",
            "S08a/S08b-docs": "all files ignored",
            "S00c-domain-small-subdirs": "review failed / 0 findings",
        },
        "critical_verification": crit,
        "spot_checks": spot,
        "group_counts": {k: len(v) for k, v in by_group.items()},
    }
    out_json = ROOT / "findings_relevance_report.json"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown for humans
    lines: list[str] = []
    lines.append("# CodeRabbit 2026-09-25 — актуальность находок")
    lines.append("")
    lines.append(f"- Каталог: `{ROOT}`")
    lines.append(f"- Audit root SHA: `{report['root_sha'][:12]}`")
    lines.append(f"- Baseline main SHA: `{report['baseline_main_sha'][:12]}`")
    lines.append(f"- Findings extracted: **{report['findings_total']}** (ok-leaves only)")
    lines.append(f"- Severity: {report['by_severity']}")
    lines.append("")
    lines.append("## Incomplete scopes (нет usable findings)")
    for k, v in report["incomplete_leaves"].items():
        lines.append(f"- `{k}`: {v}")
    lines.append("")
    lines.append("## Critical — ручная верификация")
    for c in crit:
        mark = "АКТУАЛЬНО" if c["still_current"] else "СОМНИТЕЛЬНО/НУЖНА РУЧНАЯ"
        lines.append(f"### [{mark}] `{c['file']}:{c['lines']}`")
        lines.append(f"- Evidence: {', '.join(c['evidence']) or 'n/a'}")
        lines.append(f"- Finding: {c['body'][:400]}")
        lines.append("")
    lines.append("## Spot-checks (selected majors/criticals)")
    for s in spot:
        mark = "АКТУАЛЬНО" if s["still_current"] else "НЕ АКТУАЛЬНО / ИЗМЕНИЛОСЬ"
        lines.append(f"- **{mark}** `{s['file']}:{s['lines']}` — {s['evidence']}")
    lines.append("")
    lines.append("## Proposed GitHub issues (только по актуальным кластерам)")
    lines.append("")
    lines.append("### ISSUE A — [P0] Checkpoint count uses fetched instead of confirmed bronze")
    lines.append("Scope: `batch_executor_loop_flow.py`, `batch_execution/lifecycle.py`")
    lines.append("Source: 2× critical from S01-app-core. Still uses fetched/total_fetched at checkpoint sites.")
    lines.append("")
    lines.append("### ISSUE B — [P0] Composition resource bootstrap without PROVIDERS scope")
    lines.append("Scope: `composition/_resource_management.py` (`_bootstrap_registered_resource`, `preview_cleanup`)")
    lines.append("Source: 1× critical from S04-composition.")
    lines.append("")
    lines.append("### ISSUE C — [P1] Metrics port: label allowlist + loopback default")
    lines.append("Scope: `domain/ports/observability/metrics.py`")
    lines.append("Source: 2× major from S00a.")
    lines.append("")
    lines.append("### ISSUE D — [P1] Domain normalization/VO hardening cluster")
    lines.append("Scope: chembl units case-sensitivity, standard profile overrides, RunContext UTC offset, chembl policy registry idempotency, protein class hierarchy, etc.")
    lines.append(f"Source: ~{sum(1 for f in TRIAGED if f['severity']=='major' and group_key(f)=='domain-hardening')} major domain findings (triage individually in issue body).")
    lines.append("")
    lines.append("### ISSUE E — [P1] Composition correctness (non-layering)")
    lines.append("Scope: entity_type extraction, clear_delta None table, service registry mutable global, workflow memory lock race, replay parentage propagation, config cache key resolve, etc.")
    lines.append("Source: subset of S04 majors that are concrete bugs/races, not pure 'move to application' advice.")
    lines.append("")
    lines.append("### ISSUE F — [P2] Composition layering debt (move logic out of composition)")
    lines.append("Scope: health_service persistence, archive_assessment, run_manifest policy modules, artifact publication policy.")
    lines.append("Source: architectural majors; valid as debt but not runtime defects.")
    lines.append("")
    lines.append("### ISSUE G — [P2] Application control-plane / app-core residual majors")
    lines.append("Scope: remaining S01/S02 majors after checkpoint issue extracted.")
    lines.append("")
    lines.append("## Not proposed as issues")
    lines.append("- Incomplete leaves (S03/S05/S06/S07/S08): re-run CodeRabbit first.")
    lines.append("- Trivial/minor doc-only items: batch into ISSUE F/G or skip.")
    lines.append("- Pure 'move to application layer' without concrete defect: ISSUE F only.")

    md = ROOT / "FINDINGS_RELEVANCE_20260925.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
