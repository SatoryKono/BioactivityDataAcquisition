#!/usr/bin/env python3
"""Product ``# pyright:`` suppression inventory (shrink-only debt ledger).

Project Diagnostics RF-001 tooling (see
``docs/00-project/ai/agents/guides/BASEDPRIGHT_PROJECT_DIAGNOSTICS.md`` and
``reports/quality/PROJECT_DIAGNOSTICS_REMEDIATION_PLAN_2026-08-14.md``).

Walks ``src/bioetl`` (product surface), counts ``# pyright: ignore[...]`` rules
and file-level ``# pyright: <mode>`` directives, and enforces a shrink-only
ledger:

* ``--update`` writes the current inventory to the baseline JSON.
* ``--check`` fails (exit 1) if the number of suppressed files, total suppressed
  rule occurrences, or any per-rule count **grew** versus the committed baseline.

The command only reads ``*.py`` sources and writes the ledger artifact, so it is
safe to run without a type checker. It intentionally counts the same
source-level suppressions a reviewer sees, independent of a live basedpyright run.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from pathlib import Path

PRODUCT_ROOT = Path("src/bioetl")
DEFAULT_BASELINE = Path("reports/quality/basedpyright-suppression-inventory.json")

_IGNORE_RE = re.compile(r"#\s*pyright:\s*ignore\[([^\]]*)\]")
_MODE_RE = re.compile(r"#\s*pyright:\s*(basic|standard|strict|off)\b")


def collect(root: Path) -> dict[str, object]:
    rule_counts: Counter[str] = Counter()
    mode_counts: Counter[str] = Counter()
    files_with_suppressions: set[str] = set()

    for path in sorted(root.rglob("*.py")):
        rel = path.as_posix()
        text = path.read_text(encoding="utf-8")
        found = False
        for match in _IGNORE_RE.finditer(text):
            found = True
            for raw in match.group(1).split(","):
                rule = raw.strip()
                if rule:
                    rule_counts[rule] += 1
        for match in _MODE_RE.finditer(text):
            found = True
            mode_counts[f"mode:{match.group(1)}"] += 1
        if found:
            files_with_suppressions.add(rel)

    total_rules = sum(rule_counts.values()) + sum(mode_counts.values())
    return {
        "product_root": root.as_posix(),
        "files": len(files_with_suppressions),
        "total_rules": total_rules,
        "by_rule": dict(
            sorted(
                {**rule_counts, **mode_counts}.items(), key=lambda kv: (-kv[1], kv[0])
            )
        ),
        "files_list": sorted(files_with_suppressions),
    }


def _atomic_write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, path)


def _dump(inv: dict[str, object]) -> str:
    return json.dumps(inv, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def _as_int_map(obj: object) -> dict[str, int]:
    if isinstance(obj, dict):
        return {str(k): int(v) for k, v in obj.items()}
    return {}


def check(current: dict[str, object], baseline: dict[str, object]) -> list[str]:
    problems: list[str] = []
    cur_files, base_files = int(str(current["files"])), int(str(baseline["files"]))
    cur_rules_total, base_rules_total = (
        int(str(current["total_rules"])),
        int(str(baseline["total_rules"])),
    )
    if cur_files > base_files:
        problems.append(f"files grew: {base_files} -> {cur_files}")
    if cur_rules_total > base_rules_total:
        problems.append(f"total_rules grew: {base_rules_total} -> {cur_rules_total}")
    base_rules = _as_int_map(baseline.get("by_rule"))
    cur_rules = _as_int_map(current.get("by_rule"))
    for rule, count in sorted(cur_rules.items()):
        if count > base_rules.get(rule, 0):
            problems.append(f"rule {rule} grew: {base_rules.get(rule, 0)} -> {count}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=PRODUCT_ROOT)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument(
        "--update", action="store_true", help="write current inventory as baseline"
    )
    parser.add_argument(
        "--check", action="store_true", help="fail if suppressions grew vs baseline"
    )
    args = parser.parse_args(argv)

    if not args.root.exists():
        parser.error(f"product root not found: {args.root}")

    current = collect(args.root)
    print(
        f"suppression inventory: {current['files']} files, "
        f"{current['total_rules']} rule occurrences"
    )
    for rule, count in list(_as_int_map(current.get("by_rule")).items())[:12]:
        print(f"  {count:>6}  {rule}")

    if args.update:
        _atomic_write(args.baseline, _dump(current))
        print(f"baseline written -> {args.baseline}")
        return 0

    if args.check:
        if not args.baseline.exists():
            parser.error(f"baseline missing: {args.baseline} (run with --update first)")
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        problems = check(current, baseline)
        if problems:
            print("SHRINK-ONLY VIOLATION (debt budgets must not grow):")
            for p in problems:
                print(f"  - {p}")
            return 1
        print("OK: suppressions did not grow vs baseline")
        return 0

    # default: report only
    _atomic_write(
        args.baseline.with_name("basedpyright-suppression-inventory.latest.json"),
        _dump(current),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
