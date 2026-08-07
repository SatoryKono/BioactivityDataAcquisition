#!/usr/bin/env python3
"""Report VCR corpus size by provider vs soft budget (#8337)."""
from __future__ import annotations
import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import yaml
from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path
DEFAULT_ROOT = Path("tests/fixtures/vcr")
DEFAULT_POLICY = Path("configs/quality/integration_vcr_policy.yaml")
DEFAULT_JSON = Path("reports/quality/vcr-corpus-budget-report.json")
DEFAULT_MD = Path("reports/quality/vcr-corpus-budget-report.md")

def _load_budget(policy_path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
    def walk(obj: Any) -> dict[str, Any] | None:
        if isinstance(obj, dict):
            if "corpus_size_budget" in obj and isinstance(obj["corpus_size_budget"], dict):
                return obj["corpus_size_budget"]
            for value in obj.values():
                found = walk(value)
                if found is not None:
                    return found
        return None
    return walk(payload) or {}

def measure_corpus(root: Path) -> dict[str, Any]:
    providers: dict[str, dict[str, int]] = {}
    total_bytes = 0
    total_files = 0
    if not root.exists():
        return {"providers": {}, "total_bytes": 0, "total_files": 0}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".yaml", ".yml"}:
            continue
        rel = path.relative_to(root)
        provider = rel.parts[0] if rel.parts else "_root"
        size = path.stat().st_size
        bucket = providers.setdefault(provider, {"files": 0, "bytes": 0})
        bucket["files"] += 1
        bucket["bytes"] += size
        total_bytes += size
        total_files += 1
    return {"providers": providers, "total_bytes": total_bytes, "total_files": total_files}

def build_report(measure: dict[str, Any], budget: dict[str, Any]) -> dict[str, Any]:
    soft_bytes = int(budget.get("soft_max_total_bytes") or 150_000_000)
    soft_files = int(budget.get("soft_max_file_count") or 500)
    total_bytes = int(measure["total_bytes"])
    total_files = int(measure["total_files"])
    return {
        "schema_version": "vcr-corpus-budget-report-v1",
        "linked_issue": "#8337",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "canonical_root": "tests/fixtures/vcr",
        "budget": {"soft_max_total_bytes": soft_bytes, "soft_max_file_count": soft_files, "gc_policy": budget.get("gc_policy", {})},
        "measured": measure,
        "status": {"within_soft_byte_budget": total_bytes <= soft_bytes, "within_soft_file_budget": total_files <= soft_files,
                   "byte_utilization": round(total_bytes / soft_bytes, 4) if soft_bytes else None},
        "policy_note": "Default action is retain. Deletion requires owner sign-off and replay proof.",
    }

def render_md(report: dict[str, Any]) -> str:
    m = report["measured"]
    lines = ["# VCR corpus size budget report", "",
        "Generated: " + report["generated_at_utc"] + " (" + report["linked_issue"] + ")", "",
        "- Total files: **" + str(m["total_files"]) + "** (soft max " + str(report["budget"]["soft_max_file_count"]) + ")",
        "- Total bytes: **" + str(m["total_bytes"]) + "** (soft max " + str(report["budget"]["soft_max_total_bytes"]) + ")",
        "- Within soft budgets: bytes=" + str(report["status"]["within_soft_byte_budget"]) + " files=" + str(report["status"]["within_soft_file_budget"]),
        "", "## Per provider", "", "| Provider | Files | Bytes |", "| --- | ---: | ---: |"]
    for provider, stats in sorted(m["providers"].items()):
        lines.append("| " + provider + " | " + str(stats["files"]) + " | " + str(stats["bytes"]) + " |")
    lines.extend(["", report["policy_note"], ""])
    return chr(10).join(lines) + chr(10)

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vcr-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD)
    args = parser.parse_args(argv)
    budget = _load_budget(REPO_ROOT / args.policy)
    measure = measure_corpus((REPO_ROOT / args.vcr_root).resolve())
    report = build_report(measure, budget)
    json_out = resolve_output_path(args.json_out, root=REPO_ROOT)
    md_out = resolve_output_path(args.md_out, root=REPO_ROOT)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
    md_out.write_text(render_md(report), encoding="utf-8")
    print("Wrote", json_out)
    print("Wrote", md_out)
    print("files=", measure["total_files"], "bytes=", measure["total_bytes"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
