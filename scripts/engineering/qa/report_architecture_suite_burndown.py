#!/usr/bin/env python3
"""Inventory architecture suite size and duplicate ratchet stems (#8331)."""

from __future__ import annotations
import argparse
import json
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

DEFAULT_ROOT = Path("tests/architecture")
DEFAULT_JSON = Path("reports/quality/architecture-suite-burndown-inventory.json")
DEFAULT_MD = Path("reports/quality/architecture-suite-burndown-inventory.md")
STEM_SUFFIXES = (
    "_ratchet",
    "_gate",
    "_policy",
    "_inventory",
    "_baseline",
    "_closeout",
)


def _stem_family(path: Path) -> str:
    stem = path.stem
    if stem.startswith("test_"):
        stem = stem[5:]
    while suffix := next(
        (candidate for candidate in STEM_SUFFIXES if stem.endswith(candidate)),
        None,
    ):
        stem = stem[: -len(suffix)]
    return stem


def scan(root: Path) -> dict[str, Any]:
    files = sorted(root.rglob("test_*.py"))
    total_loc = 0
    skip_hits = 0
    families: dict[str, list[str]] = defaultdict(list)
    largest = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        loc = text.count(chr(10)) + 1
        total_loc += loc
        skip_hits += len(
            re.findall(r"pytest\.(skip|xfail)|@pytest\.mark\.(skip|xfail)", text)
        )
        rel = path.relative_to(REPO_ROOT).as_posix()
        families[_stem_family(path)].append(rel)
        largest.append({"path": rel, "loc": loc})
    largest.sort(key=lambda item: item["loc"], reverse=True)
    multi = {k: v for k, v in families.items() if len(v) > 1}
    duplicate_families = {
        family: paths
        for family, paths in sorted(multi.items())
        if any(
            token in family
            for token in ("ratchet", "gate", "purity", "duplication", "hotspot")
        )
    }
    return {
        "file_count": len(files),
        "approx_loc": total_loc,
        "skip_xfail_pattern_hits": skip_hits,
        "multi_file_families_count": len(multi),
        "duplicate_ratchet_candidates": duplicate_families,
        "largest_files": largest[:25],
    }


def build_report(scan_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "architecture-suite-burndown-inventory-v1",
        "linked_issue": "#8331",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "local_lane_recommendation": {
            "pr_default": "architecture-fast-boundary",
            "full_audit": "architecture or architecture-slow-governance",
            "do_not_weaken": ["import-linter", "domain purity", "debt no-growth"],
        },
        "scan": scan_result,
        "burndown_policy": {
            "merge_or_retire": "confirmed duplicates only with owner sign-off",
            "mass_delete": False,
        },
    }


def render_md(report: dict[str, Any]) -> str:
    s = report["scan"]
    lines = [
        "# Architecture suite burndown inventory",
        "",
        "Generated: "
        + report["generated_at_utc"]
        + " ("
        + report["linked_issue"]
        + ")",
        "",
        "- Architecture test files: **" + str(s["file_count"]) + "**",
        "- Approx LOC: **" + str(s["approx_loc"]) + "**",
        "- skip/xfail pattern hits: **" + str(s["skip_xfail_pattern_hits"]) + "**",
        "- Multi-file stem families: **" + str(s["multi_file_families_count"]) + "**",
        "",
        "## Local lane recommendation",
        "",
        "- PR-local: " + report["local_lane_recommendation"]["pr_default"],
        "- Full audit: " + report["local_lane_recommendation"]["full_audit"],
        "",
        "## Duplicate ratchet candidates (advisory)",
        "",
    ]
    cands = s.get("duplicate_ratchet_candidates") or {}
    if not cands:
        lines.append(
            "No high-confidence multi-file ratchet families detected by stem heuristic."
        )
    else:
        for family, paths in list(cands.items())[:30]:
            lines.append("- " + family + ": " + str(len(paths)) + " files")
            for path in paths[:8]:
                lines.append("  - " + path)
    lines.extend(["", "## Largest files", ""])
    for row in s["largest_files"][:15]:
        lines.append("- " + row["path"] + " (" + str(row["loc"]) + " LOC)")
    lines.append("")
    return chr(10).join(lines) + chr(10)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arch-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD)
    args = parser.parse_args(argv)
    result = scan((REPO_ROOT / args.arch_root).resolve())
    report = build_report(result)
    json_out = resolve_output_path(args.json_out, root=REPO_ROOT)
    md_out = resolve_output_path(args.md_out, root=REPO_ROOT)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8"
    )
    md_out.write_text(render_md(report), encoding="utf-8")
    print("Wrote", json_out)
    print("Wrote", md_out)
    print("files=", result["file_count"], "loc=", result["approx_loc"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
