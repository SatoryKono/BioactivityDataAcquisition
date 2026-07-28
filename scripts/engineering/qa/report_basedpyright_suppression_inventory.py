#!/usr/bin/env python3
"""Inventory + shrink-only ratchet for product ``# pyright:`` suppressions (PD3-9 / #6971).

Baseline and check mode for file-level basedpyright residual flags under src/bioetl.

Usage:
    python -m scripts.engineering.qa.report_basedpyright_suppression_inventory
    python -m scripts.engineering.qa.report_basedpyright_suppression_inventory --check
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "bioetl"
DEFAULT_OUTPUT = (
    ROOT / "reports" / "quality" / "basedpyright-suppression-inventory.json"
)

_DIRECTIVE_RE = re.compile(
    r"^#\s*pyright:\s*(?P<body>.+)$",
)
_RULE_RE = re.compile(r"(report\w+)\s*=\s*false")


def collect_inventory() -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    by_rule: Counter[str] = Counter()
    by_layer: Counter[str] = Counter()
    directive_lines = 0

    for path in sorted(SRC.rglob("*.py")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        # File-level residual flags only (leading `# pyright: reportX=false`).
        # Inline `# pyright: ignore[...]` on a statement is narrower and counted
        # separately as optional metadata, not the PD3 file-level ledger.
        rel = str(path.relative_to(SRC)).replace("\\", "/")
        layer = rel.split("/", 1)[0]
        rules: list[str] = []
        file_level_lines = 0
        inline_ignores = 0
        for line in text.splitlines():
            stripped = line.strip()
            match = _DIRECTIVE_RE.match(stripped)
            if match:
                file_level_lines += 1
                directive_lines += 1
                for rule_match in _RULE_RE.finditer(match.group("body")):
                    rule = rule_match.group(1)
                    rules.append(rule)
                    by_rule[rule] += 1
                continue
            if "pyright: ignore" in line:
                inline_ignores += 1
        if not rules:
            continue
        by_layer[layer] += 1
        files.append(
            {
                "path": rel,
                "layer": layer,
                "rules": sorted(set(rules)),
                "rule_count": len(set(rules)),
                "file_level_directive_lines": file_level_lines,
                "inline_ignore_mentions": inline_ignores,
            }
        )

    return {
        "schema_version": "basedpyright-suppression-inventory-v1",
        "linked_issue": "#6971",
        "parent_epic": "#6961",
        "snapshot_date": date.today().isoformat(),
        "generated_by": "scripts.engineering.qa.report_basedpyright_suppression_inventory",
        "policy": {
            "direction": "shrink_only",
            "tech_debt_budget_growth": "forbidden",
            "product_errors_must_remain": 0,
            "new_suppressions": "require issue link + rationale in same PR",
            "on_edit": "try remove # pyright directive first, then structural fix",
        },
        "summary": {
            "files_with_suppressions": len(files),
            "directive_line_count": directive_lines,
            "rule_assignment_count": int(sum(by_rule.values())),
        },
        "by_layer": dict(by_layer.most_common()),
        "by_rule": dict(by_rule.most_common()),
        "files": files,
    }


def write_inventory(output: Path) -> dict[str, Any]:
    payload = collect_inventory()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return payload


def check_inventory(output: Path) -> None:
    if not output.is_file():
        raise SystemExit(f"missing suppression inventory: {output}")
    committed = json.loads(output.read_text(encoding="utf-8"))
    live = collect_inventory()
    c_files = int(committed.get("summary", {}).get("files_with_suppressions", 0))
    l_files = int(live.get("summary", {}).get("files_with_suppressions", 0))
    c_rules = int(committed.get("summary", {}).get("rule_assignment_count", 0))
    l_rules = int(live.get("summary", {}).get("rule_assignment_count", 0))
    if l_files > c_files or l_rules > c_rules:
        raise SystemExit(
            "basedpyright suppression residual grew: "
            f"files live={l_files} committed={c_files}; "
            f"rules live={l_rules} committed={c_rules}"
        )
    print(
        "[ok] basedpyright suppression non-growth: "
        f"files live={l_files} committed={c_files}; "
        f"rules live={l_rules} committed={c_rules}"
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    output = args.json_out if args.json_out.is_absolute() else ROOT / args.json_out
    if args.check:
        check_inventory(output)
        return
    payload = write_inventory(output)
    s = payload["summary"]
    print(
        "[updated] wrote suppression inventory: "
        f"{output} files={s['files_with_suppressions']} "
        f"rules={s['rule_assignment_count']}"
    )


if __name__ == "__main__":
    main()
